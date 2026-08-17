"""Strażnik adresu modelu — bramka I-6 dla KODU, KTÓRY WYSYŁAMY.

════════════════════════════════════════════════════════════════════════
 CZYM TO SIĘ RÓŻNI OD `tests/izolacja/test_straznik.py`
════════════════════════════════════════════════════════════════════════

Tamten plik testuje `src/opencontracts` — fork, którego nie wysyłamy —
i robi to na KOPII walidatora zdefiniowanej w samym pliku testu
(`test_straznik.py:32-55`). Sześć testów I-6/I-7 nie dotyka więc żadnego
uruchamianego kodu. Test badający własną kopię implementacji jest gorszy
od jego braku: daje zielony pasek i zero gwarancji.

Ten plik wywołuje `panel/siec.py`, czyli funkcję, przez którą faktycznie
przechodzi każdy adres modelu w produkcie.

⚠️ TO JEST OSTATNIA LINIA OBRONY OBIETNICY „AKTA NIE OPUSZCZAJĄ TEGO
   URZĄDZENIA". Jeśli te testy przestaną przechodzić, przestaje
   obowiązywać zdanie, na którym opiera się cała dokumentacja zgodności.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PANEL = Path(__file__).resolve().parents[1] / "panel"
sys.path.insert(0, str(PANEL))

import siec  # noqa: E402


# ── adresy, które MUSZĄ zostać odrzucone ────────────────────────────

@pytest.mark.parametrize("adres", [
    "http://api.openai.com",
    "http://api.anthropic.com:11434",
    "http://8.8.8.8:11434",
    "http://192.168.1.50:11434",          # sieć lokalna to NIE to urządzenie
    "http://10.0.0.5:11434",
    "http://model.kancelaria.local:11434",
    "https://127.0.0.1:11434",            # HTTPS poza zakresem
    "ftp://127.0.0.1:11434",
    "127.0.0.1:11434",                    # bez schematu
    "",
    "   ",
    # ⚠️ ZAPIS SKRÓCONY ODRZUCANY ŚWIADOMIE.
    # „127.1" jest dla systemu operacyjnego pętlą zwrotną, ale
    # `ipaddress` wymaga czterech oktetów. Nie rozluźniamy tego:
    # przy adresie modelu fałszywe odrzucenie kosztuje jeden komunikat
    # przy starcie, a fałszywe przyjęcie kosztuje wyciek akt.
    "http://127.1:11434",
])
def test_adres_spoza_petli_zwrotnej_odrzucony(adres):
    with pytest.raises(siec.BlednyAdresModelu):
        siec.waliduj(adres)


@pytest.mark.parametrize("adres", [
    "http://127.0.0.1@zly.host:11434",
    "http://localhost@example.com",
    "http://user:haslo@127.0.0.1.evil.com:11434",
])
def test_adres_udajacy_lokalny_przez_znak_at_odrzucony(adres):
    """Najgroźniejszy wariant: WYGLĄDA na lokalny, prowadzi na zewnątrz.

    Część przed `@` to dane logowania, nie host. Taki adres przechodzi
    wzrokowy przegląd kodu, bo zaczyna się od `127.0.0.1`.
    """
    with pytest.raises(siec.BlednyAdresModelu) as e:
        siec.waliduj(adres)
    assert "@" in str(e.value), (
        "komunikat ma nazwać przyczynę, żeby dało się ją zrozumieć")


@pytest.mark.parametrize("adres", [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11434/",
    "http://localhost:11434",
    "http://127.0.0.2:11434",             # cała 127.0.0.0/8 to pętla
    "http://[::1]:11434",
])
def test_adres_lokalny_przechodzi(adres):
    assert siec.waliduj(adres)


def test_adres_ze_sciezka_odrzucony():
    """Adres ma być hostem z portem — ścieżka sugeruje pomyłkę
    (np. wklejenie pełnego URL-a punktu końcowego)."""
    with pytest.raises(siec.BlednyAdresModelu):
        siec.waliduj("http://127.0.0.1:11434/api/generate")


# ── stan faktyczny produktu ─────────────────────────────────────────

def test_adres_modelu_wskazuje_petle_zwrotna():
    """To, co system faktycznie ma ustawione — nie tylko co potrafi."""
    assert siec.waliduj(siec.ADRES_MODELU) == siec.ADRES_MODELU


def test_nadpisanie_ze_srodowiska_przechodzi_walidacje(monkeypatch):
    """Zmienna środowiskowa jest dozwolona, ale nie omija strażnika.

    Bez tego konfiguracja byłaby drogą na skróty wokół całej bramki.
    """
    monkeypatch.setenv(siec.ZMIENNA, "http://api.openai.com")
    with pytest.raises(siec.BlednyAdresModelu):
        siec._z_otoczenia()

    monkeypatch.setenv(siec.ZMIENNA, "http://127.0.0.1:9999")
    assert siec._z_otoczenia() == "http://127.0.0.1:9999"


def test_moduly_korzystaja_ze_straznika():
    """Trzy moduły wywołujące model biorą adres z `siec`, nie własny."""
    import agent
    import analiza
    import kontrola

    for modul in (agent, analiza, kontrola):
        assert modul.OLLAMA == siec.ADRES_MODELU, (
            f"{modul.__name__} ma własny adres modelu — strażnik go nie "
            f"obejmuje")


# ── skan statyczny: żeby nikt nie dopisał drugiego adresu ───────────

# Adresy dozwolone w kodzie panelu poza `siec.py`. Lista jest krótka
# i każda pozycja ma uzasadnienie — rozszerzanie jej bez uzasadnienia
# rozbraja tę bramkę.
_DOZWOLONE_LITERALY = re.compile(
    # Panel nasłuchujący sam u siebie — to nie jest wyjście na zewnątrz.
    r"http://127\.0\.0\.1:8713"
    r"|http://localhost:8713"
    r"|http://\{HOST\}:\{PORT\}"          # ten sam adres w f-stringu
    # Przestrzenie nazw XML. To IDENTYFIKATORY, nie adresy do pobrania —
    # parser DOCX porównuje je jako napisy i nigdy pod nie nie sięga.
    r"|http://schemas\.openxmlformats\.org/"
    r"|http://schemas\.microsoft\.com/"
    r"|http://www\.w3\.org/")

_ADRES_W_KODZIE = re.compile(r"https?://[^\s\"'<>)\]]+")


def test_zaden_modul_panelu_nie_ma_wlasnego_adresu_modelu():
    """Bramka przed cichym obejściem strażnika.

    Ktoś dopisujący `urlopen("http://...")` obok `siec` nie złamie
    żadnego innego testu — ten ma go zatrzymać.

    Sprawdzamy WYŁĄCZNIE kod, nie komentarze i nie docstringi: adresy
    w opisach są potrzebne i nieszkodliwe.
    """
    naruszenia: list[str] = []

    for plik in sorted(PANEL.glob("*.py")):
        if plik.name == "siec.py":
            continue
        for nr, linia in enumerate(
                plik.read_text(encoding="utf-8").splitlines(), 1):
            kod = linia.split("#", 1)[0]
            if '"""' in kod or "'''" in kod:
                continue
            for trafienie in _ADRES_W_KODZIE.findall(kod):
                if _DOZWOLONE_LITERALY.match(trafienie):
                    continue
                naruszenia.append(f"{plik.name}:{nr}: {trafienie}")

    assert not naruszenia, (
        "Adres sieciowy w kodzie panelu z pominięciem `siec.py`:\n  "
        + "\n  ".join(naruszenia)
        + "\n\nKażde wyjście sieciowe musi przechodzić przez strażnika "
          "(`panel/siec.py`), inaczej bramka izolacji go nie obejmuje.")
