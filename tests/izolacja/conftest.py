"""Wspólne narzędzia dla testów izolacji.

Zasada nadrzędna (docs/11-testy-i-bramki.md):
test bezpieczeństwa, który przechodzi zawsze, jest GORSZY niż brak testu.

Dlatego brak działającego Dockera nie daje wyniku "zaliczone" — daje
błąd z jednoznacznym komunikatem. Skorzystanie z --dozwol-pominiecie
jest świadomą decyzją operatora, odnotowaną w wyniku przebiegu.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[2]
COMPOSE = KORZEN / "infra" / "compose" / "compose.yml"


# ══════════════════════════════════════════════════════════════════════
#  ŚWIADOME POMINIĘCIE — DOSTĘP DLA FUNKCJI POMOCNICZYCH, 17.08.2026.
#
#  `--dozwol-pominiecie` dało się dotąd odczytać wyłącznie tam, gdzie
#  jest `request` (patrz test_warunki_wstepne.py). Bramki I-1…I-3 pytają
#  o obecność forka ze zwykłej funkcji, więc flagi nie widziały i przy
#  braku forka kończyły się BŁĘDEM ZAWSZE.
#
#  Na maszynie docelowej to jest zachowanie prawidłowe i zostaje: fork
#  ma tam być, a jego brak nie może uchodzić za wynik pozytywny. Ale
#  `src/opencontracts/` jest z założenia poza repozytorium (klonowany,
#  nie wersjonowany), więc w CI te bramki nie mogły być zielone NIGDY.
#  Bramka, która nie może przejść, przestaje nieść informację — ludzie
#  uczą się ignorować jej czerwień, a razem z nią wszystkie pozostałe.
#
#  Rozwiązanie zachowuje zasadę: BEZ flagi nadal błąd, z flagą —
#  pominięcie widoczne w podsumowaniu przebiegu jako `skipped`, nigdy
#  jako `passed`. Domyślnie zamknięte: gdy konfiguracji nie da się
#  odczytać, zwracamy False, czyli bramka pozostaje wymagająca.
# ══════════════════════════════════════════════════════════════════════
_KONFIGURACJA: pytest.Config | None = None


def pytest_configure(config: pytest.Config) -> None:
    global _KONFIGURACJA
    _KONFIGURACJA = config


def wolno_pominac() -> bool:
    """Czy operator świadomie zgodził się na pominięcie bramki."""
    if _KONFIGURACJA is None:
        return False
    return bool(_KONFIGURACJA.getoption("--dozwol-pominiecie", default=False))

# Kontenery, które muszą być odcięte od świata zewnętrznego.
# traefik i frontend są w net_edge — obsługują LAN kancelarii,
# więc nie podlegają testom egresu w ten sam sposób.
KONTENERY_ODCIETE = [
    "django",
    "celeryworker",
    "celerybeat",
    "flower",
    "postgres",
    "redis",
    "minio",
    "ollama",
    "embedder",
    "docling",
    "gotenberg",
    "docxodus",
    "privacy_filter",
]

# Pakiety, których obecność w obrazie oznacza utratę warstwy A izolacji.
# UWAGA: "openai" NIE jest na tej liście — jest transportem do lokalnej
# Ollamy (ustalenie U-1, ADR-0003). Usunięcie go zepsułoby model lokalny.
PAKIETY_ZAKAZANE = [
    "anthropic",
    "google-genai",
    "google-generativeai",
    "google-cloud-aiplatform",
    "posthog",
    "mcp",
    "cohere",
    "litellm",
]

# Adresy używane do sprawdzenia, czy kontener wychodzi na zewnątrz.
# Adresy IP wprost — z pominięciem DNS, żeby test nie mylił braku
# rozwiązywania nazw z brakiem trasy.
CELE_TCP = [
    ("1.1.1.1", 443),
    ("8.8.8.8", 53),
    ("140.82.121.4", 443),   # github.com
]

NAZWY_DNS = ["api.openai.com", "api.anthropic.com", "github.com"]


# `pytest_addoption` przeniesione do tests/conftest.py — pytest przyjmuje
# je wyłącznie z conftestu początkowego. Tutaj rejestrowało się dopiero
# przy zbieraniu testów, więc opcji nie dało się podać w wierszu poleceń,
# choć dokumentacja i komunikat bramki kazały to robić.


def pytest_collection_modifyitems(items):
    """Nadaje znacznik `izolacja` wszystkiemu w tym katalogu.

    ⚠️ Znacznik był zadeklarowany w pytest.ini i opisany jako „bramki
    izolacji (I-1…I-9)", ale nie nosił go ANI JEDEN test. Skutki były
    dwa i oba ciche:

      pytest -m izolacja          zbierał zero testów i kończył się
                                  kodem 5 — przebieg „bramek izolacji"
                                  nie sprawdzał niczego
      pytest -m "not izolacja"    nie wykluczał niczego, więc bramki
                                  wymagające Dockera wchodziły do
                                  szybkiego przebiegu jednostkowego

    Znacznik nadawany katalogiem, a nie ręcznie w każdym pliku, bo test
    izolacji dopisany w przyszłości ma go dostać sam z siebie. Bramka,
    o której trzeba pamiętać, prędzej czy później zostanie pominięta.
    """
    katalog = Path(__file__).resolve().parent
    for item in items:
        sciezka = Path(str(item.fspath)).resolve()
        if sciezka.parent == katalog:
            item.add_marker(pytest.mark.izolacja)


def docker_dostepny() -> bool:
    try:
        wynik = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, timeout=15,
        )
        return wynik.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


KOMUNIKAT_BRAK_DOCKERA = (
    "\n"
    "═══════════════════════════════════════════════════════════════\n"
    "  DEMON DOCKERA NIE DZIAŁA — IZOLACJA SIECIOWA NIESPRAWDZONA\n"
    "═══════════════════════════════════════════════════════════════\n"
    "  Bramki I-3, I-4, I-5 NIE zostały wykonane. Pominięte testy\n"
    "  izolacji NIE są testami zaliczonymi.\n"
    "\n"
    "  Uruchom Docker Desktop, postaw stos i powtórz przebieg:\n"
    "    docker compose -f infra/compose/compose.yml up -d\n"
    "\n"
    "  Świadome pominięcie: pytest --dozwol-pominiecie\n"
    "═══════════════════════════════════════════════════════════════\n"
)


@pytest.fixture(scope="session")
def docker():
    """Testy egresu wymagają Dockera.

    Fixture POMIJA, żeby nie zasypać wyniku osiemdziesięcioma
    identycznymi błędami. Czerwony sygnał daje pojedynczy, celowo
    głośny test `test_docker_dostepny_dla_bramek_izolacji` — build
    i tak jest czerwony, ale komunikat da się przeczytać.
    """
    if not docker_dostepny():
        pytest.skip("brak Dockera — patrz test_docker_dostepny_dla_bramek_izolacji")
    return True


def w_kontenerze(nazwa: str, polecenie: list[str], timeout: int = 20):
    """Uruchamia polecenie w kontenerze. Zwraca CompletedProcess."""
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "exec", "-T", nazwa, *polecenie],
        capture_output=True, timeout=timeout, text=True,
    )


def kontener_dziala(nazwa: str) -> bool:
    wynik = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "ps", "--format", "json", nazwa],
        capture_output=True, text=True, timeout=15,
    )
    if wynik.returncode != 0 or not wynik.stdout.strip():
        return False
    for linia in wynik.stdout.strip().splitlines():
        try:
            if json.loads(linia).get("State") == "running":
                return True
        except json.JSONDecodeError:
            continue
    return False
