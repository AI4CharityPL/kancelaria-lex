"""Zamknięcie zakresu w obrębie sprawy — właściwość rozstrzygająca panelu.

Wymaganie użytkownika: dokumenty i dane trafiają wyłącznie do wybranej
sprawy, a pamięć czatu jest zamknięta w jej obrębie.

To nie jest wygoda interfejsu, tylko realizacja wymagań F-30 (zasada
wiedzy koniecznej) i F-32 (ściany etyczne), a w sprawach karnych —
warunek zachowania tajemnicy zawodowej wobec różnych klientów
obsługiwanych w jednej instalacji.

Testy sprawdzają, że wyciek między sprawami wymagałby ZMIANY KODU,
a nie pomyłki w wywołaniu.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))
sys.path.insert(0, str(KORZEN / "src" / "aplikacje"))

import baza  # noqa: E402
from agenci.weryfikator_cytatow import (  # noqa: E402
    Cytat, Twierdzenie, WeryfikatorCytatow, Werdykt,
)

TRESC_A = ("Protokół w sprawie A. Świadek zeznał, że widział pojazd "
           "marki Opel koloru srebrnego.")
TRESC_B = ("Protokół w sprawie B. Oskarżony przyznał się do zarzucanego "
           "mu czynu w całości.")


@pytest.fixture
def db():
    polaczenie = baza.polacz(":memory:")
    yield polaczenie
    polaczenie.close()


@pytest.fixture
def dwie_sprawy(db):
    """Dwie niepowiązane sprawy — jak dwóch różnych klientów kancelarii."""
    a = baza.dodaj_sprawe(db, "II K 147/26", "Sprawa A", "SR Nowe Miasto")
    b = baza.dodaj_sprawe(db, "III K 999/25", "Sprawa B", "SO Nowe Miasto")
    dok_a = baza.dodaj_dokument(db, a, "protokol-A.txt", TRESC_A)
    dok_b = baza.dodaj_dokument(db, b, "protokol-B.txt", TRESC_B)
    return {"a": a, "b": b, "dok_a": dok_a, "dok_b": dok_b}


# ── dokumenty ───────────────────────────────────────────────────────

def test_dokument_trafia_wylacznie_do_wskazanej_sprawy(db, dwie_sprawy):
    dokumenty_a = baza.lista_dokumentow(db, dwie_sprawy["a"])
    dokumenty_b = baza.lista_dokumentow(db, dwie_sprawy["b"])

    assert [d["nazwa"] for d in dokumenty_a] == ["protokol-A.txt"]
    assert [d["nazwa"] for d in dokumenty_b] == ["protokol-B.txt"]


def test_tresci_zawezone_do_jednej_sprawy(db, dwie_sprawy):
    """To jedyne wejście do treści w całym panelu."""
    tresci_a = baza.tresci_dokumentow(db, dwie_sprawy["a"])
    polaczone = " ".join(tresci_a.values())

    assert "Opel" in polaczone
    assert "przyznał się" not in polaczone, (
        "Treść sprawy B przeciekła do zakresu sprawy A."
    )


def test_dokument_z_obcej_sprawy_jest_niewidoczny(db, dwie_sprawy):
    """Podanie numeru dokumentu z innej sprawy nie zwraca nic.

    Sam identyfikator dokumentu nie wystarcza — zapytanie zawsze niesie
    identyfikator sprawy w klauzuli WHERE.
    """
    obcy = baza.pobierz_dokument(db, dwie_sprawy["a"], dwie_sprawy["dok_b"])
    assert obcy is None

    wlasny = baza.pobierz_dokument(db, dwie_sprawy["a"], dwie_sprawy["dok_a"])
    assert wlasny is not None


def test_nie_da_sie_usunac_dokumentu_z_obcej_sprawy(db, dwie_sprawy):
    usunieto = baza.usun_dokument(db, dwie_sprawy["a"], dwie_sprawy["dok_b"])
    assert usunieto is False
    assert len(baza.lista_dokumentow(db, dwie_sprawy["b"])) == 1


def test_dokument_nie_moze_zawisnac_poza_sprawa(db):
    """Nie istnieje wariant dodania dokumentu bez sprawy."""
    with pytest.raises(ValueError, match="nie istnieje"):
        baza.dodaj_dokument(db, 99999, "sierota.txt", "treść")


# ── pamięć czatu ────────────────────────────────────────────────────

def test_pamiec_czatu_zamknieta_w_sprawie(db, dwie_sprawy):
    baza.dodaj_wiadomosc(db, dwie_sprawy["a"], "uzytkownik", "Pytanie o Opla")
    baza.dodaj_wiadomosc(db, dwie_sprawy["b"], "uzytkownik", "Pytanie o przyznanie")

    historia_a = baza.historia(db, dwie_sprawy["a"])
    historia_b = baza.historia(db, dwie_sprawy["b"])

    assert [w["tresc"] for w in historia_a] == ["Pytanie o Opla"]
    assert [w["tresc"] for w in historia_b] == ["Pytanie o przyznanie"]


def test_watek_dokumentu_odrebny_od_watku_sprawy(db, dwie_sprawy):
    """Rozmowa o jednym piśmie nie miesza się z rozmową o całej sprawie."""
    sprawa = dwie_sprawy["a"]
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie o całą sprawę")
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie o dokument",
                         dokument_id=dwie_sprawy["dok_a"])

    assert len(baza.historia(db, sprawa)) == 1
    assert len(baza.historia(db, sprawa, dwie_sprawy["dok_a"])) == 1
    assert baza.historia(db, sprawa)[0]["tresc"] == "Pytanie o całą sprawę"


def test_czyszczenie_watku_nie_rusza_innych_spraw(db, dwie_sprawy):
    baza.dodaj_wiadomosc(db, dwie_sprawy["a"], "uzytkownik", "A")
    baza.dodaj_wiadomosc(db, dwie_sprawy["b"], "uzytkownik", "B")

    baza.wyczysc_historie(db, dwie_sprawy["a"])

    assert baza.historia(db, dwie_sprawy["a"]) == []
    assert len(baza.historia(db, dwie_sprawy["b"])) == 1


# ── weryfikator na zawężonym zbiorze ────────────────────────────────

def test_cytat_z_obcej_sprawy_odrzucony(db, dwie_sprawy):
    """Rdzeń gwarancji.

    Weryfikator dostaje dokładnie ten sam zbiór, co model — dokumenty
    jednej sprawy. Cytat z innej sprawy nie ma jak przejść, bo nie ma
    go w zbiorze, wobec którego prowadzona jest weryfikacja.
    """
    zakres_a = baza.tresci_dokumentow(db, dwie_sprawy["a"])
    weryfikator = WeryfikatorCytatow(zakres_a)

    przeciek = Twierdzenie(
        "Oskarżony przyznał się do czynu.",
        [Cytat(str(dwie_sprawy["dok_b"]), 0, 30, "Oskarżony przyznał się")],
    )
    wynik = weryfikator.sprawdz_twierdzenie(przeciek)

    assert not wynik.przeszlo
    assert wynik.werdykt is Werdykt.ODRZUCONY_BRAK_DOKUMENTU


def test_zawezenie_do_dokumentu_odcina_reszte_sprawy(db, dwie_sprawy):
    """Wybór jednego pisma zawęża zakres także wewnątrz sprawy."""
    sprawa = dwie_sprawy["a"]
    drugi = baza.dodaj_dokument(db, sprawa, "opinia.txt",
                                "Opinia biegłego z zakresu mechanoskopii.")

    pelny = baza.tresci_dokumentow(db, sprawa)
    zawezony = baza.tresci_dokumentow(db, sprawa, dokument_id=drugi)

    assert len(pelny) == 2
    assert len(zawezony) == 1
    assert "Opel" not in " ".join(zawezony.values())


# ── log audytowy ────────────────────────────────────────────────────

def test_operacje_trafiaja_do_logu_audytowego(db, dwie_sprawy):
    wpisy = db.execute("SELECT operacja FROM audyt ORDER BY id").fetchall()
    operacje = [w["operacja"] for w in wpisy]
    assert operacje.count("utworzenie_sprawy") == 2
    assert operacje.count("dodanie_dokumentu") == 2


def test_lancuch_sum_audytu_nieprzerwany(db, dwie_sprawy):
    ok, opis = baza.zweryfikuj_lancuch_audytu(db)
    assert ok, opis


def test_manipulacja_logiem_jest_wykrywalna(db, dwie_sprawy):
    """Log podatny na modyfikację nie jest dowodem (wymaganie F-34)."""
    db.execute("UPDATE audyt SET szczegol = 'podmienione' WHERE id = 1")
    db.commit()

    ok, opis = baza.zweryfikuj_lancuch_audytu(db)
    assert not ok
    assert "przerwany" in opis
