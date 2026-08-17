"""Wyczerpujący sprawdzian formatów daty — czy KAŻDY wariant przechodzi.

Zakotwiczenie odpowiedzi w pytaniu odrzuca cytat, w którym nie ma
wyróżnika z pytania. Jeżeli ten sam dzień zapisany inaczej nie zostanie
rozpoznany jako ta sama data, prawnik dostaje „w aktach nie ma podstawy
do odpowiedzi" przy zdaniu, które w aktach stoi.

Ten skrypt sprawdza obie strony naraz:
  1. czy wariant zapisu daje właściwą wartość,
  2. czy pytanie w JEDNYM formacie kotwiczy się na cytacie w KAŻDYM innym.

Punkt 2 jest istotniejszy: w praktyce prawnik pyta „14 września 2006",
a w aktach stoi „14.09.2006".

Uruchomienie:  python eval/sprawdz_daty.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panel"))

from wyrozniki import zakotwiczone, znajdz_daty  # noqa: E402


# (oczekiwana wartość ISO, warianty zapisu spotykane w aktach)
PRZYPADKI = [
    ("2016-10-06", [
        "October 6, 2016", "October 6th, 2016", "Oct. 6, 2016", "Oct 6, 2016",
        "6 October 2016", "6th October 2016", "2016-10-06", "10/6/2016",
        "10.6.2016", "10-6-2016", "06 October 2016",
    ]),
    ("2006-09-14", [
        "14 września 2006", "14 września 2006 r.", "14 września 2006 roku",
        "14.09.2006", "14/09/2006", "14-09-2006", "2006-09-14",
        "14 WRZEŚNIA 2006",
    ]),
    ("2023-01-01", [
        "1 stycznia 2023", "1 stycznia 2023 r.", "January 1, 2023",
        "January 1st, 2023", "1 January 2023", "01.01.2023", "2023-01-01",
        "Jan. 1, 2023",
    ]),
    ("2025-12-31", [
        "31 grudnia 2025", "December 31, 2025", "31 December 2025",
        "31.12.2025", "2025-12-31", "Dec. 31, 2025",
    ]),
]

# Zapisy, które NIE MOGĄ się zejść z 2016-10-06.
KONTROLE = [
    ("October 7, 2016", "sąsiedni dzień"),
    ("October 6, 2015", "inny rok"),
    ("November 6, 2016", "inny miesiąc"),
    ("throughout 2016 several motions", "sam zgodny rok"),
]


def main() -> int:
    bledy = 0

    print("═" * 74)
    print("  1. ROZPOZNANIE WARTOŚCI")
    print("═" * 74)
    for oczekiwana, warianty in PRZYPADKI:
        print(f"\n  {oczekiwana}")
        for w in warianty:
            znalezione = znajdz_daty(f"Zdarzenie miało miejsce {w} w sprawie.")
            ok = oczekiwana in znalezione
            print(f"    {'✓' if ok else '✗ BŁĄD'}  {w:<26} → {sorted(znalezione) or '—'}")
            bledy += not ok

    print("\n" + "═" * 74)
    print("  2. ZAKOTWICZENIE KRZYŻOWE (pytanie w formacie A, akta w formacie B)")
    print("═" * 74)
    for oczekiwana, warianty in PRZYPADKI:
        print(f"\n  {oczekiwana}  —  {len(warianty)}×{len(warianty)} kombinacji")
        niezgodne = []
        for pyt in warianty:
            for akt in warianty:
                pytanie = f"Jakie zdarzenie akta wiążą z datą {pyt}?"
                zdanie = f"Rozprawa odbyła się {akt} przed sądem."
                if not zakotwiczone(pytanie, [zdanie]):
                    niezgodne.append((pyt, akt))
        if niezgodne:
            bledy += len(niezgodne)
            print(f"    ✗ BŁĄD — {len(niezgodne)} kombinacji nie kotwiczy:")
            for pyt, akt in niezgodne[:8]:
                print(f"        pytanie [{pyt}] -> akta [{akt}]")
        else:
            print("    ✓ wszystkie kombinacje kotwiczą")

    print("\n" + "═" * 74)
    print("  3. KONTROLE — te NIE MOGĄ przechodzić")
    print("═" * 74)
    pytanie = "Jakie zdarzenie akta wiążą z datą October 6, 2016?"
    for zapis, opis in KONTROLE:
        przeszlo = zakotwiczone(pytanie, [f"Rozprawa odbyła się {zapis}."])
        print(f"    {'✗ BŁĄD' if przeszlo else '✓'}  {opis:<20} {zapis}")
        bledy += przeszlo

    print("\n" + "═" * 74)
    if bledy:
        print(f"  WYNIK: {bledy} BŁĘDÓW")
    else:
        laczna = sum(len(w) ** 2 for _, w in PRZYPADKI)
        print(f"  WYNIK: wszystko przechodzi "
              f"({laczna} kombinacji krzyżowych + {len(KONTROLE)} kontroli)")
    print("═" * 74)
    return 1 if bledy else 0


if __name__ == "__main__":
    raise SystemExit(main())
