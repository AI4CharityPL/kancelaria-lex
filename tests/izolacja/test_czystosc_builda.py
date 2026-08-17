"""Bramka I-1 i I-8 — warstwa A izolacji (build).

Te testy NIE wymagają Dockera i działają od razu. To najtańsza
i najskuteczniejsza bariera w całym projekcie.

Chronią przed najbardziej prawdopodobnym trybem awarii (ryzyko RY-03):
za pół roku ktoś robi rutynowy merge z upstreamem, wraca
    pydantic-ai-slim[openai,anthropic,google,mcp]
i nikt tego nie zauważa aż do incydentu.

Z tą bramką — build pada tego samego dnia.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import KORZEN, COMPOSE, PAKIETY_ZAKAZANE, wolno_pominac

ZRODLA = KORZEN / "src" / "opencontracts"


def _pliki_zaleznosci() -> list[Path]:
    wzorce = ["requirements*.txt", "requirements/*.txt",
              "pyproject.toml", "poetry.lock", "uv.lock"]
    znalezione: list[Path] = []
    for wzorzec in wzorce:
        znalezione.extend(ZRODLA.glob(wzorzec))
    return znalezione


def _wymagaj_zrodel():
    if ZRODLA.exists():
        return

    # Fork jest klonowany, nie wersjonowany (patrz .gitignore), więc na
    # maszynie budującej z samego repozytorium go nie ma. Pominięcie jest
    # dopuszczalne WYŁĄCZNIE na wyraźne żądanie i widać je w podsumowaniu
    # jako `skipped` — nigdy jako `passed`.
    if wolno_pominac():
        pytest.skip(
            f"Brak forka w {ZRODLA} — bramka NIE została sprawdzona. "
            "Pominięcie świadome (--dozwol-pominiecie). Warstwa A izolacji "
            "pozostaje niezweryfikowana w tym przebiegu."
        )

    pytest.fail(
        f"\nBrak forka w {ZRODLA}.\n"
        "Bramka I-1 nie mogła zostać sprawdzona — to NIE jest wynik\n"
        "pozytywny. Wykonaj krok 3 z docs/10-operacje/runbook-wdrozenie.md.\n"
        "Świadome pominięcie: pytest --dozwol-pominiecie",
        pytrace=False,
    )


@pytest.mark.parametrize("pakiet", PAKIETY_ZAKAZANE)
def test_i1_brak_zakazanych_pakietow(pakiet: str):
    """I-1 · SDK dostawców chmurowych, telemetria i MCP poza obrazem."""
    _wymagaj_zrodel()
    pliki = _pliki_zaleznosci()
    assert pliki, f"Nie znaleziono plików zależności w {ZRODLA}"

    # Granica słowa, żeby "mcp" nie łapało "mcpower", a "anthropic"
    # łapało też ekstras w nawiasach kwadratowych.
    wzorzec = re.compile(rf"(?<![\w-]){re.escape(pakiet)}(?![\w-])", re.IGNORECASE)

    trafienia = []
    for plik in pliki:
        for nr, linia in enumerate(plik.read_text(encoding="utf-8",
                                                  errors="ignore").splitlines(), 1):
            bez_komentarza = linia.split("#", 1)[0]
            if wzorzec.search(bez_komentarza):
                trafienia.append(f"  {plik.relative_to(KORZEN)}:{nr}  {linia.strip()}")

    assert not trafienia, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  WARSTWA A IZOLACJI NARUSZONA — pakiet '{pakiet}'\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        + "\n".join(trafienia)
        + "\n\nPrawdopodobna przyczyna: merge z upstreamem cofnął patch\n"
          "01-usun-sdk-chmurowe. Patrz ADR-0003 i ryzyko RY-03.\n"
    )


def test_i1_openai_pozostaje():
    """I-1 (odwrotnie) · pakiet 'openai' MUSI zostać.

    Wbrew intuicji: Ollama jest routowana przez OpenAIProvider, bo
    wystawia API zgodne z OpenAI (ustalenie U-1). Usunięcie pakietu
    zepsułoby model lokalny.

    Punktem kontroli jest ADRES, nie klucz — patrz test_straznik.py.
    """
    _wymagaj_zrodel()
    tresc = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in _pliki_zaleznosci()
    )
    assert re.search(r"(?<![\w-])openai(?![\w-])", tresc, re.IGNORECASE), (
        "\nPakiet 'openai' zniknął z zależności.\n"
        "To NIE jest poprawka bezpieczeństwa — to awaria: Ollama jedzie\n"
        "przez OpenAIProvider (U-1). Model lokalny przestanie działać.\n"
    )


def test_i8_obrazy_przypiete_po_sha256():
    """I-8 · każdy obraz w compose przypięty po sumie, nie po tagu.

    Ustalenie U-5: upstream używa tagów ':latest' z prywatnych
    przestrzeni rejestru. Treść takiego obrazu może się zmienić
    między jednym pobraniem a drugim, bez śladu w repozytorium.
    """
    assert COMPOSE.exists(), f"Brak {COMPOSE}"

    nieprzypiete = []
    for nr, linia in enumerate(COMPOSE.read_text(encoding="utf-8").splitlines(), 1):
        bez_komentarza = linia.split("#", 1)[0]
        dopasowanie = re.match(r"\s*image:\s*(\S+)", bez_komentarza)
        if dopasowanie and "@sha256:" not in dopasowanie.group(1):
            nieprzypiete.append(f"  linia {nr}: {dopasowanie.group(1)}")

    assert not nieprzypiete, (
        "\n\n╔══════════════════════════════════════════════════════════╗\n"
        "║  OBRAZY NIEPRZYPIĘTE — łańcuch dostaw niezabezpieczony    ║\n"
        "╚══════════════════════════════════════════════════════════╝\n"
        + "\n".join(nieprzypiete)
        + "\n\nUruchom: bash skrypty/pobierz-digesty.sh\n"
          "Patrz U-5 w docs/05-izolacja-i-siec.md.\n"
    )


def test_i2_brak_routingu_mcp():
    """I-2 · serwer MCP usunięty z routingu (nie tylko wyłączony).

    ⚠️ HISTORIA TEJ BRAMKI — warta zapamiętania.

    Pierwsza wersja testu przeszukiwała wyłącznie `urls.py`. Weryfikacja
    forka wykazała, że routing MCP siedzi w `config/asgi.py` i dispatchuje
    ścieżki /mcp, /mcp/*, /sse, /sse/* do osobnej aplikacji ASGI PRZED
    Django. Bramka przechodziłaby więc przy w pełni żywym serwerze MCP.

    Dokładnie ten tryb awarii opisuje docs/11-testy-i-bramki.md: test
    bezpieczeństwa, który nie potrafi paść, jest gorszy niż jego brak.

    Dodatkowo warto wiedzieć, że MCP_SERVER["enabled"]=False NIE
    wyłączało routingu — router powstawał przy imporcie modułu.
    """
    _wymagaj_zrodel()

    pliki = list(ZRODLA.rglob("urls.py")) + list(ZRODLA.rglob("asgi.py"))
    assert pliki, "Nie znaleziono ani urls.py, ani asgi.py — sprawdź ścieżkę forka"

    # Aktywne (niezakomentowane) odwołania do ścieżek MCP/SSE
    # oraz do modułu serwera MCP.
    wzorce = [
        re.compile(r"[\"']/?mcp[/\"']", re.IGNORECASE),
        re.compile(r"[\"']/?sse[/\"']", re.IGNORECASE),
        re.compile(r"\bmcp_asgi_app\b"),
        re.compile(r"from\s+opencontractserver\.mcp\b"),
    ]

    trafienia = []
    for plik in pliki:
        for nr, linia in enumerate(plik.read_text(encoding="utf-8",
                                                  errors="ignore").splitlines(), 1):
            bez_komentarza = linia.split("#", 1)[0]
            if not bez_komentarza.strip():
                continue
            if any(w.search(bez_komentarza) for w in wzorce):
                trafienia.append(f"  {plik.relative_to(KORZEN)}:{nr}  {linia.strip()}")

    assert not trafienia, (
        "\n\n╔══════════════════════════════════════════════════════════╗\n"
        "║  ROUTING MCP NADAL AKTYWNY — instancja nie jest samodzielna║\n"
        "╚══════════════════════════════════════════════════════════╝\n"
        + "\n".join(trafienia)
        + "\n\nZagrożenie I-4. Patrz patch 02 w src/patche/.\n"
          "Uwaga: sprawdź TAKŻE asgi.py, nie tylko urls.py.\n"
    )


def test_i2_modul_mcp_usuniety_z_drzewa():
    """I-2b · moduł serwera MCP i aplikacja discovery NIE ISTNIEJĄ.

    Sprawdzenie nieobecności modułu jest ściśle mocniejsze niż
    sprawdzanie importów: nie da się zaimportować czegoś, czego nie ma,
    ani odkomentować kodu, który został usunięty.

    `discovery` wypada razem z MCP — publikowała `.well-known/mcp.json`
    i `llms.txt` z gotowym fragmentem konfiguracji dla Claude Desktop,
    czyli aktywnie ogłaszała instancję agentom.
    """
    _wymagaj_zrodel()

    zakazane_moduly = [
        ZRODLA / "opencontractserver" / "mcp",
        ZRODLA / "opencontractserver" / "discovery",
    ]
    istniejace = [m for m in zakazane_moduly if m.exists()]

    assert not istniejace, (
        "\n\n╔══════════════════════════════════════════════════════════╗\n"
        "║  MODUŁ MCP / DISCOVERY OBECNY W DRZEWIE                    ║\n"
        "╚══════════════════════════════════════════════════════════╝\n"
        + "\n".join(f"  {m.relative_to(KORZEN)}" for m in istniejace)
        + "\n\nWyłączenie konfiguracją nie wystarcza — patch 02 usuwa moduły.\n"
    )


def test_i2_brak_importow_mcp_w_kodzie_produkcyjnym():
    """I-2c · żaden moduł produkcyjny nie importuje MCP ani discovery.

    Zakres celowo pomija katalogi testowe upstreamu: nie trafiają do
    obrazu produkcyjnego, a po usunięciu modułów i tak nie mogą się
    wykonać. Gwarancję daje test wyżej (moduł nie istnieje) — ten
    pilnuje, żeby nikt nie dopisał importu w kodzie, który jedzie
    na produkcję.
    """
    _wymagaj_zrodel()
    wzorzec = re.compile(
        r"^\s*(from|import)\s+opencontractserver\.(mcp|discovery)\b"
    )

    trafienia = []
    for plik in ZRODLA.rglob("*.py"):
        sciezka = plik.as_posix()
        if "/tests/" in sciezka or plik.name.startswith("test_"):
            continue
        for nr, linia in enumerate(plik.read_text(encoding="utf-8",
                                                  errors="ignore").splitlines(), 1):
            if wzorzec.search(linia.split("#", 1)[0]):
                trafienia.append(f"  {plik.relative_to(KORZEN)}:{nr}  {linia.strip()}")

    assert not trafienia, (
        "\nKod produkcyjny wciąż importuje MCP/discovery:\n" + "\n".join(trafienia)
    )


def test_i3_straznik_adresow_obecny_w_forku():
    """I-3b · patch 03 nałożony — strażnik adresów jest w fabryce modeli.

    Bez tego testu merge z upstreamem mógłby cicho przywrócić oryginalny
    `model_factory.py` i usunąć allowlistę, nie ruszając żadnego pliku
    z listy zakazanych pakietów.
    """
    _wymagaj_zrodel()
    fabryka = ZRODLA / "opencontractserver" / "llms" / "model_factory.py"
    assert fabryka.exists(), f"Brak {fabryka}"

    tresc = fabryka.read_text(encoding="utf-8", errors="ignore")

    for wymagany in ("_waliduj_base_url_lex", "LexBlednyAdresModelu",
                     "LEX_DOZWOLONE_BASE_URL"):
        assert wymagany in tresc, (
            f"\nStrażnik adresów niekompletny — brak {wymagany!r} "
            f"w model_factory.py.\nPrawdopodobnie merge z upstreamem cofnął "
            f"patch 03. Patrz ADR-0003 i ryzyko RY-03.\n"
        )

    # Gałęzie dostawców chmurowych muszą być usunięte, nie zakomentowane
    # warunkiem — sprawdzamy brak aktywnej konstrukcji modelu.
    for zakazana in ("AnthropicProvider(", "GoogleProvider("):
        aktywne = [
            l.strip() for l in tresc.splitlines()
            if zakazana in l and not l.strip().startswith("#")
        ]
        assert not aktywne, (
            f"\nAktywna konstrukcja dostawcy chmurowego: {zakazana}\n"
            + "\n".join(f"  {l}" for l in aktywne)
        )


def test_traefik_bez_acme():
    """U-6 · ACME wymaga połączenia wychodzącego — nie może zostać."""
    assert COMPOSE.exists()
    tresc = COMPOSE.read_text(encoding="utf-8")
    aktywne = [
        linia for linia in tresc.splitlines()
        if "acme" in linia.lower() and not linia.strip().startswith("#")
    ]
    assert not aktywne, (
        "\nKonfiguracja ACME (Let's Encrypt) jest aktywna.\n"
        "ACME z definicji łączy się na zewnątrz — w środowisku zamkniętym\n"
        "nie ma prawa działać. Użyj własnego CA: infra/ca/utworz-ca.sh\n"
        + "\n".join(f"  {l.strip()}" for l in aktywne)
    )


def test_flower_bez_ekspozycji():
    """U-8 · port 5555 ujawnia nazwy i argumenty zadań Celery."""
    assert COMPOSE.exists()
    tresc = COMPOSE.read_text(encoding="utf-8")
    wystawione = [
        linia.strip() for linia in tresc.splitlines()
        if "5555" in linia and not linia.strip().startswith("#")
    ]
    assert not wystawione, (
        "\nPort 5555 (flower) jest wystawiony.\n"
        "Nazwy zadań ujawniają identyfikatory spraw, a metadane też są\n"
        "objęte tajemnicą zawodową. Patrz U-8.\n"
        + "\n".join(f"  {l}" for l in wystawione)
    )
