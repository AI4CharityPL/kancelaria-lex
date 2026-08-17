"""Weryfikator cytatów — mechaniczne sprawdzanie pokrycia w źródle.

Kluczowy komponent warstwy agentowej (ADR-0006).

Każde twierdzenie w odpowiedzi agenta niesie identyfikator dokumentu
i zakres znaków. Ten moduł pobiera zakres ze źródła i porównuje tekst.
Twierdzenia bez pokrycia są odrzucane, zanim prawnik je zobaczy.

DLACZEGO NIE SĘDZIA LLM
    Model oceniający wierność odpowiedzi dzieli słabości z modelem
    ocenianym i bywa pobłażliwy dokładnie tam, gdzie ryzyko jest
    największe — przy odpowiedzi sformułowanej pewnie. Porównanie
    ciągów znaków nie ma tej wady.

GRANICA METODY — istotna
    Weryfikacja potwierdza, że cytat POCHODZI ZE ŹRÓDŁA i nie został
    zmyślony. NIE potwierdza, że wniosek wyciągnięty z cytatu jest
    trafny. Model może poprawnie zacytować protokół i błędnie go
    zinterpretować — tego nie wyłapie żadna metoda maszynowa.

    Dlatego weryfikacja przez prawnika pozostaje obowiązkowa,
    a ryzyko RY-20 świadomie pozostaje na poziomie średnim.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


class Werdykt(str, Enum):
    POTWIERDZONY = "potwierdzony"
    ODRZUCONY_BRAK_DOKUMENTU = "odrzucony_brak_dokumentu"
    ODRZUCONY_ZAKRES_POZA_TEKSTEM = "odrzucony_zakres_poza_tekstem"
    ODRZUCONY_TRESC_NIEZGODNA = "odrzucony_tresc_niezgodna"
    ODRZUCONY_BRAK_CYTATU = "odrzucony_brak_cytatu"
    ODRZUCONY_POZA_UPRAWNIENIEM = "odrzucony_poza_uprawnieniem"


@dataclass(frozen=True)
class Cytat:
    """Cytat zadeklarowany przez model."""
    dokument_id: str
    poczatek: int
    koniec: int
    tresc: str


@dataclass
class Twierdzenie:
    """Pojedyncze twierdzenie z odpowiedzi agenta."""
    tekst: str
    cytaty: list[Cytat] = field(default_factory=list)


@dataclass
class WynikWeryfikacji:
    twierdzenie: Twierdzenie
    werdykt: Werdykt
    szczegol: str = ""

    @property
    def przeszlo(self) -> bool:
        return self.werdykt is Werdykt.POTWIERDZONY


# Znaki traktowane jako warianty zapisu tego samego. Roznica w nich nie
# zmienia tresci cytatu, a bierze sie zwykle z konwersji PDF albo edytora.
ZAMIANY = {
    " ": " ",
    "„": '"', "”": '"', "»": '"', "«": '"', "“": '"',
    "’": "'", "‘": "'",
    "–": "-", "—": "-", "−": "-",
}


def normalizuj(tekst: str) -> str:
    """Normalizacja przed porównaniem.

    Dopuszczamy różnice, które nie zmieniają treści: białe znaki,
    formy Unicode, rodzaj cudzysłowu i myślnika. NIE dopuszczamy
    różnic w słowach ani liczbach — w piśmie procesowym "14 dni"
    i "4 dni" to nie jest wariant zapisu.
    """
    tekst = unicodedata.normalize("NFKC", tekst)
    for znak, na in ZAMIANY.items():
        tekst = tekst.replace(znak, na)
    return re.sub(r"\s+", " ", tekst).strip().casefold()


def _mapa_znormalizowana(tekst: str) -> tuple[str, list[int]]:
    """Zwraca (tekst znormalizowany, mapa pozycji do oryginału).

    `mapa[i]` to pozycja w oryginale znaku, który po normalizacji trafił
    na pozycję `i`. Pozwala znaleźć fragment mimo różnic w białych
    znakach, a potem wskazać jego PRAWDZIWY zakres w źródle — bo cytat
    ma prowadzić do miejsca w dokumencie, nie w jego przetworzonej kopii.
    """
    znaki: list[str] = []
    mapa: list[int] = []
    poprzedni_bialy = False

    for i, z in enumerate(tekst):
        if z.isspace():
            if not poprzedni_bialy and znaki:
                znaki.append(" ")
                mapa.append(i)
            poprzedni_bialy = True
            continue
        poprzedni_bialy = False
        z = ZAMIANY.get(z, z)
        znaki.append(z.casefold())
        mapa.append(i)

    while znaki and znaki[-1] == " ":
        znaki.pop()
        mapa.pop()
    return "".join(znaki), mapa


def znajdz_fragment(zrodlo: str, fragment: str) -> tuple[int, int] | None:
    """Znajduje fragment w źródle, tolerując różnice w białych znakach.

    ⚠️ POWÓD ISTNIENIA TEJ FUNKCJI

    Wcześniej offsety wyznaczało zwykłe `zrodlo.find(fragment)`. Przy
    czystym tekście to działa, ale tekst wyciągnięty z PDF-a ma łamania
    wierszy w środku zdań, podwójne spacje i znaki układu strony.
    Model cytuje zdanie tak, jak je czyta — a `find()` nie znajdował
    dokładnego ciągu i cytat przepadał.

    Pomiar z 14.08.2026 na aktach z PDF-ów: 133 ze 147 twierdzeń
    odrzucono z powodem „zakres 0-0", czyli fragment nienaleziony.
    Weryfikator miał tolerancję na białe znaki, ale nigdy nie dostawał
    szansy jej użyć — odsiew następował o krok wcześniej.
    """
    if not fragment or not fragment.strip():
        return None

    # Ścieżka szybka — dokładne trafienie.
    idx = zrodlo.find(fragment)
    if idx >= 0:
        return idx, idx + len(fragment)

    zn_zrodlo, mapa = _mapa_znormalizowana(zrodlo)
    zn_fragment, _ = _mapa_znormalizowana(fragment)
    if not zn_fragment:
        return None

    poz = zn_zrodlo.find(zn_fragment)
    if poz < 0:
        return None

    poczatek = mapa[poz]
    ostatni = mapa[poz + len(zn_fragment) - 1]
    return poczatek, ostatni + 1


class WeryfikatorCytatow:
    """Sprawdza, czy twierdzenia mają pokrycie w dokumentach źródłowych.

    Parameters
    ----------
    dokumenty:
        Mapa {dokument_id: pełny tekst}. Wyłącznie dokumenty, do których
        użytkownik zadający pytanie ma dostęp — zawężenie do uprawnień
        użytkownika, nie systemu (docs/07-agenci.md).
    """

    def __init__(self, dokumenty: dict[str, str]):
        self._dokumenty = dokumenty

    # ── pojedynczy cytat ────────────────────────────────────────────

    def sprawdz_cytat(self, cytat: Cytat) -> tuple[bool, Werdykt, str]:
        zrodlo = self._dokumenty.get(cytat.dokument_id)
        if zrodlo is None:
            return False, Werdykt.ODRZUCONY_BRAK_DOKUMENTU, (
                f"dokument {cytat.dokument_id!r} nie istnieje lub jest poza "
                f"uprawnieniami użytkownika"
            )

        if not (0 <= cytat.poczatek < cytat.koniec <= len(zrodlo)):
            return False, Werdykt.ODRZUCONY_ZAKRES_POZA_TEKSTEM, (
                f"zakres {cytat.poczatek}-{cytat.koniec} poza dokumentem "
                f"o długości {len(zrodlo)}"
            )

        faktyczny = zrodlo[cytat.poczatek:cytat.koniec]
        if normalizuj(faktyczny) != normalizuj(cytat.tresc):
            return False, Werdykt.ODRZUCONY_TRESC_NIEZGODNA, (
                f"pod wskazanym zakresem jest {faktyczny.strip()[:120]!r}, "
                f"model podał {cytat.tresc.strip()[:120]!r}"
            )

        return True, Werdykt.POTWIERDZONY, ""

    # ── twierdzenie ─────────────────────────────────────────────────

    def sprawdz_twierdzenie(self, twierdzenie: Twierdzenie) -> WynikWeryfikacji:
        if not twierdzenie.cytaty:
            return WynikWeryfikacji(
                twierdzenie, Werdykt.ODRZUCONY_BRAK_CYTATU,
                "twierdzenie bez cytatu — brak pokrycia w aktach",
            )

        for cytat in twierdzenie.cytaty:
            ok, werdykt, szczegol = self.sprawdz_cytat(cytat)
            if not ok:
                # Jeden wadliwy cytat przekreśla twierdzenie.
                # Zachowawczo: lepiej odrzucić prawdziwe twierdzenie
                # niż przepuścić zmyślone.
                return WynikWeryfikacji(twierdzenie, werdykt, szczegol)

        return WynikWeryfikacji(twierdzenie, Werdykt.POTWIERDZONY)

    # ── odpowiedź ───────────────────────────────────────────────────

    def sprawdz_odpowiedz(
        self, twierdzenia: list[Twierdzenie]
    ) -> tuple[list[Twierdzenie], list[WynikWeryfikacji]]:
        """Zwraca (twierdzenia potwierdzone, wszystkie wyniki).

        Odrzucone twierdzenia trafiają do logu audytowego jako miara
        jakości modelu w czasie (docs/07-agenci.md).
        """
        wyniki = [self.sprawdz_twierdzenie(t) for t in twierdzenia]
        return [w.twierdzenie for w in wyniki if w.przeszlo], wyniki


def trafnosc_cytatow(wyniki: list[WynikWeryfikacji]) -> float:
    """Metryka J-1 — próg ≥ 99% (docs/11-testy-i-bramki.md)."""
    if not wyniki:
        return 1.0
    return sum(w.przeszlo for w in wyniki) / len(wyniki)
