"""Głosowanie większościowe nad wskazaniami zdań.

Sprawdza przede wszystkim to, co głosowanie ma naprawiać: wskazanie
przypadkowe, pojawiające się w jednym losowaniu, nie może przejść —
a wskazanie powtarzalne musi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from glosowanie import (  # noqa: E402
    policz, prog_wiekszosciowy, przefiltruj_twierdzenia,
)


# ── próg ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("probek,oczekiwany", [(1, 1), (2, 1), (3, 2), (5, 3), (7, 4)])
def test_prog_wiekszosciowy(probek, oczekiwany):
    assert prog_wiekszosciowy(probek) == oczekiwany


# ── zliczanie ───────────────────────────────────────────────────────

def test_zgodne_wskazanie_przechodzi():
    w = policz([[3, 7], [3, 7], [3, 7]])
    assert w.numery == {3, 7}
    assert w.poparcie(3) == 1.0


def test_wskazanie_przypadkowe_odpada():
    """Numer wskazany raz na trzy losowania nie przechodzi większości."""
    w = policz([[3], [3], [3, 99]])
    assert 3 in w.numery
    assert 99 not in w.numery
    assert w.poparcie(99) == pytest.approx(1 / 3)


def test_powtorzenie_w_jednym_losowaniu_to_jeden_glos():
    """Model wskazujący to samo zdanie dwa razy nie ma dwóch głosów."""
    w = policz([[5, 5, 5], [9], [9]])
    assert w.glosy[5] == 1
    assert 5 not in w.numery and 9 in w.numery


def test_prog_niski_podnosi_czulosc():
    """Próg 1 przepuszcza wszystko — świadomy wybór czułości nad precyzją."""
    w = policz([[1], [2], [3]], prog=1)
    assert w.numery == {1, 2, 3}


def test_brak_losowan():
    w = policz([])
    assert w.numery == frozenset() and w.probek == 0


def test_puste_losowania_to_odmowa():
    """Trzy razy pusta odpowiedź = zgodna odmowa, nie brak danych."""
    w = policz([[], [], []])
    assert w.numery == frozenset() and w.probek == 3


# ── filtrowanie twierdzeń ───────────────────────────────────────────

def test_twierdzenie_z_popartym_zdaniem_zostaje():
    w = policz([[3], [3], [3]])
    poparte, odrzucone = przefiltruj_twierdzenia(
        [{"tekst": "A", "zdania": [3]}], w)
    assert len(poparte) == 1 and not odrzucone
    assert poparte[0]["poparcie"] == 1.0


def test_twierdzenie_bez_poparcia_odpada_z_powodem():
    w = policz([[3], [3], [3, 99]])
    poparte, odrzucone = przefiltruj_twierdzenia(
        [{"tekst": "zmyślone", "zdania": [99]}], w)
    assert not poparte and len(odrzucone) == 1
    assert "1 z 3" in odrzucone[0]["powod_glosowania"]


def test_wystarczy_jedno_poparte_zdanie_z_dwoch():
    """Twierdzenie z dwóch zdań nie może przepadać przez słabsze z nich.

    Wymaganie poparcia dla wszystkich karałoby twierdzenia obejmujące
    dwa zdania — a to one niosą najwięcej treści.
    """
    w = policz([[3], [3], [3, 8]])
    poparte, _ = przefiltruj_twierdzenia(
        [{"tekst": "A", "zdania": [3, 8]}], w)
    assert len(poparte) == 1


def test_twierdzenie_bez_zdan():
    w = policz([[1], [1]])
    poparte, odrzucone = przefiltruj_twierdzenia([{"tekst": "A", "zdania": []}], w)
    assert not poparte and "brak wskazanych zdań" in odrzucone[0]["powod_glosowania"]


def test_smieciowe_numery_sa_pomijane():
    w = policz([[1], [1]])
    poparte, odrzucone = przefiltruj_twierdzenia(
        [{"tekst": "A", "zdania": ["abc", None]}], w)
    assert not poparte and len(odrzucone) == 1


def test_pojedyncze_losowanie_zachowuje_sie_jak_brak_glosowania():
    """Przy jednej próbce próg wynosi 1 — nic nie odpada."""
    w = policz([[4, 9]])
    poparte, odrzucone = przefiltruj_twierdzenia(
        [{"tekst": "A", "zdania": [4]}, {"tekst": "B", "zdania": [9]}], w)
    assert len(poparte) == 2 and not odrzucone
