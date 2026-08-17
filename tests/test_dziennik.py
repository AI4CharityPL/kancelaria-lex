"""Dziennik kontroli — zapis, odczyt i BRAK TREŚCI AKT we wpisie.

Test najważniejszy w tym pliku to `test_wpis_nie_zawiera_tresci`.
Sprawdza ZAWARTOŚĆ zapisanego wiersza, a nie deklarację w dokumentacji —
bo wymaganie T-4 (`log rejestruje dostęp, nie kopiuje treści`) można
złamać jednym nieuważnym dopisaniem pola.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

import dziennik  # noqa: E402


@pytest.fixture()
def db():
    polaczenie = sqlite3.connect(":memory:")
    polaczenie.row_factory = sqlite3.Row
    dziennik.przygotuj(polaczenie)
    yield polaczenie
    polaczenie.close()


PYTANIE = "Jakie zdarzenie akta sprawy II K 147/26 wiążą z datą 8 maja 2023 r.?"

ODPOWIEDZ = {
    "tekst": "Świadek zeznał, że widział pojazd marki Opel.",
    "cytaty": [
        {"dokument_id": "106", "poczatek": 10, "koniec": 90,
         "fragment": "Świadek C. L. zeznał, że widział pojazd marki Opel "
                     "koloru srebrnego przy ulicy Długiej.",
         "stopien": "mocne", "pokrycie": 0.92, "kontrola": "prawda"},
        {"dokument_id": "106", "poczatek": 200, "koniec": 260,
         "fragment": "Zdarzenie miało miejsce około godziny 21:30.",
         "stopien": "slabe", "pokrycie": 0.41, "kontrola": "prawda"},
    ],
    "odrzucone": [
        {"tekst": "Oskarżony przyznał się do winy.",
         "powod": "odrzucony_kontrola_niezalezna",
         "szczegol": "Zdanie tego nie stwierdza."},
        {"tekst": "Kwota 5000 zł.",
         "powod": "odrzucony_brak_wsparcia_w_cytacie",
         "szczegol": "twierdzenie powołuje 5000 zł, a w cytacie tego nie ma"},
    ],
}


# ── zasada nadrzędna: bez treści ─────────────────────────────────────

def test_wpis_nie_zawiera_tresci(db):
    """We wpisie nie ma ANI pytania, ANI cytatów, ANI treści akt.

    Gdyby dziennik zapisywał treść, sam stałby się zbiorem objętym
    tajemnicą zawodową — i przy zajęciu sprzętu wydałby akta drugi raz.
    """
    wpis = dziennik.z_odpowiedzi(ODPOWIEDZ, sprawa_id=1, tor="szybki")
    dziennik.zapisz(db, PYTANIE, wpis)

    wiersz = dziennik.ostatnie(db)[0]
    zapisane = " ".join(str(v) for v in wiersz.values()).casefold()

    zakazane = [
        "II K 147/26", "8 maja", "Opel", "srebrnego", "Długiej",
        "Świadek", "oskarżony", "przyznał", "21:30", "5000",
        "zdarzenie", "akta",
    ]
    for fraza in zakazane:
        assert fraza.casefold() not in zapisane, (
            f"WYCIEK TREŚCI DO DZIENNIKA: {fraza!r} znalazło się we wpisie. "
            f"Wymaganie T-4: log rejestruje dostęp, nie kopiuje treści."
        )


def test_pytanie_zapisane_jako_skrot(db):
    dziennik.zapisz(db, PYTANIE, dziennik.z_odpowiedzi(ODPOWIEDZ, 1, "szybki"))
    wiersz = dziennik.ostatnie(db)[0]

    assert wiersz["skrot_pytania"] == dziennik.skrot(PYTANIE)
    assert len(wiersz["skrot_pytania"]) == 16
    assert PYTANIE not in str(wiersz)


def test_skrot_rozpoznaje_powtorzenie_ale_nie_odtwarza():
    a = dziennik.skrot("Kiedy doręczono postanowienie?")
    b = dziennik.skrot("  kiedy doręczono postanowienie?  ")
    c = dziennik.skrot("Kiedy wydano postanowienie?")

    assert a == b, "ten sam sens po normalizacji powinien dać ten sam skrót"
    assert a != c, "różne pytania muszą dać różne skróty"


# ── zliczanie ────────────────────────────────────────────────────────

def test_liczniki_z_odpowiedzi():
    wpis = dziennik.z_odpowiedzi(ODPOWIEDZ, sprawa_id=3, tor="analiza")

    assert wpis.mocne == 1
    assert wpis.slabe == 1
    assert wpis.brak == 1                    # jedno odrzucone przez wsparcie
    assert wpis.kontrola_falsz == 1          # jedno odrzucone przez kontrolę
    assert wpis.twierdzen == 4               # 2 cytaty + 2 odrzucone
    assert 0.6 < wpis.srednie_pokrycie < 0.7


def test_niezweryfikowane_sa_liczone():
    odp = {"cytaty": [{"stopien": "mocne", "pokrycie": 0.9,
                       "kontrola": "niezweryfikowane"}], "odrzucone": []}
    assert dziennik.z_odpowiedzi(odp, 1, "szybki").kontrola_brak == 1


def test_pusta_odpowiedz_nie_wywraca():
    wpis = dziennik.z_odpowiedzi({}, None, "szybki")
    assert wpis.twierdzen == 0 and wpis.srednie_pokrycie == 0.0


# ── odczyt zbiorczy ──────────────────────────────────────────────────

def test_zbiorczo_liczy_udzialy(db):
    for _ in range(3):
        dziennik.zapisz(db, PYTANIE, dziennik.z_odpowiedzi(ODPOWIEDZ, 1, "szybki"))

    z = dziennik.zbiorczo(db, dni=7)
    assert z["zapytan"] == 3
    assert z["twierdzen"] == 12
    assert z["mocne"] == 3 and z["kontrola_falsz"] == 3
    assert z["udzial_falsz"] == pytest.approx(3 / 12, abs=0.01)


def test_zbiorczo_bez_wpisow_nie_dzieli_przez_zero(db):
    z = dziennik.zbiorczo(db, dni=7)
    assert z["zapytan"] == 0 and z["udzial_brak"] == 0.0


# ── retencja ─────────────────────────────────────────────────────────

def test_posprzataj_usuwa_stare(db):
    dziennik.zapisz(db, PYTANIE, dziennik.z_odpowiedzi(ODPOWIEDZ, 1, "szybki"))
    db.execute("UPDATE dziennik_kontroli SET czas = '2020-01-01T00:00:00+00:00'")
    db.commit()

    assert dziennik.posprzataj(db, dni=90) == 1
    assert dziennik.ostatnie(db) == []


def test_posprzataj_zostawia_swieze(db):
    dziennik.zapisz(db, PYTANIE, dziennik.z_odpowiedzi(ODPOWIEDZ, 1, "szybki"))
    assert dziennik.posprzataj(db, dni=90) == 0
    assert len(dziennik.ostatnie(db)) == 1
