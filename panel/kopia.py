"""Kopia zapasowa bazy — z odtworzeniem sprawdzanym, nie deklarowanym.

════════════════════════════════════════════════════════════════════════
 PO CO
════════════════════════════════════════════════════════════════════════

Procedura odtworzenia była opisana w `docs/10-operacje/backup-i-dr.md`
i NIGDY NIEPRZEĆWICZONA — mówi o tym wprost oświadczenie, które każda
osoba przyjmuje przy zakładaniu profilu. Deklarowane RPO ≤ 24 h
i RTO ≤ 8 h pozostawały założeniem.

RODO art. 32 ust. 1 lit. c wymaga „zdolności do szybkiego przywrócenia
dostępności danych", a art. 21 ust. 2 lit. c dyrektywy 2022/2555 —
ciągłości działania. Kopia, której nikt nigdy nie odtworzył, nie jest
dowodem żadnej z tych zdolności.

════════════════════════════════════════════════════════════════════════
 ZASADA: KOPIA BEZ SPRAWDZONEGO ODTWORZENIA TO NIE KOPIA
════════════════════════════════════════════════════════════════════════

Najczęstszy sposób utraty akt nie polega na braku kopii, tylko na
kopii, która okazuje się nieczytelna dopiero w dniu awarii. Dlatego
`wykonaj()` po zapisie:

    1. otwiera kopię jako osobną bazę,
    2. sprawdza ją `PRAGMA integrity_check`,
    3. porównuje liczbę spraw, dokumentów i wpisów audytu z oryginałem,
    4. dopiero wtedy melduje sukces.

Niepowodzenie któregokolwiek kroku kasuje plik i podnosi wyjątek.
Kopia, o której wiadomo, że jest zła, jest lepsza od kopii, o której
nie wiadomo nic.

⚠️ `sqlite3.Connection.backup` ZAMIAST KOPIOWANIA PLIKU.
   Skopiowanie pliku bazy, do której ktoś w tej chwili pisze, daje plik
   uszkodzony — i to w sposób ujawniający się dopiero przy odczycie.
   API `backup` robi spójny zrzut bez zatrzymywania panelu.

⚠️ KOPIA ZAWIERA CAŁE AKTA I NIE JEST SZYFROWANA PRZEZ TEN MODUŁ.
   Ochrona nośnika należy do kancelarii — plik kopii jest tak samo
   wrażliwy jak sama baza i musi trafić na zaszyfrowany dysk.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Ile kopii trzymamy. Powyżej tej liczby najstarsze są usuwane —
# dysk kancelarii nie jest archiwum, a kopia sprzed pół roku i tak
# nie odpowiada aktualnym aktom.
ILE_TRZYMAMY = 14

TABELE_KONTROLNE = ("sprawy", "dokumenty", "audyt", "wiadomosci", "profile")


class BladKopii(RuntimeError):
    """Kopia nie powstała albo nie przeszła sprawdzenia."""


@dataclass(frozen=True)
class Kopia:
    sciezka: Path
    bajtow: int
    liczniki: dict[str, int]
    sekund: float

    @property
    def megabajtow(self) -> float:
        return round(self.bajtow / 1024 / 1024, 1)


def _liczniki(db: sqlite3.Connection) -> dict[str, int]:
    wynik: dict[str, int] = {}
    for tabela in TABELE_KONTROLNE:
        try:
            wynik[tabela] = db.execute(
                f"SELECT COUNT(*) AS ile FROM {tabela}").fetchone()[0]
        except sqlite3.OperationalError:
            continue                     # tabela z nowszego schematu
    return wynik


def _sprawdz(sciezka: Path, oczekiwane: dict[str, int]) -> dict[str, int]:
    """Otwiera kopię i sprawdza, czy da się z niej odtworzyć akta."""
    kontrolna = sqlite3.connect(f"file:{sciezka}?mode=ro", uri=True)
    try:
        stan = kontrolna.execute("PRAGMA integrity_check").fetchone()[0]
        if stan != "ok":
            raise BladKopii(f"Kopia nie przeszła kontroli spójności: {stan}")

        odczytane = _liczniki(kontrolna)
        rozbieznosci = [
            f"{tabela}: oryginał {ile}, kopia {odczytane.get(tabela)}"
            for tabela, ile in oczekiwane.items()
            if odczytane.get(tabela) != ile
        ]
        if rozbieznosci:
            raise BladKopii(
                "Kopia ma inną zawartość niż oryginał — "
                + "; ".join(rozbieznosci))
        return odczytane
    finally:
        kontrolna.close()


def wykonaj(db: sqlite3.Connection, katalog: Path,
            ile_trzymamy: int = ILE_TRZYMAMY) -> Kopia:
    """Kopia bazy, sprawdzona odczytem. Podnosi `BladKopii` przy porażce."""
    katalog = Path(katalog)
    katalog.mkdir(parents=True, exist_ok=True)

    # ⚠️ NIEZATWIERDZONA TRANSAKCJA ZAWIESZA `backup()` — ZMIERZONE.
    #
    # `sqlite3.Connection.backup` czeka na zwolnienie blokady zapisu
    # i czeka BEZ KOŃCA. Przy otwartej transakcji na tym samym połączeniu
    # oznacza to żądanie panelu, które nigdy nie wraca, i operatora,
    # który nie wie, czy kopia trwa, czy zawisła.
    #
    # Odmawiamy więc od razu i mówimy, co jest nie tak. Panel zatwierdza
    # każdą operację od razu (`baza.*` woła `commit`), więc otwarta
    # transakcja w tym miejscu jest sama w sobie usterką do naprawienia,
    # a nie stanem do przeczekania.
    if db.in_transaction:
        raise BladKopii(
            "Na połączeniu z bazą stoi niezatwierdzona transakcja — kopia "
            "zawisłaby w oczekiwaniu na zwolnienie blokady. Zakończ trwający "
            "zapis i powtórz.")

    # ⚠️ ZNACZNIK Z MILISEKUNDAMI — KOLIZJA ZMIERZONA TESTEM.
    #
    # Przy rozdzielczości sekundowej dwie kopie zdjęte w tej samej
    # sekundzie dostawały tę samą nazwę, więc druga NADPISYWAŁA pierwszą
    # bez słowa. Przy kopii przed ryzykowną operacją i kopii kontrolnej
    # tuż po niej zostawał jeden plik zamiast dwóch — i to ten młodszy.
    znacznik = datetime.now(timezone.utc).astimezone().strftime(
        "%Y-%m-%d-%H%M%S-%f")[:-3]
    cel = katalog / f"panel-{znacznik}.sqlite3"
    poczatek = datetime.now(timezone.utc)

    oczekiwane = _liczniki(db)

    docelowa = sqlite3.connect(cel)
    try:
        # ⚠️ `backup` zamiast kopiowania pliku — patrz komentarz na górze.
        db.backup(docelowa)
    except sqlite3.Error as e:
        docelowa.close()
        cel.unlink(missing_ok=True)
        raise BladKopii(f"Nie udało się wykonać kopii: {e}") from e
    finally:
        docelowa.close()

    try:
        liczniki = _sprawdz(cel, oczekiwane)
    except BladKopii:
        # Plik, o którym wiadomo, że jest zły, nie może zostać na dysku
        # i udawać kopii w dniu awarii.
        cel.unlink(missing_ok=True)
        raise

    posprzataj(katalog, ile_trzymamy)
    sekund = (datetime.now(timezone.utc) - poczatek).total_seconds()
    return Kopia(cel, cel.stat().st_size, liczniki, round(sekund, 2))


def lista(katalog: Path) -> list[dict]:
    katalog = Path(katalog)
    if not katalog.exists():
        return []
    return [
        {"nazwa": p.name,
         "megabajtow": round(p.stat().st_size / 1024 / 1024, 1),
         "czas": datetime.fromtimestamp(p.stat().st_mtime).isoformat(
             timespec="seconds")}
        for p in sorted(katalog.glob("panel-*.sqlite3"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    ]


def posprzataj(katalog: Path, ile_trzymamy: int = ILE_TRZYMAMY) -> int:
    pliki = sorted(Path(katalog).glob("panel-*.sqlite3"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    usuniete = 0
    for stary in pliki[ile_trzymamy:]:
        stary.unlink(missing_ok=True)
        usuniete += 1
    return usuniete


def odtworz(kopia: Path, cel: Path) -> dict[str, int]:
    """Odtworzenie bazy z kopii. Zwraca liczniki odtworzonych tabel.

    ⚠️ NADPISUJE `cel`. Poprzednia baza jest odkładana obok z sufiksem
    `.przed-odtworzeniem`, a nie kasowana: odtworzenie z niewłaściwej
    kopii jest błędem możliwym do popełnienia pod presją, i musi być
    odwracalne.
    """
    kopia, cel = Path(kopia), Path(cel)
    if not kopia.exists():
        raise BladKopii(f"Nie ma pliku kopii: {kopia}")

    # ⚠️ Wyjątek SQLite nie może wyciec do wywołującego.
    #
    # Plik, który nie jest bazą, podnosi `DatabaseError` — komunikat
    # „file is not a database" nie mówi operatorowi w dniu awarii, co
    # ma zrobić. Zamieniamy go na jeden typ błędu z jednoznaczną treścią.
    try:
        kontrolna = sqlite3.connect(f"file:{kopia}?mode=ro", uri=True)
        try:
            if kontrolna.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BladKopii("Kopia jest uszkodzona — odtworzenie przerwane.")
            liczniki = _liczniki(kontrolna)
        finally:
            kontrolna.close()
    except sqlite3.Error as e:
        raise BladKopii(
            f"Pliku {kopia.name} nie da się otworzyć jako bazy — nie jest "
            f"kopią albo jest uszkodzony. Odtworzenie przerwane, bieżąca "
            f"baza nietknięta. Szczegół: {e}") from e

    if cel.exists():
        shutil.copy2(cel, cel.with_suffix(cel.suffix + ".przed-odtworzeniem"))
    shutil.copy2(kopia, cel)
    return liczniki
