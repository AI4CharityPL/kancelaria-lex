"""Strażnik adresu modelu — jedyne miejsce, w którym powstaje adres Ollamy.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TO POWSTAŁO
════════════════════════════════════════════════════════════════════════

Cały projekt opiera się na jednym zdaniu: **akta nie opuszczają tego
urządzenia**. Do 16.08.2026 zdanie to nie miało w panelu żadnego
mechanizmu egzekwującego. Adres modelu był zaszyty osobno w trzech
modułach:

    agent.py:51      OLLAMA = "http://127.0.0.1:11434"
    analiza.py:57    OLLAMA = "http://127.0.0.1:11434"
    kontrola.py:54   OLLAMA = "http://127.0.0.1:11434"

Trzy niezależne literały, każdy do zmiany jednym podstawieniem, żaden
niesprawdzany. Zmiana któregokolwiek na adres zewnętrzny wysyłałaby akta
sprawy karnej do cudzego serwera i **nic by tego nie zatrzymało ani nie
odnotowało**.

⚠️ WARSTWA IZOLACJI NIE OBEJMOWAŁA PRODUKTU.
   Testy w `tests/izolacja/` badają `src/opencontracts` — fork, którego
   nie wysyłamy. Co gorsza, `test_straznik.py` sprawdzał KOPIĘ walidatora
   zdefiniowaną w samym pliku testu, więc sześć testów I-6/I-7 nie
   dotykało żadnego uruchamianego kodu. Ten moduł zamyka tę lukę po
   stronie, która faktycznie działa.

════════════════════════════════════════════════════════════════════════
 ZASADA: AWARIA GŁOŚNA, NIE CICHA
════════════════════════════════════════════════════════════════════════

Walidacja odbywa się przy IMPORCIE. Proces z niedozwolonym adresem
**nie wstaje**, zamiast wstać i wysłać akta gdzie indziej. To ta sama
zasada, co przy bramkach izolacji („brak Dockera nie daje wyniku
pozytywnego") i przy kontroli modelem („awaria nie może oznaczać zgody").

Nadpisanie ze zmiennej środowiskowej jest dozwolone — bo bywa potrzebne
przy zmianie portu Ollamy — ale **przechodzi przez tę samą walidację**.
Nie ma drogi na skróty.
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

ZMIENNA = "KANCELARIA_LEX_MODEL"

# Domyślnie pętla zwrotna i port Ollamy. Zmiana wyłącznie przez zmienną
# środowiskową i wyłącznie na inny adres pętli zwrotnej.
DOMYSLNY = "http://127.0.0.1:11434"

# Nazwy hostów uznawane za lokalne. Adresy liczbowe sprawdzamy osobno,
# przez `ipaddress`, bo „127.1", „127.0.0.001" i „0x7f000001" to też
# pętla zwrotna, a porównanie napisów by ich nie złapało.
NAZWY_LOKALNE = frozenset({"localhost", "ip6-localhost", "ip6-loopback"})

SCHEMATY = frozenset({"http"})


class BlednyAdresModelu(ValueError):
    """Adres modelu prowadzi poza to urządzenie.

    Wyjątek osobnej klasy, żeby dało się go wyłapać w teście i żeby
    w logu startowym był odróżnialny od zwykłej literówki w konfiguracji.
    """


def _host_jest_lokalny(host: str) -> bool:
    """Czy host wskazuje na TO urządzenie.

    Najpierw próba odczytu jako adres liczbowy — wtedy rozstrzyga
    `is_loopback`, które rozumie wszystkie zapisy 127.0.0.0/8 oraz ::1.
    Dopiero gdy to nie jest adres, porównujemy z listą nazw.

    ⚠️ NIE ROZWIĄZUJEMY NAZW PRZEZ DNS. Zapytanie DNS samo w sobie jest
    ruchem wychodzącym i zdradza, że system istnieje — a to jest dokładnie
    ta klasa wycieku, którą bramka I-5 (kanarek DNS) ma wykrywać.
    Nazwa spoza krótkiej listy jest odrzucana bez pytania kogokolwiek.
    """
    if not host:
        return False
    czysty = host.strip().strip("[]").casefold()
    try:
        return ipaddress.ip_address(czysty).is_loopback
    except ValueError:
        return czysty in NAZWY_LOKALNE


def waliduj(adres: str) -> str:
    """Zwraca adres, jeśli prowadzi do modelu na tym urządzeniu.

    W przeciwnym razie podnosi `BlednyAdresModelu` z komunikatem
    mówiącym, co dokładnie jest nie tak — bo ten wyjątek zobaczy ktoś,
    komu panel nie wstał, i musi wiedzieć dlaczego.
    """
    if not adres or not adres.strip():
        raise BlednyAdresModelu("Adres modelu jest pusty.")

    adres = adres.strip().rstrip("/")
    czesci = urlsplit(adres)

    if czesci.scheme.casefold() not in SCHEMATY:
        raise BlednyAdresModelu(
            f"Adres modelu musi zaczynać się od http:// — dostano "
            f"{czesci.scheme or 'brak schematu'!r} w {adres!r}. "
            f"HTTPS do pętli zwrotnej nie jest potrzebny, a poza nią "
            f"nie jest dozwolony.")

    # ⚠️ NAJWAŻNIEJSZY WARUNEK W TYM PLIKU.
    # `http://127.0.0.1@zly.host/` wygląda na adres lokalny i prowadzi
    # do `zly.host` — część przed `@` jest danymi logowania, nie hostem.
    # `urlsplit` rozstrzyga to poprawnie (`hostname` == "zly.host"),
    # ale wzrokowy przegląd kodu tego nie łapie, więc odrzucamy takie
    # adresy osobno i z własnym komunikatem.
    if czesci.username is not None or "@" in (czesci.netloc or ""):
        raise BlednyAdresModelu(
            f"Adres modelu zawiera dane logowania przed znakiem @ — "
            f"{adres!r}. Taki zapis wygląda na lokalny, a prowadzi do "
            f"hosta po prawej stronie @.")

    if not _host_jest_lokalny(czesci.hostname or ""):
        raise BlednyAdresModelu(
            f"Adres modelu musi wskazywać pętlę zwrotną tego urządzenia. "
            f"Dostano host {czesci.hostname!r} w {adres!r}.\n"
            f"System przetwarza akta objęte tajemnicą zawodową i nie "
            f"komunikuje się z żadnym zewnętrznym dostawcą modelu.")

    if czesci.path not in ("", "/"):
        raise BlednyAdresModelu(
            f"Adres modelu ma być samym hostem z portem, bez ścieżki — "
            f"dostano {czesci.path!r} w {adres!r}.")

    return adres


def _z_otoczenia() -> str:
    """Adres z konfiguracji albo domyślny — zawsze po walidacji."""
    return waliduj(os.environ.get(ZMIENNA) or DOMYSLNY)


# Walidacja przy imporcie: proces z niedozwolonym adresem nie wstaje.
ADRES_MODELU = _z_otoczenia()
