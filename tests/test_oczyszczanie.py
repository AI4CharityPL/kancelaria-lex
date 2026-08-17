"""Oczyszczanie treści dokumentu ze znaczników.

TŁO — zmierzona przyczyna dominującej klasy błędów (14.08.2026):
    100% orzeczeń z SAOS niosło surowy HTML, 15,4% znaków to znaczniki,
    a filtr jakości odrzucał przez to 78% zdań polskiego korpusu.
    Model nie widział trzech czwartych akt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from oczyszczanie import oczysc, statystyka, zawiera_znaczniki  # noqa: E402


# ── przypadek, który to wykrył ──────────────────────────────────────

def test_zdanie_z_orzeczenia_saos():
    """DOKŁADNIE to zdanie przepadało — niesie datę i sygnaturę wyroku SN."""
    surowe = ("603 – 604 teza 3, także wyrok Sądu Najwyższego z dnia "
              "23 lipca 1974 r., sygn. akt V KR 212/74).</p>\n"
              "          </td>\n        </tr>\n        <tr>")
    czyste = oczysc(surowe)
    assert "<" not in czyste and ">" not in czyste
    assert "23 lipca 1974 r." in czyste
    assert "V KR 212/74" in czyste


# ── znaczniki ───────────────────────────────────────────────────────

@pytest.mark.parametrize("surowe,oczekiwany_fragment", [
    ("<p>Sąd orzekł.</p>", "Sąd orzekł."),
    ("<div class='x'>Treść</div>", "Treść"),
    ("Tekst<br/>dalej", "Tekst"),
    ("<b>Wyrok</b> sądu", "Wyrok"),
])
def test_usuwa_znaczniki(surowe, oczekiwany_fragment):
    czyste = oczysc(surowe)
    assert oczekiwany_fragment in czyste
    assert "<" not in czyste


def test_usuwa_tresc_skryptow():
    assert "alert" not in oczysc("<script>alert(1)</script>Wyrok")
    assert "Wyrok" in oczysc("<script>alert(1)</script>Wyrok")


def test_encje_sa_dekodowane():
    assert oczysc("s&oacute;d &amp; strona") == "sód & strona"
    assert " " not in oczysc("kwota&nbsp;1000 zł")


# ── granice: czego NIE wolno zepsuć ─────────────────────────────────

def test_nie_kasuje_nierownosci_matematycznej():
    """„kwota < 1000" nie jest znacznikiem — bywa w opinii biegłego."""
    assert "< 1000" in oczysc("ustalono, że kwota < 1000 zł")


def test_nie_kasuje_porownania_liter():
    assert oczysc("warunek a < b jest spełniony") == "warunek a < b jest spełniony"


def test_czysty_tekst_zostaje_nietkniety():
    """Najczęstszy przypadek — dokument bez znaczników nie może się zmienić."""
    tekst = "Sąd Rejonowy uznał oskarżonego za winnego. Rozprawa 14.09.2006 r."
    assert oczysc(tekst) == tekst


def test_pusty_tekst():
    assert oczysc("") == "" and oczysc(None or "") == ""


# ── struktura ───────────────────────────────────────────────────────

def test_zamkniecie_akapitu_daje_granice_zdania():
    """Bez tego treść dwóch komórek skleja się w jedno bezsensowne zdanie."""
    czyste = oczysc("<td>Pierwsza teza</td><td>Druga teza</td>")
    assert "Pierwsza teza" in czyste and "Druga teza" in czyste
    assert "Pierwsza tezaDruga" not in czyste
    assert "Pierwsza teza Druga teza" not in czyste.replace("\n", "@")


def test_spacja_przed_interpunkcja_znika():
    assert "orzekł." in oczysc("<b>orzekł</b>.")


def test_wielokrotne_puste_linie_sa_zwijane():
    assert "\n\n\n" not in oczysc("<p>A</p><p></p><p></p><p>B</p>")


# ── wykrywanie i statystyka ─────────────────────────────────────────

def test_wykrywanie_znacznikow():
    assert zawiera_znaczniki("<p>tekst</p>")
    assert not zawiera_znaczniki("zwykły tekst z 1 < 2")


def test_statystyka_mierzy_zysk():
    s = statystyka("<p>Sąd orzekł.</p><td></td>")
    assert s["mial_znaczniki"] and s["usuniete"] > 0 and s["po"] < s["przed"]
