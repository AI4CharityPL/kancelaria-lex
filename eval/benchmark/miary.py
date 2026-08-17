"""Metryki benchmarku — punktacja maszynowa, bez sędziego LLM.

MIARA NACZELNA: ROZRÓŻNIALNOŚĆ PAR / PAIR DISCRIMINATION

Klasyczne metryki RAG-a dają się oszukać zachowaniem zdegenerowanym:

    system, który ZAWSZE odmawia    → 100% poprawnych odmów (J-3)
    system, który ZAWSZE odpowiada  → 100% braku fałszywych odmów (J-4)

Każdy z nich wygląda świetnie w jednej kolumnie i fatalnie w drugiej,
więc zwykle patrzy się na obie naraz i próbuje je ważyć. To działa,
ale nie mówi wprost tego, co interesuje kancelarię: czy system POTRAFI
ODRÓŻNIĆ sytuację, w której odpowiedź w aktach jest, od tej, w której
jej nie ma.

Pary dopasowane pozwalają zapytać o to jednym pomiarem. Para liczy się
jako rozróżniona tylko wtedy, gdy system:

    a) zacytował właściwy fragment w przypadku odpowiadalnym  ORAZ
    b) odmówił w bliźniaku

Oba zachowania zdegenerowane dostają w tej mierze ZERO. Pytania w parze
mają identyczną formę i różnią się wyłącznie wartością kotwicy, więc
różnicy nie da się wytłumaczyć trudnością pytania.

    ⚠️ Wynik 50% NIE oznacza „w połowie dobrze". Oznacza, że w połowie
       par system zachował się tak samo wobec pytania z odpowiedzią
       i bez odpowiedzi — czyli w tych parach nie sprawdzał akt.

ENGLISH SUMMARY
    Pair discrimination is the headline metric: a pair counts only if
    the system cites the correct span for the answerable case AND
    refuses its form-identical twin. Both degenerate strategies —
    always answer, always refuse — score zero, which classical
    precision/recall style metrics do not enforce.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .generator import (
    OCZEKIWANIE_CYTAT, Przypadek,
)


@dataclass
class Odpowiedz:
    """Znormalizowana odpowiedź systemu na jeden przypadek."""
    odmowa: bool
    cytaty: list[dict] = field(default_factory=list)   # dokument_id/poczatek/koniec
    tekst: str = ""
    odrzucone: list[dict] = field(default_factory=list)
    czas_s: float = 0.0
    blad: str | None = None


@dataclass
class Ocena:
    """Wynik jednego przypadku."""
    przypadek_id: str
    kategoria: str
    jezyk: str
    trafiony: bool                  # zacytował właściwy zakres
    odmowil: bool
    poprawny: bool                  # zachował się zgodnie z oczekiwaniem
    pokrycie: float = 0.0           # udział wzorca objęty cytatem (0–1)
    czas_s: float = 0.0
    blad: str | None = None


def _nachodzi(a_od: int, a_do: int, b_od: int, b_do: int) -> int:
    return max(0, min(a_do, b_do) - max(a_od, b_od))


def ocen(przypadek: Przypadek, odpowiedz: Odpowiedz,
         min_pokrycie: float = 0.30) -> Ocena:
    """Ocenia jedną odpowiedź wobec prawdy wzorcowej.

    `min_pokrycie` — jaka część zdania wzorcowego musi zostać objęta
    cytatem, żeby uznać trafienie. Nie wymagamy pokrycia całkowitego:
    system cytujący samo zdanie kluczowe jest lepszy od cytującego
    cały akapit, a oba są poprawne. Wymagamy natomiast, żeby cytat
    trafiał we WŁAŚCIWY DOKUMENT i we właściwe miejsce.
    """
    if odpowiedz.blad:
        return Ocena(przypadek.id, przypadek.kategoria, przypadek.jezyk,
                     trafiony=False, odmowil=False, poprawny=False,
                     czas_s=odpowiedz.czas_s, blad=odpowiedz.blad)

    odmowil = odpowiedz.odmowa or not odpowiedz.cytaty

    pokrycie = 0.0
    trafiony = False
    if przypadek.oczekiwanie == OCZEKIWANIE_CYTAT and przypadek.poczatek is not None:
        dlugosc = max(1, przypadek.koniec - przypadek.poczatek)
        najlepsze = 0
        for c in odpowiedz.cytaty:
            if str(c.get("dokument_id")) != str(przypadek.dokument_id):
                continue
            najlepsze = max(najlepsze, _nachodzi(
                przypadek.poczatek, przypadek.koniec,
                int(c.get("poczatek", 0)), int(c.get("koniec", 0)),
            ))
        pokrycie = najlepsze / dlugosc
        trafiony = pokrycie >= min_pokrycie

    poprawny = trafiony if przypadek.odpowiadalny else odmowil

    return Ocena(przypadek.id, przypadek.kategoria, przypadek.jezyk,
                 trafiony=trafiony, odmowil=odmowil, poprawny=poprawny,
                 pokrycie=pokrycie, czas_s=odpowiedz.czas_s)


# ── agregacja ────────────────────────────────────────────────────────

def _udzial(licznik: int, mianownik: int) -> float:
    return licznik / mianownik if mianownik else 0.0


def zbiorczo(przypadki: list[Przypadek], oceny: dict[str, Ocena]) -> dict:
    """Metryki zbiorcze dla całego przebiegu."""
    wg_id = {p.id: p for p in przypadki}

    odpowiadalne = [o for o in oceny.values() if wg_id[o.przypadek_id].odpowiadalny]
    odmowne = [o for o in oceny.values() if not wg_id[o.przypadek_id].odpowiadalny]

    # ── rozróżnialność par ───────────────────────────────────────────
    par_razem = 0
    par_rozroznionych = 0
    par_oba_odmowa = 0
    par_oba_odpowiedz = 0

    for p in przypadki:
        if not (p.odpowiadalny and p.para_id):
            continue
        a, b = oceny.get(p.id), oceny.get(p.para_id)
        if a is None or b is None:
            continue
        par_razem += 1
        if a.trafiony and b.odmowil:
            par_rozroznionych += 1
        elif a.odmowil and b.odmowil:
            par_oba_odmowa += 1
        elif not a.odmowil and not b.odmowil:
            par_oba_odpowiedz += 1

    czasy = sorted(o.czas_s for o in oceny.values() if o.czas_s > 0)

    def _percentyl(p: float) -> float:
        if not czasy:
            return 0.0
        return czasy[min(len(czasy) - 1, int(len(czasy) * p))]

    czulosc = _udzial(sum(1 for o in odpowiadalne if o.trafiony), len(odpowiadalne))
    swoistosc = _udzial(sum(1 for o in odmowne if o.odmowil), len(odmowne))

    return {
        "przypadkow": len(oceny),
        "bledow": sum(1 for o in oceny.values() if o.blad),

        # ── miara naczelna ───────────────────────────────────────────
        "rozroznialnosc_par": _udzial(par_rozroznionych, par_razem),
        "par": par_razem,
        "par_rozroznionych": par_rozroznionych,
        "par_zawsze_odmowa": par_oba_odmowa,
        "par_zawsze_odpowiedz": par_oba_odpowiedz,

        # ── bramki projektu ──────────────────────────────────────────
        "J3_odmowa_poprawna": swoistosc,
        "J4_odmowa_falszywa": _udzial(
            sum(1 for o in odpowiadalne if o.odmowil), len(odpowiadalne)),
        "trafnosc_zakotwiczona": czulosc,
        "srednie_pokrycie": _udzial(
            sum(o.pokrycie for o in odpowiadalne), len(odpowiadalne)),

        # Youden J — jedna liczba łącząca czułość i swoistość.
        # 0 dla każdego zachowania zdegenerowanego, 1 dla doskonałego.
        "youden_j": czulosc + swoistosc - 1.0,

        # ── wydajność ────────────────────────────────────────────────
        "czas_mediana_s": _percentyl(0.5),
        "czas_p90_s": _percentyl(0.9),
        "czas_max_s": czasy[-1] if czasy else 0.0,
    }


def wg_jezyka(przypadki: list[Przypadek], oceny: dict[str, Ocena]) -> dict[str, dict]:
    """Te same metryki w rozbiciu na języki — parytet PL/EN.

    Rozjazd między językami jest w tym systemie zjawiskiem zmierzonym,
    nie hipotetycznym: model polski proszony o dosłowne cytaty
    z angielskiego tekstu parafrazował, przez co weryfikator odrzucił
    62 z 68 twierdzeń (eval/wyniki/skala-2026-08-14.md). Ta funkcja
    pilnuje, żeby taki rozjazd nie wrócił niezauważony.
    """
    wynik: dict[str, dict] = {}
    for jezyk in sorted({p.jezyk for p in przypadki}):
        podzbior = [p for p in przypadki if p.jezyk == jezyk]
        ids = {p.id for p in podzbior}
        wynik[jezyk] = zbiorczo(
            podzbior, {k: v for k, v in oceny.items() if k in ids})
    return wynik


def parytet(wg_jez: dict[str, dict], miara: str = "rozroznialnosc_par") -> float:
    """Różnica bezwzględna między językami dla wskazanej miary.

    Zero oznacza pełny parytet. Wartość powyżej ~0,15 znaczy, że system
    jest realnie gorszy w jednym z języków i nie wolno raportować
    wyniku łącznego bez tego zastrzeżenia.
    """
    wartosci = [w.get(miara, 0.0) for w in wg_jez.values()]
    return max(wartosci) - min(wartosci) if len(wartosci) > 1 else 0.0
