"""Pomiar kontroli wsparcia PRZED wpięciem jej do potoku.

DLACZEGO OSOBNO, A NIE OD RAZU W POTOKU

W tej sesji zaostrzenie zakotwiczenia bez sprawdzenia, co robi etap
wcześniejszy, zamieniło jedną degenerację na drugą: fałszywe odpowiedzi
spadły, ale fałszywe odmowy wzrosły z 12,5% na 56%. Kontrola dokładana
w ciemno robi dokładnie to samo ryzyko.

Ten skrypt puszcza kontrolę na ZNANYCH przypadkach z benchmarku
i pokazuje, ile z nich łapie — i ile poprawnych psuje.

Pytania, na które odpowiada:
    1. ile twierdzeń odpada na kontroli mechanicznej (za darmo)
    2. ile trafia do kontroli modelem i ile to kosztuje czasu
    3. czy kontrola odróżnia przypadki ZNANE jako dobre od ZNANYCH
       jako złe — bo jeśli nie, nie ma po co jej wpinać

Uruchomienie:
    python eval/zmierz_kontrole.py [--z-modelem] [plik.json]
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import agent  # noqa: E402
import baza  # noqa: E402
import kontrola as mod_kontrola  # noqa: E402
import wsparcie as mod_wsparcie  # noqa: E402
import wyszukiwarka  # noqa: E402


def _wczytaj(sciezka: Path | None) -> dict:
    if sciezka is None:
        pliki = sorted((KORZEN / "eval" / "wyniki").glob("benchmark-*.json"))
        if not pliki:
            raise SystemExit("Brak wyników benchmarku.")
        sciezka = pliki[-1]
    print(f"Wynik odniesienia: {sciezka.name}\n")
    return json.loads(sciezka.read_text(encoding="utf-8"))


def main() -> int:
    z_modelem = "--z-modelem" in sys.argv
    pliki = [a for a in sys.argv[1:] if not a.startswith("--")]
    dane = _wczytaj(Path(pliki[0]) if pliki else None)

    # Przypadki znane jako dobre i jako złe — z ocen benchmarku.
    dobre = [p for p in dane["przypadki"]
             if p["oczekiwanie"] == "cytat" and p["trafiony"]]
    zle = [p for p in dane["przypadki"]
           if p["oczekiwanie"] == "cytat" and not p["odmowil"] and not p["trafiony"]]

    print(f"Przypadki ZNANE JAKO DOBRE (trafiony cytat):  {len(dobre)}")
    print(f"Przypadki ZNANE JAKO ZŁE (zły cytat):        {len(zle)}")
    if not dobre and not zle:
        print("\nBrak przypadków do oceny w tym raporcie.")
        return 1

    db = baza.polacz()
    korpusy = {3: baza.tresci_dokumentow(db, 3), 4: baza.tresci_dokumentow(db, 4)}
    fragmenty = {k: wyszukiwarka.podziel_wiele(v, {}) for k, v in korpusy.items()}

    print(f"\n{'klasa':<8} {'stopień':<8} {'pokrycie':>9} {'werdykt':<16} "
          f"{'czas':>7}  pytanie")
    print("-" * 96)

    statystyka: dict[str, Counter] = {"dobre": Counter(), "zle": Counter()}
    czasy: list[float] = []
    wywolan = 0

    for etykieta, grupa in (("dobre", dobre), ("zle", zle)):
        for p in grupa:
            sprawa = 3 if p["jezyk"] == "pl" else 4
            zaw = {d: korpusy[sprawa][d] for d in wyszukiwarka.dokumenty_trafne(
                fragmenty[sprawa], p["pytanie"], ile=12) if d in korpusy[sprawa]}
            w = agent.odpowiedz(p["pytanie"], zaw)
            if w.get("blad") or not w.get("cytaty"):
                statystyka[etykieta]["brak odpowiedzi"] += 1
                continue

            tekst = w["tekst"]
            cytaty = [c["fragment"] for c in w["cytaty"]]
            ws = mod_wsparcie.oszacuj(tekst, cytaty, p["jezyk"])
            statystyka[etykieta][f"mech:{ws.stopien.value}"] += 1

            werdykt, czas = "—", 0.0
            if z_modelem and ws.wymaga_kontroli_modelem:
                wynik = mod_kontrola.sprawdz(tekst, cytaty, p["jezyk"])
                werdykt, czas = wynik.werdykt.value, wynik.czas_s
                czasy.append(czas)
                wywolan += 1
                statystyka[etykieta][f"model:{werdykt}"] += 1

            print(f"{etykieta:<8} {ws.stopien.value:<8} {ws.pokrycie:>8.2f} "
                  f"{werdykt:<16} {czas:>6.1f}s  {p['pytanie'][:40]}")

    print("\n" + "=" * 96)
    for etykieta in ("dobre", "zle"):
        print(f"\n{etykieta.upper()}:")
        for k, n in sorted(statystyka[etykieta].items()):
            print(f"   {k:<24} {n}")

    if czasy:
        czasy.sort()
        print(f"\nKOSZT KONTROLI MODELEM:")
        print(f"   wywołań:  {wywolan}")
        print(f"   mediana:  {czasy[len(czasy)//2]:.1f}s")
        print(f"   suma:     {sum(czasy):.1f}s")

    print("\nCZYTANIE WYNIKU:")
    print("   Kontrola ma sens, gdy w klasie ZŁE dominuje 'brak'/'falsz',")
    print("   a w klasie DOBRE dominuje 'mocne'/'prawda'. Odwrotny rozkład")
    print("   znaczy, że kontrola psułaby poprawne odpowiedzi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
