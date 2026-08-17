"""Diagnoza wyników benchmarku — gdzie dokładnie system się myli.

Miary zbiorcze mówią ILE błędów. Ten skrypt mówi JAKICH, bo dopiero to
wskazuje lekarstwo. Fałszywa odmowa przy braku zdania w kontekście to
wada wyszukiwarki; ta sama odmowa przy zdaniu obecnym w kontekście to
wada modelu. Leczy się je zupełnie inaczej.

Uruchomienie:
    python eval/benchmark/diagnoza.py [plik.json]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[2]


def wczytaj(sciezka: Path | None) -> dict:
    if sciezka is None:
        wyniki = sorted((KORZEN / "eval" / "wyniki").glob("benchmark-*.json"))
        if not wyniki:
            raise SystemExit("Brak plików benchmark-*.json w eval/wyniki/")
        sciezka = wyniki[-1]
    print(f"Plik: {sciezka.name}\n")
    return json.loads(sciezka.read_text(encoding="utf-8"))


def rozklad(nazwa: str, wartosci) -> None:
    licznik = Counter(wartosci)
    if not licznik:
        return
    szer = max(len(str(k)) for k in licznik)
    print(f"  {nazwa}:")
    for k, n in licznik.most_common():
        print(f"    {str(k):<{szer}}  {n}")


def main() -> int:
    sciezka = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    d = wczytaj(sciezka)
    p = d["przypadki"]

    z_odpowiedzia = [x for x in p if x["oczekiwanie"] == "cytat"]
    bez_pokrycia = [x for x in p if x["oczekiwanie"] == "odmowa"]

    falszywa_odmowa = [x for x in z_odpowiedzia if x["odmowil"]]
    nietrafiony = [x for x in z_odpowiedzia
                   if not x["odmowil"] and not x["trafiony"]]
    trafiony = [x for x in z_odpowiedzia if x["trafiony"]]
    brak_odmowy = [x for x in bez_pokrycia if not x["odmowil"]]

    print("=" * 70)
    print(f"PYTANIA Z ODPOWIEDZIĄ: {len(z_odpowiedzia)}")
    print(f"  ✓ trafiony cytat        {len(trafiony):>3}")
    print(f"  ✗ FAŁSZYWA ODMOWA       {len(falszywa_odmowa):>3}   ← J-4, próg ≤10%")
    print(f"  ✗ odpowiedź, zły cytat  {len(nietrafiony):>3}")
    print()
    print(f"PYTANIA BEZ POKRYCIA: {len(bez_pokrycia)}")
    print(f"  ✓ poprawna odmowa       {len(bez_pokrycia)-len(brak_odmowy):>3}   ← J-3, próg ≥90%")
    print(f"  ✗ ZMYŚLONA ODPOWIEDŹ    {len(brak_odmowy):>3}")
    print("=" * 70)

    if falszywa_odmowa:
        print("\n── FAŁSZYWE ODMOWY ──")
        rozklad("język", (x["jezyk"] for x in falszywa_odmowa))
        rozklad("kategoria", (x["kategoria"] for x in falszywa_odmowa))
        rozklad("typ kotwicy", (x["typ_kotwicy"] for x in falszywa_odmowa))
        print()
        for x in falszywa_odmowa:
            print(f"    [{x['jezyk']}] {x['typ_kotwicy']:<10} {x['pytanie'][:74]}")

    if brak_odmowy:
        print("\n── ZMYŚLONE ODPOWIEDZI (najgroźniejsze) ──")
        rozklad("język", (x["jezyk"] for x in brak_odmowy))
        for x in brak_odmowy:
            print(f"    [{x['jezyk']}] {x['pytanie'][:74]}")

    if nietrafiony:
        print("\n── ODPOWIEDŹ Z NIEWŁAŚCIWYM CYTATEM ──")
        for x in nietrafiony:
            print(f"    [{x['jezyk']}] pokrycie={x['pokrycie']:.2f} {x['pytanie'][:64]}")

    bledy = [x for x in p if x.get("blad")]
    if bledy:
        print(f"\n── BŁĘDY WYKONANIA: {len(bledy)} ──")
        rozklad("treść", (str(x["blad"])[:60] for x in bledy))

    # Czy problem jest językowy?
    print("\n── ROZKŁAD BŁĘDÓW WG JĘZYKA ──")
    for jez in ("pl", "en"):
        zo = [x for x in z_odpowiedzia if x["jezyk"] == jez]
        bp = [x for x in bez_pokrycia if x["jezyk"] == jez]
        if not zo and not bp:
            continue
        fo = sum(1 for x in zo if x["odmowil"])
        zm = sum(1 for x in bp if not x["odmowil"])
        print(f"  {jez}:  fałszywa odmowa {fo}/{len(zo)}"
              f"   zmyślona odpowiedź {zm}/{len(bp)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
