"""TOTP — drugi składnik uwierzytelniania.

Wektory kontrolne z RFC 6238 (Appendix B) sprawdzają, że implementacja
liczy to samo co aplikacja w telefonie prawnika. Bez nich „działa u mnie"
znaczy tylko tyle, że nasz kod zgadza się sam ze sobą.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import totp  # noqa: E402

# Sekret z RFC 6238: ASCII "12345678901234567890" w Base32.
SEKRET_RFC = base64.b32encode(b"12345678901234567890").decode().rstrip("=")


# ── zgodność z RFC 6238 ──────────────────────────────────────────────

def test_wektory_kontrolne_rfc6238():
    """⚠️ Bez tego testu nie wiadomo, czy telefon policzy ten sam kod.

    Wartości z RFC 6238 Appendix B dla SHA-1, przycięte do 6 cyfr.
    """
    for chwila, oczekiwany in ((59, "287082"),
                               (1111111109, "081804"),
                               (1111111111, "050471"),
                               (1234567890, "005924"),
                               (2000000000, "279037")):
        assert totp.kod_teraz(SEKRET_RFC, chwila) == oczekiwany, chwila


def test_kod_ma_szesc_cyfr():
    kod = totp.kod_teraz(totp.nowy_sekret())
    assert len(kod) == 6 and kod.isdigit()


def test_kod_zmienia_sie_co_okno():
    sekret = totp.nowy_sekret()
    assert totp.kod_teraz(sekret, 1000) != totp.kod_teraz(sekret, 1000 + totp.OKNO_S)


def test_kod_staly_w_obrebie_okna():
    """Okna są wyrównane do wielokrotności 30 s, nie liczone od zera.

    1000 i 1029 leżą w RÓŻNYCH oknach (33 i 34) — pierwsza wersja tego
    testu tego nie uwzględniała i padła, choć kod był poprawny.
    """
    sekret = totp.nowy_sekret()
    poczatek = 1020                       # 1020 // 30 == 34
    assert totp.kod_teraz(sekret, poczatek) == totp.kod_teraz(sekret, poczatek + 29)


# ── sprawdzanie ──────────────────────────────────────────────────────

def test_wlasciwy_kod_przechodzi():
    sekret = totp.nowy_sekret()
    assert totp.sprawdz(sekret, totp.kod_teraz(sekret, 5000), 5000)


def test_zly_kod_odrzucony():
    sekret = totp.nowy_sekret()
    assert not totp.sprawdz(sekret, "000000", 5000) or \
        totp.kod_teraz(sekret, 5000) == "000000"


def test_tolerancja_zegara_telefonu():
    """⚠️ Zegar telefonu odchodzi o kilkanaście sekund — to normalne.

    Bez tolerancji prawnik z lekko spóźnionym telefonem nie wejdzie
    do akt i nie będzie wiedział dlaczego. To najgorsza możliwa awaria
    w dniu rozprawy.
    """
    sekret = totp.nowy_sekret()
    kod_poprzedni = totp.kod_teraz(sekret, 5000 - totp.OKNO_S)
    kod_nastepny = totp.kod_teraz(sekret, 5000 + totp.OKNO_S)
    assert totp.sprawdz(sekret, kod_poprzedni, 5000)
    assert totp.sprawdz(sekret, kod_nastepny, 5000)


def test_kod_sprzed_dwoch_okien_odrzucony():
    """Tolerancja ma granicę — każde okno to 30 s więcej na zgadywanie."""
    sekret = totp.nowy_sekret()
    stary = totp.kod_teraz(sekret, 5000 - 3 * totp.OKNO_S)
    assert not totp.sprawdz(sekret, stary, 5000)


def test_kod_innego_sekretu_odrzucony():
    a, b = totp.nowy_sekret(), totp.nowy_sekret()
    assert not totp.sprawdz(a, totp.kod_teraz(b, 5000), 5000)


def test_smieci_odrzucane_bez_wyjatku():
    sekret = totp.nowy_sekret()
    for smiec in ("", "   ", "abcdef", "12345", "1234567", None, "12 34 56 78"):
        assert totp.sprawdz(sekret, smiec, 5000) is False


def test_spacje_w_kodzie_tolerowane():
    """Aplikacje pokazują kod jako „123 456" — prawnik przepisze ze spacją."""
    sekret = totp.nowy_sekret()
    kod = totp.kod_teraz(sekret, 5000)
    assert totp.sprawdz(sekret, f"{kod[:3]} {kod[3:]}", 5000)


# ── sekret i adres dla aplikacji ─────────────────────────────────────

def test_sekret_jest_base32_i_losowy():
    a, b = totp.nowy_sekret(), totp.nowy_sekret()
    assert a != b
    assert len(a) >= 32
    base64.b32decode(a + "=" * (-len(a) % 8))     # nie może rzucić


def test_adres_dla_aplikacji_ma_komplet_pol():
    adres = totp.adres_do_aplikacji("ABCDEFGH", "a.kowalska")
    assert adres.startswith("otpauth://totp/")
    for pole in ("secret=ABCDEFGH", "issuer=kancelaria-lex",
                 "digits=6", "period=30"):
        assert pole in adres


# ── kody zapasowe ────────────────────────────────────────────────────

def test_kody_zapasowe_sa_rozne_i_czytelne():
    kody = totp.nowe_kody_zapasowe()
    assert len(kody) == totp.ILE_KODOW_ZAPASOWYCH
    assert len(set(kody)) == len(kody)
    assert all("-" in k for k in kody)      # do przepisania z kartki


def test_skrot_kodu_niezalezny_od_zapisu():
    """Prawnik przepisze kod z kartki — wielkość liter i spacje bez znaczenia."""
    assert totp.skrot_kodu("ab12-cd34") == totp.skrot_kodu(" AB12-CD34 ")


def test_skrot_nie_odtwarza_kodu():
    kod = totp.nowe_kody_zapasowe(1)[0]
    assert kod not in totp.skrot_kodu(kod)
