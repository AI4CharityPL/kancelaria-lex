"""Wielu użytkowników naraz — sprawdzenie wymogu, który dotąd nie był badany.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TO POWSTAŁO
════════════════════════════════════════════════════════════════════════

Wymóg projektu brzmiał od początku: „różne osoby, w różnym czasie, na
różnych profilach". Testy pokrywały część „w różnym czasie" — każdy
wysyłał żądania po kolei. **Żaden test nie wysłał dwóch żądań naraz.**

Tymczasem panel jest wielowątkowy (`serwer.py`: `ThreadingHTTPServer`),
dzieli JEDNO połączenie SQLite między wątki (`serwer.py:50`,
`baza.py:195` z `check_same_thread=False`) i ma jedną globalną kolejkę
z semaforem 1 (`zadania.py:60`). Trzy założenia, z których każde może
zawieść dopiero pod obciążeniem — czyli u klienta, nie na testach.

⚠️ BEZ WYWOŁAŃ MODELU. Te testy mają trwać sekundy, nie minuty:
   współbieżność sprawdzamy na warstwie HTTP i kolejki, a nie na
   generowaniu odpowiedzi. Kolejność zdarzeń wymuszamy przez
   `threading.Event`, nie przez usypianie — dzięki temu test jest
   deterministyczny i nie zależy od tego, jak zajęta jest maszyna.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402
import serwer  # noqa: E402
import zadania as mod_zadania  # noqa: E402

HASLO = "haslo-do-testu-wspolbieznosci"
ZGODY = [z["id"] for z in mod_profile.ZGODY]


@pytest.fixture()
def panel():
    """Panel z DWOMA profilami, na bazie w pamięci dzielonej przez wątki.

    Baza w pamięci jest tu właściwym wyborem: sprawdzamy zachowanie
    współbieżne jednego połączenia, a nie trwałość zapisu.
    """
    poprzednia = serwer.DB
    serwer.DB = baza.polacz(":memory:")

    mod_profile.zaloz(serwer.DB, "adwokat", HASLO, "Anna", "Kowalska",
                      "prawnik", zgody=ZGODY)
    mod_profile.zaloz(serwer.DB, "aplikant", HASLO, "Piotr", "Zieliński",
                      "aplikant", zgody=ZGODY)
    sprawa_id = baza.dodaj_sprawe(serwer.DB, "II K 50/26", "Sprawa wspólna")

    usluga = ThreadingHTTPServer(("127.0.0.1", 0), serwer.Uchwyt)
    threading.Thread(target=usluga.serve_forever, daemon=True).start()
    adres = f"http://127.0.0.1:{usluga.server_address[1]}"

    yield adres, sprawa_id

    usluga.shutdown()
    usluga.server_close()
    serwer.DB.close()
    serwer.DB = poprzednia


def _zaloguj(adres: str, login: str) -> str:
    cialo = json.dumps({"login": login, "haslo": HASLO}).encode()
    zadanie = urllib.request.Request(
        adres + "/api/profil/logowanie", data=cialo,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(zadanie, timeout=10) as odp:
        return (odp.headers.get("Set-Cookie") or "").split(";")[0]


def _zadaj(adres, sciezka, ciastko=None, cialo=None, metoda="GET"):
    naglowki = {"Content-Type": "application/json"}
    if ciastko:
        naglowki["Cookie"] = ciastko
    zadanie = urllib.request.Request(
        adres + sciezka,
        data=json.dumps(cialo).encode() if cialo is not None else None,
        headers=naglowki, method=metoda)
    try:
        with urllib.request.urlopen(zadanie, timeout=30) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        tresc = e.read()
        return e.code, (json.loads(tresc) if tresc else {})


# ── 1. Sesje dwóch osób nie mieszają się pod obciążeniem ────────────

def test_sesje_dwoch_osob_nie_mieszaja_sie(panel):
    """Najgroźniejsza możliwa usterka współbieżności w tym systemie.

    Gdyby wątki serwera dzieliły stan sesji, jedna osoba widziałaby akta
    pod tożsamością drugiej — a wpisy audytu przypisywałyby jej cudze
    pytania. Wysyłamy 40 przeplecionych żądań i sprawdzamy, że każde
    odpowiada właściwym profilem.
    """
    adres, _ = panel
    ciastka = {"adwokat": _zaloguj(adres, "adwokat"),
               "aplikant": _zaloguj(adres, "aplikant")}

    def kto(login: str) -> str:
        kod, d = _zadaj(adres, "/api/profil/stan", ciastka[login])
        assert kod == 200
        return (d.get("profil") or {}).get("login")

    with ThreadPoolExecutor(max_workers=8) as pula:
        loginy = ["adwokat", "aplikant"] * 20
        wyniki = list(pula.map(kto, loginy))

    assert wyniki == loginy, (
        "sesja przeciekła między wątkami — któreś żądanie dostało cudzy "
        "profil")


def test_bez_ciastka_zawsze_odmowa_takze_pod_obciazeniem(panel):
    """Strażnik nie może się „zmęczyć" przy wielu żądaniach naraz."""
    adres, sprawa_id = panel

    def bez_sesji(_):
        kod, _d = _zadaj(adres, f"/api/sprawy/{sprawa_id}/watki")
        return kod

    with ThreadPoolExecutor(max_workers=8) as pula:
        kody = list(pula.map(bez_sesji, range(30)))

    assert set(kody) == {401}, f"strażnik przepuścił: {sorted(set(kody))}"


# ── 2. Zapisy równoległe nie gubią się ──────────────────────────────

def test_dwadziescia_watkow_naraz_nie_gubi_zapisu(panel):
    """Jedno połączenie SQLite dzielone przez wątki serwera.

    `check_same_thread=False` zdejmuje ochronę biblioteki, więc to
    założenie trzeba sprawdzić, a nie przyjąć. Gubienie zapisów przy
    dwóch osobach pracujących naraz byłoby usterką niewidoczną do
    momentu, w którym ktoś zauważy brak swojego wątku.
    """
    adres, sprawa_id = panel
    ciastko = _zaloguj(adres, "adwokat")

    def zaloz(nr: int):
        kod, d = _zadaj(adres, f"/api/sprawy/{sprawa_id}/watki", ciastko,
                        {"tytul": f"Wątek {nr:02d}"}, "POST")
        return kod, d

    with ThreadPoolExecutor(max_workers=10) as pula:
        wyniki = list(pula.map(zaloz, range(20)))

    kody = {k for k, _ in wyniki}
    assert kody == {201}, f"nie wszystkie zapisy się udały: {sorted(kody)}"

    kod, d = _zadaj(adres, f"/api/sprawy/{sprawa_id}/watki", ciastko)
    tytuly = sorted(w["tytul"] for w in d["watki"])
    assert tytuly == sorted(f"Wątek {n:02d}" for n in range(20)), (
        f"zgubiono zapisy: jest {len(tytuly)} z 20")


def test_odczyt_i_zapis_naraz_nie_wywraca_bazy(panel):
    """Mieszanka odczytów i zapisów — typowa praca dwóch osób."""
    adres, sprawa_id = panel
    ciastko_a = _zaloguj(adres, "adwokat")
    ciastko_b = _zaloguj(adres, "aplikant")

    def praca(nr: int):
        if nr % 2:
            return _zadaj(adres, f"/api/sprawy/{sprawa_id}/watki", ciastko_a,
                          {"tytul": f"Zapis {nr}"}, "POST")[0]
        return _zadaj(adres, f"/api/sprawy/{sprawa_id}/watki", ciastko_b)[0]

    with ThreadPoolExecutor(max_workers=10) as pula:
        kody = list(pula.map(praca, range(40)))

    assert set(kody) <= {200, 201}, (
        f"żądanie zakończyło się błędem: {sorted(set(kody))}")


# ── 3. Kolejka: semafor 1 faktycznie szereguje ──────────────────────

def test_semafor_przepuszcza_jedno_zadanie_naraz():
    """Założenie z `konfiguracja.py:36` („panel wykonuje jedno zapytanie
    naraz") nie było dotąd nigdzie sprawdzone.

    Kolejność wymuszamy zdarzeniami, nie usypianiem — test jest przez to
    deterministyczny i trwa milisekundy.
    """
    kolejka = mod_zadania.Kolejka()
    pierwsze_ruszylo = threading.Event()
    zwolnij_pierwsze = threading.Event()
    drugie_ruszylo = threading.Event()

    def praca_pierwsza(_melduj):
        pierwsze_ruszylo.set()
        zwolnij_pierwsze.wait(timeout=5)
        return "pierwsze"

    def praca_druga(_melduj):
        drugie_ruszylo.set()
        return "drugie"

    id1 = kolejka.uruchom(praca_pierwsza)
    assert pierwsze_ruszylo.wait(timeout=5), "pierwsze zadanie nie ruszyło"

    id2 = kolejka.uruchom(praca_druga)
    # Drugie NIE MOŻE ruszyć, dopóki pierwsze trzyma slot.
    assert not drugie_ruszylo.wait(timeout=0.5), (
        "dwa zadania weszły naraz — semafor nie szereguje, a model na "
        "8 GB VRAM obsłuży tylko jedno")
    assert kolejka.stan(id2)["stan"] == "oczekuje"

    zwolnij_pierwsze.set()
    assert drugie_ruszylo.wait(timeout=5), "drugie zadanie nigdy nie ruszyło"

    for zid in (id1, id2):
        for _ in range(100):
            if kolejka.stan(zid)["stan"] in ("gotowe", "blad"):
                break
        assert kolejka.stan(zid)["stan"] == "gotowe", kolejka.stan(zid)


def test_blad_jednego_zadania_zwalnia_slot():
    """Zadanie, które padło, nie może zablokować kolejki na zawsze.

    Bez tego jeden wyjątek w analizie unieruchamiałby panel dla
    wszystkich użytkowników aż do restartu.
    """
    kolejka = mod_zadania.Kolejka()

    def praca_zla(_melduj):
        raise RuntimeError("celowy błąd")

    id_zle = kolejka.uruchom(praca_zla)
    for _ in range(200):
        if kolejka.stan(id_zle)["stan"] in ("gotowe", "blad"):
            break
    assert kolejka.stan(id_zle)["stan"] == "blad"

    ruszylo = threading.Event()
    id_dobre = kolejka.uruchom(lambda _m: ruszylo.set() or "ok")
    assert ruszylo.wait(timeout=5), "slot nie został zwolniony po błędzie"


def test_przepelnienie_historii_nie_wywraca_kolejki():
    """`zadania.py:68-69` przycina historię do 50 pozycji.

    Wpis może zostać usunięty ze słownika, ZANIM jego wątek skończy —
    sprawdzamy, że nie kończy się to wyjątkiem w wątku tła ani zawieszeniem.
    """
    kolejka = mod_zadania.Kolejka(maks_historii=5)
    identyfikatory = [kolejka.uruchom(lambda _m, n=n: n) for n in range(20)]

    for _ in range(500):
        if all(kolejka.stan(z) is None or
               kolejka.stan(z)["stan"] in ("gotowe", "blad")
               for z in identyfikatory):
            break

    zyjace = [z for z in identyfikatory if kolejka.stan(z) is not None]
    assert len(zyjace) <= 5, f"historia nie została przycięta: {len(zyjace)}"
    assert all(kolejka.stan(z)["stan"] == "gotowe" for z in zyjace)
