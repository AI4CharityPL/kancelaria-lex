"""Kontrola mechaniczna — czy zacytowane zdanie POPIERA twierdzenie.

CZWARTA WARSTWA, KTÓREJ BRAKOWAŁO

    weryfikator cytatów   cytat ISTNIEJE w aktach, znak w znak
    numery zdań           cytat odtwarza KOD, więc jest niepodrabialny
    zakotwiczenie         odpowiedź dotyczy TEGO, O CO PYTANO
    ── brak ──            czy zdanie POPIERA to, co mu przypisano

Model może wskazać zdanie prawdziwe, z akt, zawierające szukaną datę —
i mimo to niemówiące tego, co mu przypisano. To dominująca klasa błędu
po naprawach z 14.08.2026: fałszywe odmowy spadły z 6 do 2, ale
pojawiło się 5 przypadków „odpowiedź ze złym cytatem".

Ta sama klasa, którą Stanford RegLab zmierzył w narzędziach
komercyjnych: 24% odpowiedzi powoływało przepis, który nie popierał
tezy (przegląd 3 000 odpowiedzi, 2026).

DLACZEGO MECHANICZNIE, I DLACZEGO PIERWSZE

Ta warstwa jest deterministyczna i darmowa — bez modelu, bez VRAM,
czas bliski zeru. Idzie PRZED kontrolą modelem, bo twierdzenie
powołujące kwotę, której w cytacie fizycznie nie ma, nie wymaga
pytania modelu o zdanie.

Ta sama zasada, co przy terminach (ADR-0005) i rozpoznaniu języka:
tam, gdzie wystarczy reguła, model jest gorszym narzędziem.

⚠️ CZEGO TA WARSTWA NIE UMIE — zapisane wprost, bo obietnica bez
   pokrycia byłaby gorsza od braku kontroli.

   Sprawdzamy POKRYCIE LEKSYKALNE, nie wynikanie. Twierdzenie może
   użyć wyłącznie słów ze zdania i mimo to je przekręcić — „sąd
   uwzględnił" wobec „sąd nie uwzględnił" ma niemal identyczny
   zestaw słów znaczących. Od tego jest kontrola niezależna
   (`panel/kontrola.py`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Stopien(str, Enum):
    MOCNE = "mocne"          # wyróżniki zgodne, pokrycie wysokie
    SLABE = "slabe"          # pokrycie między progami — znacznik dla prawnika
    BRAK = "brak"            # wyróżnik z twierdzenia nieobecny w cytacie


# ── PROGI ZESTROJONE NA POMIARZE 15.08.2026 ──────────────────────────
#
# Benchmark v2 z przypisaniem etapu wykazał, że TA WARSTWA odpowiada
# za 60% fałszywych odmów (6 z 10). Rozkład pokrycia twierdzeń ZNANYCH
# JAKO POPRAWNE, zmierzony na sprawach 3 i 4:
#
#     0,17  0,20  0,29  0,33  0,38  0,50  0,67  0,92  1,00  1,00
#            ↑ próg 0,30 przecinał tutaj ↑
#
# Trzy poprawne odpowiedzi odpadały przez sam próg, nie przez treść.
#
# ⚠️ ZMIANA ZASADY, NIE TYLKO LICZBY.
#
# Warstwa mechaniczna miała decydować, CZY WARTO ZAPŁACIĆ za wywołanie
# modelu — a zaczęła orzekać ostatecznie. To zła kolejność: tania
# i przybliżona warstwa wydawała wyroki, które miała wydawać warstwa
# dokładna. Kontroler niezależny ma zmierzone 8/8 na próbie
# różnicującej; pokrycie leksykalne nie ma i mieć nie może, bo z definicji
# nie widzi negacji („sąd uwzględnił" wobec „sąd NIE uwzględnił" ma
# pokrycie bliskie 100%).
#
# Odrzucenie zostaje więc zarezerwowane dla przypadków rozstrzygniętych
# mechanicznie: zmyślonego wyróżnika twardego (sekcja A) i pokrycia
# bliskiego zeru. Reszta idzie do kontrolera i to on orzeka.
PROG_MOCNE = 0.60

# 0,15 zamiast 0,30 — poniżej tej wartości twierdzenie i cytat nie mają
# praktycznie wspólnych słów znaczących i pytanie modelu nic nie wniesie.
PROG_SLABE = 0.15


@dataclass(frozen=True)
class Wsparcie:
    stopien: Stopien
    pokrycie: float                                   # 0–1
    brakujace: tuple[str, ...] = ()                   # wyróżniki nieobecne w cytacie
    powod: str = ""

    @property
    def wymaga_kontroli_modelem(self) -> bool:
        """Czy warto zapłacić za wywołanie modelu.

        Twierdzenie bez wyróżnika obecnego w cytacie odpada tutaj —
        pytanie modelu o zdanie nic nie doda, a kosztuje.
        """
        return self.stopien is not Stopien.BRAK


_LICZBA = re.compile(r"\b\d{1,9}(?:[.,]\d{1,2})?\b")


def _wyrozniki(tekst: str):
    from wyrozniki import wyrozniki as _w
    return _w(tekst)


def _tokeny_znaczace(tekst: str, jezyk: str | None = None) -> set[str]:
    from wyszukiwarka import tokenizuj
    return set(tokenizuj(tekst, jezyk))


def oszacuj(tekst: str, cytaty: list[str],
            jezyk: str | None = None,
            kontekst_znany: str = "") -> Wsparcie:
    """Czy cytaty popierają twierdzenie.

    `cytaty` to WSZYSTKIE zdania wskazane dla tego twierdzenia — gdy
    okoliczność wynika z dwóch zdań, oba wchodzą do sprawdzenia.
    Wymaganie pokrycia przez każde z osobna karałoby twierdzenia
    obejmujące dwa zdania, a to one niosą najwięcej treści.
    """
    if not tekst or not tekst.strip():
        return Wsparcie(Stopien.BRAK, 0.0, (), "puste twierdzenie")
    if not cytaty:
        return Wsparcie(Stopien.BRAK, 0.0, (), "twierdzenie bez cytatu")

    material = " ".join(cytaty)

    # ── A. Wyróżniki twarde ──────────────────────────────────────────
    # Data, kwota, sygnatura, przepis wymienione w TWIERDZENIU muszą być
    # w cytacie. Porównanie po WARTOŚCI, więc „23.07.1974" i „23 lipca
    # 1974 r." to zgodność — inaczej odrzucalibyśmy poprawne cytaty
    # wskazujące to samo orzeczenie innym zapisem (ustalenie U-1).
    #
    # ⚠️ `kontekst_znany` — WYRÓŻNIKI, KTÓRE PADŁY JUŻ W PYTANIU.
    #
    # Pomiar z 14.08.2026 pokazał, że bez tego kontrola odrzuca poprawne
    # odpowiedzi. Model pisze twierdzenie łączące kontekst pytania
    # z faktem z akt:
    #
    #     pytanie:     „...with the date October 6, 2016?"
    #     twierdzenie: „The Court granted the motion on October 6, 2016."
    #     cytat:       „IT IS ORDERED that the Motion ... is granted."
    #
    # Data pochodzi z PYTANIA, nie ze zdania. Karanie za nią oznaczałoby
    # liczenie tego samego wyróżnika dwa razy: raz przy zakotwiczeniu
    # w pytaniu (gdzie sprawdzono, że odpowiedź dotyczy właściwej daty),
    # drugi raz tutaj — przeciwko poprawnej odpowiedzi.
    #
    # Karzemy więc wyłącznie za to, co twierdzenie DODAJE ponad pytanie
    # i cytat. Wyróżnik zmyślony — nieobecny ani w pytaniu, ani w aktach —
    # nadal odpada.
    w_twierdzeniu = _wyrozniki(tekst).zlozone
    w_cytacie = _wyrozniki(material).zlozone
    w_pytaniu = _wyrozniki(kontekst_znany).zlozone if kontekst_znany else set()
    brakujace = tuple(sorted(w_twierdzeniu - w_cytacie - w_pytaniu))
    if brakujace:
        return Wsparcie(
            Stopien.BRAK, 0.0, brakujace,
            f"twierdzenie powołuje {', '.join(brakujace)}, "
            f"a w cytacie tego nie ma")

    # ── B. Liczby ────────────────────────────────────────────────────
    # Osobno od wyróżników, bo łapie liczby nietworzące wyróżnika
    # złożonego: liczbę świadków, wiek, numer strony.
    # Wyróżniki złożone są już zaliczone wyżej — ich cyfry nie mogą
    # iść do osobnego sprawdzenia, bo „23 lipca 1974" i „23.07.1974"
    # tokenizują się na różne liczby mimo tej samej wartości.
    from wyrozniki import usun_wyrozniki
    liczby_t = {m.group(0) for m in _LICZBA.finditer(usun_wyrozniki(tekst))}
    liczby_c = {m.group(0) for m in _LICZBA.finditer(usun_wyrozniki(material))}
    liczby_p = ({m.group(0) for m in _LICZBA.finditer(usun_wyrozniki(kontekst_znany))}
                if kontekst_znany else set())
    brak_liczb = tuple(sorted(liczby_t - liczby_c - liczby_p))
    # ⚠️ SŁABE, NIE BRAK — złagodzone 15.08.2026.
    #
    # Gołe liczby to nie to samo, co wyróżnik twardy. Model pisze
    # „dwóch świadków", „punkt 3", „strona 12" — liczby porządkowe
    # i opisowe, których w cytowanym zdaniu nie musi być, mimo że
    # twierdzenie jest wierne. Odrzucanie za to kosztowało poprawne
    # odpowiedzi, a sygnał jest zbyt słaby na wyrok.
    #
    # Zostaje jako ostrzeżenie i przechodzi do kontrolera, który
    # potrafi rozstrzygnąć (zmierzone: rozpoznaje „14 dni" wobec
    # „7 dni" jako sprzeczność).
    if brak_liczb:
        return Wsparcie(
            Stopien.SLABE, 0.0, brak_liczb,
            f"twierdzenie podaje liczby {', '.join(brak_liczb)}, "
            f"których w cytacie nie ma")

    # ── C. Pokrycie treściowe ────────────────────────────────────────
    #
    # ⚠️ Odsiew stopsłów MUSI obejmować język twierdzenia. Do 14.08.2026
    # `tokenizuj` znało wyłącznie listę polską, więc angielskie „the",
    # „of", „that" wchodziły do mianownika jako słowa znaczące. Pokrycie
    # angielskich twierdzeń wychodziło 0,20–0,29 zamiast realnego i przy
    # progu 0,30 kwalifikowało poprawne twierdzenia jako „brak wsparcia".
    t_tw = _tokeny_znaczace(tekst, jezyk)
    if not t_tw:
        # Twierdzenie z samych słów funkcyjnych — nie ma czego mierzyć.
        return Wsparcie(Stopien.SLABE, 0.0, (), "brak słów znaczących")

    t_cy = _tokeny_znaczace(material, jezyk)
    pokrycie = len(t_tw & t_cy) / len(t_tw)

    if pokrycie >= PROG_MOCNE:
        return Wsparcie(Stopien.MOCNE, pokrycie)
    if pokrycie >= PROG_SLABE:
        return Wsparcie(
            Stopien.SLABE, pokrycie, (),
            f"tylko {pokrycie:.0%} słów znaczących twierdzenia "
            f"występuje w cytacie")
    return Wsparcie(
        Stopien.BRAK, pokrycie, (),
        f"zaledwie {pokrycie:.0%} słów znaczących twierdzenia "
        f"występuje w cytacie")


@dataclass
class Podsumowanie:
    mocne: int = 0
    slabe: int = 0
    brak: int = 0
    srednie_pokrycie: float = 0.0
    szczegoly: list[Wsparcie] = field(default_factory=list)


def podsumuj(wyniki: list[Wsparcie]) -> Podsumowanie:
    """Rozkład stopni — do dziennika i do bramki jakości."""
    if not wyniki:
        return Podsumowanie()
    return Podsumowanie(
        mocne=sum(1 for w in wyniki if w.stopien is Stopien.MOCNE),
        slabe=sum(1 for w in wyniki if w.stopien is Stopien.SLABE),
        brak=sum(1 for w in wyniki if w.stopien is Stopien.BRAK),
        srednie_pokrycie=sum(w.pokrycie for w in wyniki) / len(wyniki),
        szczegoly=list(wyniki),
    )
