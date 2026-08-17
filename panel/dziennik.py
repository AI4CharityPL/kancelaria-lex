"""Dziennik kontroli — wykrywanie degradacji bez czekania na benchmark.

PO CO

Pełny przebieg benchmarku trwa kilkanaście minut i wymaga korpusu
pomiarowego. Degradacja po zmianie modelu, po aktualizacji Ollamy albo
po zmianie progu bywa natomiast widoczna od razu w rozkładzie stopni
wsparcia: nagły skok udziału „brak" albo werdyktów „falsz" znaczy,
że coś się zmieniło.

Ten dziennik jest odpowiednikiem trace'ów z narzędzi obserwowalności
(Phoenix, LangSmith) — z jedną zasadniczą różnicą, opisaną niżej.

⚠️ DZIENNIK NIE MOŻE STAĆ SIĘ DRUGIM ZBIOREM OBJĘTYM TAJEMNICĄ

Narzędzia obserwowalności zapisują pełne trace'y: pytanie, kontekst,
odpowiedź. Tutaj jest to niedopuszczalne. Wymaganie T-4
(`docs/09-compliance/tajemnica-zawodowa.md`) mówi, że log **rejestruje
dostęp, a nie kopiuje treści** — inaczej sam wymaga tej samej ochrony
co akta, a przy zajęciu sprzętu wydaje wszystko drugi raz.

Dlatego wpis niesie WYŁĄCZNIE liczby i skróty:

    zapisujemy:  czas · sprawa · SKRÓT pytania · liczniki · model
    nie zapisujemy: treści pytania · treści cytatów · treści akt
                    · nazw stron · sygnatur

Sam fakt, o co pytano, bywa informacją o sprawie — stąd skrót, a nie
tekst. Skrót wystarcza, żeby rozpoznać powtórzone pytanie i porównać
zachowanie systemu w czasie, a nie pozwala odtworzyć pytania.

Pilnuje tego `tests/test_dziennik.py`, sprawdzając ZAWARTOŚĆ wpisu,
a nie deklarację w tej dokumentacji.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SCHEMAT = """
CREATE TABLE IF NOT EXISTS dziennik_kontroli (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    czas            TEXT NOT NULL,
    sprawa_id       INTEGER,
    skrot_pytania   TEXT NOT NULL,      -- sha256, NIE treść
    tor             TEXT NOT NULL,      -- 'szybki' | 'analiza'
    twierdzen       INTEGER DEFAULT 0,
    mocne           INTEGER DEFAULT 0,
    slabe           INTEGER DEFAULT 0,
    brak            INTEGER DEFAULT 0,
    kontrola_falsz  INTEGER DEFAULT 0,
    kontrola_brak   INTEGER DEFAULT 0,  -- niezweryfikowane
    srednie_pokrycie REAL DEFAULT 0.0,
    model           TEXT DEFAULT '',
    czas_ms         INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_dziennik_czas ON dziennik_kontroli(czas);
"""

# Ile dni wpisów trzymamy. Dziennik ma służyć wykrywaniu degradacji,
# a nie archiwizacji — nieograniczony rósłby bez powodu.
RETENCJA_DNI = 90


@dataclass(frozen=True)
class Wpis:
    sprawa_id: int | None
    tor: str
    twierdzen: int = 0
    mocne: int = 0
    slabe: int = 0
    brak: int = 0
    kontrola_falsz: int = 0
    kontrola_brak: int = 0
    srednie_pokrycie: float = 0.0
    model: str = ""
    czas_ms: int = 0


def przygotuj(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMAT)
    db.commit()


def skrot(pytanie: str) -> str:
    """Skrót pytania — rozpoznaje powtórzenie, nie pozwala odtworzyć treści."""
    return hashlib.sha256(pytanie.strip().casefold().encode("utf-8")).hexdigest()[:16]


def zapisz(db: sqlite3.Connection, pytanie: str, wpis: Wpis) -> int:
    """Zapisuje wpis. `pytanie` jest natychmiast zamieniane na skrót.

    Parametr nazywa się `pytanie`, a nie `skrot_pytania`, celowo:
    zamiana ma być zrobiona TUTAJ, w jednym miejscu. Gdyby przyjmował
    gotowy skrót, prędzej czy później ktoś przekazałby tekst.
    """
    przygotuj(db)
    kursor = db.execute(
        "INSERT INTO dziennik_kontroli (czas, sprawa_id, skrot_pytania, tor, "
        "twierdzen, mocne, slabe, brak, kontrola_falsz, kontrola_brak, "
        "srednie_pokrycie, model, czas_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"),
         wpis.sprawa_id, skrot(pytanie), wpis.tor, wpis.twierdzen,
         wpis.mocne, wpis.slabe, wpis.brak, wpis.kontrola_falsz,
         wpis.kontrola_brak, round(wpis.srednie_pokrycie, 3),
         wpis.model, wpis.czas_ms),
    )
    db.commit()
    return kursor.lastrowid


def z_odpowiedzi(odpowiedz: dict, sprawa_id: int | None, tor: str,
                 model: str = "", czas_ms: int = 0) -> Wpis:
    """Buduje wpis z odpowiedzi panelu — bez sięgania do treści."""
    cytaty = odpowiedz.get("cytaty") or []
    odrzucone = odpowiedz.get("odrzucone") or []

    stopnie = [c.get("stopien") for c in cytaty]
    pokrycia = [c.get("pokrycie", 0.0) for c in cytaty
                if isinstance(c.get("pokrycie"), (int, float))]

    return Wpis(
        sprawa_id=sprawa_id,
        tor=tor,
        twierdzen=len(cytaty) + len(odrzucone),
        mocne=sum(1 for s in stopnie if s == "mocne"),
        slabe=sum(1 for s in stopnie if s == "slabe"),
        brak=sum(1 for o in odrzucone
                 if o.get("powod") == "odrzucony_brak_wsparcia_w_cytacie"),
        kontrola_falsz=sum(1 for o in odrzucone
                           if o.get("powod") == "odrzucony_kontrola_niezalezna"),
        kontrola_brak=sum(1 for c in cytaty
                          if c.get("kontrola") == "niezweryfikowane"),
        srednie_pokrycie=sum(pokrycia) / len(pokrycia) if pokrycia else 0.0,
        model=model,
        czas_ms=czas_ms,
    )


def zbiorczo(db: sqlite3.Connection, dni: int = 7) -> dict:
    """Rozkład z ostatnich `dni` — do wykrycia degradacji.

    Skok udziału „brak" albo „falsz" po zmianie modelu jest widoczny
    tutaj od razu, bez czekania na pełny przebieg benchmarku.
    """
    przygotuj(db)
    od = (datetime.now(timezone.utc) - timedelta(days=dni)).isoformat(timespec="seconds")
    w = db.execute(
        "SELECT COUNT(*) n, COALESCE(SUM(twierdzen),0) tw, "
        "COALESCE(SUM(mocne),0) m, COALESCE(SUM(slabe),0) s, "
        "COALESCE(SUM(brak),0) b, COALESCE(SUM(kontrola_falsz),0) kf, "
        "COALESCE(SUM(kontrola_brak),0) kb, "
        "COALESCE(AVG(srednie_pokrycie),0) sp, COALESCE(AVG(czas_ms),0) cms "
        "FROM dziennik_kontroli WHERE czas >= ?", (od,)).fetchone()

    tw = w["tw"] or 0
    return {
        "dni": dni,
        "zapytan": w["n"],
        "twierdzen": tw,
        "mocne": w["m"], "slabe": w["s"], "brak": w["b"],
        "kontrola_falsz": w["kf"], "kontrola_niezweryfikowane": w["kb"],
        "udzial_brak": round((w["b"] or 0) / tw, 3) if tw else 0.0,
        "udzial_falsz": round((w["kf"] or 0) / tw, 3) if tw else 0.0,
        "srednie_pokrycie": round(w["sp"] or 0.0, 3),
        "sredni_czas_ms": int(w["cms"] or 0),
    }


def ostatnie(db: sqlite3.Connection, limit: int = 50) -> list[dict]:
    przygotuj(db)
    return [dict(w) for w in db.execute(
        "SELECT * FROM dziennik_kontroli ORDER BY id DESC LIMIT ?", (limit,))]


def posprzataj(db: sqlite3.Connection, dni: int = RETENCJA_DNI) -> int:
    """Usuwa wpisy starsze niż `dni`. Zwraca liczbę usuniętych."""
    przygotuj(db)
    prog = (datetime.now(timezone.utc) - timedelta(days=dni)).isoformat(timespec="seconds")
    kursor = db.execute("DELETE FROM dziennik_kontroli WHERE czas < ?", (prog,))
    db.commit()
    return kursor.rowcount
