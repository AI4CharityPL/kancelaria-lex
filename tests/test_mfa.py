"""Drugi składnik wpięty w profile i logowanie.

`test_totp.py` sprawdza sam algorytm wobec wektorów z RFC 6238.
Tutaj sprawdzamy to, czego tamten test nie widzi: czy drugi składnik
faktycznie STOI NA DRODZE do akt, czy tylko istnieje w bazie.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import profile as mod_profile  # noqa: E402
import totp  # noqa: E402

HASLO = "Praworzadnosc2026!"


@pytest.fixture
def db():
    polaczenie = baza.polacz(":memory:")
    yield polaczenie
    polaczenie.close()


@pytest.fixture
def anna(db):
    return mod_profile.zaloz(db, "a.kowalska", HASLO, "Anna", "Kowalska",
                             "prawnik",
                             zgody=[z["id"] for z in mod_profile.ZGODY])


# ── stan wyjściowy ───────────────────────────────────────────────────

def test_bez_mfa_logowanie_dziala_jak_dotad(db, anna):
    assert not mod_profile.wymaga_drugiego_skladnika(db, anna)
    assert mod_profile.uwierzytelnij(db, "a.kowalska", HASLO) is not None


def test_stan_mowi_ze_nie_jest_wlaczony(db, anna):
    stan = mod_profile.stan_mfa(db, anna.id)
    assert stan["wlaczony"] is False
    assert stan["przygotowany"] is False


# ── włączanie ────────────────────────────────────────────────────────

def test_przygotowanie_nie_wlacza_od_razu(db, anna):
    """⚠️ WŁĄCZENIE JEST DWUETAPOWE I TO NIE JEST OZDOBNIK.

    Włączenie przy samym wygenerowaniu sekretu zamykałoby dostęp do akt
    każdemu, kto źle przepisał kod QR — bez drogi powrotu, bo system
    nie ma poczty.
    """
    sekret, adres = mod_profile.przygotuj_mfa(db, anna)
    assert sekret and adres.startswith("otpauth://")
    assert not mod_profile.wymaga_drugiego_skladnika(db, anna)
    assert mod_profile.stan_mfa(db, anna.id)["przygotowany"] is True


def test_wlaczenie_wymaga_wlasciwego_kodu(db, anna):
    mod_profile.przygotuj_mfa(db, anna)
    with pytest.raises(mod_profile.BladDrugiegoSkladnika):
        mod_profile.wlacz_mfa(db, anna, "000000")
    assert not mod_profile.wymaga_drugiego_skladnika(db, anna)


def test_wlaczenie_kodem_z_aplikacji(db, anna):
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    kody = mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))

    assert mod_profile.wymaga_drugiego_skladnika(db, anna)
    assert len(kody) == totp.ILE_KODOW_ZAPASOWYCH
    assert mod_profile.stan_mfa(db, anna.id)["kodow_zapasowych"] == len(kody)


# ── sprawdzanie przy logowaniu ───────────────────────────────────────

def test_wlasciwy_kod_wpuszcza(db, anna):
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))
    assert mod_profile.sprawdz_drugi_skladnik(db, anna, totp.kod_teraz(sekret))


def test_zly_kod_nie_wpuszcza(db, anna):
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))
    assert not mod_profile.sprawdz_drugi_skladnik(db, anna, "000000")


def test_kod_zapasowy_dziala_raz(db, anna):
    """⚠️ Cały sens kodu zapasowego polega na tym, że działa RAZ.

    Kod z kartki wpuszczający wielokrotnie jest drugim hasłem — gorszym,
    bo krótszym i zapisanym na papierze.
    """
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    kody = mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))

    assert mod_profile.sprawdz_drugi_skladnik(db, anna, kody[0])
    assert not mod_profile.sprawdz_drugi_skladnik(db, anna, kody[0])
    assert mod_profile.stan_mfa(db, anna.id)["kodow_zapasowych"] == len(kody) - 1


def test_kody_zapasowe_dzialaja_niezaleznie(db, anna):
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    kody = mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))
    mod_profile.sprawdz_drugi_skladnik(db, anna, kody[0])
    assert mod_profile.sprawdz_drugi_skladnik(db, anna, kody[1])


def test_kod_zapasowy_lezy_w_bazie_jako_skrot(db, anna):
    """Baza wykradziona nie może dawać drogi obejścia drugiego składnika."""
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    kody = mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))
    zapisane = [w["skrot"] for w in db.execute(
        "SELECT skrot FROM kody_zapasowe WHERE profil_id = ?", (anna.id,))]
    assert kody[0] not in zapisane
    assert totp.skrot_kodu(kody[0]) in zapisane


# ── wyłączanie i ponowne włączanie ───────────────────────────────────

def test_wylaczenie_usuwa_takze_kody_zapasowe(db, anna):
    sekret, _ = mod_profile.przygotuj_mfa(db, anna)
    mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(sekret))
    mod_profile.wylacz_mfa(db, anna)

    assert not mod_profile.wymaga_drugiego_skladnika(db, anna)
    assert mod_profile.stan_mfa(db, anna.id)["kodow_zapasowych"] == 0


def test_ponowne_przygotowanie_uniewaznia_stary_sekret(db, anna):
    stary, _ = mod_profile.przygotuj_mfa(db, anna)
    mod_profile.wlacz_mfa(db, anna, totp.kod_teraz(stary))

    nowy, _ = mod_profile.przygotuj_mfa(db, anna)
    assert nowy != stary
    # Ponowne przygotowanie wyłącza drugi składnik do czasu potwierdzenia.
    assert not mod_profile.wymaga_drugiego_skladnika(db, anna)
