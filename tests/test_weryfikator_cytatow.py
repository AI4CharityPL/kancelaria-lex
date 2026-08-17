"""Testy weryfikatora cytatów — bramka J-1 (kamień milowy M3).

Najważniejszy test w tym pliku: test_wykrywa_zmyslony_cytat.
Jeśli on przechodzi, halucynacja nie dotrze do prawnika.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "aplikacje"))

from agenci.weryfikator_cytatow import (  # noqa: E402
    Cytat, Twierdzenie, WeryfikatorCytatow, Werdykt,
    normalizuj, trafnosc_cytatow,
)


PROTOKOL = (
    "Protokół przesłuchania świadka z dnia 12 sierpnia 2026 r. "          # 0-63
    "Świadek zeznał, że w dniu zdarzenia widział pojazd marki Opel "      # 63-125
    "koloru srebrnego. Świadek nie potrafił podać numeru rejestracyjnego."
)

POSTANOWIENIE = (
    "Odpis postanowienia z uzasadnieniem doręczono obrońcy "
    "w dniu 12 sierpnia 2026 r."
)

DOKUMENTY = {"dok-1": PROTOKOL, "dok-2": POSTANOWIENIE}


@pytest.fixture
def weryfikator():
    return WeryfikatorCytatow(DOKUMENTY)


def _cytat_z(dokument_id: str, fragment: str) -> Cytat:
    """Buduje poprawny cytat, znajdując fragment w dokumencie."""
    zrodlo = DOKUMENTY[dokument_id]
    poczatek = zrodlo.index(fragment)
    return Cytat(dokument_id, poczatek, poczatek + len(fragment), fragment)


# ── ścieżka pozytywna ───────────────────────────────────────────────

def test_poprawny_cytat_przechodzi(weryfikator):
    cytat = _cytat_z("dok-1", "widział pojazd marki Opel")
    ok, werdykt, _ = weryfikator.sprawdz_cytat(cytat)
    assert ok and werdykt is Werdykt.POTWIERDZONY


def test_twierdzenie_z_poprawnym_cytatem_przechodzi(weryfikator):
    t = Twierdzenie(
        "Świadek widział pojazd marki Opel.",
        [_cytat_z("dok-1", "widział pojazd marki Opel")],
    )
    assert weryfikator.sprawdz_twierdzenie(t).przeszlo


# ── ścieżka krytyczna: wykrywanie halucynacji ───────────────────────

def test_wykrywa_zmyslony_cytat(weryfikator):
    """KLUCZOWY TEST — kamień milowy M3.

    Model twierdzi, że świadek rozpoznał kierowcę. W protokole nie ma
    takiego fragmentu. Zakres wskazuje na istniejący tekst, ale treść
    się nie zgadza — dokładnie tak wygląda halucynacja z cytatem.
    """
    zmyslony = Cytat("dok-1", 63, 125, "świadek rozpoznał kierowcę pojazdu")
    twierdzenie = Twierdzenie("Świadek rozpoznał kierowcę.", [zmyslony])

    wynik = weryfikator.sprawdz_twierdzenie(twierdzenie)

    assert not wynik.przeszlo
    assert wynik.werdykt is Werdykt.ODRZUCONY_TRESC_NIEZGODNA
    assert "rozpoznał kierowcę" in wynik.szczegol


def test_wykrywa_twierdzenie_bez_cytatu(weryfikator):
    """Twierdzenie bez cytatu nie ma pokrycia — odrzucone."""
    wynik = weryfikator.sprawdz_twierdzenie(
        Twierdzenie("Oskarżony był na miejscu zdarzenia.", [])
    )
    assert not wynik.przeszlo
    assert wynik.werdykt is Werdykt.ODRZUCONY_BRAK_CYTATU


def test_wykrywa_nieistniejacy_dokument(weryfikator):
    """Zasięg zawężony do uprawnień użytkownika (docs/07-agenci.md)."""
    obcy = Cytat("dok-999", 0, 10, "cokolwiek")
    wynik = weryfikator.sprawdz_twierdzenie(Twierdzenie("X", [obcy]))
    assert wynik.werdykt is Werdykt.ODRZUCONY_BRAK_DOKUMENTU


@pytest.mark.parametrize("poczatek,koniec", [
    (-1, 10), (0, 0), (10, 5), (0, 100_000), (len(PROTOKOL), len(PROTOKOL) + 5),
])
def test_wykrywa_zakres_poza_tekstem(weryfikator, poczatek, koniec):
    wynik = weryfikator.sprawdz_twierdzenie(
        Twierdzenie("X", [Cytat("dok-1", poczatek, koniec, "cokolwiek")])
    )
    assert wynik.werdykt is Werdykt.ODRZUCONY_ZAKRES_POZA_TEKSTEM


def test_jeden_wadliwy_cytat_przekresla_twierdzenie(weryfikator):
    """Zachowawczo: lepiej odrzucić prawdziwe niż przepuścić zmyślone."""
    t = Twierdzenie("X", [
        _cytat_z("dok-1", "widział pojazd marki Opel"),
        Cytat("dok-1", 0, 20, "treść całkowicie inna"),
    ])
    assert not weryfikator.sprawdz_twierdzenie(t).przeszlo


# ── normalizacja: co wolno, a czego nie ─────────────────────────────

def test_normalizacja_dopuszcza_roznice_zapisu(weryfikator):
    """Białe znaki, cudzysłowy i myślniki nie zmieniają treści."""
    fragment = "widział pojazd marki Opel"
    poczatek = PROTOKOL.index(fragment)
    rozstrzelony = Cytat("dok-1", poczatek, poczatek + len(fragment),
                         "widział  pojazd\n  marki   Opel")
    ok, _, _ = weryfikator.sprawdz_cytat(rozstrzelony)
    assert ok


def test_normalizacja_nie_dopuszcza_zmiany_liczb():
    """W piśmie procesowym '14 dni' i '4 dni' to nie wariant zapisu."""
    assert normalizuj("termin 14 dni") != normalizuj("termin 4 dni")


def test_normalizacja_nie_dopuszcza_negacji():
    """Najgroźniejszy wariant halucynacji — dodane lub usunięte 'nie'."""
    assert normalizuj("świadek nie potrafił podać") != normalizuj("świadek potrafił podać")


def test_wykrywa_usuniecie_negacji(weryfikator):
    """Model gubi 'nie' — zmiana o jedno słowo, przeciwne znaczenie."""
    fragment = "Świadek nie potrafił podać numeru rejestracyjnego."
    poczatek = PROTOKOL.index(fragment)
    przekrecony = Cytat("dok-1", poczatek, poczatek + len(fragment),
                        "Świadek potrafił podać numeru rejestracyjnego.")
    ok, werdykt, _ = weryfikator.sprawdz_cytat(przekrecony)
    assert not ok and werdykt is Werdykt.ODRZUCONY_TRESC_NIEZGODNA


# ── odpowiedź jako całość i metryka ─────────────────────────────────

def test_odpowiedz_mieszana_przepuszcza_tylko_potwierdzone(weryfikator):
    twierdzenia = [
        Twierdzenie("Świadek widział Opla.",
                    [_cytat_z("dok-1", "widział pojazd marki Opel")]),
        Twierdzenie("Świadek rozpoznał kierowcę.",
                    [Cytat("dok-1", 63, 125, "świadek rozpoznał kierowcę")]),
        Twierdzenie("Oskarżony przyznał się.", []),
    ]
    potwierdzone, wyniki = weryfikator.sprawdz_odpowiedz(twierdzenia)

    assert len(potwierdzone) == 1
    assert potwierdzone[0].tekst == "Świadek widział Opla."
    assert trafnosc_cytatow(wyniki) == pytest.approx(1 / 3)


def test_metryka_j1_pusta_odpowiedz():
    """Odmowa odpowiedzi nie psuje metryki — odmowa jest poprawna."""
    assert trafnosc_cytatow([]) == 1.0
