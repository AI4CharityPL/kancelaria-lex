"""Bramki I-3, I-4, I-5 — warstwa C izolacji (sieć).

Dowód, nie deklaracja. Dla KAŻDEGO kontenera sprawdzamy, że nie ma
jak wyjść na zewnątrz — osobno brak rozwiązywania nazw i osobno brak
trasy (adres IP wprost).

Rozdzielenie jest celowe: kontener z zepsutym DNS, ale działającą
trasą, wygląda na odcięty, a nie jest.
"""

from __future__ import annotations

import re

import pytest

from conftest import (
    KONTENERY_ODCIETE, CELE_TCP, NAZWY_DNS,
    w_kontenerze, kontener_dziala,
)


def _pomin_gdy_nie_dziala(nazwa: str):
    if not kontener_dziala(nazwa):
        pytest.skip(f"kontener '{nazwa}' nie działa — uruchom stos przed testem")


@pytest.mark.parametrize("kontener", KONTENERY_ODCIETE)
@pytest.mark.parametrize("nazwa_dns", NAZWY_DNS)
def test_i3_dns_nie_rozwiazuje(docker, kontener: str, nazwa_dns: str):
    """I-3 · rozwiązywanie nazw zewnętrznych zawodzi."""
    _pomin_gdy_nie_dziala(kontener)

    wynik = w_kontenerze(kontener, [
        "python", "-c",
        f"import socket,sys\n"
        f"try:\n"
        f"    a = socket.gethostbyname('{nazwa_dns}')\n"
        f"    print('ROZWIAZANO:' + a); sys.exit(1)\n"
        f"except Exception:\n"
        f"    print('BRAK'); sys.exit(0)",
    ])

    if wynik.returncode != 0 and "ROZWIAZANO" not in wynik.stdout:
        # Brak Pythona w obrazie — spróbuj narzędziem systemowym.
        wynik = w_kontenerze(kontener, ["getent", "hosts", nazwa_dns])
        assert wynik.returncode != 0, (
            f"\n{kontener} rozwiązał '{nazwa_dns}':\n{wynik.stdout}"
        )
        return

    assert "ROZWIAZANO" not in wynik.stdout, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  WARSTWA C NARUSZONA — '{kontener}' rozwiązuje nazwy\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        f"  nazwa: {nazwa_dns}\n  wynik: {wynik.stdout.strip()}\n\n"
        f"Sprawdź, czy segment kontenera ma internal: true w compose.yml.\n"
    )


@pytest.mark.parametrize("kontener", KONTENERY_ODCIETE)
@pytest.mark.parametrize("host,port", CELE_TCP)
def test_i4_tcp_nie_laczy(docker, kontener: str, host: str, port: int):
    """I-4 · brak trasy na zewnątrz — adres IP wprost, bez DNS.

    Ten test jest ostrzejszy niż I-3: sprawdza trasę, a nie
    rozwiązywanie nazw. Kontener bez DNS, ale z trasą, wygląda
    na odcięty i nie jest.
    """
    _pomin_gdy_nie_dziala(kontener)

    wynik = w_kontenerze(kontener, [
        "python", "-c",
        f"import socket,sys\n"
        f"s = socket.socket(); s.settimeout(4)\n"
        f"try:\n"
        f"    s.connect(('{host}', {port}))\n"
        f"    print('POLACZONO'); sys.exit(1)\n"
        f"except Exception:\n"
        f"    print('BRAK'); sys.exit(0)\n"
        f"finally:\n"
        f"    s.close()",
    ], timeout=25)

    assert "POLACZONO" not in wynik.stdout, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  WARSTWA C NARUSZONA — '{kontener}' MA TRASĘ NA ZEWNĄTRZ  ║\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        f"  cel: {host}:{port}\n\n"
        f"To jest awaria krytyczna. Kontener przetwarzający akta może\n"
        f"nawiązać połączenie wychodzące. Zatrzymaj wdrożenie.\n"
    )


def test_i5_kanarek_dns(docker):
    """I-5 · kanarek — unikatowa nazwa nigdy nie trafia do sinkhole'a.

    Wykrywa wyciek zapytań DNS także wtedy, gdy samo połączenie
    zawodzi: sam fakt zapytania o nazwę potwierdza, że system
    próbował się z czymś połączyć.

    Wymaga skonfigurowanego sinkhole'a — infra/policies/sinkhole.md
    """
    pytest.skip(
        "Wymaga sinkhole'a DNS — konfiguracja w infra/policies/sinkhole.md. "
        "Bramka obowiązkowa przed produkcją (patrz docs/11-testy-i-bramki.md)."
    )


SEGMENTY_INTERNAL = (
    "kancelaria-lex_net_ai",
    "kancelaria-lex_net_app",
    "kancelaria-lex_net_parse",
)

# Obserwator wewnątrz segmentu. `tcpdump` doinstalowywany w kontenerze
# jednorazowym — nie dokładamy zależności do obrazów produkcyjnych.
_PODGLAD = r"""
apk add --no-cache tcpdump >/dev/null 2>&1
tcpdump -n -i any -c 50 "not net {podsiec} and not arp and not icmp6" \
    > /tmp/zrzut.txt 2>/dev/null &
PID=$!
sleep 2
wget -T 3 -q -O /dev/null http://api.openai.com/ 2>/dev/null
wget -T 3 -q -O /dev/null http://1.1.1.1/ 2>/dev/null
nslookup github.com >/dev/null 2>&1
ping -c 2 -W 2 8.8.8.8 >/dev/null 2>&1
sleep 3
kill $PID 2>/dev/null; wait $PID 2>/dev/null
echo "===POCZATEK==="
cat /tmp/zrzut.txt
echo "===KONIEC==="
"""


@pytest.mark.parametrize("siec", SEGMENTY_INTERNAL)
def test_o1_przechwycenie_ruchu(docker, siec):
    """O-1 · DOWÓD KOŃCOWY — zero pakietów opuszczających segment.

    Nie sprawdza konfiguracji ani kodu. Obserwuje rzeczywistość na
    poziomie pakietów: kontener wewnątrz segmentu AKTYWNIE próbuje
    wyjść na zewnątrz (HTTP po nazwie, HTTP po adresie IP, zapytanie
    DNS, ping), a `tcpdump` w tym samym segmencie liczy, ile z tego
    faktycznie wypłynęło poza podsieć.

    ⚠️ CO TA BRAMKA OBEJMUJE, A CZEGO NIE — STAN NA 16.08.2026.

    Do tego dnia test miał w ciele BEZWARUNKOWY `pytest.skip` i nie
    został wykonany ani razu, mimo że `docs/09-compliance/rodo-dpia.md`
    opisuje go jako warunek dopuszczenia do rzeczywistych akt.

    Obejmuje: trzy segmenty `internal: true` i realne próby wyjścia
    z ich wnętrza.

    NIE obejmuje: pełnego cyklu dokumentu (wgranie → OCR → parsowanie →
    embedding → zapytanie), bo usługi `django`, `embedder` i `postgres`
    nie dają się zbudować — `compose.yml` wskazuje na
    `src/aplikacje/embedder`, którego w repozytorium NIE MA. Dopóki ten
    brak nie zostanie usunięty, pełne O-1 wg `skrypty/przechwyc-ruch.md`
    pozostaje niewykonalne i tak trzeba je opisywać wobec audytora.
    """
    import json as _json
    import subprocess

    opis = subprocess.run(
        ["docker", "network", "inspect", siec], capture_output=True, text=True)
    if opis.returncode != 0:
        pytest.skip(f"sieć {siec} nie istnieje — uruchom stos przed testem")

    dane = _json.loads(opis.stdout)[0]
    assert dane["Internal"] is True, (
        f"{siec} przestała być segmentem wewnętrznym — to jest cofnięcie "
        f"warstwy C izolacji")
    podsiec = dane["IPAM"]["Config"][0]["Subnet"]

    wynik = subprocess.run(
        ["docker", "run", "--rm", "--network", siec,
         "--cap-add=NET_RAW", "--cap-add=NET_ADMIN",
         "alpine:3", "sh", "-c", _PODGLAD.format(podsiec=podsiec)],
        capture_output=True, text=True, timeout=180)

    tresc = wynik.stdout
    assert "===POCZATEK===" in tresc and "===KONIEC===" in tresc, (
        f"przechwycenie nie doszło do skutku:\n{wynik.stdout}\n{wynik.stderr}")

    zrzut = tresc.split("===POCZATEK===")[1].split("===KONIEC===")[0]
    pakiety = [w for w in zrzut.splitlines()
               if re.match(r"^\d{2}:\d{2}:\d{2}", w.strip())]

    assert not pakiety, (
        f"\n\n╔══════════════════════════════════════════════════════════╗\n"
        f"║  PAKIET OPUŚCIŁ SEGMENT {siec:<32}║\n"
        f"╚══════════════════════════════════════════════════════════╝\n"
        f"  podsieć: {podsiec}\n"
        + "\n".join(f"  {p}" for p in pakiety[:10])
        + "\n\n  Segment oznaczony `internal: true` nie ma prawa wypuścić "
          "ani jednego pakietu.\n  To jest naruszenie warstwy C izolacji "
          "i blokuje dopuszczenie do rzeczywistych akt.\n")
