"""Wyszukiwanie fragmentów — warunek skalowania do stu dokumentów.

PROBLEM
    Wcześniejsza wersja wrzucała całą treść sprawy do jednego zapytania.
    Przy 8k kontekstu starcza to na 2–3 pisma. Przy stu dokumentach
    (typowa sprawa karna to setki stron) model dostawał urwane akta
    i odpowiadał na podstawie tego, co się zmieściło — czyli losowo.

ROZWIĄZANIE
    Dokumenty dzielone na fragmenty Z ZACHOWANIEM OFFSETÓW w oryginale,
    ranking BM25 z obsługą polskiej fleksji, do modelu trafia tylko to,
    co trafne.

DLACZEGO OFFSETY SĄ KLUCZOWE
    Weryfikator cytatów porównuje zakres znaków z treścią dokumentu
    ŹRÓDŁOWEGO. Gdyby fragmenty miały własną numerację, każdy cytat
    wskazywałby w próżnię. Każdy fragment niesie więc pozycję startową
    w oryginale i wszystkie offsety są do niego przeliczane.

DLACZEGO BM25, A NIE WEKTORY
    Wyszukiwanie wektorowe gubi sygnatury, daty i numery — a w pismach
    procesowych to połowa zapytań ("co ustalono w II K 147/26",
    "kiedy doręczono"). BM25 jest dokładny tam, gdzie wektory zawodzą,
    działa bez GPU i bez dodatkowego modelu do pobrania.

    Miejsce na dołożenie wektorów jest przygotowane (`polacz_rankingi`)
    — docelowo hybryda, zgodnie z ADR-0004.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

# ── polska normalizacja ─────────────────────────────────────────────

STOPSLOWA = frozenset("""
a aby albo ale ani az bez bo by byc byl byla byly bylo byc chociaz co coz
czy czyli dla do gdy gdyz gdzie go i ich ile im inne iz ja jak jakby jaki
je jego jej jemu jest jestem jesli juz kazdy kiedy kto ktora ktore ktorego
ktorej ktory ktorym ku lecz lub ma majac mam mi mimo mnie moga moze mozna
mu my na nad nam nami nas nasz nasza nasze naszego nie niech nim nimi niz
o od oraz po pod podczas ponad poniewaz przed przez przy raz sa sie sobie
sposob swoje ta tak taka take takze tam te tego tej temu ten teraz tez to
tobie tu tutaj twoj twoja twoje ty tych tylko tym u w we wie wiec wszystko
wtedy wy za ze zeby
""".split())

# Końcówki fleksyjne odcinane przy budowie rdzenia.
#
# Lista jest sortowana po długości malejąco AUTOMATYCZNIE — ręczne
# układanie kolejności jest źródłem cichych błędów: gdyby "em" trafiło
# przed "iem", "świadkiem" dałoby rdzeń "swiadki" zamiast "swiadk"
# i przestałoby się schodzić ze "świadka".
#
# Uwzględnione są też formy nieosobowe ("doręczono") i odsłowne
# ("doręczenie", "doręczenia") — w pismach procesowych to najczęstszy
# sposób opisywania czynności, a bez nich pytanie "kiedy doręczono"
# nie trafiałoby w dokument mówiący o "doręczeniu".
_KONCOWKI_SUROWE = """
iejszego iejszemu iejszych ejszego ejszemu aniami eniami owaniem owania
owanie aniach eniach iejszy eniami ajacy acego eniem aniem eniu aniu
enie enia anie ania ono ano ych emu ego iej imi ami owi iem ach owy
ie ia em ym im ej ow om y a e i u o
""".split()

KONCOWKI: tuple[str, ...] = tuple(
    sorted(set(_KONCOWKI_SUROWE), key=len, reverse=True)
)

MIN_RDZEN = 4


def _bez_ogonkow(tekst: str) -> str:
    """⚠️ NFD nie rozkłada „ł" (U+0142) — to odrębna litera, nie „l"
    ze znakiem diakrytycznym. Bez jawnej podmiany „doręczył" i „doreczyl"
    trafiałyby na różne rdzenie, a wyszukiwarka gubiłaby połowę
    polskich form czasownikowych.
    """
    tekst = tekst.replace("ł", "l").replace("Ł", "L")
    rozlozony = unicodedata.normalize("NFD", tekst)
    return "".join(z for z in rozlozony if unicodedata.category(z) != "Mn")


def rdzen(slowo: str) -> str:
    """Prymitywny rdzeń — odcięcie końcówki fleksyjnej.

    Nie jest to stemmer w sensie lingwistycznym i nie ma nim być.
    Ma sprawiać, że "doręczono", "doręczenie" i "doręczenia" trafiają
    na siebie. Numery i sygnatury zostają nietknięte — tam liczy się
    dokładność, nie fleksja.
    """
    slowo = _bez_ogonkow(slowo.casefold())
    if any(z.isdigit() for z in slowo):
        return slowo
    for koncowka in KONCOWKI:
        if len(slowo) - len(koncowka) >= MIN_RDZEN and slowo.endswith(koncowka):
            return slowo[: -len(koncowka)]
    return slowo


# ⚠️ STOPSŁOWA ANGIELSKIE — BRAK ICH BYŁ USTERKĄ MIERZALNĄ.
#
# `STOPSLOWA` wyżej jest listą polską. Zastosowana do tekstu angielskiego
# nie usuwa niczego: „the", „of", „and", „that", „is", „for" liczą się
# jako słowa znaczące.
#
# Skutek zmierzony 14.08.2026 przy kontroli wsparcia (`wsparcie.oszacuj`):
# angielskie twierdzenia dostawały pokrycie 0,20–0,29 zamiast realnego,
# bo mianownik pęczniał od słów funkcyjnych, których w cytacie akurat
# nie było. Przy progu 0,30 kwalifikowało to poprawne twierdzenia jako
# „brak wsparcia" — kontrola odrzucałaby je, zanim ktokolwiek je przeczyta.
#
# Dla BM25 skutek jest łagodniejszy (IDF i tak spycha częste słowa
# w dół), ale też realny: „the" w zapytaniu punktuje każdy fragment.

STOPSLOWA_EN = frozenset("""
a an the this that these those and or but nor for yet so as if than then
of in on at by to from with without within into onto upon about above below
under over between among during before after since until while
is are was were be been being am do does did done doing have has had having
will would shall should may might must can could
it its it's they them their there here he she his her him we us our you your
i me my no not any all each every both few more most other some such
which who whom whose what when where why how
""".split())


WZORZEC_TOKENU = re.compile(r"[0-9]+(?:[./][0-9]+)*|[a-ząćęłńóśźż]+", re.IGNORECASE)

# Zwijanie białych znaków przy budowie wsadu dla modelu — patrz
# `dla_modelu()`. Skompilowany na poziomie modułu, a nie w pętli po
# zdaniach: przy dużej sprawie ta pętla przechodzi dziesiątki tysięcy
# zdań przy każdym pytaniu.
_ODSTEPY = re.compile(r"\s+")


def tokenizuj(tekst: str, jezyk: str | None = None) -> list[str]:
    """Tokeny znaczące. Stopsłowa angielskie WYŁĄCZNIE przy `jezyk="en"`.

    ⚠️ DOMYŚLNIE NIE ODSIEWAMY LISTY ANGIELSKIEJ. TO NIE JEST OSTROŻNOŚĆ,
       TYLKO NAPRAWA BŁĘDU, KTÓRY TU POPEŁNIONO 14.08.2026.

    Pierwsza wersja odsiewała domyślnie OBIE listy, „bo zbiory prawie
    się nie pokrywają". Pokrywają się i to w miejscach kosztownych:

        on   — po angielsku przyimek, po polsku ZAIMEK OSOBOWY
        to   — po angielsku partykuła, po polsku zaimek wskazujący
        do, we, by, a, no — pełnoprawne wyrazy polskie

    „on" wycinane z polskiego protokołu przesłuchania usuwa podmiot
    zdania. A `tokenizuj` zasila `Indeks`, czyli CAŁY retrieval BM25 —
    więc zmiana dotknęła nie jednej miary, tylko doboru dokumentów
    i zdań dla każdego pytania.

    Skutek zmierzony pełnym przebiegiem: J-4 (odmowa fałszywa) wzrosła
    z 12,5% na 56,2% przy niezmienionej reszcie potoku. Kontrola
    wsparcia, którą wtedy wpinano, nie odrzucała ani jednego twierdzenia —
    winna była wyłącznie ta zmiana.

    Lista angielska ma sens tam, gdzie język jest ZNANY i angielski:
    przy pokryciu leksykalnym w `wsparcie.oszacuj`. Tam jest podawana
    jawnie i tylko tam.
    """
    if jezyk == "en":
        odsiew = STOPSLOWA | STOPSLOWA_EN
    else:
        odsiew = STOPSLOWA

    surowe = WZORZEC_TOKENU.findall(tekst)
    return [
        rdzen(t) for t in surowe
        if len(t) > 1 and _bez_ogonkow(t.casefold()) not in odsiew
    ]


# ── sondy wyróżnikowe ───────────────────────────────────────────────

def _wyrozniki(tekst: str):
    """Import leniwy — `wyrozniki` importuje tylko `re`, ale trzymamy
    zależność w jedną stronę, żeby moduły dały się testować osobno."""
    from wyrozniki import wyrozniki as _w
    return _w(tekst)


def _rozbij_wyroznik(wartosc: str) -> set[str]:
    """Tanie sondy tekstowe dla wyróżnika sprowadzonego do wartości.

    Pełna ekstrakcja wyróżników z każdego zdania korpusu byłaby
    kosztowna (przy 320 dokumentach to kilkanaście tysięcy zdań).
    Sonda to część, która MUSI wystąpić dosłownie w każdym zapisie
    danego wyróżnika — rok w dacie, liczba w kwocie, numer w przepisie.

    ⚠️ Ograniczenie: data zapisana z rokiem dwucyfrowym („23.07.74")
    nie zawiera „1974" i sonda jej nie złapie. W pismach procesowych
    rok pisze się w pełni, więc przyjmujemy to świadomie — sonda ma
    być tania, a nie kompletna. Pełne porównanie i tak idzie po wartości.
    """
    czesci: set[str] = set()
    if wartosc.count("-") == 2 and wartosc[:4].isdigit():        # data ISO
        rok, miesiac, dzien = wartosc.split("-")
        czesci.add(rok)
        czesci.add(str(int(dzien)))
    elif wartosc.startswith("art"):                              # przepis
        cyfry = "".join(z if z.isdigit() else " " for z in wartosc).split()
        czesci.update(cyfry)
    elif "." in wartosc and wartosc.replace(".", "").isdigit():  # kwota
        czesci.add(wartosc.split(".")[0])
    else:                                                        # sygnatura
        cyfry = "".join(z if z.isdigit() else " " for z in wartosc).split()
        czesci.update(c for c in cyfry if len(c) >= 2)
    return {c for c in czesci if c}


# ── fragmenty ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Fragment:
    """Kawałek dokumentu z pozycją w ORYGINALE.

    `poczatek` i `koniec` odnoszą się do pełnej treści dokumentu, nie do
    fragmentu — dzięki temu cytat wskazany przez model da się zweryfikować
    wobec źródła.
    """
    dokument_id: str
    nazwa: str
    poczatek: int
    koniec: int
    tresc: str

    @property
    def klucz(self) -> str:
        return f"{self.dokument_id}:{self.poczatek}"


ROZMIAR_FRAGMENTU = 1400
ZAKLADKA = 250


def podziel(dokument_id: str, nazwa: str, tresc: str,
            rozmiar: int = ROZMIAR_FRAGMENTU,
            zakladka: int = ZAKLADKA) -> list[Fragment]:
    """Dzieli dokument na fragmenty z zakładką.

    Zakładka jest po to, żeby zdanie rozcięte na granicy nie przepadło —
    w piśmie procesowym granica akapitu bywa dokładnie tam, gdzie jest
    istotne ustalenie.

    Cięcie próbuje trafić w koniec akapitu lub zdania, żeby fragment
    był czytelny dla modelu.
    """
    if not tresc:
        return []
    if len(tresc) <= rozmiar:
        return [Fragment(dokument_id, nazwa, 0, len(tresc), tresc)]

    fragmenty: list[Fragment] = []
    start = 0
    while start < len(tresc):
        koniec = min(start + rozmiar, len(tresc))
        if koniec < len(tresc):
            okno = tresc[start:koniec]
            # Preferuj koniec akapitu, potem koniec zdania.
            for separator in ("\n\n", ".\n", ". ", "\n"):
                pozycja = okno.rfind(separator)
                if pozycja > rozmiar * 0.5:
                    koniec = start + pozycja + len(separator)
                    break
        fragmenty.append(
            Fragment(dokument_id, nazwa, start, koniec, tresc[start:koniec])
        )
        if koniec >= len(tresc):
            break
        start = max(start + 1, koniec - zakladka)
    return fragmenty


def podziel_wiele(dokumenty: dict[str, str],
                  nazwy: dict[str, str] | None = None) -> list[Fragment]:
    nazwy = nazwy or {}
    wynik: list[Fragment] = []
    for doc_id, tresc in dokumenty.items():
        wynik.extend(podziel(doc_id, nazwy.get(doc_id, doc_id), tresc))
    return wynik


# ── BM25 ────────────────────────────────────────────────────────────

K1 = 1.5
B = 0.75


class Indeks:
    """BM25 nad fragmentami. Budowany od nowa przy każdym pytaniu.

    Przy stu dokumentach to nadal ułamek sekundy, a odpada cały problem
    unieważniania indeksu po dodaniu dokumentu — w kancelarii dokumenty
    dochodzą w trakcie pracy nad sprawą.
    """

    def __init__(self, fragmenty: list[Fragment],
                 jezyki: list[str] | None = None):
        """`jezyki` — lista RÓWNOLEGŁA do `fragmenty`, po jednym wpisie.

        ⚠️ DLACZEGO LISTA, A NIE SŁOWNIK PO `dokument_id`.
        `Indeks` punktuje i `Fragment` (ma `dokument_id`), i `Zdanie`
        (nie ma). Lista równoległa obsługuje oba bez wymuszania wspólnego
        interfejsu na typach, które poza polem `tresc` nie mają ze sobą nic.

        Po co w ogóle: baza trzyma język KAŻDEGO dokumentu (sprawa 3 —
        320 pl, sprawa 4 — 397 en, 4 pl), a tokenizacja dotąd tego nie
        używała. Angielskie „the", „of", „that" indeksowały się jako
        wyrazy treści i rozcieńczały ranking dokumentów Lacey.

        Odsiew jest per pozycja, więc polskie dokumenty w sprawie
        angielskiej dostają polską listę stopsłów, a nie odwrotnie —
        to ta pułapka, przez którą globalne włączenie listy angielskiej
        wycięło „on", „to", „do" z polskich protokołów.
        """
        self.fragmenty = fragmenty
        if jezyki is None:
            self._tokeny = [tokenizuj(f.tresc) for f in fragmenty]
        else:
            # ⚠️ `zip` przy różnych długościach ucina po krótszej i robi to
            # bez słowa. `punktuj` indeksuje potem `self._czestosc[i]` po
            # pozycjach `self.fragmenty`, więc krótsza lista języków dałaby
            # IndexError w środku zapytania prawnika — w miejscu, które
            # z językami nie ma nic wspólnego, a więc trudnym do powiązania
            # z przyczyną. Lepiej paść tutaj i powiedzieć, o co chodzi.
            if len(jezyki) != len(fragmenty):
                raise ValueError(
                    f"jezyki ma {len(jezyki)} pozycji, fragmenty "
                    f"{len(fragmenty)} — listy muszą być równoległe")
            self._tokeny = [tokenizuj(f.tresc, j)
                            for f, j in zip(fragmenty, jezyki)]
        self._dlugosci = [len(t) for t in self._tokeny]
        self._srednia = (sum(self._dlugosci) / len(self._dlugosci)
                         if self._dlugosci else 0.0)

        self._czestosc: list[dict[str, int]] = []
        dokumentowe: dict[str, int] = {}
        for tokeny in self._tokeny:
            licznik: dict[str, int] = {}
            for t in tokeny:
                licznik[t] = licznik.get(t, 0) + 1
            self._czestosc.append(licznik)
            for t in licznik:
                dokumentowe[t] = dokumentowe.get(t, 0) + 1

        n = len(fragmenty)
        self._idf = {
            t: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for t, df in dokumentowe.items()
        }

    def punktuj(self, zapytanie: str,
                jezyk_zapytania: str | None = None) -> list[tuple[float, Fragment]]:
        """`jezyk_zapytania` dotyczy PYTANIA, nie dokumentów.

        Pytanie ma własny język, niezależny od akt: polski prawnik pyta
        po polsku o dokument angielski. Odsiewanie angielskich stopsłów
        z polskiego pytania wycięłoby „on", „to", „do" — czyli dokładnie
        ten błąd, tylko innymi drzwiami.
        """
        tokeny = tokenizuj(zapytanie, jezyk_zapytania)
        if not tokeny or not self.fragmenty:
            return []

        wyniki: list[tuple[float, Fragment]] = []
        for i, fragment in enumerate(self.fragmenty):
            punkty = 0.0
            dlugosc = self._dlugosci[i] or 1
            for token in tokeny:
                tf = self._czestosc[i].get(token, 0)
                if not tf:
                    continue
                idf = self._idf.get(token, 0.0)
                norma = 1 - B + B * dlugosc / (self._srednia or 1)
                punkty += idf * (tf * (K1 + 1)) / (tf + K1 * norma)
            if punkty > 0:
                wyniki.append((punkty, fragment))
        wyniki.sort(key=lambda p: p[0], reverse=True)
        return wyniki


def polacz_rankingi(*rankingi: list[tuple[float, Fragment]],
                    k: int = 60) -> list[tuple[float, Fragment]]:
    """Łączenie rankingów metodą RRF (Reciprocal Rank Fusion).

    Miejsce na dołożenie wyszukiwania wektorowego obok BM25 bez zmiany
    reszty pipeline'u — wystarczy podać drugi ranking (ADR-0004).
    """
    punkty: dict[str, float] = {}
    fragmenty: dict[str, Fragment] = {}
    for ranking in rankingi:
        for pozycja, (_, fragment) in enumerate(ranking, start=1):
            punkty[fragment.klucz] = punkty.get(fragment.klucz, 0.0) + 1 / (k + pozycja)
            fragmenty[fragment.klucz] = fragment
    polaczone = [(p, fragmenty[kl]) for kl, p in punkty.items()]
    polaczone.sort(key=lambda x: x[0], reverse=True)
    return polaczone


def wybierz(fragmenty: list[Fragment], zapytanie: str,
            ile: int = 8, budzet_znakow: int = 9000) -> list[Fragment]:
    """Najtrafniejsze fragmenty mieszczące się w budżecie kontekstu.

    Gdy zapytanie nie trafia w nic (pytanie o rzecz spoza akt), zwraca
    kilka pierwszych fragmentów, żeby model miał na czym oprzeć ODMOWĘ.
    Odmowa bez kontekstu bywa mylona przez model z brakiem danych
    technicznym.
    """
    if not fragmenty:
        return []

    ranking = Indeks(fragmenty).punktuj(zapytanie)
    kandydaci = [f for _, f in ranking[:ile]] if ranking else fragmenty[:3]

    wybrane: list[Fragment] = []
    zuzyte = 0
    for fragment in kandydaci:
        if zuzyte + len(fragment.tresc) > budzet_znakow and wybrane:
            break
        wybrane.append(fragment)
        zuzyte += len(fragment.tresc)

    # Kolejność czytania: dokument po dokumencie, od początku.
    wybrane.sort(key=lambda f: (f.dokument_id, f.poczatek))
    return wybrane


# ── wybór ZDAŃ — jednostka cytatu ───────────────────────────────────
#
# ⚠️ DLACZEGO ZDANIE, A NIE FRAGMENT
#
# `wybierz` zwraca okna po ~1400 znaków, cięte na granicy akapitu albo
# zdania — ale gdy żadna nie wypada w oknie, cięcie idzie w środku.
# Dopóki model przepisywał cytat sam, nie miało to znaczenia: cytował
# to, co widział, a kod szukał tego w pełnej treści.
#
# Przy cytowaniu po NUMERZE zdania ma to znaczenie rozstrzygające.
# Podział takiego okna na zdania daje pozycje w rodzaju:
#
#     [1] za w przypadku wnioskowania orzeczenia takiej instytucji
#     [2] n/d
#
# Pierwsza to urwany ogon zdania z poprzedniego okna, druga to śmieć
# po konwersji PDF-a. Gdyby model wskazał [1], kod wziąłby dosłownie
# ten urwany ciąg i podał prawnikowi jako cytat z akt.
#
# Dlatego podział na zdania idzie po PEŁNYM dokumencie, gdzie offsety
# są prawdziwe, a ranking punktuje całe zdania. Warstwa fragmentów
# zostaje do rankingu dokumentów (`dokumenty_trafne`), gdzie sprawdza
# się dobrze i gdzie granice okien nie mają znaczenia.

@dataclass(frozen=True)
class ZdanieZAkt:
    """Zdanie z numerem GLOBALNYM w obrębie jednego wywołania modelu.

    `numer` jest numerem prezentacyjnym — tym, który zobaczy model
    i który wskaże w odpowiedzi. Jest globalny dla całego wsadu, bo
    numeracja per dokument kolidowałaby przy kilku dokumentach naraz.

    `poczatek`/`koniec` odnoszą się do ORYGINAŁU dokumentu `dokument_id`,
    więc cytat odtworzony z tych offsetów przechodzi weryfikację
    znak w znak.
    """
    numer: int
    dokument_id: str
    nazwa: str
    poczatek: int
    koniec: int
    tekst: str


@dataclass(frozen=True)
class WyborZdan:
    """Ponumerowany wsad dla modelu wraz z mapą powrotną.

    Trzy rzeczy, które muszą pochodzić z jednego miejsca, żeby nie
    mogły się rozjechać: tekst pokazany modelowi, zbiór dopuszczalnych
    numerów w schemacie JSON i odwzorowanie numeru na zakres w źródle.
    """
    zdania: tuple[ZdanieZAkt, ...]

    @property
    def numery(self) -> list[int]:
        """Dozwolone wartości enum w schemacie odpowiedzi."""
        return [z.numer for z in self.zdania]

    def rozwiaz(self, numer: int) -> ZdanieZAkt | None:
        for z in self.zdania:
            if z.numer == numer:
                return z
        return None

    def dla_modelu(self, naglowki: bool = True) -> str:
        """Wsad w postaci pokazywanej modelowi, pogrupowany po dokumentach.

        ⚠️ Białe znaki są tu ZWIJANE, a offsety zostają nietknięte.

        Tekst z PDF-a ma łamania wierszy w środku zdań i słupki spacji
        z układu strony. Pokazane modelowi w surowej postaci rozbijają
        jedno zdanie na kilka linii, przez co „[12]" wygląda jak numer
        czterech osobnych pozycji i model gubi numerację.

        Zwinięcie jest bezpieczne właśnie dlatego, że model wskazuje
        NUMER, a nie przepisuje treść: cytat kod odtwarza z `poczatek`
        i `koniec` w oryginale, więc to, co widzi prawnik, pochodzi
        ze źródła znak w znak — niezależnie od tego, jak wsad wyglądał.
        """
        linie: list[str] = []
        biezacy: str | None = None
        for z in self.zdania:
            if naglowki and z.dokument_id != biezacy:
                if linie:
                    linie.append("")
                linie.append(f"=== DOKUMENT id={z.dokument_id} ({z.nazwa}) ===")
                biezacy = z.dokument_id
            # Podstawienie stoi w osobnej zmiennej, a nie wewnątrz klamry
            # f-stringa, bo backslash w części WYRAŻENIA jest dozwolony
            # dopiero od Pythona 3.12 (PEP 701). Na 3.11 plik nie
            # kompilował się wcale — a że pracujemy na 3.13, było to
            # niewidoczne aż do bramki CI. Deklarujemy >=3.11, więc kod
            # ma się na 3.11 kompilować.
            zwiniete = _ODSTEPY.sub(" ", z.tekst).strip()
            linie.append(f"[{z.numer}] {zwiniete}")
        return "\n".join(linie)

    def __len__(self) -> int:
        return len(self.zdania)


def _jezyk_pytania(zapytanie: str) -> str:
    """Język pytania — rozpoznany, z zapasowym polskim.

    Pytania są krótkie, więc rozpoznanie bywa niepewne. Przy „nieznanym"
    wracamy do polskiego, bo instalacja jest polska, a polska lista
    stopsłów nie zawiera wyrazów angielskich — pomyłka w tę stronę
    nic nie psuje. Pomyłka w drugą stronę wycina „on" i „to" z akt.
    """
    try:
        import jezyk as _mod_jezyk
        rozpoznanie = _mod_jezyk.rozpoznaj(zapytanie)
        return rozpoznanie.jezyk if rozpoznanie.jezyk in ("pl", "en") else "pl"
    except Exception:                                     # noqa: BLE001
        return "pl"


def wybierz_zdania(dokumenty: dict[str, str], zapytanie: str,
                   nazwy: dict[str, str] | None = None,
                   jezyki: dict[str, str] | None = None,
                   budzet_znakow: int = 9000,
                   maks_zdan: int = 120,
                   filtr_jakosci: bool = True) -> WyborZdan:
    """Najtrafniejsze CAŁE zdania mieszczące się w budżecie.

    Kolejność prezentacji jest kolejnością czytania — dokument po
    dokumencie, od początku — a nie kolejnością rankingu. Model, który
    dostaje zdania poprzestawiane, gubi następstwo zdarzeń, a w aktach
    następstwo bywa treścią ustalenia.
    """
    from zdania import podziel_na_zdania, zdanie_uzyteczne

    nazwy = nazwy or {}
    jezyki = jezyki or {}

    wszystkie: list[tuple[str, object]] = []
    for doc_id, tresc in dokumenty.items():
        jez = jezyki.get(doc_id, "pl")
        for z in podziel_na_zdania(tresc, jezyk=jez):
            if filtr_jakosci and not zdanie_uzyteczne(z.tekst):
                continue
            wszystkie.append((doc_id, z))

    if not wszystkie:
        return WyborZdan(())

    # Każde zdanie tokenizowane językiem SWOJEGO dokumentu, a pytanie
    # swoim własnym — rozpoznanym, nie założonym.
    jezyk_pytania = _jezyk_pytania(zapytanie)
    ranking = Indeks(
        [z for _, z in wszystkie],
        jezyki=[jezyki.get(doc_id, "pl") for doc_id, _ in wszystkie],
    ).punktuj(zapytanie, jezyk_pytania)

    # ⚠️ ZDANIA TRAFNE TO DOPIERO KOTWICE, NIE CAŁY WSAD.
    #
    # `Indeks.punktuj` zwraca wyłącznie pozycje z punktacją dodatnią,
    # czyli dzielące token z pytaniem. Przy fragmencie na 1400 znaków
    # to prawie zawsze coś daje; przy pojedynczym zdaniu — rzadko.
    # Pomiar: pytanie o cztery słowa trafiało w 7 zdań i zużywało
    # 2 104 z 9 000 znaków budżetu. Reszta budżetu przepadała, a fakt
    # wyrażony bez żadnego słowa z pytania był niewidoczny.
    #
    # Trafione zdania traktujemy więc jako kotwice i dobieramy wokół
    # nich sąsiedztwo, dopóki starcza budżetu. Daje to dwie rzeczy:
    # kontekst, w którym zdanie jest zrozumiałe (samo „Sąd podzielił
    # ten pogląd." nic nie znaczy), oraz zdania powiązane treściowo,
    # a nie leksykalnie.
    indeksy: dict[str, list] = {}
    for doc_id, z in wszystkie:
        indeksy.setdefault(doc_id, []).append(z)
    pozycja = {(doc_id, id(z)): i
               for doc_id, lista in indeksy.items()
               for i, z in enumerate(lista)}
    gdzie = {id(z): doc_id for doc_id, z in wszystkie}

    # ⚠️ ZDANIA NIOSĄCE WYRÓŻNIK Z PYTANIA WCHODZĄ ZAWSZE.
    #
    # ZMIERZONA PRZYCZYNA 23 FAŁSZYWYCH ODMÓW (benchmark 2026-08-14 20:02).
    #
    # Śledzenie pojedynczego przypadku pokazało rzecz, której nie widać
    # w miarach zbiorczych: przy pytaniu o datę 23 lipca 1974 r. model
    # dostał 12 zdań i w żadnym z nich tej daty NIE BYŁO. Odmówił więc
    # POPRAWNIE — w pokazanym mu materiale odpowiedzi rzeczywiście nie było.
    #
    # To nie była wada modelu ani zakotwiczenia, tylko WYSZUKIWARKI.
    # BM25 traktuje „23" i „1974" jak zwykłe tokeny, a daty stoją
    # w aktach na każdej stronie — więc mają niską wagę IDF i zdanie
    # z szukaną datą nie wchodziło do czołówki rankingu.
    #
    # Wyróżnik z pytania (data, kwota, sygnatura, przepis) jest więc
    # traktowany jak twarde kryterium, nie jak słowo. Porównanie idzie
    # po WARTOŚCI, więc inny zapis tej samej daty też trafia.
    kotwice_wyroznikowe: list = []
    _p = _wyrozniki(zapytanie)
    if _p.zlozone:
        # Tani wstępny filtr — pełna ekstrakcja na każdym zdaniu korpusu
        # byłaby kosztowna. Sondy to części wyróżnika, które muszą
        # wystąpić dosłownie: rok daty, liczba kwoty, numer przepisu.
        sondy = [_rozbij_wyroznik(w) for w in _p.zlozone]
        for _doc_id, _z in wszystkie:
            if not any(all(c in _z.tekst for c in zestaw) for zestaw in sondy):
                continue
            if _wyrozniki(_z.tekst).zlozone & _p.zlozone:
                kotwice_wyroznikowe.append(_z)

    if ranking:
        kotwice = kotwice_wyroznikowe + [z for _, z in ranking[:maks_zdan]]
    else:
        # Brak trafienia — pierwsze zdania, żeby model miał na czym
        # oprzeć ODMOWĘ. Odmowa bez kontekstu bywa mylona przez model
        # z brakiem danych technicznym.
        kotwice = kotwice_wyroznikowe or [z for _, z in wszystkie[:6]]

    wybrane_ids: set[int] = set()
    zuzyte = 0

    def dodaj(z) -> bool:
        nonlocal zuzyte
        if id(z) in wybrane_ids:
            return True
        koszt = len(z.tekst) + 6                # narzut na „[123] ”
        if zuzyte + koszt > budzet_znakow and wybrane_ids:
            return False
        wybrane_ids.add(id(z))
        zuzyte += koszt
        return True

    for z in kotwice:
        if not dodaj(z):
            break

    # Rozszerzanie o sąsiedztwo, warstwami — najpierw ±1 zdanie wokół
    # każdej kotwicy, potem ±2. Warstwowo, a nie po kolei, żeby budżet
    # rozłożył się równo na wszystkie kotwice zamiast wyczerpać się
    # na sąsiedztwie pierwszej.
    for odleglosc in (1, 2):
        if zuzyte >= budzet_znakow:
            break
        for z in list(kotwice):
            doc_id = gdzie[id(z)]
            lista = indeksy[doc_id]
            i = pozycja[(doc_id, id(z))]
            for j in (i - odleglosc, i + odleglosc):
                if 0 <= j < len(lista):
                    dodaj(lista[j])

    wybrane = [(gdzie[id(z)], z) for _, z in wszystkie if id(z) in wybrane_ids]
    wybrane.sort(key=lambda para: (para[0], para[1].poczatek))

    return WyborZdan(tuple(
        ZdanieZAkt(numer=i, dokument_id=doc_id, nazwa=nazwy.get(doc_id, doc_id),
                   poczatek=z.poczatek, koniec=z.koniec, tekst=z.tekst)
        for i, (doc_id, z) in enumerate(wybrane, start=1)
    ))


def dokumenty_trafne(fragmenty: list[Fragment], zapytanie: str,
                     ile: int = 12) -> list[str]:
    """Identyfikatory dokumentów, które w ogóle warto analizować.

    Używane przez etap mapowania: przy stu dokumentach nie ma sensu
    czytać wszystkich, jeśli pytanie dotyczy trzech.
    """
    # ⚠️ DOKUMENT NIOSĄCY WYRÓŻNIK Z PYTANIA WCHODZI ZAWSZE.
    #
    # Ta sama usterka co przy wyborze zdań, ale PIĘTRO WYŻEJ — i dlatego
    # przez chwilę niewidoczna. Po naprawieniu warstwy zdań wyglądało,
    # że wyszukiwanie działa: zdanie z szukaną datą trafiało do wsadu.
    # Trafiało jednak tylko wtedy, gdy właściwy dokument w ogóle
    # dotarł do tego etapu.
    #
    # Pomiar z 14.08.2026 na korpusie 320 orzeczeń: w 2 z 4 sprawdzonych
    # pytań zakotwiczonych właściwy dokument NIE ZNALAZŁ SIĘ w dwunastce
    # wybranej przez BM25. Model nie miał szans — nie dostał akt,
    # w których leżała odpowiedź.
    #
    # Powód jest ten sam: BM25 traktuje „2023" i „6" jak zwykłe tokeny,
    # a daty stoją w aktach na każdej stronie, więc mają niską wagę IDF.
    kandydaci_wyroznikowe: list[str] = []
    _p = _wyrozniki(zapytanie)
    if _p.zlozone:
        # Sonda na wyróżnik: WSZYSTKIE jego części muszą wystąpić.
        # „Którakolwiek" przepuszczała fragment z samym rokiem, a rok
        # stoi w aktach wszędzie — pełna ekstrakcja szła wtedy na
        # tysiącach fragmentów i wybór dokumentów trwał ~10 s.
        sondy = [_rozbij_wyroznik(w) for w in _p.zlozone]
        for f in fragmenty:
            if f.dokument_id in kandydaci_wyroznikowe:
                continue
            if not any(all(c in f.tresc for c in zestaw) for zestaw in sondy):
                continue
            if _wyrozniki(f.tresc).zlozone & _p.zlozone:
                kandydaci_wyroznikowe.append(f.dokument_id)

    # ⚠️ USTALENIE 15.08.2026 — ŚWIADOMIE NIEZMIENIONE, NIE PRZEOCZONE.
    #
    # Ten `Indeks` powstaje BEZ `jezyki`, więc angielskie dokumenty są
    # tokenizowane samą listą polskich stopsłów: „the", „of", „that"
    # indeksują się jako wyrazy treści. Dokładnie ten skutek opisuje
    # docstring `Indeks.__init__` — a naprawiony został tylko na poziomie
    # ZDAŃ (`wybierz_zdania`), nie DOKUMENTÓW, czyli nie tam, gdzie waży
    # najwięcej: to ten etap rozstrzyga, których akt model w ogóle
    # nie zobaczy.
    #
    # Nie zmieniane tutaj z premedytacją. Retrieval jest etapem najdalej
    # w górę potoku i w tej sesji trzykrotnie potwierdziło się, że zmiana
    # w nim przestawia wszystkie miary poniżej. Poprawka wymaga własnego
    # przebiegu porównawczego, a nie dołożenia do zestawu innych zmian —
    # inaczej znowu nie da się przypisać różnicy przyczynie.
    ranking = Indeks(fragmenty).punktuj(zapytanie)
    kolejnosc: list[str] = list(kandydaci_wyroznikowe[:ile])
    for _, fragment in ranking:
        if len(kolejnosc) >= ile:
            break
        if fragment.dokument_id not in kolejnosc:
            kolejnosc.append(fragment.dokument_id)
    return kolejnosc
