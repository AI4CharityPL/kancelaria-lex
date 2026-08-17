"""Dławienie prób logowania — seria zgadywania hasła.

PO CO

`hashlib.scrypt` sprawia, że atak słownikowy na SKRADZIONEJ BAZIE
kosztuje sprzęt. Nie robi nic przeciwko zgadywaniu hasła PRZEZ PANEL:
tam każda próba to jedno żądanie HTTP, a żądań można wysłać dowolnie
wiele. Przy systemie trzymającym akta spraw karnych brak dławienia jest
luką, nie niuansem.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402

HASLO = "Praworzadnosc2026!"
ZGODY = [z["id"] for z in mod_profile.ZGODY]


@pytest.fixture
def db():
    # Baza w pamięci, jak w `test_profile.py` — bez pliku i bez zależności
    # od katalogu tymczasowego, który przy równoległych przebiegach
    # potrafi być zajęty.
    polaczenie = baza.polacz(":memory:")
    mod_profile.zaloz(polaczenie, "adwokat", HASLO, "Anna", "Kowalska",
                      "prawnik", zgody=ZGODY)
    yield polaczenie
    polaczenie.close()


def test_poprawne_haslo_wpuszcza(db):
    assert mod_profile.uwierzytelnij(db, "adwokat", HASLO) is not None


def test_seria_bledow_konczy_sie_blokada(db):
    for _ in range(mod_profile.PROB_PRZED_BLOKADA):
        assert mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo") is None

    with pytest.raises(mod_profile.BlokadaLogowania) as info:
        mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo")
    assert info.value.sekundy > 0


def test_blokada_dziala_takze_na_POPRAWNE_haslo(db):
    """⚠️ Inaczej dławienie nie dławi niczego.

    Gdyby poprawne hasło przechodziło mimo blokady, napastnik zgadujący
    hasło dostawałby dostęp dokładnie w tej próbie, w której trafi —
    a blokada opóźniałaby wyłącznie próby nietrafione.
    """
    for _ in range(mod_profile.PROB_PRZED_BLOKADA):
        mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo")

    with pytest.raises(mod_profile.BlokadaLogowania):
        mod_profile.uwierzytelnij(db, "adwokat", HASLO)


def test_nieistniejacy_login_tez_jest_dlawiony(db):
    """⚠️ WARUNEK NIEUJAWNIANIA ISTNIENIA KONT.

    Gdyby blokował się wyłącznie login istniejący, tabela prób stałaby
    się wyrocznią: „blokuje się, więc konto istnieje". `uwierzytelnij`
    liczy skrót nawet przy braku profilu właśnie po to, żeby tego nie
    zdradzić — dławienie musi trzymać ten sam standard.
    """
    for _ in range(mod_profile.PROB_PRZED_BLOKADA):
        assert mod_profile.uwierzytelnij(db, "nie-ma-takiego", "cokolwiek") is None

    with pytest.raises(mod_profile.BlokadaLogowania):
        mod_profile.uwierzytelnij(db, "nie-ma-takiego", "cokolwiek")


def test_udane_logowanie_zeruje_licznik(db):
    for _ in range(mod_profile.PROB_PRZED_BLOKADA - 1):
        mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo")

    assert mod_profile.uwierzytelnij(db, "adwokat", HASLO) is not None

    # Po wyzerowaniu znowu mamy pełną pulę prób — pomyłka sprzed
    # udanego logowania nie może dokładać się do następnej serii.
    for _ in range(mod_profile.PROB_PRZED_BLOKADA - 1):
        assert mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo") is None


def test_licznik_wygasa_po_oknie(db, monkeypatch):
    """Pięć pomyłek rozłożonych na pół roku nie może sumować się do blokady."""
    for _ in range(mod_profile.PROB_PRZED_BLOKADA - 1):
        mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo")

    prawdziwe_teraz = mod_profile._teraz
    pozniej = prawdziwe_teraz() + mod_profile.OKNO_ZLICZANIA + timedelta(minutes=1)
    monkeypatch.setattr(mod_profile, "_teraz", lambda: pozniej)

    # Licznik zaczyna od zera, więc kolejne cztery próby nie blokują.
    for _ in range(mod_profile.PROB_PRZED_BLOKADA - 1):
        assert mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo") is None


def test_blokada_nie_jest_trwala(db, monkeypatch):
    """Trwałe zamknięcie konta byłoby narzędziem ataku na dostępność.

    Wystarczyłoby wpisać cudzy login z błędnym hasłem, żeby odciąć
    prawnika od akt w dniu rozprawy.
    """
    for _ in range(mod_profile.PROB_PRZED_BLOKADA):
        mod_profile.uwierzytelnij(db, "adwokat", "zle-haslo")
    with pytest.raises(mod_profile.BlokadaLogowania):
        mod_profile.uwierzytelnij(db, "adwokat", HASLO)

    pozniej = mod_profile._teraz() + timedelta(seconds=mod_profile.BLOKADA_MAKS_S + 60)
    monkeypatch.setattr(mod_profile, "_teraz", lambda: pozniej)

    assert mod_profile.uwierzytelnij(db, "adwokat", HASLO) is not None
