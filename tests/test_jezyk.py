"""Rozpoznanie języka dokumentu — sprawdzane na REALNYCH aktach.

Pomyłka tutaj jest kosztowna: pomiar z 14.08.2026 pokazał, że model
polski na angielskich aktach parafrazuje zamiast cytować dosłownie,
przez co weryfikator odrzucił 62 z 68 twierdzeń (trafność 9% zamiast 82%).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

from jezyk import (  # noqa: E402
    MODEL_ZAPASOWY, model_dla, pogrupuj_wg_jezyka, rozpoznaj,
)

PL_ORZECZENIE = """
Sąd Rejonowy w Nowym Mieście, II Wydział Karny, po rozpoznaniu sprawy
oskarżonego o czyn z art. 178a § 1 k.k., uznaje oskarżonego za winnego
i wymierza mu karę grzywny. Sąd wziął pod uwagę okoliczności łagodzące,
w tym uprzednią niekaralność oraz przyznanie się do winy.
"""

PL_BEZ_OGONKOW = """
Sad Rejonowy po rozpoznaniu sprawy oskarzonego uznaje go za winnego
i wymierza kare grzywny. Sad wzial pod uwage okolicznosci lagodzace,
w tym uprzednia niekaralnosc oraz przyznanie sie do winy oskarzonego.
"""

EN_ORZECZENIE = """
The defendant's motion to dismiss the indictment is denied. The court has
considered the arguments of counsel and the record in this case, and finds
that the government has established probable cause. It is hereby ordered
that the motion filed by the defendant is denied without prejudice.
"""


# ── rozpoznanie ─────────────────────────────────────────────────────

def test_polskie_orzeczenie():
    w = rozpoznaj(PL_ORZECZENIE)
    assert w.jezyk == "pl" and w.pewne, w.powod


def test_angielskie_orzeczenie():
    w = rozpoznaj(EN_ORZECZENIE)
    assert w.jezyk == "en" and w.pewne, w.powod


def test_polski_bez_znakow_diakrytycznych():
    """Skany po OCR często gubią ogonki — nie może to przełączyć języka."""
    w = rozpoznaj(PL_BEZ_OGONKOW)
    assert w.jezyk == "pl", f"{w.jezyk} ({w.powod})"


def test_pusty_dokument():
    assert rozpoznaj("").jezyk == "nieznany"
    assert rozpoznaj("   \n  ").jezyk == "nieznany"


def test_za_krotki_dokument():
    """Trzy słowa nie wystarczą do rozstrzygnięcia."""
    w = rozpoznaj("Sąd oddala wniosek")
    assert w.jezyk == "nieznany"
    assert "za mało" in w.powod


def test_sam_szum_bez_slow_funkcyjnych():
    w = rozpoznaj("XYZ 12345 ABC-999 QQQ WWW ZZZ RRR TTT YYY UUU III OOO")
    assert w.jezyk == "nieznany"


def test_dokument_prawie_wylacznie_liczbowy():
    w = rozpoznaj("1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11. 12. 13. 14. 15.")
    assert w.jezyk == "nieznany"


# ── dobór modelu ────────────────────────────────────────────────────

def test_model_dla_polskiego():
    assert model_dla("pl") == "bielik-lex-map"


def test_model_dla_angielskiego():
    assert model_dla("en") == "llama-lex-map"


def test_model_dla_nieznanego_jezyka():
    """Instalacja jest polska — zapasowo Bielik."""
    assert model_dla("nieznany") == MODEL_ZAPASOWY
    assert model_dla("de") == MODEL_ZAPASOWY


# ── grupowanie ──────────────────────────────────────────────────────

def test_grupowanie_ogranicza_zamiany_modelu():
    """Przy 8 GB VRAM mieści się jeden model — grupowanie to oszczędność
    kilkunastu przeładowań."""
    grupy = pogrupuj_wg_jezyka({
        "1": PL_ORZECZENIE, "2": EN_ORZECZENIE,
        "3": PL_ORZECZENIE, "4": EN_ORZECZENIE, "5": PL_ORZECZENIE,
    })
    assert sorted(grupy) == ["en", "pl"]
    assert sorted(grupy["pl"]) == ["1", "3", "5"]
    assert sorted(grupy["en"]) == ["2", "4"]


def test_nieznany_trafia_do_polskiego():
    grupy = pogrupuj_wg_jezyka({"1": "krótko"})
    assert grupy == {"pl": ["1"]}


def test_grupowanie_respektuje_zapisany_jezyk():
    """Język zapisany przy wgraniu ma pierwszeństwo — nie liczymy dwa razy."""
    grupy = pogrupuj_wg_jezyka({"1": EN_ORZECZENIE}, jezyki={"1": "pl"})
    assert grupy == {"pl": ["1"]}


# ── na realnych aktach ──────────────────────────────────────────────

@pytest.mark.parametrize("katalog,oczekiwany", [
    ("eval/korpus-syntetyczny", "pl"),
    ("eval/korpus-rzeczywisty", "pl"),
    ("eval/sprawa-lacey/txt", "en"),
])
def test_na_realnych_aktach(katalog, oczekiwany):
    """Sprawdzenie na faktycznie pobranych aktach, nie na próbkach."""
    sciezka = KORZEN / katalog
    pliki = sorted(sciezka.glob("*.txt"))[:40] if sciezka.exists() else []
    if not pliki:
        pytest.skip(f"brak korpusu {katalog}")

    wyniki = [rozpoznaj(p.read_text(encoding="utf-8", errors="ignore")) for p in pliki]
    trafione = sum(1 for w in wyniki if w.jezyk == oczekiwany)
    udzial = trafione / len(wyniki)

    assert udzial >= 0.95, (
        f"{katalog}: rozpoznano {trafione}/{len(wyniki)} jako {oczekiwany}. "
        f"Przykłady pomyłek: "
        f"{[(p.name, w.jezyk, w.powod[:50]) for p, w in zip(pliki, wyniki) if w.jezyk != oczekiwany][:3]}"
    )
