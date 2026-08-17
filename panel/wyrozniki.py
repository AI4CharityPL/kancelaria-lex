"""Wyróżniki pytania — daty, kwoty, sygnatury — sprowadzone do WARTOŚCI.

PO CO TO ISTNIEJE

Zakotwiczenie odpowiedzi w pytaniu (ADR-0007, pkt 3) sprawdza, czy
zacytowany materiał dotyczy tego, o co pytano. Pierwsza wersja
porównywała NAPISY po normalizacji białych znaków. Na polskim to
uchodziło, na angielskim rozsypało się kompletnie.

Pomiar z benchmarku 2026-08-14 18:27 — 6 fałszywych odmów, WSZYSTKIE
z kotwicą typu `data`, 5 z nich angielskie. Sprawdzenie bezpośrednie
pokazało dlaczego: dla pytania o „October 6, 2016" przechodził wyłącznie
zapis bajtowo identyczny.

    October 6, 2016    ✓ przechodzi
    6 October 2016     ✗ odmowa      ← ta sama data
    10/6/2016          ✗ odmowa      ← ta sama data
    October 6th, 2016  ✗ odmowa      ← ta sama data
    Oct. 6, 2016       ✗ odmowa      ← ta sama data

Prawnik dostawał „w aktach nie ma podstawy do odpowiedzi" przy zdaniu,
które leżało w aktach i mówiło dokładnie o tej dacie. Odmowa wyglądała
na ostrożność systemu, a była skutkiem porównywania napisów.

Angielskie pisma procesowe używają zmiennych formatów dat nieporównanie
częściej niż polskie — stąd 5:1 w rozkładzie błędów.

ZASADA: data to trójka (rok, miesiąc, dzień), a nie ciąg znaków.
        Kwota to liczba. Sygnatura to znormalizowany identyfikator.
        Porównujemy wartości.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── miesiące ────────────────────────────────────────────────────────

_MIESIACE_PL = {
    "stycznia": 1, "styczeń": 1, "styczen": 1,
    "lutego": 2, "luty": 2,
    "marca": 3, "marzec": 3,
    "kwietnia": 4, "kwiecień": 4, "kwiecien": 4,
    "maja": 5, "maj": 5,
    "czerwca": 6, "czerwiec": 6,
    "lipca": 7, "lipiec": 7,
    "sierpnia": 8, "sierpień": 8, "sierpien": 8,
    "września": 9, "wrzesień": 9, "wrzesnia": 9, "wrzesien": 9,
    "października": 10, "październik": 10, "pazdziernika": 10, "pazdziernik": 10,
    "listopada": 11, "listopad": 11,
    "grudnia": 12, "grudzień": 12, "grudzien": 12,
}

_MIESIACE_EN = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

_MIESIACE = {**_MIESIACE_PL, **_MIESIACE_EN}
_NAZWY = "|".join(sorted(_MIESIACE, key=len, reverse=True))


@dataclass(frozen=True)
class Wyrozniki:
    """Wyróżniki znalezione w tekście, sprowadzone do wartości."""
    daty: frozenset[str]          # "2016-10-06"
    kwoty: frozenset[str]         # "1008.00"
    sygnatury: frozenset[str]     # "iik14726"
    liczby: frozenset[str]        # zapasowe, gdy brak wyróżnika złożonego

    @property
    def zlozone(self) -> frozenset[str]:
        return self.daty | self.kwoty | self.sygnatury

    def __bool__(self) -> bool:
        return bool(self.zlozone or self.liczby)


# ── daty ────────────────────────────────────────────────────────────
#
# Sufiksy porządkowe (6th, 1st, 2nd, 3rd) i kropka po skrócie miesiąca
# („Oct.") to zapis, nie treść — usuwane przed dopasowaniem.

# ⚠️ „day of" I PRZECINEK PRZED ROKIEM — FORMA KANONICZNA PISM FEDERALNYCH.
#
# „RESPECTFULLY SUBMITTED this 8th day of June, 2018" to standardowa
# klauzula podpisu w aktach USA. Bez tego wtrącenia wzorzec jej nie
# łapał, więc data z pisma nie schodziła się z datą z pytania.
#
# Pomiar v2 na 50 przypadkach: zakotwiczenie odpowiadało za 9 z 16
# fałszywych odmów (56%) — największa pojedyncza przyczyna. Z dziewięciu
# form zapisu daty rozpoznawano siedem; brakowały dokładnie te dwie.
#
# Przecinek po miesiącu obsłużony przy okazji („June, 2018").
_DATA_SLOWNA = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(" + _NAZWY + r")\.?,?\s+(\d{4})\b",
    re.IGNORECASE)                    # 6 October 2016 · 8th day of June, 2018

_DATA_SLOWNA_ODWROTNA = re.compile(
    r"\b(" + _NAZWY + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE)                                   # October 6, 2016

_DATA_CYFROWA = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_DATA_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")


def _data(rok: int, miesiac: int, dzien: int) -> str | None:
    if not (1 <= miesiac <= 12 and 1 <= dzien <= 31 and 1000 <= rok <= 2999):
        return None
    return f"{rok:04d}-{miesiac:02d}-{dzien:02d}"


def znajdz_daty(tekst: str) -> set[str]:
    """Daty sprowadzone do postaci ISO. Wariant zapisu przestaje mieć znaczenie.

    ⚠️ ZAPIS CYFROWY BYWA DWUZNACZNY: „10/6/2016" to 6 października
    w konwencji amerykańskiej i 10 czerwca w europejskiej. Gdy obie
    liczby są ≤ 12, zwracamy OBIE interpretacje.

    Świadomy wybór: to sprawdzenie odpowiada na pytanie „czy odpowiedź
    dotyczy tego, o co pytano", a nie „jaka to data". Przy dwuznaczności
    lepiej przepuścić cytat, który prawnik zobaczy i oceni, niż odmówić
    odpowiedzi na pytanie o dokument, w którym data stoi.
    Ostrzejszy wariant odrzucałby prawdziwe ustalenia.
    """
    wynik: set[str] = set()

    for m in _DATA_SLOWNA.finditer(tekst):
        d = _data(int(m.group(3)), _MIESIACE[m.group(2).casefold()], int(m.group(1)))
        if d:
            wynik.add(d)

    for m in _DATA_SLOWNA_ODWROTNA.finditer(tekst):
        d = _data(int(m.group(3)), _MIESIACE[m.group(1).casefold()], int(m.group(2)))
        if d:
            wynik.add(d)

    for m in _DATA_ISO.finditer(tekst):
        d = _data(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            wynik.add(d)

    for m in _DATA_CYFROWA.finditer(tekst):
        a, b, rok = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # a/b/rok — jedna z liczb > 12 rozstrzyga jednoznacznie.
        if b > 12:
            d = _data(rok, a, b)          # miesiąc/dzień
            if d:
                wynik.add(d)
        elif a > 12:
            d = _data(rok, b, a)          # dzień/miesiąc
            if d:
                wynik.add(d)
        else:
            for d in (_data(rok, b, a), _data(rok, a, b)):
                if d:
                    wynik.add(d)
    return wynik


# ── kwoty ───────────────────────────────────────────────────────────

# ⚠️ Kolejność alternatyw ma znaczenie i pierwsza wersja miała ją złą.
#
# Wariant z separatorem tysięcy stał przed gołą liczbą i używał `*`,
# więc „1008 zł" dopasowywało się jako „100" (trzy cyfry, zero grup),
# a resztę „8" łapał kolejny przebieg. Wychodziły dwie kwoty: 100,00
# i 8,00 — żadna prawdziwa.
#
# Teraz separator jest OBOWIĄZKOWY w pierwszym wariancie (`+`), więc
# „1 008,00" nadal wchodzi tą ścieżką, a „1008" spada do drugiej.
_KWOTA = re.compile(
    r"(?:(?:PLN|USD|EUR|\$|€)\s*)?"
    r"(\d{1,3}(?:[ .,\u00a0]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"\s*(?:zł|złotych|zlotych|PLN|USD|EUR)?",
    re.IGNORECASE)

_Z_WALUTA = re.compile(r"zł|złotych|zlotych|PLN|USD|EUR|\$|€", re.IGNORECASE)


def znajdz_kwoty(tekst: str) -> set[str]:
    """Kwoty sprowadzone do liczby. „1.008,00 zł" i „1008 PLN" to ta sama kwota.

    Liczymy wyłącznie te, przy których stoi oznaczenie waluty — inaczej
    każda liczba w dokumencie stałaby się kwotą i wyróżnik przestałby
    cokolwiek wyróżniać.
    """
    wynik: set[str] = set()
    for m in _KWOTA.finditer(tekst):
        otoczenie = tekst[max(0, m.start() - 6):m.end() + 12]
        if not _Z_WALUTA.search(otoczenie):
            continue
        surowa = m.group(1)
        # Ostatni separator z dwiema cyframi po nim to część ułamkowa.
        znormalizowana = re.sub(r"[ \u00a0]", "", surowa)
        if re.search(r"[.,]\d{1,2}$", znormalizowana):
            czesc_calkowita, _, czesc_ulamkowa = re.split(
                r"([.,])(?=\d{1,2}$)", znormalizowana, maxsplit=1)[0], "", ""
            trafienie = re.match(r"^(.*)[.,](\d{1,2})$", znormalizowana)
            if trafienie:
                czesc_calkowita = re.sub(r"[.,]", "", trafienie.group(1))
                czesc_ulamkowa = trafienie.group(2).ljust(2, "0")
        else:
            czesc_calkowita = re.sub(r"[.,]", "", znormalizowana)
            czesc_ulamkowa = "00"
        if czesc_calkowita.isdigit():
            wynik.add(f"{int(czesc_calkowita)}.{czesc_ulamkowa}")
    return wynik


# ── sygnatury ───────────────────────────────────────────────────────

_SYGNATURA_PL = re.compile(r"\b([IVX]{1,4})\s+([A-Z][a-z]?)\s+(\d{1,5})/(\d{2,4})\b")
_SYGNATURA_US = re.compile(r"\b(\d:\d{2})-([a-z]{2})-(\d{3,6})\b", re.IGNORECASE)
_PRZEPIS = re.compile(r"\bart\.?\s*(\d{1,4})(?:\s*§\s*(\d{1,3}))?", re.IGNORECASE)

# ⚠️ WYRÓŻNIKI ANGIELSKIE — LUKA ZMIERZONA 15.08.2026.
#
# Ekstraktor rozpoznawał 50/50 kotwic polskich i 38/50 angielskich.
# Nierozpoznane były DOKŁADNIE dwa typy, po sześć każdy:
#
#     okres     '51 years'          0/6
#     przepis   '18 U.S.C. § 3142'  0/6
#
# Skutek nie był kosmetyczny. Bramka `_wyroznik_jest_w_aktach` przepuszcza
# dalej, gdy pytanie NIE MA wyróżnika złożonego — bo nie ma czego szukać.
# Przy tych kotwicach ekstraktor zwracał pustkę, więc bramka uznawała
# pytanie za „bez wyróżnika", eskalacja ruszała i model znajdował coś do
# zacytowania także tam, gdzie nie było nic. To jest udział w J-3 = 44%
# po angielsku wobec 88% po polsku.
#
# `\s+` zamiast spacji nie jest ostrożnością: kotwica zmierzona w aktach
# federalnych ma postać '18 U.S.C. \n§ 3142' — z łamaniem wiersza
# w środku, bo tekst pochodzi z PDF-a.

_PRZEPIS_US = re.compile(
    r"\b(\d{1,2})\s+U\.?\s?S\.?\s?C\.?\s*§{1,2}\s*(\d{1,5})(?:\s*\(\s*([a-z0-9]{1,3})\s*\))?",
    re.IGNORECASE)

_OKRES_EN = re.compile(
    r"\b(\d{1,4})\s+(day|days|week|weeks|month|months|year|years)\b",
    re.IGNORECASE)

_OKRES_PL = re.compile(
    r"\b(\d{1,4})\s+(dni|dnia|dzien|dzień|tygodni|tygodnia|"
    r"miesiecy|miesięcy|miesiaca|miesiąca|lat|lata|roku)\b",
    re.IGNORECASE)


def _WYGLADA_NA_ROK(wartosc: int) -> bool:
    """Czy liczba przy jednostce roku jest datą, a nie czasem trwania.

    Zakres kalendarzowy, nie „duża liczba": okres 150 lat jest w aktach
    możliwy (służebność, zasiedzenie), okres 2016 lat nie jest.
    """
    return 1900 <= wartosc <= 2100

# Jednostki sprowadzone do dni — „12 months" i „1 year" to nie to samo
# co do wartości, więc NIE normalizujemy między jednostkami. Normalizujemy
# wyłącznie nazwę jednostki, żeby „51 years" i „51 lat" się zeszły.
_JEDNOSTKI = {
    "day": "d", "days": "d", "dni": "d", "dnia": "d", "dzien": "d", "dzień": "d",
    "week": "t", "weeks": "t", "tygodni": "t", "tygodnia": "t",
    "month": "m", "months": "m", "miesiecy": "m", "miesięcy": "m",
    "miesiaca": "m", "miesiąca": "m",
    "year": "r", "years": "r", "lat": "r", "lata": "r", "roku": "r",
}


def znajdz_sygnatury(tekst: str) -> set[str]:
    """Sygnatury i powołania przepisów, znormalizowane.

    Rok dwucyfrowy i czterocyfrowy to ta sama sprawa: „II K 147/26"
    i „II K 147/2026" muszą się zejść.
    """
    wynik: set[str] = set()

    for m in _SYGNATURA_PL.finditer(tekst):
        rok = m.group(4)
        rok = rok[-2:] if len(rok) == 4 else rok
        wynik.add(f"{m.group(1).lower()}{m.group(2).lower()}{int(m.group(3))}/{rok}")

    for m in _SYGNATURA_US.finditer(tekst):
        wynik.add(f"{m.group(1)}-{m.group(2).lower()}-{int(m.group(3))}")

    for m in _PRZEPIS.finditer(tekst):
        paragraf = m.group(2)
        wynik.add(f"art{int(m.group(1))}" + (f"§{int(paragraf)}" if paragraf else ""))

    # Przepisy amerykańskie: „18 U.S.C. § 3142", „42 USC §1983(a)".
    for m in _PRZEPIS_US.finditer(tekst):
        litera = m.group(3)
        wynik.add(f"usc{int(m.group(1))}§{int(m.group(2))}"
                  + (f"({litera.lower()})" if litera else ""))

    # Okresy w obu językach, jednostka znormalizowana.
    for wzorzec in (_OKRES_EN, _OKRES_PL):
        for m in wzorzec.finditer(tekst):
            jednostka = _JEDNOSTKI.get(m.group(2).casefold())
            if not jednostka:
                continue
            wartosc = int(m.group(1))
            if jednostka == "r" and _WYGLADA_NA_ROK(wartosc):
                # ⚠️ „2016 roku" TO DATA, NIE CZAS TRWANIA.
                #
                # Zmierzone 16.08.2026: bez tego warunku wzorzec dawał
                # 2585 fałszywych wyróżników na samej sprawie 3 — każde
                # „13 stycznia 2025 roku" produkowało `okres2025r`.
                # Ponieważ okresy wchodzą do `zlozone`, a `wsparcie.py`
                # sekcja A ODRZUCA twierdzenie, gdy wyróżnika nie ma
                # w cytacie, kosztowało to poprawne odpowiedzi: 14 z 18
                # szkodliwych odrzuceń w przebiegu angielskim miało tu
                # przyczynę.
                #
                # Żaden akt prawny nie mówi o okresie 2016 lat. Wartość
                # w zakresie kalendarzowym przy jednostce roku jest datą
                # i data ją wyłapie — po to jest osobny ekstraktor.
                continue
            wynik.add(f"okres{wartosc}{jednostka}")
    return wynik


# ── liczby zapasowe ─────────────────────────────────────────────────

_GOLA_LICZBA = re.compile(r"\b\d{1,6}\b")


def usun_wyrozniki(tekst: str) -> str:
    """Zwraca tekst z wymazanymi wyróżnikami złożonymi.

    Potrzebne tam, gdzie po sprawdzeniu wyróżników chcemy sprawdzić
    GOŁE liczby — bez powtórnego liczenia cyfr, które są już częścią
    zaliczonej daty czy sygnatury.

    Bez tego twierdzenie „wyrok z 23 lipca 1974 r." wobec cytatu
    „wyrok z 23.07.1974 r." odpadało: data zgadzała się po wartości,
    ale osobne sprawdzenie liczb szukało „23" i nie znajdowało go,
    bo w cytacie stoi „23.07".
    """
    for wzorzec in (_DATA_SLOWNA, _DATA_SLOWNA_ODWROTNA, _DATA_ISO,
                    _DATA_CYFROWA, _SYGNATURA_PL, _SYGNATURA_US, _PRZEPIS,
                    _PRZEPIS_US, _OKRES_EN, _OKRES_PL):
        tekst = wzorzec.sub(" ", tekst)

    # ⚠️ Kwoty osobno i WARUNKOWO. `_KWOTA` ma oznaczenie waluty
    # opcjonalne z obu stron, więc dopasowuje KAŻDĄ liczbę. Bezwarunkowe
    # podstawienie wymazywało wszystkie liczby z tekstu i sprawdzenie
    # gołych liczb w `wsparcie.oszacuj` przestawało cokolwiek wykrywać —
    # twierdzenie „świadków było 3" przechodziło wobec cytatu bez
    # żadnej liczby.
    def _tylko_z_waluta(m: re.Match) -> str:
        otoczenie = tekst[max(0, m.start() - 6):m.end() + 12]
        return " " if _Z_WALUTA.search(otoczenie) else m.group(0)

    return _KWOTA.sub(_tylko_z_waluta, tekst)


def wyrozniki(tekst: str) -> Wyrozniki:
    return Wyrozniki(
        daty=frozenset(znajdz_daty(tekst)),
        kwoty=frozenset(znajdz_kwoty(tekst)),
        sygnatury=frozenset(znajdz_sygnatury(tekst)),
        liczby=frozenset(m.group(0) for m in _GOLA_LICZBA.finditer(tekst)),
    )


def zakotwiczone(pytanie: str, fragmenty: list[str]) -> bool:
    """Czy zacytowany materiał dotyczy tego, o co pytano.

    Gdy pytanie niesie wyróżnik złożony — datę, kwotę, sygnaturę —
    przynajmniej jeden musi wystąpić w cytacie. Porównanie idzie po
    WARTOŚCI, więc inny zapis tej samej daty przechodzi.

    Gołe liczby są wyróżnikiem zapasowym: wchodzą do gry dopiero wtedy,
    gdy pytanie nie zawiera żadnego wyróżnika złożonego. Inaczej pytanie
    o „1 stycznia 2023" kotwiczyłoby się na samym „2023", a rok 2023
    stoi w aktach na każdej stronie.
    """
    p = wyrozniki(pytanie)
    if not p:
        return True                      # nie ma czego kotwiczyć

    o = wyrozniki(" ".join(fragmenty))

    if p.zlozone:
        return bool(p.zlozone & o.zlozone)
    return bool(p.liczby & o.liczby)
