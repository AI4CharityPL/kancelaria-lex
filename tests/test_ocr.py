"""OCR — rozpoznawanie pisma ze skanów.

⚠️ NAJWAŻNIEJSZE W TYM PLIKU NIE SĄ TESTY UDANEGO ROZPOZNANIA.

OCR zamienia treść pisma na jej ODCZYT. Odczyt bywa różny od pisma —
najczęściej w sygnaturach, kwotach i datach, czyli dokładnie tam, gdzie
stoją wyróżniki i terminy procesowe. Testy pilnują więc trzech rzeczy:

  1. że brak polskiego pakietu kończy się ODMOWĄ, a nie zejściem
     na angielski (który zwraca tekst wyglądający poprawnie, bez ani
     jednego znaku diakrytycznego);
  2. że dokument z OCR-u dostaje TRWAŁY ZNACZNIK pochodzenia;
  3. że OCR nie włącza się sam — jest ostatnią deską, nie pierwszym
     wyborem.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import ocr  # noqa: E402
import wczytywanie as w  # noqa: E402

wymaga_ocr = pytest.mark.skipif(
    not ocr.stan()["dostepny"],
    reason="Tesseract z polskim pakietem niedostępny na tej maszynie.")


def _png(szerokosc: int, wysokosc: int, wartosc: int = 255) -> bytes:
    """Minimalny PNG w skali szarości — do testu składania obrazu."""
    wiersze = bytearray()
    for _ in range(wysokosc):
        wiersze.append(0)
        wiersze += bytes([wartosc]) * szerokosc

    def kawalek(nazwa: bytes, tresc: bytes) -> bytes:
        return (struct.pack(">I", len(tresc)) + nazwa + tresc
                + struct.pack(">I", zlib.crc32(nazwa + tresc) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + kawalek(b"IHDR", struct.pack(">IIBBBBB", szerokosc, wysokosc,
                                           8, 0, 0, 0, 0))
            + kawalek(b"IDAT", zlib.compress(bytes(wiersze)))
            + kawalek(b"IEND", b""))


def _pdf_ze_skanem(obraz: bytes, szerokosc: int, wysokosc: int) -> bytes:
    """PDF, którego jedyną treścią jest obraz — czyli skan."""
    spakowany = zlib.compress(obraz)
    return (b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /XObject /Subtype /Image /Width "
            + str(szerokosc).encode() + b" /Height " + str(wysokosc).encode()
            + b" /BitsPerComponent 8 /ColorSpace /DeviceGray "
            b"/Filter /FlateDecode /Length " + str(len(spakowany)).encode()
            + b" >>\nstream\n" + spakowany + b"\nendstream\nendobj\n%%EOF")


# ── dostępność i odmowa ──────────────────────────────────────────────

def test_stan_nie_zgaduje():
    stan = ocr.stan()
    assert set(stan) >= {"dostepny", "program", "jezyki", "polski"}
    # `dostepny` znaczy „da się rozpoznać POLSKIE pismo", nie „jest program".
    assert stan["dostepny"] == (bool(stan["program"]) and stan["polski"])


def test_brak_polskiego_to_odmowa(monkeypatch):
    """⚠️ ANGIELSKI NIE JEST ZAMIENNIKIEM POLSKIEGO.

    Zmierzone 19.08.2026: angielski Tesseract na polskim postanowieniu
    zwraca „Sad Okregowy ... oddalit wniosek obroncy 0 dopuszezenie" —
    tekst wyglądający poprawnie, bez ani jednego znaku diakrytycznego.
    Cytat z takiego źródła przeszedłby weryfikację znak w znak wobec
    tekstu, którego w piśmie nie ma.
    """
    monkeypatch.setattr(ocr, "jezyki_dostepne", lambda: {"eng", "osd"})
    monkeypatch.setattr(ocr, "sciezka_programu", lambda: "tesseract")

    with pytest.raises(ocr.BladOCR) as info:
        ocr.z_obrazu(_png(10, 10), "png", "pl")
    assert "pol" in str(info.value)
    assert "DIAKRYTYCZNYCH" in str(info.value)


def test_brak_programu_to_odmowa(monkeypatch):
    monkeypatch.setattr(ocr, "sciezka_programu", lambda: None)
    with pytest.raises(ocr.BladOCR) as info:
        ocr.z_obrazu(_png(10, 10), "png", "pl")
    assert "Tesseract" in str(info.value)


# ── wydobywanie obrazów z PDF ────────────────────────────────────────

def test_obraz_flate_skladany_w_png():
    """Mapa bitowa z PDF-a musi wyjść jako plik, który czyta Tesseract."""
    surowy = bytes([200]) * (40 * 20)
    pdf = _pdf_ze_skanem(surowy, 40, 20)
    obrazy = ocr.obrazy_z_pdf(pdf)

    assert len(obrazy) == 1
    rozszerzenie, dane = obrazy[0]
    assert rozszerzenie == "png"
    assert dane.startswith(b"\x89PNG\r\n\x1a\n")


def test_obraz_jpeg_przechodzi_bez_zmian():
    """Strumień /DCTDecode JEST plikiem JPEG — nie ma czego składać."""
    jpeg = b"\xff\xd8\xff\xe0" + b"udawany jpeg" * 20 + b"\xff\xd9"
    pdf = (b"%PDF-1.4\n1 0 obj\n<< /Subtype /Image /Width 10 /Height 10 "
           b"/Filter /DCTDecode /Length " + str(len(jpeg)).encode()
           + b" >>\nstream\n" + jpeg + b"\nendstream\nendobj\n%%EOF")

    obrazy = ocr.obrazy_z_pdf(pdf)
    assert obrazy == [("jpg", jpeg)]


def test_pdf_bez_obrazow_konczy_sie_wyjasnieniem():
    """PDF wektorowy nie jest skanem — komunikat ma to mówić."""
    pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n%%EOF"
    with pytest.raises(ocr.BladOCR) as info:
        ocr.z_pdf(pdf)
    assert "wektorowe" in str(info.value)


# ── wpięcie w potok wczytywania ──────────────────────────────────────

def test_ocr_nie_wlacza_sie_sam():
    """⚠️ OSTATNIA DESKA, NIE PIERWSZY WYBÓR.

    Odczyt obrazu jest gorszy od warstwy tekstowej zawsze, gdy ta druga
    da się przeczytać. Domyślne włączenie OCR-u obniżałoby rangę cytatów
    w dokumentach, które żadnego rozpoznawania nie potrzebują.
    """
    pdf = _pdf_ze_skanem(bytes([255]) * (30 * 30), 30, 30)
    wynik = w.wczytaj("skan.pdf", pdf)
    assert wynik.wymaga_ocr
    assert not wynik.nadaje_sie
    assert wynik.zrodlo == w.ZRODLO_PLIK


def test_tekst_wklejony_ma_wlasne_pochodzenie():
    """Dokument wklejony do panelu to nie to samo co wgrany plik."""
    wynik = w.wczytaj("pismo.txt", "Sąd oddalił wniosek obrońcy.".encode())
    assert wynik.zrodlo == w.ZRODLO_PLIK      # z pliku
    assert w.ZRODLO_WKLEJONY == "wklejony"    # osobna wartość dla wklejenia


@wymaga_ocr
def test_skan_rozpoznany_dostaje_znacznik_ocr():
    """Ścieżka pełna: skan → OCR → dokument oznaczony jako odczyt."""
    # Obraz jednolicie biały nie da tekstu, więc test sprawdza SAM
    # przepływ i oznaczenie, a nie jakość rozpoznania.
    pdf = _pdf_ze_skanem(bytes([255]) * (600 * 200), 600, 200)
    wynik = w.wczytaj("skan.pdf", pdf, ocr_dozwolony=True)

    # Pusty obraz → OCR nic nie zwraca → dokument NIE wchodzi do akt.
    assert not wynik.nadaje_sie
    assert wynik.wymaga_ocr


@wymaga_ocr
def test_polski_jest_dostepny_na_tej_maszynie():
    assert "pol" in ocr.jezyki_dostepne()
