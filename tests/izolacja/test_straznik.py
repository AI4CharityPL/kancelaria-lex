"""Bramki I-6 i I-7 — warstwa B izolacji (proces).

Odpowiedź na ustalenia U-1 i U-2:

  U-1  Ollama jedzie przez OpenAIProvider, a kod SAM podstawia atrapę
       klucza. Teza "bez klucza ścieżka jest niedostępna" jest fałszywa.
       Punktem kontroli musi być ADRES, nie klucz.

  U-2  Poświadczenia mogą mieszkać w bazie (PipelineSettings), z regułą
       "baza wygrywa nad zmienną środowiskową". Czysty .env nie wystarcza
       — potrzebna blokada także na zapisie do modelu.

Referencyjna implementacja walidatora znajduje się poniżej, żeby logikę
dało się testować bez uruchamiania Django. Patch 03-straznik-adresow
używa tej samej funkcji.

════════════════════════════════════════════════════════════════════════
 ⚠️ CO TEN PLIK SPRAWDZA, A CZEGO NIE — DOPISANE 16.08.2026
════════════════════════════════════════════════════════════════════════

Ten plik testuje **kopię referencyjną** walidatora, zdefiniowaną niżej
w tym samym pliku — a nie kod uruchamiany w produkcji. Sprawdza więc,
że REGUŁA jest spójna, i nic ponadto. Gdyby ktoś usunął strażnika
z forka, wszystkie testy poniżej nadal byłyby zielone.

Jest to świadomy kompromis: kod forka jest aplikacją Django i jego
import wymagałby postawienia całego środowiska. Obecność strażnika
w prawdziwym pliku forka pilnuje osobny test, przez wyszukanie ciągów
znaków: `test_czystosc_builda.py::test_i3_straznik_adresow_obecny_w_forku`.

⚠️ NIE JEST TO BRAMKA DLA PRODUKTU, KTÓRY WYSYŁAMY.
   Produktem jest `panel/`, nie fork. Strażnik panelu — wywoływany
   przy każdym imporcie i zatrzymujący proces przy złym adresie —
   znajduje się w `panel/siec.py`, a jego bramka w:

       tests/test_straznik_panelu.py

   Tamten plik wywołuje kod produkcyjny, w tym skan statyczny
   pilnujący, żeby nikt nie dopisał drugiego adresu obok strażnika.
   Do 16.08.2026 taka bramka nie istniała: obietnica „akta nie
   opuszczają tego urządzenia" nie miała w produkcie żadnego
   mechanizmu egzekwującego.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest


DOZWOLONE = ["http://ollama:11434/v1", "http://embedder:8000"]


class BlednyAdresModelu(Exception):
    """Podnoszony przy adresie spoza allowlisty. Zatrzymuje proces."""


def waliduj_base_url(adres: str | None, dozwolone: list[str] = None) -> str:
    """Zwraca adres, jeśli należy do allowlisty. Inaczej podnosi wyjątek.

    Porównanie po (schemat, host, port) — a nie po całym ciągu — żeby
    końcowy ukośnik albo dopisana ścieżka nie omijały kontroli.
    """
    dozwolone = DOZWOLONE if dozwolone is None else dozwolone

    if not adres:
        raise BlednyAdresModelu("Adres modelu nie został ustawiony.")

    def klucz(u: str):
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            raise BlednyAdresModelu(f"Niedozwolony schemat: {p.scheme!r}")
        return (p.scheme, p.hostname, p.port)

    biezacy = klucz(adres)
    if biezacy not in {klucz(d) for d in dozwolone}:
        raise BlednyAdresModelu(
            f"Adres {adres!r} jest spoza allowlisty. Proces nie zostanie "
            f"uruchomiony. Dozwolone: {dozwolone}. Patrz ADR-0003."
        )
    return adres


# ── I-6 · strażnik startowy ────────────────────────────────────────

@pytest.mark.parametrize("adres", DOZWOLONE)
def test_i6_adresy_lokalne_przechodza(adres):
    assert waliduj_base_url(adres) == adres


def test_i6_koncowy_ukosnik_nie_omija_kontroli():
    assert waliduj_base_url("http://ollama:11434/v1/")


@pytest.mark.parametrize("adres", [
    "https://api.openai.com/v1",
    "https://api.anthropic.com",
    "https://generativelanguage.googleapis.com/v1beta",
    "http://ollama.evil.example/v1",        # host podobny, ale inny
    "http://ollama:11434@evil.example/v1",  # host w części user-info
    "http://127.0.0.1:11434/v1",            # nawet lokalny, ale spoza listy
    "file:///etc/passwd",
    "",
    None,
])
def test_i6_adresy_zewnetrzne_zatrzymuja_proces(adres):
    """Adres spoza allowlisty MUSI zatrzymać start — nie ostrzec.

    Wybór twardego zatrzymania zamiast ostrzeżenia jest świadomy:
    system, który przy błędnej konfiguracji działa dalej i loguje
    ostrzeżenie, będzie działał dalej. Ostrzeżeń nikt nie czyta.
    """
    with pytest.raises(BlednyAdresModelu):
        waliduj_base_url(adres)


def test_i6_klucz_api_nie_jest_zabezpieczeniem():
    """U-1 — dokumentacja wykonywalna.

    Kod upstreamu podstawia atrapę klucza "ollama", gdy klucza brak.
    Brak klucza NIE blokuje więc żadnej ścieżki. Ten test utrwala
    wniosek: liczy się adres.
    """
    with pytest.raises(BlednyAdresModelu):
        waliduj_base_url("https://api.openai.com/v1")   # bez klucza — i tak nie wolno

    assert waliduj_base_url("http://ollama:11434/v1")   # z atrapą klucza — wolno


# ── I-7 · blokada zapisu do bazy ───────────────────────────────────

class RejestrAudytu:
    def __init__(self):
        self.wpisy: list[dict] = []

    def zapisz(self, **dane):
        self.wpisy.append(dane)


def symuluj_zapis_pipeline_settings(adres, uzytkownik, audyt: RejestrAudytu):
    """Odpowiednik sygnału pre_save z patcha 03-straznik-adresow."""
    try:
        return waliduj_base_url(adres)
    except BlednyAdresModelu:
        audyt.zapisz(
            zdarzenie="odrzucono_zapis_base_url",
            adres=adres,
            uzytkownik=uzytkownik,
        )
        raise


def test_i7_zapis_do_bazy_odrzucony_i_zalogowany():
    """U-2 · sama czystość .env nie wystarcza.

    Osoba z dostępem do panelu administracyjnego mogłaby skierować
    model na zewnątrz, nie dotykając żadnego pliku — bo baza wygrywa
    nad zmienną środowiskową.
    """
    audyt = RejestrAudytu()

    with pytest.raises(BlednyAdresModelu):
        symuluj_zapis_pipeline_settings(
            "https://api.openai.com/v1", uzytkownik="admin", audyt=audyt
        )

    assert len(audyt.wpisy) == 1, (
        "Próba zapisu adresu zewnętrznego nie trafiła do logu audytowego. "
        "Odrzucenie bez śladu nie pozwala wykryć, że ktoś próbował."
    )
    assert audyt.wpisy[0]["uzytkownik"] == "admin"
    assert audyt.wpisy[0]["adres"] == "https://api.openai.com/v1"


def test_i7_zapis_dozwolony_nie_zasmieca_audytu():
    audyt = RejestrAudytu()
    symuluj_zapis_pipeline_settings(
        "http://ollama:11434/v1", uzytkownik="admin", audyt=audyt
    )
    assert audyt.wpisy == []
