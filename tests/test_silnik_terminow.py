"""Testy deterministycznego silnika terminów — kamień milowy M4.

Sprawdzają przede wszystkim, że system NIE POZWALA obejść
zabezpieczeń proceduralnych: niezatwierdzona reguła nie tworzy
terminu wiążącego, a termin bez potwierdzenia prawnika nie wiąże.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "aplikacje"))

from sprawy.silnik_terminow import (  # noqa: E402
    KalendarzDniWolnych, ObslugaDniWolnych, Regula, SilnikTerminow,
    SposobLiczenia, StatusTerminu, ZdarzenieInicjujace,
)


REGULA_ZATWIERDZONA = Regula(
    id="apelacja_karna",
    zdarzenie="doreczenie_wyroku_z_uzasadnieniem",
    dlugosc_dni=14,
    liczenie=SposobLiczenia.OD_DNIA_NASTEPNEGO,
    dni_wolne=ObslugaDniWolnych.PRZESUN_NA_NASTEPNY_ROBOCZY,
    podstawa="art. 445 § 1 k.p.k.",
    zatwierdzil="adw. Testowa",
    data_zatwierdzenia=date(2026, 8, 1),
)

REGULA_NIEZATWIERDZONA = Regula(
    id="zazalenie_karne",
    zdarzenie="doreczenie_postanowienia",
    dlugosc_dni=7,
    liczenie=SposobLiczenia.OD_DNIA_NASTEPNEGO,
    dni_wolne=ObslugaDniWolnych.PRZESUN_NA_NASTEPNY_ROBOCZY,
    podstawa="art. 460 k.p.k.",
)

REGULY = {r.id: r for r in (REGULA_ZATWIERDZONA, REGULA_NIEZATWIERDZONA)}


def zdarzenie(d: date, rodzaj="doreczenie_wyroku_z_uzasadnieniem"):
    return ZdarzenieInicjujace(rodzaj, d, "dok-2", 0, 60)


@pytest.fixture
def silnik():
    return SilnikTerminow(REGULY)


# ── arytmetyka ──────────────────────────────────────────────────────

def test_liczenie_od_dnia_nastepnego(silnik):
    """Doręczenie 12.08.2026 (śr) + 14 dni → 26.08.2026 (śr)."""
    t = silnik.oblicz(zdarzenie(date(2026, 8, 12)), "apelacja_karna")
    assert t.data_uplywu == date(2026, 8, 26)


def test_liczenie_od_dnia_zdarzenia():
    regula = Regula(
        id="x", zdarzenie="e", dlugosc_dni=7,
        liczenie=SposobLiczenia.OD_DNIA_ZDARZENIA,
        dni_wolne=ObslugaDniWolnych.BEZ_PRZESUNIECIA,
        podstawa="-", zatwierdzil="a", data_zatwierdzenia=date(2026, 1, 1),
    )
    s = SilnikTerminow({"x": regula})
    t = s.oblicz(zdarzenie(date(2026, 8, 12), "e"), "x")
    assert t.data_uplywu == date(2026, 8, 18)


def test_przesuniecie_z_soboty_na_poniedzialek(silnik):
    """Termin wypadający w sobotę przesuwa się na poniedziałek."""
    # 2026-08-08 to sobota
    kal = KalendarzDniWolnych()
    assert kal.wolny(date(2026, 8, 8))
    assert kal.nastepny_roboczy(date(2026, 8, 8)) == date(2026, 8, 10)


def test_przesuniecie_ze_swieta_stalego():
    """15 sierpnia to dzień ustawowo wolny."""
    kal = KalendarzDniWolnych()
    assert kal.wolny(date(2026, 8, 15))


def test_przesuniecie_generuje_ostrzezenie(silnik):
    """Prawnik musi wiedzieć, że termin został przesunięty."""
    # Dobieramy zdarzenie tak, by termin wypadł w dzień wolny.
    for dzien in range(1, 29):
        t = silnik.oblicz(zdarzenie(date(2026, 8, dzien)), "apelacja_karna")
        if any("dzień wolny" in o for o in t.ostrzezenia):
            return
    pytest.fail("Żaden termin nie wypadł w dzień wolny — test nie sprawdza tego, co miał")


def test_kalendarz_nie_wpada_w_petle():
    """Błędny wykaz świąt nie może zawiesić systemu."""
    wszystkie_wolne = {date(2026, 9, d) for d in range(1, 31)}
    kal = KalendarzDniWolnych(swieta_ruchome=wszystkie_wolne)
    with pytest.raises(ValueError, match="30 kolejnych dni wolnych"):
        kal.nastepny_roboczy(date(2026, 9, 1))


# ── zabezpieczenia proceduralne (istota ADR-0005) ───────────────────

def test_termin_domyslnie_nie_jest_wiazacy(silnik):
    """Nawet z zatwierdzonej reguły — czeka na potwierdzenie prawnika."""
    t = silnik.oblicz(zdarzenie(date(2026, 8, 12)), "apelacja_karna")
    assert t.status is StatusTerminu.PROPOZYCJA
    assert not t.wiazacy
    assert any("wymaga potwierdzenia" in o for o in t.ostrzezenia)


def test_niezatwierdzona_regula_daje_status_ostrzegawczy(silnik):
    t = silnik.oblicz(
        zdarzenie(date(2026, 8, 12), "doreczenie_postanowienia"), "zazalenie_karne"
    )
    assert t.status is StatusTerminu.NIEZATWIERDZONA_REGULA
    assert not t.wiazacy
    assert "NIE ZOSTAŁA ZATWIERDZONA" in t.ostrzezenia[0]


def test_nie_mozna_potwierdzic_terminu_z_niezatwierdzonej_reguly(silnik):
    """Zabezpieczenie przed obejściem przeglądu prawniczego."""
    t = silnik.oblicz(
        zdarzenie(date(2026, 8, 12), "doreczenie_postanowienia"), "zazalenie_karne"
    )
    with pytest.raises(ValueError, match="niezatwierdzonej"):
        SilnikTerminow.potwierdz(t, "adw. Testowa")


def test_potwierdzenie_czyni_termin_wiazacym(silnik):
    t = silnik.oblicz(zdarzenie(date(2026, 8, 12)), "apelacja_karna")
    SilnikTerminow.potwierdz(t, "adw. Testowa")
    assert t.wiazacy
    assert any("adw. Testowa" in o for o in t.ostrzezenia)


# ── ślad audytowy ───────────────────────────────────────────────────

def test_termin_niesie_podstawe_prawna(silnik):
    t = silnik.oblicz(zdarzenie(date(2026, 8, 12)), "apelacja_karna")
    assert t.podstawa == "art. 445 § 1 k.p.k."


def test_termin_niesie_cytat_ze_zrodla(silnik):
    """Prawnik musi móc sprawdzić, skąd wziął się termin."""
    t = silnik.oblicz(zdarzenie(date(2026, 8, 12)), "apelacja_karna")
    assert t.zdarzenie.dokument_id == "dok-2"
    assert t.zdarzenie.cytat_koniec > t.zdarzenie.cytat_poczatek


def test_nieznana_regula_podnosi_wyjatek(silnik):
    with pytest.raises(KeyError):
        silnik.oblicz(zdarzenie(date(2026, 8, 12)), "nie_istnieje")


def test_wyszukiwanie_regul_po_zdarzeniu(silnik):
    reguly = silnik.reguly_dla("doreczenie_wyroku_z_uzasadnieniem")
    assert [r.id for r in reguly] == ["apelacja_karna"]
