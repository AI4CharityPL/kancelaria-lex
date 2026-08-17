"""Warstwa danych panelu — SQLite, z zamknięciem w obrębie sprawy.

ZASADA NACZELNA TEGO MODUŁU:
    Nie istnieje funkcja, która zwraca dokumenty lub wiadomości
    bez podania `sprawa_id`.

To nie jest konwencja ani dobra praktyka — to jedyna droga dostępu.
Zapytanie o dokumenty zawsze niesie identyfikator sprawy w klauzuli
WHERE, więc wyciek między sprawami wymagałby zmiany kodu, a nie
pomyłki w wywołaniu.

Wynika to wprost z wymagań F-30 (zasada wiedzy koniecznej) i F-32
(ściany etyczne) — docs/02-wymagania.md.

Celowo używamy wyłącznie biblioteki standardowej: żadnych nowych
zależności, których trzeba by pilnować w łańcuchu dostaw (art. 21
ust. 2 lit. d ustawy o KSC).
"""

from __future__ import annotations

import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

KORZEN = Path(__file__).resolve().parent
SCIEZKA_BAZY = KORZEN / "dane" / "panel.sqlite3"

SCHEMAT = """
CREATE TABLE IF NOT EXISTS sprawy (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sygnatura       TEXT NOT NULL,
    nazwa           TEXT NOT NULL,
    organ           TEXT DEFAULT '',
    rodzaj          TEXT DEFAULT 'karna',
    etap            TEXT DEFAULT 'postępowanie przygotowawcze',
    prowadzacy      TEXT DEFAULT '',
    poufnosc        TEXT DEFAULT 'standardowa',
    utworzono       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dokumenty (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sprawa_id       INTEGER NOT NULL REFERENCES sprawy(id) ON DELETE CASCADE,
    nazwa           TEXT NOT NULL,
    rodzaj          TEXT DEFAULT 'pismo',
    tresc           TEXT NOT NULL,
    jezyk           TEXT DEFAULT '',        -- 'pl' | 'en' | 'nieznany'
    jezyk_pewnosc   REAL DEFAULT 0.0,
    dodano          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dok_sprawa ON dokumenty(sprawa_id);
-- Indeks na `jezyk` zakładany dopiero w _domiguj(): przy bazie założonej
-- starszym schematem kolumny jeszcze nie ma, a CREATE INDEX w tym miejscu
-- wywracałby cały start panelu.

CREATE TABLE IF NOT EXISTS wiadomosci (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sprawa_id       INTEGER NOT NULL REFERENCES sprawy(id) ON DELETE CASCADE,
    dokument_id     INTEGER REFERENCES dokumenty(id) ON DELETE CASCADE,
    rola            TEXT NOT NULL,          -- 'uzytkownik' | 'asystent'
    tresc           TEXT NOT NULL,
    cytaty_json     TEXT DEFAULT '[]',
    odrzucone_json  TEXT DEFAULT '[]',
    utworzono       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wiad_sprawa ON wiadomosci(sprawa_id);

CREATE TABLE IF NOT EXISTS audyt (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    czas            TEXT NOT NULL,
    sprawa_id       INTEGER,
    operacja        TEXT NOT NULL,
    szczegol        TEXT DEFAULT '',
    poprzedni_hash  TEXT DEFAULT '',
    hash            TEXT NOT NULL
);

-- ── profile i sesje ────────────────────────────────────────────────
--
-- Do 16.08.2026 warstwa profili istniała WYŁĄCZNIE w przeglądarce:
-- ekran logowania zapisywał imię i rolę do `localStorage` i się chował.
-- Nie było tabeli użytkowników, hasła ani sesji, a `wiadomosci` nie
-- miały kolumny osoby — więc dwie osoby pracujące na jednej sprawie
-- dzieliły jedną historię, bez śladu, kto o co pytał.
--
-- Hasło trzymamy jako skrót `scrypt` z solą per profil. Bez zależności
-- zewnętrznych: `hashlib.scrypt` jest w bibliotece standardowej
-- (art. 21 ust. 2 lit. d — pusty łańcuch dostaw).
CREATE TABLE IF NOT EXISTS profile (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    login              TEXT NOT NULL UNIQUE COLLATE NOCASE,
    imie               TEXT NOT NULL,
    nazwisko           TEXT NOT NULL,
    rola               TEXT NOT NULL,   -- 'prawnik' | 'sekretariat' | 'aplikant'
    skrot              BLOB NOT NULL,
    sol                BLOB NOT NULL,
    utworzono          TEXT NOT NULL,
    ostatnie_logowanie TEXT DEFAULT '',
    -- Ślad przyjęcia oświadczeń o obowiązkach ciążących na kancelarii.
    -- Wersja, a nie samo „tak": bez niej nie wiadomo, CO ta osoba widziała.
    zgody_wersja       TEXT DEFAULT '',
    zgody_czas         TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sesje (
    token       TEXT PRIMARY KEY,
    profil_id   INTEGER NOT NULL REFERENCES profile(id) ON DELETE CASCADE,
    utworzono   TEXT NOT NULL,
    wygasa      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sesje_profil ON sesje(profil_id);

-- ── nieudane próby logowania ──────────────────────────────────────
--
-- ⚠️ SCRYPT SPOWALNIA POJEDYNCZĄ PRÓBĘ, NIE POWSTRZYMUJE SERII.
--
-- Skrót hasła kosztuje ułamek sekundy, co czyni atak słownikowy na
-- SKRADZIONEJ BAZIE kosztownym. Nie robi natomiast nic przeciwko
-- zgadywaniu hasła PRZEZ PANEL: kilkanaście prób na sekundę, bez końca
-- i bez śladu poza logiem audytowym.
--
-- Przy systemie trzymającym akta spraw karnych to nie jest niuans.
-- Napastnik z dostępem do maszyny lub do sieci kancelarii (gdy panel
-- stanie za reverse proxy) dostaje nieograniczoną liczbę prób.
--
-- Klucz to LOGIN, także nieistniejący. Blokowanie wyłącznie loginów
-- istniejących zamieniłoby tę tabelę w wyrocznię: „ten się blokuje,
-- więc konto istnieje" — czyli dokładnie to ujawnienie, któremu
-- `uwierzytelnij` zapobiega, licząc skrót nawet przy braku profilu.
-- ── drugi składnik uwierzytelniania (TOTP) ────────────────────────
--
-- Art. 21 ust. 2 lit. j dyrektywy 2022/2555 mówi o uwierzytelnianiu
-- WIELOSKŁADNIKOWYM. Sekret TOTP jest wspólny dla panelu i aplikacji
-- w telefonie; nic między nimi nie wędruje, więc drugi składnik nie
-- łamie zasady „nic nie wychodzi poza urządzenie".
--
-- ⚠️ Kody zapasowe leżą tu jako SKRÓTY, nie kody. Baza wykradziona
--    razem z sekretem TOTP daje wtedy drugi składnik, ale nie daje
--    drogi obejścia go kodem zapasowym.
CREATE TABLE IF NOT EXISTS drugi_skladnik (
    profil_id   INTEGER PRIMARY KEY REFERENCES profile(id) ON DELETE CASCADE,
    sekret      TEXT NOT NULL,
    wlaczony    INTEGER NOT NULL DEFAULT 0,
    utworzono   TEXT NOT NULL,
    potwierdzono TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS kody_zapasowe (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profil_id   INTEGER NOT NULL REFERENCES profile(id) ON DELETE CASCADE,
    skrot       TEXT NOT NULL,
    zuzyty      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_kody_profil ON kody_zapasowe(profil_id);

CREATE TABLE IF NOT EXISTS proby_logowania (
    login           TEXT PRIMARY KEY COLLATE NOCASE,
    nieudanych      INTEGER NOT NULL DEFAULT 0,
    ostatnia        TEXT NOT NULL,
    zablokowany_do  TEXT DEFAULT ''
);

-- ── wątki rozmów ──────────────────────────────────────────────────
--
-- Dotąd historia była JEDNĄ rozmową na parę (sprawa, dokument). Prawnik
-- prowadzący dwa oddzielne tropy w tej samej sprawie mieszał je w jednym
-- ciągu, a wrócić do wcześniejszego wątku po tygodniu nie dało się inaczej
-- niż przewijaniem. Wątek nazwany rozwiązuje oba te problemy naraz.
--
-- `dokument_id` zostaje na wątku, nie na wiadomości: wątek o konkretnym
-- piśmie i wątek o całej sprawie to dwa różne konteksty i nie powinny się
-- przeplatać w jednym ciągu — ta zasada obowiązywała już wcześniej.
CREATE TABLE IF NOT EXISTS watki (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    sprawa_id          INTEGER NOT NULL REFERENCES sprawy(id) ON DELETE CASCADE,
    dokument_id        INTEGER REFERENCES dokumenty(id) ON DELETE CASCADE,
    tytul              TEXT NOT NULL,
    profil_id          INTEGER REFERENCES profile(id) ON DELETE SET NULL,
    utworzono          TEXT NOT NULL,
    ostatnia_aktywnosc TEXT NOT NULL,
    zamkniety          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_watki_sprawa
    ON watki(sprawa_id, ostatnia_aktywnosc DESC);
"""


def _teraz() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Polaczenie(sqlite3.Connection):
    """Połączenie bezpieczne przy pracy KILKU OSÓB NARAZ.

    ════════════════════════════════════════════════════════════════
     ZMIERZONA USTERKA, NIE OSTROŻNOŚĆ — 16.08.2026
    ════════════════════════════════════════════════════════════════

    Panel jest wielowątkowy (`serwer.py`: `ThreadingHTTPServer`) i dzieli
    JEDNO połączenie między wszystkie wątki. Pierwszy test wysyłający
    żądania równolegle (`tests/test_wspolbieznosc.py`) wywrócił je
    natychmiast:

        sqlite3.InterfaceError: bad parameter or other API misuse

    przy dziesięciu wątkach zakładających wątki rozmów jednocześnie.
    W praktyce: dwie osoby pracujące w tej samej chwili dostają błąd
    i **tracą zapis** — czyli dokładnie ten scenariusz, dla którego ten
    system powstał („różne osoby, w różnym czasie, na różnych profilach").

    PRZYCZYNA. `sqlite3.threadsafety == 3`, więc warstwa C jest
    serializowana i to nie ona zawodzi. Zawodzi warstwa Pythona:
    moduł trzyma **cache przygotowanych zapytań** per połączenie, a dwa
    wątki wykonujące ten sam SQL sięgają po ten sam obiekt statement
    i resetują go sobie nawzajem.

    NAPRAWA — dwa niezależne środki, bo koszt jest znikomy przy tej
    skali obciążenia, a skutek usterki to utrata danych:

      1. `cached_statements=0` — każde wywołanie przygotowuje własne
         zapytanie, więc nie ma czego współdzielić;
      2. zamek na `execute`/`executemany`/`executescript`/`commit` —
         serializacja także przygotowania i zatwierdzania.

    Zamek jest RE-ENTRANT: `_domiguj` i inne funkcje wywołują `execute`
    zagnieżdżone w obrębie jednego wątku, a zwykły `Lock` zakleszczyłby
    się na pierwszym takim wywołaniu.

    ⚠️ NIE JEST TO OPTYMALIZACJA WYDAJNOŚCI I NIE MA BYĆ.
       Kancelaria to kilka osób, a SQLite i tak szereguje zapisy.
       Poprawność przy dwóch osobach jest tu warta więcej niż
       przepustowość przy dwustu.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zamek = threading.RLock()

    def execute(self, *args, **kwargs):
        with self._zamek:
            return super().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        with self._zamek:
            return super().executemany(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        with self._zamek:
            return super().executescript(*args, **kwargs)

    def commit(self):
        with self._zamek:
            return super().commit()


def polacz(sciezka: Path | str | None = None) -> sqlite3.Connection:
    sciezka = Path(sciezka) if sciezka else SCIEZKA_BAZY
    if str(sciezka) != ":memory:":
        sciezka.parent.mkdir(parents=True, exist_ok=True)
    polaczenie = sqlite3.connect(
        sciezka, check_same_thread=False,
        factory=Polaczenie,
        # Patrz `Polaczenie` — współdzielony cache zapytań jest tu
        # przyczyną utraty zapisów przy pracy równoległej.
        cached_statements=0)
    polaczenie.row_factory = sqlite3.Row
    polaczenie.execute("PRAGMA foreign_keys = ON")
    polaczenie.executescript(SCHEMAT)
    _domiguj(polaczenie)
    return polaczenie


def _domiguj(db) -> None:
    """Dołożenie kolumn do bazy założonej wcześniejszą wersją schematu.

    `CREATE TABLE IF NOT EXISTS` nie dodaje kolumn do istniejącej tabeli,
    więc bez tego kroku baza z dokumentami wgranymi przed wprowadzeniem
    rozpoznawania języka wywracałaby zapytania na nieznanej kolumnie.
    """
    istniejace = {w["name"] for w in db.execute("PRAGMA table_info(dokumenty)")}
    for kolumna, definicja in (("jezyk", "TEXT DEFAULT ''"),
                               ("jezyk_pewnosc", "REAL DEFAULT 0.0")):
        if kolumna not in istniejace:
            db.execute(f"ALTER TABLE dokumenty ADD COLUMN {kolumna} {definicja}")
    # Dopiero teraz — kolumna na pewno istnieje.
    db.execute("CREATE INDEX IF NOT EXISTS idx_dok_jezyk "
               "ON dokumenty(sprawa_id, jezyk)")

    # Autor wiadomości. Bez tej kolumny historia sprawy jest wspólna dla
    # wszystkich, co przeczy wymogowi obsługi przez różne osoby na różnych
    # profilach. NULL znaczy „wiadomość sprzed wprowadzenia profili" —
    # nie podstawiamy tu żadnego profilu, bo autorstwa wstecz nie znamy.
    prof = {w["name"] for w in db.execute("PRAGMA table_info(profile)")}
    for kolumna in ("zgody_wersja", "zgody_czas"):
        if kolumna not in prof:
            db.execute(f"ALTER TABLE profile ADD COLUMN {kolumna} TEXT DEFAULT ''")

    wiad = {w["name"] for w in db.execute("PRAGMA table_info(wiadomosci)")}
    if "profil_id" not in wiad:
        db.execute("ALTER TABLE wiadomosci ADD COLUMN profil_id INTEGER "
                   "REFERENCES profile(id) ON DELETE SET NULL")
    if "watek_id" not in wiad:
        db.execute("ALTER TABLE wiadomosci ADD COLUMN watek_id INTEGER "
                   "REFERENCES watki(id) ON DELETE CASCADE")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wiad_profil "
               "ON wiadomosci(sprawa_id, profil_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_wiad_watek "
               "ON wiadomosci(watek_id, id)")
    db.commit()


def oczysc_dokumenty(db) -> dict:
    """Usuwa znaczniki z dokumentów wgranych przed wprowadzeniem oczyszczania.

    Bezpieczne do powtórzenia: dokument bez znaczników nie zmienia się,
    więc ponowne uruchomienie nic nie psuje.

    ⚠️ Zmienia offsety w treści, więc cytaty zapisane w historii czatu
    dla tych dokumentów przestają wskazywać właściwe miejsce. Świadomy
    koszt: alternatywą jest zostawienie akt, w których model widzi
    jedną czwartą treści.
    """
    import oczyszczanie

    wiersze = db.execute("SELECT id, tresc FROM dokumenty").fetchall()
    zmienione = usuniete_znakow = 0
    for w in wiersze:
        czysta = oczyszczanie.oczysc(w["tresc"])
        if czysta != w["tresc"]:
            usuniete_znakow += len(w["tresc"]) - len(czysta)
            db.execute("UPDATE dokumenty SET tresc = ? WHERE id = ?",
                       (czysta, w["id"]))
            zmienione += 1
    if zmienione:
        db.commit()
        zapisz_audyt(db, "oczyszczenie_dokumentow", None,
                     f"{zmienione} dok., usunięto {usuniete_znakow} znaków")
    return {"dokumentow": len(wiersze), "zmienionych": zmienione,
            "usunietych_znakow": usuniete_znakow}


def uzupelnij_jezyki(db) -> int:
    """Rozpoznaje język dokumentów, które go jeszcze nie mają.

    Uruchamiane przy starcie panelu — dzięki temu dokumenty wgrane
    wcześniej też trafiają do właściwego modelu.
    """
    import jezyk as mod_jezyk

    braki = db.execute(
        "SELECT id, tresc FROM dokumenty WHERE jezyk IS NULL OR jezyk = ''"
    ).fetchall()
    for w in braki:
        wynik = mod_jezyk.rozpoznaj(w["tresc"])
        db.execute("UPDATE dokumenty SET jezyk = ?, jezyk_pewnosc = ? WHERE id = ?",
                   (wynik.jezyk, round(wynik.pewnosc, 3), w["id"]))
    db.commit()
    return len(braki)


# ── log audytowy z łańcuchem sum kontrolnych ────────────────────────

def zapisz_audyt(db, operacja: str, sprawa_id: int | None = None,
                 szczegol: str = "") -> None:
    """Wpis append-only z łańcuchem sum (wymaganie F-34).

    Każdy wpis wiąże sumę poprzedniego, więc usunięcie lub podmiana
    wiersza w środku łańcucha jest wykrywalna.
    """
    import hashlib

    wiersz = db.execute(
        "SELECT hash FROM audyt ORDER BY id DESC LIMIT 1"
    ).fetchone()
    poprzedni = wiersz["hash"] if wiersz else ""

    czas = _teraz()
    material = f"{poprzedni}|{czas}|{sprawa_id}|{operacja}|{szczegol}"
    biezacy = hashlib.sha256(material.encode("utf-8")).hexdigest()

    db.execute(
        "INSERT INTO audyt (czas, sprawa_id, operacja, szczegol, "
        "poprzedni_hash, hash) VALUES (?,?,?,?,?,?)",
        (czas, sprawa_id, operacja, szczegol, poprzedni, biezacy),
    )
    db.commit()


def zweryfikuj_lancuch_audytu(db) -> tuple[bool, str]:
    """Sprawdza spójność łańcucha. Używane w teście odtworzenia kopii."""
    import hashlib

    poprzedni = ""
    for w in db.execute("SELECT * FROM audyt ORDER BY id"):
        material = (f"{poprzedni}|{w['czas']}|{w['sprawa_id']}|"
                    f"{w['operacja']}|{w['szczegol']}")
        oczekiwany = hashlib.sha256(material.encode("utf-8")).hexdigest()
        if oczekiwany != w["hash"]:
            return False, f"Łańcuch przerwany na wpisie {w['id']}"
        poprzedni = w["hash"]
    return True, "Łańcuch nieprzerwany"


# ── sprawy ──────────────────────────────────────────────────────────

def dodaj_sprawe(db, sygnatura: str, nazwa: str, organ: str = "",
                 rodzaj: str = "karna", etap: str = "",
                 prowadzacy: str = "", poufnosc: str = "standardowa") -> int:
    kursor = db.execute(
        "INSERT INTO sprawy (sygnatura, nazwa, organ, rodzaj, etap, "
        "prowadzacy, poufnosc, utworzono) VALUES (?,?,?,?,?,?,?,?)",
        (sygnatura.strip(), nazwa.strip(), organ.strip(), rodzaj,
         etap.strip(), prowadzacy.strip(), poufnosc, _teraz()),
    )
    db.commit()
    sprawa_id = kursor.lastrowid
    zapisz_audyt(db, "utworzenie_sprawy", sprawa_id, sygnatura)
    return sprawa_id


def lista_spraw(db) -> list[dict]:
    """Lista spraw z licznikami. Nie zwraca ŻADNEJ treści dokumentów."""
    wiersze = db.execute("""
        SELECT s.*,
               (SELECT COUNT(*) FROM dokumenty d WHERE d.sprawa_id = s.id)
                   AS liczba_dokumentow,
               (SELECT COUNT(*) FROM wiadomosci w WHERE w.sprawa_id = s.id)
                   AS liczba_wiadomosci
        FROM sprawy s ORDER BY s.id DESC
    """).fetchall()
    return [dict(w) for w in wiersze]


def pobierz_sprawe(db, sprawa_id: int) -> dict | None:
    w = db.execute("SELECT * FROM sprawy WHERE id = ?", (sprawa_id,)).fetchone()
    return dict(w) if w else None


# ── dokumenty — zawsze w obrębie sprawy ─────────────────────────────

def dodaj_dokument(db, sprawa_id: int, nazwa: str, tresc: str,
                   rodzaj: str = "pismo") -> int:
    """Dodaje dokument DO WSKAZANEJ SPRAWY.

    Nie istnieje wariant bez `sprawa_id` — dokument nie może zawisnąć
    poza sprawą.
    """
    if pobierz_sprawe(db, sprawa_id) is None:
        raise ValueError(f"Sprawa {sprawa_id} nie istnieje.")

    import jezyk as mod_jezyk
    import oczyszczanie

    tresc = unicodedata.normalize("NFC", tresc)
    # ⚠️ OCZYSZCZANIE MUSI NASTĄPIĆ PRZED ZAPISEM, NIE PRZY ODCZYCIE.
    #
    # Cytat jest zakresem znaków w treści dokumentu (ADR-0006, ADR-0007).
    # Gdyby znaczniki usuwać przy odczycie, offsety przesunęłyby się
    # względem tego, co stoi w bazie, i każdy zapisany cytat wskazywałby
    # w złe miejsce.
    #
    # Pomiar z 14.08.2026: 100% orzeczeń z SAOS niosło surowy HTML,
    # 15,4% znaków to znaczniki, a filtr jakości odrzucał przez to
    # 78% zdań polskiego korpusu — model nie widział trzech czwartych akt.
    tresc = oczyszczanie.oczysc(tresc)
    # Język rozpoznawany przy wgraniu — raz, a nie przy każdej analizie.
    rozpoznanie = mod_jezyk.rozpoznaj(tresc)

    kursor = db.execute(
        "INSERT INTO dokumenty (sprawa_id, nazwa, rodzaj, tresc, jezyk, "
        "jezyk_pewnosc, dodano) VALUES (?,?,?,?,?,?,?)",
        (sprawa_id, nazwa.strip(), rodzaj, tresc,
         rozpoznanie.jezyk, round(rozpoznanie.pewnosc, 3), _teraz()),
    )
    db.commit()
    zapisz_audyt(db, "dodanie_dokumentu", sprawa_id,
                 f"{nazwa} ({len(tresc)} zn., język: {rozpoznanie.jezyk})")
    return kursor.lastrowid


def lista_dokumentow(db, sprawa_id: int) -> list[dict]:
    """Metadane dokumentów JEDNEJ sprawy (bez treści)."""
    wiersze = db.execute(
        "SELECT id, sprawa_id, nazwa, rodzaj, LENGTH(tresc) AS dlugosc, "
        "jezyk, jezyk_pewnosc, dodano "
        "FROM dokumenty WHERE sprawa_id = ? ORDER BY id",
        (sprawa_id,),
    ).fetchall()
    return [dict(w) for w in wiersze]


def jezyki_dokumentow(db, sprawa_id: int) -> dict[str, str]:
    """Mapa {id_dokumentu: język} — wejście dla doboru modelu w analizie."""
    wiersze = db.execute(
        "SELECT id, jezyk FROM dokumenty WHERE sprawa_id = ?", (sprawa_id,)
    ).fetchall()
    return {str(w["id"]): (w["jezyk"] or "nieznany") for w in wiersze}


def tresci_dokumentow(db, sprawa_id: int,
                      dokument_id: int | None = None) -> dict[str, str]:
    """Mapa {id_dokumentu: treść} — WYŁĄCZNIE z jednej sprawy.

    To jedyne wejście do treści dokumentów w całym panelu. Agent i
    weryfikator cytatów dostają dokładnie ten słownik, więc cytat
    z innej sprawy jest strukturalnie niemożliwy — nie ma go w zbiorze,
    wobec którego prowadzona jest weryfikacja.

    `dokument_id` dodatkowo zawęża zakres do jednego dokumentu, gdy
    prawnik chce rozmawiać tylko o nim.
    """
    if dokument_id is not None:
        wiersze = db.execute(
            "SELECT id, tresc FROM dokumenty WHERE sprawa_id = ? AND id = ?",
            (sprawa_id, dokument_id),
        ).fetchall()
    else:
        wiersze = db.execute(
            "SELECT id, tresc FROM dokumenty WHERE sprawa_id = ? ORDER BY id",
            (sprawa_id,),
        ).fetchall()
    return {str(w["id"]): w["tresc"] for w in wiersze}


def pobierz_dokument(db, sprawa_id: int, dokument_id: int) -> dict | None:
    """Pobranie dokumentu wymaga PODANIA SPRAWY.

    Sam identyfikator dokumentu nie wystarcza — gdyby ktoś podał numer
    dokumentu z innej sprawy, zapytanie nie zwróci nic.
    """
    w = db.execute(
        "SELECT * FROM dokumenty WHERE id = ? AND sprawa_id = ?",
        (dokument_id, sprawa_id),
    ).fetchone()
    return dict(w) if w else None


def usun_dokument(db, sprawa_id: int, dokument_id: int) -> bool:
    kursor = db.execute(
        "DELETE FROM dokumenty WHERE id = ? AND sprawa_id = ?",
        (dokument_id, sprawa_id),
    )
    db.commit()
    if kursor.rowcount:
        zapisz_audyt(db, "usuniecie_dokumentu", sprawa_id, str(dokument_id))
    return bool(kursor.rowcount)


# ── pamięć czatu — zamknięta w obrębie sprawy ───────────────────────

def dodaj_wiadomosc(db, sprawa_id: int, rola: str, tresc: str,
                    dokument_id: int | None = None,
                    cytaty_json: str = "[]",
                    odrzucone_json: str = "[]",
                    profil_id: int | None = None,
                    watek_id: int | None = None) -> int:
    kursor = db.execute(
        "INSERT INTO wiadomosci (sprawa_id, dokument_id, rola, tresc, "
        "cytaty_json, odrzucone_json, utworzono, profil_id, watek_id) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (sprawa_id, dokument_id, rola, tresc, cytaty_json,
         odrzucone_json, _teraz(), profil_id, watek_id),
    )
    if watek_id is not None:
        # Kolejność listy wątków ma odpowiadać temu, gdzie trwa praca.
        db.execute("UPDATE watki SET ostatnia_aktywnosc = ? WHERE id = ?",
                   (_teraz(), watek_id))
    db.commit()
    return kursor.lastrowid


def historia(db, sprawa_id: int, dokument_id: int | None = None,
             limit: int = 200) -> list[dict]:
    """Pamięć rozmowy — WYŁĄCZNIE z jednej sprawy.

    Gdy podano `dokument_id`, historia zawęża się do wątku o tym
    dokumencie. Wątek sprawy i wątek dokumentu są rozdzielone celowo:
    prawnik rozmawiający o jednym piśmie nie chce w kontekście
    wcześniejszych pytań o całą sprawę.
    """
    # Autor dołączany zapytaniem LEFT JOIN: wiadomości sprzed wprowadzenia
    # profili mają `profil_id` puste i mają takie zostać — autorstwa wstecz
    # nie znamy i nie wolno go zmyślić.
    wybor = ("SELECT w.*, p.login AS autor_login, p.imie AS autor_imie, "
             "p.nazwisko AS autor_nazwisko, p.rola AS autor_rola "
             "FROM wiadomosci w LEFT JOIN profile p ON p.id = w.profil_id ")
    # ⚠️ WIADOMOŚCI NALEŻĄCE DO WĄTKU SĄ TU WYKLUCZONE.
    #
    # Wykryte przeglądem 16.08.2026: wpisy wątku mają `dokument_id` puste,
    # więc bez tego warunku wpadały RÓWNIEŻ do rozmowy całej sprawy.
    # Skutek nie był wizualny — przy pytaniu „o całą sprawę" do modelu
    # szła pamięć zanieczyszczona cudzymi wątkami, a prawnik dostawał
    # w kontekście rozmowę, której nie prowadził w tym miejscu.
    #
    # Rozmowa sprawy = wpisy POZA jakimkolwiek wątkiem. Wątek ma własną
    # ścieżkę odczytu (`historia_watku`).
    if dokument_id is not None:
        wiersze = db.execute(
            wybor + "WHERE w.sprawa_id = ? AND w.dokument_id = ? "
                    "AND w.watek_id IS NULL ORDER BY w.id LIMIT ?",
            (sprawa_id, dokument_id, limit),
        ).fetchall()
    else:
        wiersze = db.execute(
            wybor + "WHERE w.sprawa_id = ? AND w.dokument_id IS NULL "
                    "AND w.watek_id IS NULL ORDER BY w.id LIMIT ?",
            (sprawa_id, limit),
        ).fetchall()
    return [dict(w) for w in wiersze]


# ── wątki ───────────────────────────────────────────────────────────
#
# ZASADA NACZELNA TEGO MODUŁU OBOWIĄZUJE TAKŻE TUTAJ: nie ma funkcji,
# która zwraca wątek bez podania `sprawa_id`. Wątek z innej sprawy jest
# nieodróżnialny od nieistniejącego.

TYTUL_MAKS = 120


def zaloz_watek(db, sprawa_id: int, tytul: str,
                dokument_id: int | None = None,
                profil_id: int | None = None) -> int:
    teraz = _teraz()
    tytul = (tytul or "").strip()[:TYTUL_MAKS] or "Nowy wątek"
    kursor = db.execute(
        "INSERT INTO watki (sprawa_id, dokument_id, tytul, profil_id, "
        "utworzono, ostatnia_aktywnosc) VALUES (?,?,?,?,?,?)",
        (sprawa_id, dokument_id, tytul, profil_id, teraz, teraz))
    db.commit()
    return int(kursor.lastrowid)


def lista_watkow(db, sprawa_id: int, limit: int = 100) -> list[dict]:
    """Wątki sprawy, najświeższe pierwsze — razem z autorem i licznikiem.

    Licznik wiadomości liczony podzapytaniem, żeby lista wątków dała się
    pokazać jednym żądaniem. Bez tego interfejs musiałby odpytywać
    o każdy wątek osobno.
    """
    wiersze = db.execute(
        "SELECT w.*, p.imie AS autor_imie, p.nazwisko AS autor_nazwisko, "
        "  d.nazwa AS dokument_nazwa, "
        "  (SELECT COUNT(*) FROM wiadomosci m WHERE m.watek_id = w.id) AS wiadomosci "
        "FROM watki w "
        "LEFT JOIN profile p ON p.id = w.profil_id "
        "LEFT JOIN dokumenty d ON d.id = w.dokument_id "
        "WHERE w.sprawa_id = ? "
        "ORDER BY w.ostatnia_aktywnosc DESC, w.id DESC LIMIT ?",
        (sprawa_id, limit)).fetchall()
    return [dict(w) for w in wiersze]


def pobierz_watek(db, sprawa_id: int, watek_id: int) -> dict | None:
    wiersz = db.execute(
        "SELECT * FROM watki WHERE id = ? AND sprawa_id = ?",
        (watek_id, sprawa_id)).fetchone()
    return dict(wiersz) if wiersz else None


def odswiez_watek(db, watek_id: int) -> None:
    db.execute("UPDATE watki SET ostatnia_aktywnosc = ? WHERE id = ?",
               (_teraz(), watek_id))
    db.commit()


def zmien_watek(db, sprawa_id: int, watek_id: int,
                tytul: str | None = None,
                zamkniety: bool | None = None) -> bool:
    """Zmiana nazwy lub zamknięcie/wznowienie. Zwraca, czy coś zmieniono."""
    if pobierz_watek(db, sprawa_id, watek_id) is None:
        return False
    if tytul is not None:
        db.execute("UPDATE watki SET tytul = ? WHERE id = ?",
                   ((tytul or "").strip()[:TYTUL_MAKS] or "Nowy wątek", watek_id))
    if zamkniety is not None:
        # Zamknięcie NIE kasuje wiadomości — wątek da się wznowić.
        db.execute("UPDATE watki SET zamkniety = ? WHERE id = ?",
                   (1 if zamkniety else 0, watek_id))
    db.commit()
    return True


def usun_watek(db, sprawa_id: int, watek_id: int) -> bool:
    kursor = db.execute("DELETE FROM watki WHERE id = ? AND sprawa_id = ?",
                        (watek_id, sprawa_id))
    db.commit()
    return kursor.rowcount > 0


def historia_watku(db, sprawa_id: int, watek_id: int,
                   limit: int = 200) -> list[dict]:
    """Wiadomości wątku. `sprawa_id` w warunku, mimo że `watek_id` jest
    unikalny — zamknięcie w obrębie sprawy ma nie zależeć od tego, czy
    wywołujący podał właściwy identyfikator wątku."""
    wiersze = db.execute(
        "SELECT m.*, p.login AS autor_login, p.imie AS autor_imie, "
        "p.nazwisko AS autor_nazwisko, p.rola AS autor_rola "
        "FROM wiadomosci m "
        "LEFT JOIN profile p ON p.id = m.profil_id "
        "JOIN watki w ON w.id = m.watek_id "
        "WHERE m.watek_id = ? AND w.sprawa_id = ? "
        "ORDER BY m.id LIMIT ?",
        (watek_id, sprawa_id, limit)).fetchall()
    return [dict(w) for w in wiersze]


def wyczysc_historie(db, sprawa_id: int, dokument_id: int | None = None) -> int:
    if dokument_id is not None:
        kursor = db.execute(
            "DELETE FROM wiadomosci WHERE sprawa_id = ? AND dokument_id = ?",
            (sprawa_id, dokument_id),
        )
    else:
        kursor = db.execute(
            "DELETE FROM wiadomosci WHERE sprawa_id = ? AND dokument_id IS NULL",
            (sprawa_id,),
        )
    db.commit()
    zapisz_audyt(db, "wyczyszczenie_historii", sprawa_id, str(dokument_id))
    return kursor.rowcount
