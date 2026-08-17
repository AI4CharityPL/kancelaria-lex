"""Wpięcie kontroli w potok — przełączniki, tryb cienia, adnotacje.

PO CO OSOBNY PLIK

`test_wsparcie.py` i `test_kontrola.py` sprawdzają, czy obie warstwy
dobrze OCENIAJĄ. Tu sprawdzamy rzecz inną i — jak pokazała ta sesja —
łatwiejszą do przeoczenia: czy są **wpięte tam, gdzie mają być, i tak
samo w obu torach**.

Usterka, którą te testy zamykają, wyglądała tak:

    agent._sprawdz_wsparcie          za przełącznikami → kontrola WYŁĄCZONA
    analiza._sprawdz_wsparcie_ustalen bezwarunkowo      → kontrola WŁĄCZONA

Benchmark odpytuje tor szybki, panel prawnika chodzi torem analizy.
Mierzono więc jeden układ, a pracowano na drugim — i żaden test tego
nie widział, bo każda warstwa z osobna działała poprawnie.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import agent  # noqa: E402
import analiza  # noqa: E402
import kontrola as mod_kontrola  # noqa: E402
import wsparcie as mod_wsparcie  # noqa: E402
from agenci.weryfikator_cytatow import Cytat, Twierdzenie  # noqa: E402


ZDANIE = "Sąd oddalił wniosek obrońcy o dopuszczenie dowodu z opinii biegłego."


def _twierdzenie(tekst: str, fragment: str = ZDANIE) -> Twierdzenie:
    return Twierdzenie(tekst, [Cytat("1", 0, len(fragment), fragment)])


@pytest.fixture
def przelaczniki():
    """Przywraca stan przełączników po każdym teście.

    Bez tego test zostawiający włączoną kontrolę zmieniałby wynik
    kolejnych — a to ta klasa błędu, przez którą w tej sesji cztery razy
    porównano przebiegi wykonane w różnych układach.
    """
    stan = (agent.KONTROLA_MECHANICZNA, agent.KONTROLA_MODELEM,
            agent.KONTROLA_CIEN)
    yield
    (agent.KONTROLA_MECHANICZNA, agent.KONTROLA_MODELEM,
     agent.KONTROLA_CIEN) = stan


# ── przełączniki działają w OBU torach tak samo ──────────────────────

def test_wylaczona_kontrola_nie_rusza_twierdzen(przelaczniki):
    agent.KONTROLA_MECHANICZNA = False
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = False

    t = [_twierdzenie("cokolwiek, czego w zdaniu nie ma: 999 999 zł")]
    zostaje, odrzucone, adnotacje = agent._sprawdz_wsparcie(t, "pytanie")

    assert zostaje == t
    assert odrzucone == []
    assert adnotacje == {}


def test_tor_analizy_slucha_tych_samych_przelacznikow(przelaczniki, monkeypatch):
    """⚠️ TEST NA USTERKĘ, KTÓRA ROZJECHAŁA POMIAR Z PRODUKCJĄ.

    Gdyby tor analizy znów zaczął wołać kontrolę bezwarunkowo, ten test
    padnie — bo przy wyłączonych przełącznikach nie wolno mu wywołać
    modelu ani odrzucić ustalenia.
    """
    agent.KONTROLA_MECHANICZNA = False
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = False

    def nie_wolno(*_a, **_k):                       # pragma: no cover
        raise AssertionError(
            "Tor analizy wywołał kontrolę modelem przy wyłączonym "
            "przełączniku — pomiar przestałby opisywać produkcję.")

    monkeypatch.setattr(mod_kontrola, "sprawdz", nie_wolno)

    wynik = analiza.WynikAnalizy(pytanie="p")
    ustalenia = [analiza.Ustalenie(
        tekst="twierdzenie powołujące 999 999 zł, których w zdaniu nie ma",
        dokument="dok", cytaty=[{"dokument_id": "1", "poczatek": 0,
                                 "koniec": len(ZDANIE), "fragment": ZDANIE}])]

    zostaje = analiza._sprawdz_wsparcie_ustalen(ustalenia, wynik, "pytanie")

    assert zostaje == ustalenia
    assert wynik.odrzucone == []


def test_tor_analizy_przekazuje_kontekst_pytania(przelaczniki, monkeypatch):
    """Wyróżnik z PYTANIA nie może być liczony przeciwko odpowiedzi.

    Tor szybki dostał tę poprawkę 14.08.2026, tor analizy nie — przez co
    ta sama poprawna odpowiedź przechodziła w czacie i odpadała
    w analizie. Test pilnuje, że `kontekst_znany` faktycznie dojeżdża
    do `wsparcie.oszacuj`, a nie tylko stoi w sygnaturze.
    """
    agent.KONTROLA_MECHANICZNA = True
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = False

    widziane: dict = {}
    prawdziwe = mod_wsparcie.oszacuj

    def podglad(tekst, cytaty, jezyk=None, kontekst_znany=""):
        widziane["kontekst"] = kontekst_znany
        return prawdziwe(tekst, cytaty, jezyk, kontekst_znany)

    monkeypatch.setattr(mod_wsparcie, "oszacuj", podglad)

    wynik = analiza.WynikAnalizy(pytanie="p")
    ustalenia = [analiza.Ustalenie(
        tekst="Sąd oddalił wniosek 14 września 2006 r.",
        dokument="dok", cytaty=[{"dokument_id": "1", "poczatek": 0,
                                 "koniec": len(ZDANIE), "fragment": ZDANIE}])]

    analiza._sprawdz_wsparcie_ustalen(
        ustalenia, wynik, "Co wydarzyło się 14 września 2006 r.?")

    assert widziane["kontekst"] == "Co wydarzyło się 14 września 2006 r.?"


# ── tryb cienia ──────────────────────────────────────────────────────

def test_cien_nie_odrzuca_niczego(przelaczniki, monkeypatch):
    """⚠️ WŁASNOŚĆ, BEZ KTÓREJ TRYB CIENIA BYŁBY GROŹNY.

    Cień istnieje po to, żeby JEDEN przebieg dał wynik z kontrolą i bez.
    Gdyby przy okazji odrzucał, mierzyłby układ z kontrolą i podawał go
    za układ bez — czyli dokładnie to zafałszowanie, któremu ma zapobiec.
    """
    agent.KONTROLA_MECHANICZNA = False
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = True

    monkeypatch.setattr(
        mod_kontrola, "sprawdz",
        lambda *_a, **_k: mod_kontrola.Wynik(mod_kontrola.Werdykt.FALSZ,
                                             "test"))

    t = [_twierdzenie("Sąd uwzględnił wniosek obrońcy.")]
    zostaje, odrzucone, adnotacje = agent._sprawdz_wsparcie(t, "pytanie")

    assert zostaje == t, "cień odrzucił twierdzenie — to nie jest cień"
    assert odrzucone == []
    assert adnotacje[id(t[0])]["_kontrola_cien"] == "kontrola_falsz"


def test_cien_oznacza_takze_brak_wsparcia(przelaczniki):
    """Odpadnięcie na warstwie mechanicznej też musi być policzone.

    Inaczej pomiar pokazywałby wyłącznie zysk z kontroli modelem
    i pomijał tańszą warstwę, która odrzuca więcej.
    """
    agent.KONTROLA_MECHANICZNA = False
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = True

    t = [_twierdzenie("Sąd zasądził 1 250 000 zł tytułem odszkodowania.")]
    zostaje, odrzucone, adnotacje = agent._sprawdz_wsparcie(t, "pytanie")

    assert zostaje == t
    assert odrzucone == []
    assert adnotacje[id(t[0])]["_kontrola_cien"] == "wsparcie_brak"


def test_kontrola_wlaczona_ma_pierwszenstwo_przed_cieniem(przelaczniki, monkeypatch):
    """Gdy kontrola działa na serio, cień nie ma czego udawać."""
    agent.KONTROLA_MECHANICZNA = True
    agent.KONTROLA_MODELEM = True
    agent.KONTROLA_CIEN = True

    monkeypatch.setattr(
        mod_kontrola, "sprawdz",
        lambda *_a, **_k: mod_kontrola.Wynik(mod_kontrola.Werdykt.FALSZ,
                                             "test"))

    t = [_twierdzenie("Sąd uwzględnił wniosek obrońcy.")]
    zostaje, odrzucone, _ = agent._sprawdz_wsparcie(t, "pytanie")

    assert zostaje == []
    assert odrzucone[0]["powod"] == "odrzucony_kontrola_niezalezna"


# ── adnotacje, na których stoi interfejs ─────────────────────────────

def test_adnotacje_niosa_pola_wymagane_przez_panel(przelaczniki):
    """Panel rysuje znacznik z `stopien`/`pokrycie`/`kontrola`.

    Zmiana nazwy któregoś pola nie wywaliłaby niczego po stronie
    Pythona — znacznik po prostu przestałby się pokazywać, cicho.
    """
    agent.KONTROLA_MECHANICZNA = True
    agent.KONTROLA_MODELEM = False
    agent.KONTROLA_CIEN = False

    t = [_twierdzenie("Sąd oddalił wniosek obrońcy.")]
    zostaje, _, adnotacje = agent._sprawdz_wsparcie(t, "Co sąd zrobił?")

    assert zostaje, "twierdzenie wierne cytatowi nie powinno odpaść"
    a = adnotacje[id(t[0])]
    assert a["stopien"] in ("mocne", "slabe")
    assert isinstance(a["pokrycie"], float)
