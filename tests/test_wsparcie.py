"""Kontrola mechaniczna — czy cytat popiera twierdzenie.

Sprawdza obie strony: że niewsparte twierdzenia odpadają ORAZ że
poprawne przechodzą. Ta druga jest tu ważniejsza — kontrola, która
odrzuca prawdziwe ustalenia, zamienia jedną klasę błędu na drugą
i pogarsza J-4, które już jest poza limitem.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from wsparcie import Stopien, oszacuj, podsumuj  # noqa: E402


# ── wyróżniki twarde ────────────────────────────────────────────────

def test_kwota_z_twierdzenia_musi_byc_w_cytacie():
    w = oszacuj("Sąd zasądził 20,00 zł tytułem kosztów",
                ["Sąd orzekł o kosztach postępowania odwoławczego."])
    assert w.stopien is Stopien.BRAK
    assert "20.00" in " ".join(w.brakujace)


def test_zgodna_kwota_przechodzi():
    w = oszacuj("Sąd zasądził 20,00 zł tytułem kosztów",
                ["zasądza od oskarżonego 20,00 zł tytułem kosztów procesu"])
    assert w.stopien is Stopien.MOCNE


def test_inny_zapis_tej_samej_daty_przechodzi():
    """USTALENIE U-1 — to jest przypadek, przez który powstała ta kontrola.

    Model zacytował dokument, w którym ten sam wyrok SN przywołano
    jako „23.07.1974 r." zamiast „23 lipca 1974 r.". Cytat jest
    poprawny; kontrola porównująca napisy odrzuciłaby go.
    """
    w = oszacuj("wyrok SN z 23 lipca 1974 r., V KR 212/74",
                ["por. wyrok SN z 23.07.1974 r., V KR 212/74, OSNKW 1974/12"])
    assert w.stopien is not Stopien.BRAK, w.powod


def test_inna_data_odpada():
    w = oszacuj("rozprawa odbyła się 14 września 2006 r.",
                ["rozprawa odbyła się 15 września 2006 r. przed sądem"])
    assert w.stopien is Stopien.BRAK


def test_inny_przepis_odpada():
    w = oszacuj("sąd orzekł na podstawie art. 49 § 2",
                ["sąd orzekł na podstawie art. 58 k.k. w zw. z art. 12"])
    assert w.stopien is Stopien.BRAK


# ── liczby ──────────────────────────────────────────────────────────

def test_liczba_z_twierdzenia_jest_sygnalizowana_ale_nie_odrzucana():
    """Gola liczba to OSTRZEŻENIE, nie wyrok — zmiana z 15.08.2026.

    Wcześniej brak liczby w cytacie dawał `BRAK`, czyli odrzucenie.
    Benchmark v2 z przypisaniem etapu wykazał, że ta warstwa odpowiada
    za 60% fałszywych odmów, a liczby porządkowe i opisowe („dwóch
    świadków", „punkt 3", „strona 12") bywają nieobecne w cytowanym
    zdaniu mimo wiernego twierdzenia.

    Sygnał zostaje — jako `SLABE` z wykazem brakujących liczb — ale
    rozstrzyga kontroler niezależny, który to potrafi (zmierzone:
    rozpoznaje „14 dni" wobec „7 dni" jako sprzeczność). Warstwa tania
    segreguje, warstwa dokładna orzeka.
    """
    w = oszacuj("przy pojeździe stało dwóch mężczyzn, świadków było 3",
                ["przy pojeździe stał mężczyzna w ciemnej kurtce"])
    assert w.stopien is Stopien.SLABE
    assert "3" in w.brakujace, "brakująca liczba ma zostać wykazana"
    assert w.wymaga_kontroli_modelem, "ma trafić do kontrolera, nie przepaść"


def test_zgodna_liczba_nie_przeszkadza():
    w = oszacuj("obserwował zdarzenie przez 2 minuty",
                ["całe zdarzenie obserwowałem przez 2 minuty, po czym odszedłem"])
    assert w.stopien is Stopien.MOCNE


# ── pokrycie treściowe ──────────────────────────────────────────────

def test_wierne_streszczenie_jest_mocne():
    w = oszacuj("Świadek widział pojazd marki Opel koloru srebrnego",
                ["Zauważyłem stojący pojazd marki Opel koloru srebrnego."])
    assert w.stopien is Stopien.MOCNE and w.pokrycie >= 0.6


def test_twierdzenie_o_czym_innym_odpada():
    w = oszacuj("biegły stwierdził uszkodzenie zamka w drzwiach",
                ["świadek zeznał, że wracał z pracy ulicą Ogrodową"])
    assert w.stopien is Stopien.BRAK


def test_czesciowe_pokrycie_daje_slabe():
    w = oszacuj("świadek zeznał o pojeździe stojącym przy krawężniku nocą",
                ["świadek zeznał o pojeździe"])
    assert w.stopien in (Stopien.SLABE, Stopien.BRAK)


# ── granice zapisane wprost ─────────────────────────────────────────

def test_odwrocona_negacja_NIE_jest_lapana():
    """⚠️ UDOKUMENTOWANA GRANICA, NIE USTERKA.

    „sąd uwzględnił" i „sąd nie uwzględnił" mają niemal identyczny
    zestaw słów znaczących, bo „nie" jest stopsłowem. Pokrycie
    leksykalne tego nie odróżni — od tego jest kontrola niezależna
    (panel/kontrola.py).

    Test istnieje po to, żeby ta granica była widoczna w kodzie,
    a nie odkrywana przez prawnika na sprawie.
    """
    w = oszacuj("sąd uwzględnił wniosek obrońcy o dopuszczenie dowodu",
                ["sąd nie uwzględnił wniosku obrońcy o dopuszczenie dowodu"])
    assert w.stopien is Stopien.MOCNE     # przechodzi — i to jest problem
    assert w.wymaga_kontroli_modelem      # dlatego idzie dalej


# ── przypadki brzegowe ──────────────────────────────────────────────

def test_twierdzenie_bez_cytatu():
    w = oszacuj("cokolwiek", [])
    assert w.stopien is Stopien.BRAK and not w.wymaga_kontroli_modelem


@pytest.mark.parametrize("tekst", ["", "   ", "\n"])
def test_puste_twierdzenie(tekst):
    assert oszacuj(tekst, ["treść"]).stopien is Stopien.BRAK


def test_dwa_zdania_licza_sie_lacznie():
    """Twierdzenie z dwóch zdań nie może przepadać przez słabsze z nich.

    Sprawdzenie idzie po SUMIE cytatów: „pojazd" jest w pierwszym
    zdaniu, „numer rejestracyjny" w drugim. Wymaganie pokrycia przez
    każde z osobna dałoby tu ocenę słabą mimo pełnego pokrycia.
    """
    w = oszacuj("pojazd marki Opel, numeru rejestracyjnego nie podano",
                ["Zauważyłem pojazd marki Opel.",
                 "Numeru rejestracyjnego nie podano."])
    assert w.stopien is Stopien.MOCNE, f"{w.pokrycie:.2f} {w.powod}"


def test_parafraza_dostaje_slabe():
    """Twierdzenie oddające sens innymi słowami nie jest błędem —
    ale prawnik ma o tym wiedzieć.

    „świadek widział" wobec „zauważyłem", „podał" wobec „potrafię
    podać" — sens ten sam, słowa inne. Pokrycie leksykalne spada,
    więc twierdzenie dostaje znacznik i idzie do kontroli modelem,
    która ocenia sens, a nie słowa.
    """
    w = oszacuj("świadek widział Opla i nie podał numeru rejestracyjnego",
                ["Zauważyłem pojazd marki Opel.",
                 "Nie potrafię podać numeru rejestracyjnego."])
    assert w.stopien is not Stopien.MOCNE
    assert w.wymaga_kontroli_modelem


def test_brak_nie_idzie_do_modelu():
    """Oszczędność: po co pytać model, skoro kwoty fizycznie nie ma."""
    w = oszacuj("zasądzono 500,00 zł", ["sąd orzekł o kosztach"])
    assert not w.wymaga_kontroli_modelem


# ── podsumowanie ────────────────────────────────────────────────────

def test_podsumowanie_liczy_stopnie():
    p = podsumuj([
        oszacuj("Świadek widział pojazd marki Opel",
                ["Zauważyłem pojazd marki Opel."]),
        oszacuj("zasądzono 500,00 zł", ["sąd orzekł o kosztach"]),
    ])
    assert p.mocne == 1 and p.brak == 1


def test_podsumowanie_pustej_listy():
    p = podsumuj([])
    assert p.mocne == p.slabe == p.brak == 0
