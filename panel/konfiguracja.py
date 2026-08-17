"""Konfiguracja środowiska modelu — jedno źródło prawdy.

DLACZEGO TEN PLIK ISTNIEJE

14.08.2026 zmierzono, że `OLLAMA_NUM_PARALLEL=8` rozdmuchuje cache KV
ośmiokrotnie (8192 × 8 = 65 tys. tokenów), przez co model puchnie
z 6,7 GB do 20 GB i schodzi w 71% na CPU. Naprawa dała przyspieszenie
~18× i została opisana w eval/wyniki/skala-2026-08-14.md.

Naprawę wykonano w sesji powłoki i nigdy nie utrwalono. Miesiąc później
log serwera Ollamy pokazywał znowu:

    llama_kv_cache: size = 12800.00 MiB (8192 cells, 50 layers, 8/8 seqs)
    llama_kv_cache: CPU KV buffer size = 9216.00 MiB

`8/8 seqs` i cache `K (f16)` — czyli dokładnie stan sprzed naprawy,
podczas gdy raport twierdził, że problem jest zamknięty.

Wniosek: ustawienie zapisane wyłącznie w czyjejś pamięci albo w historii
powłoki nie jest ustawieniem. Wartości stoją więc tutaj, `skrypty/start.ps1`
je stąd czyta, a `tests/test_konfiguracja_ollamy.py` pilnuje, żeby
środowisko im nie przeczyło. Regresja ma być wykrywalna, nie pamiętana.
"""

from __future__ import annotations

# ── wymagane zmienne środowiskowe serwera Ollamy ─────────────────────
#
# ⚠️ Czyta je SERWER Ollamy przy starcie, nie proces panelu. Zmiana
#    wymaga ponownego uruchomienia `ollama serve` — samo ustawienie
#    zmiennej w otwartej konsoli niczego nie zmienia w działającym
#    serwerze. To jest ta pułapka, przez którą naprawa „przepadła".

WYMAGANE: dict[str, str] = {
    # Jeden slot. Każdy dodatkowy mnoży cache KV przez rozmiar kontekstu.
    # Panel i tak wykonuje jedno zapytanie naraz (Kolejka, semafor 1),
    # więc sloty ponad jeden są czystą stratą VRAM-u.
    "OLLAMA_NUM_PARALLEL": "1",

    # Kwantyzacja cache'u KV — połowa pamięci przy różnicy jakości
    # nierozpoznawalnej na tym zadaniu. Przy kontekście 8192 to różnica
    # między ~1,6 GB a ~0,8 GB, czyli między zmieszczeniem się na karcie
    # a zejściem na CPU.
    "OLLAMA_KV_CACHE_TYPE": "q8_0",

    # Wymagane przez kwantyzację cache'u.
    "OLLAMA_FLASH_ATTENTION": "1",

    # Jeden model naraz — przy 8 GB VRAM drugi i tak by się nie zmieścił,
    # a próba trzymania dwóch wypycha oba częściowo na CPU.
    "OLLAMA_MAX_LOADED_MODELS": "1",
}

# ── zmienne, które MUSZĄ być nieustawione ────────────────────────────

ZAKAZANE: dict[str, str] = {
    # Ogranicza liczbę warstw wysyłanych na kartę. Ustawione „na wszelki
    # wypadek" robi dokładnie odwrotnie, niż się wydaje: zostawia część
    # warstw na CPU i dławi całość. Ollama sama dobiera lepiej.
    "OLLAMA_NUM_GPU": (
        "Ogranicza liczbę warstw na GPU. Pomiar z 14.08.2026: 13% warstw "
        "na CPU kosztowało ~7x spowolnienia. Zostaw dobór Ollamie."
    ),
}


def srodowisko_trwale() -> dict[str, str]:
    """Konfiguracja TRWAŁA — ta, którą dostanie serwer przy następnym starcie.

    ⚠️ NIE `os.environ`. To rozróżnienie kosztowało godzinę zamieszania.

    `os.environ` opisuje środowisko odziedziczone przez TEN proces
    w chwili jego uruchomienia. Proces uruchomiony z rodzica, który
    wystartował przed poprawką, widzi stare wartości — nawet gdy profil
    użytkownika jest od dawna poprawny. Sprawdzanie `os.environ`
    odpowiadałoby więc na pytanie „co odziedziczył pytest", a nie
    „co dostanie Ollama".

    Na Windows wartości trwałe leżą w rejestrze. Użytkownik ma
    pierwszeństwo przed maszyną — tak samo, jak przy tworzeniu procesu.
    """
    import os
    import sys

    if sys.platform != "win32":
        return dict(os.environ)

    import winreg

    zrodla = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, r"Environment"),
    ]

    zebrane: dict[str, str] = {}
    for gniazdo, sciezka in zrodla:          # maszyna, potem użytkownik
        try:
            with winreg.OpenKey(gniazdo, sciezka) as klucz:
                for i in range(winreg.QueryInfoKey(klucz)[1]):
                    nazwa, wartosc, _ = winreg.EnumValue(klucz, i)
                    zebrane[nazwa.upper()] = str(wartosc)
        except OSError:
            continue
    return zebrane


def rozbiezne(srodowisko: dict[str, str] | None = None) -> list[str]:
    """Zwraca opisy rozbieżności między konfiguracją trwałą a wymaganiami.

    Pusta lista oznacza konfigurację zgodną. Używane i przez test,
    i przez panel przy starcie — użytkownik ma zobaczyć ostrzeżenie
    od razu, a nie dopiero po czterech minutach wolnej analizy.

    Uwaga: zgodna konfiguracja trwała NIE znaczy, że działający serwer
    jej używa. Od tego jest `serwer_wymaga_restartu()`.
    """
    srodowisko = srodowisko_trwale() if srodowisko is None else srodowisko
    problemy: list[str] = []

    for nazwa, oczekiwana in WYMAGANE.items():
        biezaca = srodowisko.get(nazwa)
        if biezaca is None:
            problemy.append(f"{nazwa} nieustawione — powinno być {oczekiwana!r}")
        elif biezaca != oczekiwana:
            problemy.append(
                f"{nazwa}={biezaca!r} — powinno być {oczekiwana!r}"
            )

    for nazwa, powod in ZAKAZANE.items():
        if srodowisko.get(nazwa) is not None:
            problemy.append(
                f"{nazwa}={srodowisko[nazwa]!r} — ma być nieustawione. {powod}"
            )

    return problemy


# ── stan serwera, który DZIAŁA TERAZ ─────────────────────────────────
#
# ⚠️ To jest warstwa, bez której cała reszta tego pliku bywa bezużyteczna.
#
# Zmienne powyżej opisują, co zastanie serwer PRZY NASTĘPNYM STARCIE.
# Nie mówią nic o procesie, który już działa — ten trzyma środowisko
# z chwili swojego uruchomienia i nie zauważy późniejszych zmian.
#
# Tak właśnie przetrwała regresja z sierpnia: wartości w profilu
# użytkownika były poprawne, a serwer Ollamy chodził od godzin
# ze starymi, odziedziczonymi. Sprawdzanie samych zmiennych
# pokazywało „wszystko w porządku", podczas gdy analiza szła
# osiemnastokrotnie wolniej.
#
# Dlatego stan żywego serwera czytamy z jego logu, a nie z konfiguracji.

import re as _re
from pathlib import Path as _Path

# `llama_kv_cache: size = 12800.00 MiB (8192 cells, 50 layers, 8/8 seqs), K (f16)`
_WZORZEC_CACHE = _re.compile(
    r"llama_kv_cache:\s*size\s*=.*?(\d+)\s*/\s*(\d+)\s*seqs\).*?K\s*\((\w+)\)",
    _re.IGNORECASE,
)


def log_serwera() -> "_Path | None":
    """Ścieżka do logu serwera Ollamy albo None, gdy go nie ma."""
    import os

    kandydaci = [
        _Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "server.log",
        _Path.home() / ".ollama" / "logs" / "server.log",
    ]
    for sciezka in kandydaci:
        if sciezka.is_file():
            return sciezka
    return None


def stan_serwera() -> "tuple[int, str] | None":
    """(liczba slotów, typ cache'u K) z ostatniego wczytania modelu.

    None oznacza „nie da się ustalić" — brak logu albo brak wpisu.
    Nie oznacza „jest dobrze".
    """
    log = log_serwera()
    if log is None:
        return None
    try:
        tekst = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    trafienia = _WZORZEC_CACHE.findall(tekst)
    if not trafienia:
        return None
    _, slotow, typ_k = trafienia[-1]
    return int(slotow), typ_k.lower()


def serwer_wymaga_restartu() -> list[str]:
    """Opisy rozbieżności między żywym serwerem a wymaganiami.

    Pusta lista = serwer pracuje zgodnie z konfiguracją albo nie da się
    tego ustalić. Rozstrzygnięcie „nie da się ustalić" należy do
    wywołującego — `stan_serwera()` zwraca wtedy None.
    """
    stan = stan_serwera()
    if stan is None:
        return []

    slotow, typ_k = stan
    problemy: list[str] = []
    if slotow != 1:
        problemy.append(
            f"serwer wczytał model na {slotow} slotach zamiast 1 — "
            f"cache KV jest {slotow}x większy, niż potrzeba"
        )
    if typ_k == "f16":
        problemy.append(
            "cache KV nie jest kwantyzowany (K f16) — zajmuje dwa razy "
            "więcej, niż musi"
        )
    return problemy


KOMUNIKAT_NAPRAWY = (
    "\n"
    "═══════════════════════════════════════════════════════════════\n"
    "  KONFIGURACJA OLLAMY ODBIEGA OD WYMAGANEJ\n"
    "═══════════════════════════════════════════════════════════════\n"
    "  Skutek jest mierzalny, nie teoretyczny: przy NUM_PARALLEL=8\n"
    "  cache KV rośnie do 12,8 GB, z czego 9,2 GB ląduje na CPU,\n"
    "  a analiza zwalnia ~18-krotnie.\n"
    "\n"
    "  Naprawa:\n"
    "    powershell -File skrypty/start.ps1 -TylkoKonfiguracja\n"
    "\n"
    "  Skrypt ustawia zmienne na stałe dla użytkownika i restartuje\n"
    "  serwer Ollamy — bez restartu zmienne nic nie zmieniają,\n"
    "  bo czyta je serwer przy starcie.\n"
    "═══════════════════════════════════════════════════════════════\n"
)
