"""Wyróżniki sprowadzone do wartości — daty, kwoty, sygnatury.

TŁO — zmierzony błąd, nie hipoteza.
    Benchmark 2026-08-14 18:27: 6 fałszywych odmów, WSZYSTKIE z kotwicą
    typu `data`, 5 z nich angielskie. Przyczyna: porównywanie napisów.
    Dla pytania o „October 6, 2016" przechodził wyłącznie zapis bajtowo
    identyczny; „6 October 2016", „10/6/2016", „October 6th, 2016"
    i „Oct. 6, 2016" dawały odmowę.

Te testy pilnują, żeby warianty zapisu schodziły się na wartości —
i żeby przy okazji NIE zeszły się rzeczy naprawdę różne.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from wyrozniki import (  # noqa: E402
    wyrozniki, zakotwiczone, znajdz_daty, znajdz_kwoty, znajdz_sygnatury,
)


# ── daty: warianty tej samej wartości ───────────────────────────────

@pytest.mark.parametrize("zapis", [
    "October 6, 2016",
    "6 October 2016",
    "October 6th, 2016",
    "Oct. 6, 2016",
    "Oct 6, 2016",
    "2016-10-06",
])
def test_warianty_angielskiej_daty(zapis):
    """DOKŁADNIE te zapisy dawały fałszywą odmowę."""
    assert "2016-10-06" in znajdz_daty(f"The hearing was held on {zapis}.")


@pytest.mark.parametrize("zapis", [
    "14 września 2006 r.",
    "14 września 2006 roku",
    "14.09.2006",
    "2006-09-14",
])
def test_warianty_polskiej_daty(zapis):
    assert "2006-09-14" in znajdz_daty(f"Rozprawa odbyła się {zapis}.")


def test_data_dwuznaczna_daje_obie_interpretacje():
    """10/6/2016 to 6 X (USA) albo 10 VI (Europa) — obie dopuszczone.

    Świadomy wybór: to sprawdzenie odpowiada na pytanie „czy odpowiedź
    dotyczy tego, o co pytano", nie „jaka to data".
    """
    d = znajdz_daty("filed 10/6/2016")
    assert "2016-10-06" in d and "2016-06-10" in d


def test_data_jednoznaczna_gdy_dzien_powyzej_12():
    d = znajdz_daty("filed 25/6/2016")
    assert d == {"2016-06-25"}


def test_odrzuca_niemozliwe_daty():
    assert znajdz_daty("13/45/2016") == set()
    assert znajdz_daty("32 October 2016") == set()


# ── kwoty ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("zapis", ["1.008,00 zł", "1008 zł", "1 008,00 PLN"])
def test_warianty_kwoty(zapis):
    assert "1008.00" in znajdz_kwoty(f"zasądza {zapis} tytułem kosztów")


def test_kwota_wymaga_waluty():
    """Bez waluty każda liczba byłaby kwotą i wyróżnik przestałby wyróżniać."""
    assert znajdz_kwoty("na stronie 1008 akt") == set()


def test_kwota_dolarowa():
    assert "12500.00" in znajdz_kwoty("a fine of $12,500 was imposed")


# ── sygnatury ───────────────────────────────────────────────────────

def test_rok_dwucyfrowy_i_czterocyfrowy_to_ta_sama_sprawa():
    a = znajdz_sygnatury("sygn. akt II K 147/26")
    b = znajdz_sygnatury("sygn. akt II K 147/2026")
    assert a == b and a


def test_sygnatura_amerykanska():
    assert "2:18-cr-422" in znajdz_sygnatury("Case 2:18-cr-00422 filed")


@pytest.mark.parametrize("zapis", ["art. 445 § 1", "art.445 §1", "Art. 445 § 1"])
def test_powolanie_przepisu(zapis):
    assert "art445§1" in znajdz_sygnatury(f"na podstawie {zapis} k.p.k.")


def test_rozne_przepisy_sie_nie_zlewaja():
    assert znajdz_sygnatury("art. 445") != znajdz_sygnatury("art. 446")


# ── zakotwiczenie ───────────────────────────────────────────────────

PYTANIE_EN = "What event do the case files associate with the date October 6, 2016?"


@pytest.mark.parametrize("zdanie", [
    "The hearing was held on October 6, 2016 before the court.",
    "The hearing was held on 6 October 2016 before the court.",
    "The hearing was held on October 6th, 2016 before the court.",
    "The hearing was held on Oct. 6, 2016 before the court.",
])
def test_zakotwiczenie_przechodzi_dla_wariantow(zdanie):
    """Te cztery przypadki to zmierzone fałszywe odmowy."""
    assert zakotwiczone(PYTANIE_EN, [zdanie])


def test_zakotwiczenie_odrzuca_inna_date():
    assert not zakotwiczone(PYTANIE_EN,
                            ["The hearing was held on October 7, 2016."])


def test_zakotwiczenie_odrzuca_sam_zgodny_rok():
    """Rok 2016 stoi w aktach na każdej stronie — nie jest wyróżnikiem."""
    assert not zakotwiczone(PYTANIE_EN,
                            ["Several motions were filed throughout 2016."])


def test_pytanie_bez_wyroznika_przechodzi():
    """Nie ma czego kotwiczyć — nie udajemy, że jest."""
    assert zakotwiczone("Czy zeznania świadków są spójne?",
                        ["Świadek zeznał, że widział pojazd."])


def test_zakotwiczenie_po_sygnaturze():
    assert zakotwiczone("W jakim kontekście akta powołują art. 49 § 2?",
                        ["Sąd orzekł na podstawie art. 49 § 2 k.p.k."])


def test_zakotwiczenie_odrzuca_inny_przepis():
    assert not zakotwiczone("W jakim kontekście akta powołują art. 49 § 2?",
                            ["Sąd orzekł na podstawie art. 58 k.k."])


def test_lamanie_wiersza_w_kotwicy():
    """Tekst z PDF łamie wiersze w środku daty."""
    assert zakotwiczone("What happened on October 6, 2016?",
                        ["The hearing was held on October 6,\n2016 before the court."])


# ── okresy: rok kalendarzowy to NIE czas trwania ────────────────────
#
# TŁO — zmierzony błąd, nie hipoteza.
#   Przebieg 2026-08-16 (sprawa 4, tryb cienia): 14 z 18 SZKODLIWYCH
#   odrzuceń miało przyczynę „wyroznik", a wśród wyciętych wartości
#   13 z 15 to były okresy typu `okres2016r`. Wzorzec czytał „2016 roku"
#   — standardowy polski zapis DATY — jako czas trwania 2016 lat.
#   Na samej sprawie 3 dawało to 2585 fałszywych wyróżników.
#
#   Skutek nie był kosmetyczny: okresy wchodzą do `zlozone`, a sekcja A
#   w `wsparcie.py` ODRZUCA twierdzenie, gdy wyróżnika nie ma w cytacie.
#   Fałszywy wyróżnik kasował więc poprawne odpowiedzi.

@pytest.mark.parametrize("zapis", [
    "13 stycznia 2025 roku",
    "z dnia 29 lipca 2005 roku o przeciwdziałaniu narkomanii",
    "w okresie od 01 stycznia 2019 roku do 31 marca 2021 roku",
])
def test_rok_kalendarzowy_nie_jest_okresem(zapis):
    """Data zapisana po polsku nie może udawać czasu trwania."""
    okresy = {s for s in znajdz_sygnatury(zapis) if s.startswith("okres")}
    assert not okresy, f"{zapis!r} dało fałszywe okresy: {okresy}"


@pytest.mark.parametrize("zapis,oczekiwany", [
    ("kara 8 lat pozbawienia wolności", "okres8r"),
    ("termin 30 dni na wniesienie zażalenia", "okres30d"),
    ("sentence of 51 years", "okres51r"),
    ("within 14 days of service", "okres14d"),
    # Granica: długi, ale realny okres zostaje wyróżnikiem.
    ("służebność na 150 lat", "okres150r"),
])
def test_prawdziwy_okres_zostaje(zapis, oczekiwany):
    """Zabezpieczenie nie może wyciąć okresów, dla których powstało.

    Rozpoznanie „51 years" i „18 U.S.C. §" było naprawą luki zmierzonej
    15.08.2026 (0/6 kotwic angielskich). Ta naprawa musi przetrwać.
    """
    assert oczekiwany in znajdz_sygnatury(zapis)
