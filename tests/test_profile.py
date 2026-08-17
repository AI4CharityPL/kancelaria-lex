"""Profile lokalne — logowanie, sesje, rozdzielenie autorstwa.

TŁO — zmierzona luka, nie hipoteza.
    Do 16.08.2026 ekran logowania zapisywał imię i rolę do `localStorage`
    przeglądarki i się chował. W panelu nie było ani tabeli użytkowników,
    ani weryfikacji hasła, ani sesji — a `wiadomosci` nie miały kolumny
    autora. Skutki: każdy, kto pominął interfejs i uderzył prosto w API,
    dostawał akta; a dwie osoby na jednej sprawie dzieliły jedną historię
    bez śladu, kto o co pytał.

    Te testy pilnują, żeby żadna z tych rzeczy nie wróciła.
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


KOMPLET = list(mod_profile.WYMAGANE_ZGODY)


@pytest.fixture()
def anna(db):
    return mod_profile.zaloz(db, "a.kowalska", "tajne-haslo-123",
                             "Anna", "Kowalska", "prawnik", zgody=KOMPLET)


# ── oświadczenia o obowiązkach kancelarii ───────────────────────────
#
# Część obowiązków prawnych ciąży na PODMIOCIE i żadne oprogramowanie ich
# nie wykona. Komplet oświadczeń jest warunkiem założenia konta, a
# sprawdzenie MUSI stać po stronie serwera — lista zaznaczeń przysłana
# z przeglądarki jest danymi, nie dowodem.

@pytest.mark.parametrize("zgody", [None, [], ["weryfikacja"]])
def test_brak_kompletu_zgod_blokuje_zalozenie(db, zgody):
    with pytest.raises(mod_profile.BladProfilu):
        mod_profile.zaloz(db, "b.nowak", "haslo-do-testu-1", "Bartosz",
                          "Nowak", "prawnik", zgody=zgody)


def test_niemal_komplet_tez_blokuje(db):
    """Jedno pominięte oświadczenie wystarczy, żeby odmówić."""
    bez_jednego = [z for z in KOMPLET if z != "ksc"]
    with pytest.raises(mod_profile.BladProfilu) as e:
        mod_profile.zaloz(db, "c.wisniewska", "haslo-do-testu-1", "Celina",
                          "Wiśniewska", "aplikant", zgody=bez_jednego)
    # Komunikat ma NAZYWAĆ brakujące, a nie mówić ogólnie „brak zgód".
    assert "KSC" in str(e.value)


def test_zgody_zapisane_z_wersja(db, anna):
    """Sam fakt „przyjął" nie wystarcza — bez wersji nie wiadomo, CO widział."""
    wiersz = db.execute("SELECT * FROM profile WHERE id = ?",
                        (anna.id,)).fetchone()
    assert wiersz["zgody_wersja"] == mod_profile.ZGODY_WERSJA
    assert wiersz["zgody_czas"]


def test_kazde_oswiadczenie_ma_podstawe_prawna(db):
    """Oświadczenie bez wskazania przepisu jest dla użytkownika pustym
    zobowiązaniem — ma wiedzieć, z czego obowiązek wynika."""
    for z in mod_profile.ZGODY:
        assert z["id"] and z["tytul"] and z["tresc"]
        assert z["podstawa"], f"{z['id']} bez podstawy prawnej"
        assert len(z["tresc"]) > 60, f"{z['id']}: treść zbyt ogólna"


# ── hasło ───────────────────────────────────────────────────────────

def test_haslo_nie_jest_zapisane_jawnie(db, anna):
    """Najprostszy test, jaki tu może być — i najważniejszy."""
    wiersz = db.execute("SELECT * FROM profile WHERE id = ?", (anna.id,)).fetchone()
    assert b"tajne-haslo-123" not in bytes(wiersz["skrot"])
    assert "tajne-haslo-123" not in str(dict(wiersz))


def test_ten_sam_haslo_daje_rozne_skroty(db):
    """Sól per profil — dwa identyczne hasła nie mogą dać tego samego skrótu,
    bo inaczej tęczowa tablica rozbija całą bazę naraz."""
    a = mod_profile.zaloz(db, "a.nowak", "identyczne-haslo", "A", "N",
                          "prawnik", zgody=KOMPLET)
    b = mod_profile.zaloz(db, "b.nowak", "identyczne-haslo", "B", "N",
                          "aplikant", zgody=KOMPLET)
    skrot_a = db.execute("SELECT skrot FROM profile WHERE id=?", (a.id,)).fetchone()[0]
    skrot_b = db.execute("SELECT skrot FROM profile WHERE id=?", (b.id,)).fetchone()[0]
    assert skrot_a != skrot_b


def test_poprawne_haslo_wpuszcza(db, anna):
    assert mod_profile.uwierzytelnij(db, "a.kowalska", "tajne-haslo-123") is not None


@pytest.mark.parametrize("login,haslo", [
    ("a.kowalska", "zle-haslo-000"),
    ("a.kowalska", ""),
    ("nie.istnieje", "tajne-haslo-123"),
])
def test_zle_dane_nie_wpuszczaja(db, anna, login, haslo):
    assert mod_profile.uwierzytelnij(db, login, haslo) is None


def test_login_bez_wzgledu_na_wielkosc_liter(db, anna):
    assert mod_profile.uwierzytelnij(db, "A.Kowalska", "tajne-haslo-123") is not None


def test_duplikat_loginu_odrzucony(db, anna):
    with pytest.raises(mod_profile.BladProfilu):
        mod_profile.zaloz(db, "a.kowalska", "inne-haslo-456", "Anna", "K", "aplikant")


@pytest.mark.parametrize("login,haslo,imie,nazwisko,rola", [
    ("ab", "dlugie-haslo-123", "A", "B", "prawnik"),            # login za krótki
    ("a.kowalska", "krotkie", "A", "B", "prawnik"),             # hasło za krótkie
    ("a.kowalska", "a.kowalska", "A", "B", "prawnik"),          # hasło = login
    ("a.kowalska", "dlugie-haslo-123", "", "B", "prawnik"),     # brak imienia
    ("a.kowalska", "dlugie-haslo-123", "A", "B", "szef"),       # rola spoza listy
    ("A.Kowalska!", "dlugie-haslo-123", "A", "B", "prawnik"),   # znaki spoza zakresu
])
def test_walidacja_odrzuca(db, login, haslo, imie, nazwisko, rola):
    with pytest.raises(mod_profile.BladProfilu):
        mod_profile.zaloz(db, login, haslo, imie, nazwisko, rola)


# ── sesje ───────────────────────────────────────────────────────────

def test_sesja_zwraca_ten_sam_profil(db, anna):
    token = mod_profile.otworz_sesje(db, anna)
    z_sesji = mod_profile.z_sesji(db, token)
    assert z_sesji is not None and z_sesji.id == anna.id


@pytest.mark.parametrize("token", [None, "", "zmyslony-token"])
def test_brak_lub_zly_token_nie_daje_profilu(db, anna, token):
    assert mod_profile.z_sesji(db, token) is None


def test_wylogowanie_uniewaznia_sesje(db, anna):
    """Wylogowanie musi kasować sesję po stronie SERWERA.

    Chowanie ekranu w przeglądarce zostawiłoby token ważny — czyli
    dokładnie ten błąd, który ta warstwa naprawia.
    """
    token = mod_profile.otworz_sesje(db, anna)
    mod_profile.zamknij_sesje(db, token)
    assert mod_profile.z_sesji(db, token) is None


def test_wygasla_sesja_nie_wpuszcza(db, anna):
    token = mod_profile.otworz_sesje(db, anna)
    db.execute("UPDATE sesje SET wygasa = ? WHERE token = ?",
               ("2000-01-01T00:00:00+00:00", token))
    db.commit()
    assert mod_profile.z_sesji(db, token) is None


def test_dwa_logowania_daja_rozne_tokeny(db, anna):
    assert mod_profile.otworz_sesje(db, anna) != mod_profile.otworz_sesje(db, anna)


# ── autorstwo wiadomości ────────────────────────────────────────────

def test_historia_niesie_autora(db, anna):
    """Bez tego dwie osoby na jednej sprawie dzielą historię bez śladu,
    kto o co pytał — a to był wprost postawiony wymóg."""
    sprawa_id = baza.dodaj_sprawe(db, "II K 1/26", "Sprawa testowa")
    baza.dodaj_wiadomosc(db, sprawa_id, "uzytkownik", "Pytanie?",
                         profil_id=anna.id)
    wpis = baza.historia(db, sprawa_id)[0]
    assert wpis["profil_id"] == anna.id
    assert wpis["autor_nazwisko"] == "Kowalska"
    assert wpis["autor_rola"] == "prawnik"


def test_wiadomosc_bez_profilu_zostaje_bez_autora(db):
    """Wpisy sprzed wprowadzenia profili mają autora pustego i mają
    takie zostać — autorstwa wstecz nie znamy i nie wolno go zmyślić."""
    sprawa_id = baza.dodaj_sprawe(db, "II K 2/26", "Sprawa testowa")
    baza.dodaj_wiadomosc(db, sprawa_id, "uzytkownik", "Stare pytanie?")
    wpis = baza.historia(db, sprawa_id)[0]
    assert wpis["profil_id"] is None
    assert wpis["autor_nazwisko"] is None
