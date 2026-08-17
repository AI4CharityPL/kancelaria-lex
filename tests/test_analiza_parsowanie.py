"""Odporność parsowania odpowiedzi modelu.

TŁO — realny błąd, nie hipoteza.
    Szablon prosił o klucz "watki". Bielik zwrócił "wątki", z ogonkiem.
    Sztywny odczyt dał pustą listę, pipeline poszedł dalej, zameldował
    postęp i zwrócił analizę bez ani jednego ustalenia — bez żadnego
    błędu. Cicha awaria z pozorem poprawnego działania.

    Kwantyzowany model lokalny nie trzyma schematu tak ściśle jak duży.
    Parsowanie musi być liberalne, a te testy pilnują, żeby tolerancja
    nie zniknęła przy kolejnej zmianie.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from analiza import _json_lub_pusty, _lista, _pole  # noqa: E402


# ── normalizacja kluczy ─────────────────────────────────────────────

def test_klucz_z_ogonkami_jest_rozpoznawany():
    """DOKŁADNIE ten błąd wystąpił w praktyce."""
    dane = _json_lub_pusty(json.dumps({"wątki": ["a", "b"]}, ensure_ascii=False))
    assert _lista(dane, "watki") == ["a", "b"]


def test_klucz_z_wielkiej_litery():
    dane = _json_lub_pusty('{"Ustalenia": [{"tekst": "x"}]}')
    assert len(_lista(dane, "ustalenia")) == 1


def test_klucz_ze_spacja_i_myslnikiem():
    dane = _json_lub_pusty('{"podstawa prawna": [1], "oparte-na": [2]}')
    assert _lista(dane, "podstawa_prawna") == [1]


def test_niepoprawny_json_nie_wywala_analizy():
    assert _json_lub_pusty("to nie jest JSON") == {}
    assert _json_lub_pusty("") == {}


def test_lista_zamiast_obiektu():
    """Model bywa zwraca gołą listę zamiast obiektu."""
    assert _json_lub_pusty('[1,2,3]') == {}


# ── wybór spośród wielu nazw ────────────────────────────────────────

def test_pierwsza_pasujaca_nazwa_wygrywa():
    dane = _json_lub_pusty('{"fakty": ["a"]}')
    assert _lista(dane, "ustalenia", "fakty") == ["a"]


def test_brak_wszystkich_nazw_daje_pusta_liste():
    dane = _json_lub_pusty('{"cos_innego": ["a"]}')
    assert _lista(dane, "ustalenia", "fakty") == []


def test_wartosc_nie_bedaca_lista_jest_pomijana():
    dane = _json_lub_pusty('{"ustalenia": "tekst zamiast listy"}')
    assert _lista(dane, "ustalenia") == []


# ── pola wewnątrz pozycji ───────────────────────────────────────────

@pytest.mark.parametrize("pozycja,oczekiwany", [
    ({"fragment": "abc"}, "abc"),
    ({"cytat": "abc"}, "abc"),
    ({"cytat_doslowny": "abc"}, "abc"),
    ({"Fragment": "abc"}, "abc"),
    ({"cytat dosłowny": "abc"}, "abc"),
])
def test_warianty_nazwy_pola_cytatu(pozycja, oczekiwany):
    assert _pole(pozycja, "fragment", "cytat", "cytat_doslowny") == oczekiwany


def test_puste_pole_traktowane_jak_brak():
    assert _pole({"tekst": ""}, "tekst", "opis") == ""


def test_pole_liczbowe_zamieniane_na_tekst():
    assert _pole({"tekst": 42}, "tekst") == "42"


def test_brak_pola_daje_pusty_ciag():
    assert _pole({"inne": "x"}, "tekst") == ""
