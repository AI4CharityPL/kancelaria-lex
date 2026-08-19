"""Wczytywanie akt z plików — TXT, DOCX, PDF, RTF.

⚠️ NAJWAŻNIEJSZE W TYM PLIKU NIE SĄ TESTY UDANEGO WCZYTANIA.

Tekst wydobyty z pliku staje się ŹRÓDŁEM CYTATÓW: weryfikator porównuje
z nim cytat znak w znak. Jeżeli ekstrakcja przekręci polskie znaki,
cytat przejdzie weryfikację wobec zepsutego źródła i prawnik dostanie
w odpowiedzi tekst, którego w piśmie nie ma — zgodny znak w znak
i całkowicie fałszywy.

Testy odmowy są więc tu ważniejsze od testów sukcesu.
"""

from __future__ import annotations

import sys
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import wczytywanie as w  # noqa: E402

ZDANIE = ("Sąd Okręgowy w Warszawie postanowieniem z 14 września 2006 r. "
          "oddalił wniosek obrońcy o dopuszczenie dowodu z opinii biegłego. "
          "Zabezpieczenie ustalono na kwotę 1 008,00 zł, o czym pouczono "
          "strony na rozprawie.")


def _docx(tresc: str, akapity: list[str] | None = None) -> bytes:
    czesci = [tresc, *(akapity or [])]
    bufor = BytesIO()
    with zipfile.ZipFile(bufor, "w") as archiwum:
        archiwum.writestr("[Content_Types].xml", "<Types/>")
        akapity_xml = "".join(
            f"<w:p><w:r><w:t>{a}</w:t></w:r></w:p>" for a in czesci)
        archiwum.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            f'wordprocessingml/2006/main"><w:body>{akapity_xml}</w:body>'
            '</w:document>')
    return bufor.getvalue()


def _pdf(tekst_bajty: bytes) -> bytes:
    tresc = b"BT /F1 12 Tf (" + tekst_bajty + b") Tj ET"
    spakowana = zlib.compress(tresc)
    return (b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Page /Font << /F1 2 0 R >> >>\nendobj\n"
            b"2 0 obj\n<< /Type /Font /BaseFont /Helvetica >>\nendobj\n"
            b"3 0 obj\n<< /Length " + str(len(spakowana)).encode() +
            b" /Filter /FlateDecode >>\nstream\n" + spakowana +
            b"\nendstream\nendobj\n%%EOF")


# ── formaty tekstowe ─────────────────────────────────────────────────

def test_txt_utf8_odtwarza_tekst_co_do_znaku():
    wynik = w.wczytaj("pismo.txt", ZDANIE.encode("utf-8"))
    assert wynik.nadaje_sie
    assert wynik.tekst == ZDANIE          # znak w znak — od tego zależy cytat


def test_txt_cp1250_odzyskuje_polskie_znaki():
    """Pisma z polskiego Windowsa. Najczęstszy przypadek po UTF-8."""
    wynik = w.wczytaj("pismo.txt", ZDANIE.encode("cp1250"))
    assert wynik.nadaje_sie
    assert "Sąd" in wynik.tekst and "września" in wynik.tekst


def test_pusty_plik_odrzucony():
    with pytest.raises(w.BladWczytywania):
        w.wczytaj("puste.txt", b"")


def test_nieobslugiwany_format_odrzucony():
    with pytest.raises(w.BladWczytywania) as info:
        w.wczytaj("zdjecie.png", b"\x89PNG" + b"x" * 500)
    assert ".pdf" in str(info.value)      # komunikat mówi, co wolno


# ── DOCX ─────────────────────────────────────────────────────────────

def test_docx_wydobywa_tresc():
    wynik = w.wczytaj("pismo.docx", _docx(ZDANIE))
    assert wynik.nadaje_sie
    assert "Sąd Okręgowy" in wynik.tekst
    assert "1 008,00 zł" in wynik.tekst


def test_docx_akapit_konczy_sie_przelamaniem():
    """⚠️ Nie kosmetyka — od tego zależy numeracja zdań (ADR-0007).

    Sklejenie akapitów spacją tworzy zdanie, którego w piśmie nie ma,
    a model cytuje po NUMERZE zdania. Cytat wskazywałby wtedy twór
    powstały przy wczytywaniu.
    """
    wynik = w.wczytaj("pismo.docx", _docx("Pierwszy akapit.", ["Drugi akapit."]))
    assert "Pierwszy akapit.\n\nDrugi akapit." in wynik.tekst


def test_uszkodzony_docx_odrzucony_z_powodem():
    with pytest.raises(w.BladWczytywania) as info:
        w.wczytaj("pismo.docx", b"to nie jest zip")
    assert "DOCX" in str(info.value)


# ── PDF ──────────────────────────────────────────────────────────────

def test_pdf_wydobywa_tekst_i_polskie_znaki():
    wynik = w.wczytaj("pismo.pdf", _pdf(ZDANIE.encode("cp1250")))
    assert wynik.nadaje_sie
    assert "Sąd Okręgowy" in wynik.tekst
    assert "września" in wynik.tekst


def test_skan_bez_warstwy_tekstowej_jest_ODRZUCANY():
    """⚠️ Test odmowy, nie sukcesu.

    Skan wczytany jako pusty dokument byłby gorszy od braku funkcji:
    sprawa dostaje akta, których model nie widzi, a prawnik nie wie,
    że pytanie odbija się od pustego pliku.
    """
    skan = (b"%PDF-1.4\n1 0 obj\n<< /Type /XObject /Subtype /Image >>\n"
            b"endobj\n" + b"\x00" * 300_000)
    wynik = w.wczytaj("skan.pdf", skan)
    assert wynik.wymaga_ocr
    assert not wynik.nadaje_sie
    assert wynik.ostrzezenia


def test_pdf_zaszyfrowany_odrzucony_z_instrukcja():
    zaszyfrowany = (b"%PDF-1.4\n/Encrypt 9 0 R\n" + b"x" * 1000)
    with pytest.raises(w.BladWczytywania) as info:
        w.wczytaj("tajne.pdf", zaszyfrowany)
    assert "zaszyfrowany" in str(info.value).lower()


def test_za_duzy_plik_odrzucony():
    with pytest.raises(w.BladWczytywania):
        w.wczytaj("tom.pdf", b"x" * (w.MAKS_BAJTOW + 1))


# ── pomylona strona kodowa ───────────────────────────────────────────

def test_naprawa_cp1252_zamiast_cp1250():
    """⚠️ NAJGROŹNIEJSZY BŁĄD, BO NIEWIDOCZNY.

    Bajty polskiego pisma odczytane jako WinAnsi dają tekst złożony
    z POPRAWNYCH znaków, tyle że nie z tych. Bramka śmieci tego nie
    złapie — „¹" i „ê" są drukowalne.
    """
    zniekształcony = ZDANIE.encode("cp1250").decode("cp1252")
    assert "ą" not in zniekształcony            # potwierdzenie założenia

    naprawiony, czy = w.napraw_kodowanie(zniekształcony)
    assert czy
    assert "Sąd" in naprawiony and "września" in naprawiony


def test_naprawa_nie_rusza_zdrowego_tekstu():
    """Dokument, który po prostu zawiera „±" albo „¹", ma zostać jak jest."""
    zdrowy = ZDANIE + " Tolerancja ±5%."
    naprawiony, czy = w.napraw_kodowanie(zdrowy)
    assert not czy
    assert naprawiony == zdrowy


def test_wczytanie_naprawia_i_ostrzega():
    zniekształcony = ZDANIE.encode("cp1250").decode("cp1252")
    wynik = w.wczytaj("pismo.txt", zniekształcony.encode("utf-8"))
    assert wynik.nadaje_sie
    assert "Sąd" in wynik.tekst
    assert any("stronie kodowej" in o for o in wynik.ostrzezenia)


def test_nieodwracalne_znieksztalcenie_jest_odrzucane():
    """Gdy naprawa nie działa, dokument NIE wchodzi do akt."""
    smiec = "¹ê³¿æñ¶œŸ£¥¾¼¯¡Œ" * 40
    ostrzezenia, wymaga_ocr = w.ocen_jakosc(smiec, len(smiec), "tekst")
    assert wymaga_ocr
    assert "kodow" in ostrzezenia[0]


def test_znaki_sterujace_odrzucane():
    wynik = w.wczytaj("pismo.txt", (b"\x00\x01\x02\x03" * 200) + b"tekst")
    assert not wynik.nadaje_sie


# ── porządkowanie ────────────────────────────────────────────────────

def test_dzielenie_wyrazu_na_koncu_wiersza_sklejane():
    """PDF-y z sądu łamią wyrazy myślnikiem — cytat musi być całym słowem."""
    wynik = w.wczytaj("pismo.txt",
                      "postano-\nwienie sądu jest prawomocne.".encode("utf-8"))
    assert "postanowienie" in wynik.tekst


# ── znaki sterujące a długość w bazie ────────────────────────────────

def test_znaki_sterujace_usuwane_z_wczytanego_tekstu():
    """⚠️ USTERKA ZMIERZONA 19.08.2026 — DOKUMENT WYGLĄDAŁ NA PUSTY.

    Bajt NUL w treści ma skutek uboczny, którego nie widać: `LENGTH()`
    w SQLite zatrzymuje się na nim. Faktura o 2672 znakach, z pierwszym
    NUL-em na pozycji 31, pokazywała się na liście dokumentów jako
    `31 zn.` — treść była w bazie w całości, ale prawnik patrzył na
    pozycję wyglądającą na pustą i nie miał powodu jej otwierać.
    """
    tekst = "Sąd oddalił wniosek\x00 obrońcy\x01 o dopuszczenie dowodu."
    wynik = w.wczytaj("pismo.txt", tekst.encode("utf-8"))

    assert wynik.nadaje_sie
    assert "\x00" not in wynik.tekst
    assert "\x01" not in wynik.tekst
    assert "Sąd oddalił wniosek" in wynik.tekst


def test_usuniecie_znakow_jest_zglaszane():
    """Dokument niepełny musi o tym mówić — brak treści jest niewidoczny."""
    tekst = "Treść pisma procesowego" + "\x00" * 5 + " ciąg dalszy."
    wynik = w.wczytaj("pismo.txt", tekst.encode("utf-8"))
    assert any("NIEPEŁNY" in o for o in wynik.ostrzezenia)


def test_zdrowy_tekst_nie_dostaje_ostrzezenia():
    wynik = w.wczytaj("pismo.txt", ZDANIE.encode("utf-8"))
    assert not any("NIEPEŁNY" in o for o in wynik.ostrzezenia)
    assert wynik.tekst == ZDANIE


def test_usun_sterujace_liczy_ile_usunelo():
    oczyszczony, ile = w.usun_sterujace("a\x00b\x01c\x1fd")
    assert oczyszczony == "abcd"
    assert ile == 3


def test_tabulator_i_nowa_linia_zostaja():
    """Nie każdy znak poniżej spacji to śmieć — układ tekstu ma znaczenie."""
    oczyszczony, ile = w.usun_sterujace("wiersz\tkolumna\nnastępny")
    assert oczyszczony == "wiersz\tkolumna\nnastępny"
    assert ile == 0
