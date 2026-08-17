"""Kontrola niezależna — czystość zapytania i obsługa awarii.

Testy dzielą się na dwie grupy:

  KONSTRUKCYJNE  — sprawdzają, że zapytanie NIE NIESIE kontekstu
                   i że awaria nie daje zgody. Działają bez modelu.
                   To one dają gwarancję.

  BEHAWIORALNE   — sprawdzają, czy kontroler faktycznie odróżnia
                   prawdę od fałszu. Wymagają Ollamy, uruchamiane
                   osobno: pytest -m behawioralny
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from kontrola import (  # noqa: E402
    SZABLON_EN, SZABLON_PL, Werdykt, sprawdz, zbuduj_zapytanie,
)


# ═══════════════════════════════════════════════════════════════════
#  CZYSTOŚĆ ZAPYTANIA — to jest właściwa gwarancja
# ═══════════════════════════════════════════════════════════════════

PYTANIE_PRAWNIKA = "Jakie zdarzenie akta tej sprawy wiążą z datą 14 września 2006 r.?"
INNY_DOKUMENT = "Opinia biegłego z zakresu mechanoskopii dotycząca zamka."
NAZWA_SPRAWY = "II K 147/26 Kowalski — wypadek drogowy"
HISTORIA = "Prawnik: a co ze świadkiem Nowak? Asystent: świadek zeznał..."


def test_zapytanie_nie_niesie_kontekstu():
    """SEDNO CAŁEJ KONSTRUKCJI — sprawdzane na ZAWARTOŚCI, nie na deklaracji.

    Kontroler ma widzieć dwa zdania i nic więcej. Gdyby zapytanie
    przechodziło przez `agent.zapytaj_model`, wciągnęłoby instrukcję
    systemową, historię rozmowy i cały materiał sprawy — i kontrola
    straciłaby jedyną własność, dla której istnieje.
    """
    z = zbuduj_zapytanie(
        "Rozprawa odbyła się 14 września 2006 r.",
        ["Rozprawa odbyła się 14 września 2006 r. przed sądem."])

    for czego_nie_ma in (PYTANIE_PRAWNIKA, INNY_DOKUMENT, NAZWA_SPRAWY, HISTORIA):
        assert czego_nie_ma not in z, f"zapytanie niesie kontekst: {czego_nie_ma[:40]}"


def test_zapytanie_zawiera_dokladnie_cytat_i_twierdzenie():
    twierdzenie = "Świadek widział pojazd marki Opel"
    cytat = "Zauważyłem stojący pojazd marki Opel koloru srebrnego."
    z = zbuduj_zapytanie(twierdzenie, [cytat])
    assert twierdzenie in z and cytat in z


def test_dwa_zdania_trafiaja_oba():
    z = zbuduj_zapytanie("A i B", ["Zdanie pierwsze.", "Zdanie drugie."])
    assert "Zdanie pierwsze." in z and "Zdanie drugie." in z


def test_zapytanie_angielskie_dla_angielskich_akt():
    z = zbuduj_zapytanie("The hearing was held", ["The hearing was held."],
                         jezyk="en")
    assert "SENTENCE FROM THE DOCUMENT" in z
    assert "ZDANIE Z DOKUMENTU" not in z


def test_szablony_nie_zawieraja_miejsca_na_pytanie():
    """Zabezpieczenie przed cichym dodaniem kontekstu przy przyszłej edycji."""
    for szablon in (SZABLON_PL, SZABLON_EN):
        assert "{pytanie}" not in szablon
        assert "{historia}" not in szablon
        assert "{sprawa}" not in szablon


# ═══════════════════════════════════════════════════════════════════
#  AWARIA NIE MOŻE OZNACZAĆ ZGODY
# ═══════════════════════════════════════════════════════════════════

def test_model_niedostepny_daje_niezweryfikowane():
    """Kontrola, która przy awarii cicho przepuszcza, jest gorsza od jej braku."""
    import urllib.error
    with patch("kontrola._wywolaj", side_effect=urllib.error.URLError("brak")):
        w = sprawdz("twierdzenie", ["cytat"])
    assert w.werdykt is Werdykt.NIEZWERYFIKOWANE
    assert w.werdykt is not Werdykt.PRAWDA
    assert not w.blad          # to nie jest błąd merytoryczny, tylko brak kontroli


def test_dowolny_wyjatek_nie_daje_zgody():
    with patch("kontrola._wywolaj", side_effect=ValueError("cokolwiek")):
        assert sprawdz("t", ["c"]).werdykt is Werdykt.NIEZWERYFIKOWANE


def test_nieoczekiwana_odpowiedz_nie_daje_zgody():
    """Schemat wymusza enum, ale nie zgadujemy na korzyść odpowiedzi."""
    with patch("kontrola._wywolaj", return_value={"odpowiedz": "MOŻE"}):
        assert sprawdz("t", ["c"]).werdykt is Werdykt.NIEZWERYFIKOWANE


def test_brak_cytatu_nie_wola_modelu():
    with patch("kontrola._wywolaj") as m:
        w = sprawdz("twierdzenie", [])
        assert not m.called
    assert w.werdykt is Werdykt.NIEZWERYFIKOWANE


# ── odczyt werdyktu ─────────────────────────────────────────────────

def test_tak_daje_prawde():
    with patch("kontrola._wywolaj",
               return_value={"odpowiedz": "TAK", "powod": "zgadza się"}):
        w = sprawdz("t", ["c"])
    assert w.werdykt is Werdykt.PRAWDA and not w.blad


def test_nie_daje_blad():
    """Decyzja użytkownika: przy odpowiedzi przeczącej ma wyskoczyć BŁĄD."""
    with patch("kontrola._wywolaj",
               return_value={"odpowiedz": "NIE", "powod": "zdanie mówi co innego"}):
        w = sprawdz("t", ["c"])
    assert w.werdykt is Werdykt.FALSZ
    assert w.blad
    assert "co innego" in w.powod


def test_nie_bez_uzasadnienia_dostaje_domyslne():
    with patch("kontrola._wywolaj", return_value={"odpowiedz": "NIE"}):
        assert sprawdz("t", ["c"]).powod


# ── dobór modelu ────────────────────────────────────────────────────

def test_model_dobierany_do_jezyka_cytatu():
    """Nie do języka instalacji — model polski parafrazuje angielski tekst."""
    with patch("kontrola._wywolaj", return_value={"odpowiedz": "TAK"}) as m:
        sprawdz("claim", ["The hearing was held."], jezyk="en")
        assert m.call_args[0][1] == "llama-lex-map"
        m.reset_mock()
        sprawdz("twierdzenie", ["Rozprawa się odbyła."], jezyk="pl")
        assert m.call_args[0][1] == "bielik-lex-map"


# ═══════════════════════════════════════════════════════════════════
#  BEHAWIORALNE — wymagają modelu
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.behawioralny
def test_odwrocona_negacja_daje_falsz():
    """Klasa, której kontrola mechaniczna z definicji nie łapie."""
    w = sprawdz("Sąd uwzględnił wniosek obrońcy",
                ["Sąd nie uwzględnił wniosku obrońcy o dopuszczenie dowodu."])
    assert w.werdykt is Werdykt.FALSZ, w.powod


@pytest.mark.behawioralny
def test_wierne_twierdzenie_daje_prawde():
    w = sprawdz("Świadek widział pojazd marki Opel",
                ["Zauważyłem stojący pojazd marki Opel koloru srebrnego."])
    assert w.werdykt is Werdykt.PRAWDA, w.powod
