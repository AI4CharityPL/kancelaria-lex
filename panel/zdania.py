"""Podział tekstu na zdania z zachowaniem offsetów w oryginale.

DWA ZASTOSOWANIA, JEDNA IMPLEMENTACJA

  1. Benchmark — wybór zdania jako prawdy wzorcowej dla przypadku
     testowego (eval/benchmark/).
  2. Cytowanie po numerze zdania — model wskazuje NUMER, a treść
     cytatu bierze kod, przez co zmyślenie cytatu przestaje być
     wyrażalne (planowane ADR-0007).

Oba wymagają dokładnie tego samego: zdań z pozycją w ORYGINALE.
Offsety są tu warunkiem poprawności, nie wygodą — weryfikator cytatów
porównuje zakres znaków z treścią dokumentu źródłowego, więc zdanie
bez wiernej pozycji wskazywałoby w próżnię.

⚠️ DLACZEGO NIE `re.split(r'[.!?]')`

Bo polszczyzna prawnicza składa się ze skrótów z kropką. Zdanie
„Sąd na podstawie art. 445 § 1 k.p.k. w zw. z art. 437 § 2 k.p.k.
uchylił wyrok." rozpadłoby się na sześć „zdań", z których żadne nie
jest zdaniem. Przy cytowaniu po numerze zdania numeracja przestałaby
cokolwiek znaczyć, a cytat wskazywałby fragment „445 §".

To jest najłatwiejsza rzecz do zepsucia w całym module i najtrudniejsza
do zauważenia, bo psuje się cicho — testy w tests/test_zdania.py
sprawdzają wprost katalog skrótów.

ENGLISH SUMMARY
    Sentence segmentation that preserves offsets into the original text.
    Naive punctuation splitting fails on legal Polish, which is dense
    with abbreviations ending in a period ("art.", "§", "k.p.k.", "ust.").
    The abbreviation catalogue below is the load-bearing part.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── skróty, po których kropka NIE kończy zdania ──────────────────────
#
# Katalog jest celowo obszerny i celowo polski. Każda pozycja pochodzi
# z rzeczywistych pism procesowych, nie ze słownika ogólnego.

SKROTY_PL: frozenset[str] = frozenset("""
art ust pkt lit par § tj tzn tzw m.in np itp itd zob por
k.k k.p.k k.c k.p.c k.p.a k.k.w k.r.o u.s.p
dz.u m.p nr poz sygn akt
r godz min sek zł gr tys mln mld
ul al pl woj gm pow
prof dr hab mgr inż płk ppłk kpt por sierż asp
ws zw zam ur zm nast poprz
sa so sr sn nsa wsa tk sdz
p.o s.c sp.z.o.o s.a
""".split())

SKROTY_EN: frozenset[str] = frozenset("""
no nos art sec secs para paras cf eg ie viz etc et al
mr mrs ms dr prof hon jr sr
inc corp co ltd llc llp
u.s u.s.c c.f.r f.2d f.3d f.supp
v vs ex rel id ibid supra infra
jan feb mar apr jun jul aug sep sept oct nov dec
fed r civ p crim
""".split())


@dataclass(frozen=True)
class Zdanie:
    """Zdanie z pozycją w ORYGINALNYM tekście dokumentu.

    `numer` liczony od 1 — numeracja pokazywana modelowi i przez niego
    wskazywana. Zero jako pierwszy numer bywa źródłem pomyłek o jeden
    tam, gdzie pomyłka oznacza zacytowanie sąsiedniego zdania.
    """
    numer: int
    poczatek: int
    koniec: int
    tekst: str

    def __len__(self) -> int:
        return self.koniec - self.poczatek

    @property
    def tresc(self) -> str:
        """Alias pod `wyszukiwarka.Indeks`, który punktuje po polu `tresc`.

        Dzięki temu ten sam BM25 obsługuje i fragmenty, i zdania —
        bez drugiej implementacji rankingu.
        """
        return self.tekst


# Koniec zdania: kropka, wykrzyknik, pytajnik lub średnik na końcu
# akapitu, po którym następuje spacja i wielka litera albo koniec tekstu.
_GRANICA = re.compile(r"[.!?]+[\"'”»)\]]*\s+|\n{2,}")

# Ostatni „wyraz" przed kropką — do sprawdzenia w katalogu skrótów.
_OSTATNI_WYRAZ = re.compile(r"([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż.]+)\.?\s*$")


def _jest_skrotem(przed: str, skroty: frozenset[str]) -> bool:
    """Czy tekst przed kropką kończy się skrótem, po którym zdanie trwa."""
    m = _OSTATNI_WYRAZ.search(przed)
    if not m:
        return False
    wyraz = m.group(1).rstrip(".").casefold()
    if wyraz in skroty:
        return True
    # Pojedyncza litera z kropką to prawie zawsze inicjał („J. Kowalski")
    # albo oznaczenie jednostki redakcyjnej.
    if len(wyraz) == 1 and wyraz.isalpha():
        return True
    # Liczba z kropką to numeracja pozycji („1. Sąd ustalił…”) — kropka
    # kończy numer, nie zdanie.
    return wyraz.isdigit()


def podziel_na_zdania(tresc: str, jezyk: str = "pl",
                      min_znakow: int = 25) -> list[Zdanie]:
    """Dzieli tekst na zdania, zachowując pozycje w oryginale.

    `min_znakow` odsiewa okruchy — nagłówki, numery stron, puste linie
    z układu PDF-a. Zdanie krótsze niż kilkadziesiąt znaków nie niesie
    ustalenia faktycznego, a zaśmieca numerację.
    """
    if not tresc or not tresc.strip():
        return []

    skroty = SKROTY_EN if jezyk == "en" else SKROTY_PL
    zdania: list[Zdanie] = []
    start = 0
    numer = 1

    for dopasowanie in _GRANICA.finditer(tresc):
        koniec = dopasowanie.end()
        kandydat = tresc[start:koniec]

        # Kropka po skrócie nie kończy zdania — szukamy dalej.
        if _jest_skrotem(tresc[start:dopasowanie.start() + 1], skroty):
            continue

        if len(kandydat.strip()) >= min_znakow:
            zdania.append(_zbuduj(numer, tresc, start, koniec))
            numer += 1
            start = koniec
        # Za krótkie: nie zamykamy zdania, doklei się do następnego.

    # Ogon bez znaku końca.
    if start < len(tresc) and len(tresc[start:].strip()) >= min_znakow:
        zdania.append(_zbuduj(numer, tresc, start, len(tresc)))

    return zdania


def _zbuduj(numer: int, tresc: str, start: int, koniec: int) -> Zdanie:
    """Przycina białe znaki z brzegów, KORYGUJĄC offsety.

    Bez korekty cytat zaczynałby się od spacji albo znaku nowego wiersza
    z poprzedniego akapitu — a weryfikator porównuje zakres znak w znak.
    """
    surowe = tresc[start:koniec]
    lewy = len(surowe) - len(surowe.lstrip())
    prawy = len(surowe) - len(surowe.rstrip())
    return Zdanie(
        numer=numer,
        poczatek=start + lewy,
        koniec=koniec - prawy,
        tekst=surowe.strip(),
    )


_ZNACZNIK_HTML = re.compile(r"<[^>]{1,80}>")
_WYRAZ = re.compile(r"[^\W\d_]{3,}")


def zdanie_uzyteczne(tekst: str, min_udzial_liter: float = 0.62,
                     min_wyrazow: int = 5) -> bool:
    """Czy zdanie nadaje się na cytat pokazywany prawnikowi.

    ⚠️ POWÓD, DLA KTÓREGO TEN FILTR MUSI BYĆ W PANELU, A NIE W BENCHMARKU.

    Akta po konwersji PDF-a i po imporcie HTML zawierają pozycje, które
    formalnie są zdaniami, a treścią nie są:

        n/d
        ☒Uniewinnienie</p> </td> <td colspan="3">
        DATED this /S-t:.h day of March _2_0_18

    Dopóki model przepisywał cytat sam, takie pozycje po prostu obniżały
    jakość wsadu. Przy cytowaniu po NUMERZE zdania stają się groźniejsze:
    kod weźmie wskazaną pozycję dosłownie i poda ją prawnikowi jako
    cytat z akt — formalnie wierny, praktycznie bezużyteczny.

    Filtr istniał dotąd wyłącznie po stronie benchmarku, co znaczyło,
    że odsiewaliśmy śmieci ze zbioru testowego, a modelowi podawaliśmy
    je dalej. Mierzyliśmy więc system na łatwiejszym materiale, niż
    dostaje w pracy.
    """
    if not tekst or len(tekst) < 30:
        return False
    if _ZNACZNIK_HTML.search(tekst):
        return False
    if tekst.count("_") > 3 or tekst.count("|") > 2:
        return False
    if sum(1 for z in tekst if z.isalpha() or z.isspace()) / len(tekst) < min_udzial_liter:
        return False
    return len(_WYRAZ.findall(tekst)) >= min_wyrazow


def ponumeruj(zdania: list[Zdanie], limit_znakow: int | None = None) -> str:
    """Tekst z numeracją, w postaci pokazywanej modelowi.

        [12] Świadek zeznał, że pojazd był koloru srebrnego.

    Model odsyła numer, a treść cytatu kod bierze ze źródła — dzięki
    czemu cytat jest wierny z definicji, a nie z dobrej woli modelu.
    """
    linie: list[str] = []
    zuzyte = 0
    for z in zdania:
        linia = f"[{z.numer}] {z.tekst}"
        # Pierwsze zdanie wchodzi ZAWSZE, choćby przekraczało budżet.
        #
        # Wcześniej pusty budżet dawał pusty wynik, a model dostawał zero
        # zdań do wyboru i zwracał pustą listę ustaleń. Wyglądało to jak
        # „w dokumencie nic nie ma", a znaczyło „nie pokazano dokumentu" —
        # ten sam tryb cichego zera, który kosztował już ten pipeline
        # dwie pułapki (patrz docs/16-panel.md).
        #
        # Zdania nie przycinamy: cytat ma być wierny, a ucięte zdanie
        # przestałoby się zgadzać ze źródłem znak w znak.
        if linie and limit_znakow is not None and zuzyte + len(linia) > limit_znakow:
            break
        linie.append(linia)
        zuzyte += len(linia) + 1
    return "\n".join(linie)


def znajdz_zdanie(zdania: list[Zdanie], pozycja: int) -> Zdanie | None:
    """Zdanie zawierające wskazaną pozycję znakową w oryginale."""
    for z in zdania:
        if z.poczatek <= pozycja < z.koniec:
            return z
    return None
