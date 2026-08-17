"""Drugi składnik uwierzytelniania — TOTP (RFC 6238).

════════════════════════════════════════════════════════════════════════
 PO CO
════════════════════════════════════════════════════════════════════════

Art. 21 ust. 2 lit. j dyrektywy 2022/2555 mówi o uwierzytelnianiu
WIELOSKŁADNIKOWYM. Panel realizował login i hasło, więc w tabeli
zgodności widniało przy tym wymogu „nie jest wdrożone" — jedyny punkt
z całej dziesiątki opisany w ten sposób.

════════════════════════════════════════════════════════════════════════
 DLACZEGO TOTP, A NIE SMS ANI KLUCZ SPRZĘTOWY
════════════════════════════════════════════════════════════════════════

TOTP jest jedynym drugim składnikiem, który da się zrobić **bez sieci**.
SMS wymaga bramki, powiadomienie push — serwera dostawcy, klucz
sprzętowy (WebAuthn) — dostępu do przeglądarki przez HTTPS, którego
panel na pętli zwrotnej nie ma.

TOTP to wspólny sekret i zegar. Aplikacja w telefonie liczy ten sam
kod co panel, każde z osobna, bez wymiany czegokolwiek między nimi.
Zgodne z zasadą naczelną: nic nie wychodzi poza urządzenie.

Implementacja: `hmac` i `hashlib` z biblioteki standardowej, plus
własne Base32 dla kodu QR. Zero nowych zależności (art. 21 ust. 2
lit. d ustawy o KSC).

════════════════════════════════════════════════════════════════════════
 CZEGO TO NIE ZAŁATWIA — ZAPISANE WPROST
════════════════════════════════════════════════════════════════════════

⚠️ Gdy telefon i komputer to to samo urządzenie, drugi składnik jest
   pozorny. Aplikacja TOTP MA STAĆ NA TELEFONIE — inaczej włamanie na
   komputer daje oba składniki naraz. Wymóg jest w oświadczeniu przy
   włączaniu MFA, bo żaden kod tego nie sprawdzi.

⚠️ Kody zapasowe są jednorazowe i trzymane jako skróty. Utrata telefonu
   bez kodów zapasowych oznacza utratę dostępu do akt — nie ma tu
   „resetu przez e-mail", bo system nie ma i nie ma mieć poczty.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

# 6 cyfr co 30 sekund — ustawienia domyślne wszystkich aplikacji TOTP.
# Zmiana wymagałaby ręcznej konfiguracji w telefonie, co jest źródłem
# błędów przy wdrożeniu w kancelarii.
CYFR = 6
OKNO_S = 30

# ⚠️ Tolerancja zegara: przyjmujemy kod z okna poprzedniego i następnego.
#
# Zegar telefonu potrafi odejść o kilkanaście sekund. Bez tolerancji
# prawnik z lekko spóźnionym telefonem nie wejdzie do akt i nie będzie
# wiedział dlaczego — a to najgorsza możliwa awaria w dniu rozprawy.
# Szerzej nie idziemy: każde dodatkowe okno to trzydzieści sekund
# więcej na zgadywanie.
TOLERANCJA_OKIEN = 1

ILE_KODOW_ZAPASOWYCH = 8


def nowy_sekret() -> str:
    """Sekret w Base32, jak oczekują tego aplikacje TOTP."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _kod(sekret: str, licznik: int) -> str:
    klucz = base64.b32decode(sekret + "=" * (-len(sekret) % 8), casefold=True)
    skrot = hmac.new(klucz, struct.pack(">Q", licznik), hashlib.sha1).digest()
    przesuniecie = skrot[-1] & 0x0F
    wycinek = struct.unpack(">I", skrot[przesuniecie:przesuniecie + 4])[0]
    return str((wycinek & 0x7FFFFFFF) % (10 ** CYFR)).zfill(CYFR)


def kod_teraz(sekret: str, chwila: float | None = None) -> str:
    return _kod(sekret, int((chwila if chwila is not None else time.time()) // OKNO_S))


def sprawdz(sekret: str, podany: str, chwila: float | None = None) -> bool:
    """Czy podany kod pasuje do sekretu w bieżącym oknie (z tolerancją).

    Porównanie przez `hmac.compare_digest`: czas wykonania nie zależy
    od tego, ile początkowych cyfr się zgadza.
    """
    podany = (podany or "").strip().replace(" ", "")
    if len(podany) != CYFR or not podany.isdigit():
        return False

    teraz = int((chwila if chwila is not None else time.time()) // OKNO_S)
    for przesuniecie in range(-TOLERANCJA_OKIEN, TOLERANCJA_OKIEN + 1):
        if hmac.compare_digest(_kod(sekret, teraz + przesuniecie), podany):
            return True
    return False


def adres_do_aplikacji(sekret: str, login: str,
                       wydawca: str = "kancelaria-lex") -> str:
    """Adres `otpauth://`, który aplikacja w telefonie czyta z kodu QR.

    Kod QR rysuje panel po stronie przeglądarki — obraz generowany
    na serwerze musiałby wędrować przez sieć razem z sekretem.
    """
    etykieta = quote(f"{wydawca}:{login}")
    return (f"otpauth://totp/{etykieta}?secret={sekret}"
            f"&issuer={quote(wydawca)}&algorithm=SHA1"
            f"&digits={CYFR}&period={OKNO_S}")


# ── kody zapasowe ────────────────────────────────────────────────────
#
# ⚠️ Bez nich utrata telefonu = utrata dostępu do akt, na zawsze.
#    System nie ma poczty, więc nie ma „resetu przez e-mail". Kody są
#    jedyną drogą powrotu i muszą zostać wydrukowane albo zapisane poza
#    komputerem, na którym stoi panel.

def nowe_kody_zapasowe(ile: int = ILE_KODOW_ZAPASOWYCH) -> list[str]:
    """Kody w postaci czytelnej do przepisania z kartki."""
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}"
            for _ in range(ile)]


def skrot_kodu(kod: str) -> str:
    """Skrót kodu zapasowego. W bazie nie leży kod, tylko jego skrót."""
    return hashlib.sha256(
        kod.strip().casefold().replace(" ", "").encode("utf-8")).hexdigest()
