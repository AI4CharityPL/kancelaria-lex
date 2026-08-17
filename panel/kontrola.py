"""Kontrola niezależna — czyste, jednorazowe zapytanie o prawdziwość.

CO TO JEST I CZYM SIĘ RÓŻNI OD SĘDZIEGO LLM

ADR-0006 odrzucił sędziego LLM i potwierdziło to niezależne badanie
(„LLM-as-a-Judge is Bad", Springer 2026, materiał egzaminu KIO).
Odrzucono tam jednak **sędziego oceniającego wierność w pełnym
kontekście** — model, który widzi to samo, co model oceniany, i po nim
dziedziczy to samo nastawienie. Jeśli wyszukiwarka podsunęła mylące
zdanie, sędzia z tym samym kontekstem uzna je za trafne, bo patrzy
na nie tak samo.

Ten kontroler widzi DWA ZDANIA i nic więcej:

    generator widzi:   pytanie + 12 dokumentów + historia rozmowy
    kontroler widzi:   JEDNO zdanie z akt + JEDNO twierdzenie
                       nie wie, o co pytano
                       nie wie, z jakiej sprawy to jest
                       nie wie, co model odpowiedział wcześniej

Zadanie jest wąskie i zamknięte: czy to zdanie stwierdza tamto zdanie.
To pytanie z czytania ze zrozumieniem, nie z oceny jakości. Model nie
ma się na czym zasugerować, bo nie dostaje niczego poza dwoma zdaniami.

⚠️ GRANICA, ZAPISANA WPROST
   To nadal ten sam model. Izolacja kontekstu usuwa ZASUGEROWANIE,
   nie niekompetencję. Dlatego kontrola modelem jest DRUGĄ warstwą —
   pierwsza (`panel/wsparcie.py`) jest mechaniczna i nie może mylić
   się w ten sposób.

⚠️ AWARIA NIE MOŻE OZNACZAĆ ZGODY
   Gdy model jest niedostępny, werdykt brzmi „nie zweryfikowano",
   nigdy „TAK". Kontrola, która przy awarii cicho przepuszcza, jest
   gorsza od jej braku — daje złudzenie sprawdzenia. Ta sama zasada
   co w bramce izolacji: brak Dockera nie daje wyniku pozytywnego.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

KORZEN = Path(__file__).resolve().parent
sys.path.insert(0, str(KORZEN))

import jezyk as mod_jezyk  # noqa: E402

# Adres modelu z jednego miejsca, walidowany przy imporcie — patrz
# `panel/siec.py`. Wcześniej był tu własny literał.
from siec import ADRES_MODELU as OLLAMA  # noqa: E402

# Kontekst mały, bo zapytanie jest małe — dwa zdania. To dlatego
# kontrola modelem jest tania mimo że jest wywołaniem modelu.
KONTEKST = 2048
TIMEOUT = 120


class Werdykt(str, Enum):
    PRAWDA = "prawda"
    FALSZ = "falsz"
    NIEZWERYFIKOWANE = "niezweryfikowane"


@dataclass(frozen=True)
class Wynik:
    werdykt: Werdykt
    powod: str = ""
    czas_s: float = 0.0

    @property
    def blad(self) -> bool:
        """Czy prawnikowi należy się wyraźny błąd, a nie znacznik."""
        return self.werdykt is Werdykt.FALSZ


# ── zapytanie ───────────────────────────────────────────────────────
#
# Budowane TUTAJ, nie przez `agent.zapytaj_model` — tamten skleja
# instrukcję systemową, historię rozmowy i cały materiał sprawy.
# Przejście przez niego zniszczyłoby jedyną własność, dla której
# ta kontrola istnieje.

SZABLON_PL = """ZDANIE Z DOKUMENTU:
{cytat}

TWIERDZENIE:
{twierdzenie}

Czy powyższe ZDANIE stwierdza to, co mówi TWIERDZENIE?

Odpowiedz wyłącznie w formacie JSON:
{{"odpowiedz": "TAK", "powod": "krótkie uzasadnienie"}}

Odpowiedz TAK tylko wtedy, gdy zdanie faktycznie to stwierdza.
Odpowiedz NIE, gdy zdanie mówi coś innego, coś przeciwnego, albo
gdy twierdzenie dodaje coś, czego w zdaniu nie ma."""

SZABLON_EN = """SENTENCE FROM THE DOCUMENT:
{cytat}

CLAIM:
{twierdzenie}

Does the SENTENCE above state what the CLAIM says?

Answer only in JSON:
{{"odpowiedz": "TAK", "powod": "brief justification"}}

Answer TAK only if the sentence actually states it.
Answer NIE if the sentence says something else, something contrary,
or if the claim adds anything the sentence does not contain."""


SCHEMAT = {
    "type": "object",
    "properties": {
        "odpowiedz": {"type": "string", "enum": ["TAK", "NIE"]},
        "powod": {"type": "string"},
    },
    "required": ["odpowiedz"],
}


def zbuduj_zapytanie(twierdzenie: str, cytaty: list[str],
                     jezyk: str = "pl") -> str:
    """Treść wysyłana do kontrolera. Wydzielona, żeby dała się przetestować.

    Test `test_kontrola.py::test_zapytanie_nie_niesie_kontekstu` sprawdza
    ZAWARTOŚĆ tego ciągu, nie deklarację w dokumentacji.
    """
    szablon = SZABLON_EN if jezyk == "en" else SZABLON_PL
    return szablon.format(
        cytat="\n".join(cytaty),
        twierdzenie=twierdzenie.strip(),
    )


def _wywolaj(zapytanie: str, model: str) -> dict:
    dane = json.dumps({
        "model": model,
        "prompt": zapytanie,
        "stream": False,
        "format": SCHEMAT,
        # Zero, bo to nie jest zadanie twórcze — ma być powtarzalne.
        "options": {"temperature": 0, "num_ctx": KONTEKST},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=dane,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as odp:
        return json.loads(json.loads(odp.read())["response"])


def sprawdz(twierdzenie: str, cytaty: list[str],
            jezyk: str = "pl") -> Wynik:
    """Czy zacytowane zdania stwierdzają to, co twierdzenie.

    `jezyk` dobiera model do języka CYTATU, nie do języka instalacji —
    pomiar z 14.08.2026 pokazał, że model polski na angielskim tekście
    parafrazuje zamiast czytać dosłownie.
    """
    if not twierdzenie.strip() or not cytaty:
        return Wynik(Werdykt.NIEZWERYFIKOWANE, "brak twierdzenia lub cytatu")

    model = mod_jezyk.model_dla(jezyk)
    t0 = time.monotonic()
    try:
        dane = _wywolaj(zbuduj_zapytanie(twierdzenie, cytaty, jezyk), model)
    except urllib.error.URLError as e:
        return Wynik(Werdykt.NIEZWERYFIKOWANE,
                     f"model niedostępny pod {OLLAMA}: {e}",
                     time.monotonic() - t0)
    except Exception as e:                                # noqa: BLE001
        return Wynik(Werdykt.NIEZWERYFIKOWANE,
                     f"{type(e).__name__}: {e}", time.monotonic() - t0)

    czas = time.monotonic() - t0
    odpowiedz = str(dane.get("odpowiedz", "")).strip().upper()
    powod = str(dane.get("powod", "")).strip()[:300]

    if odpowiedz == "TAK":
        return Wynik(Werdykt.PRAWDA, powod, czas)
    if odpowiedz == "NIE":
        return Wynik(Werdykt.FALSZ,
                     powod or "kontroler uznał, że zdanie tego nie stwierdza",
                     czas)
    # Schemat wymusza enum, więc tu nie powinniśmy trafić. Gdyby jednak —
    # nie zgadujemy na korzyść odpowiedzi.
    return Wynik(Werdykt.NIEZWERYFIKOWANE,
                 f"nieoczekiwana odpowiedź kontrolera: {odpowiedz!r}", czas)
