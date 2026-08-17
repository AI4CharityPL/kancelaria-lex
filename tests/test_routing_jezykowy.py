"""Dobór modelu do języka akt — w torze szybkim.

TŁO — luka znaleziona 14.08.2026.
    Tor analizy (`analiza.py`) routował po języku od początku. Tor szybki
    (`agent.py`) miał `MODEL = "bielik-lex-map"` zaszyte na stałe, więc
    angielskie akta czytał model trenowany pod polski.

    Benchmark odpytuje właśnie tor szybki, więc wyniki EN były mierzone
    złym modelem — co tłumaczy część różnicy 37,5% (EN) do 75,0% (PL)
    w rozróżnialności par.

WYMÓG KANCELARII (postawiony wprost):
    szukanie w języku plików, odpowiedź po polsku.

    materiał        → w oryginale, nietknięty
    instrukcja      → w języku materiału, żeby model czytał go dobrze
    opis ustalenia  → PO POLSKU, bo to czyta prawnik
    cytat           → w oryginale, bo cytat z akt nie podlega tłumaczeniu
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import agent  # noqa: E402
import wyszukiwarka  # noqa: E402

PL = ("Sąd Rejonowy uznał oskarżonego za winnego zarzucanego mu czynu. "
      "Rozprawa odbyła się 14 września 2006 r. przed sądem okręgowym. "
      "Świadek zeznał, że nie potrafi podać numeru rejestracyjnego pojazdu.")

EN = ("The court found the defendant guilty of the charged offense. "
      "The hearing was held on October 6, 2016 before the district court. "
      "The witness stated that he could not provide the license plate number.")


def _wybor(tresc: str, pytanie: str):
    return wyszukiwarka.wybierz_zdania({"1": tresc}, pytanie, budzet_znakow=5000)


# ── dobór modelu ────────────────────────────────────────────────────

def test_polskie_akta_ida_do_bielika():
    model, _ = agent._model_i_instrukcja(_wybor(PL, "Kiedy odbyła się rozprawa?"))
    assert model == "bielik-lex-map"


def test_angielskie_akta_ida_do_llamy():
    """DOKŁADNIE ta ścieżka była zepsuta — szła do modelu polskiego."""
    model, _ = agent._model_i_instrukcja(_wybor(EN, "When was the hearing held?"))
    assert model == "llama-lex-map"


def test_polskie_akta_dostaja_szablon_polski():
    _, instrukcja = agent._model_i_instrukcja(_wybor(PL, "Kiedy rozprawa?"))
    assert instrukcja is agent.INSTRUKCJA


def test_angielskie_akta_dostaja_szablon_angielski():
    _, instrukcja = agent._model_i_instrukcja(_wybor(EN, "When was the hearing?"))
    assert instrukcja is agent.INSTRUKCJA_EN


# ── wymóg: odpowiedź po polsku mimo angielskich akt ─────────────────

def test_szablon_angielski_kaze_opisywac_po_polsku():
    """Prawnik czyta po polsku, nawet gdy akta są angielskie."""
    assert "IN POLISH" in agent.INSTRUKCJA_EN


def test_szablon_angielski_zakazuje_tlumaczenia_cytatu():
    """Cytat z akt nie podlega tłumaczeniu — straciłby wartość dowodową.

    W praktyce jest to niemożliwe także fizycznie: cytat odtwarza KOD
    z dokumentu źródłowego (ADR-0007). Instrukcja mówi o tym wprost,
    żeby model nie próbował.
    """
    assert "Do not translate the quotation" in agent.INSTRUKCJA_EN


# ── rozpoznanie języka materiału ────────────────────────────────────

def test_jezyk_rozpoznawany_z_WYBRANYCH_zdan():
    """Nie z metadanych sprawy — sprawa bywa mieszana językowo.

    Liczy się to, co model faktycznie zobaczy.
    """
    assert agent._jezyk_materialu(_wybor(PL, "rozprawa")) == "pl"
    assert agent._jezyk_materialu(_wybor(EN, "hearing")) == "en"


def test_pusty_wybor_daje_polski():
    """Instalacja jest polska — zapasowo polski."""
    assert agent._jezyk_materialu(None) == "pl"


def test_model_zapasowy_dla_nierozpoznanego():
    """Materiał bez rozpoznawalnego języka nie może wywrócić wywołania."""
    wybor = _wybor("XYZ 123 ABC-999 QQQ WWW", "cokolwiek")
    model, _ = agent._model_i_instrukcja(wybor)
    assert model in ("bielik-lex-map", "llama-lex-map")


# ── spójność z torem analizy ────────────────────────────────────────

def test_oba_tory_uzywaja_tej_samej_mapy_modeli():
    """Rozjazd między torami oznaczałby inny model dla tego samego pliku."""
    import jezyk as mod_jezyk
    assert mod_jezyk.model_dla("pl") == "bielik-lex-map"
    assert mod_jezyk.model_dla("en") == "llama-lex-map"

    model_szybki, _ = agent._model_i_instrukcja(_wybor(EN, "hearing"))
    assert model_szybki == mod_jezyk.model_dla("en")
