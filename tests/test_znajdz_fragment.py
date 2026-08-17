"""Szukanie cytatu tolerancyjne na białe znaki.

TŁO — realny pomiar, nie hipoteza.
    Na aktach wyciągniętych z PDF-ów 133 ze 147 twierdzeń przepadło
    z powodem „zakres 0-0" — fragment nienaleziony w źródle. Nie dlatego,
    że model zmyślał, tylko dlatego, że tekst z PDF ma łamania wierszy
    w środku zdań, a offsety wyznaczało zwykłe `find()`.

    Weryfikator miał tolerancję na białe znaki, ale nigdy nie dostawał
    szansy jej użyć — odsiew następował o krok wcześniej.

Te testy pilnują, żeby tolerancja została, a jednocześnie żeby NIE
rozciągnęła się na różnice, które zmieniają treść.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "aplikacje"))

from agenci.weryfikator_cytatow import znajdz_fragment  # noqa: E402


# ── tolerancja ──────────────────────────────────────────────────────

def test_dokladne_trafienie():
    z = "Świadek zeznał, że widział pojazd marki Opel."
    frag = "widział pojazd marki Opel"
    w = znajdz_fragment(z, frag)
    assert w == (z.index(frag), z.index(frag) + len(frag))
    assert z[w[0]:w[1]] == frag


def test_lamanie_wiersza_w_srodku_zdania():
    """Typowy artefakt konwersji PDF."""
    z = "Attorney for Defendant: Paul Cambria, \nRetained \nDefendant: Present"
    w = znajdz_fragment(z, "Paul Cambria, Retained Defendant: Present")
    assert w is not None
    assert z[w[0]:w[1]] == "Paul Cambria, \nRetained \nDefendant: Present"


def test_podwojne_spacje():
    z = "Sąd  oddalił   wniosek obrońcy."
    w = znajdz_fragment(z, "Sąd oddalił wniosek")
    assert w is not None and z[w[0]:w[1]] == "Sąd  oddalił   wniosek"


def test_roznica_wielkosci_liter():
    z = "POSTANOWIENIE Sądu Rejonowego"
    assert znajdz_fragment(z, "postanowienie sądu") is not None


def test_warianty_cudzyslowu_i_myslnika():
    z = 'Świadek powiedział „nie wiem” — tak zeznał.'
    assert znajdz_fragment(z, '"nie wiem" - tak zeznał') is not None


def test_zakres_wskazuje_oryginal_nie_kopie():
    """Cytat ma prowadzić do miejsca w dokumencie, nie w przetworzonej kopii."""
    z = "aaa\n\nSąd   oddalił\nwniosek. bbb"
    w = znajdz_fragment(z, "Sąd oddalił wniosek.")
    assert w is not None
    assert z[w[0]:w[1]].startswith("Sąd")
    assert z[w[0]:w[1]].endswith("wniosek.")


# ── granice tolerancji — czego NIE wolno przepuścić ─────────────────

def test_nie_przepuszcza_zmienionej_liczby():
    """„14 dni" i „4 dni" to nie wariant zapisu."""
    z = "Termin wynosi 14 dni od doręczenia."
    assert znajdz_fragment(z, "Termin wynosi 4 dni") is None


def test_nie_przepuszcza_usunietej_negacji():
    """Najgroźniejszy wariant halucynacji."""
    z = "Świadek nie potrafił podać numeru."
    assert znajdz_fragment(z, "Świadek potrafił podać numeru") is None


def test_nie_przepuszcza_zmyslonego_fragmentu():
    z = "Świadek widział pojazd marki Opel."
    assert znajdz_fragment(z, "świadek rozpoznał kierowcę") is None


def test_nie_przepuszcza_parafrazy():
    z = "Oskarżony przyznał się do zarzucanego mu czynu."
    assert znajdz_fragment(z, "Oskarżony przyznał winę") is None


# ── przypadki brzegowe ──────────────────────────────────────────────

@pytest.mark.parametrize("fragment", ["", "   ", "\n\n"])
def test_pusty_fragment(fragment):
    assert znajdz_fragment("dowolna treść", fragment) is None


def test_puste_zrodlo():
    assert znajdz_fragment("", "cokolwiek") is None


def test_fragment_dluzszy_niz_zrodlo():
    assert znajdz_fragment("krótkie", "dużo dłuższy tekst niż źródło") is None


def test_znaki_ukladu_strony_z_pdf():
    """Kratki wyboru i podobne znaki z formularzy PDF."""
    z = "Defendant: ☒ Present ☐ Not Present"
    w = znajdz_fragment(z, "Defendant: ☒ Present")
    assert w is not None
