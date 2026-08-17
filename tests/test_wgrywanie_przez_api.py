"""Wgrywanie plików przez API — od żądania HTTP po wpis w bazie.

Testy modułu `wczytywanie` sprawdzają ekstrakcję. Tutaj sprawdzamy to,
czego one nie widzą: rozbiór `multipart/form-data`, strażnika sesji
i to, że plik ODRZUCONY nie trafia do akt.

⚠️ Własna baza w katalogu tymczasowym. Test dotykający `panel/dane/`
   dopisywałby dokumenty do akt, na których pracuje kancelaria.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
import uuid
import zipfile
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402
import serwer  # noqa: E402

HASLO = "Praworzadnosc2026!"
ZDANIE = ("Sąd Okręgowy w Warszawie postanowieniem z 14 września 2006 r. "
          "oddalił wniosek obrońcy o dopuszczenie dowodu z opinii biegłego.")


def _docx(tresc: str) -> bytes:
    bufor = BytesIO()
    with zipfile.ZipFile(bufor, "w") as archiwum:
        archiwum.writestr("[Content_Types].xml", "<Types/>")
        archiwum.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main"><w:body>'
            f'<w:p><w:r><w:t>{tresc}</w:t></w:r></w:p>'
            '</w:body></w:document>')
    return bufor.getvalue()


def _multipart(pliki: list[tuple[str, bytes]],
               pola: dict[str, str] | None = None) -> tuple[bytes, str]:
    granica = "----kl" + uuid.uuid4().hex
    czesci: list[bytes] = []
    for nazwa, wartosc in (pola or {}).items():
        czesci.append(
            f"--{granica}\r\nContent-Disposition: form-data; "
            f'name="{nazwa}"\r\n\r\n{wartosc}\r\n'.encode("utf-8"))
    for nazwa_pliku, bajty in pliki:
        czesci.append(
            f"--{granica}\r\nContent-Disposition: form-data; name=\"pliki\"; "
            f'filename="{nazwa_pliku}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
            + bajty + b"\r\n")
    czesci.append(f"--{granica}--\r\n".encode("utf-8"))
    return b"".join(czesci), f"multipart/form-data; boundary={granica}"


@pytest.fixture(scope="module")
def panel():
    """Serwer panelu na własnej bazie, na porcie przydzielonym przez system.

    Baza w pamięci, nie w katalogu tymczasowym: test dotykający
    `panel/dane/` dopisywałby dokumenty do akt, na których pracuje
    kancelaria, a `tmp_path` bywa niedostępny przy równoległych
    przebiegach. Połączenie ma `check_same_thread=False`, więc wątki
    obsługi żądań korzystają z tego samego obiektu.
    """
    poprzednia = serwer.DB
    serwer.DB = baza.polacz(":memory:")

    mod_profile.zaloz(serwer.DB, "adwokat", HASLO, "Anna", "Kowalska",
                      "prawnik", zgody=[z["id"] for z in mod_profile.ZGODY])
    sprawa_id = baza.dodaj_sprawe(serwer.DB, "II K 1/26", "Sprawa testowa")

    usluga = ThreadingHTTPServer(("127.0.0.1", 0), serwer.Uchwyt)
    watek = threading.Thread(target=usluga.serve_forever, daemon=True)
    watek.start()
    adres = f"http://127.0.0.1:{usluga.server_address[1]}"

    yield adres, sprawa_id

    usluga.shutdown()
    usluga.server_close()
    serwer.DB.close()
    serwer.DB = poprzednia


def _zaloguj(adres: str) -> str:
    cialo = json.dumps({"login": "adwokat", "haslo": HASLO}).encode()
    zadanie = urllib.request.Request(
        adres + "/api/profil/logowanie", data=cialo,
        headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(zadanie, timeout=10) as odp:
        ciastko = odp.headers.get("Set-Cookie") or ""
    return ciastko.split(";")[0]


def _wgraj(adres: str, sprawa_id: int, pliki, ciastko: str | None):
    cialo, typ = _multipart(pliki)
    naglowki = {"Content-Type": typ}
    if ciastko:
        naglowki["Cookie"] = ciastko
    zadanie = urllib.request.Request(
        f"{adres}/api/sprawy/{sprawa_id}/dokumenty/plik",
        data=cialo, headers=naglowki)
    try:
        with urllib.request.urlopen(zadanie, timeout=30) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ── strażnik sesji ───────────────────────────────────────────────────

def test_wgrywanie_bez_zalogowania_odrzucone(panel):
    """⚠️ Wgrywanie jest zapisem do akt — musi być za strażnikiem.

    Endpoint jest rozpatrywany PRZED odczytem ciała żądania, więc łatwo
    o pominięcie kontroli sesji przy takiej kolejności.
    """
    adres, sprawa_id = panel
    kod, odp = _wgraj(adres, sprawa_id, [("pismo.txt", b"tresc")], None)
    assert kod == 401
    assert odp.get("wymaga_logowania")


# ── ścieżka udana ────────────────────────────────────────────────────

def test_wgranie_txt_trafia_do_akt(panel):
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    kod, odp = _wgraj(adres, sprawa_id,
                      [("postanowienie.txt", ZDANIE.encode("utf-8"))], ciastko)

    assert kod == 201, odp
    assert len(odp["wczytane"]) == 1
    assert odp["wczytane"][0]["nazwa"] == "postanowienie.txt"

    dok = baza.pobierz_dokument(serwer.DB, sprawa_id, odp["wczytane"][0]["id"])
    assert dok is not None
    assert "Sąd Okręgowy" in dok["tresc"]


def test_wgranie_wielu_plikow_naraz(panel):
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    kod, odp = _wgraj(adres, sprawa_id, [
        ("pismo-a.txt", ZDANIE.encode("utf-8")),
        ("pismo-b.docx", _docx(ZDANIE)),
    ], ciastko)

    assert kod == 201, odp
    assert len(odp["wczytane"]) == 2
    assert {w["typ"] for w in odp["wczytane"]} == {"tekst", "docx"}


def test_polskie_znaki_przezywaja_droge_przez_http(panel):
    """Granica multipart rozdziela BAJTY. Dekodowanie całości jako tekst
    psułoby pliki binarne i polskie znaki w treści."""
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    kod, odp = _wgraj(adres, sprawa_id,
                      [("pismo.docx", _docx(ZDANIE))], ciastko)

    assert kod == 201
    dok = baza.pobierz_dokument(serwer.DB, sprawa_id, odp["wczytane"][0]["id"])
    assert "września" in dok["tresc"] and "obrońcy" in dok["tresc"]


# ── ścieżka odmowy ───────────────────────────────────────────────────

def test_skan_nie_trafia_do_akt(panel):
    """⚠️ TEST NAJWAŻNIEJSZY W TYM PLIKU.

    Sprawa, która dostaje pusty dokument, wygląda na kompletną i nie
    jest. Prawnik pyta o akta, w których model niczego nie widzi,
    i dostaje odmowę nie do odróżnienia od „w aktach tego nie ma".
    """
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    przed = len(baza.lista_dokumentow(serwer.DB, sprawa_id))

    skan = (b"%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\n"
            b"endobj\n" + b"\x00" * 300_000)
    kod, odp = _wgraj(adres, sprawa_id, [("skan.pdf", skan)], ciastko)

    assert kod == 400
    assert odp["wczytane"] == []
    assert odp["odrzucone"][0]["wymaga_ocr"] is True
    assert len(baza.lista_dokumentow(serwer.DB, sprawa_id)) == przed


def test_odrzucenie_jednego_nie_blokuje_pozostalych(panel):
    """Wgranie dwudziestu pism nie może paść przez jeden zły plik."""
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    skan = (b"%PDF-1.4\n1 0 obj\n<< /Subtype /Image >>\nendobj\n"
            + b"\x00" * 300_000)

    kod, odp = _wgraj(adres, sprawa_id, [
        ("dobre.txt", ZDANIE.encode("utf-8")),
        ("skan.pdf", skan),
    ], ciastko)

    assert kod == 201
    assert len(odp["wczytane"]) == 1
    assert len(odp["odrzucone"]) == 1


def test_zadanie_bez_pliku_odrzucone(panel):
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres)
    kod, odp = _wgraj(adres, sprawa_id, [], ciastko)
    assert kod == 400
    assert "plik" in odp["blad"].lower()


# ── terminy procesowe przez API ──────────────────────────────────────

def _get(adres: str, sciezka: str, ciastko: str | None):
    zadanie = urllib.request.Request(
        adres + sciezka, headers={"Cookie": ciastko} if ciastko else {})
    try:
        with urllib.request.urlopen(zadanie, timeout=10) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(adres: str, sciezka: str, cialo: dict, ciastko: str | None):
    naglowki = {"Content-Type": "application/json; charset=utf-8"}
    if ciastko:
        naglowki["Cookie"] = ciastko
    zadanie = urllib.request.Request(
        adres + sciezka, data=json.dumps(cialo).encode("utf-8"),
        headers=naglowki)
    try:
        with urllib.request.urlopen(zadanie, timeout=10) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_katalog_regul_wymaga_zalogowania(panel):
    adres, _ = panel
    kod, _ = _get(adres, "/api/terminy/reguly", None)
    assert kod == 401


def test_katalog_regul_przez_api(panel):
    adres, _ = panel
    kod, odp = _get(adres, "/api/terminy/reguly", _zaloguj(adres))
    assert kod == 200
    assert len(odp["reguly"]) >= 7


def test_liczenie_terminu_przez_api(panel):
    """Ten sam przypadek, co w teście modułu: upływ na Boże Ciało."""
    adres, sprawa_id = panel
    kod, odp = _post(adres, "/api/terminy/oblicz",
                     {"regula_id": "apelacja_karna",
                      "data_zdarzenia": "2026-05-21",
                      "sprawa_id": sprawa_id}, _zaloguj(adres))
    assert kod == 200
    assert odp["data_uplywu"] == "2026-06-05"
    assert odp["wiazacy"] is False


def test_liczenie_terminu_trafia_do_audytu(panel):
    """Policzony termin jest czynnością, którą trzeba móc odtworzyć."""
    adres, sprawa_id = panel
    _post(adres, "/api/terminy/oblicz",
          {"regula_id": "zazalenie_karne", "data_zdarzenia": "2026-03-02",
           "sprawa_id": sprawa_id}, _zaloguj(adres))
    wpisy = [dict(w) for w in serwer.DB.execute(
        "SELECT * FROM audyt WHERE operacja = 'termin.policzony'")]
    assert wpisy
    assert "zazalenie_karne" in wpisy[-1]["szczegol"]


def test_zla_data_zwraca_400_a_nie_500(panel):
    adres, _ = panel
    kod, odp = _post(adres, "/api/terminy/oblicz",
                     {"regula_id": "apelacja_karna",
                      "data_zdarzenia": "wczoraj"}, _zaloguj(adres))
    assert kod == 400
    assert "RRRR-MM-DD" in odp["blad"]
