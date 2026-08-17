"""Głęboka analiza akt — pipeline wieloetapowy (map-reduce).

PROBLEM
    Jedno wywołanie modelu nad wklejonymi aktami daje odpowiedź płytką:
    jedno zdanie i cytat. To wyszukiwarka, nie analiza. Prawnik potrzebuje
    ustaleń, wniosków, rozbieżności i luk dowodowych — a przy stu
    dokumentach jedno wywołanie w ogóle się nie mieści w kontekście.

ROZWIĄZANIE — mapowanie i redukcja
    ┌── 1. DEKOMPOZYCJA ────────────────────────────────────────────┐
    │  model rozbija pytanie na wątki analityczne                   │
    ├── 2. WYBÓR DOKUMENTÓW ────────────────────────────────────────┤
    │  BM25 wskazuje, które z N dokumentów w ogóle warto czytać     │
    ├── 3. MAPOWANIE (osobne wywołanie na dokument) ────────────────┤
    │  ustalenia faktyczne z cytatami — każde wywołanie mieści      │
    │  się w kontekście niezależnie od rozmiaru akt                 │
    ├── 4. PRZEPISY ────────────────────────────────────────────────┤
    │  retrieval po korpusie przepisów (odrębna przestrzeń)         │
    ├── 5. SYNTEZA ─────────────────────────────────────────────────┤
    │  wnioski, rozbieżności, luki dowodowe, podstawa prawna        │
    ├── 6. WERYFIKACJA ─────────────────────────────────────────────┤
    │  mechaniczne sprawdzenie każdego cytatu wobec źródła          │
    └───────────────────────────────────────────────────────────────┘

ZAKOTWICZENIE WNIOSKÓW — istota konstrukcji
    Ustalenia faktyczne MUSZĄ mieć zweryfikowany cytat. Wnioski cytatu
    nie mają — bo są rozumowaniem, nie faktem. Zamiast tego wskazują
    NUMERY USTALEŃ, z których wynikają.

    Wniosek oparty na ustaleniu, które przepadło na weryfikacji, jest
    odrzucany razem z nim. Rozumowanie jest więc śledzalne do zdania
    w aktach, choć samo nie podlega weryfikacji maszynowej — patrz
    ograniczenie zapisane wprost w ADR-0006.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

KORZEN = Path(__file__).resolve().parent
sys.path.insert(0, str(KORZEN))
sys.path.insert(0, str(KORZEN.parent / "src" / "aplikacje"))

import jezyk as mod_jezyk  # noqa: E402
import schematy  # noqa: E402
import wyszukiwarka  # noqa: E402
from agenci.weryfikator_cytatow import (  # noqa: E402
    Cytat, Twierdzenie, WeryfikatorCytatow, znajdz_fragment,
)

# Adres modelu z jednego miejsca, walidowany przy imporcie — patrz
# `panel/siec.py`. Wcześniej był tu własny literał.
from siec import ADRES_MODELU as OLLAMA  # noqa: E402

# ── DOBÓR MODELU PER ETAP ────────────────────────────────────────────
#
# Mapowanie to 12 z 13 wywołań w jednej analizie i zadanie jest wąskie:
# znaleźć fakty i przepisać cytat dosłownie. To praca językowa, nie
# rozumowanie — mniejszy model robi to równie dobrze, a wielokrotnie
# szybciej.
#
# POMIAR NA TYM SPRZĘCIE (8 GB VRAM, AutoCAD zajmuje ~2,1 GB):
#
#   model                  czas    tok/s   rozkład      ustaleń  cytaty
#   bielik-11B  Q4_K_M    170,4s    4,6   13%/87% CPU/GPU   7     7/7
#   bielik-4.5B Q8_0       44,1s   34,4   100% GPU          7     7/7
#   minitron-7B Q4_K_M     22,0s   38,3   100% GPU          8     8/8
#
# Różnica NIE bierze się z liczby parametrów, tylko z tego, że 11B
# (6,7 GB) nie mieści się w wolnym VRAM. Część warstw ląduje na CPU
# i dławi całość — 13% warstw na procesorze kosztuje ~7× spowolnienia.
# Model mieszczący się w całości wygrywa nieproporcjonalnie do rozmiaru.
#
# Wniosek praktyczny: przy ograniczonym VRAM dobierać model do TEGO,
# CO ZOSTAŁO WOLNE, a nie do rozmiaru karty.

MODEL_MAPOWANIA = "bielik-lex-map"       # minitron-7B, mieści się w całości
MODEL_SYNTEZY = "bielik-lex-map"         # patrz uwaga niżej
MODEL = MODEL_MAPOWANIA                  # zgodność wsteczna

# Synteza to JEDNO wywołanie na analizę, więc dałoby się tu użyć
# większego modelu kosztem ~170 s. Przy 8 GB VRAM oznacza to jednak
# przeładowanie modelu (wyrzucenie mapującego z pamięci i wczytanie
# 11B), co dokłada kilkanaście sekund i wraca do pracy na CPU.
# Na maszynie produkcyjnej (GPU 24–48 GB) oba modele zmieszczą się
# naraz i wtedy MODEL_SYNTEZY = "bielik-lex-dev" ma sens.

MAKS_DOKUMENTOW_DO_ANALIZY = 12

# Ile treści dokumentu trafia do jednego wywołania mapowania.
#
# Pomiar z 14.08.2026 na orzeczeniu o objętości 54 tys. znaków:
#   budżet  kontekst   wsad     czas   ustaleń   rozkład
#    5 500      4 096  4 996    12,4s        0   100% GPU
#    9 000      8 192  7 782    40,2s        5   100% GPU
#   14 000     16 384  7 782    41,4s        5   100% GPU
#
# Przy 5 500 znaków wybrane fragmenty nie zawierały jeszcze tego, o co
# pytano — dokument dał ZERO ustaleń, choć odpowiedź w nim była.
# Podniesienie budżetu to różnica między znalezieniem a nieznalezieniem,
# warta trzykrotnie dłuższego wywołania.
#
# 14 000 nic nie dodaje, bo ogranicza już liczba fragmentów (`ile`),
# nie budżet znaków. Kontekst 8 192 mieści się w całości na GPU.
BUDZET_MAPOWANIA = 9000
FRAGMENTOW_NA_DOKUMENT = 6
BUDZET_PRZEPISOW = 3500

# ── KONTEKST — JEDNA WARTOŚĆ DLA WSZYSTKICH ETAPÓW ───────────────────
#
# ⚠️ DWA POWODY, DLA KTÓRYCH TA STAŁA MUSI BYĆ JEDNA I MUSI BYĆ UŻYWANA.
#
# 1. `num_ctx` obejmuje WSAD I ODPOWIEDŹ RAZEM.
#
#    Przy `BUDZET_MAPOWANIA = 9000` znaków i zmierzonym stosunku
#    ~2,74 znaku na token (log Ollamy: `task.n_tokens = 3726`) sam wsad
#    to ~3 285 tokenów, a z szablonem ~3 700. W oknie 4 096 zostawało
#    ~400 tokenów na odpowiedź — przy ośmiu ustaleniach z dosłownymi
#    cytatami potrzeba 600–900. Odpowiedź była ucinana w połowie.
#
#    To była przyczyna „cichych zer": pipeline meldował postęp
#    i zwracał ustalenia częściowe albo niepoprawny JSON, bo model
#    nie miał gdzie dokończyć zdania.
#
# 2. Każda zmiana `num_ctx` PRZEŁADOWUJE MODEL.
#
#    Mapowanie prosiło o 4 096, czat i synteza o 8 192. Ollama trzyma
#    model wczytany pod konkretny rozmiar okna, więc każda zmiana to
#    wyładowanie i wczytanie od nowa — kilkanaście sekund. Dokładnie
#    ten koszt, który grupowanie dokumentów po języku (patrz `analizuj`)
#    miało ograniczyć do jednej zamiany na analizę.
#
# Zmieściło się przy 8 GB VRAM: wagi 4,19 GB + cache KV ~0,8 GB
# (przy OLLAMA_KV_CACHE_TYPE=q8_0) ≈ 5,0 GB. Warunkiem jest
# OLLAMA_NUM_PARALLEL=1 — przy 8 slotach cache rośnie ośmiokrotnie
# i ląduje na CPU. Pilnuje tego `tests/test_konfiguracja_ollamy.py`.
KONTEKST = 8192

# Nazwa zachowana dla czytelności w miejscu wywołania mapowania.
KONTEKST_MAPOWANIA = KONTEKST


# ── wywołanie modelu ────────────────────────────────────────────────

def _wywolaj(zadanie: str, temperatura: float = 0.1,
             timeout: int = 900, model: str | None = None,
             kontekst: int = KONTEKST,
             schemat: dict | None = None) -> str:
    """Wywołanie modelu z opcjonalnym schematem wymuszanym przy dekodowaniu.

    `schemat` podany → Ollama kompiluje go do gramatyki i maskuje przy
    próbkowaniu tokeny, które by go złamały. `schemat` pominięty →
    zachowanie jak dotąd, czyli wyłącznie wymóg poprawnego JSON-a.

    Ścieżka bez schematu zostaje świadomie: przy bardzo długim `enum`
    kompilacja gramatyki bywa kosztowna, a cicha awaria całego etapu
    jest gorsza od wolniejszego parsowania po fakcie.
    """
    dane = json.dumps({
        "model": model or MODEL_MAPOWANIA,
        "prompt": zadanie,
        "stream": False,
        "format": schemat if schemat is not None else "json",
        "options": {"temperature": temperatura, "num_ctx": kontekst},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=dane,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as odp:
        return json.loads(odp.read())["response"]


def _bez_ogonkow(tekst: str) -> str:
    """Usuwa znaki diakrytyczne — z jawną obsługą „ł".

    ⚠️ NFD NIE rozkłada „ł" (U+0142). To odrębna litera, a nie „l"
    ze znakiem diakrytycznym, więc samo odfiltrowanie znaków łączących
    zostawia ją nietkniętą. Bez tej podmiany klucz „cytat dosłowny"
    nie schodził się z „cytat_doslowny" i pole przepadało po cichu.
    """
    import unicodedata
    tekst = tekst.replace("ł", "l").replace("Ł", "L")
    return "".join(
        z for z in unicodedata.normalize("NFD", tekst)
        if unicodedata.category(z) != "Mn"
    ).casefold()


def _json_lub_pusty(surowe: str) -> dict:
    """Parsuje odpowiedź modelu i NORMALIZUJE nazwy kluczy.

    Model pisze po polsku i naturalnie zwraca `"wątki"` tam, gdzie
    szablon prosił o `"watki"`. Sztywne odczytywanie jednej pisowni
    kończyło się cichym zerem: pipeline szedł dalej, meldował postęp
    i zwracał pustą analizę, bo klucz się nie zgadzał o jeden ogonek.

    Kwantyzowany model lokalny nie trzyma schematu tak ściśle jak duży —
    dlatego przyjmujemy liberalnie: klucze bez ogonków, casefold,
    spacje i myślniki ujednolicone do podkreślenia.
    """
    try:
        dane = json.loads(surowe)
    except json.JSONDecodeError:
        return {}
    if not isinstance(dane, dict):
        return {}
    return {
        _bez_ogonkow(str(k)).replace(" ", "_").replace("-", "_"): v
        for k, v in dane.items()
    }


def _lista(dane: dict, *nazwy: str) -> list:
    """Pierwsza niepusta lista spod którejkolwiek z podanych nazw."""
    for nazwa in nazwy:
        wartosc = dane.get(_bez_ogonkow(nazwa))
        if isinstance(wartosc, list):
            return wartosc
    return []


def _pole(poz: dict, *nazwy: str) -> str:
    """Wartość tekstowa spod pierwszej pasującej nazwy pola."""
    znormalizowany = {
        _bez_ogonkow(str(k)).replace(" ", "_").replace("-", "_"): v
        for k, v in poz.items()
    }
    for nazwa in nazwy:
        wartosc = znormalizowany.get(_bez_ogonkow(nazwa))
        if wartosc not in (None, ""):
            return str(wartosc).strip()
    return ""


# ── wynik ───────────────────────────────────────────────────────────

@dataclass
class Ustalenie:
    tekst: str
    cytaty: list[dict] = field(default_factory=list)
    dokument: str = ""


@dataclass
class WynikAnalizy:
    pytanie: str
    watki: list[str] = field(default_factory=list)
    ustalenia: list[Ustalenie] = field(default_factory=list)
    wnioski: list[dict] = field(default_factory=list)
    rozbieznosci: list[dict] = field(default_factory=list)
    luki: list[str] = field(default_factory=list)
    podstawa_prawna: list[dict] = field(default_factory=list)
    odrzucone: list[dict] = field(default_factory=list)
    przeanalizowane_dokumenty: list[str] = field(default_factory=list)
    jezyki_dokumentow: dict[str, str] = field(default_factory=dict)
    pominiete_dokumenty: int = 0
    odmowa: bool = False
    blad: str | None = None

    def na_slownik(self) -> dict:
        return {
            "pytanie": self.pytanie,
            "watki": self.watki,
            "ustalenia": [
                {"tekst": u.tekst, "cytaty": u.cytaty, "dokument": u.dokument}
                for u in self.ustalenia
            ],
            "wnioski": self.wnioski,
            "rozbieznosci": self.rozbieznosci,
            "luki": self.luki,
            "podstawa_prawna": self.podstawa_prawna,
            "odrzucone": self.odrzucone,
            "przeanalizowane_dokumenty": self.przeanalizowane_dokumenty,
            "jezyki_dokumentow": self.jezyki_dokumentow,
            "pominiete_dokumenty": self.pominiete_dokumenty,
            "odmowa": self.odmowa,
            "blad": self.blad,
        }


# ── etap 1: dekompozycja ────────────────────────────────────────────

SZABLON_DEKOMPOZYCJI = """Jesteś asystentem prawnika. Rozbij pytanie na 2–4 wątki,
które trzeba sprawdzić w aktach, aby odpowiedzieć rzetelnie.

Zwróć wyłącznie JSON:
{{"watki": ["...", "..."]}}

Wątek to konkretna rzecz do ustalenia w dokumentach, nie plan pracy.
Dobrze: "ustalić, o której godzinie świadkowie umiejscawiają zdarzenie".
Źle: "przeanalizować akta".

PYTANIE: {pytanie}"""


def dekomponuj(pytanie: str) -> list[str]:
    try:
        dane = _json_lub_pusty(_wywolaj(SZABLON_DEKOMPOZYCJI.format(pytanie=pytanie)))
        surowe = _lista(dane, "watki", "wątki", "zagadnienia", "pytania")
        watki = [str(w).strip() for w in surowe if str(w).strip()]
        return watki[:4] or [pytanie]
    except Exception:                                    # noqa: BLE001
        # Dekompozycja jest ulepszeniem, nie warunkiem. Gdy zawiedzie,
        # analiza idzie dalej na samym pytaniu.
        return [pytanie]


# ── etap 3: mapowanie ───────────────────────────────────────────────

# ⚠️ NAJWAŻNIEJSZA LEKCJA Z BUDOWY TEGO PIPELINE'U
#
# Pierwsza wersja tego szablonu brzmiała: „wypisz ustalenia istotne dla
# pytania", a pytaniem było „czy zeznania świadków są spójne?".
# Model dostawał JEDEN protokół i słusznie odpowiadał pustą listą —
# pojedyncze zeznanie rzeczywiście nic nie mówi o spójności MIĘDZY
# świadkami. Analiza kończyła się zerem ustaleń, choć dokumenty
# były pełne faktów.
#
# Błąd był w konstrukcji, nie w modelu: etap mapowania nie może
# odpowiadać na pytanie. Ma WYDOBYWAĆ FAKTY. Porównanie i wnioski
# należą do etapu syntezy, który widzi wszystkie dokumenty naraz.
#
# To jest istota rozdziału map/reduce i najłatwiejsza rzecz do
# zepsucia przy pisaniu promptów.

SZABLON_MAPOWANIA = """Wydobywasz fakty z JEDNEGO dokumentu akt sprawy.

Ten dokument jest jednym z wielu. NIE oceniaj, czy sam odpowiada na pytanie
— porównania i wnioski powstaną później, na podstawie faktów zebranych ze
wszystkich dokumentów. Twoim jedynym zadaniem jest wypisać, co ten dokument
stwierdza.

Wypisz każdą konkretną okoliczność dotyczącą poniższych zagadnień:
kto, co, kiedy, gdzie, w jakich warunkach, jak długo, a także czego dana
osoba NIE była w stanie podać lub czego nie zaobserwowała.

Zdania w dokumencie są PONUMEROWANE. Każdy fakt wskazujesz przez NUMER
zdania, z którego wynika — nie przepisujesz treści. Cytat zostanie
odtworzony z dokumentu automatycznie, więc nie musisz go kopiować
i nie możesz się przy tym pomylić.

Zwróć wyłącznie JSON:
{{"ustalenia": [{{"tekst": "zwięzły opis faktu", "zdania": [12]}}]}}

Gdy fakt wynika z dwóch zdań, podaj oba numery: "zdania": [12, 13].
Wskazuj wyłącznie numery, które widzisz w dokumencie poniżej.

Pustą listę zwróć TYLKO wtedy, gdy dokument nie zawiera żadnych okoliczności
dotyczących tych zagadnień. Sam brak odpowiedzi na pytanie nie jest powodem
do zwrócenia pustej listy.

ZAGADNIENIA: {watki}
PYTANIE NADRZĘDNE (kontekst, nie odpowiadaj na nie): {pytanie}

=== DOKUMENT id={doc_id} ({nazwa}) — zdania ponumerowane ===
{tresc}"""


SZABLON_MAPOWANIA_EN = """You extract facts from ONE document in a case file.

This document is one of many. Do NOT judge whether it answers the question
on its own — comparison and conclusions come later, from facts gathered
across all documents. Your only task is to state what THIS document says.

List every concrete circumstance relevant to the topics below: who, what,
when, where, under what conditions, for how long, and also what a person
was NOT able to state or did not observe.

Sentences in the document are NUMBERED. You identify each fact by the
NUMBER of the sentence it comes from — you do not copy the text. The quote
is reconstructed from the document automatically, so you cannot get it
wrong and you must not attempt to reproduce it.

Return JSON only:
{{"ustalenia": [{{"tekst": "concise description of the fact", "zdania": [12]}}]}}

If a fact follows from two sentences, give both numbers: "zdania": [12, 13].
Use only numbers you can see in the document below.

Return an empty list ONLY if the document contains no circumstances relating
to these topics. Failing to answer the question is not a reason for an
empty list.

TOPICS: {watki}
OVERARCHING QUESTION (context only, do not answer it): {pytanie}

=== DOCUMENT id={doc_id} ({nazwa}) — sentences numbered ===
{tresc}"""


def _mapuj_dokument(pytanie: str, watki: list[str], doc_id: str, nazwa: str,
                    wybor: wyszukiwarka.WyborZdan,
                    zrodlo: str, jezyk: str = "pl") -> list[Ustalenie]:
    """Wydobycie faktów z jednego dokumentu — cytat przez NUMER zdania.

    Model wskazuje numer, a treść cytatu odtwarza KOD z offsetów
    w oryginale. Cytat jest więc wierny z definicji, a nie z dobrej
    woli modelu — zmyślenie go przestaje być wyrażalne (ADR-0007).

    Szablon i model nadal dobierane są do języka dokumentu. Pomiar
    z 14.08.2026: model polski proszony po polsku o cytaty z angielskiego
    tekstu parafrazował zamiast cytować, przez co weryfikator odrzucił
    62 z 68 twierdzeń. Po przejściu na numery ta klasa błędu znika —
    model nie przepisuje już niczego.
    """
    if not len(wybor):
        return []

    szablon = SZABLON_MAPOWANIA_EN if jezyk == "en" else SZABLON_MAPOWANIA
    zadanie = szablon.format(
        pytanie=pytanie, watki="; ".join(watki),
        doc_id=doc_id, nazwa=nazwa, tresc=wybor.dla_modelu(naglowki=False),
    )
    surowa = _wywolaj(
        zadanie, model=mod_jezyk.model_dla(jezyk), kontekst=KONTEKST_MAPOWANIA,
        schemat=schematy.mapowanie(wybor.numery),
    )
    dane = _json_lub_pusty(surowa)

    ustalenia: list[Ustalenie] = []
    for poz in _lista(dane, "ustalenia", "fakty", "ustalenie"):
        if not isinstance(poz, dict):
            continue
        tekst = _pole(poz, "tekst", "ustalenie", "opis", "tresc")
        if not tekst:
            continue

        numery = [n for n in (poz.get("zdania") or []) if isinstance(n, int)]
        cytaty: list[dict] = []
        for numer in numery:
            zdanie = wybor.rozwiaz(numer)
            if zdanie is None:
                # Gramatyka nie powinna na to pozwolić. Jeśli się zdarzy,
                # ma być widoczne, a nie po cichu pominięte.
                continue
            cytaty.append({
                "dokument_id": zdanie.dokument_id,
                "poczatek": zdanie.poczatek,
                "koniec": zdanie.koniec,
                # ⚠️ Treść ZE ŹRÓDŁA, nie z odpowiedzi modelu.
                # To jest cała istota konstrukcji: model podał numer,
                # a nie tekst, więc nie miał jak go przekręcić.
                "fragment": zrodlo[zdanie.poczatek:zdanie.koniec],
            })

        if not cytaty:
            # Ścieżka zapasowa — model mimo schematu podał tekst cytatu.
            fragment = _pole(poz, "fragment", "cytat", "cytat_doslowny")
            if not fragment:
                continue
            zakres = znajdz_fragment(zrodlo, fragment)
            cytaty = [{"dokument_id": doc_id,
                       "poczatek": zakres[0] if zakres else 0,
                       "koniec": zakres[1] if zakres else 0,
                       "fragment": fragment}]

        ustalenia.append(Ustalenie(tekst, cytaty, nazwa))
    return ustalenia


# ── etap 5: synteza ─────────────────────────────────────────────────

SZABLON_SYNTEZY = """Jesteś asystentem prawnika. Masz zweryfikowane ustalenia
faktyczne z akt sprawy. Przeprowadź analizę.

Zwróć wyłącznie JSON:
{{
 "wnioski": [{{"tekst": "...", "oparte_na": [1, 3]}}],
 "rozbieznosci": [{{"opis": "...", "oparte_na": [2, 5]}}],
 "luki": ["czego brakuje w aktach, aby odpowiedzieć pewniej"],
 "podstawa_prawna": [{{"tekst": "...", "przepis": "dosłowny cytat przepisu"}}]
}}

ZASADY:
- "oparte_na" to NUMERY ustaleń z listy poniżej. Wniosek bez wskazania
  ustaleń zostanie odrzucony.
- Nie dopisuj faktów spoza listy ustaleń. Jeżeli czegoś brakuje, to jest
  luka, a nie wniosek.
- "rozbieznosci" to sprzeczności między ustaleniami. Wskazujesz je,
  ale NIE rozstrzygasz, która wersja jest prawdziwa, i NIE oceniasz
  wiarygodności osób.
- "podstawa_prawna" wypełniaj WYŁĄCZNIE cytatami z podanych przepisów.
  Jeśli przepisów nie podano, zostaw pustą listę.
- Nie formułujesz porady prawnej ani kwalifikacji prawnej czynu.

PYTANIE: {pytanie}

USTALENIA Z AKT (zweryfikowane):
{ustalenia}
{przepisy}"""


def _sprawdz_wsparcie_ustalen(ustalenia: list[Ustalenie],
                              wynik: "WynikAnalizy",
                              pytanie: str = "",
                              melduj=None) -> list[Ustalenie]:
    """Warstwy 3 i 4 dla toru analizy.

    Odrzucone trafiają do `wynik.odrzucone` z powodem, tak jak wszystko
    inne — prawnik ma widzieć, że coś odpadło i dlaczego, a nie dostać
    krótszą listę bez wyjaśnienia.

    ⚠️ TE SAME PRZEŁĄCZNIKI, CO W TORZE SZYBKIM — I TO JEST ISTOTA POPRAWKI.

    Do 15.08.2026 ta funkcja wywoływała kontrolę BEZWARUNKOWO, podczas gdy
    `agent._sprawdz_wsparcie` sprawdzał `KONTROLA_MECHANICZNA`/`KONTROLA_MODELEM`.
    Skutek był gorszy niż niespójność stylu: **benchmark mierzył potok bez
    kontroli, a panel prawnika chodził z kontrolą**. Każda liczba w raporcie
    opisywała inny układ niż ten, którym prawnik faktycznie pracował.

    Jeden przełącznik dla obu torów jest tu warunkiem tego, żeby pomiar
    w ogóle o czymkolwiek świadczył.

    ⚠️ `kontekst_znany=pytanie` — BRAKOWAŁO GO TUTAJ.

    Tor szybki przekazuje wyróżniki pytania, żeby sekcja A `wsparcie`
    karała wyłącznie to, co twierdzenie DODAJE ponad pytanie i cytat.
    Bez tego data przeniesiona z pytania do twierdzenia liczy się jako
    wyróżnik zmyślony i poprawne ustalenie odpada. Ta sama przyczyna,
    którą rozpoznano i naprawiono w torze szybkim 14.08.2026 — tor
    analizy jej poprawki nigdy nie dostał.
    """
    import agent as mod_agent
    import kontrola as mod_kontrola
    import wsparcie as mod_wsparcie

    if not mod_agent.KONTROLA_MECHANICZNA:
        return ustalenia

    zostaje: list[Ustalenie] = []
    for i, u in enumerate(ustalenia, start=1):
        # Kontrola modelem kosztuje kilka sekund na ustalenie, więc krok
        # bez postępu wygląda w panelu na zawieszenie. Melduje pozycję.
        if melduj is not None:
            melduj("Sprawdzam wsparcie ustaleń", i - 1, len(ustalenia))

        fragmenty = [c.get("fragment", "") for c in u.cytaty]
        jez = mod_jezyk.rozpoznaj(" ".join(fragmenty)[:2000]).jezyk
        if jez == "nieznany":
            jez = None

        ws = mod_wsparcie.oszacuj(u.tekst, fragmenty, jez,
                                  kontekst_znany=pytanie)
        if ws.stopien is mod_wsparcie.Stopien.BRAK:
            wynik.odrzucone.append({
                "tekst": u.tekst, "powod": "odrzucony_brak_wsparcia_w_cytacie",
                "szczegol": ws.powod, "dokument": u.dokument,
            })
            continue

        kw = (mod_kontrola.sprawdz(u.tekst, fragmenty, jez or "pl")
              if mod_agent.KONTROLA_MODELEM
              else mod_kontrola.Wynik(mod_kontrola.Werdykt.NIEZWERYFIKOWANE,
                                      "kontrola modelem wyłączona"))
        if kw.werdykt is mod_kontrola.Werdykt.FALSZ:
            wynik.odrzucone.append({
                "tekst": u.tekst, "powod": "odrzucony_kontrola_niezalezna",
                "szczegol": ("Niezależna kontrola uznała, że zacytowane zdanie "
                             f"tego nie stwierdza. {kw.powod}"),
                "dokument": u.dokument,
            })
            continue

        for c in u.cytaty:
            c["stopien"] = ws.stopien.value
            c["pokrycie"] = round(ws.pokrycie, 2)
            c["kontrola"] = kw.werdykt.value
            # Znacznik „nie zweryfikowano" niesie sens tylko wtedy, gdy
            # kontrola miała działać i nie zadziałała. Przy wyłączonej
            # byłby szumem na każdym cytacie.
            if (kw.werdykt is mod_kontrola.Werdykt.NIEZWERYFIKOWANE
                    and mod_agent.KONTROLA_MODELEM):
                c["ostrzezenie"] = f"nie zweryfikowano niezależnie: {kw.powod}"
            elif ws.stopien is mod_wsparcie.Stopien.SLABE:
                c["ostrzezenie"] = ws.powod or "słabe pokrycie przez cytat"
        zostaje.append(u)

    return zostaje


def _syntezuj(pytanie: str, ustalenia: list[Ustalenie],
              przepisy_tekst: str) -> dict:
    lista = "\n".join(
        f"{i}. {u.tekst}  [źródło: {u.dokument}]"
        for i, u in enumerate(ustalenia, start=1)
    )
    blok_przepisow = (
        f"\nPRZEPISY DO WYKORZYSTANIA:\n{przepisy_tekst}"
        if przepisy_tekst else
        "\nPRZEPISY: nie podłączono żadnych — zostaw podstawa_prawna pustą."
    )
    # Ten sam kontekst co pozostałe etapy — wchodzi tu lista wszystkich
    # zweryfikowanych ustaleń plus wybrane przepisy. Jednakowy `num_ctx`
    # w całym pipelinie oszczędza przeładowanie modelu (patrz KONTEKST).
    return _json_lub_pusty(_wywolaj(
        SZABLON_SYNTEZY.format(pytanie=pytanie, ustalenia=lista,
                               przepisy=blok_przepisow),
        temperatura=0.2, model=MODEL_SYNTEZY, kontekst=KONTEKST,
    ))


# ── pipeline ────────────────────────────────────────────────────────

def analizuj(pytanie: str,
             dokumenty: dict[str, str],
             nazwy: dict[str, str] | None = None,
             przepisy: dict[str, str] | None = None,
             nazwy_przepisow: dict[str, str] | None = None,
             postep: Callable[[str, int, int], None] | None = None,
             maks_dokumentow: int = MAKS_DOKUMENTOW_DO_ANALIZY,
             jezyki: dict[str, str] | None = None) -> WynikAnalizy:
    """Pełna analiza. `dokumenty` pochodzą WYŁĄCZNIE z jednej sprawy.

    `postep(etap, zrobione, wszystkie)` pozwala pokazać, co się dzieje —
    analiza stu dokumentów trwa i użytkownik musi widzieć, że system
    pracuje, a nie zawisł.
    """
    nazwy = nazwy or {}
    wynik = WynikAnalizy(pytanie=pytanie)

    def melduj(etap: str, zrobione: int = 0, wszystkie: int = 0):
        if postep:
            postep(etap, zrobione, wszystkie)

    if not dokumenty:
        wynik.odmowa = True
        wynik.luki = ["Sprawa nie zawiera żadnych dokumentów."]
        return wynik

    try:
        # 1 ── dekompozycja
        melduj("Rozbijam pytanie na wątki", 0, 0)
        wynik.watki = dekomponuj(pytanie)

        # 2 ── wybór dokumentów
        melduj("Przeszukuję akta", 0, len(dokumenty))
        wszystkie_fragmenty = wyszukiwarka.podziel_wiele(dokumenty, nazwy)
        zapytanie_zbiorcze = pytanie + " " + " ".join(wynik.watki)
        trafne = wyszukiwarka.dokumenty_trafne(
            wszystkie_fragmenty, zapytanie_zbiorcze, ile=maks_dokumentow)
        if not trafne:
            trafne = list(dokumenty)[:maks_dokumentow]
        wynik.pominiete_dokumenty = max(0, len(dokumenty) - len(trafne))

        # Grupowanie raz, zamiast pełnego przebiegu po liście dla każdego
        # z dwunastu dokumentów — przy korpusie rzędu kilkunastu tysięcy
        # fragmentów to różnica między jednym a dwunastoma skanami.
        wg_dokumentu: dict[str, list[wyszukiwarka.Fragment]] = {}
        for f in wszystkie_fragmenty:
            wg_dokumentu.setdefault(f.dokument_id, []).append(f)

        # 3 ── mapowanie, pogrupowane po języku
        #
        # Kolejność nie jest kosmetyką: przy 8 GB VRAM mieści się JEDEN
        # model naraz, więc każda zmiana języka to wyładowanie jednego
        # i wczytanie drugiego. Przetworzenie najpierw wszystkich polskich,
        # potem angielskich, ogranicza to do jednej zamiany.
        jezyki = jezyki or {}
        trafne = sorted(trafne, key=lambda d: jezyki.get(d, "pl"))

        surowe: list[Ustalenie] = []
        for i, doc_id in enumerate(trafne, start=1):
            nazwa = nazwy.get(doc_id, doc_id)
            jez = jezyki.get(doc_id) or mod_jezyk.rozpoznaj(
                dokumenty[doc_id][:5000]).jezyk
            if jez == "nieznany":
                jez = "pl"
            wynik.jezyki_dokumentow[nazwa] = jez

            melduj(f"Analizuję dokument [{jez}]: {nazwa}", i, len(trafne))
            # Zdania, nie okna znakowe — jednostką cytatu jest zdanie,
            # więc jednostką wyboru też musi być zdanie. Okno cięte
            # w środku zdania dawałoby numer wskazujący urwany ciąg.
            wybor = wyszukiwarka.wybierz_zdania(
                {doc_id: dokumenty[doc_id]}, zapytanie_zbiorcze,
                nazwy={doc_id: nazwa}, jezyki={doc_id: jez},
                budzet_znakow=BUDZET_MAPOWANIA)
            if not len(wybor):
                continue
            surowe.extend(_mapuj_dokument(
                pytanie, wynik.watki, doc_id, nazwa, wybor,
                dokumenty[doc_id], jezyk=jez))
            wynik.przeanalizowane_dokumenty.append(nazwa)

        # 6a ── weryfikacja ustaleń (przed syntezą — synteza ma stać
        #        wyłącznie na faktach, które przeszły)
        melduj("Weryfikuję cytaty", 0, len(surowe))
        weryfikator = WeryfikatorCytatow(dokumenty)
        potwierdzone: list[Ustalenie] = []
        for u in surowe:
            twierdzenie = Twierdzenie(u.tekst, [
                Cytat(c["dokument_id"], c["poczatek"], c["koniec"], c["fragment"])
                for c in u.cytaty
            ])
            ocena = weryfikator.sprawdz_twierdzenie(twierdzenie)
            if ocena.przeszlo:
                potwierdzone.append(u)
            else:
                wynik.odrzucone.append({
                    "tekst": u.tekst, "powod": ocena.werdykt.value,
                    "szczegol": ocena.szczegol, "dokument": u.dokument,
                })
        # ── warstwy 3 i 4: czy cytat POPIERA ustalenie ───────────────
        #
        # Ten sam mechanizm co w torze szybkim (`agent._sprawdz_wsparcie`).
        # Tor analizy jest tu ważniejszy, nie mniej: prawnik zamawia
        # analizę przed rozprawą i czyta jej wynik jako materiał roboczy,
        # a nie jako pojedynczą odpowiedź na czacie.
        melduj("Sprawdzam wsparcie ustaleń", 0, len(potwierdzone))
        potwierdzone = _sprawdz_wsparcie_ustalen(
            potwierdzone, wynik, pytanie, melduj)

        wynik.ustalenia = potwierdzone

        if not potwierdzone:
            wynik.odmowa = True
            wynik.luki = [
                "W aktach tej sprawy nie znaleziono ustaleń popartych "
                "cytatem, które odpowiadałyby na pytanie."
            ]
            return wynik

        # 4 ── przepisy (odrębna przestrzeń cytatów)
        przepisy_tekst = ""
        if przepisy:
            melduj("Szukam podstawy prawnej", 0, len(przepisy))
            fragmenty_p = wyszukiwarka.podziel_wiele(
                przepisy, nazwy_przepisow or {})
            wybrane_p = wyszukiwarka.wybierz(
                fragmenty_p, zapytanie_zbiorcze, ile=5,
                budzet_znakow=BUDZET_PRZEPISOW)
            przepisy_tekst = "\n\n".join(
                f"[{f.nazwa}] {f.tresc}" for f in wybrane_p)

        # 5 ── synteza
        melduj("Buduję wnioski", 0, 0)
        synteza = _syntezuj(pytanie, potwierdzone, przepisy_tekst)

        # 6b ── zakotwiczenie wniosków w ustaleniach
        dozwolone = set(range(1, len(potwierdzone) + 1))

        def _zakotwiczone(pozycje: list) -> list[int]:
            wynik_poz = []
            for p in pozycje or []:
                try:
                    n = int(p)
                except (TypeError, ValueError):
                    continue
                if n in dozwolone:
                    wynik_poz.append(n)
            return wynik_poz

        for w in _lista(synteza, "wnioski", "wniosek", "analiza"):
            if not isinstance(w, dict):
                continue
            tekst = _pole(w, "tekst", "wniosek", "opis")
            oparte = _zakotwiczone(
                w.get("oparte_na") or w.get("oparte na") or w.get("ustalenia") or [])
            if not tekst:
                continue
            if not oparte:
                wynik.odrzucone.append({
                    "tekst": tekst, "powod": "wniosek_bez_zakotwiczenia",
                    "szczegol": "Wniosek nie wskazuje ustaleń, z których wynika.",
                    "dokument": "",
                })
                continue
            wynik.wnioski.append({"tekst": tekst, "oparte_na": oparte})

        for r in _lista(synteza, "rozbieznosci", "rozbieżności", "sprzecznosci"):
            if not isinstance(r, dict):
                continue
            opis = _pole(r, "opis", "tekst", "rozbieznosc")
            oparte = _zakotwiczone(
                r.get("oparte_na") or r.get("oparte na") or r.get("ustalenia") or [])
            if opis and oparte:
                wynik.rozbieznosci.append({"opis": opis, "oparte_na": oparte})

        wynik.luki = [
            str(l).strip()
            for l in _lista(synteza, "luki", "braki", "luki_dowodowe")
            if str(l).strip()
        ][:6]

        # Podstawa prawna — weryfikowana wobec KORPUSU PRZEPISÓW,
        # nigdy wobec akt sprawy. Rozdzielenie przestrzeni jest celowe:
        # zdanie o prawie nie może być "potwierdzone" protokołem.
        if przepisy:
            weryfikator_p = WeryfikatorCytatow(przepisy)
            for p in _lista(synteza, "podstawa_prawna", "podstawa prawna",
                            "przepisy"):
                if not isinstance(p, dict):
                    continue
                tekst = _pole(p, "tekst", "opis", "uzasadnienie")
                cytat_p = _pole(p, "przepis", "fragment", "cytat", "tresc")
                if not tekst or not cytat_p:
                    continue
                trafiony = None
                for pid, tresc_p in przepisy.items():
                    zakres_p = znajdz_fragment(tresc_p, cytat_p)
                    if zakres_p:
                        trafiony = {"przepis_id": pid,
                                    "nazwa": (nazwy_przepisow or {}).get(pid, pid),
                                    "poczatek": zakres_p[0],
                                    "koniec": zakres_p[1],
                                    "fragment": cytat_p}
                        break
                if trafiony:
                    wynik.podstawa_prawna.append(
                        {"tekst": tekst, "cytat": trafiony})
                else:
                    wynik.odrzucone.append({
                        "tekst": tekst, "powod": "przepis_bez_pokrycia",
                        "szczegol": f"Nie znaleziono cytatu w korpusie "
                                    f"przepisów: {cytat_p[:80]}",
                        "dokument": "przepisy",
                    })
            _ = weryfikator_p  # rozdzielenie przestrzeni: patrz wyżej

        melduj("Gotowe", 1, 1)
        return wynik

    except urllib.error.URLError as e:
        wynik.blad = (f"Model lokalny jest niedostępny pod {OLLAMA}. "
                      f"Sprawdź, czy Ollama działa. Szczegół: {e}")
        return wynik
    except Exception as e:                               # noqa: BLE001
        wynik.blad = f"Błąd analizy: {type(e).__name__}: {e}"
        return wynik
