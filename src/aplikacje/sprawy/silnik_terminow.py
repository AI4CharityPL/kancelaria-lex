"""Deterministyczny silnik terminów procesowych (ADR-0005).

MODEL NIE LICZY TERMINÓW. Model proponuje wyłącznie zdarzenie
inicjujące — to zadanie językowe. Termin wylicza ten moduł, na
sztywnych regułach, testowalnie i audytowalnie.

Uzasadnienie: przeoczony termin oznacza utratę środka zaskarżenia —
szkodę dla klienta, zwykle nieodwracalną, oraz odpowiedzialność
zawodową prawnika. To jedyny obszar systemu, w którym błąd ma
bezpośrednie skutki prawne.

⚠️ REGUŁY WYMAGAJĄ ZATWIERDZENIA PRZEZ PRAWNIKA.
   Reguła bez wypełnionego pola `zatwierdzil` działa w trybie
   "tylko propozycja z ostrzeżeniem" i NIE tworzy terminu wiążącego.
   Katalog w reguly_terminow.yaml jest szkicem, nie źródłem prawa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class SposobLiczenia(str, Enum):
    OD_DNIA_NASTEPNEGO = "od_dnia_nastepnego"
    OD_DNIA_ZDARZENIA = "od_dnia_zdarzenia"


class ObslugaDniWolnych(str, Enum):
    PRZESUN_NA_NASTEPNY_ROBOCZY = "przesun_na_nastepny_roboczy"
    BEZ_PRZESUNIECIA = "bez_przesuniecia"


class StatusTerminu(str, Enum):
    PROPOZYCJA = "propozycja"          # czeka na potwierdzenie prawnika
    POTWIERDZONY = "potwierdzony"      # wiążący
    NIEZATWIERDZONA_REGULA = "niezatwierdzona_regula"  # reguła bez podpisu


@dataclass(frozen=True)
class Regula:
    id: str
    zdarzenie: str
    dlugosc_dni: int
    liczenie: SposobLiczenia
    dni_wolne: ObslugaDniWolnych
    podstawa: str
    zatwierdzil: str | None = None
    data_zatwierdzenia: date | None = None
    uwaga: str = ""

    @property
    def zatwierdzona(self) -> bool:
        return bool(self.zatwierdzil and self.data_zatwierdzenia)


@dataclass(frozen=True)
class ZdarzenieInicjujace:
    """Rozpoznane przez model — z obowiązkowym cytatem ze źródła."""
    rodzaj: str
    data: date
    dokument_id: str
    cytat_poczatek: int
    cytat_koniec: int


@dataclass
class Termin:
    regula_id: str
    zdarzenie: ZdarzenieInicjujace
    data_uplywu: date
    podstawa: str
    status: StatusTerminu
    ostrzezenia: list[str]

    @property
    def wiazacy(self) -> bool:
        return self.status is StatusTerminu.POTWIERDZONY


def wielkanoc(rok: int) -> date:
    """Niedziela wielkanocna w kalendarzu gregoriańskim.

    Algorytm Meeusa/Jonesa/Butchera — czysta arytmetyka, bez tablic
    i bez konieczności aktualizowania czegokolwiek raz do roku.
    """
    a = rok % 19
    b, c = divmod(rok, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7                   # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    miesiac, dzien = divmod(h + l - 7 * m + 114, 31)
    return date(rok, miesiac, dzien + 1)


class KalendarzDniWolnych:
    """Dni ustawowo wolne od pracy.

    ⚠️ ŚWIĘTA RUCHOME SĄ LICZONE, A NIE WPISYWANE — ZMIANA Z 16.08.2026.
    ═══════════════════════════════════════════════════════════════════

    Wcześniej wykaz świąt ruchomych był pustą listą w `reguly_terminow.yaml`
    z komentarzem „DO UZUPEŁNIENIA" i wymogiem corocznej aktualizacji przez
    kancelarię. To najgorsze możliwe rozwiązanie akurat w tym miejscu:

      · Boże Ciało wypada w CZWARTEK — pominięte przesuwa upływ terminu
        o dzień, a przy terminie apelacji dzień to utrata środka
        zaskarżenia;
      · pominięcie jest CICHE. Silnik nie wie, że wykaz jest pusty,
        i podaje datę z pełnym przekonaniem;
      · obowiązek „raz do roku uzupełnić plik" zostanie prędzej czy
        później przeoczony, a skutek ujawni się dopiero przy sprawie.

    Data Wielkanocy jest wyliczalna arytmetycznie, więc wszystkie polskie
    święta ruchome też. Nie ma powodu, żeby ktokolwiek je wpisywał.

    Wpis `swieta_dodatkowe` zostaje dla przypadków szczególnych —
    dni wolnych ogłoszonych ustawą incydentalnie.
    """

    SWIETA_STALE = {
        (1, 1),                 # Nowy Rok
        (1, 6),                 # Trzech Króli
        (5, 1),                 # Święto Pracy
        (5, 3),                 # Święto Konstytucji 3 Maja
        (8, 15),                # Wniebowzięcie NMP / Święto Wojska Polskiego
        (11, 1),                # Wszystkich Świętych
        (11, 11),               # Narodowe Święto Niepodległości
        (12, 25), (12, 26),     # Boże Narodzenie
    }

    # Przesunięcia względem Niedzieli Wielkanocnej. Niedziele są i tak
    # wolne, ale trzymamy je dla czytelności wykazu.
    OD_WIELKANOCY = {
        0: "Wielkanoc",
        1: "Poniedziałek Wielkanocny",
        49: "Zesłanie Ducha Świętego",
        60: "Boże Ciało",
    }

    def __init__(self, swieta_ruchome: set[date] | None = None):
        # Nazwa parametru zachowana dla zgodności — teraz są to święta
        # DODATKOWE, doliczane do wyliczonych.
        self._dodatkowe = swieta_ruchome or set()
        self._zapamietane: dict[int, set[date]] = {}

    def swieta_ruchome(self, rok: int) -> set[date]:
        """Polskie święta ruchome danego roku, wyliczone z daty Wielkanocy."""
        if rok not in self._zapamietane:
            niedziela = wielkanoc(rok)
            self._zapamietane[rok] = {
                niedziela + timedelta(days=przesuniecie)
                for przesuniecie in self.OD_WIELKANOCY
            }
        return self._zapamietane[rok]

    def wolny(self, d: date) -> bool:
        if d.weekday() >= 5:                      # sobota, niedziela
            return True
        if (d.month, d.day) in self.SWIETA_STALE:
            return True
        if d in self.swieta_ruchome(d.year):
            return True
        return d in self._dodatkowe

    def nastepny_roboczy(self, d: date) -> date:
        # Zabezpieczenie przed pętlą przy błędnie skonfigurowanym wykazie.
        for _ in range(30):
            if not self.wolny(d):
                return d
            d += timedelta(days=1)
        raise ValueError(
            "Ponad 30 kolejnych dni wolnych — sprawdź wykaz świąt ruchomych."
        )


class SilnikTerminow:
    def __init__(self, reguly: dict[str, Regula],
                 kalendarz: KalendarzDniWolnych | None = None):
        self._reguly = reguly
        self._kalendarz = kalendarz or KalendarzDniWolnych()

    def reguly_dla(self, rodzaj_zdarzenia: str) -> list[Regula]:
        return [r for r in self._reguly.values() if r.zdarzenie == rodzaj_zdarzenia]

    def oblicz(self, zdarzenie: ZdarzenieInicjujace, regula_id: str) -> Termin:
        regula = self._reguly.get(regula_id)
        if regula is None:
            raise KeyError(f"Nieznana reguła: {regula_id!r}")

        ostrzezenia: list[str] = []

        # Liczenie
        start = zdarzenie.data
        if regula.liczenie is SposobLiczenia.OD_DNIA_NASTEPNEGO:
            start = start + timedelta(days=1)
        uplyw = start + timedelta(days=regula.dlugosc_dni - 1)

        # Dni wolne
        if regula.dni_wolne is ObslugaDniWolnych.PRZESUN_NA_NASTEPNY_ROBOCZY:
            przesuniety = self._kalendarz.nastepny_roboczy(uplyw)
            if przesuniety != uplyw:
                ostrzezenia.append(
                    f"Termin wypadał {uplyw.isoformat()} (dzień wolny); "
                    f"przesunięto na {przesuniety.isoformat()}."
                )
                uplyw = przesuniety

        # Status
        if not regula.zatwierdzona:
            status = StatusTerminu.NIEZATWIERDZONA_REGULA
            ostrzezenia.insert(0, (
                f"⚠️ Reguła {regula.id!r} NIE ZOSTAŁA ZATWIERDZONA przez "
                f"prawnika. Termin ma charakter wyłącznie informacyjny "
                f"i nie jest wiążący."
            ))
        else:
            status = StatusTerminu.PROPOZYCJA
            ostrzezenia.append(
                "Termin wymaga potwierdzenia przez prawnika. "
                "System nie zwalnia z obowiązku sprawdzenia terminu w aktach."
            )

        return Termin(
            regula_id=regula.id,
            zdarzenie=zdarzenie,
            data_uplywu=uplyw,
            podstawa=regula.podstawa,
            status=status,
            ostrzezenia=ostrzezenia,
        )

    @staticmethod
    def potwierdz(termin: Termin, prawnik: str) -> Termin:
        """Potwierdzenie przez prawnika czyni termin wiążącym."""
        if termin.status is StatusTerminu.NIEZATWIERDZONA_REGULA:
            raise ValueError(
                f"Nie można potwierdzić terminu opartego na niezatwierdzonej "
                f"regule {termin.regula_id!r}. Najpierw reguła musi zostać "
                f"zatwierdzona przez prawnika w reguly_terminow.yaml."
            )
        termin.status = StatusTerminu.POTWIERDZONY
        termin.ostrzezenia.append(f"Potwierdzony przez: {prawnik}")
        return termin
