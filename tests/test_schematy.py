"""Schematy JSON wymuszające cytat — rdzeń gwarancji ADR-0007.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TEN PLIK POWSTAŁ PÓŹNO I DLACZEGO JEST WAŻNY
════════════════════════════════════════════════════════════════════════

`panel/schematy.py` nie miał do 16.08.2026 **ani jednego testu**, mimo
że buduje gramatykę, na której opiera się główna obietnica produktu:
numer zdania spoza pokazanego zakresu ma być NIEWYRAŻALNY, a nie tylko
odrzucany po fakcie.

Cała reszta łańcucha — weryfikator cytatów, wsparcie, kontrola — jest
warstwą DRUGĄ. Jeśli enum w schemacie zbuduje się źle, model dostanie
możliwość wskazania zdania, którego nie widział, i pierwsza warstwa
przestanie istnieć w ciszy.

⚠️ GRANICA ZAPISANA W MODULE, KTÓREJ TE TESTY PILNUJĄ
   Dokumentacja Ollamy mówi wprost: `enum` gwarantuje, że wartość jest
   DOPUSZCZALNA, nie że jest WŁAŚCIWA. Sprawdzone doświadczalnie
   14.08.2026: przy `enum: [7]` i dokumencie o pięciu zdaniach model
   zwrócił `[7, 7]`, bo tylko to było dozwolone. Stąd zasada: enum musi
   pochodzić z numerów FAKTYCZNIE pokazanych zdań. Schemat rozminięty
   z wsadem zamienia się z zabezpieczenia w wymuszacz błędu — i tego
   pilnuje `test_enum_odwzorowuje_podane_numery`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

import schematy  # noqa: E402


def _zdania(schemat: dict, klucz: str) -> dict:
    return schemat["properties"][klucz]["items"]["properties"]["zdania"]


# ── mapowanie: cytat przez numer zdania ─────────────────────────────

def test_enum_odwzorowuje_podane_numery():
    """Zasada naczelna: enum pochodzi z numerów POKAZANYCH zdań."""
    numery = [3, 7, 11, 42]
    schemat = schematy.mapowanie(numery)
    assert _zdania(schemat, "ustalenia")["items"]["enum"] == numery


def test_numer_spoza_zakresu_jest_niewyrazalny():
    """Sedno ADR-0007 wyrażone jako asercja.

    Gramatyka dopuszcza wyłącznie numery z enum — nie ma w schemacie
    żadnej furtki (`anyOf`, `type: integer` bez ograniczenia), przez
    którą przeszedłby numer spoza zakresu.
    """
    schemat = schematy.mapowanie([1, 2, 3])
    pole = _zdania(schemat, "ustalenia")["items"]
    assert set(pole) == {"type", "enum"}, (
        f"pole numeru zdania ma dodatkowe warunki: {pole}")
    assert 99 not in pole["enum"]


def test_pusty_zbior_zdan_dopuszcza_wylacznie_pusta_liste():
    """Gdy nie ma czego cytować, model ma to powiedzieć wprost.

    Pusty `enum` jest w gramatyce niewyrażalny, więc moduł zwraca
    schemat z `maxItems: 0` zamiast schematu, którego nie da się
    spełnić — inaczej wywołanie kończyłoby się błędem dekodowania,
    a nie odmową.
    """
    schemat = schematy.mapowanie([])
    ustalenia = schemat["properties"]["ustalenia"]
    assert ustalenia["maxItems"] == 0
    assert schemat["required"] == ["ustalenia"]


def test_ustalenie_wymaga_i_tekstu_i_zdan():
    """Ustalenie bez cytatu jest tym, czego cały system zabrania."""
    schemat = schematy.mapowanie([1])
    wymagane = schemat["properties"]["ustalenia"]["items"]["required"]
    assert set(wymagane) == {"tekst", "zdania"}


def test_co_najmniej_jedno_zdanie_na_ustalenie():
    schemat = schematy.mapowanie([1, 2])
    assert _zdania(schemat, "ustalenia")["minItems"] == 1


@pytest.mark.parametrize("maks_ustalen,maks_zdan", [(1, 1), (12, 3), (40, 8)])
def test_limity_sa_przekazywane(maks_ustalen, maks_zdan):
    schemat = schematy.mapowanie([1, 2, 3], maks_ustalen, maks_zdan)
    assert schemat["properties"]["ustalenia"]["maxItems"] == maks_ustalen
    assert _zdania(schemat, "ustalenia")["maxItems"] == maks_zdan


# ── twierdzenia: ta sama mechanika, inna nazwa klucza ───────────────

def test_twierdzenia_maja_ten_sam_rygor_co_ustalenia():
    """Tor szybki nie może być słabszy od analizy.

    Nazwa klucza różni się wyłącznie dlatego, że zapisane w bazie wątki
    rozmów znają „twierdzenia" — zmiana nazwy unieważniłaby historię.
    Rygor musi być identyczny.
    """
    numery = [4, 8, 15]
    z_analizy = _zdania(schematy.mapowanie(numery), "ustalenia")
    z_czatu = _zdania(schematy.twierdzenia(numery), "twierdzenia")
    assert z_analizy == z_czatu


def test_twierdzenia_przy_pustym_zbiorze():
    schemat = schematy.twierdzenia([])
    assert schemat["properties"]["twierdzenia"]["maxItems"] == 0
    assert schemat["required"] == ["twierdzenia"]


# ── dekompozycja ────────────────────────────────────────────────────

def test_dekompozycja_wymusza_nazwe_klucza():
    """Usuwa klasę usterek, którą łatała normalizacja nazw.

    Model pisał po polsku i zwracał „wątki" tam, gdzie szablon prosił
    o „watki" — sztywny odczyt dawał ciche zero.
    """
    schemat = schematy.dekompozycja()
    assert schemat["required"] == ["watki"]
    assert schemat["properties"]["watki"]["minItems"] == 1


# ── synteza: wniosek zakotwiczony w numerze ustalenia ───────────────

def test_wniosek_moze_powolac_wylacznie_ustalenie_ktore_przeszlo():
    """Wniosek oparty na ustaleniu odrzuconym staje się niewyrażalny."""
    schemat = schematy.synteza([1, 2])
    kotwica = schemat["properties"]["wnioski"]["items"]["properties"]["oparte_na"]
    assert kotwica["items"]["enum"] == [1, 2]
    assert kotwica["minItems"] == 1


def test_brak_ustalen_nie_pozwala_na_zaden_wniosek():
    """Bez ustalenia nie ma wniosku — nie ma na czym go oprzeć."""
    schemat = schematy.synteza([])
    kotwica = schemat["properties"]["wnioski"]["items"]["properties"]["oparte_na"]
    assert kotwica["maxItems"] == 0


def test_synteza_wymaga_kompletu_sekcji():
    """Braki i rozbieżności są częścią odpowiedzi, nie dodatkiem.

    Gdyby model mógł je pominąć, analiza wyglądałaby na pełniejszą,
    niż jest — a luka w aktach jest dla prawnika informacją.
    """
    schemat = schematy.synteza([1])
    assert set(schemat["required"]) == {
        "wnioski", "rozbieznosci", "luki", "podstawa_prawna"}


def test_podstawa_prawna_bez_przepisow_jest_pusta():
    """Bez podanych przepisów model nie może żadnego powołać."""
    schemat = schematy.synteza([1], numery_przepisow=None)
    assert schemat["properties"]["podstawa_prawna"]["maxItems"] == 0


def test_podstawa_prawna_ograniczona_do_podanych_przepisow():
    schemat = schematy.synteza([1], numery_przepisow=[5, 9])
    pole = schemat["properties"]["podstawa_prawna"]["items"]
    assert pole["properties"]["przepis"]["enum"] == [5, 9]
    assert set(pole["required"]) == {"tekst", "przepis"}


# ── odporność na wejście spoza scenariusza ─────────────────────────

def test_numery_nie_sa_wspoldzielone_miedzy_wywolaniami():
    """Schemat nie może trzymać referencji do listy wywołującego.

    Gdyby trzymał, dopisanie numeru po zbudowaniu schematu cicho
    rozszerzyłoby enum — czyli dopuściło zdanie, którego model nie
    widział.
    """
    numery = [1, 2]
    schemat = schematy.mapowanie(numery)
    numery.append(999)
    assert 999 not in _zdania(schemat, "ustalenia")["items"]["enum"]
