"""Wczytywanie akt z plików — TXT, MD, DOCX, PDF.

════════════════════════════════════════════════════════════════════════
 PO CO TO POWSTAŁO
════════════════════════════════════════════════════════════════════════

Do 16.08.2026 panel nie miał ANI JEDNEGO pola wyboru pliku. Akta trzeba
było wkleić do pola tekstowego. Realne akta to PDF-y, skany i pisma
w DOCX — więc cały system, mimo działającego cytowania i weryfikacji,
pozostawał demonstracją, a nie narzędziem pracy.

════════════════════════════════════════════════════════════════════════
 ZASADA NADRZĘDNA: LEPIEJ ODMÓWIĆ NIŻ PODAĆ ŚMIECI
════════════════════════════════════════════════════════════════════════

Tekst wydobyty z pliku staje się ŹRÓDŁEM CYTATÓW. Weryfikator porównuje
cytat z tym tekstem znak w znak, więc jeśli ekstrakcja przekręci choćby
polskie znaki, cały łańcuch gwarancji rozsypuje się po cichu: cytat
przejdzie weryfikację wobec zepsutego źródła i prawnik dostanie
w odpowiedzi tekst, którego w piśmie nie ma.

To jest gorsze niż brak funkcji. Dlatego każda ścieżka kończy się
BRAMKĄ JAKOŚCI (`ocen_jakosc`), a wynik niesie wprost, czy nadaje się
do użycia. Skan bez warstwy tekstowej jest odrzucany z jednoznacznym
komunikatem, a nie wczytywany jako pusty dokument.

════════════════════════════════════════════════════════════════════════
 DLACZEGO BEZ BIBLIOTEK ZEWNĘTRZNYCH
════════════════════════════════════════════════════════════════════════

Panel korzysta wyłącznie z biblioteki standardowej — łańcuch dostaw
aplikacji jest pusty (art. 21 ust. 2 lit. d ustawy o KSC). Dołożenie
`pypdf` czy `python-docx` oznaczałoby dwie nowe zależności w systemie,
który przetwarza akta spraw karnych, i unieważniałoby argument
powtarzany w całej dokumentacji.

    DOCX  — to ZIP z XML-em. `zipfile` + `xml.etree` w zupełności starczy.
    PDF   — strumienie skompresowane `zlib`, też w bibliotece standardowej.
    OCR   — NIE tutaj. OCR wymaga silnika (Tesseract/RapidOCR), który
            należy do stosu kontenerowego, nie do panelu. Skany są
            rozpoznawane i odsyłane z instrukcją, zamiast udawać, że
            zostały wczytane.

⚠️ CZEGO TEN MODUŁ NIE UMIE — zapisane wprost:
   · PDF-ów będących skanem (brak warstwy tekstowej) — patrz wyżej;
   · PDF-ów z szyfrowaniem;
   · układu dwukolumnowego — kolejność tekstu może się przeplatać;
   · tabel — struktura kolumn nie jest odtwarzana.
   Pierwsze dwa są WYKRYWANE i zgłaszane. Dwa kolejne nie dają się
   wykryć mechanicznie i są wypisane w interfejsie przy wgrywaniu.
"""

from __future__ import annotations

import re
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass, field
from io import BytesIO
from xml.etree import ElementTree

# Górny limit pojedynczego pliku. Akta bywają duże, ale plik powyżej tej
# granicy to zwykle skan całego tomu — i tak wymaga OCR-u.
MAKS_BAJTOW = 40 * 1024 * 1024

ROZSZERZENIA = (".txt", ".md", ".markdown", ".docx", ".pdf", ".rtf")


class BladWczytywania(ValueError):
    """Błąd do pokazania użytkownikowi wprost."""


@dataclass
class Wynik:
    tekst: str
    typ: str
    znakow: int = 0
    ostrzezenia: list[str] = field(default_factory=list)
    wymaga_ocr: bool = False

    @property
    def nadaje_sie(self) -> bool:
        return bool(self.tekst.strip()) and not self.wymaga_ocr


# ════════════════════════════════════════════════════════════════════
#  BRAMKA JAKOŚCI
# ════════════════════════════════════════════════════════════════════

# Skan zapisany jako PDF ma warstwę tekstową pustą albo szczątkową.
# Odróżniamy go po gęstości tekstu względem rozmiaru pliku: strona
# tekstu to ok. 2 kB znaków, strona obrazu — setki kilobajtów.
MIN_ZNAKOW_NA_KB = 0.5

# Udział znaków, które nie są literą, cyfrą, spacją ani interpunkcją.
# Zepsute kodowanie objawia się właśnie tym: tekst „wygląda", ale składa
# się ze znaczków zastępczych i bloków sterujących.
MAKS_UDZIAL_SMIECI = 0.15

_SMIEC = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ufeff]")


def ocen_jakosc(tekst: str, bajtow: int, typ: str) -> tuple[list[str], bool]:
    """Zwraca (ostrzeżenia, czy_wymaga_ocr).

    ⚠️ To jest ta funkcja, która chroni cały łańcuch cytowania przed
    wpuszczeniem zepsutego źródła. Zmieniając progi, pamiętaj, że
    fałszywe „wczytane poprawnie" jest tu droższe niż fałszywe „to skan".
    """
    ostrzezenia: list[str] = []
    czysty = tekst.strip()

    if not czysty:
        # Komunikat mówi CO ZROBIĆ, nie tylko co jest nie tak. Osoba
        # wgrywająca akta w sekretariacie nie musi wiedzieć, czym jest
        # „warstwa tekstowa" — musi wiedzieć, że to skan i czego wymaga.
        # Druga ścieżka (szczątkowa warstwa, niżej) mówiła to od początku;
        # ta była napisana żargonem. Wyrównane 16.08.2026.
        if typ == "pdf":
            return (["PDF nie zawiera tekstu, a jedynie obraz — to skan. "
                     "Wymaga OCR-u (rozpoznania pisma) przed wczytaniem. "
                     "Wczytanie go w tej postaci dałoby sprawę bez ani "
                     "jednego cytatu."], True)
        return ([f"Plik {typ.upper()} jest pusty albo nie zawiera tekstu "
                 f"możliwego do odczytania."], False)

    smieci = len(_SMIEC.findall(czysty))
    if smieci / max(1, len(czysty)) > MAKS_UDZIAL_SMIECI:
        return ([f"Wydobyty tekst zawiera {smieci} znaków nieczytelnych — "
                 f"kodowanie pliku nie zostało rozpoznane poprawnie. "
                 f"Dokument NIE został wczytany, bo cytaty z takiego "
                 f"źródła byłyby niewiarygodne."], True)

    # Podpis pomylonej strony kodowej, którego naprawa NIE usunęła.
    # Znaki są drukowalne, więc powyższy licznik śmieci ich nie widzi —
    # a tekst nadal nie jest treścią pisma. Patrz `napraw_kodowanie`.
    podejrzanych = _ile_z(czysty, _PODPIS_POMYLKI)
    if podejrzanych / len(czysty) > PROG_POMYLKI * 3:
        return ([f"Tekst zawiera {podejrzanych} znaków wskazujących na "
                 f"pomyloną stronę kodową, której nie udało się odwrócić "
                 f"(polskie litery zapisane jako ¹, ê, ³). Dokument NIE "
                 f"został wczytany — cytaty z takiego źródła byłyby "
                 f"zgodne znak w znak z tekstem, którego w piśmie nie ma."],
                True)

    if typ == "pdf" and bajtow > 0:
        gestosc = len(czysty) / (bajtow / 1024)
        if gestosc < MIN_ZNAKOW_NA_KB:
            return ([f"PDF ma znikomą warstwę tekstową "
                     f"({len(czysty)} znaków na {bajtow // 1024} kB) — "
                     f"to najpewniej skan. Wymaga OCR-u przed wczytaniem."], True)

    # Litery ze znakami diakrytycznymi rozłożone na znak bazowy i znak
    # łączący czytają się tak samo, a porównują inaczej — a weryfikator
    # cytatów porównuje znak w znak.
    if czysty != unicodedata.normalize("NFC", czysty):
        ostrzezenia.append("Znaki diakrytyczne znormalizowano do postaci NFC.")

    if len(czysty) < 200:
        ostrzezenia.append(
            f"Wydobyto tylko {len(czysty)} znaków — sprawdź, czy to cały "
            f"dokument.")

    return (ostrzezenia, False)


# ════════════════════════════════════════════════════════════════════
#  TEKST
# ════════════════════════════════════════════════════════════════════

# Kolejność nieprzypadkowa: cp1250 przed latin2, bo polskie pisma
# z Windowsa są nieporównanie częstsze niż z systemów uniksowych.
KODOWANIA = ("utf-8-sig", "utf-8", "cp1250", "iso-8859-2", "cp852")


def _zdekoduj(dane: bytes) -> str:
    for kodowanie in KODOWANIA:
        try:
            return dane.decode(kodowanie)
        except UnicodeDecodeError:
            continue
    # Ostatnia deska: dekodujemy z zamianą, a bramka jakości i tak
    # odrzuci wynik, jeżeli znaków zastępczych będzie za dużo.
    return dane.decode("utf-8", errors="replace")


def _z_tekstu(dane: bytes) -> str:
    return _zdekoduj(dane)


def _z_rtf(dane: bytes) -> str:
    """RTF sprowadzony do tekstu — bez pełnego parsera.

    RTF wychodzi z Worda i starych systemów kancelaryjnych. Interesuje
    nas wyłącznie treść, więc usuwamy grupy sterujące i rozwijamy
    sekwencje `\\'xx`, którymi RTF koduje polskie znaki.
    """
    tekst = dane.decode("cp1250", errors="replace")
    tekst = re.sub(r"\{\\\*.*?\}", " ", tekst, flags=re.DOTALL)
    tekst = re.sub(r"\\par[d]?\b", "\n", tekst)
    tekst = re.sub(r"\\'([0-9a-fA-F]{2})",
                   lambda m: bytes([int(m.group(1), 16)]).decode(
                       "cp1250", errors="replace"), tekst)
    tekst = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", tekst)
    tekst = tekst.replace("{", " ").replace("}", " ")
    return tekst


# ════════════════════════════════════════════════════════════════════
#  DOCX
# ════════════════════════════════════════════════════════════════════

_NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _z_docx(dane: bytes) -> str:
    """Treść z `word/document.xml`, z akapitami jako granicami zdań.

    Akapit musi kończyć się przełamaniem wiersza, nie spacją — inaczej
    ostatnie zdanie akapitu skleja się z pierwszym zdaniem następnego
    i podział na zdania (ADR-0007) numeruje twór, którego w piśmie nie ma.
    """
    try:
        with zipfile.ZipFile(BytesIO(dane)) as archiwum:
            nazwy = set(archiwum.namelist())
            if "word/document.xml" not in nazwy:
                raise BladWczytywania(
                    "Plik DOCX nie zawiera `word/document.xml` — to nie jest "
                    "dokument Worda albo jest uszkodzony.")
            surowy = archiwum.read("word/document.xml")
    except zipfile.BadZipFile as e:
        raise BladWczytywania(
            "Pliku DOCX nie da się otworzyć — jest uszkodzony lub to nie "
            f"jest DOCX. Szczegół: {e}") from e

    korzen = ElementTree.fromstring(surowy)
    czesci: list[str] = []

    for akapit in korzen.iter(f"{_NS_W}p"):
        wiersz: list[str] = []
        for wezel in akapit.iter():
            if wezel.tag == f"{_NS_W}t":
                wiersz.append(wezel.text or "")
            elif wezel.tag in (f"{_NS_W}tab",):
                wiersz.append("\t")
            elif wezel.tag in (f"{_NS_W}br", f"{_NS_W}cr"):
                wiersz.append("\n")
        tresc = "".join(wiersz).strip()
        if tresc:
            czesci.append(tresc)

    return "\n\n".join(czesci)


# ════════════════════════════════════════════════════════════════════
#  PDF
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ NAJTRUDNIEJSZY I NAJRYZYKOWNIEJSZY FORMAT — DLATEGO NAJOSTROŻNIEJ.
#
# PDF nie przechowuje tekstu, tylko instrukcje rysowania glifów. Bajt
# w strumieniu jest numerem glifu w foncie, a nie znakiem Unicode.
# Dopiero mapa `/ToUnicode` mówi, co ten glif znaczy — i bez niej
# polskie znaki wychodzą przypadkowe.
#
# Stąd kolejność:
#   1. mapy ToUnicode dla każdego fontu (bfchar / bfrange),
#   2. śledzenie bieżącego fontu operatorem `Tf`,
#   3. odczyt tekstu operatorami Tj / TJ / ' / ",
#   4. bramka jakości na końcu — jeżeli cokolwiek poszło źle, odmawiamy.

_OBIEKT = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.DOTALL)
_STRUMIEN = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
_TOUNICODE = re.compile(rb"/ToUnicode\s+(\d+)\s+\d+\s+R")
_FONT_ZASOB = re.compile(rb"/(\w+)\s+(\d+)\s+\d+\s+R")


def _rozpakuj(cialo: bytes, surowy: bytes) -> bytes:
    """Zawartość strumienia, rozpakowana gdy trzeba."""
    if b"/FlateDecode" not in surowy:
        return cialo
    try:
        return zlib.decompress(cialo)
    except zlib.error:
        # Bywają strumienie z nadmiarowymi bajtami na końcu.
        try:
            return zlib.decompressobj().decompress(cialo)
        except zlib.error:
            return b""


def _mapa_tounicode(dane: bytes) -> dict[int, str]:
    """Mapa kod glifu → znak, z bloków `beginbfchar` i `beginbfrange`."""
    mapa: dict[int, str] = {}

    def _znak(surowy: bytes) -> str:
        # Wartości są ciągami UTF-16BE, czasem wieloznakowymi.
        try:
            return bytes.fromhex(surowy.decode("ascii")).decode(
                "utf-16-be", errors="ignore")
        except ValueError:
            return ""

    for blok in re.findall(rb"beginbfchar(.*?)endbfchar", dane, re.DOTALL):
        for zrodlo, cel in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
                                      blok):
            znak = _znak(cel)
            if znak:
                mapa[int(zrodlo, 16)] = znak

    for blok in re.findall(rb"beginbfrange(.*?)endbfrange", dane, re.DOTALL):
        for od, do, cel in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
                blok):
            poczatek, koniec = int(od, 16), int(do, 16)
            baza = _znak(cel)
            if not baza or koniec - poczatek > 65535:
                continue
            for i in range(koniec - poczatek + 1):
                mapa[poczatek + i] = chr(ord(baza[0]) + i) + baza[1:]

    return mapa


def _rozwin_literal(surowy: bytes) -> bytes:
    """Ciąg `(...)` z rozwiniętymi sekwencjami ucieczki PDF-a."""
    wynik = bytearray()
    i = 0
    ucieczki = {b"n": 10, b"r": 13, b"t": 9, b"b": 8, b"f": 12,
                b"(": 40, b")": 41, b"\\": 92}
    while i < len(surowy):
        bajt = surowy[i:i + 1]
        if bajt != b"\\":
            wynik += bajt
            i += 1
            continue
        nastepny = surowy[i + 1:i + 2]
        if nastepny in ucieczki:
            wynik.append(ucieczki[nastepny])
            i += 2
        elif nastepny.isdigit():
            osemkowo = surowy[i + 1:i + 4]
            cyfry = bytes(b for b in osemkowo if 48 <= b <= 55)
            wynik.append(int(cyfry, 8) & 0xFF)
            i += 1 + len(cyfry)
        elif nastepny in (b"\n", b"\r"):
            i += 2                       # złamanie wiersza w źródle
        else:
            wynik += nastepny
            i += 2
    return bytes(wynik)


def _na_znaki(surowy: bytes, mapa: dict[int, str] | None) -> str:
    if mapa:
        # Fonty z ToUnicode adresują glify dwubajtowo w zdecydowanej
        # większości pism; jednobajtowe traktujemy jako zapasowe.
        if len(surowy) % 2 == 0 and any(
                int.from_bytes(surowy[i:i + 2], "big") in mapa
                for i in range(0, min(len(surowy), 16), 2)):
            return "".join(
                mapa.get(int.from_bytes(surowy[i:i + 2], "big"), "")
                for i in range(0, len(surowy) - 1, 2))
        if any(b in mapa for b in surowy):
            return "".join(mapa.get(b, "") for b in surowy)
    # Bez mapy zostaje WinAnsi — domyślne kodowanie pism z Worda.
    # ⚠️ Dla polskich pism to kodowanie BŁĘDNE i naprawia je dopiero
    #    `napraw_kodowanie` na całości tekstu — patrz komentarz tam.
    return surowy.decode("cp1252", errors="replace")


_TEKST_W_STRUMIENIU = re.compile(
    rb"/(\w+)\s+[\d.]+\s+Tf"                     # 1: wybór fontu
    rb"|\((?:[^()\\]|\\.|\([^()]*\))*\)\s*Tj"    # literal + Tj
    rb"|\[(?:[^\[\]\\]|\\.)*\]\s*TJ"             # tablica + TJ
    rb"|<([0-9A-Fa-f\s]+)>\s*Tj"                 # 2: hex + Tj
    rb"|(T\*|Td|TD|'|\"|ET)",                    # 3: przejścia wiersza
    re.DOTALL)

_LITERAL = re.compile(rb"\((?:[^()\\]|\\.|\([^()]*\))*\)")
_HEX = re.compile(rb"<([0-9A-Fa-f\s]+)>")
_PRZESUNIECIE = re.compile(rb"(-?[\d.]+)")


def _tekst_ze_strumienia(strumien: bytes,
                         mapy: dict[str, dict[int, str]]) -> str:
    """Tekst z jednego strumienia treści, z podziałem na wiersze."""
    czesci: list[str] = []
    biezaca: dict[int, str] | None = None

    for dopasowanie in _TEKST_W_STRUMIENIU.finditer(strumien):
        calosc = dopasowanie.group(0)

        if dopasowanie.group(1):                       # /F1 12 Tf
            biezaca = mapy.get(dopasowanie.group(1).decode("ascii", "ignore"))
            continue

        if dopasowanie.group(3):                       # koniec wiersza
            czesci.append("\n")
            continue

        if dopasowanie.group(2):                       # <hex> Tj
            surowy = bytes.fromhex(
                re.sub(rb"\s", b"", dopasowanie.group(2)).decode("ascii"))
            czesci.append(_na_znaki(surowy, biezaca))
            continue

        if calosc.rstrip().endswith(b"TJ"):
            # Tablica: ciągi tekstu przeplatane przesunięciami. Duże
            # przesunięcie ujemne to w praktyce spacja między wyrazami.
            for element in re.finditer(
                    rb"\((?:[^()\\]|\\.)*\)|<([0-9A-Fa-f\s]+)>|(-?[\d.]+)",
                    calosc):
                if element.group(2):
                    try:
                        if float(element.group(2)) < -120:
                            czesci.append(" ")
                    except ValueError:
                        pass
                elif element.group(1):
                    surowy = bytes.fromhex(
                        re.sub(rb"\s", b"", element.group(1)).decode("ascii"))
                    czesci.append(_na_znaki(surowy, biezaca))
                else:
                    czesci.append(_na_znaki(
                        _rozwin_literal(element.group(0)[1:-1]), biezaca))
            continue

        dopasowany_literal = _LITERAL.search(calosc)
        if dopasowany_literal:
            czesci.append(_na_znaki(
                _rozwin_literal(dopasowany_literal.group(0)[1:-1]), biezaca))

    return "".join(czesci)


def _z_pdf(dane: bytes) -> str:
    if b"/Encrypt" in dane[:4096] or re.search(rb"/Encrypt\s+\d+\s+\d+\s+R", dane):
        raise BladWczytywania(
            "PDF jest zaszyfrowany. Zdejmij zabezpieczenie w programie, "
            "w którym go otwierasz, i wgraj ponownie.")

    obiekty: dict[int, tuple[bytes, bytes]] = {}
    for numer, _, cialo in _OBIEKT.findall(dane):
        strumien = _STRUMIEN.search(cialo)
        obiekty[int(numer)] = (cialo,
                               _rozpakuj(strumien.group(1), cialo)
                               if strumien else b"")

    # Mapy ToUnicode: nazwa zasobu fontu → mapa znaków.
    mapy: dict[str, dict[int, str]] = {}
    for numer, (cialo, _) in obiekty.items():
        if b"/Font" not in cialo and b"/ToUnicode" not in cialo:
            continue
        odwolanie = _TOUNICODE.search(cialo)
        if not odwolanie:
            continue
        cel = obiekty.get(int(odwolanie.group(1)))
        if not cel or not cel[1]:
            continue
        mapa = _mapa_tounicode(cel[1])
        if not mapa:
            continue
        # Font bywa podpięty pod kilkoma nazwami zasobów; wiążemy go
        # z każdą, pod którą występuje w słowniku /Font strony.
        for nazwa, wskazanie in _FONT_ZASOB.findall(cialo):
            if int(wskazanie) == numer:
                mapy[nazwa.decode("ascii", "ignore")] = mapa
        mapy.setdefault(f"__obj{numer}", mapa)

    # Powiązanie nazw zasobów z fontami po stronie stron dokumentu.
    for _, (cialo, _) in obiekty.items():
        zasoby = re.search(rb"/Font\s*<<(.*?)>>", cialo, re.DOTALL)
        if not zasoby:
            continue
        for nazwa, wskazanie in _FONT_ZASOB.findall(zasoby.group(1)):
            klucz = f"__obj{int(wskazanie)}"
            if klucz in mapy:
                mapy[nazwa.decode("ascii", "ignore")] = mapy[klucz]

    strony: list[str] = []
    for _, (cialo, tresc) in obiekty.items():
        if not tresc or b"/Image" in cialo:
            continue
        if not re.search(rb"\bBT\b", tresc):
            continue
        fragment = _tekst_ze_strumienia(tresc, mapy)
        if fragment.strip():
            strony.append(fragment)

    return "\n\n".join(strony)


# ════════════════════════════════════════════════════════════════════
#  WEJŚCIE
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
#  NAPRAWA POMYLONEJ STRONY KODOWEJ
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ NAJGROŹNIEJSZY BŁĄD W CAŁYM WCZYTYWANIU, BO NIEWIDOCZNY.
#
# Polskiego tekstu NIE DA SIĘ zapisać w cp1252 (WinAnsi) — ta strona
# kodowa nie zawiera ą, ę, ł, ń, ś, ź, ż. Polskie pisma używają cp1250
# albo mapy /ToUnicode. Gdy mapy brakuje i odczytamy bajty jako cp1252,
# dostaniemy tekst ZŁOŻONY Z POPRAWNYCH ZNAKÓW, ale niebędący treścią
# pisma:
#
#     bajt 0xB9   cp1250 → „ą"      cp1252 → „¹"
#     bajt 0xEA   cp1250 → „ę"      cp1252 → „ê"
#     bajt 0xB3   cp1250 → „ł"      cp1252 → „³"
#
# Bramka jakości tego nie złapie: „¹" i „ê" to znaki drukowalne, więc
# udział śmieci pozostaje zerowy. Dokument wszedłby do akt jako źródło
# cytatów, a weryfikator porównywałby cytaty ze zniekształconym tekstem
# — zgodnie, znak w znak, i całkowicie fałszywie.
#
# Stąd osobna naprawa: rozpoznajemy podpis tej pomyłki i odwracamy ją
# przejściem cp1252 → bajty → cp1250. Wybieramy wersję z większą liczbą
# polskich liter, a gdy naprawa nie pomaga — zostawiamy oryginał, żeby
# nie psuć dokumentów, które po prostu zawierają znak „¹".

# Znaki, na które cp1252 odwzorowuje bajty polskich liter z cp1250.
_PODPIS_POMYLKI = "¹³ê¿æñ¶œŸ£¥¾¼¯¡Œ"
_POLSKIE = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"

# Udział, powyżej którego uznajemy tekst za zniekształcony. Pojedyncze
# „¹" w przypisie zdarza się naprawdę; kilka na tysiąc znaków nie.
PROG_POMYLKI = 0.004


def _ile_z(tekst: str, znaki: str) -> int:
    zbior = set(znaki)
    return sum(1 for z in tekst if z in zbior)


def napraw_kodowanie(tekst: str) -> tuple[str, bool]:
    """Zwraca (tekst, czy_naprawiono).

    Naprawa jest podejmowana wyłącznie wtedy, gdy podpis pomyłki jest
    wyraźny, i przyjmowana wyłącznie wtedy, gdy wynik ma WIĘCEJ polskich
    liter i MNIEJ znaków z podpisu. Inaczej zostaje oryginał.
    """
    if not tekst:
        return tekst, False

    podejrzanych = _ile_z(tekst, _PODPIS_POMYLKI)
    if podejrzanych / len(tekst) < PROG_POMYLKI:
        return tekst, False

    try:
        naprawiony = tekst.encode("cp1252", errors="strict").decode("cp1250")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return tekst, False

    lepiej_polskich = _ile_z(naprawiony, _POLSKIE) > _ile_z(tekst, _POLSKIE)
    mniej_podejrzanych = _ile_z(naprawiony, _PODPIS_POMYLKI) < podejrzanych

    if lepiej_polskich and mniej_podejrzanych:
        return naprawiony, True
    return tekst, False


def _porzadkuj(tekst: str) -> str:
    tekst = unicodedata.normalize("NFC", tekst)
    tekst = tekst.replace("\r\n", "\n").replace("\r", "\n")
    tekst = tekst.replace("\u00a0", " ")
    # Dzielenie wyrazów na końcu wiersza — częste w PDF-ach z sądu.
    tekst = re.sub(r"(\w)-\n(\w)", r"\1\2", tekst)
    tekst = re.sub(r"[ \t]+", " ", tekst)
    tekst = re.sub(r" *\n *", "\n", tekst)
    tekst = re.sub(r"\n{3,}", "\n\n", tekst)
    return tekst.strip()


def wczytaj(nazwa: str, dane: bytes) -> Wynik:
    """Treść pliku jako tekst, z oceną, czy nadaje się na źródło cytatów."""
    if not dane:
        raise BladWczytywania("Plik jest pusty.")
    if len(dane) > MAKS_BAJTOW:
        raise BladWczytywania(
            f"Plik ma {len(dane) // 1024 // 1024} MB, limit to "
            f"{MAKS_BAJTOW // 1024 // 1024} MB.")

    koncowka = "." + nazwa.rsplit(".", 1)[-1].lower() if "." in nazwa else ""

    if koncowka == ".docx":
        typ, tekst = "docx", _z_docx(dane)
    elif koncowka == ".pdf":
        typ, tekst = "pdf", _z_pdf(dane)
    elif koncowka == ".rtf":
        typ, tekst = "rtf", _z_rtf(dane)
    elif koncowka in (".txt", ".md", ".markdown", ""):
        typ, tekst = "tekst", _z_tekstu(dane)
    else:
        raise BladWczytywania(
            f"Nieobsługiwany format: {koncowka}. Obsługiwane: "
            f"{', '.join(ROZSZERZENIA)}.")

    tekst, naprawiono = napraw_kodowanie(tekst)
    tekst = _porzadkuj(tekst)
    ostrzezenia, wymaga_ocr = ocen_jakosc(tekst, len(dane), typ)
    if naprawiono:
        ostrzezenia.insert(0, (
            "Plik był zapisany w pomylonej stronie kodowej (cp1252 zamiast "
            "cp1250) — polskie znaki zostały odtworzone. Sprawdź na oko "
            "pierwsze zdania, zanim oprzesz na tym dokumencie pismo."))

    return Wynik(tekst=tekst, typ=typ, znakow=len(tekst),
                 ostrzezenia=ostrzezenia, wymaga_ocr=wymaga_ocr)
