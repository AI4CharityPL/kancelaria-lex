"""Raport z przebiegu — dwujęzyczny, po polsku i angielsku.

Dwujęzyczność nie jest ozdobnikiem. Raport z bramek jest materiałem
dowodowym dla art. 32 ust. 1 lit. d RODO i art. 21 ust. 2 lit. f ustawy
o KSC (docs/11-testy-i-bramki.md), a jednocześnie jedyną postacią,
w jakiej ten pomiar da się pokazać poza Polską. Jeden dokument w dwóch
językach jest audytowalny; dwa osobne rozjeżdżają się po pierwszej
poprawce.
"""

from __future__ import annotations

from pathlib import Path

# ── słownik miar / metric glossary ───────────────────────────────────

MIARY = {
    "rozroznialnosc_par": (
        "Rozróżnialność par",
        "Pair discrimination",
        "Para liczy się tylko wtedy, gdy system zacytował właściwy fragment "
        "w pytaniu z odpowiedzią ORAZ odmówił w bliźniaku. Oba zachowania "
        "zdegenerowane — „zawsze odpowiadaj” i „zawsze odmawiaj” — dostają zero.",
        "A pair counts only if the system cites the correct span for the "
        "answerable question AND refuses its twin. Both degenerate "
        "strategies — always answer, always refuse — score zero.",
    ),
    "youden_j": (
        "Youden J",
        "Youden's J",
        "Czułość + swoistość − 1. Zero dla zachowania zdegenerowanego, "
        "jeden dla doskonałego.",
        "Sensitivity + specificity − 1. Zero for degenerate behaviour, "
        "one for perfect.",
    ),
    "trafnosc_zakotwiczona": (
        "Trafność zakotwiczona",
        "Anchored hit rate",
        "Udział pytań z odpowiedzią, w których cytat trafił we właściwy "
        "zakres właściwego dokumentu.",
        "Share of answerable questions where the citation landed on the "
        "correct span of the correct document.",
    ),
    "J3_odmowa_poprawna": (
        "J-3 · odmowa poprawna",
        "J-3 · correct refusal",
        "Udział pytań bez pokrycia, w których system odmówił. Próg ≥ 90%.",
        "Share of unanswerable questions correctly refused. Gate ≥ 90%.",
    ),
    "J4_odmowa_falszywa": (
        "J-4 · odmowa fałszywa",
        "J-4 · false refusal",
        "Udział pytań Z ODPOWIEDZIĄ, w których system mimo to odmówił. "
        "Próg ≤ 10%. Chroni przed zdegenerowaniem w stronę „odmawiaj zawsze”.",
        "Share of ANSWERABLE questions the system refused anyway. "
        "Gate ≤ 10%. Guards against degenerating into always-refuse.",
    ),
    "srednie_pokrycie": (
        "Średnie pokrycie wzorca",
        "Mean span coverage",
        "Jaka część zdania wzorcowego została objęta cytatem.",
        "Fraction of the reference sentence covered by the citation.",
    ),
}

PROGI = {
    "J3_odmowa_poprawna": (0.90, "min"),
    "J4_odmowa_falszywa": (0.10, "max"),
}


def _ocena_progu(klucz: str, wartosc: float) -> str:
    if klucz not in PROGI:
        return ""
    prog, kierunek = PROGI[klucz]
    ok = wartosc >= prog if kierunek == "min" else wartosc <= prog
    return " ✅" if ok else " ❌"


def zbuduj_raport(wynik: dict) -> str:
    z = wynik["zbiorczo"]
    g = wynik["generowanie"]
    wj = wynik["wg_jezyka"]

    L: list[str] = []
    A = L.append

    A("# Benchmark kancelaria-lex")
    A("")
    A(f"**Data / Date:** {wynik['data']}  ")
    A(f"**Sprawy / Cases:** {', '.join(map(str, wynik['sprawy']))}  ")
    A(f"**Ziarno / Seed:** {wynik['ziarno']} — przebieg jest powtarzalny "
      f"/ run is reproducible")
    A("")
    A("---")
    A("")

    # ── PL ───────────────────────────────────────────────────────────
    A("## 🇵🇱 Wynik")
    A("")
    A("### Miara naczelna")
    A("")
    A(f"> **Rozróżnialność par: {z['rozroznialnosc_par']:.1%}** "
      f"({z['par_rozroznionych']} z {z['par']} par)")
    A("")
    A("Para liczy się wyłącznie wtedy, gdy system zacytował właściwy fragment")
    A("w pytaniu z odpowiedzią **oraz** odmówił w bliźniaku. Pytania w parze")
    A("mają identyczną formę i różnią się tylko wartością kotwicy, więc")
    A("różnicy nie da się wytłumaczyć trudnością pytania.")
    A("")
    A("| Rozkład par | Liczba | Znaczenie |")
    A("|---|---:|---|")
    A(f"| Rozróżnione | {z['par_rozroznionych']} | zachowanie prawidłowe |")
    A(f"| Odmowa w obu | {z['par_zawsze_odmowa']} | system nie znalazł "
      f"odpowiedzi, która była |")
    A(f"| Odpowiedź w obu | {z['par_zawsze_odpowiedz']} | **system odpowiedział "
      f"na pytanie bez pokrycia** |")
    A("")

    A("### Bramki jakościowe")
    A("")
    A("| Miara | Wynik | Próg |")
    A("|---|---:|---|")
    for klucz in ("J3_odmowa_poprawna", "J4_odmowa_falszywa",
                  "trafnosc_zakotwiczona", "srednie_pokrycie", "youden_j"):
        nazwa = MIARY[klucz][0]
        wartosc = z[klucz]
        postac = f"{wartosc:+.3f}" if klucz == "youden_j" else f"{wartosc:.1%}"
        prog = PROGI.get(klucz)
        opis_progu = (f"{'≥' if prog[1] == 'min' else '≤'} {prog[0]:.0%}"
                      if prog else "—")
        A(f"| {nazwa} | {postac}{_ocena_progu(klucz, wartosc)} | {opis_progu} |")
    A("")

    A("### Parytet językowy")
    A("")
    A(f"Różnica rozróżnialności między językami: **{wynik['parytet_jezykowy']:.3f}**")
    A("")
    A("| Język | Przypadków | Rozróżnialność | J-3 | J-4 | Mediana czasu |")
    A("|---|---:|---:|---:|---:|---:|")
    for jezyk, m in sorted(wj.items()):
        A(f"| {jezyk.upper()} | {m['przypadkow']} | "
          f"{m['rozroznialnosc_par']:.1%} | {m['J3_odmowa_poprawna']:.1%} | "
          f"{m['J4_odmowa_falszywa']:.1%} | {m['czas_mediana_s']:.1f} s |")
    A("")
    if wynik["parytet_jezykowy"] > 0.15:
        A("> ⚠️ **Rozjazd językowy powyżej 0,15.** Wyniku łącznego nie wolno")
        A("> raportować bez tego zastrzeżenia — system jest realnie gorszy")
        A("> w jednym z języków.")
        A("")

    A("### Wydajność")
    A("")
    A(f"- mediana: **{z['czas_mediana_s']:.1f} s** · "
      f"p90: **{z['czas_p90_s']:.1f} s** · maks.: {z['czas_max_s']:.1f} s")
    A(f"- przypadków: {z['przypadkow']} · błędów: {z['bledow']}")
    A("")

    A("### Zbiór testowy")
    A("")
    A(f"- par dopasowanych: **{g['par']}** · przypadków razem: {g['razem']}")
    A(f"- kategorie: {g['wg_kategorii']}")
    A(f"- typy kotwic: {g['wg_typu_kotwicy']}")
    A("")
    A("Prawda wzorcowa wyznaczona maszynowo: dla pytań z odpowiedzią jest to")
    A("zakres znaków w dokumencie źródłowym, dla bliźniaków — potwierdzony")
    A("wyszukiwaniem brak kotwicy w całych aktach. Bez sędziego LLM")
    A("i bez pracy prawnika (ADR-0006).")
    A("")
    A("---")
    A("")

    # ── EN ───────────────────────────────────────────────────────────
    A("## 🇬🇧 Results")
    A("")
    A("### Headline metric")
    A("")
    A(f"> **Pair discrimination: {z['rozroznialnosc_par']:.1%}** "
      f"({z['par_rozroznionych']} of {z['par']} pairs)")
    A("")
    A("A pair counts only if the system cited the correct span for the")
    A("answerable question **and** refused its twin. Both questions in a pair")
    A("are form-identical and differ only in the anchor value, so the")
    A("difference cannot be explained by question difficulty.")
    A("")
    A("| Pair outcome | Count | Meaning |")
    A("|---|---:|---|")
    A(f"| Discriminated | {z['par_rozroznionych']} | correct behaviour |")
    A(f"| Refused both | {z['par_zawsze_odmowa']} | missed an answer that "
      f"was present |")
    A(f"| Answered both | {z['par_zawsze_odpowiedz']} | **answered a question "
      f"with no support in the files** |")
    A("")

    A("### Quality gates")
    A("")
    A("| Metric | Result | Gate |")
    A("|---|---:|---|")
    for klucz in ("J3_odmowa_poprawna", "J4_odmowa_falszywa",
                  "trafnosc_zakotwiczona", "srednie_pokrycie", "youden_j"):
        nazwa = MIARY[klucz][1]
        wartosc = z[klucz]
        postac = f"{wartosc:+.3f}" if klucz == "youden_j" else f"{wartosc:.1%}"
        prog = PROGI.get(klucz)
        opis_progu = (f"{'≥' if prog[1] == 'min' else '≤'} {prog[0]:.0%}"
                      if prog else "—")
        A(f"| {nazwa} | {postac}{_ocena_progu(klucz, wartosc)} | {opis_progu} |")
    A("")

    A("### Language parity")
    A("")
    A(f"Absolute gap in pair discrimination between languages: "
      f"**{wynik['parytet_jezykowy']:.3f}**")
    A("")
    A("| Language | Cases | Discrimination | J-3 | J-4 | Median latency |")
    A("|---|---:|---:|---:|---:|---:|")
    for jezyk, m in sorted(wj.items()):
        A(f"| {jezyk.upper()} | {m['przypadkow']} | "
          f"{m['rozroznialnosc_par']:.1%} | {m['J3_odmowa_poprawna']:.1%} | "
          f"{m['J4_odmowa_falszywa']:.1%} | {m['czas_mediana_s']:.1f} s |")
    A("")

    A("### Method")
    A("")
    A("Ground truth is derived mechanically, never by an LLM judge:")
    A("answerable cases carry an exact character span in the source document;")
    A("their twins are verified absent by exhaustive search over the case")
    A("files. No annotator time is required, so the benchmark scales with")
    A("the corpus rather than with reviewer availability.")
    A("")
    A("---")
    A("")
    A("## Słownik miar / Metric glossary")
    A("")
    for klucz, (pl, en, opis_pl, opis_en) in MIARY.items():
        A(f"**{pl} / {en}**  ")
        A(f"🇵🇱 {opis_pl}  ")
        A(f"🇬🇧 {opis_en}")
        A("")

    return "\n".join(L)


def zapisz_raport(wynik: dict, sciezka: Path) -> Path:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(zbuduj_raport(wynik), encoding="utf-8")
    return sciezka
