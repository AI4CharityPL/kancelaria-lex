"""Terminy procesowe w panelu — most do silnika z ADR-0005.

════════════════════════════════════════════════════════════════════════
 PO CO TEN MODUŁ
════════════════════════════════════════════════════════════════════════

`src/aplikacje/sprawy/silnik_terminow.py` był napisany, otestowany
i NIEOSIĄGALNY z panelu. Deterministyczne liczenie terminów procesowych
to jedyna funkcja tego systemu, w której błąd ma bezpośredni skutek
prawny — przeoczony termin oznacza utratę środka zaskarżenia — a przy
tym jedyna, w której model nie bierze udziału w liczeniu.

════════════════════════════════════════════════════════════════════════
 DLACZEGO WŁASNY ODCZYT YAML-A
════════════════════════════════════════════════════════════════════════

ADR-0005 wymaga, żeby reguły były DANYMI, a nie kodem — po to, żeby
prawnik mógł je przejrzeć i wziąć za nie odpowiedzialność, nie czytając
Pythona. YAML czyta się w tym celu lepiej niż JSON.

PyYAML byłby jednak nową zależnością w systemie, którego łańcuch dostaw
jest pusty (art. 21 ust. 2 lit. d ustawy o KSC) — i to zależnością
z historią podatności na wykonanie kodu przy wczytywaniu. Odczyt jest
tu ściśle ograniczony do kształtu `reguly_terminow.yaml`.

⚠️ PARSER JEST CELOWO NIEUSTĘPLIWY.
   Każde odstępstwo od oczekiwanego kształtu podnosi wyjątek zamiast
   zgadywać. Reguła wczytana błędnie jest groźniejsza od reguły
   niewczytanej: druga jest widoczna, pierwsza podaje złą datę
   z pełnym przekonaniem.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "src" / "aplikacje"))

from sprawy.silnik_terminow import (  # noqa: E402
    KalendarzDniWolnych, ObslugaDniWolnych, Regula, SilnikTerminow,
    SposobLiczenia, StatusTerminu, ZdarzenieInicjujace,
)

SCIEZKA_REGUL = KORZEN / "src" / "aplikacje" / "sprawy" / "reguly_terminow.yaml"


class BladRegul(ValueError):
    """Reguł nie da się wczytać — do pokazania wprost, nie do ukrycia."""


# ── odczyt YAML-a (podzbiór) ─────────────────────────────────────────

def _wartosc(surowa: str):
    """Skalar YAML-a sprowadzony do typu Pythona."""
    surowa = surowa.strip()
    if surowa in ("null", "~", ""):
        return None
    if surowa in ("true", "false"):
        return surowa == "true"
    if len(surowa) >= 2 and surowa[0] == surowa[-1] and surowa[0] in "\"'":
        return surowa[1:-1]
    if surowa.lstrip("-").isdigit():
        return int(surowa)
    return surowa


def _czysta(linia: str) -> str:
    """Linia bez komentarza. Znak `#` w cudzysłowie nie jest komentarzem."""
    wynik, cudzyslow = [], ""
    for znak in linia:
        if cudzyslow:
            if znak == cudzyslow:
                cudzyslow = ""
        elif znak in "\"'":
            cudzyslow = znak
        elif znak == "#":
            break
        wynik.append(znak)
    return "".join(wynik).rstrip()


def czytaj_reguly(sciezka: Path | None = None) -> list[dict]:
    """Lista słowników reguł z pliku YAML.

    Obsługiwany kształt to dokładnie ten z `reguly_terminow.yaml`:
    klucz `reguly:` z listą wpisów `- klucz: wartość`, w tym blokami
    zwijanymi `>` dla pola `uwaga`.
    """
    sciezka = sciezka or SCIEZKA_REGUL
    if not sciezka.exists():
        raise BladRegul(f"Brak pliku reguł: {sciezka}")

    reguly: list[dict] = []
    biezaca: dict | None = None
    w_regulach = False
    klucz_bloku: str | None = None
    wciecie_bloku = 0
    blok: list[str] = []

    for numer, surowa in enumerate(
            sciezka.read_text(encoding="utf-8").splitlines(), start=1):
        linia = _czysta(surowa)

        # Blok zwijany — trwa, dopóki wcięcie jest większe niż nagłówka.
        if klucz_bloku is not None:
            wciecie = len(surowa) - len(surowa.lstrip())
            if surowa.strip() and wciecie > wciecie_bloku:
                blok.append(surowa.strip())
                continue
            if biezaca is not None:
                biezaca[klucz_bloku] = " ".join(blok)
            klucz_bloku, blok = None, []

        if not linia.strip():
            continue

        if linia.startswith("reguly:"):
            w_regulach = True
            continue
        if not linia.startswith((" ", "\t")) and linia.endswith(":"):
            w_regulach = False           # inna sekcja, np. swieta_ruchome
            continue
        if not w_regulach:
            continue

        obcieta = linia.strip()
        if obcieta.startswith("- "):
            if biezaca:
                reguly.append(biezaca)
            biezaca = {}
            obcieta = obcieta[2:]

        if biezaca is None or ":" not in obcieta:
            continue

        klucz, _, reszta = obcieta.partition(":")
        klucz, reszta = klucz.strip(), reszta.strip()

        if reszta in (">", "|", ">-", "|-"):
            klucz_bloku = klucz
            wciecie_bloku = len(linia) - len(linia.lstrip())
            blok = []
            continue

        biezaca[klucz] = _wartosc(reszta)

    if klucz_bloku is not None and biezaca is not None:
        biezaca[klucz_bloku] = " ".join(blok)
    if biezaca:
        reguly.append(biezaca)

    if not reguly:
        raise BladRegul(
            f"Plik {sciezka.name} nie zawiera żadnej reguły. Terminy nie "
            f"będą liczone — to nie jest stan poprawny.")
    return reguly


# ── budowa silnika ───────────────────────────────────────────────────

WYMAGANE_POLA = ("id", "zdarzenie", "dlugosc_dni", "liczenie",
                 "dni_wolne", "podstawa")


def zbuduj_silnik(sciezka: Path | None = None) -> SilnikTerminow:
    reguly: dict[str, Regula] = {}

    for wpis in czytaj_reguly(sciezka):
        brakujace = [p for p in WYMAGANE_POLA if wpis.get(p) in (None, "")]
        if brakujace:
            raise BladRegul(
                f"Reguła {wpis.get('id', '?')!r} nie ma pól: "
                f"{', '.join(brakujace)}. Reguła niepełna nie jest wczytywana, "
                f"bo termin policzony z niekompletnej reguły wygląda tak samo "
                f"jak policzony poprawnie.")

        try:
            liczenie = SposobLiczenia(wpis["liczenie"])
            dni_wolne = ObslugaDniWolnych(wpis["dni_wolne"])
        except ValueError as e:
            raise BladRegul(
                f"Reguła {wpis['id']!r} ma nieznaną wartość: {e}") from e

        zatwierdzenie = wpis.get("data_zatwierdzenia")
        if isinstance(zatwierdzenie, str):
            try:
                zatwierdzenie = date.fromisoformat(zatwierdzenie)
            except ValueError as e:
                raise BladRegul(
                    f"Reguła {wpis['id']!r}: data zatwierdzenia "
                    f"{zatwierdzenie!r} nie jest datą ISO.") from e

        reguly[wpis["id"]] = Regula(
            id=wpis["id"],
            zdarzenie=wpis["zdarzenie"],
            dlugosc_dni=int(wpis["dlugosc_dni"]),
            liczenie=liczenie,
            dni_wolne=dni_wolne,
            podstawa=wpis["podstawa"],
            zatwierdzil=wpis.get("zatwierdzil"),
            data_zatwierdzenia=zatwierdzenie,
            uwaga=wpis.get("uwaga") or "",
        )

    return SilnikTerminow(reguly, KalendarzDniWolnych())


# ── warstwa dla panelu ───────────────────────────────────────────────

def katalog() -> list[dict]:
    """Reguły do pokazania w interfejsie, z jawnym stanem zatwierdzenia."""
    silnik = zbuduj_silnik()
    return sorted(
        ({
            "id": r.id,
            "zdarzenie": r.zdarzenie,
            "dlugosc_dni": r.dlugosc_dni,
            "podstawa": r.podstawa,
            "zatwierdzona": r.zatwierdzona,
            "zatwierdzil": r.zatwierdzil or "",
            "uwaga": r.uwaga,
        } for r in silnik._reguly.values()),
        key=lambda r: (not r["zatwierdzona"], r["id"]))


def policz(regula_id: str, data_zdarzenia: str,
           dokument_id: str = "", poczatek: int = 0, koniec: int = 0) -> dict:
    """Termin dla reguły i daty zdarzenia.

    ⚠️ Model nie bierze udziału w liczeniu (ADR-0005). Podaje najwyżej
    zdarzenie inicjujące — datę wpisuje albo potwierdza prawnik.
    """
    try:
        dzien = date.fromisoformat(data_zdarzenia)
    except (TypeError, ValueError) as e:
        raise BladRegul(
            f"Data zdarzenia {data_zdarzenia!r} nie jest datą w formacie "
            f"RRRR-MM-DD.") from e

    silnik = zbuduj_silnik()
    if regula_id not in silnik._reguly:
        raise BladRegul(f"Nieznana reguła: {regula_id!r}")

    regula = silnik._reguly[regula_id]
    termin = silnik.oblicz(
        ZdarzenieInicjujace(
            rodzaj=regula.zdarzenie, data=dzien,
            dokument_id=str(dokument_id),
            cytat_poczatek=int(poczatek), cytat_koniec=int(koniec)),
        regula_id)

    return {
        "regula_id": termin.regula_id,
        "zdarzenie": regula.zdarzenie,
        "data_zdarzenia": dzien.isoformat(),
        "data_uplywu": termin.data_uplywu.isoformat(),
        "dni": regula.dlugosc_dni,
        "podstawa": termin.podstawa,
        "status": termin.status.value,
        "wiazacy": termin.status is StatusTerminu.POTWIERDZONY,
        "ostrzezenia": termin.ostrzezenia,
        "dokument_id": str(dokument_id) or None,
    }
