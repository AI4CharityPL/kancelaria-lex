"""Przebieg benchmarku — odpytanie systemu i punktacja.

    python -m eval.benchmark.przebieg --sprawa 3 --sprawa 4 --par 25

Odpytuje TĘ SAMĄ ścieżkę, którą chodzi panel (`agent.odpowiedz`),
na tym samym zawężonym słowniku dokumentów. Benchmark mierzący
obejście produkcyjnej ścieżki mierzyłby cudzy system.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KORZEN))
sys.path.insert(0, str(KORZEN / "panel"))

from eval.benchmark import generator as gen          # noqa: E402
from eval.benchmark import korpus as mod_korpus      # noqa: E402
from eval.benchmark import miary                     # noqa: E402
from eval.benchmark.raport import zapisz_raport      # noqa: E402


def _odpytaj(przypadek: gen.Przypadek, dokumenty: dict[str, str],
             limit_dokumentow: int = 12) -> miary.Odpowiedz:
    """Jedno pytanie do systemu, torem szybkim.

    Zawężenie do `limit_dokumentow` odwzorowuje to, co robi panel:
    BM25 wybiera najtrafniejsze dokumenty, bo cała sprawa nie mieści
    się w kontekście. Bez tego kroku mierzylibyśmy model przy wsadzie,
    jakiego nigdy nie dostaje.
    """
    import agent
    import wyszukiwarka

    fragmenty = wyszukiwarka.podziel_wiele(dokumenty, {})
    trafne = wyszukiwarka.dokumenty_trafne(
        fragmenty, przypadek.pytanie, ile=limit_dokumentow)
    if not trafne:
        trafne = list(dokumenty)[:limit_dokumentow]
    zawezone = {d: dokumenty[d] for d in trafne if d in dokumenty}

    start = time.perf_counter()
    try:
        wynik = agent.odpowiedz(przypadek.pytanie, zawezone, historia=None)
    except Exception as e:                                # noqa: BLE001
        return miary.Odpowiedz(odmowa=False, czas_s=time.perf_counter() - start,
                               blad=f"{type(e).__name__}: {e}")
    czas = time.perf_counter() - start

    return miary.Odpowiedz(
        odmowa=bool(wynik.get("odmowa")),
        cytaty=wynik.get("cytaty") or [],
        tekst=wynik.get("tekst") or "",
        odrzucone=wynik.get("odrzucone") or [],
        czas_s=czas,
        blad=wynik.get("blad"),
    )


def uruchom(sprawy: list[int], par_na_sprawe: int = 25,
            limit_dokumentow: int | None = None,
            ziarno: int = 42, szczelnosc: bool = True,
            postep: bool = True) -> dict:
    """Pełny przebieg: generowanie, odpytanie, punktacja."""
    korpusy: dict[int, gen.Korpus] = {}
    przypadki: list[gen.Przypadek] = []

    for sprawa_id in sprawy:
        k = mod_korpus.z_bazy(sprawa_id, limit_dokumentow=limit_dokumentow)
        korpusy[sprawa_id] = k
        nowe = gen.generuj_pary(k, ile_par=par_na_sprawe, ziarno=ziarno)
        for p in nowe:
            przypadki.append(p)
        if postep:
            print(f"  sprawa {sprawa_id} [{k.jezyk}]: {len(k.dokumenty)} dok., "
                  f"{len(nowe)} przypadków", file=sys.stderr)

    # Szczelność — kotwice z jednej sprawy zadawane w drugiej.
    zrodla: dict[str, int] = {}
    if szczelnosc and len(sprawy) >= 2:
        for zrodlo_id in sprawy:
            for cel_id in sprawy:
                if zrodlo_id == cel_id:
                    continue
                nowe = gen.generuj_szczelnosc(
                    korpusy[zrodlo_id], korpusy[cel_id],
                    ile=max(5, par_na_sprawe // 3), ziarno=ziarno)
                for p in nowe:
                    przypadki.append(p)
                    zrodla[p.id] = cel_id
                if postep and nowe:
                    print(f"  szczelność {zrodlo_id}→{cel_id}: {len(nowe)}",
                          file=sys.stderr)

    # Mapowanie przypadek → sprawa, w której ma być zadany.
    for sprawa_id in sprawy:
        for p in przypadki:
            if p.id in zrodla:
                continue
            if p.dokument_id in korpusy[sprawa_id].dokumenty or (
                    p.dokument_id is None
                    and korpusy[sprawa_id].jezyk == p.jezyk
                    and p.id not in zrodla):
                zrodla.setdefault(p.id, sprawa_id)

    oceny: dict[str, miary.Ocena] = {}
    for i, p in enumerate(przypadki, start=1):
        sprawa_id = zrodla.get(p.id, sprawy[0])
        odp = _odpytaj(p, korpusy[sprawa_id].dokumenty)
        oceny[p.id] = miary.ocen(p, odp)
        if postep:
            znak = "OK " if oceny[p.id].poprawny else "BŁ "
            print(f"  [{i:3}/{len(przypadki)}] {znak} {p.kategoria:20} "
                  f"{odp.czas_s:5.1f}s  {p.pytanie[:58]}", file=sys.stderr)

    wynik = {
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sprawy": sprawy,
        "ziarno": ziarno,
        "generowanie": gen.statystyki(przypadki),
        "zbiorczo": miary.zbiorczo(przypadki, oceny),
        "wg_jezyka": miary.wg_jezyka(przypadki, oceny),
        "przypadki": [
            {
                "id": p.id, "kategoria": p.kategoria, "jezyk": p.jezyk,
                "pytanie": p.pytanie, "oczekiwanie": p.oczekiwanie,
                "kotwica": p.kotwica, "typ_kotwicy": p.typ_kotwicy,
                "trafiony": oceny[p.id].trafiony,
                "odmowil": oceny[p.id].odmowil,
                "poprawny": oceny[p.id].poprawny,
                "pokrycie": round(oceny[p.id].pokrycie, 3),
                "czas_s": round(oceny[p.id].czas_s, 2),
                "blad": oceny[p.id].blad,
            }
            for p in przypadki if p.id in oceny
        ],
    }
    wynik["parytet_jezykowy"] = miary.parytet(wynik["wg_jezyka"])
    return wynik


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark kancelaria-lex — wierność cytatu i odmowa.")
    parser.add_argument("--sprawa", type=int, action="append", required=True,
                        help="Identyfikator sprawy w bazie panelu (można wielokrotnie).")
    parser.add_argument("--par", type=int, default=25,
                        help="Ile par dopasowanych na sprawę.")
    parser.add_argument("--dokumenty", type=int, default=None,
                        help="Ogranicz liczbę dokumentów wczytanych ze sprawy.")
    parser.add_argument("--ziarno", type=int, default=42)
    parser.add_argument("--bez-szczelnosci", action="store_true")
    parser.add_argument("--wyjscie", type=Path, default=None,
                        help="Katalog na raport (domyślnie eval/wyniki/).")
    args = parser.parse_args(argv)

    print("Generowanie przypadków…", file=sys.stderr)
    wynik = uruchom(
        sprawy=args.sprawa, par_na_sprawe=args.par,
        limit_dokumentow=args.dokumenty, ziarno=args.ziarno,
        szczelnosc=not args.bez_szczelnosci,
    )

    katalog = args.wyjscie or (KORZEN / "eval" / "wyniki")
    katalog.mkdir(parents=True, exist_ok=True)
    znacznik = datetime.now().strftime("%Y-%m-%d-%H%M")

    (katalog / f"benchmark-{znacznik}.json").write_text(
        json.dumps(wynik, ensure_ascii=False, indent=2), encoding="utf-8")
    sciezka_md = zapisz_raport(wynik, katalog / f"benchmark-{znacznik}.md")

    z = wynik["zbiorczo"]
    print("\n" + "═" * 70)
    print(f"  ROZRÓŻNIALNOŚĆ PAR:  {z['rozroznialnosc_par']:.1%}  "
          f"({z['par_rozroznionych']}/{z['par']})")
    print(f"  Youden J:            {z['youden_j']:+.3f}")
    print(f"  J-3 odmowa poprawna: {z['J3_odmowa_poprawna']:.1%}")
    print(f"  J-4 odmowa fałszywa: {z['J4_odmowa_falszywa']:.1%}")
    print(f"  Parytet PL/EN:       {wynik['parytet_jezykowy']:.3f}")
    print(f"  Raport:              {sciezka_md}")
    print("═" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
