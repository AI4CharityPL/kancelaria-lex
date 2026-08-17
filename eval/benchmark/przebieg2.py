"""Przebieg benchmarku v2 — z przypisaniem etapu.

    python -m eval.benchmark.przebieg2 --sprawa 3 --sprawa 4 --par 8

Różnica wobec v1 nie polega na innych pytaniach — zbiór jest ten sam,
generator ten sam, ziarno to samo. Różnica polega na tym, że v2
odpowiada na pytanie „GDZIE przypadek umarł", a v1 tylko „czy umarł".
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
from eval.benchmark import v2                        # noqa: E402


def _zdanie_dotarlo(przypadek: gen.Przypadek, dokumenty: dict[str, str]) -> bool:
    """Czy zdanie wzorcowe znalazło się we wsadzie pokazanym modelowi.

    ⚠️ To jest pomiar RETRIEVALU W IZOLACJI, wzorowany na LegalBench-RAG.
    Bez niego „model nie znalazł odpowiedzi" i „modelowi nie pokazano
    odpowiedzi" są w wyniku nieodróżnialne — a to dwa zupełnie różne
    problemy, wymagające dwóch różnych napraw.

    Powtarza dokładnie ten sam wybór, który robi tor szybki, więc mierzy
    to, co system faktycznie widzi, a nie osobną ścieżkę.
    """
    import agent

    if przypadek.poczatek is None or przypadek.dokument_id is None:
        return False

    # ⚠️ Przez `agent._wybor_zdan`, a nie własnym wywołaniem.
    # Pomiar retrievalu musi używać DOKŁADNIE tej ścieżki, którą chodzi
    # potok — inaczej mierzy inny wybór niż ten, który widzi model,
    # i „recall retrievalu" przestaje cokolwiek znaczyć.
    wybor = agent._wybor_zdan(dokumenty, przypadek.pytanie)

    for z in wybor.zdania:
        if z.dokument_id != przypadek.dokument_id:
            continue
        if min(z.koniec, przypadek.koniec) - max(z.poczatek, przypadek.poczatek) > 0:
            return True
    return False


# ── KONFIGURACJA ZAPISANA W RAPORCIE ─────────────────────────────────
#
# ⚠️ USTERKA, KTÓRA UNIEWAŻNIAŁA BRAMKĘ JAKOŚCI — ZNALEZIONA 16.08.2026.
#
# Raport nie zapisywał NICZEGO o układzie, w którym powstał. Wszystkie
# przebiegi wyglądały więc identycznie: `v2-<data>.json`, te same pola,
# te same sprawy, to samo ziarno. Nie dało się odróżnić pomiaru
# konfiguracji wysyłkowej od pomiaru eksperymentu, który sprawdzono
# i ODRZUCONO.
#
# Skutek był natychmiastowy i mylący. Bramka bierze najnowszy pełny
# raport — a najnowszym pełnym był przebieg odrzuconej hipotezy
# „NL-do-formatu" (trafność 58%, J-3 86%). Bramka orzekała więc REGRES
# systemu na podstawie pomiaru układu, którego nikt nie zamierzał
# wysyłać, i wskazywała winnego tam, gdzie żadnej winy nie było.
#
# To ta sama klasa błędu, którą ten projekt popełnił już czterokrotnie:
# porównywanie przebiegów z różnych układów. Tym razem popełniło ją
# narzędzie, a nie człowiek — więc lekarstwem też musi być kod.
#
# Zapisujemy WYŁĄCZNIE przełączniki zmieniające zachowanie potoku.
# Nie czasy, nie limity, nie nazwy plików — inaczej każda kosmetyczna
# zmiana unieważniałaby historyczne raporty.
def konfiguracja() -> dict:
    """Układ potoku, w którym powstał ten pomiar."""
    import agent

    return {
        "kontrola_mechaniczna": bool(agent.KONTROLA_MECHANICZNA),
        "kontrola_modelem": bool(agent.KONTROLA_MODELEM),
        "kontrola_cien": bool(agent.KONTROLA_CIEN),
        "nl_do_formatu": bool(agent.NL_DO_FORMATU),
        "probek": int(agent.PROBEK),
        "dokumentow_w_torze_szybkim": int(agent.DOKUMENTOW_W_TORZE_SZYBKIM),
        "dokumentow_w_eskalacji": int(agent.DOKUMENTOW_W_ESKALACJI),
    }


def uruchom(sprawy: list[int], par: int = 8, ziarno: int = 42,
            dokumenty_limit: int | None = None) -> dict:
    import agent
    import wyszukiwarka

    korpusy: dict[int, gen.Korpus] = {}
    przypadki: list[gen.Przypadek] = []
    gdzie: dict[str, int] = {}

    for sprawa_id in sprawy:
        k = mod_korpus.z_bazy(sprawa_id, limit_dokumentow=dokumenty_limit)
        korpusy[sprawa_id] = k
        for p in gen.generuj_pary(k, ile_par=par, ziarno=ziarno):
            przypadki.append(p)
            gdzie[p.id] = sprawa_id
        print(f"  sprawa {sprawa_id} [{k.jezyk}]: {len(k.dokumenty)} dok.",
              file=sys.stderr)

    oceny: dict[str, v2.OcenaV2] = {}
    for i, p in enumerate(przypadki, start=1):
        k = korpusy[gdzie[p.id]]

        # Zawężenie jak w panelu — BM25 wybiera dokumenty do czytania.
        fragmenty = wyszukiwarka.podziel_wiele(k.dokumenty, {})
        trafne = wyszukiwarka.dokumenty_trafne(fragmenty, p.pytanie, ile=12)
        zaw = {d: k.dokumenty[d] for d in trafne if d in k.dokumenty} \
            or dict(list(k.dokumenty.items())[:12])

        dotarlo = _zdanie_dotarlo(p, zaw) if p.odpowiadalny else True
        wystapienia = v2.wszystkie_wystapienia(k, p) if p.odpowiadalny else []

        t0 = time.perf_counter()
        try:
            odp = agent.odpowiedz(p.pytanie, zaw)
        except Exception as e:                            # noqa: BLE001
            odp = {"blad": f"{type(e).__name__}: {e}", "cytaty": [],
                   "odrzucone": [], "odmowa": False}
        odp["_czas_s"] = time.perf_counter() - t0

        oceny[p.id] = v2.ocen(p, odp, wystapienia, dotarlo)
        o = oceny[p.id]
        print(f"  [{i:3}/{len(przypadki)}] {'OK ' if o.poprawny else 'BŁ '} "
              f"{o.etap.value:<14} wyst={o.liczba_wystapien:<3} "
              f"{o.czas_s:5.1f}s  {p.pytanie[:44]}", file=sys.stderr)

    return {
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "wersja": "v2",
        "sprawy": sprawy, "ziarno": ziarno,
        "konfiguracja": konfiguracja(),
        "podsumowanie": v2.podsumuj(przypadki, oceny),
        "wg_jezyka": {
            j: v2.podsumuj([p for p in przypadki if p.jezyk == j],
                           {k_: v for k_, v in oceny.items()
                            if v.jezyk == j})
            for j in sorted({p.jezyk for p in przypadki})
        },
        "przypadki": [
            {"id": o.przypadek_id, "kategoria": o.kategoria, "jezyk": o.jezyk,
             "etap": o.etap.value, "poprawny": o.poprawny,
             "trafiony": o.trafiony, "zdanie_dotarlo": o.zdanie_dotarlo,
             "wystapien": o.liczba_wystapien, "czas_s": round(o.czas_s, 2),
             "szczegol": o.szczegol,
             **({"cien_odpowiedzialby": o.odpowiedzialby_z_kontrola,
                 "cien_trafiony": o.trafiony_z_kontrola,
                 "cien_odrzuconych": o.twierdzen_odrzuconych}
                if o.kontrola_cien else {})}
            for o in oceny.values()
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark v2 — z etapami.")
    ap.add_argument("--sprawa", type=int, action="append", required=True)
    ap.add_argument("--par", type=int, default=8)
    ap.add_argument("--ziarno", type=int, default=42)
    ap.add_argument("--dokumenty", type=int, default=None)
    ap.add_argument(
        "--cien", action="store_true",
        help="Kontrola liczy się, ale nie odrzuca — jeden przebieg daje "
             "wynik z kontrolą i bez, na tym samym zbiorze.")
    a = ap.parse_args(argv)

    if a.cien:
        import agent
        agent.KONTROLA_CIEN = True
        print("  tryb CIENIA: kontrola mierzona, twierdzenia nieodrzucane",
              file=sys.stderr)

    wynik = uruchom(a.sprawa, a.par, a.ziarno, a.dokumenty)

    katalog = KORZEN / "eval" / "wyniki"
    katalog.mkdir(parents=True, exist_ok=True)
    znacznik = datetime.now().strftime("%Y-%m-%d-%H%M")
    (katalog / f"v2-{znacznik}.json").write_text(
        json.dumps(wynik, ensure_ascii=False, indent=2), encoding="utf-8")

    p = wynik["podsumowanie"]
    print("\n" + "=" * 68)
    print(f"  TRAFNOŚĆ:            {p['trafnosc']:.1%}")
    print(f"  RECALL RETRIEVALU:   {p['recall_retrievalu']:.1%}  "
          f"← ile zdań wzorcowych DOTARŁO do modelu")
    print(f"  średnio wystąpień:   {p['srednia_wystapien']:.1f}  "
          f"(przypadków bez żadnego: {p['bez_wystapien']})")
    print()
    znak = "✅" if p["J3_odmowa_poprawna"] >= 0.90 else "❌"
    print(f"  J-3 ODMOWA POPRAWNA: {p['J3_odmowa_poprawna']:.1%} {znak}  "
          f"({p['bez_pokrycia_odmowionych']}/{p['bez_pokrycia']})   próg ≥ 90%")
    print(f"     ⚠️  fałszywe ODPOWIEDZI (akta nie dają podstawy): "
          f"{p['falszywe_odpowiedzi']}")
    print()
    print(f"  BŁĘDY PRZY PYTANIACH Z ODPOWIEDZIĄ:")
    print(f"     fałszywe odmowy    {p['falszywych_odmow']:>3}  "
          f"(odmówił, choć odpowiedź była)")
    print(f"     błędne odpowiedzi  {p['blednych_odpowiedzi']:>3}  "
          f"(odpowiedział, cytat nie trafił)")
    if p["etapy_falszywych_odmow"]:
        print("     gdzie giną odmowy:", p["etapy_falszywych_odmow"])
    print()
    print(f"  wszystkie etapy: {p['etapy']}")

    if p.get("gdyby_kontrola"):
        k = p["gdyby_kontrola"]
        print("\n" + "-" * 68)
        print("  GDYBY KONTROLA ODRZUCAŁA (ten sam zbiór, ten sam przebieg)")
        ws, km = k.get("sama_mechanika", {}), k.get("sam_kontroler", {})
        naglowek = (f"     {'':<22}{'bez':>10}{'mechanika':>12}"
                    f"{'kontroler':>12}{'obie':>10}")
        print(naglowek)

        def _wiersz(nazwa, klucz, procent=False):
            f = (lambda v: f"{v:.1%}") if procent else (lambda v: f"{v}")
            print(f"     {nazwa:<22}{f(p[klucz]):>10}{f(ws[klucz]):>12}"
                  f"{f(km[klucz]):>12}{f(k[klucz]):>10}")

        _wiersz("J-3 odmowa poprawna", "J3_odmowa_poprawna", procent=True)
        _wiersz("fałszywe odpowiedzi", "falszywe_odpowiedzi")
        _wiersz("trafność", "trafnosc", procent=True)
        print()
        print(f"     {'twierdzeń odrzuconych':<22}{'':>10}"
              f"{ws['twierdzen_odrzuconych']:>12}"
              f"{km['twierdzen_odrzuconych']:>12}"
              f"{k['twierdzen_odrzuconych']:>10}")
        print(f"     {'utracone trafienia':<22}{'':>10}"
              f"{ws['utracone_trafienia']:>12}{km['utracone_trafienia']:>12}"
              f"{k['utracone_trafienia']:>10}")
        print(f"     {'zatrzymane fałszywe':<22}{'':>10}"
              f"{p['falszywe_odpowiedzi'] - ws['falszywe_odpowiedzi']:>12}"
              f"{p['falszywe_odpowiedzi'] - km['falszywe_odpowiedzi']:>12}"
              f"{p['falszywe_odpowiedzi'] - k['falszywe_odpowiedzi']:>10}")

        if k.get("przyczyny_odrzucen"):
            print("\n     DLACZEGO CYTAT ODPADŁ "
                  "(szkodliwe = trafiał w prawdziwe wystąpienie)")
            print(f"     {'przyczyna':<14}{'razem':>7}{'szkodliwe':>11}"
                  f"{'pokrycie':>18}")
            for nazwa, w in k["przyczyny_odrzucen"].items():
                zakres = ("—" if w["pokrycie_min"] is None
                          else f"{w['pokrycie_min']}–{w['pokrycie_maks']}")
                print(f"     {nazwa:<14}{w['razem']:>7}{w['szkodliwe']:>11}"
                      f"{zakres:>18}")
        if k.get("wyrozniki_szkodliwe"):
            print("\n     WYRÓŻNIKI WYCIĘTE SZKODLIWIE "
                  "(kandydaci na nadgorliwy wzorzec):")
            for wyr, ile in k["wyrozniki_szkodliwe"].items():
                print(f"       {ile:>3}× {wyr}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
