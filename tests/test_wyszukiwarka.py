"""Testy wyszukiwarki — warunek skalowania do stu dokumentów.

Najważniejsze: offsety fragmentów muszą wskazywać pozycje w ORYGINALE.
Gdyby fragmenty miały własną numerację, każdy cytat trafiałby w próżnię
i weryfikator odrzucałby poprawne odpowiedzi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

from wyszukiwarka import (  # noqa: E402
    Indeks, dokumenty_trafne, podziel, podziel_wiele, rdzen, tokenizuj, wybierz,
)


# ── normalizacja polska ─────────────────────────────────────────────

@pytest.mark.parametrize("odmiany", [
    ("doręczono", "doręczenie", "doręczenia"),
    ("pojazdu", "pojazdem", "pojazdy"),
    ("świadka", "świadkowi", "świadkiem"),
])
def test_odmiany_maja_wspolny_rdzen(odmiany):
    """Fleksja nie może rozbijać dopasowania."""
    rdzenie = {rdzen(s) for s in odmiany}
    assert len(rdzenie) == 1, f"{odmiany} dały różne rdzenie: {rdzenie}"


def test_litera_l_z_kreska_normalizowana():
    """⚠️ NFD NIE rozkłada „ł" — to odrębna litera, nie „l" z diakrytykiem.

    Bez jawnej podmiany połowa polskich form czasownikowych („doręczył",
    „przesłuchał", „złożył") trafiałaby na inne rdzenie niż formy bez „ł".
    """
    assert "ł" not in rdzen("doręczył")
    assert rdzen("złożono").startswith("zloz")
    assert rdzen("przesłuchanie").startswith("przesluch")


def test_sygnatury_i_liczby_nietkniete():
    """Tam, gdzie liczy się dokładność, fleksja nie może majstrować."""
    assert rdzen("147/26") == "147/26"
    assert rdzen("2026") == "2026"


def test_stopslowa_odfiltrowane():
    tokeny = tokenizuj("W dniu zdarzenia oraz na miejscu")
    assert "w" not in tokeny and "oraz" not in tokeny and "na" not in tokeny
    assert any(t.startswith("zdarz") for t in tokeny)


# ── podział na fragmenty ────────────────────────────────────────────

def test_krotki_dokument_zostaje_calosci():
    fragmenty = podziel("1", "a.txt", "Krótka treść.")
    assert len(fragmenty) == 1
    assert fragmenty[0].poczatek == 0


def test_offsety_wskazuja_oryginal():
    """TEST ROZSTRZYGAJĄCY dla poprawności cytatów."""
    tresc = "".join(f"Zdanie numer {i}. " for i in range(400))
    fragmenty = podziel("1", "a.txt", tresc)

    assert len(fragmenty) > 1, "Dokument powinien się podzielić"
    for f in fragmenty:
        assert tresc[f.poczatek:f.koniec] == f.tresc, (
            f"Fragment {f.poczatek}-{f.koniec} nie zgadza się z oryginałem — "
            f"cytaty z tego fragmentu byłyby odrzucane przez weryfikator."
        )


def test_fragmenty_pokrywaja_caly_dokument():
    tresc = "".join(f"Akapit {i}.\n\n" for i in range(200))
    fragmenty = podziel("1", "a.txt", tresc)
    assert fragmenty[0].poczatek == 0
    assert fragmenty[-1].koniec == len(tresc)


def test_zakladka_zapobiega_gubieniu_granicy():
    tresc = "x" * 3000
    fragmenty = podziel("1", "a.txt", tresc, rozmiar=1000, zakladka=200)
    for poprzedni, nastepny in zip(fragmenty, fragmenty[1:]):
        assert nastepny.poczatek < poprzedni.koniec, "Brak zakładki między fragmentami"


def test_podzial_pustego_dokumentu():
    assert podziel("1", "a.txt", "") == []


# ── ranking ─────────────────────────────────────────────────────────

@pytest.fixture
def korpus():
    return podziel_wiele({
        "1": "Świadek zeznał, że widział pojazd marki Opel koloru srebrnego.",
        "2": "Odpis postanowienia doręczono obrońcy w dniu 12 sierpnia 2026 r.",
        "3": "Opinia biegłego z zakresu mechanoskopii dotycząca zamka drzwi.",
    }, {"1": "protokol.txt", "2": "postanowienie.txt", "3": "opinia.txt"})


def test_ranking_wskazuje_wlasciwy_dokument(korpus):
    wynik = Indeks(korpus).punktuj("Kiedy doręczono postanowienie?")
    assert wynik, "Ranking nie zwrócił nic"
    assert wynik[0][1].dokument_id == "2"


def test_ranking_dziala_mimo_fleksji(korpus):
    """Pytanie w innej formie gramatycznej niż dokument."""
    wynik = Indeks(korpus).punktuj("doręczenie odpisu")
    assert wynik[0][1].dokument_id == "2"


def test_ranking_znajduje_po_marce(korpus):
    wynik = Indeks(korpus).punktuj("Jakiej marki był pojazd?")
    assert wynik[0][1].dokument_id == "1"


def test_pytanie_bez_pokrycia_nie_wywala_wyszukiwarki(korpus):
    """Zwraca kontekst, żeby model miał na czym oprzeć ODMOWĘ."""
    wybrane = wybierz(korpus, "Jaki jest kurs euro do dolara?")
    assert wybrane, "Model musi dostać kontekst także przy pytaniu bez pokrycia"


# ── skala ───────────────────────────────────────────────────────────

def test_sto_dokumentow_miesci_sie_w_budzecie():
    """Warunek postawiony wprost: sto dokumentów ma działać."""
    dokumenty = {
        str(i): (f"Dokument numer {i}. " + "Treść wypełniająca akta sprawy. " * 60)
        for i in range(100)
    }
    dokumenty["42"] += (
        " Biegły stwierdził obecność śladów hamowania na odcinku 18 metrów."
    )

    fragmenty = podziel_wiele(dokumenty)
    assert len(fragmenty) > 100

    wybrane = wybierz(fragmenty, "Czy stwierdzono ślady hamowania?",
                      budzet_znakow=9000)

    assert sum(len(f.tresc) for f in wybrane) <= 9000 + 1400, (
        "Wybór przekroczył budżet kontekstu — model dostałby urwane akta."
    )
    assert any(f.dokument_id == "42" for f in wybrane), (
        "Wyszukiwarka nie znalazła jedynego dokumentu z odpowiedzią "
        "wśród stu — analiza opierałaby się na przypadkowych aktach."
    )


def test_wybor_dokumentow_do_analizy():
    dokumenty = {str(i): f"Rutynowa treść {i}." for i in range(50)}
    dokumenty["7"] = "Protokół oględzin miejsca zdarzenia drogowego."
    dokumenty["9"] = "Notatka o oględzinach pojazdu."

    trafne = dokumenty_trafne(podziel_wiele(dokumenty), "oględziny", ile=5)
    assert "7" in trafne and "9" in trafne
    assert len(trafne) <= 5


def test_budzet_respektowany_takze_przy_jednym_duzym_fragmencie():
    """Pierwszy fragment wchodzi zawsze, nawet gdy sam przekracza budżet."""
    fragmenty = podziel("1", "a.txt", "słowo " * 500)
    wybrane = wybierz(fragmenty, "słowo", budzet_znakow=100)
    assert len(wybrane) >= 1
