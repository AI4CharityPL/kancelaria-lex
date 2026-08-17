"""Kontrolowane zaszumienie tekstu — symulacja błędów OCR.

PO CO TO JEST / WHY THIS EXISTS

OCR jest pierwszym ogniwem łańcucha (docs/06-stos-ai.md): błąd tutaj
propaguje się na retrieval, cytat i odpowiedź. Bramki N-14 i N-15
stawiają progi CER (≤2% na dobrych skanach, ≤10% na kserokopiach),
ale próg CER sam w sobie nic nie mówi o tym, ILE JAKOŚCI TRACI SYSTEM
przy danym poziomie szumu.

To jest pytanie ilościowe i da się na nie odpowiedzieć tylko jednym
sposobem: wziąć tekst o znanej treści, zepsuć go w kontrolowany sposób
i zmierzyć krzywą degradacji.

⚠️ SZUM MUSI BYĆ REALISTYCZNY, NIE LOSOWY

Losowa podmiana znaków zaniża trudność. Prawdziwy OCR myli się
systematycznie i te pomyłki są inne w polskim niż w angielskim:

  - polski traci ogonki, bo skan jest blady albo czcionka cienka
    (ą→a, ę→e, ł→l) — i to jest najczęstszy błąd na polskich aktach
  - „rn" zlewa się w „m", „cl" w „d" — błąd kroju, nie języka
  - cyfry mylą się z literami w obie strony (0↔O, 1↔l, 5↔S, 8↔B)
    i to jest błąd NAJGROŹNIEJSZY w piśmie procesowym, bo dotyka
    sygnatur, dat i kwot

Ostatnia grupa jest osobno wyróżniona, bo w aktach „II K 147/26"
i „II K l47/26" to dwie różne sprawy, a „14 dni" i „l4 dni" to
różnica między zachowanym a utraconym terminem.

ENGLISH SUMMARY
    Controlled, realistic OCR-noise injection used to measure how much
    answer quality degrades at a known character error rate (CER).
    Confusions are language-specific: Polish loses diacritics, both
    languages suffer glyph confusions, and digit/letter confusions are
    tracked separately because in court documents they change meaning
    rather than merely spelling.
"""

from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass

# ── klasy pomyłek / confusion classes ────────────────────────────────

# Zlewanie i rozpad glifów — niezależne od języka.
GLIFY: dict[str, str] = {
    "rn": "m", "m": "rn", "cl": "d", "vv": "w", "w": "vv",
    "ii": "n", "li": "h", "nn": "rm",
}

# Cyfra ↔ litera. Wyodrębnione, bo psują sygnatury, daty i kwoty —
# czyli dokładnie to, o co pyta się akt najczęściej.
CYFROWE: dict[str, str] = {
    "0": "O", "O": "0", "1": "l", "l": "1", "5": "S", "S": "5",
    "8": "B", "B": "8", "6": "b", "2": "Z", "Z": "2",
}

# Utrata znaków diakrytycznych — dominujący błąd na polskich skanach.
DIAKRYTYCZNE: dict[str, str] = {
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
    "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
}

# Sąsiedztwo klawiszy — literówki operatora przepisującego skan ręcznie.
SASIEDZTWO: dict[str, str] = {
    "a": "s", "s": "a", "e": "r", "r": "e", "o": "p", "i": "o",
    "n": "m", "t": "y", "c": "v", "u": "y",
}


@dataclass(frozen=True)
class Uszkodzenie:
    """Pojedyncza wprowadzona zmiana — do rozliczenia, co się stało."""
    pozycja: int
    przed: str
    po: str
    klasa: str          # 'diakrytyczne' | 'glify' | 'cyfrowe' | 'sasiedztwo'


@dataclass
class WynikZaszumienia:
    tekst: str
    uszkodzenia: list[Uszkodzenie]
    cer_zadany: float
    cer_faktyczny: float

    @property
    def cyfrowych(self) -> int:
        """Ile pomyłek dotknęło cyfr — te zmieniają sens, nie pisownię."""
        return sum(1 for u in self.uszkodzenia if u.klasa == "cyfrowe")


def _kandydaci(tekst: str, jezyk: str) -> list[tuple[int, str, str, str]]:
    """Wszystkie możliwe podmiany: (pozycja, przed, po, klasa)."""
    wynik: list[tuple[int, str, str, str]] = []

    # Wagi klas dobrane tak, by odwzorować rozkład błędów rzeczywistego
    # OCR: na polskim dominuje utrata ogonków, na angielskim glify.
    if jezyk == "pl":
        tablice = [(DIAKRYTYCZNE, "diakrytyczne"), (CYFROWE, "cyfrowe"),
                   (GLIFY, "glify"), (SASIEDZTWO, "sasiedztwo")]
    else:
        tablice = [(GLIFY, "glify"), (CYFROWE, "cyfrowe"),
                   (SASIEDZTWO, "sasiedztwo")]

    for tablica, klasa in tablice:
        for wzorzec, zamiennik in tablica.items():
            start = 0
            while True:
                i = tekst.find(wzorzec, start)
                if i < 0:
                    break
                wynik.append((i, wzorzec, zamiennik, klasa))
                start = i + 1
    return wynik


def zaszum(tekst: str, cer: float, jezyk: str = "pl",
           ziarno: int = 42) -> WynikZaszumienia:
    """Wprowadza błędy na zadanym poziomie CER.

    `cer` to udział znaków dotkniętych zmianą (0.0–1.0). Wynik jest
    powtarzalny dla tego samego ziarna — bez tego porównanie przebiegów
    nie miałoby sensu.

    Podmiany nie nakładają się na siebie: raz dotknięty zakres jest
    wyłączony z dalszych zmian, żeby faktyczny CER dało się policzyć.
    """
    if not tekst or cer <= 0:
        return WynikZaszumienia(tekst, [], cer, 0.0)

    los = random.Random(ziarno)
    kandydaci = _kandydaci(tekst, jezyk)
    if not kandydaci:
        return WynikZaszumienia(tekst, [], cer, 0.0)

    los.shuffle(kandydaci)
    budzet = max(1, int(len(tekst) * cer))

    zajete: set[int] = set()
    wybrane: list[tuple[int, str, str, str]] = []
    zmienionych_znakow = 0

    for pozycja, przed, po, klasa in kandydaci:
        if zmienionych_znakow >= budzet:
            break
        zakres = set(range(pozycja, pozycja + len(przed)))
        if zakres & zajete:
            continue
        zajete |= zakres
        wybrane.append((pozycja, przed, po, klasa))
        zmienionych_znakow += len(przed)

    # Składanie od końca — wcześniejsze pozycje pozostają poprawne.
    wybrane.sort(key=lambda x: x[0], reverse=True)
    znaki = list(tekst)
    uszkodzenia: list[Uszkodzenie] = []
    for pozycja, przed, po, klasa in wybrane:
        znaki[pozycja:pozycja + len(przed)] = list(po)
        uszkodzenia.append(Uszkodzenie(pozycja, przed, po, klasa))

    zaszumiony = "".join(znaki)
    uszkodzenia.reverse()

    return WynikZaszumienia(
        tekst=zaszumiony,
        uszkodzenia=uszkodzenia,
        cer_zadany=cer,
        cer_faktyczny=zmienionych_znakow / len(tekst),
    )


def cer(wzorzec: str, zmierzony: str) -> float:
    """Character Error Rate metodą Levenshteina, znormalizowany długością.

    Miara bramek N-14 i N-15. Implementacja w dwóch wierszach pamięci —
    pełna macierz przy dokumencie na 100 tys. znaków zajęłaby dziesiątki
    gigabajtów.
    """
    if not wzorzec:
        return 0.0 if not zmierzony else 1.0

    poprzedni = list(range(len(zmierzony) + 1))
    for i, znak_w in enumerate(wzorzec, start=1):
        biezacy = [i]
        for j, znak_z in enumerate(zmierzony, start=1):
            biezacy.append(min(
                poprzedni[j] + 1,                                   # usunięcie
                biezacy[j - 1] + 1,                                 # wstawienie
                poprzedni[j - 1] + (znak_w != znak_z),              # zamiana
            ))
        poprzedni = biezacy
    return poprzedni[-1] / len(wzorzec)


def bez_diakrytykow(tekst: str) -> str:
    """Skrajny przypadek: skan, z którego zniknęły wszystkie ogonki.

    ⚠️ NFD nie rozkłada „ł" (U+0142) — to odrębna litera, nie „l"
    ze znakiem diakrytycznym. Ta sama pułapka, co w wyszukiwarce
    i w parsowaniu analizy; bez jawnej podmiany połowa polskich form
    zostałaby nietknięta i test byłby łatwiejszy, niż się wydaje.
    """
    tekst = tekst.replace("ł", "l").replace("Ł", "L")
    return "".join(
        z for z in unicodedata.normalize("NFD", tekst)
        if unicodedata.category(z) != "Mn"
    )
