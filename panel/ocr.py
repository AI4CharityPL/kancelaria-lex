"""Rozpoznawanie pisma ze skanów (OCR) — Tesseract, lokalnie.

════════════════════════════════════════════════════════════════════════
 PO CO
════════════════════════════════════════════════════════════════════════

Na 173 rzeczywistych PDF-ach zmierzonych 19.08.2026 czternaście nie ma
warstwy tekstowej w ogóle, a dalsze kilkadziesiąt ma fonty, których nie
da się wiarygodnie odczytać bez pełnego rozbioru kodowań PDF-a. Dla obu
grup OCR jest właściwą odpowiedzią — a `wczytywanie.py` i tak je już
rozpoznaje i odrzuca.

════════════════════════════════════════════════════════════════════════
 ⚠️ OCR ZMIENIA CHARAKTER GŁÓWNEJ GWARANCJI SYSTEMU
════════════════════════════════════════════════════════════════════════

Obietnica brzmi: „cytat prowadzi do konkretnego znaku w aktach". Przy
dokumencie z OCR-u prawdziwe zdanie brzmi inaczej:

    cytat prowadzi do konkretnego znaku W ODCZYCIE SKANU

a odczyt bywa różny od pisma. Nawet dobry OCR myli 1 z l, 0 z O i gubi
znaki w pieczątkach — czyli akurat w sygnaturach, kwotach i datach,
na których stoją wyróżniki i terminy procesowe.

Dlatego dokument wczytany tą drogą dostaje TRWAŁY ZNACZNIK pochodzenia,
a każdy cytat z niego — ostrzeżenie „sprawdź przy oryginale". Bez tego
system obiecywałby dokładność, której przy skanie nie ma.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TESSERACT JAKO PROGRAM, A NIE BIBLIOTEKA
════════════════════════════════════════════════════════════════════════

Panel korzysta wyłącznie z biblioteki standardowej (art. 21 ust. 2
lit. d ustawy o KSC). `pytesseract` czy `pdf2image` byłyby nowymi
zależnościami Pythona; Tesseract wywoływany jako osobny proces nie jest
— tak samo jak Ollama, od której panel zależy od początku.

⚠️ POLSKI JEST WYMAGANY, ANGIELSKI NIE WYSTARCZY.
   Zmierzone 19.08.2026 na zdaniu z polskiego postanowienia:

       pol:  Sąd Okręgowy … oddalił wniosek obrońcy o dopuszczenie
       eng:  Sad Okregowy … oddalit wniosek obroncy 0 dopuszezenie

   Angielski „działa" i zwraca tekst wyglądający poprawnie — bez ani
   jednego znaku diakrytycznego, z zerem zamiast litery o i przekręconym
   „dopuszezenie". To jest dokładnie ten rodzaj cichego zepsucia,
   przed którym broni bramka jakości. Brak polskiego pakietu to więc
   ODMOWA, nie zejście na angielski.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]

# Dane językowe trzymamy przy projekcie, nie w Program Files: instalacja
# nie wymaga wtedy uprawnień administratora, a wersja jest przypięta sumą
# kontrolną w `models/manifest.md`.
TESSDATA = KORZEN / "models" / "tessdata"

# Kolejność szukania: PATH, potem typowe miejsca instalacji na Windows.
KANDYDACI = (
    "tesseract",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

JEZYKI = {"pl": "pol", "en": "eng"}

# Skan strony A4 przy 300 dpi to kilkanaście sekund pracy procesora.
TIMEOUT_S = 300


class BladOCR(RuntimeError):
    """OCR nie mógł się wykonać — do pokazania użytkownikowi wprost."""


@dataclass
class WynikOCR:
    tekst: str
    stron: int = 0
    jezyk: str = "pol"
    ostrzezenia: list[str] = field(default_factory=list)


# ── dostępność ───────────────────────────────────────────────────────

def sciezka_programu() -> str | None:
    for kandydat in KANDYDACI:
        if os.sep in kandydat:
            if Path(kandydat).exists():
                return kandydat
            continue
        znaleziony = shutil.which(kandydat)
        if znaleziony:
            return znaleziony
    return None


def _srodowisko() -> dict:
    srodowisko = dict(os.environ)
    if TESSDATA.exists():
        srodowisko["TESSDATA_PREFIX"] = str(TESSDATA)
    return srodowisko


def jezyki_dostepne() -> set[str]:
    program = sciezka_programu()
    if not program:
        return set()
    try:
        wynik = subprocess.run([program, "--list-langs"], capture_output=True,
                               text=True, env=_srodowisko(), timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {w.strip() for w in (wynik.stdout or "").splitlines()
            if w.strip() and " " not in w.strip()}


def stan() -> dict:
    """Stan OCR do pokazania w panelu — bez zgadywania."""
    program = sciezka_programu()
    jezyki = jezyki_dostepne() if program else set()
    return {
        "dostepny": bool(program) and "pol" in jezyki,
        "program": program or "",
        "jezyki": sorted(jezyki),
        "polski": "pol" in jezyki,
        "tessdata": str(TESSDATA) if TESSDATA.exists() else "",
    }


# ── obrazy osadzone w PDF ────────────────────────────────────────────
#
# ⚠️ WYDOBYWAMY OBRAZY ZAMIAST RENDEROWAĆ STRONĘ.
#
# Renderowanie PDF-a wymaga silnika (poppler, Ghostscript) — kolejnego
# programu do przypięcia i pilnowania. Skan zapisany jako PDF ma jednak
# stronę BĘDĄCĄ obrazem, więc wystarczy ten obraz wyjąć:
#
#     /DCTDecode   — strumień JEST plikiem JPEG, zapisujemy go wprost
#     /FlateDecode — mapa bitowa; składamy z niej PNG, bo PNG to nagłówek
#                    plus te same dane spakowane zlibem
#
# Czego to NIE obsłuży: stron wektorowych, czyli PDF-ów z warstwą
# tekstową, której nie umiemy odczytać. Tam potrzebny byłby renderer
# i jest to zapisane wprost w ograniczeniach.

_OBIEKT = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.DOTALL)
_STRUMIEN = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)


def _liczba(slownik: bytes, klucz: bytes) -> int | None:
    m = re.search(klucz + rb"\s+(\d+)", slownik)
    return int(m.group(1)) if m else None


def _png_z_mapy(dane: bytes, szerokosc: int, wysokosc: int,
                kanaly: int, bitow: int) -> bytes | None:
    """Składa PNG z surowej mapy bitowej."""
    typ = {1: 0, 3: 2}.get(kanaly)          # 0 = szary, 2 = RGB; CMYK odpada
    if typ is None or bitow not in (1, 2, 4, 8):
        return None

    bajtow_na_wiersz = (szerokosc * kanaly * bitow + 7) // 8
    if len(dane) < bajtow_na_wiersz * wysokosc:
        return None

    # PNG wymaga bajtu filtra przed każdym wierszem.
    wiersze = bytearray()
    for y in range(wysokosc):
        wiersze.append(0)
        wiersze += dane[y * bajtow_na_wiersz:(y + 1) * bajtow_na_wiersz]

    def kawalek(nazwa: bytes, tresc: bytes) -> bytes:
        return (struct.pack(">I", len(tresc)) + nazwa + tresc
                + struct.pack(">I", zlib.crc32(nazwa + tresc) & 0xFFFFFFFF))

    naglowek = struct.pack(">IIBBBBB", szerokosc, wysokosc, bitow, typ, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + kawalek(b"IHDR", naglowek)
            + kawalek(b"IDAT", zlib.compress(bytes(wiersze), 6))
            + kawalek(b"IEND", b""))


def obrazy_z_pdf(dane: bytes, maks: int = 40) -> list[tuple[str, bytes]]:
    """Obrazy osadzone w PDF jako [(rozszerzenie, bajty)]."""
    wynik: list[tuple[str, bytes]] = []

    for _, _, cialo in _OBIEKT.findall(dane):
        if len(wynik) >= maks:
            break
        slownik = cialo.split(b"stream", 1)[0]
        if not re.search(rb"/Subtype\s*/Image", slownik):
            continue
        strumien = _STRUMIEN.search(cialo)
        if not strumien:
            continue
        surowy = strumien.group(1)

        if b"/DCTDecode" in slownik:
            wynik.append(("jpg", surowy))       # strumień JEST plikiem JPEG
            continue

        if b"/FlateDecode" not in slownik:
            continue
        try:
            mapa = zlib.decompress(surowy)
        except zlib.error:
            continue

        szerokosc = _liczba(slownik, rb"/Width")
        wysokosc = _liczba(slownik, rb"/Height")
        bitow = _liczba(slownik, rb"/BitsPerComponent") or 8
        if not szerokosc or not wysokosc:
            continue
        kanaly = (3 if b"/DeviceRGB" in slownik else
                  4 if b"/DeviceCMYK" in slownik else 1)

        png = _png_z_mapy(mapa, szerokosc, wysokosc, kanaly, bitow)
        if png:
            wynik.append(("png", png))

    return wynik


# ── rozpoznawanie ────────────────────────────────────────────────────

def z_obrazu(obraz: bytes, rozszerzenie: str = "png", jezyk: str = "pl") -> str:
    program = sciezka_programu()
    if not program:
        raise BladOCR(
            "Nie znaleziono programu Tesseract. OCR jest wyłączony — skany "
            "trzeba rozpoznać w osobnym narzędziu przed wgraniem.")

    kod = JEZYKI.get(jezyk, "pol")
    if kod not in jezyki_dostepne():
        raise BladOCR(
            f"Brak pakietu językowego {kod} dla Tesseracta. Rozpoznawanie "
            f"polskiego pisma bez niego daje tekst BEZ ZNAKÓW "
            f"DIAKRYTYCZNYCH, co czyni cytaty niewiarygodnymi — dlatego "
            f"odmawiamy zamiast schodzić na angielski.")

    with tempfile.TemporaryDirectory() as katalog:
        plik = Path(katalog) / f"strona.{rozszerzenie}"
        plik.write_bytes(obraz)
        try:
            wynik = subprocess.run(
                [program, str(plik), "stdout", "-l", kod],
                capture_output=True, env=_srodowisko(), timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired as e:
            raise BladOCR(f"Rozpoznawanie przekroczyło {TIMEOUT_S} s.") from e
        except OSError as e:
            raise BladOCR(f"Nie udało się uruchomić Tesseracta: {e}") from e

    if wynik.returncode != 0:
        raise BladOCR(
            "Tesseract zakończył się błędem: "
            + (wynik.stderr or b"").decode("utf-8", "replace").strip()[:200])
    return (wynik.stdout or b"").decode("utf-8", "replace")


def z_pdf(dane: bytes, jezyk: str = "pl") -> WynikOCR:
    """Rozpoznanie skanu zapisanego jako PDF."""
    obrazy = obrazy_z_pdf(dane)
    if not obrazy:
        raise BladOCR(
            "W tym PDF-ie nie ma obrazów możliwych do rozpoznania. Strony są "
            "wektorowe — plik ma warstwę tekstową, której nie da się "
            "odczytać, a nie skan. Zapisz go ponownie jako obraz albo wgraj "
            "w innym formacie.")

    czesci, ostrzezenia = [], []
    for rozszerzenie, obraz in obrazy:
        try:
            czesci.append(z_obrazu(obraz, rozszerzenie, jezyk))
        except BladOCR as e:
            ostrzezenia.append(str(e))

    if not czesci:
        raise BladOCR(
            "Żadnej ze stron nie udało się rozpoznać. "
            + (ostrzezenia[0] if ostrzezenia else ""))

    return WynikOCR(tekst="\n\n".join(czesci), stron=len(czesci),
                    jezyk=JEZYKI.get(jezyk, "pol"), ostrzezenia=ostrzezenia)
