"""Generator przypadków testowych z automatyczną prawdą wzorcową.

════════════════════════════════════════════════════════════════════════
 IDEA / THE IDEA — PARY DOPASOWANE (MATCHED PAIRS)
════════════════════════════════════════════════════════════════════════

Każdy przypadek odpowiadalny ma BLIŹNIAKA, który jest identyczny co do
formy, a nieodpowiadalny co do treści. Różnią się jedną rzeczą: kotwicą.

    A.  „Czego dotyczy kwota 12 500 zł w tych aktach?"   → kwota JEST
    B.  „Czego dotyczy kwota 87 310 zł w tych aktach?"   → kwoty NIE MA

Zdanie zawierające 12 500 zł jest znane co do znaku, więc przypadek A
ma prawdę wzorcową bez udziału człowieka. Kwota z przypadku B została
sprawdzona wyszukiwaniem po całych aktach i nie występuje, więc jedyną
poprawną odpowiedzią jest odmowa.

DLACZEGO TO JEST MOCNIEJSZE OD ZWYKŁEGO ZBIORU PYTAŃ

System, który odmawia zawsze, zdobywa komplet punktów za odmowę
i zero za cytowanie. System, który cytuje zawsze, odwrotnie. Dopiero
RÓŻNICA MIĘDZY BLIŹNIAKAMI mierzy to, o co chodzi: czy system rozróżnia
sytuację, w której odpowiedź w aktach jest, od tej, w której jej nie ma.

Forma pytania, długość, typ kotwicy i dokument źródłowy są w parze
takie same, więc różnica w zachowaniu nie da się wytłumaczyć trudnością
pytania. To jest zwykły eksperyment z grupą kontrolną, przeniesiony
na grunt ewaluacji RAG-a.

DLACZEGO BEZ SĘDZIEGO LLM

Bo prawda wzorcowa jest tu zakresem znaków, a nie opinią. Zgodnie
z ADR-0006 ocena cytatu jest maszynowa. Stanowisko to ma zresztą
niezależne potwierdzenie w literaturze na gruncie polskiego prawa —
patrz eval/benchmark/README.md.

DLACZEGO BEZ PRACY PRAWNIKA

Bo gold set wymagający weryfikacji człowieka rośnie do 150 pytań
i tam się zatrzymuje (docs/11-testy-i-bramki.md). Ten generator robi
tysiące przypadków z tych samych akt i skaluje się z korpusem.
NIE ZASTĘPUJE gold setu — mierzy co innego: wierność cytatu i odmowę,
a nie poprawność merytoryczną. Obie miary są potrzebne.

════════════════════════════════════════════════════════════════════════

ENGLISH SUMMARY
    Generates benchmark cases with mechanically-derived ground truth,
    in matched pairs: every answerable case has a form-identical
    unanswerable twin, differing only in the anchor value. Ground truth
    for answerable cases is an exact character span; for twins it is
    "must refuse", verified by exhaustive search over the case files.
    No LLM judge, no lawyer time.
"""

from __future__ import annotations

import hashlib
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "panel"))

from zdania import Zdanie, podziel_na_zdania  # noqa: E402

# ── kategorie / categories ───────────────────────────────────────────

FAKT_ZAKOTWICZONY = "fakt_zakotwiczony"      # answerable, span known
BEZ_POKRYCIA = "bez_pokrycia"                # must refuse
PULAPKA_LICZBOWA = "pulapka_liczbowa"        # near-miss number, must refuse
SZCZELNOSC = "szczelnosc"                    # fact from another case

OCZEKIWANIE_CYTAT = "cytat"
OCZEKIWANIE_ODMOWA = "odmowa"


# ── kotwice / anchors ────────────────────────────────────────────────
#
# Kotwica to wyrażenie na tyle rzadkie, żeby jednoznacznie wskazywało
# jedno zdanie w aktach. Typy dobrane pod to, o co prawnik pyta akt
# najczęściej — i pod to, co wyszukiwanie wektorowe gubi najchętniej
# (patrz uzasadnienie BM25 w panel/wyszukiwarka.py).

MIESIACE_PL = ("stycznia lutego marca kwietnia maja czerwca lipca sierpnia "
               "września października listopada grudnia").split()

WZORCE_PL: dict[str, re.Pattern] = {
    "sygnatura": re.compile(r"\b[IVX]{1,4}\s+[A-Z][a-z]?\s+\d{1,5}/\d{2,4}\b"),
    # ⚠️ Separator tysięcy w polskim zapisie kwot to KROPKA, a część
    #    ułamkowa idzie po przecinku: „1.008,00 zł". Wzorzec bez kropki
    #    łapał wyłącznie ogon („008,00 zł") i generował pytanie o kwotę,
    #    która w aktach nie występuje — przypadek „odpowiadalny" bez
    #    odpowiedzi. Spacja i spacja nierozdzielająca też się zdarzają.
    "kwota": re.compile(
        r"\b\d{1,3}(?:[.  ]\d{3})*(?:,\d{2})?\s*(?:zł|złotych)\b"
    ),
    "data": re.compile(
        r"\b\d{1,2}\s+(?:" + "|".join(MIESIACE_PL) + r")\s+\d{4}\s*r\.?"
    ),
    "okres": re.compile(r"\b\d{1,3}\s+(?:dni|dnia|miesięcy|miesiąca|lat|lata)\b"),
    "przepis": re.compile(r"\bart\.\s*\d{1,3}[a-z]?(?:\s*§\s*\d{1,2})?\b"),
}

WZORCE_EN: dict[str, re.Pattern] = {
    "sygnatura": re.compile(r"\b\d:\d{2}-[a-z]{2}-\d{5}\b"),
    "kwota": re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b"),
    "data": re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    ),
    "okres": re.compile(r"\b\d{1,3}\s+(?:days|day|months|month|years|year)\b"),
    "przepis": re.compile(r"\b\d{1,2}\s+U\.S\.C\.\s*§*\s*\d{1,5}\b"),
}


# ── szablony pytań / question templates ──────────────────────────────
#
# Pytania są sformułowane tak, jak pyta prawnik przeglądający akta:
# od konkretu (kwota, data, sygnatura) do okoliczności. Ta sama forma
# obsługuje bliźniaka, więc para różni się WYŁĄCZNIE wartością kotwicy.

SZABLONY_PL: dict[str, str] = {
    "sygnatura": "Co akta tej sprawy stwierdzają w odniesieniu do sygnatury {kotwica}?",
    "kwota": "Czego dotyczy kwota {kotwica} w aktach tej sprawy?",
    "data": "Jakie zdarzenie akta tej sprawy wiążą z datą {kotwica}?",
    "okres": "Do czego odnosi się okres {kotwica} w aktach tej sprawy?",
    "przepis": "W jakim kontekście akta tej sprawy powołują {kotwica}?",
}

SZABLONY_EN: dict[str, str] = {
    "sygnatura": "What do the case files state with respect to docket {kotwica}?",
    "kwota": "What does the amount {kotwica} relate to in these case files?",
    "data": "What event do the case files associate with the date {kotwica}?",
    "okres": "What does the period of {kotwica} refer to in these case files?",
    "przepis": "In what context do the case files invoke {kotwica}?",
}


@dataclass(frozen=True)
class Przypadek:
    """Pojedynczy przypadek testowy z prawdą wzorcową."""
    id: str
    kategoria: str
    jezyk: str
    pytanie: str
    oczekiwanie: str                       # cytat | odmowa
    kotwica: str
    typ_kotwicy: str
    dokument_id: str | None = None         # tylko dla oczekiwania „cytat"
    poczatek: int | None = None
    koniec: int | None = None
    zdanie_wzorcowe: str = ""
    para_id: str | None = None             # bliźniak z pary dopasowanej
    uwagi: str = ""

    @property
    def odpowiadalny(self) -> bool:
        return self.oczekiwanie == OCZEKIWANIE_CYTAT


@dataclass
class Korpus:
    """Akta jednej sprawy przygotowane do generowania przypadków."""
    sprawa_id: int
    jezyk: str
    dokumenty: dict[str, str]              # {id: pełna treść}
    nazwy: dict[str, str] = field(default_factory=dict)
    _polaczone: str | None = None

    @property
    def polaczone(self) -> str:
        """Cała treść sprawy — do sprawdzania, czy kotwicy NA PEWNO nie ma."""
        if self._polaczone is None:
            self._polaczone = "\n".join(self.dokumenty.values())
        return self._polaczone

    def zawiera(self, fraza: str) -> bool:
        return fraza in self.polaczone


def _identyfikator(*czesci: str) -> str:
    surowe = "|".join(czesci).encode("utf-8")
    return hashlib.sha256(surowe).hexdigest()[:12]


def _wzorce(jezyk: str) -> dict[str, re.Pattern]:
    return WZORCE_EN if jezyk == "en" else WZORCE_PL


def _szablony(jezyk: str) -> dict[str, str]:
    return SZABLONY_EN if jezyk == "en" else SZABLONY_PL


def znajdz_kotwice(zdanie: Zdanie, jezyk: str) -> list[tuple[str, str]]:
    """Kotwice w zdaniu jako (typ, wartość)."""
    trafienia: list[tuple[str, str]] = []
    for typ, wzorzec in _wzorce(jezyk).items():
        for m in wzorzec.finditer(zdanie.tekst):
            trafienia.append((typ, m.group(0).strip()))
    return trafienia


def _kotwica_unikalna(korpus: Korpus, wartosc: str) -> bool:
    """Czy kotwica wskazuje JEDNO miejsce w aktach.

    Kotwica występująca dziesięć razy nie ma jednoznacznej prawdy
    wzorcowej — system mógłby zacytować dowolne z wystąpień i miałby
    rację, a punktacja i tak by go ukarała. Takie przypadki odpadają.
    """
    return korpus.polaczone.count(wartosc) == 1


# ── perturbacja kotwicy → bliźniak nieodpowiadalny ───────────────────

MIESIACE_EN = ("January February March April May June July August September "
               "October November December").split()

_ROK = re.compile(r"\b(1[89]\d{2}|20[0-4]\d)\b")


def _przesun_liczby(wartosc: str, typ: str, los: random.Random) -> str:
    """Zmienia wartość, zachowując kształt ORAZ WIARYGODNOŚĆ.

    ⚠️ WIARYGODNOŚĆ BLIŹNIAKA JEST WARUNKIEM POPRAWNOŚCI POMIARU.

    Pierwsza wersja przesuwała losowe cyfry i produkowała „16 kwietnia
    7029 r." albo „December 12, 7010". Taki bliźniak nie mierzy tego,
    co trzeba: system może odmówić dlatego, że rok 7029 jest absurdalny,
    a nie dlatego, że sprawdził akta i niczego nie znalazł. Odmowa
    z właściwego powodu i odmowa z niewłaściwego powodu dają ten sam
    wynik punktowy, więc pomiar przestaje cokolwiek znaczyć.

    Bliźniak ma być wartością, która SPOKOJNIE MOGŁABY wystąpić w tych
    aktach, a jednak nie występuje. Dlatego przesunięcia są zależne
    od typu: w datach ruszamy dzień i miesiąc, zostawiając rok; w
    kwotach zmieniamy cyfry środkowe, zachowując rząd wielkości.
    """
    if typ == "data":
        return _przesun_date(wartosc, los)

    znaki = list(wartosc)
    pozycje = [i for i, z in enumerate(znaki) if z.isdigit()]
    if not pozycje:
        return wartosc

    # Wiodąca cyfra zostaje — inaczej „1.008,00 zł" robi się
    # „7.008,00 zł" i zmienia rząd wielkości, co samo w sobie bywa
    # sygnałem, że coś jest nie tak.
    kandydaci = pozycje[1:] if len(pozycje) > 2 else pozycje
    for i in los.sample(kandydaci, min(2, len(kandydaci))):
        znaki[i] = str((int(znaki[i]) + los.randint(3, 6)) % 10)
    return "".join(znaki)


def _przesun_date(wartosc: str, los: random.Random) -> str:
    """Przesuwa dzień i miesiąc, ZOSTAWIAJĄC rok nietknięty.

    Data pozostaje datą, jaka mogła paść w tych aktach — zmienia się
    tylko to, którą. Rok zachowany, bo to on decyduje o wiarygodności.
    """
    wynik = wartosc

    # Miesiąc słowny → inny miesiąc.
    for miesiace in (MIESIACE_PL, MIESIACE_EN):
        for m in miesiace:
            if m in wynik:
                inny = los.choice([x for x in miesiace if x != m])
                wynik = wynik.replace(m, inny, 1)
                break

    # Dzień → inny dzień z bezpiecznego zakresu 1–28.
    def _dzien(dopasowanie: re.Match) -> str:
        stary = int(dopasowanie.group(0))
        nowy = los.choice([d for d in range(1, 29) if d != stary])
        return str(nowy) if len(dopasowanie.group(0)) == 1 else f"{nowy:02d}"

    # Pierwsza liczba 1–2 cyfrowa, która NIE jest rokiem.
    for m in re.finditer(r"\b\d{1,2}\b", wynik):
        wynik = wynik[:m.start()] + _dzien(m) + wynik[m.end():]
        break

    return wynik


def _bliznik_nieodpowiadalny(korpus: Korpus, wartosc: str, typ: str,
                             los: random.Random, prob: int = 40) -> str | None:
    """Wartość tego samego kształtu, której W AKTACH NIE MA.

    Zwraca None, gdy nie udało się takiej znaleźć — lepiej stracić
    przypadek niż wygenerować „nieodpowiadalny", który jednak
    w aktach jest.
    """
    for _ in range(prob):
        kandydat = _przesun_liczby(wartosc, typ, los)
        if kandydat != wartosc and not korpus.zawiera(kandydat):
            return kandydat
    return None


# ── jakość zdania wzorcowego ─────────────────────────────────────────

_ZNACZNIK = re.compile(r"<[^>]{1,80}>")


def zdanie_nadaje_sie(tekst: str, min_udzial_liter: float = 0.62) -> bool:
    """Czy zdanie nadaje się na prawdę wzorcową.

    ⚠️ Bez tego filtra do zbioru wchodziły fragmenty tabel i śmieci
    po konwersji: „☒Uniewinnienie</p> </td> <td colspan="3">" albo
    „DATED this /S-t:.h day of March _2_0_18". Formalnie są to zdania
    zawierające kotwicę, ale nie da się o nich sensownie zapytać
    i nie da się rozstrzygnąć, czy odpowiedź systemu jest trafna.

    Zbiór testowy pełen takich pozycji daje liczby, które wyglądają
    na pomiar, a mierzą jakość konwersji PDF-a.
    """
    if not tekst or len(tekst) < 40:
        return False
    if _ZNACZNIK.search(tekst):                 # pozostałości HTML
        return False
    if tekst.count("_") > 3 or tekst.count("|") > 2:
        return False

    litery = sum(1 for z in tekst if z.isalpha() or z.isspace())
    if litery / len(tekst) < min_udzial_liter:
        return False

    # Zdanie musi mieć kilka prawdziwych wyrazów, a nie sam nagłówek.
    wyrazy = [w for w in re.findall(r"[^\W\d_]{3,}", tekst)]
    return len(wyrazy) >= 6


# ── generowanie ──────────────────────────────────────────────────────

def generuj_pary(korpus: Korpus, ile_par: int = 50,
                 ziarno: int = 42,
                 min_dlugosc_zdania: int = 60) -> list[Przypadek]:
    """Pary dopasowane: przypadek odpowiadalny + jego bliźniak.

    Zwraca listę, w której bliźniaki sąsiadują ze sobą i wskazują
    na siebie przez `para_id`.
    """
    los = random.Random(ziarno)
    szablony = _szablony(korpus.jezyk)
    przypadki: list[Przypadek] = []

    # Kolejność dokumentów losowa, ale powtarzalna — inaczej przypadki
    # pochodziłyby zawsze z pierwszych kilku dokumentów sprawy.
    doc_ids = sorted(korpus.dokumenty)
    los.shuffle(doc_ids)

    for doc_id in doc_ids:
        if len(przypadki) >= ile_par * 2:
            break
        tresc = korpus.dokumenty[doc_id]
        zdania = podziel_na_zdania(tresc, jezyk=korpus.jezyk)

        for zdanie in zdania:
            if len(przypadki) >= ile_par * 2:
                break
            if len(zdanie.tekst) < min_dlugosc_zdania:
                continue
            if not zdanie_nadaje_sie(zdanie.tekst):
                continue

            for typ, wartosc in znajdz_kotwice(zdanie, korpus.jezyk):
                if typ not in szablony:
                    continue
                if not _kotwica_unikalna(korpus, wartosc):
                    continue

                bliznik = _bliznik_nieodpowiadalny(korpus, wartosc, typ, los)
                if bliznik is None:
                    continue

                id_a = _identyfikator(str(korpus.sprawa_id), doc_id,
                                      str(zdanie.poczatek), wartosc)
                id_b = _identyfikator(str(korpus.sprawa_id), doc_id,
                                      str(zdanie.poczatek), bliznik, "b")

                przypadki.append(Przypadek(
                    id=id_a, kategoria=FAKT_ZAKOTWICZONY, jezyk=korpus.jezyk,
                    pytanie=szablony[typ].format(kotwica=wartosc),
                    oczekiwanie=OCZEKIWANIE_CYTAT,
                    kotwica=wartosc, typ_kotwicy=typ,
                    dokument_id=doc_id,
                    poczatek=zdanie.poczatek, koniec=zdanie.koniec,
                    zdanie_wzorcowe=zdanie.tekst,
                    para_id=id_b,
                ))
                przypadki.append(Przypadek(
                    id=id_b,
                    kategoria=PULAPKA_LICZBOWA if typ in ("kwota", "okres")
                              else BEZ_POKRYCIA,
                    jezyk=korpus.jezyk,
                    pytanie=szablony[typ].format(kotwica=bliznik),
                    oczekiwanie=OCZEKIWANIE_ODMOWA,
                    kotwica=bliznik, typ_kotwicy=typ,
                    para_id=id_a,
                    uwagi=f"bliźniak {wartosc!r}; sprawdzono: brak w aktach",
                ))
                break                      # jedna para na zdanie

    return przypadki


def generuj_szczelnosc(zrodlo: Korpus, cel: Korpus,
                       ile: int = 20, ziarno: int = 42) -> list[Przypadek]:
    """Fakty z jednej sprawy, zadawane w drugiej — muszą dać odmowę.

    To jest ilościowa wersja tego, co `tests/test_panel_izolacja_spraw.py`
    sprawdza strukturalnie. Test jednostkowy dowodzi, że zapytanie niesie
    `sprawa_id`; ten pomiar sprawdza, czy przy setkach prób model ani razu
    nie wyprodukuje treści z akt, do których nie sięgnął.

    Próg jest zerowy. Jedno trafienie to naruszenie tajemnicy zawodowej,
    a nie „spadek metryki".
    """
    los = random.Random(ziarno)
    szablony = _szablony(cel.jezyk)
    przypadki: list[Przypadek] = []

    doc_ids = sorted(zrodlo.dokumenty)
    los.shuffle(doc_ids)

    for doc_id in doc_ids:
        if len(przypadki) >= ile:
            break
        zdania = podziel_na_zdania(zrodlo.dokumenty[doc_id], jezyk=zrodlo.jezyk)
        for zdanie in zdania:
            if len(przypadki) >= ile:
                break
            if not zdanie_nadaje_sie(zdanie.tekst):
                continue
            for typ, wartosc in znajdz_kotwice(zdanie, zrodlo.jezyk):
                if typ not in szablony:
                    continue
                # Kotwica MUSI być obecna w źródle i nieobecna w celu.
                if not zrodlo.zawiera(wartosc) or cel.zawiera(wartosc):
                    continue
                przypadki.append(Przypadek(
                    id=_identyfikator("szczelnosc", str(cel.sprawa_id),
                                      doc_id, wartosc),
                    kategoria=SZCZELNOSC, jezyk=cel.jezyk,
                    pytanie=szablony[typ].format(kotwica=wartosc),
                    oczekiwanie=OCZEKIWANIE_ODMOWA,
                    kotwica=wartosc, typ_kotwicy=typ,
                    uwagi=(f"kotwica pochodzi ze sprawy {zrodlo.sprawa_id}, "
                           f"pytanie zadane w sprawie {cel.sprawa_id}"),
                ))
                break

    return przypadki


def statystyki(przypadki: list[Przypadek]) -> dict:
    """Rozkład wygenerowanego zbioru — do raportu i do kontroli sanity."""
    from collections import Counter

    return {
        "razem": len(przypadki),
        "wg_kategorii": dict(Counter(p.kategoria for p in przypadki)),
        "wg_jezyka": dict(Counter(p.jezyk for p in przypadki)),
        "wg_typu_kotwicy": dict(Counter(p.typ_kotwicy for p in przypadki)),
        "odpowiadalnych": sum(1 for p in przypadki if p.odpowiadalny),
        "odmownych": sum(1 for p in przypadki if not p.odpowiadalny),
        "par": sum(1 for p in przypadki if p.para_id) // 2,
    }
