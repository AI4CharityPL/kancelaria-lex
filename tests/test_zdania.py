"""Podział na zdania — testy skrótów prawniczych i wierności offsetów.

Dwie własności są tu krytyczne i obie psują się cicho:

  1. Skrót z kropką NIE kończy zdania. Bez tego „art. 445 § 1 k.p.k."
     rozpada się na kilka „zdań", numeracja przestaje cokolwiek znaczyć,
     a cytat po numerze wskazuje fragment „445 §".

  2. Offsety muszą wskazywać ORYGINAŁ. Weryfikator cytatów porównuje
     zakres znaków z treścią dokumentu źródłowego — zdanie z błędną
     pozycją daje cytat, który nie przejdzie weryfikacji, choć jest
     prawdziwy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from zdania import (  # noqa: E402
    podziel_na_zdania, ponumeruj, znajdz_zdanie,
)


# ── własność nadrzędna: offsety wskazują oryginał ────────────────────

TEKSTY = [
    "Sąd ustalił, że oskarżony przebywał w tym czasie w miejscu pracy. "
    "Świadek zeznał, że widział pojazd marki Opel koloru srebrnego.",

    "Na podstawie art. 445 § 1 k.p.k. w zw. z art. 437 § 2 k.p.k. sąd "
    "uchylił zaskarżony wyrok w całości. Sprawę przekazano do ponownego "
    "rozpoznania.",

    "The Court finds that the defendant, Mr. Lacey, was not present. "
    "See United States v. Smith, 123 F.3d 456 (9th Cir. 1997).",
]


@pytest.mark.parametrize("tresc", TEKSTY)
def test_offsety_wskazuja_oryginal(tresc):
    """Każde zdanie da się odczytać z powrotem ze źródła po offsetach.

    To jest ta własność, od której zależy cały mechanizm cytowania.
    """
    for z in podziel_na_zdania(tresc):
        assert tresc[z.poczatek:z.koniec] == z.tekst, (
            f"zdanie {z.numer}: offsety {z.poczatek}-{z.koniec} dają "
            f"{tresc[z.poczatek:z.koniec]!r}, a tekst to {z.tekst!r}"
        )


@pytest.mark.parametrize("tresc", TEKSTY)
def test_zdania_nie_nachodza_i_zachowuja_kolejnosc(tresc):
    zdania = podziel_na_zdania(tresc)
    for wcz, nast in zip(zdania, zdania[1:]):
        assert wcz.koniec <= nast.poczatek, "zdania nachodzą na siebie"
        assert wcz.numer < nast.numer


# ── skróty prawnicze ─────────────────────────────────────────────────

SKROTY_KTORE_NIE_KONCZA_ZDANIA = [
    ("Sąd zastosował art. 445 k.p.k. i uchylił wyrok.", "art. + k.p.k."),
    ("Zgodnie z art. 12 ust. 3 pkt 2 ustawy oskarżony odpowiada.", "ust. + pkt"),
    ("Postanowienie z dnia 5 sierpnia 2026 r. doręczono obrońcy.", "r."),
    ("Opublikowano w Dz.U. z 2026 r. poz. 1234 bez zmian.", "Dz.U. + poz."),
    ("Zdarzenie miało miejsce o godz. 21.30 na ul. Długiej w Krakowie.", "godz. + ul."),
    ("Biegły dr hab. Jan Kowalski sporządził opinię w tej sprawie.", "dr hab."),
    ("Wartość szkody ustalono na 12 tys. zł według cen rynkowych.", "tys."),
    ("Sprawę rozpoznał SO w Krakowie w składzie trzyosobowym zawodowym.", "SO"),
]


@pytest.mark.parametrize("tresc,opis", SKROTY_KTORE_NIE_KONCZA_ZDANIA)
def test_skrot_nie_rozbija_zdania(tresc, opis):
    """Kropka po skrócie nie jest końcem zdania."""
    zdania = podziel_na_zdania(tresc)
    assert len(zdania) == 1, (
        f"{opis}: tekst rozbity na {len(zdania)} zdań zamiast jednego — "
        f"{[z.tekst for z in zdania]}"
    )


def test_inicjal_nie_rozbija_zdania():
    tresc = "Zeznania złożył J. Kowalski w obecności obrońcy oskarżonego."
    assert len(podziel_na_zdania(tresc)) == 1


def test_numeracja_pozycji_nie_rozbija_zdania():
    tresc = "1. Sąd ustalił, że oskarżony działał umyślnie i z premedytacją."
    assert len(podziel_na_zdania(tresc)) == 1


ANG_SKROTY = [
    "The motion cites 18 U.S.C. § 1591 as the operative statute here.",
    "See Brown v. Board, 347 U.S. 483 (1954), for the governing rule.",
    "Defendant Mr. Lacey filed the motion on Sept. 14 of that year.",
]


@pytest.mark.parametrize("tresc", ANG_SKROTY)
def test_skroty_angielskie(tresc):
    assert len(podziel_na_zdania(tresc, jezyk="en")) == 1


# ── faktyczny podział ────────────────────────────────────────────────

def test_dwa_zdania_sa_rozdzielone():
    tresc = ("Sąd ustalił, że oskarżony był obecny na miejscu zdarzenia. "
             "Świadek potwierdził tę okoliczność w swoich zeznaniach.")
    zdania = podziel_na_zdania(tresc)
    assert len(zdania) == 2
    assert zdania[0].tekst.startswith("Sąd ustalił")
    assert zdania[1].tekst.startswith("Świadek potwierdził")


def test_zdanie_ze_skrotem_i_prawdziwym_koncem():
    """Skrót w środku, prawdziwa granica na końcu — dwa zdania, nie pięć."""
    tresc = ("Sąd na podstawie art. 445 § 1 k.p.k. uchylił zaskarżony wyrok. "
             "Sprawę przekazano do ponownego rozpoznania sądowi rejonowemu.")
    zdania = podziel_na_zdania(tresc)
    assert len(zdania) == 2, [z.tekst for z in zdania]
    assert "art. 445 § 1 k.p.k." in zdania[0].tekst


# ── przypadki brzegowe ───────────────────────────────────────────────

@pytest.mark.parametrize("tresc", ["", "   ", "\n\n\n"])
def test_pusty_tekst(tresc):
    assert podziel_na_zdania(tresc) == []


def test_okruchy_ponizej_progu_sa_pomijane():
    """Nagłówki i numery stron nie zaśmiecają numeracji."""
    tresc = ("Str. 1\n\nSąd Rejonowy w Krakowie ustalił następujący stan "
             "faktyczny w niniejszej sprawie karnej.")
    zdania = podziel_na_zdania(tresc)
    assert all(len(z.tekst) >= 20 for z in zdania)


def test_numeracja_od_jedynki():
    zdania = podziel_na_zdania(TEKSTY[0])
    assert [z.numer for z in zdania] == list(range(1, len(zdania) + 1))


# ── funkcje pomocnicze ───────────────────────────────────────────────

def test_ponumeruj_daje_postac_dla_modelu():
    zdania = podziel_na_zdania(TEKSTY[0])
    wynik = ponumeruj(zdania)
    assert wynik.startswith("[1] ")
    assert "\n[2] " in wynik


def test_ponumeruj_respektuje_limit():
    zdania = podziel_na_zdania(TEKSTY[0])
    assert len(zdania) >= 2, "test wymaga co najmniej dwóch zdań"
    krotkie = ponumeruj(zdania, limit_znakow=len(zdania[0].tekst) + 20)
    assert krotkie.startswith("[1] ")
    assert "[2] " not in krotkie


def test_ponumeruj_nigdy_nie_zwraca_pustki():
    """Budżet mniejszy od pierwszego zdania NIE może dać pustego wyniku.

    Pusty wykaz zdań wygląda dla modelu jak dokument bez treści —
    zwróciłby pustą listę ustaleń, a to nieodróżnialne od „w aktach
    nic nie ma". Pierwsze zdanie wchodzi zawsze, choćby przekraczało
    budżet; przycinanie odpada, bo zepsułoby wierność cytatu.
    """
    zdania = podziel_na_zdania(TEKSTY[0])
    wynik = ponumeruj(zdania, limit_znakow=1)
    assert wynik.startswith("[1] ")
    assert zdania[0].tekst in wynik


def test_znajdz_zdanie_po_pozycji():
    tresc = TEKSTY[0]
    zdania = podziel_na_zdania(tresc)
    cel = zdania[1]
    trafione = znajdz_zdanie(zdania, cel.poczatek + 5)
    assert trafione is not None and trafione.numer == cel.numer


def test_znajdz_zdanie_poza_zakresem():
    zdania = podziel_na_zdania(TEKSTY[0])
    assert znajdz_zdanie(zdania, 10_000) is None
