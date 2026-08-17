"""Terminy w panelu — odczyt reguł z YAML-a i liczenie dat.

⚠️ TO JEDYNY OBSZAR SYSTEMU, W KTÓRYM BŁĄD MA BEZPOŚREDNI SKUTEK PRAWNY.

Przeoczony termin oznacza utratę środka zaskarżenia — szkodę dla
klienta, zwykle nieodwracalną, i odpowiedzialność zawodową prawnika.
Stąd testy sprawdzają nie tylko poprawne liczenie, lecz także to, że
reguła bez podpisu prawnika NIE wystawia terminu wiążącego.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))
sys.path.insert(0, str(KORZEN / "src" / "aplikacje"))

import terminy as mod_terminy  # noqa: E402
from sprawy.silnik_terminow import KalendarzDniWolnych, wielkanoc  # noqa: E402


# ── święta ruchome ───────────────────────────────────────────────────

@pytest.mark.parametrize("rok, oczekiwana", [
    (2024, date(2024, 3, 31)),
    (2025, date(2025, 4, 20)),
    (2026, date(2026, 4, 5)),
    (2027, date(2027, 3, 28)),
    (2030, date(2030, 4, 21)),
])
def test_wielkanoc_wyliczona(rok, oczekiwana):
    assert wielkanoc(rok) == oczekiwana


def test_boze_cialo_jest_dniem_wolnym():
    """⚠️ NAJWAŻNIEJSZE ŚWIĘTO RUCHOME W TYM MODULE.

    Wypada w czwartek, więc jako jedyne realnie przesuwa termin w środku
    tygodnia roboczego. Pominięte w wykazie dawało datę o dzień za
    wczesną — cicho i z pełnym przekonaniem.
    """
    kalendarz = KalendarzDniWolnych()
    assert kalendarz.wolny(date(2026, 6, 4))       # Boże Ciało 2026
    assert kalendarz.wolny(date(2027, 5, 27))      # Boże Ciało 2027
    assert not kalendarz.wolny(date(2026, 6, 5))   # piątek po nim


def test_poniedzialek_wielkanocny_jest_wolny():
    kalendarz = KalendarzDniWolnych()
    assert kalendarz.wolny(date(2026, 4, 6))
    assert kalendarz.wolny(date(2027, 3, 29))


def test_swieta_stale_nadal_dzialaja():
    kalendarz = KalendarzDniWolnych()
    for dzien in (date(2026, 1, 1), date(2026, 5, 1), date(2026, 11, 11),
                  date(2026, 12, 25)):
        assert kalendarz.wolny(dzien), dzien


def test_dzien_dodatkowy_ustawowy_da_sie_dopisac():
    """Dni wolne ogłaszane incydentalnie nie są wyliczalne — muszą wejść
    ręcznie. To ta część wykazu, której nie zastąpi arytmetyka."""
    zwykly = date(2026, 9, 15)
    assert not KalendarzDniWolnych().wolny(zwykly)
    assert KalendarzDniWolnych({zwykly}).wolny(zwykly)


# ── odczyt reguł ─────────────────────────────────────────────────────

def test_reguly_wczytuja_sie_z_pliku():
    reguly = mod_terminy.czytaj_reguly()
    assert len(reguly) >= 7
    identyfikatory = {r["id"] for r in reguly}
    assert "apelacja_karna" in identyfikatory
    assert "zazalenie_karne" in identyfikatory


def test_regula_niesie_komplet_pol():
    silnik = mod_terminy.zbuduj_silnik()
    regula = silnik._reguly["apelacja_karna"]
    assert regula.dlugosc_dni == 14
    assert "445" in regula.podstawa
    assert regula.zdarzenie == "doreczenie_wyroku_z_uzasadnieniem"


def test_blok_zwijany_yaml_wczytany_jako_tekst():
    """Pole `uwaga` bywa blokiem `>` na kilku wierszach."""
    silnik = mod_terminy.zbuduj_silnik()
    assert "WERYFIKACJI" in silnik._reguly["apelacja_karna"].uwaga


def test_niekompletna_regula_odrzucona(tmp_path=None):
    """⚠️ Reguła wczytana błędnie jest groźniejsza od niewczytanej.

    Niewczytana jest widoczna. Wczytana błędnie podaje złą datę
    z pełnym przekonaniem.
    """
    plik = KORZEN / "eval" / "_reguly_niepelne.yaml"
    plik.write_text(
        "reguly:\n"
        "  - id: bez_podstawy\n"
        "    zdarzenie: ogloszenie_wyroku\n"
        "    dlugosc_dni: 7\n"
        "    liczenie: od_dnia_nastepnego\n"
        "    dni_wolne: bez_przesuniecia\n",
        encoding="utf-8")
    try:
        with pytest.raises(mod_terminy.BladRegul) as info:
            mod_terminy.zbuduj_silnik(plik)
        assert "podstawa" in str(info.value)
    finally:
        plik.unlink()


def test_pusty_katalog_regul_to_blad():
    plik = KORZEN / "eval" / "_reguly_puste.yaml"
    plik.write_text("reguly:\n", encoding="utf-8")
    try:
        with pytest.raises(mod_terminy.BladRegul):
            mod_terminy.czytaj_reguly(plik)
    finally:
        plik.unlink()


# ── liczenie ─────────────────────────────────────────────────────────

def test_termin_liczony_od_dnia_nastepnego():
    """14 dni od doręczenia 1 czerwca 2026 to 15 czerwca (poniedziałek)."""
    wynik = mod_terminy.policz("apelacja_karna", "2026-06-01")
    assert wynik["data_uplywu"] == "2026-06-15"
    assert wynik["dni"] == 14


def test_termin_przesuwany_z_bozego_ciala():
    """⚠️ TEST, DLA KTÓREGO POWSTAŁO WYLICZANIE ŚWIĄT.

    Doręczenie 21 maja 2026 + 14 dni daje 4 czerwca — Boże Ciało.
    Bez wykazu świąt system podałby tę datę jako upływ terminu.
    """
    wynik = mod_terminy.policz("apelacja_karna", "2026-05-21")
    assert wynik["data_uplywu"] == "2026-06-05"
    assert any("wolny" in o for o in wynik["ostrzezenia"])


def test_termin_przesuwany_z_weekendu():
    wynik = mod_terminy.policz("zazalenie_karne", "2026-08-14")
    upływ = date.fromisoformat(wynik["data_uplywu"])
    assert upływ.weekday() < 5


def test_regula_bez_podpisu_nie_jest_wiazaca():
    """⚠️ WARUNEK Z ADR-0005, NIE OZDOBNIK.

    Katalog reguł jest szkicem: podstawy prawne wymagają sprawdzenia
    co do brzmienia. Dopóki nikt się pod nimi nie podpisał, termin ma
    być informacyjny — i musi to mówić wprost.
    """
    wynik = mod_terminy.policz("apelacja_karna", "2026-06-01")
    assert wynik["status"] == "niezatwierdzona_regula"
    assert wynik["wiazacy"] is False
    assert any("NIE ZOSTAŁA ZATWIERDZONA" in o for o in wynik["ostrzezenia"])


def test_nieznana_regula_odrzucona():
    with pytest.raises(mod_terminy.BladRegul):
        mod_terminy.policz("nie_ma_takiej", "2026-06-01")


def test_zla_data_odrzucona_z_komunikatem():
    with pytest.raises(mod_terminy.BladRegul) as info:
        mod_terminy.policz("apelacja_karna", "1 czerwca 2026")
    assert "RRRR-MM-DD" in str(info.value)


def test_liczenie_jest_powtarzalne():
    """Ta sama data przy każdym wywołaniu — na tym polega ADR-0005."""
    wyniki = {mod_terminy.policz("apelacja_karna", "2026-05-21")["data_uplywu"]
              for _ in range(5)}
    assert len(wyniki) == 1


def test_katalog_pokazuje_stan_zatwierdzenia():
    katalog = mod_terminy.katalog()
    assert katalog
    assert all("zatwierdzona" in r for r in katalog)
    # Niezatwierdzone na górze — prawnik ma je zobaczyć, a nie przewijać.
    assert katalog[0]["zatwierdzona"] is False
