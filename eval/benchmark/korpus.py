"""Wczytywanie akt do benchmarku — z bazy panelu albo z plików.

Benchmark celowo czyta te same akta, na których pracuje panel, i tą
samą drogą (`baza.tresci_dokumentow`). Gdyby korzystał z osobnej kopii,
mierzyłby coś innego niż to, co widzi system.

⚠️ ZASADA T-6 OBOWIĄZUJE TAKŻE TUTAJ.
   Benchmark uruchamiamy na korpusie syntetycznym i publicznym.
   Sprawy 3 i 4 to publiczne orzeczenia SAOS i jawne akta federalne
   USA — nadają się do pomiaru i nie są aktami klienta.
   Rzeczywiste akta nie wchodzą do żadnego przebiegu ewaluacyjnego
   (docs/09-compliance/tajemnica-zawodowa.md).
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402

from .generator import Korpus  # noqa: E402

# ── oczyszczanie znaczników ──────────────────────────────────────────
#
# ⚠️ ZNALEZISKO O SAMYM SYSTEMIE, NIE O BENCHMARKU.
#
# Dokumenty sprawy 3 (320 orzeczeń SAOS) zostały wgrane do panelu
# RAZEM ZE ZNACZNIKAMI HTML: <p>, <div>, <h2>, <td colspan="3">,
# <span class="anon-block">. Panel widzi je tak samo jak treść.
#
# Skutki są trzy i wszystkie kosztują jakość:
#
#   1. Tokenizacja BM25 indeksuje „colspan", „anon", „block" jako
#      wyrazy treści — rozcieńcza ranking.
#   2. Do modelu w budżecie 9000 znaków wchodzą znaczniki zamiast
#      zdań; przy dokumencie gęsto otagowanym to realna strata wsadu.
#   3. Cytat wskazuje zakres razem ze znacznikiem, więc prawnik
#      dostaje „<p>Dnia 16 kwietnia 2026 r.</p>" jako fragment akt.
#
# Benchmark czyści je przy wczytaniu, ŻEBY MIERZYĆ MODEL, A NIE
# JAKOŚĆ IMPORTU. To jest obejście na potrzeby pomiaru — właściwym
# miejscem naprawy jest ścieżka wgrywania dokumentu (`baza.dodaj_dokument`
# albo przyszły `panel/pliki.py`), gdzie znaczniki powinny zostać
# usunięte raz, przy wejściu.
#
# Oczyszczanie zachowuje granice akapitów, bo od nich zależy podział
# na zdania.

_SKRYPTY = re.compile(r"<(script|style)\b[^>]*>.*?</\1>",
                      re.IGNORECASE | re.DOTALL)
_BLOKOWE = re.compile(r"</?(p|div|br|tr|li|h[1-6]|table|td|th)\b[^>]*>",
                      re.IGNORECASE)
_ZNACZNIK = re.compile(r"<[^>]{1,200}>")


def oczysc_html(tekst: str) -> str:
    """Usuwa znaczniki, zachowując granice akapitów."""
    if "<" not in tekst:
        return tekst
    tekst = _SKRYPTY.sub(" ", tekst)
    tekst = _BLOKOWE.sub("\n", tekst)
    tekst = _ZNACZNIK.sub(" ", tekst)
    tekst = html.unescape(tekst)
    tekst = re.sub(r"[ \t ]+", " ", tekst)
    return re.sub(r"\n{3,}", "\n\n", tekst).strip()


def udzial_znacznikow(tekst: str) -> float:
    """Jaka część znaków to znaczniki — do raportu o jakości importu."""
    if not tekst:
        return 0.0
    return sum(len(m.group(0)) for m in _ZNACZNIK.finditer(tekst)) / len(tekst)


def z_bazy(sprawa_id: int, sciezka_bazy: Path | None = None,
           limit_dokumentow: int | None = None,
           czysc_html: bool = True) -> Korpus:
    """Wczytuje akta sprawy tą samą drogą, którą chodzi panel.

    `czysc_html=False` pokazuje akta dokładnie tak, jak widzi je panel —
    ze znacznikami. Przydatne do zmierzenia, ILE kosztuje ich obecność.
    """
    db = baza.polacz(sciezka_bazy)
    try:
        sprawa = baza.pobierz_sprawe(db, sprawa_id)
        if sprawa is None:
            raise ValueError(f"Sprawa {sprawa_id} nie istnieje w bazie.")

        dokumenty = baza.tresci_dokumentow(db, sprawa_id)
        nazwy = {str(d["id"]): d["nazwa"]
                 for d in baza.lista_dokumentow(db, sprawa_id)}
        jezyki = baza.jezyki_dokumentow(db, sprawa_id)

        if limit_dokumentow is not None:
            wybrane = sorted(dokumenty)[:limit_dokumentow]
            dokumenty = {k: dokumenty[k] for k in wybrane}

        if czysc_html:
            dokumenty = {k: oczysc_html(v) for k, v in dokumenty.items()}

        # Język sprawy = język przeważający wśród jej dokumentów.
        # Sprawa Lacey ma 397 dokumentów angielskich i 4 polskie;
        # o doborze szablonów pytań decyduje większość.
        licznik: dict[str, int] = {}
        for doc_id in dokumenty:
            j = jezyki.get(doc_id, "nieznany")
            if j in ("pl", "en"):
                licznik[j] = licznik.get(j, 0) + 1
        jezyk = max(licznik, key=licznik.get) if licznik else "pl"

        return Korpus(sprawa_id=sprawa_id, jezyk=jezyk,
                      dokumenty=dokumenty, nazwy=nazwy)
    finally:
        db.close()


def z_plikow(katalog: Path, jezyk: str, sprawa_id: int = 0,
             limit: int | None = None, wzorzec: str = "*.txt") -> Korpus:
    """Wczytuje akta wprost z katalogu — bez bazy, do szybkich prób."""
    pliki = sorted(katalog.glob(wzorzec))
    if limit is not None:
        pliki = pliki[:limit]
    dokumenty = {p.stem: p.read_text(encoding="utf-8", errors="replace")
                 for p in pliki}
    return Korpus(sprawa_id=sprawa_id, jezyk=jezyk, dokumenty=dokumenty,
                  nazwy={p.stem: p.name for p in pliki})
