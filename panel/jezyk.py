"""Automatyczne rozpoznanie języka dokumentu — polski czy angielski.

DLACZEGO NIE MODELEM JĘZYKOWYM

Rozpoznanie języka to zadanie rozstrzygnięte i deterministyczne. Model
kosztowałby sekundy na dokument (przy 400 dokumentach — kilkanaście
minut), zajmował VRAM i bywał niepewny. Tutaj liczenie słów funkcyjnych
i znaków diakrytycznych daje odpowiedź w mikrosekundach, zawsze tak
samo, bez GPU.

To ta sama zasada, co przy terminach procesowych (ADR-0005): tam, gdzie
wystarczy reguła, model jest gorszym narzędziem — wolniejszym i mniej
przewidywalnym.

Dla przypadków granicznych (dokument bardzo krótki albo mieszany)
funkcja zwraca `nieznany` wraz z pewnością, a decyzję podejmuje warstwa
wyżej — może zapytać model albo poprosić człowieka.

WYNIK STEROWUJE DOBOREM MODELU
    polski     → bielik-lex-map   (Bielik, trenowany pod polski)
    angielski  → llama-lex-map    (Llama 3.1, ścisłe trzymanie schematu)

Pomiar z 14.08.2026 pokazał, że pomyłka tutaj jest kosztowna: model
polski na angielskich aktach parafrazował zamiast cytować dosłownie
i weryfikator odrzucił 62 z 68 twierdzeń.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Znaki występujące w polskim, a nieobecne w angielskim.
DIAKRYTYKI_PL = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")

# Słowa funkcyjne — najczęstsze i praktycznie niewymienne między językami.
FUNKCYJNE_PL = frozenset("""
i w z na do nie że się to jest o od po za nad pod przez oraz lub albo
ale gdy jak który która które których był była było były będzie są
sąd sądu wyrok oskarżony obrońca postanowienie sprawy sprawie art
""".split())

FUNKCYJNE_EN = frozenset("""
the of and to in that is was for on with as by at from this it be are
were has have not or but which their they defendant court order motion
plaintiff pursuant hereby shall filed against united states
""".split())

TOKEN = re.compile(r"[a-ząćęłńóśźż]+", re.IGNORECASE)

PROG_PEWNOSCI = 0.55
MIN_TOKENOW = 12


@dataclass(frozen=True)
class Rozpoznanie:
    jezyk: str          # "pl" | "en" | "nieznany"
    pewnosc: float      # 0.0–1.0
    powod: str

    @property
    def pewne(self) -> bool:
        return self.jezyk in ("pl", "en") and self.pewnosc >= PROG_PEWNOSCI


def rozpoznaj(tekst: str, probka: int = 20_000) -> Rozpoznanie:
    """Rozpoznaje język na podstawie próbki tekstu.

    Próbka zamiast całości: przy dokumencie na 200 stron pierwsze
    20 tys. znaków rozstrzyga tak samo, a jest 30× tańsze.
    """
    if not tekst or not tekst.strip():
        return Rozpoznanie("nieznany", 0.0, "pusty dokument")

    fragment = tekst[:probka]
    tokeny = [t.casefold() for t in TOKEN.findall(fragment)]
    if len(tokeny) < MIN_TOKENOW:
        return Rozpoznanie("nieznany", 0.0,
                           f"za mało tekstu ({len(tokeny)} słów)")

    # Sygnał 1 — znaki diakrytyczne. Ich obecność jest niemal
    # rozstrzygająca; ich brak nie dowodzi niczego (polski tekst bywa
    # pisany bez ogonków).
    diakrytykow = sum(1 for z in fragment if z in DIAKRYTYKI_PL)
    udzial_diakrytykow = diakrytykow / max(len(fragment), 1)

    # Sygnał 2 — słowa funkcyjne.
    pl = sum(1 for t in tokeny if t in FUNKCYJNE_PL)
    en = sum(1 for t in tokeny if t in FUNKCYJNE_EN)
    razem = pl + en

    if razem == 0 and udzial_diakrytykow < 0.001:
        return Rozpoznanie("nieznany", 0.0,
                           "brak słów funkcyjnych i znaków diakrytycznych")

    udzial_pl = pl / razem if razem else 0.0
    udzial_en = en / razem if razem else 0.0

    # Diakrytyki dokładają do polskiego, proporcjonalnie do nasycenia.
    # 1,5% znaków z ogonkami to typowy polski tekst.
    bonus = min(udzial_diakrytykow / 0.015, 1.0) * 0.45
    wynik_pl = min(udzial_pl + bonus, 1.0)
    wynik_en = udzial_en * (1.0 - bonus)

    if wynik_pl > wynik_en:
        jezyk, pewnosc = "pl", wynik_pl / max(wynik_pl + wynik_en, 1e-9)
    else:
        jezyk, pewnosc = "en", wynik_en / max(wynik_pl + wynik_en, 1e-9)

    powod = (f"słowa funkcyjne pl={pl} en={en}, "
             f"znaki diakrytyczne {udzial_diakrytykow:.2%}")

    if pewnosc < PROG_PEWNOSCI:
        return Rozpoznanie("nieznany", pewnosc, f"niejednoznaczne — {powod}")
    return Rozpoznanie(jezyk, pewnosc, powod)


# ── dobór modelu ────────────────────────────────────────────────────

MODELE = {
    "pl": "bielik-lex-map",       # Bielik-minitron-7B — trenowany pod polski
    "en": "llama-lex-map",        # Llama 3.1 8B — ścisłe trzymanie schematu
}

MODEL_ZAPASOWY = "bielik-lex-map"


def model_dla(jezyk: str) -> str:
    """Model mapowania właściwy dla języka dokumentu."""
    return MODELE.get(jezyk, MODEL_ZAPASOWY)


def pogrupuj_wg_jezyka(dokumenty: dict[str, str],
                       jezyki: dict[str, str] | None = None
                       ) -> dict[str, list[str]]:
    """Grupuje identyfikatory dokumentów według języka.

    ⚠️ Grupowanie nie jest kosmetyką. Przy 8 GB VRAM mieści się JEDEN
    model naraz, więc każda zmiana języka to wyładowanie i wczytanie
    modelu (kilkanaście sekund). Przetworzenie najpierw wszystkich
    polskich, potem wszystkich angielskich, ogranicza to do jednej
    zamiany zamiast kilkunastu.
    """
    grupy: dict[str, list[str]] = {}
    for doc_id, tresc in dokumenty.items():
        j = (jezyki or {}).get(doc_id) or rozpoznaj(tresc).jezyk
        if j == "nieznany":
            j = "pl"          # zapasowo polski — instalacja jest w PL
        grupy.setdefault(j, []).append(doc_id)
    return grupy
