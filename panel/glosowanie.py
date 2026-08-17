"""Głosowanie większościowe nad wskazaniami modelu (self-consistency).

DLACZEGO TO PASUJE AKURAT TUTAJ

Self-consistency polega na kilkukrotnym odpytaniu modelu i wybraniu
odpowiedzi najbardziej zgodnej. Przy odpowiedziach tekstowych trzeba je
porównywać rozmyto — dwa zdania o tym samym mogą różnić się każdym
słowem, a wtedy głosowanie samo staje się źródłem błędu.

Po ADR-0007 model zwraca NUMERY ZDAŃ. Głosowanie nad liczbami jest
dokładne: numer albo się powtórzył, albo nie. Nie ma progu podobieństwa,
nie ma czego stroić. To uboczna korzyść z decyzji podjętej w innym celu.

CO TO NAPRAWIA, A CZEGO NIE

    próg wysoki (większość)  → rośnie precyzja, spada czułość
    próg niski (co najmniej 1) → rośnie czułość, spada precyzja

Dobór progu jest więc wyborem między dwiema klasami błędu, a nie
ulepszeniem bez kosztu. Dlatego jest parametrem i podlega pomiarowi,
a nie jest zaszyty „bo tak lepiej".

⚠️ WARUNEK KONIECZNY: RÓŻNORODNOŚĆ PRÓBEK.
   Przy `temperature 0.1` i przypiętym `seed` (tak stoi w Modelfile'ach)
   wszystkie próbki są IDENTYCZNE — głosowanie nie wnosi nic, a koszt
   rośnie N-krotnie. Każde losowanie musi dostać własne ziarno,
   a temperatura musi być podniesiona na tyle, żeby model mógł
   zawahać się tam, gdzie faktycznie jest niepewny.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


# Ziarna losowań. Stałe, żeby przebieg był powtarzalny — zmienność
# bierze się z różnych ziaren, nie z braku kontroli nad nimi.
ZIARNA = (42, 1337, 2718, 31415, 16180)

# Podniesiona wobec 0.1 z Modelfile'a. Przy zbyt niskiej próbki są
# nierozróżnialne i głosowanie degeneruje się do pojedynczego wywołania.
TEMPERATURA_PROBKOWANIA = 0.35


@dataclass(frozen=True)
class WynikGlosowania:
    """Numery zdań, które przeszły próg, wraz z liczbą głosów."""
    numery: frozenset[int]
    glosy: dict[int, int]
    probek: int
    prog: int

    def poparcie(self, numer: int) -> float:
        """Udział losowań, które wskazały to zdanie — miara pewności."""
        return self.glosy.get(numer, 0) / self.probek if self.probek else 0.0


def prog_wiekszosciowy(probek: int) -> int:
    """Ile głosów potrzeba na większość. Dla 3 → 2, dla 5 → 3."""
    return math.ceil(probek / 2)


def policz(losowania: list[list[int]], prog: int | None = None) -> WynikGlosowania:
    """Zlicza wskazania zdań z kilku losowań.

    `losowania` to lista list numerów — po jednej z każdego wywołania
    modelu. Numer powtórzony w jednym losowaniu liczy się raz: model
    wskazujący to samo zdanie w dwóch twierdzeniach nie ma przez to
    „dwóch głosów".
    """
    probek = len(losowania)
    if probek == 0:
        return WynikGlosowania(frozenset(), {}, 0, 0)

    prog = prog_wiekszosciowy(probek) if prog is None else prog
    licznik: Counter[int] = Counter()
    for losowanie in losowania:
        licznik.update(set(losowanie))

    przeszly = frozenset(n for n, g in licznik.items() if g >= prog)
    return WynikGlosowania(przeszly, dict(licznik), probek, prog)


def przefiltruj_twierdzenia(twierdzenia: list[dict],
                            wynik: WynikGlosowania) -> tuple[list[dict], list[dict]]:
    """Dzieli twierdzenia na poparte i odrzucone przez głosowanie.

    Twierdzenie zostaje, gdy CHOĆ JEDNO ze wskazanych przez nie zdań
    przeszło próg. Wymaganie, by przeszły wszystkie, karałoby twierdzenia
    obejmujące dwa zdania — a to właśnie one niosą najwięcej treści.

    Zwraca (poparte, odrzucone). Odrzucone niosą powód i liczbę głosów,
    żeby prawnik widział, że system się wahał, a nie że niczego nie było.
    """
    poparte: list[dict] = []
    odrzucone: list[dict] = []

    for t in twierdzenia:
        zdania = [int(n) for n in (t.get("zdania") or []) if str(n).lstrip("-").isdigit()]
        if not zdania:
            odrzucone.append({**t, "powod_glosowania": "brak wskazanych zdań"})
            continue

        wsparte = [n for n in zdania if n in wynik.numery]
        if wsparte:
            najlepsze = max(zdania, key=lambda n: wynik.glosy.get(n, 0))
            poparte.append({**t, "poparcie": round(wynik.poparcie(najlepsze), 2)})
        else:
            najlepsze = max(zdania, key=lambda n: wynik.glosy.get(n, 0))
            odrzucone.append({
                **t,
                "powod_glosowania": (
                    f"wskazane przez {wynik.glosy.get(najlepsze, 0)} z "
                    f"{wynik.probek} losowań, próg {wynik.prog}"),
                "poparcie": round(wynik.poparcie(najlepsze), 2),
            })
    return poparte, odrzucone
