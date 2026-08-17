"""Wątki rozmów — nazwane, wznawialne, zamknięte w obrębie sprawy.

TŁO
    Historia była JEDNĄ rozmową na parę (sprawa, dokument). Prawnik
    prowadzący dwa tropy w tej samej sprawie mieszał je w jednym ciągu,
    a powrót do wcześniejszego wątku po tygodniu wymagał przewijania.

ZASADA, KTÓREJ PILNUJĄ TE TESTY
    Zamknięcie w obrębie sprawy obowiązuje tak samo jak dla dokumentów:
    wątek z innej sprawy ma być NIEODRÓŻNIALNY od nieistniejącego.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402


@pytest.fixture()
def db():
    polaczenie = baza.polacz(":memory:")
    yield polaczenie
    polaczenie.close()


@pytest.fixture()
def sprawa(db):
    return baza.dodaj_sprawe(db, "II K 10/26", "Sprawa pierwsza")


@pytest.fixture()
def obca_sprawa(db):
    return baza.dodaj_sprawe(db, "II K 99/26", "Sprawa druga")


def test_zalozenie_i_odczyt(db, sprawa):
    wid = baza.zaloz_watek(db, sprawa, "Alibi oskarżonego")
    watek = baza.pobierz_watek(db, sprawa, wid)
    assert watek["tytul"] == "Alibi oskarżonego"
    assert watek["zamkniety"] == 0


def test_pusty_tytul_dostaje_zastepczy(db, sprawa):
    wid = baza.zaloz_watek(db, sprawa, "   ")
    assert baza.pobierz_watek(db, sprawa, wid)["tytul"] == "Nowy wątek"


def test_watek_z_innej_sprawy_niewidoczny(db, sprawa, obca_sprawa):
    """Sedno zamknięcia zakresu."""
    wid = baza.zaloz_watek(db, obca_sprawa, "Cudzy wątek")
    assert baza.pobierz_watek(db, sprawa, wid) is None
    assert baza.historia_watku(db, sprawa, wid) == []
    assert baza.usun_watek(db, sprawa, wid) is False
    assert baza.zmien_watek(db, sprawa, wid, tytul="Podmiana") is False
    # A w swojej sprawie nadal jest nietknięty.
    assert baza.pobierz_watek(db, obca_sprawa, wid)["tytul"] == "Cudzy wątek"


def test_lista_tylko_ze_swojej_sprawy(db, sprawa, obca_sprawa):
    baza.zaloz_watek(db, sprawa, "Mój")
    baza.zaloz_watek(db, obca_sprawa, "Cudzy")
    tytuly = [w["tytul"] for w in baza.lista_watkow(db, sprawa)]
    assert tytuly == ["Mój"]


def test_wiadomosci_trafiaja_do_watku(db, sprawa):
    a = baza.zaloz_watek(db, sprawa, "Wątek A")
    b = baza.zaloz_watek(db, sprawa, "Wątek B")
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie do A", watek_id=a)
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie do B", watek_id=b)

    tresci_a = [w["tresc"] for w in baza.historia_watku(db, sprawa, a)]
    assert tresci_a == ["Pytanie do A"]


def test_watek_nie_wycieka_do_rozmowy_sprawy(db, sprawa):
    """Wpisy wątku NIE mogą trafiać do rozmowy całej sprawy.

    Wykryte przeglądem 16.08.2026. Wiadomość wątku ma `dokument_id` puste,
    więc bez jawnego warunku wpadała również do historii sprawy — a stamtąd
    do PAMIĘCI przekazywanej modelowi przy pytaniu o całą sprawę.
    """
    wid = baza.zaloz_watek(db, sprawa, "Osobny trop")
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie w wątku",
                         watek_id=wid)
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Pytanie o całą sprawę")

    sprawy = [w["tresc"] for w in baza.historia(db, sprawa)]
    watku = [w["tresc"] for w in baza.historia_watku(db, sprawa, wid)]

    assert sprawy == ["Pytanie o całą sprawę"], sprawy
    assert watku == ["Pytanie w wątku"], watku


def test_watek_dokumentu_nie_wycieka_do_rozmowy_dokumentu(db, sprawa):
    """To samo dla wątku przypiętego do dokumentu."""
    dok = baza.dodaj_dokument(db, sprawa, "Pismo", "Treść pisma.")
    wid = baza.zaloz_watek(db, sprawa, "Wątek o piśmie", dokument_id=dok)
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "W wątku",
                         dokument_id=dok, watek_id=wid)
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Poza wątkiem",
                         dokument_id=dok)

    assert [w["tresc"] for w in baza.historia(db, sprawa, dok)] == ["Poza wątkiem"]


def test_licznik_wiadomosci_w_liscie(db, sprawa):
    wid = baza.zaloz_watek(db, sprawa, "Z licznikiem")
    for i in range(3):
        baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", f"P{i}", watek_id=wid)
    assert baza.lista_watkow(db, sprawa)[0]["wiadomosci"] == 3


def test_zamkniecie_nie_kasuje_wiadomosci(db, sprawa):
    """Zamknięty wątek ma dać się WZNOWIĆ — to była wprost postawiona
    potrzeba, więc zamknięcie nie może być usunięciem."""
    wid = baza.zaloz_watek(db, sprawa, "Do zamknięcia")
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Treść", watek_id=wid)

    baza.zmien_watek(db, sprawa, wid, zamkniety=True)
    assert baza.pobierz_watek(db, sprawa, wid)["zamkniety"] == 1
    assert len(baza.historia_watku(db, sprawa, wid)) == 1

    baza.zmien_watek(db, sprawa, wid, zamkniety=False)
    assert baza.pobierz_watek(db, sprawa, wid)["zamkniety"] == 0
    assert len(baza.historia_watku(db, sprawa, wid)) == 1


def test_zmiana_tytulu(db, sprawa):
    wid = baza.zaloz_watek(db, sprawa, "Stary")
    assert baza.zmien_watek(db, sprawa, wid, tytul="Nowy") is True
    assert baza.pobierz_watek(db, sprawa, wid)["tytul"] == "Nowy"


def test_usuniecie_watku_kasuje_wiadomosci(db, sprawa):
    wid = baza.zaloz_watek(db, sprawa, "Do usunięcia")
    baza.dodaj_wiadomosc(db, sprawa, "uzytkownik", "Treść", watek_id=wid)
    assert baza.usun_watek(db, sprawa, wid) is True
    assert db.execute("SELECT COUNT(*) c FROM wiadomosci "
                      "WHERE watek_id = ?", (wid,)).fetchone()["c"] == 0


def test_lista_sortuje_po_aktywnosci(db, sprawa):
    stary = baza.zaloz_watek(db, sprawa, "Starszy")
    nowy = baza.zaloz_watek(db, sprawa, "Nowszy")
    # Aktywność w starszym wątku wypycha go na górę listy.
    db.execute("UPDATE watki SET ostatnia_aktywnosc = ? WHERE id = ?",
               ("2030-01-01T00:00:00+00:00", stary))
    db.commit()
    assert baza.lista_watkow(db, sprawa)[0]["id"] == stary
    assert nowy in [w["id"] for w in baza.lista_watkow(db, sprawa)]


def test_watek_niesie_autora(db, sprawa):
    p = mod_profile.zaloz(db, "j.nowak", "haslo-do-testu-1", "Jan", "Nowak",
                          "aplikant",
                          zgody=list(mod_profile.WYMAGANE_ZGODY))
    wid = baza.zaloz_watek(db, sprawa, "Mój wątek", profil_id=p.id)
    assert baza.lista_watkow(db, sprawa)[0]["autor_nazwisko"] == "Nowak"
    assert baza.pobierz_watek(db, sprawa, wid)["profil_id"] == p.id
