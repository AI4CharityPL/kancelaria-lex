"""Kopia zapasowa — z odtworzeniem SPRAWDZANYM, nie deklarowanym.

⚠️ TO JEST TO ĆWICZENIE ODTWORZENIA, KTÓREGO DOTĄD NIE BYŁO.

Oświadczenie przyjmowane przy zakładaniu profilu mówi wprost:
„procedura odtworzenia NIE ZOSTAŁA JESZCZE PRZEĆWICZONA — do czasu
pierwszego ćwiczenia deklarowane czasy są założeniem, nie zmierzoną
wartością". Ten plik zamienia założenie w test wykonywany przy każdym
przebiegu.

Najczęstszy sposób utraty akt to nie brak kopii, tylko kopia, która
okazuje się nieczytelna dopiero w dniu awarii.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import baza  # noqa: E402
import kopia as mod_kopia  # noqa: E402

TRESC = ("Sąd Okręgowy oddalił wniosek obrońcy 14 września 2006 r. "
         "Zabezpieczenie ustalono na 1 008,00 zł.")


@pytest.fixture
def katalog():
    """Katalog roboczy poza `panel/dane/` i poza katalogiem pytesta.

    `tmp_path` bywa w tym środowisku niedostępny, a test dotykający
    `panel/dane/` pisałby po aktach, na których pracuje kancelaria.
    """
    sciezka = KORZEN / "eval" / "_kopie-testowe"
    shutil.rmtree(sciezka, ignore_errors=True)
    sciezka.mkdir(parents=True, exist_ok=True)
    yield sciezka
    shutil.rmtree(sciezka, ignore_errors=True)


@pytest.fixture
def db(katalog):
    polaczenie = baza.polacz(katalog / "zrodlo.sqlite3")
    sprawa = baza.dodaj_sprawe(polaczenie, "II K 147/26", "Sprawa testowa")
    baza.dodaj_dokument(polaczenie, sprawa, "postanowienie.txt", TRESC)
    baza.zapisz_audyt(polaczenie, "test.przygotowanie", sprawa, "szczegol")
    yield polaczenie
    polaczenie.close()


# ── wykonanie kopii ──────────────────────────────────────────────────

def test_kopia_powstaje_i_ma_zawartosc(db, katalog):
    wynik = mod_kopia.wykonaj(db, katalog / "kopie")
    assert wynik.sciezka.exists()
    assert wynik.bajtow > 0
    assert wynik.liczniki["sprawy"] == 1
    assert wynik.liczniki["dokumenty"] == 1


def test_kopia_jest_sprawdzana_odczytem(db, katalog):
    """⚠️ Sedno modułu: kopia jest OTWIERANA i porównywana z oryginałem.

    Bez tego kroku „kopia wykonana" znaczy tylko tyle, że powstał plik.
    """
    wynik = mod_kopia.wykonaj(db, katalog / "kopie")
    kontrolna = sqlite3.connect(wynik.sciezka)
    try:
        assert kontrolna.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tresc = kontrolna.execute(
            "SELECT tresc FROM dokumenty LIMIT 1").fetchone()[0]
        assert "1 008,00 zł" in tresc
    finally:
        kontrolna.close()


def test_kopia_zdejmowana_bez_zatrzymywania_panelu(db, katalog):
    """Panel nie musi być zatrzymywany na czas kopii.

    Skopiowanie pliku bazy, do której ktoś pisze, dałoby plik uszkodzony
    w sposób ujawniający się dopiero przy odczycie. `Connection.backup`
    robi zrzut spójny przy otwartym połączeniu.
    """
    db.execute("INSERT INTO audyt (czas, operacja, hash) VALUES ('t','x','h')")
    db.commit()
    wynik = mod_kopia.wykonaj(db, katalog / "kopie")
    assert wynik.liczniki["audyt"] >= 2


def test_niezatwierdzona_transakcja_konczy_sie_bledem_a_nie_zawieszeniem(
        db, katalog):
    """⚠️ USTERKA ZMIERZONA 16.08.2026, NIE HIPOTEZA.

    `sqlite3.Connection.backup` czeka na zwolnienie blokady zapisu BEZ
    KOŃCA. Pierwsza wersja tego testu zawiesiła przebieg pytesta na
    kilka minut — w panelu byłoby to żądanie, które nigdy nie wraca,
    i operator, który nie wie, czy kopia trwa, czy zawisła.

    Odmowa z komunikatem jest tu jedynym poprawnym zachowaniem.
    """
    db.execute("INSERT INTO audyt (czas, operacja, hash) VALUES ('t','x','h')")
    assert db.in_transaction, "test nie odtworzył warunku, który miał sprawdzić"

    with pytest.raises(mod_kopia.BladKopii) as info:
        mod_kopia.wykonaj(db, katalog / "kopie")
    assert "transakcja" in str(info.value)
    assert mod_kopia.lista(katalog / "kopie") == []


def test_stare_kopie_sa_usuwane(db, katalog):
    cel = katalog / "kopie"
    for _ in range(5):
        mod_kopia.wykonaj(db, cel, ile_trzymamy=3)
    assert len(mod_kopia.lista(cel)) == 3


def test_lista_kopii_od_najnowszej(db, katalog):
    cel = katalog / "kopie"
    mod_kopia.wykonaj(db, cel)
    mod_kopia.wykonaj(db, cel)
    spis = mod_kopia.lista(cel)
    assert len(spis) == 2
    assert spis[0]["czas"] >= spis[1]["czas"]


# ── ĆWICZENIE ODTWORZENIA ────────────────────────────────────────────

def test_odtworzenie_przywraca_akta(db, katalog):
    """⚠️ TEST, KTÓRY ZAMIENIA DEKLARACJĘ W DOWÓD.

    Kopia → utrata bazy → odtworzenie → akta z powrotem czytelne.
    """
    cel = katalog / "kopie"
    wykonana = mod_kopia.wykonaj(db, cel)
    sciezka_bazy = katalog / "zrodlo.sqlite3"
    db.close()

    # Awaria: baza znika.
    sciezka_bazy.unlink()
    assert not sciezka_bazy.exists()

    liczniki = mod_kopia.odtworz(wykonana.sciezka, sciezka_bazy)
    assert liczniki["dokumenty"] == 1

    odtworzona = baza.polacz(sciezka_bazy)
    try:
        tresc = odtworzona.execute(
            "SELECT tresc FROM dokumenty LIMIT 1").fetchone()[0]
        assert "Sąd Okręgowy oddalił wniosek" in tresc
        assert odtworzona.execute(
            "SELECT COUNT(*) FROM sprawy").fetchone()[0] == 1
    finally:
        odtworzona.close()


def test_odtworzenie_odklada_poprzednia_baze(db, katalog):
    """Odtworzenie z niewłaściwej kopii to błąd do popełnienia pod presją.

    Musi być odwracalne, więc poprzednia baza jest odkładana obok,
    a nie kasowana.
    """
    cel = katalog / "kopie"
    wykonana = mod_kopia.wykonaj(db, cel)
    sciezka_bazy = katalog / "zrodlo.sqlite3"
    db.close()

    mod_kopia.odtworz(wykonana.sciezka, sciezka_bazy)
    assert sciezka_bazy.with_suffix(".sqlite3.przed-odtworzeniem").exists()


def test_uszkodzona_kopia_nie_jest_odtwarzana(katalog):
    zepsuta = katalog / "zepsuta.sqlite3"
    zepsuta.write_bytes(b"SQLite format 3\x00" + b"\xff" * 4000)
    with pytest.raises(mod_kopia.BladKopii):
        mod_kopia.odtworz(zepsuta, katalog / "cel.sqlite3")


def test_brak_pliku_kopii_to_blad(katalog):
    with pytest.raises(mod_kopia.BladKopii):
        mod_kopia.odtworz(katalog / "nie-ma.sqlite3", katalog / "cel.sqlite3")


def test_kopia_ktora_nie_przeszla_kontroli_nie_zostaje_na_dysku(db, katalog,
                                                                monkeypatch):
    """⚠️ Plik, o którym wiadomo, że jest zły, nie może udawać kopii.

    W dniu awarii nikt nie sprawdza, czy najnowszy plik w katalogu jest
    dobry — bierze się najnowszy.
    """
    cel = katalog / "kopie"

    def niezgodne(*_a, **_k):
        raise mod_kopia.BladKopii("celowo niezgodne liczniki")

    monkeypatch.setattr(mod_kopia, "_sprawdz", niezgodne)
    with pytest.raises(mod_kopia.BladKopii):
        mod_kopia.wykonaj(db, cel)

    assert mod_kopia.lista(cel) == []
