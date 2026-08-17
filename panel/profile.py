"""Profile lokalne — logowanie, sesje, rozdzielenie historii per osoba.

════════════════════════════════════════════════════════════════════════
 CO TO NAPRAWIA
════════════════════════════════════════════════════════════════════════

Do 16.08.2026 „profil" istniał wyłącznie w przeglądarce: ekran logowania
zapisywał imię i rolę do `localStorage` i się chował. Nie było tabeli
użytkowników, weryfikacji hasła ani sesji. Każdy, kto otworzył panel,
wpisywał dowolne imię i wchodził.

Skutki były dwa, oba poważne:

  1. Wymóg „różne osoby, w różnym czasie, na różnych profilach" nie był
     spełniony — historia sprawy była wspólna, bez śladu autorstwa.
  2. Panel deklarował w sekcji zgodności „MFA obowiązkowe" przy art. 21
     ust. 2 lit. j ustawy o KSC, przy zerowym uwierzytelnianiu w kodzie.
     Deklaracja została sprostowana, ten moduł domyka pierwszy składnik.

⚠️ GRANICA, ZAPISANA WPROST
   To jest uwierzytelnianie JEDNOSKŁADNIKOWE. Nie zamyka art. 21 ust. 2
   lit. j, który mówi o wieloskładnikowym. Luka pozostaje i ma być
   zgłoszona przy ocenie podmiotowej, a nie przemilczana.

════════════════════════════════════════════════════════════════════════
 DECYZJE
════════════════════════════════════════════════════════════════════════

`hashlib.scrypt` zamiast pbkdf2 — jest pamięciożerny z założenia, więc
atak słownikowy na skradzionej bazie kosztuje sprzęt, nie tylko czas.
Parametry poniżej to zalecenia z dokumentacji: n=2^14, r=8, p=1.

Bez zależności zewnętrznych: `hashlib`, `secrets`, `hmac` są w bibliotece
standardowej. Dokładanie `bcrypt` czy `passlib` otwierałoby łańcuch
dostaw, który dziś jest pusty (art. 21 ust. 2 lit. d).

Sesja jest po stronie serwera: ciasteczko niesie wyłącznie losowy token,
a nie dane profilu. Token podpisany po stronie klienta (JWT) dałby się
odtworzyć z wykradzionego sekretu i nie dałby się unieważnić.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Parametry scrypt — koszt dobrany tak, żeby logowanie trwało ułamek
# sekundy na tej maszynie, a atak masowy był kosztowny.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
DLUGOSC_KLUCZA = 64

WAZNOSC_SESJI = timedelta(hours=12)

ROLE = ("prawnik", "sekretariat", "aplikant")

# ════════════════════════════════════════════════════════════════════
#  OŚWIADCZENIA PRZY ZAKŁADANIU PROFILU
# ════════════════════════════════════════════════════════════════════
#
# CZEMU TO SŁUŻY. Część obowiązków prawnych ciąży na KANCELARII i żadne
# oprogramowanie ich nie wykona — szyfrowanie nośnika, ocena podmiotowa
# KSC, zatwierdzenie DPIA, szkolenie personelu, weryfikacja cytatu przed
# użyciem w piśmie. Do 16.08.2026 system o nich milczał, więc mógł
# sprawiać wrażenie, że załatwia całość.
#
# ⚠️ WERSJONOWANE. Zmiana treści MUSI podnieść `ZGODY_WERSJA`, inaczej
#    zapis „przyjął oświadczenia" przestaje znaczyć cokolwiek konkretnego:
#    nie wiadomo byłoby, co dokładnie ta osoba widziała.
#
# ⚠️ JEDNO ŹRÓDŁO DLA INTERFEJSU I WALIDACJI. Panel pobiera tę listę
#    z serwera zamiast mieć własną kopię — inaczej ekran i sprawdzenie
#    rozjechałyby się przy pierwszej zmianie treści.
ZGODY_WERSJA = "2026-08-16"

ZGODY = (
    {
        "id": "weryfikacja",
        "tytul": "Sprawdzam cytat, zanim czegokolwiek użyję",
        "tresc": "Wiem, że system wydobywa fakty z akt i NIE udziela porady "
                 "prawnej ani nie ocenia sprawy. Każde twierdzenie sprawdzę, "
                 "klikając w cytat, zanim trafi ono do pisma, opinii albo "
                 "rozmowy z klientem. Odpowiadam za treść tego, co podpisuję.",
        "podstawa": "AI Act (rozp. UE 2024/1689) — kwalifikację narzędzia "
                    "determinuje faktyczny sposób użycia, nie deklaracja; "
                    "należyta staranność zawodowa",
    },
    {
        "id": "kompetencje",
        "tytul": "Znam ograniczenia tego systemu",
        "tresc": "Model językowy bywa w błędzie. Na pytania, na które akta "
                 "nie dają odpowiedzi, system mimo to czasem odpowiada — "
                 "w pomiarach 9 razy na 50 takich pytań. Co piąta odpowiedź "
                 "na pytanie z odpowiedzią trafia w niewłaściwe miejsce akt. "
                 "Nie traktuję wyniku jako ustalenia, dopóki go nie sprawdzę.",
        "podstawa": "AI Act art. 4 — kompetencje w zakresie AI; obowiązek "
                    "podmiotu stosującego, nie zalecenie",
    },
    {
        "id": "tajemnica",
        "tytul": "Wgrywam wyłącznie akta, do których mam uprawnienie",
        "tresc": "Nie wprowadzę do systemu materiału, do którego nie mam "
                 "dostępu w kancelarii, ani nie obejdę ścian etycznych "
                 "między sprawami. Materiał objęty tajemnicą obrończą "
                 "traktuję odrębnie.",
        "podstawa": "art. 6 Prawa o adwokaturze / art. 3 ustawy o radcach "
                    "prawnych — tajemnica zawodowa; art. 178 pkt 1 k.p.k. — "
                    "tajemnica obrończa",
    },
    {
        "id": "stanowisko",
        "tytul": "Zabezpieczenie komputera jest po mojej stronie",
        "tresc": "System pracuje w całości lokalnie i akta nie opuszczają "
                 "tego urządzenia — ale nie chroni dysku. Szyfrowanie "
                 "nośnika, osobne konto systemowe i blokada ekranu należą "
                 "do kancelarii. Wiem też, że logowanie tutaj jest "
                 "JEDNOSKŁADNIKOWE: hasło bez drugiego składnika.",
        "podstawa": "RODO art. 32 — bezpieczeństwo przetwarzania; "
                    "art. 21 ust. 2 lit. j dyrektywy 2022/2555 (MFA) — "
                    "wymóg niespełniony przez ten system",
    },
    {
        "id": "ksc",
        "tytul": "Ocena i rejestracja KSC należą do kancelarii",
        "tresc": "Ustawa działa w modelu SAMOIDENTYFIKACJI: podmiot sam "
                 "ocenia, czy jej podlega, i sam się rejestruje. Brak wpisu "
                 "nie jest neutralny. Odpowiedzialność ponosi kierownictwo "
                 "podmiotu i obejmuje ona obowiązek szkolenia. "
                 "Terminy: ocena do 15.09.2026, rejestracja do 2.10.2026.",
        "podstawa": "ustawa o krajowym systemie cyberbezpieczeństwa "
                    "(Dz.U. 2026 poz. 252); art. 21 dyrektywy 2022/2555",
    },
    {
        "id": "kopie",
        "tytul": "Kopie zapasowe robi kancelaria, nie system",
        "tresc": "System nie tworzy kopii akt i nie odtworzy ich po awarii "
                 "dysku. Procedura odtworzenia jest opisana, ale "
                 "NIE ZOSTAŁA JESZCZE PRZEĆWICZONA — do czasu pierwszego "
                 "ćwiczenia deklarowane czasy są założeniem, nie zmierzoną "
                 "wartością.",
        "podstawa": "RODO art. 32 ust. 1 lit. c — zdolność do przywrócenia "
                    "dostępności danych; art. 21 ust. 2 lit. c dyrektywy "
                    "2022/2555 — ciągłość działania",
    },
)

WYMAGANE_ZGODY = frozenset(z["id"] for z in ZGODY)

# Login bez znaków, które w URL-u albo logu wymagałyby uciekania.
_LOGIN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,30})[a-z0-9]$")

MIN_HASLO = 10


class BladProfilu(ValueError):
    """Błąd możliwy do pokazania użytkownikowi wprost."""


class BlokadaLogowania(BladProfilu):
    """Za dużo nieudanych prób. Niesie liczbę sekund do odblokowania."""

    def __init__(self, sekundy: int):
        self.sekundy = max(1, int(sekundy))
        super().__init__(
            f"Za dużo nieudanych prób logowania. Spróbuj ponownie za "
            f"{self.sekundy // 60 + 1} min.")


# ── DŁAWIENIE PRÓB LOGOWANIA ─────────────────────────────────────────
#
# Progresja zamiast twardego zamknięcia konta. Trwała blokada po N
# próbach zamienia się w narzędzie ataku na dostępność: wystarczy
# wpisać cudzy login z błędnym hasłem, żeby odciąć prawnika od akt
# w dniu rozprawy. Rosnące okno karze zgadywanie, a osobie, która
# pomyliła hasło, każe poczekać minutę.
PROB_PRZED_BLOKADA = 5
BLOKADA_BAZOWA_S = 60
BLOKADA_MAKS_S = 15 * 60

# Po tylu minutach bez próby licznik zeruje się sam. Bez tego pięć
# pomyłek rozłożonych na pół roku sumowałoby się do blokady.
OKNO_ZLICZANIA = timedelta(minutes=30)


def _klucz_prob(login: str) -> str:
    return (login or "").strip().casefold()


def sprawdz_dlawienie(db, login: str) -> None:
    """Podnosi `BlokadaLogowania`, gdy login jest w oknie blokady."""
    wiersz = db.execute(
        "SELECT zablokowany_do FROM proby_logowania WHERE login = ?",
        (_klucz_prob(login),)).fetchone()
    if wiersz is None or not wiersz["zablokowany_do"]:
        return
    try:
        do_kiedy = datetime.fromisoformat(wiersz["zablokowany_do"])
    except ValueError:
        return
    zostalo = (do_kiedy - _teraz()).total_seconds()
    if zostalo > 0:
        raise BlokadaLogowania(zostalo)


def zapisz_nieudana(db, login: str) -> int:
    """Zlicza nieudaną próbę i ustawia blokadę. Zwraca liczbę nieudanych."""
    klucz = _klucz_prob(login)
    teraz = _teraz()
    wiersz = db.execute(
        "SELECT nieudanych, ostatnia FROM proby_logowania WHERE login = ?",
        (klucz,)).fetchone()

    nieudanych = 1
    if wiersz is not None:
        try:
            ostatnia = datetime.fromisoformat(wiersz["ostatnia"])
        except ValueError:
            ostatnia = teraz
        if teraz - ostatnia <= OKNO_ZLICZANIA:
            nieudanych = int(wiersz["nieudanych"]) + 1

    blokada = ""
    if nieudanych >= PROB_PRZED_BLOKADA:
        ile = min(BLOKADA_MAKS_S,
                  BLOKADA_BAZOWA_S * 2 ** (nieudanych - PROB_PRZED_BLOKADA))
        blokada = _znacznik(teraz + timedelta(seconds=ile))

    db.execute(
        "INSERT INTO proby_logowania (login, nieudanych, ostatnia, "
        "zablokowany_do) VALUES (?,?,?,?) ON CONFLICT(login) DO UPDATE SET "
        "nieudanych = excluded.nieudanych, ostatnia = excluded.ostatnia, "
        "zablokowany_do = excluded.zablokowany_do",
        (klucz, nieudanych, _znacznik(teraz), blokada))
    db.commit()
    return nieudanych


def wyczysc_proby(db, login: str) -> None:
    """Udane logowanie zeruje licznik."""
    db.execute("DELETE FROM proby_logowania WHERE login = ?",
               (_klucz_prob(login),))
    db.commit()


@dataclass(frozen=True)
class Profil:
    id: int
    login: str
    imie: str
    nazwisko: str
    rola: str

    @property
    def podpis(self) -> str:
        return f"{self.imie} {self.nazwisko}".strip()


def _teraz() -> datetime:
    return datetime.now(timezone.utc)


def _znacznik(chwila: datetime) -> str:
    return chwila.isoformat(timespec="seconds")


def _skrot(haslo: str, sol: bytes) -> bytes:
    return hashlib.scrypt(haslo.encode("utf-8"), salt=sol, n=SCRYPT_N,
                          r=SCRYPT_R, p=SCRYPT_P, dklen=DLUGOSC_KLUCZA)


def sprawdz_sile(login: str, haslo: str, imie: str, nazwisko: str,
                 rola: str) -> None:
    """Walidacja wejścia. Osobno, żeby dała się przetestować bez bazy."""
    if not _LOGIN.match(login or ""):
        raise BladProfilu(
            "Login: 3–32 znaki, małe litery, cyfry, kropka, myślnik lub "
            "podkreślenie; musi zaczynać się i kończyć literą albo cyfrą.")
    if len(haslo or "") < MIN_HASLO:
        raise BladProfilu(f"Hasło musi mieć co najmniej {MIN_HASLO} znaków.")
    if haslo.strip().casefold() == login.strip().casefold():
        raise BladProfilu("Hasło nie może być takie samo jak login.")
    if not (imie or "").strip() or not (nazwisko or "").strip():
        raise BladProfilu("Imię i nazwisko są wymagane — podpisują wpisy "
                          "w dzienniku audytu.")
    if rola not in ROLE:
        raise BladProfilu(f"Rola musi być jedną z: {', '.join(ROLE)}.")


def ilu(db) -> int:
    return int(db.execute("SELECT COUNT(*) AS n FROM profile").fetchone()["n"])


def sprawdz_zgody(zgody) -> None:
    """Czy przyjęto KOMPLET oświadczeń.

    ⚠️ Sprawdzane po stronie SERWERA, nie tylko w przeglądarce.
    Lista zaznaczeń wysłana z klienta jest danymi, nie dowodem — bez tego
    sprawdzenia wystarczyłoby pominąć interfejs, żeby założyć konto
    z pominięciem oświadczeń. Ten sam błąd, którym był ekran logowania
    chowający się samodzielnie.
    """
    przyjete = {str(z) for z in (zgody or [])}
    brakujace = WYMAGANE_ZGODY - przyjete
    if brakujace:
        nazwy = ", ".join(z["tytul"] for z in ZGODY if z["id"] in brakujace)
        raise BladProfilu(
            "Aby korzystać z systemu, trzeba przyjąć wszystkie "
            f"oświadczenia. Brakuje: {nazwy}.")


def zaloz(db, login: str, haslo: str, imie: str, nazwisko: str,
          rola: str, zgody=None) -> Profil:
    """Nowy profil. Rejestracja od razu uprawnia do logowania —
    bez potwierdzania adresem, bo system nie ma i nie ma mieć poczty.

    `zgody` to identyfikatory przyjętych oświadczeń. Komplet jest
    WARUNKIEM założenia konta: część obowiązków prawnych ciąży na
    kancelarii i system ma o tym powiedzieć, zanim ktokolwiek wgra
    pierwsze akta.
    """
    login = (login or "").strip().casefold()
    sprawdz_sile(login, haslo, imie, nazwisko, rola)
    sprawdz_zgody(zgody)

    sol = secrets.token_bytes(16)
    try:
        kursor = db.execute(
            "INSERT INTO profile (login, imie, nazwisko, rola, skrot, sol, "
            "utworzono, zgody_wersja, zgody_czas) VALUES (?,?,?,?,?,?,?,?,?)",
            (login, imie.strip(), nazwisko.strip(), rola,
             _skrot(haslo, sol), sol, _znacznik(_teraz()),
             ZGODY_WERSJA, _znacznik(_teraz())))
    except sqlite3.IntegrityError:
        raise BladProfilu("Taki login już istnieje.") from None
    db.commit()
    return Profil(int(kursor.lastrowid), login, imie.strip(),
                  nazwisko.strip(), rola)


def uwierzytelnij(db, login: str, haslo: str) -> Profil | None:
    """Sprawdzenie hasła. `None` znaczy „nie wpuszczamy" — bez rozróżniania,
    czy zawiódł login czy hasło, żeby nie potwierdzać istnienia kont.

    Porównanie przez `hmac.compare_digest`: czas wykonania nie zależy od
    tego, ile początkowych bajtów się zgadza.

    ⚠️ Podnosi `BlokadaLogowania` przy serii nieudanych prób — patrz
    komentarz przy `sprawdz_dlawienie`. Wyjątek, a nie `None`, bo to
    inna informacja: „nie wpuszczam" wobec „nie sprawdzam, poczekaj".
    """
    sprawdz_dlawienie(db, login)

    wiersz = db.execute(
        "SELECT * FROM profile WHERE login = ?",
        ((login or "").strip().casefold(),)).fetchone()
    if wiersz is None:
        # Liczymy skrót mimo braku profilu — inaczej brak konta byłby
        # rozpoznawalny po czasie odpowiedzi. Z tego samego powodu
        # nieudaną próbę zliczamy także dla loginu, którego nie ma.
        _skrot(haslo or "", b"nieistniejacy-profil")
        zapisz_nieudana(db, login)
        return None

    if not hmac.compare_digest(wiersz["skrot"], _skrot(haslo or "", wiersz["sol"])):
        zapisz_nieudana(db, login)
        return None

    wyczysc_proby(db, login)
    db.execute("UPDATE profile SET ostatnie_logowanie = ? WHERE id = ?",
               (_znacznik(_teraz()), wiersz["id"]))
    db.commit()
    return Profil(int(wiersz["id"]), wiersz["login"], wiersz["imie"],
                  wiersz["nazwisko"], wiersz["rola"])


# ════════════════════════════════════════════════════════════════════
#  DRUGI SKŁADNIK (TOTP)
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ WŁĄCZENIE JEST DWUETAPOWE I TO NIE JEST OZDOBNIK.
#
# Sekret powstaje w kroku pierwszym, ale drugi składnik zaczyna
# obowiązywać dopiero po POTWIERDZENIU kodem z telefonu. Włączenie
# od razu przy generowaniu sekretu zamykałoby dostęp do akt każdemu,
# kto źle przepisał kod QR — bez drogi powrotu, bo system nie ma poczty.

class BladDrugiegoSkladnika(BladProfilu):
    """Drugi składnik nie przeszedł — wiadomość dla użytkownika."""


def stan_mfa(db, profil_id: int) -> dict:
    wiersz = db.execute(
        "SELECT wlaczony, potwierdzono FROM drugi_skladnik WHERE profil_id = ?",
        (profil_id,)).fetchone()
    pozostalo = db.execute(
        "SELECT COUNT(*) FROM kody_zapasowe WHERE profil_id = ? AND zuzyty = ''",
        (profil_id,)).fetchone()[0]
    return {
        "wlaczony": bool(wiersz and wiersz["wlaczony"]),
        "przygotowany": wiersz is not None,
        "kodow_zapasowych": pozostalo,
    }


def przygotuj_mfa(db, profil: Profil) -> tuple[str, str]:
    """Nowy sekret i adres dla aplikacji. NIE włącza jeszcze drugiego składnika."""
    import totp as mod_totp

    sekret = mod_totp.nowy_sekret()
    db.execute(
        "INSERT INTO drugi_skladnik (profil_id, sekret, wlaczony, utworzono) "
        "VALUES (?,?,0,?) ON CONFLICT(profil_id) DO UPDATE SET "
        "sekret = excluded.sekret, wlaczony = 0, utworzono = excluded.utworzono, "
        "potwierdzono = ''",
        (profil.id, sekret, _znacznik(_teraz())))
    db.commit()
    return sekret, mod_totp.adres_do_aplikacji(sekret, profil.login)


def wlacz_mfa(db, profil: Profil, kod: str) -> list[str]:
    """Potwierdzenie kodem z telefonu. Zwraca kody zapasowe — raz."""
    import totp as mod_totp

    wiersz = db.execute(
        "SELECT sekret FROM drugi_skladnik WHERE profil_id = ?",
        (profil.id,)).fetchone()
    if wiersz is None:
        raise BladDrugiegoSkladnika(
            "Najpierw przygotuj drugi składnik, potem potwierdź go kodem.")
    if not mod_totp.sprawdz(wiersz["sekret"], kod):
        raise BladDrugiegoSkladnika(
            f"Kod nie pasuje. Sprawdź, czy w telefonie widnieje profil "
            f"{profil.login} i czy zegar telefonu jest ustawiany "
            f"automatycznie.")

    kody = mod_totp.nowe_kody_zapasowe()
    db.execute("DELETE FROM kody_zapasowe WHERE profil_id = ?", (profil.id,))
    db.executemany(
        "INSERT INTO kody_zapasowe (profil_id, skrot) VALUES (?,?)",
        [(profil.id, mod_totp.skrot_kodu(k)) for k in kody])
    db.execute(
        "UPDATE drugi_skladnik SET wlaczony = 1, potwierdzono = ? "
        "WHERE profil_id = ?", (_znacznik(_teraz()), profil.id))
    db.commit()
    return kody


def wylacz_mfa(db, profil: Profil) -> None:
    db.execute("DELETE FROM drugi_skladnik WHERE profil_id = ?", (profil.id,))
    db.execute("DELETE FROM kody_zapasowe WHERE profil_id = ?", (profil.id,))
    db.commit()


def sprawdz_drugi_skladnik(db, profil: Profil, kod: str) -> bool:
    """Kod z aplikacji albo kod zapasowy. Zapasowy jest JEDNORAZOWY."""
    import totp as mod_totp

    wiersz = db.execute(
        "SELECT sekret, wlaczony FROM drugi_skladnik WHERE profil_id = ?",
        (profil.id,)).fetchone()
    if wiersz is None or not wiersz["wlaczony"]:
        return True                       # drugi składnik nieaktywny

    if mod_totp.sprawdz(wiersz["sekret"], kod):
        return True

    # ⚠️ Kod zapasowy zużywa się przy UŻYCIU, nie przy poprawnym logowaniu.
    #    Inaczej ten sam kod z kartki wpuszczałby wielokrotnie, a jego
    #    sens polega na tym, że działa raz.
    skrot = mod_totp.skrot_kodu(kod)
    zapasowy = db.execute(
        "SELECT id FROM kody_zapasowe WHERE profil_id = ? AND skrot = ? "
        "AND zuzyty = ''", (profil.id, skrot)).fetchone()
    if zapasowy is None:
        return False
    db.execute("UPDATE kody_zapasowe SET zuzyty = ? WHERE id = ?",
               (_znacznik(_teraz()), zapasowy["id"]))
    db.commit()
    return True


def wymaga_drugiego_skladnika(db, profil: Profil) -> bool:
    wiersz = db.execute(
        "SELECT wlaczony FROM drugi_skladnik WHERE profil_id = ?",
        (profil.id,)).fetchone()
    return bool(wiersz and wiersz["wlaczony"])


def otworz_sesje(db, profil: Profil) -> str:
    """Losowy token sesji. Zwraca wartość do ciasteczka."""
    token = secrets.token_urlsafe(32)
    teraz = _teraz()
    db.execute("INSERT INTO sesje (token, profil_id, utworzono, wygasa) "
               "VALUES (?,?,?,?)",
               (token, profil.id, _znacznik(teraz),
                _znacznik(teraz + WAZNOSC_SESJI)))
    _sprzataj(db)
    db.commit()
    return token


def z_sesji(db, token: str | None) -> Profil | None:
    """Profil dla tokenu albo `None`. Sesja wygasła jest jak jej brak."""
    if not token:
        return None
    wiersz = db.execute(
        "SELECT p.*, s.wygasa FROM sesje s JOIN profile p ON p.id = s.profil_id "
        "WHERE s.token = ?", (token,)).fetchone()
    if wiersz is None:
        return None
    if wiersz["wygasa"] < _znacznik(_teraz()):
        db.execute("DELETE FROM sesje WHERE token = ?", (token,))
        db.commit()
        return None
    return Profil(int(wiersz["id"]), wiersz["login"], wiersz["imie"],
                  wiersz["nazwisko"], wiersz["rola"])


def zamknij_sesje(db, token: str | None) -> None:
    if token:
        db.execute("DELETE FROM sesje WHERE token = ?", (token,))
        db.commit()


def _sprzataj(db) -> None:
    """Usuwa sesje wygasłe. Tabela sesji nie ma rosnąć w nieskończoność."""
    db.execute("DELETE FROM sesje WHERE wygasa < ?", (_znacznik(_teraz()),))
