"""Bramka konfiguracji serwera modelu.

Powód istnienia opisany w panel/konfiguracja.py: naprawa wydajnościowa
dająca ~18x przyspieszenia została raz wykonana, opisana w raporcie
i po cichu cofnięta, bo żyła wyłącznie w historii powłoki.

Test sprawdza DWIE WARSTWY, bo każda z nich potrafi zawieść osobno:

  1. ŚRODOWISKO   — co zastanie serwer Ollamy przy następnym starcie
  2. SERWER ŻYWY  — na czym pracuje TERAZ

Rozjazd między nimi jest stanem normalnym i najbardziej mylącym:
zmienne czyta serwer przy starcie, więc ustawienie ich w otwartej
konsoli nie zmienia nic w procesie, który już działa. Dokładnie tak
naprawa „przepadła" poprzednim razem.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KORZEN / "panel"))

import konfiguracja  # noqa: E402

pytestmark = pytest.mark.konfiguracja


# ── warstwa 1: środowisko ────────────────────────────────────────────

def test_srodowisko_zgodne_z_wymaganiami():
    """Co zastanie serwer Ollamy przy następnym uruchomieniu."""
    problemy = konfiguracja.rozbiezne()
    if not problemy:
        return
    pytest.fail(
        konfiguracja.KOMUNIKAT_NAPRAWY
        + "\n  Rozbieżności:\n"
        + "\n".join(f"    - {p}" for p in problemy)
        + "\n",
        pytrace=False,
    )


def test_rozbiezne_wykrywa_regresje_z_sierpnia():
    """Test negatywny — bramka MUSI potrafić paść.

    Odtwarza dokładnie tę konfigurację, która wróciła po naprawie.
    Bez tego nie wiadomo, czy `test_srodowisko_zgodne_z_wymaganiami`
    przechodzi dlatego, że jest dobrze, czy dlatego, że nie potrafi
    wykryć niczego (docs/11-testy-i-bramki.md).
    """
    regresja = {
        "OLLAMA_NUM_PARALLEL": "8",
        "OLLAMA_NUM_GPU": "20",
        "OLLAMA_FLASH_ATTENTION": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
    }
    problemy = konfiguracja.rozbiezne(regresja)

    opis = " | ".join(problemy)
    assert "OLLAMA_NUM_PARALLEL" in opis, "nie wykryto ośmiu slotów"
    assert "OLLAMA_NUM_GPU" in opis, "nie wykryto ograniczenia warstw"
    assert "OLLAMA_KV_CACHE_TYPE" in opis, "nie wykryto braku kwantyzacji cache'u"


def test_konfiguracja_wzorcowa_przechodzi():
    """Odwrotna strona testu negatywnego: poprawne środowisko jest czyste."""
    assert konfiguracja.rozbiezne(dict(konfiguracja.WYMAGANE)) == []


# ── warstwa 2: serwer, który działa teraz ────────────────────────────

def test_serwer_pracuje_na_jednym_slocie():
    """Czy DZIAŁAJĄCY serwer faktycznie stosuje wymaganą konfigurację.

    Ta warstwa okazała się ważniejsza od sprawdzenia samych zmiennych.
    Pomiar z 14.08.2026: profil użytkownika miał już poprawne wartości
    (NUM_PARALLEL=1, KV_CACHE_TYPE=q8_0), a serwer Ollamy chodził od
    dwóch godzin ze starymi, odziedziczonymi przy starcie — i pracował
    na ośmiu slotach z cache'em f16.

    Sprawdzenie samych zmiennych mówiło „wszystko w porządku".
    """
    if konfiguracja.stan_serwera() is None:
        pytest.skip(
            "nie da się ustalić stanu serwera Ollamy (brak logu albo wpisu "
            "o wczytaniu modelu) — to nie jest wynik pozytywny"
        )

    problemy = konfiguracja.serwer_wymaga_restartu()
    if not problemy:
        return

    pytest.fail(
        konfiguracja.KOMUNIKAT_NAPRAWY
        + f"\n  Log: {konfiguracja.log_serwera()}\n"
        + "\n".join(f"    - {p}" for p in problemy)
        + "\n\n  Zmienne środowiskowe mogą być JUŻ POPRAWNE — serwer Ollamy\n"
          "  czyta je wyłącznie przy starcie. Wymagany restart serwera.\n",
        pytrace=False,
    )
