"""Odtworzenie z kopii przez panel — bramka ciągłości działania.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TO POWSTAŁO
════════════════════════════════════════════════════════════════════════

`kopia.odtworz()` istniało od dawna i było przetestowane (11 testów
w `test_kopia.py`), ale **nie miało drogi z panelu** — ani punktu
końcowego, ani przycisku. Odtworzenie było czynnością programistyczną.

Deklarowane w dokumentacji RTO ≤ 8 h nie miało wtedy pokrycia: w dniu
awarii dysku nikt nie uruchamia Pythona z konsoli, a osoba w kancelarii
nie ma jak przywrócić akt.

⚠️ TO JEST NAJBARDZIEJ NISZCZĄCA OPERACJA W CAŁYM PANELU.
   Podmienia całą bazę akt. Dlatego trzy niezależne warunki, z których
   KAŻDY blokuje osobno — i każdy ma tutaj własny test:

     1. rola `prawnik`               → inaczej 403
     2. brak trwającego zadania      → inaczej 409
     3. przepisanie nazwy pliku      → inaczej 400

   Testy sprawdzają też rzecz najważniejszą: że przy odmowie
   **bieżące akta pozostają nietknięte**.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import kopia as mod_kopia  # noqa: E402
import profile as mod_profile  # noqa: E402
import serwer  # noqa: E402

HASLO = "haslo-do-testu-odtworzenia"
ZGODY = [z["id"] for z in mod_profile.ZGODY]


@pytest.fixture()
def panel():
    """Panel na bazie PLIKOWEJ w katalogu tymczasowym.

    ⚠️ Baza musi być plikiem, nie `:memory:` — odtworzenie polega na
    podmianie pliku, więc na bazie w pamięci nie dałoby się go
    przetestować wcale.

    ⚠️ NIE UŻYWAMY `tmp_path`. Fixture pytest tworzy katalog
    `pytest-of-<user>`, a na tej maszynie kończy się to `PermissionError`.
    Ten sam problem obszedł już `test_wgrywanie_przez_api.py`, wybierając
    bazę w pamięci — tutaj to niemożliwe, więc katalog robimy wprost
    przez `tempfile`.

    `serwer.SCIEZKA_DB` jest podmieniane razem z `serwer.DB`: bez tego
    ponowne połączenie po odtworzeniu poszłoby do PRAWDZIWEJ bazy
    kancelarii, a przebieg testów dotknąłby akt.
    """
    tmp_path = Path(tempfile.mkdtemp(prefix="kl-odtworzenie-"))
    poprzednia_db, poprzednia_sciezka = serwer.DB, serwer.SCIEZKA_DB
    poprzedni_katalog = serwer.KATALOG_KOPII

    serwer.SCIEZKA_DB = tmp_path / "panel.sqlite3"
    serwer.DB = baza.polacz(serwer.SCIEZKA_DB)
    serwer.KATALOG_KOPII = tmp_path / "kopie"
    serwer.KATALOG_KOPII.mkdir()

    mod_profile.zaloz(serwer.DB, "adwokat", HASLO, "Anna", "Kowalska",
                      "prawnik", zgody=ZGODY)
    mod_profile.zaloz(serwer.DB, "sekretarka", HASLO, "Ewa", "Nowak",
                      "sekretariat", zgody=ZGODY)

    usluga = ThreadingHTTPServer(("127.0.0.1", 0), serwer.Uchwyt)
    threading.Thread(target=usluga.serve_forever, daemon=True).start()
    adres = f"http://127.0.0.1:{usluga.server_address[1]}"

    yield adres, tmp_path

    usluga.shutdown()
    usluga.server_close()
    serwer.DB.close()
    serwer.DB, serwer.SCIEZKA_DB = poprzednia_db, poprzednia_sciezka
    serwer.KATALOG_KOPII = poprzedni_katalog
    shutil.rmtree(tmp_path, ignore_errors=True)


def _zaloguj(adres: str, login: str = "adwokat") -> str:
    cialo = json.dumps({"login": login, "haslo": HASLO}).encode()
    zadanie = urllib.request.Request(
        adres + "/api/profil/logowanie", data=cialo,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(zadanie, timeout=10) as odp:
        return (odp.headers.get("Set-Cookie") or "").split(";")[0]


def _zadaj(adres: str, sciezka: str, ciastko: str | None = None,
           cialo: dict | None = None, metoda: str = "POST"):
    naglowki = {"Content-Type": "application/json"}
    if ciastko:
        naglowki["Cookie"] = ciastko
    zadanie = urllib.request.Request(
        adres + sciezka,
        data=json.dumps(cialo or {}).encode() if metoda == "POST" else None,
        headers=naglowki, method=metoda)
    try:
        with urllib.request.urlopen(zadanie, timeout=30) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        tresc = e.read()
        return e.code, (json.loads(tresc) if tresc else {})


def _zrob_kopie(adres: str, ciastko: str) -> str:
    kod, d = _zadaj(adres, "/api/kopie", ciastko)
    assert kod == 201, d
    return d["nazwa"]


# ── ścieżka właściwa ────────────────────────────────────────────────

def test_odtworzenie_cofa_baze_do_stanu_z_kopii(panel):
    """Sedno całej funkcji: baza wraca do stanu z chwili zdjęcia kopii.

    Scenariusz odpowiada prawdziwej awarii: po kopii ktoś wprowadził
    zmiany, które trzeba cofnąć — albo baza uległa uszkodzeniu i wraca
    się do ostatniego dobrego stanu.
    """
    adres, _ = panel
    ciastko = _zaloguj(adres)

    kod, _ = _zadaj(adres, "/api/sprawy", ciastko,
                    {"sygnatura": "II K 7/26", "nazwa": "Sprawa sprzed kopii"})
    assert kod == 201
    nazwa = _zrob_kopie(adres, ciastko)

    kod, _ = _zadaj(adres, "/api/sprawy", ciastko,
                    {"sygnatura": "II K 8/26", "nazwa": "Dodana PO kopii"})
    assert kod == 201
    kod, d = _zadaj(adres, "/api/sprawy", ciastko, metoda="GET")
    assert len(d["sprawy"]) == 2

    kod, d = _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko,
                    {"potwierdzenie": nazwa})
    assert kod == 200, d
    assert d["spraw_przed"] == 2 and d["spraw_po"] == 1, d

    kod, d = _zadaj(adres, "/api/sprawy", ciastko, metoda="GET")
    assert [s["sygnatura"] for s in d["sprawy"]] == ["II K 7/26"], (
        "baza nie wróciła do stanu z kopii")


def test_poprzednia_baza_zostaje_odlozona(panel):
    """Odtworzenie z niewłaściwej kopii musi być odwracalne."""
    adres, katalog = panel
    ciastko = _zaloguj(adres)
    nazwa = _zrob_kopie(adres, ciastko)

    _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko,
           {"potwierdzenie": nazwa})

    odlozone = list(katalog.glob("*.przed-odtworzeniem"))
    assert odlozone, f"nie odłożono poprzedniej bazy; jest: {list(katalog.iterdir())}"


def test_odtworzenie_trafia_do_audytu(panel):
    adres, _ = panel
    ciastko = _zaloguj(adres)
    nazwa = _zrob_kopie(adres, ciastko)
    _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko,
           {"potwierdzenie": nazwa})

    kod, d = _zadaj(adres, "/api/audyt", ciastko, metoda="GET")
    operacje = [w["operacja"] for w in d["wpisy"]]
    assert "kopia.odtworzenie" in operacje, operacje
    wpis = next(w for w in d["wpisy"] if w["operacja"] == "kopia.odtworzenie")
    assert nazwa in wpis["szczegol"]
    assert "osoba=adwokat" in wpis["szczegol"], wpis["szczegol"]


# ── trzy niezależne blokady ─────────────────────────────────────────

def test_bez_zalogowania_odrzucone(panel):
    adres, _ = panel
    kod, _ = _zadaj(adres, "/api/kopie/cokolwiek.sqlite3/odtworz", None,
                    {"potwierdzenie": "cokolwiek.sqlite3"})
    assert kod == 401


def test_rola_inna_niz_prawnik_odrzucona(panel):
    """Sekretariat nie nadpisuje akt kancelarii."""
    adres, _ = panel
    ciastko_prawnika = _zaloguj(adres)
    nazwa = _zrob_kopie(adres, ciastko_prawnika)

    ciastko_sekretarki = _zaloguj(adres, "sekretarka")
    kod, d = _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko_sekretarki,
                    {"potwierdzenie": nazwa})
    assert kod == 403, d
    assert "prawnik" in d["blad"]


@pytest.mark.parametrize("potwierdzenie", ["", "tak", "nie ta nazwa", "TAK"])
def test_zle_potwierdzenie_odrzucone(panel, potwierdzenie):
    """Kliknięcie „OK" da się zrobić odruchowo; przepisanie nazwy nie."""
    adres, _ = panel
    ciastko = _zaloguj(adres)
    nazwa = _zrob_kopie(adres, ciastko)

    kod, d = _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko,
                    {"potwierdzenie": potwierdzenie})
    assert kod == 400, d
    assert nazwa in d["blad"], "komunikat ma podać, co przepisać"


def test_nieistniejaca_kopia_to_404(panel):
    adres, _ = panel
    ciastko = _zaloguj(adres)
    kod, _ = _zadaj(adres, "/api/kopie/nie-ma-takiej.sqlite3/odtworz", ciastko,
                    {"potwierdzenie": "nie-ma-takiej.sqlite3"})
    assert kod == 404


def test_odmowa_nie_rusza_biezacych_akt(panel):
    """Najważniejszy test tego pliku.

    Przy KAŻDEJ odmowie akta muszą zostać nietknięte — inaczej nieudana
    próba odtworzenia byłaby gorsza od jej braku.
    """
    adres, _ = panel
    ciastko = _zaloguj(adres)
    _zadaj(adres, "/api/sprawy", ciastko,
           {"sygnatura": "II K 9/26", "nazwa": "Ma przetrwać"})
    nazwa = _zrob_kopie(adres, ciastko)
    _zadaj(adres, "/api/sprawy", ciastko,
           {"sygnatura": "II K 10/26", "nazwa": "Dodana po kopii"})

    # Złe potwierdzenie — odtworzenie ma się nie odbyć.
    kod, _ = _zadaj(adres, f"/api/kopie/{nazwa}/odtworz", ciastko,
                    {"potwierdzenie": "byle co"})
    assert kod == 400

    kod, d = _zadaj(adres, "/api/sprawy", ciastko, metoda="GET")
    sygnatury = sorted(s["sygnatura"] for s in d["sprawy"])
    assert sygnatury == ["II K 10/26", "II K 9/26"], (
        f"odmowa ruszyła akta: {sygnatury}")


def test_uszkodzona_kopia_nie_nadpisuje_bazy(panel):
    """Plik, który nie jest bazą, ma zostać odrzucony PRZED podmianą."""
    adres, katalog = panel
    ciastko = _zaloguj(adres)
    _zadaj(adres, "/api/sprawy", ciastko,
           {"sygnatura": "II K 11/26", "nazwa": "Ma przetrwać"})

    smiec = serwer.KATALOG_KOPII / "kopia-2026-01-01-0000.sqlite3"
    smiec.write_bytes(b"to nie jest baza danych")

    kod, d = _zadaj(adres, f"/api/kopie/{smiec.name}/odtworz", ciastko,
                    {"potwierdzenie": smiec.name})
    assert kod == 400, d

    kod, d = _zadaj(adres, "/api/sprawy", ciastko, metoda="GET")
    assert [s["sygnatura"] for s in d["sprawy"]] == ["II K 11/26"], (
        "uszkodzona kopia nadpisała bazę")
