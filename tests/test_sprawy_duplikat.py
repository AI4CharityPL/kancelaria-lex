"""Duplikat sygnatury — ostrzeżenie zamiast cichego przyjęcia.

TŁO — wykryte przeglądem interfejsu 16.08.2026.
    Lista spraw pokazywała kilka pozycji o tej samej sygnaturze i nic
    tego nie sygnalizowało. Sygnatura identyfikuje sprawę, więc dla
    prawnika oznacza to pytanie „która jest ta właściwa" — a przy
    zamknięciu zakresu w obrębie sprawy realne ryzyko, że pytanie trafi
    do niepełnego kompletu akt.

ZASADA PRZYJĘTA TUTAJ: ostrzegamy, nie blokujemy.
    Bywa, że kancelaria świadomie zakłada drugi rekord. Odmowa na twardo
    byłaby wtedy przeszkodą, a ciche przyjęcie — pułapką. Dlatego
    duplikat wymaga POTWIERDZENIA (`mimo_duplikatu`), czyli powstaje
    świadomie, a nie przez przeoczenie.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402
import serwer  # noqa: E402

HASLO = "haslo-do-testu-duplikatu"


@pytest.fixture()
def panel():
    poprzednia = serwer.DB
    serwer.DB = baza.polacz(":memory:")
    mod_profile.zaloz(serwer.DB, "adwokat", HASLO, "Anna", "Kowalska",
                      "prawnik", zgody=[z["id"] for z in mod_profile.ZGODY])

    usluga = ThreadingHTTPServer(("127.0.0.1", 0), serwer.Uchwyt)
    threading.Thread(target=usluga.serve_forever, daemon=True).start()
    adres = f"http://127.0.0.1:{usluga.server_address[1]}"
    yield adres
    usluga.shutdown()
    usluga.server_close()
    serwer.DB.close()
    serwer.DB = poprzednia


def _zaloguj(adres: str) -> str:
    cialo = json.dumps({"login": "adwokat", "haslo": HASLO}).encode()
    z = urllib.request.Request(adres + "/api/profil/logowanie", data=cialo,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(z, timeout=10) as odp:
        return (odp.headers.get("Set-Cookie") or "").split(";")[0]


def _sprawa(adres: str, ciastko: str, **pola):
    z = urllib.request.Request(
        adres + "/api/sprawy", data=json.dumps(pola).encode(),
        headers={"Content-Type": "application/json", "Cookie": ciastko})
    try:
        with urllib.request.urlopen(z, timeout=10) as odp:
            return odp.status, json.loads(odp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_pierwsza_sprawa_przechodzi(panel):
    ciastko = _zaloguj(panel)
    kod, d = _sprawa(panel, ciastko, sygnatura="II K 1/26", nazwa="Pierwsza")
    assert kod == 201 and d["id"]


def test_duplikat_zatrzymany_z_nazwa_istniejacej(panel):
    """Komunikat ma NAZWAĆ sprawę, która już istnieje.

    Sama informacja „duplikat" nie pomaga — prawnik musi wiedzieć,
    z czym koliduje, żeby rozstrzygnąć, czy to pomyłka.
    """
    ciastko = _zaloguj(panel)
    _sprawa(panel, ciastko, sygnatura="II K 2/26", nazwa="Sprawa Kowalskiego")

    kod, d = _sprawa(panel, ciastko, sygnatura="II K 2/26", nazwa="Inna nazwa")
    assert kod == 409, d
    assert d["duplikat"] is True
    assert "Sprawa Kowalskiego" in d["blad"], d["blad"]
    assert d["istniejaca"]["nazwa"] == "Sprawa Kowalskiego"


@pytest.mark.parametrize("wariant", [
    "ii k 3/26",          # inna wielkość liter
    "  II K 3/26  ",      # białe znaki na brzegach
])
def test_duplikat_wykrywany_mimo_zapisu(panel, wariant):
    """Pomyłka nie znika przez inną wielkość liter ani spację."""
    ciastko = _zaloguj(panel)
    _sprawa(panel, ciastko, sygnatura="II K 3/26", nazwa="Oryginalna")
    kod, d = _sprawa(panel, ciastko, sygnatura=wariant, nazwa="Druga")
    assert kod == 409, (kod, d)


def test_potwierdzenie_pozwala_zalozyc_duplikat(panel):
    """Świadoma decyzja prawnika ma przejść — to ostrzeżenie, nie zakaz."""
    ciastko = _zaloguj(panel)
    _sprawa(panel, ciastko, sygnatura="II K 4/26", nazwa="Pierwsza")

    kod, d = _sprawa(panel, ciastko, sygnatura="II K 4/26",
                     nazwa="Druga, świadomie", mimo_duplikatu=True)
    assert kod == 201, d

    z = urllib.request.Request(panel + "/api/sprawy",
                               headers={"Cookie": ciastko})
    with urllib.request.urlopen(z, timeout=10) as odp:
        sprawy = json.loads(odp.read())["sprawy"]
    assert sum(1 for s in sprawy if s["sygnatura"] == "II K 4/26") == 2


def test_rozne_sygnatury_nie_koliduja(panel):
    ciastko = _zaloguj(panel)
    assert _sprawa(panel, ciastko, sygnatura="II K 5/26", nazwa="A")[0] == 201
    assert _sprawa(panel, ciastko, sygnatura="II K 6/26", nazwa="B")[0] == 201
