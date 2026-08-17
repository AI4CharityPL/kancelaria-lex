"""Korpus przepisów prawnych — odrębna przestrzeń wobec akt spraw.

DLACZEGO OSOBNO, A NIE JAKO DOKUMENTY SPRAWY

  1. Przepisy są jawne. Akta spraw karnych nie są. Trzymanie ich w tej
     samej tabeli mieszałoby materiał objęty tajemnicą zawodową z tekstem,
     który każdy może pobrać z dziennika ustaw.

  2. Przepisy są WSPÓLNE dla wszystkich spraw. Kopiowanie kodeksu do
     każdej sprawy z osobna byłoby absurdem — i zaraz potem ktoś by
     zapytał, czemu "dokumenty sprawy" puchną do tysiąca pozycji.

  3. NAJWAŻNIEJSZE — rozdzielenie przestrzeni cytatów.
     Ustalenie faktyczne cytuje AKTA. Podstawa prawna cytuje PRZEPIS.
     Gdyby oba żyły w jednym zbiorze, model mógłby "potwierdzić"
     zdanie o prawie protokołem przesłuchania, a weryfikator by to
     przepuścił — bo cytat formalnie istniałby w zbiorze.

     Rozdzielenie sprawia, że taka pomyłka jest niemożliwa
     konstrukcyjnie: weryfikator ustaleń nie widzi przepisów,
     a weryfikator podstawy prawnej nie widzi akt.

⚠️ TREŚCI PRZEPISÓW WPROWADZA KANCELARIA.
   Moduł nie zawiera żadnego tekstu ustawy — celowo. System, którego
   zadaniem jest zwalczanie halucynacji, nie może sam startować
   z przepisami odtworzonymi z pamięci modelu. Teksty wkleja się
   z oficjalnego źródła, a pole `zrodlo` służy do odnotowania, skąd.
"""

from __future__ import annotations

from datetime import datetime, timezone

SCHEMAT = """
CREATE TABLE IF NOT EXISTS przepisy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    akt         TEXT NOT NULL,          -- np. "Kodeks postępowania karnego"
    jednostka   TEXT NOT NULL,          -- np. "art. 445 § 1"
    tresc       TEXT NOT NULL,
    zrodlo      TEXT DEFAULT '',        -- skąd pochodzi tekst
    zweryfikowal TEXT DEFAULT '',
    dodano      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_przepis_akt ON przepisy(akt);
"""


def _teraz() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def przygotuj(db) -> None:
    db.executescript(SCHEMAT)
    db.commit()


def dodaj(db, akt: str, jednostka: str, tresc: str,
          zrodlo: str = "", zweryfikowal: str = "") -> int:
    if not akt.strip() or not jednostka.strip() or not tresc.strip():
        raise ValueError("Akt, jednostka i treść są wymagane.")
    kursor = db.execute(
        "INSERT INTO przepisy (akt, jednostka, tresc, zrodlo, zweryfikowal, "
        "dodano) VALUES (?,?,?,?,?,?)",
        (akt.strip(), jednostka.strip(), tresc.strip(),
         zrodlo.strip(), zweryfikowal.strip(), _teraz()),
    )
    db.commit()
    return kursor.lastrowid


def lista(db) -> list[dict]:
    wiersze = db.execute(
        "SELECT id, akt, jednostka, LENGTH(tresc) AS dlugosc, zrodlo, "
        "zweryfikowal, dodano FROM przepisy ORDER BY akt, id"
    ).fetchall()
    return [dict(w) for w in wiersze]


def pobierz(db, przepis_id: int) -> dict | None:
    w = db.execute("SELECT * FROM przepisy WHERE id = ?",
                   (przepis_id,)).fetchone()
    return dict(w) if w else None


def usun(db, przepis_id: int) -> bool:
    kursor = db.execute("DELETE FROM przepisy WHERE id = ?", (przepis_id,))
    db.commit()
    return bool(kursor.rowcount)


def tresci(db, wybrane_id: list[int] | None = None) -> dict[str, str]:
    """Mapa {id_przepisu: treść} — wejście dla analizy.

    Zwraca WYŁĄCZNIE przepisy. Nigdy nie miesza się z akta­mi sprawy:
    analiza dostaje ten słownik osobnym parametrem i weryfikuje wobec
    niego wyłącznie podstawę prawną.
    """
    if wybrane_id:
        znaki = ",".join("?" * len(wybrane_id))
        wiersze = db.execute(
            f"SELECT id, tresc FROM przepisy WHERE id IN ({znaki})",
            wybrane_id,
        ).fetchall()
    else:
        wiersze = db.execute("SELECT id, tresc FROM przepisy").fetchall()
    return {str(w["id"]): w["tresc"] for w in wiersze}


def nazwy(db, wybrane_id: list[int] | None = None) -> dict[str, str]:
    """Etykiety do wyświetlenia przy cytacie, np. 'k.p.k. art. 445 § 1'."""
    if wybrane_id:
        znaki = ",".join("?" * len(wybrane_id))
        wiersze = db.execute(
            f"SELECT id, akt, jednostka FROM przepisy WHERE id IN ({znaki})",
            wybrane_id,
        ).fetchall()
    else:
        wiersze = db.execute("SELECT id, akt, jednostka FROM przepisy").fetchall()
    return {str(w["id"]): f"{w['akt']} {w['jednostka']}" for w in wiersze}
