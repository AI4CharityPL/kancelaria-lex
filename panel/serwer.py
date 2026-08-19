"""Panel spraw sądowych — serwer HTTP.

Uruchomienie:
    python panel/serwer.py           # http://127.0.0.1:8713

Wyłącznie biblioteka standardowa — zero nowych zależności do pilnowania
w łańcuchu dostaw (art. 21 ust. 2 lit. d ustawy o KSC).

⚠️ Nasłuch WYŁĄCZNIE na 127.0.0.1. Panel nie wystawia się do sieci.
   Udostępnienie w LAN kancelarii wymaga świadomej decyzji: reverse
   proxy z TLS z własnego CA i uwierzytelnianiem — patrz
   docs/10-operacje/runbook-wdrozenie.md. Panel nie ma własnego
   logowania i nie jest przeznaczony do wystawienia bez tej warstwy.
"""

from __future__ import annotations

import json
import re
import sys
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

KORZEN = Path(__file__).resolve().parent
sys.path.insert(0, str(KORZEN))

import agent  # noqa: E402
import analiza  # noqa: E402
import baza  # noqa: E402
import dziennik as mod_dziennik  # noqa: E402
import profile as mod_profile  # noqa: E402
import przepisy as mod_przepisy  # noqa: E402
import eksport as mod_eksport  # noqa: E402
import kopia as mod_kopia  # noqa: E402
import terminy as mod_terminy  # noqa: E402
import ocr as mod_ocr  # noqa: E402
import wczytywanie as mod_wczytywanie  # noqa: E402
import zadania as mod_zadania  # noqa: E402

HOST = "127.0.0.1"
PORT = 8713

STATYCZNE = KORZEN / "statyczne"
# Kopie obok bazy, w katalogu objętym tym samym `.gitignore` co akta.
# ⚠️ Kopia zawiera CAŁE akta i nie jest szyfrowana przez aplikację —
#    ochrona nośnika należy do kancelarii.
KATALOG_KOPII = KORZEN / "dane" / "kopie"

# ⚠️ ŚCIEŻKA BAZY JAWNIE, NIE DOMYŚLNIE.
#
# Odtworzenie z kopii musi zamknąć połączenie, podmienić plik i połączyć
# się PONOWNIE — a do tego trzeba wiedzieć, z czym. Bez tej stałej
# ponowne połączenie szłoby zawsze do bazy domyślnej, także w teście
# pracującym na bazie tymczasowej: przebieg testów sięgnąłby wtedy do
# prawdziwych akt kancelarii.
SCIEZKA_DB = baza.SCIEZKA_BAZY
DB = baza.polacz(SCIEZKA_DB)
mod_przepisy.przygotuj(DB)
# Dokumenty wgrane przed wprowadzeniem rozpoznawania języka dostają je teraz.
# Oczyszczenie ze znaczników PRZED rozpoznaniem języka — znaczniki
# psuły jedno i drugie (patrz panel/oczyszczanie.py).
_OCZYSZCZONO = baza.oczysc_dokumenty(DB)
_UZUPELNIONO_JEZYKOW = baza.uzupelnij_jezyki(DB)
KOLEJKA = mod_zadania.Kolejka()


CIASTKO = "kl_sesja"

# Ścieżki dostępne bez zalogowania. Wszystko poza nimi wymaga sesji —
# lista jest zamknięta celowo: nowy punkt końcowy jest chroniony
# domyślnie, a jego odsłonięcie wymaga świadomego dopisania tutaj.
PUBLICZNE = {
    "/", "/index.html",
    "/api/profil/stan", "/api/profil/logowanie", "/api/profil/rejestracja",
    "/api/profil/zgody",
}


def _json(uchwyt, dane, kod=200, ciastko: str | None = None,
          skasuj_ciastko: bool = False):
    tresc = json.dumps(dane, ensure_ascii=False).encode("utf-8")
    uchwyt.send_response(kod)
    uchwyt.send_header("Content-Type", "application/json; charset=utf-8")
    uchwyt.send_header("Content-Length", str(len(tresc)))
    # Panel nie ma być osadzany ani odpytywany z innych stron.
    uchwyt.send_header("X-Content-Type-Options", "nosniff")
    uchwyt.send_header("X-Frame-Options", "DENY")
    uchwyt.send_header("Referrer-Policy", "no-referrer")
    if ciastko is not None:
        # HttpOnly — skrypt strony nie ma dostępu do tokenu, więc XSS
        # nie wynosi sesji. SameSite=Strict — ciasteczko nie idzie przy
        # żądaniu wywołanym z obcej strony (CSRF).
        # Bez `Secure`: panel chodzi po http na pętli zwrotnej, a ta flaga
        # kazałaby przeglądarce ciasteczko pominąć.
        uchwyt.send_header(
            "Set-Cookie",
            f"{CIASTKO}={ciastko}; HttpOnly; SameSite=Strict; Path=/")
    if skasuj_ciastko:
        uchwyt.send_header(
            "Set-Cookie",
            f"{CIASTKO}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
    uchwyt.end_headers()
    uchwyt.wfile.write(tresc)


class Uchwyt(BaseHTTPRequestHandler):
    server_version = "kancelaria-lex/1.0"

    def log_message(self, format, *args):        # noqa: A002
        # Ścieżki mogą zawierać identyfikatory spraw — nie logujemy
        # ich na konsolę. Ślad idzie do logu audytowego w bazie.
        pass

    # ── sesja ───────────────────────────────────────────────────────

    def _token(self) -> str | None:
        surowe = self.headers.get("Cookie")
        if not surowe:
            return None
        ciastka = SimpleCookie()
        try:
            ciastka.load(surowe)
        except Exception:                            # noqa: BLE001
            return None
        wpis = ciastka.get(CIASTKO)
        return wpis.value if wpis else None

    def _profil(self):
        return mod_profile.z_sesji(DB, self._token())

    # ── wgrywanie plików ────────────────────────────────────────────
    #
    # ⚠️ WŁASNY ROZBIÓR `multipart/form-data`, A NIE `cgi.FieldStorage`.
    #
    # Moduł `cgi` został usunięty z biblioteki standardowej w Pythonie
    # 3.13, a `email.parser` wczytuje całość do pamięci jako tekst,
    # co przy pliku binarnym psuje bajty. Rozbiór jest tu prosty, bo
    # przyjmujemy jedno pole plikowe i kilka tekstowych — a każda
    # biblioteka zewnętrzna to nowa pozycja w łańcuchu dostaw
    # (art. 21 ust. 2 lit. d ustawy o KSC).

    MAKS_ZADANIE = 45 * 1024 * 1024

    def _multipart(self) -> tuple[dict[str, str], list[tuple[str, bytes]]]:
        """Zwraca (pola tekstowe, [(nazwa pliku, bajty)])."""
        typ = self.headers.get("Content-Type") or ""
        if "multipart/form-data" not in typ:
            raise self.BledneCialo("Oczekiwano multipart/form-data.")

        dopasowanie = re.search(r'boundary="?([^";]+)"?', typ)
        if not dopasowanie:
            raise self.BledneCialo("Brak granicy (boundary) w Content-Type.")
        granica = ("--" + dopasowanie.group(1)).encode("ascii")

        self._cialo_odczytane = True
        dlugosc = int(self.headers.get("Content-Length") or 0)
        if dlugosc <= 0:
            raise self.BledneCialo("Puste żądanie.")
        if dlugosc > self.MAKS_ZADANIE:
            raise self.BledneCialo(
                f"Żądanie ma {dlugosc // 1024 // 1024} MB, limit to "
                f"{self.MAKS_ZADANIE // 1024 // 1024} MB.")

        surowe = self.rfile.read(dlugosc)
        pola: dict[str, str] = {}
        pliki: list[tuple[str, bytes]] = []

        for czesc in surowe.split(granica):
            if czesc in (b"", b"--", b"--\r\n", b"\r\n"):
                continue
            rozdzial = czesc.find(b"\r\n\r\n")
            if rozdzial < 0:
                continue
            naglowki = czesc[:rozdzial].decode("utf-8", errors="replace")
            cialo = czesc[rozdzial + 4:]
            # Ostatnie CRLF należy do granicy, nie do danych.
            if cialo.endswith(b"\r\n"):
                cialo = cialo[:-2]

            nazwa_pola = re.search(r'name="([^"]*)"', naglowki)
            nazwa_pliku = re.search(r'filename="([^"]*)"', naglowki)
            if nazwa_pliku and nazwa_pliku.group(1):
                pliki.append((nazwa_pliku.group(1), cialo))
            elif nazwa_pola:
                pola[nazwa_pola.group(1)] = cialo.decode(
                    "utf-8", errors="replace").strip()

        return pola, pliki

    def _wgraj_plik(self, sprawa_id: int, profil):
        """Wgranie akt z pliku. Wiele plików w jednym żądaniu.

        ⚠️ ODMOWA JEST TU WYNIKIEM POPRAWNYM.

        Plik, z którego nie da się wydobyć wiarygodnego tekstu (skan bez
        OCR-u, pomylona strona kodowa nie do odwrócenia), NIE jest
        wczytywany. Wpuszczenie go zamieniłoby cały łańcuch cytowania
        w teatr: weryfikator porównywałby cytat ze zniekształconym
        źródłem, zgodnie znak w znak i całkowicie fałszywie.
        """
        try:
            pola, pliki = self._multipart()
        except self.BledneCialo as e:
            return _json(self, {"blad": str(e)}, 400)

        if not pliki:
            return _json(self, {"blad": "Nie przesłano żadnego pliku."}, 400)

        wczytane, odrzucone = [], []
        for nazwa, bajty in pliki:
            try:
                # OCR wyłącznie na wyraźne życzenie — patrz `panel/ocr.py`.
                wynik = mod_wczytywanie.wczytaj(
                    nazwa, bajty,
                    ocr_dozwolony=str(pola.get("ocr", "")).lower()
                    in ("1", "true", "tak"))
            except mod_wczytywanie.BladWczytywania as e:
                odrzucone.append({"nazwa": nazwa, "powod": str(e)})
                continue

            if not wynik.nadaje_sie:
                odrzucone.append({
                    "nazwa": nazwa,
                    "powod": " ".join(wynik.ostrzezenia) or
                             "Nie udało się wydobyć tekstu.",
                    "wymaga_ocr": wynik.wymaga_ocr,
                    # Panel pokazuje przycisk „rozpoznaj" tylko wtedy, gdy
                    # OCR jest faktycznie dostępny z polskim pakietem.
                    "ocr_dostepny": mod_ocr.stan()["dostepny"],
                })
                baza.zapisz_audyt(
                    DB, "dokument.odrzucony", sprawa_id,
                    f"plik={nazwa[:80]} typ={wynik.typ} znakow={wynik.znakow}")
                continue

            try:
                dok_id = baza.dodaj_dokument(
                    DB, sprawa_id, nazwa, wynik.tekst,
                    rodzaj=pola.get("rodzaj") or "pismo",
                    zrodlo_tekstu=wynik.zrodlo)
            except ValueError as e:
                odrzucone.append({"nazwa": nazwa, "powod": str(e)})
                continue

            wczytane.append({"id": dok_id, "nazwa": nazwa, "typ": wynik.typ,
                             "znakow": wynik.znakow,
                             "zrodlo": wynik.zrodlo,
                             "stron_ocr": wynik.stron_ocr,
                             "ostrzezenia": wynik.ostrzezenia})
            baza.zapisz_audyt(
                DB, "dokument.wgrany", sprawa_id,
                f"plik={nazwa[:80]} typ={wynik.typ} znakow={wynik.znakow} "
                f"osoba={getattr(profil, 'login', '?')}")

        kod = 201 if wczytane else 400
        return _json(self, {"wczytane": wczytane, "odrzucone": odrzucone}, kod)

    def _wpuszczony(self, sciezka: str):
        """Profil dla żądania albo `False` po wysłaniu odmowy.

        ⚠️ Odmowa musi być JAWNA. Wcześniejsza wersja panelu nie miała
        uwierzytelniania w ogóle, a ekran logowania chował się sam
        w przeglądarce — czyli dane były dostępne każdemu, kto pominął
        interfejs i uderzył prosto w API. Strażnik stoi więc po stronie
        serwera i domyślnie odmawia.
        """
        if sciezka in PUBLICZNE:
            return None                              # wolna ścieżka
        profil = self._profil()
        if profil is None:
            self._oproznij_cialo()
            _json(self, {"blad": "Wymagane zalogowanie.",
                         "wymaga_logowania": True}, 401)
            return False
        return profil

    def _oproznij_cialo(self) -> None:
        """Dokończenie odczytu żądania przed odmową.

        ⚠️ ZMIERZONE 16.08.2026, NIE OSTROŻNOŚĆ.
        Odmowa 401 na wgrywaniu pliku była wysyłana BEZ odczytania ciała
        żądania — plik nadal płynął do serwera. Windows zrywał wtedy
        połączenie i klient dostawał `ConnectionAbortedError` zamiast
        czytelnego 401. Objawiało się to testem, który padał raz na kilka
        przebiegów; użytkownik zobaczyłby „błąd połączenia" zamiast
        „zaloguj się".

        Czytamy w kawałkach i z górnym limitem: przy wielkim pliku nie ma
        sensu wciągać wszystkiego, żeby to wyrzucić, ale kilkadziesiąt
        kilobajtów wystarcza, by klient zdążył dopchnąć bufor i odczytać
        odpowiedź zamiast zobaczyć zerwane połączenie.

        ⚠️ TYLKO GDY CIAŁO NIE ZOSTAŁO JESZCZE ODCZYTANE.
        `do_POST` czyta je przez `_cialo()` PRZED wywołaniem strażnika,
        więc dla zwykłych żądań JSON strumień jest już pusty. Ponowny
        odczyt czekałby na bajty, które nigdy nie przyjdą, i kończył się
        timeoutem — co sam sobie tutaj zafundowałem przy pierwszym
        podejściu do tej naprawy.
        """
        if getattr(self, "_cialo_odczytane", False):
            return
        try:
            zostalo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return
        limit = 256 * 1024
        while zostalo > 0 and limit > 0:
            porcja = self.rfile.read(min(8192, zostalo, limit))
            if not porcja:
                break
            zostalo -= len(porcja)
            limit -= len(porcja)

    # ── pomocnicze ──────────────────────────────────────────────────

    class BledneCialo(Exception):
        """Ciała żądania nie dało się odczytać — z konkretnym powodem."""

    def _cialo(self) -> dict:
        """Odczyt JSON-a z żądania.

        Błąd dekodowania podnosi wyjątek z jednoznacznym komunikatem,
        zamiast zwracać pusty słownik. Wcześniejsza wersja zwracała {},
        przez co żądanie z niepoprawnym kodowaniem dostawało odpowiedź
        „nazwa i treść są wymagane" — komunikat mylący, bo pola były
        wypełnione. Przy wklejaniu polskich pism to nie jest przypadek
        brzegowy, tylko codzienność.
        """
        dlugosc = int(self.headers.get("Content-Length") or 0)
        self._cialo_odczytane = True
        if not dlugosc:
            return {}
        surowe = self.rfile.read(dlugosc)
        try:
            tekst = surowe.decode("utf-8")
        except UnicodeDecodeError as e:
            raise self.BledneCialo(
                "Treść żądania nie jest poprawnym UTF-8. Klient musi wysyłać "
                f"dane w UTF-8 (Content-Type: application/json; charset=utf-8). "
                f"Szczegół: {e}"
            ) from e
        try:
            dane = json.loads(tekst)
        except json.JSONDecodeError as e:
            raise self.BledneCialo(f"Niepoprawny JSON: {e}") from e
        if not isinstance(dane, dict):
            raise self.BledneCialo("Oczekiwano obiektu JSON.")
        return dane

    @staticmethod
    def _int_lub_none(wartosc):
        try:
            return int(wartosc) if wartosc not in (None, "", "null") else None
        except (TypeError, ValueError):
            return None

    def _plik_statyczny(self, nazwa: str):
        sciezka = (STATYCZNE / nazwa).resolve()
        # Zabezpieczenie przed wyjściem poza katalog statycznych.
        if not str(sciezka).startswith(str(STATYCZNE.resolve())) \
                or not sciezka.is_file():
            self.send_error(404)
            return
        typy = {".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8"}
        dane = sciezka.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",
                         typy.get(sciezka.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(dane)))
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(dane)

    # ── GET ─────────────────────────────────────────────────────────

    def do_GET(self):                            # noqa: N802
        trasa = urlparse(self.path)
        sciezka = trasa.path
        zapytanie = parse_qs(trasa.query)

        if sciezka in ("/", "/index.html"):
            return self._plik_statyczny("index.html")

        if sciezka == "/api/profil/stan":
            # Odpowiada ZAWSZE 200 — przeglądarka pyta o to przy starcie,
            # żeby wiedzieć, czy pokazać ekran logowania. Brak sesji nie
            # jest tu błędem, tylko stanem.
            p = self._profil()
            return _json(self, {
                "zalogowany": p is not None,
                "mfa": mod_profile.stan_mfa(DB, p.id) if p else None,
                "profil": ({"login": p.login, "imie": p.imie,
                            "nazwisko": p.nazwisko, "rola": p.rola}
                           if p else None),
                "sa_profile": mod_profile.ilu(DB) > 0,
            })

        if sciezka == "/api/profil/zgody":
            # Panel renderuje listę Z TEGO ŹRÓDŁA, zamiast trzymać własną
            # kopię — inaczej ekran i walidacja rozjechałyby się przy
            # pierwszej zmianie treści oświadczeń.
            return _json(self, {"wersja": mod_profile.ZGODY_WERSJA,
                                "zgody": list(mod_profile.ZGODY)})

        if (profil := self._wpuszczony(sciezka)) is False:
            return None

        if sciezka == "/api/sprawy":
            return _json(self, {"sprawy": baza.lista_spraw(DB)})

        m = re.fullmatch(r"/api/sprawy/(\d+)/dokumenty", sciezka)
        if m:
            sprawa_id = int(m.group(1))
            return _json(self, {"dokumenty": baza.lista_dokumentow(DB, sprawa_id)})

        m = re.fullmatch(r"/api/sprawy/(\d+)/dokumenty/(\d+)", sciezka)
        if m:
            sprawa_id, dok_id = int(m.group(1)), int(m.group(2))
            dok = baza.pobierz_dokument(DB, sprawa_id, dok_id)
            if dok is None:
                # Dokument z innej sprawy jest nieodróżnialny od
                # nieistniejącego — celowo.
                return _json(self, {"blad": "Nie znaleziono dokumentu "
                                            "w tej sprawie."}, 404)
            return _json(self, {"dokument": dok})

        m = re.fullmatch(r"/api/sprawy/(\d+)/watki", sciezka)
        if m:
            return _json(self, {"watki": baza.lista_watkow(DB, int(m.group(1)))})

        m = re.fullmatch(r"/api/sprawy/(\d+)/watki/(\d+)", sciezka)
        if m:
            sprawa_id, watek_id = int(m.group(1)), int(m.group(2))
            watek = baza.pobierz_watek(DB, sprawa_id, watek_id)
            if watek is None:
                # Wątek z innej sprawy jest nieodróżnialny od nieistniejącego.
                return _json(self, {"blad": "Nie znaleziono wątku w tej sprawie."}, 404)
            return _json(self, {
                "watek": watek,
                "wiadomosci": baza.historia_watku(DB, sprawa_id, watek_id)})

        m = re.fullmatch(r"/api/sprawy/(\d+)/czat", sciezka)
        if m:
            sprawa_id = int(m.group(1))
            dok_id = self._int_lub_none((zapytanie.get("dokument_id") or [None])[0])
            return _json(self, {"wiadomosci": baza.historia(DB, sprawa_id, dok_id)})

        if sciezka == "/api/przepisy":
            return _json(self, {"przepisy": mod_przepisy.lista(DB)})

        m = re.fullmatch(r"/api/przepisy/(\d+)", sciezka)
        if m:
            p = mod_przepisy.pobierz(DB, int(m.group(1)))
            if p is None:
                return _json(self, {"blad": "Nie znaleziono przepisu."}, 404)
            return _json(self, {"przepis": p})

        m = re.fullmatch(r"/api/zadania/([0-9a-f]+)", sciezka)
        if m:
            stan = KOLEJKA.stan(m.group(1))
            if stan is None:
                return _json(self, {"blad": "Nieznane zadanie."}, 404)
            return _json(self, stan)

        # Katalog reguł terminów. Stan zatwierdzenia jest tu polem
        # pierwszej klasy, a nie przypisem: reguła bez podpisu prawnika
        # wystawia termin NIEWIĄŻĄCY i prawnik ma to widzieć, zanim
        # zaplanuje na nim czynność procesową (ADR-0005).
        if sciezka == "/api/terminy/reguly":
            try:
                return _json(self, {"reguly": mod_terminy.katalog()})
            except mod_terminy.BladRegul as e:
                return _json(self, {"blad": str(e)}, 500)

        if sciezka == "/api/kopie":
            return _json(self, {
                "kopie": mod_kopia.lista(KATALOG_KOPII),
                "katalog": str(KATALOG_KOPII),
                "ile_trzymamy": mod_kopia.ILE_TRZYMAMY,
            })

        if sciezka == "/api/dziennik":
            dni = self._int_lub_none((zapytanie.get("dni") or [None])[0]) or 7
            return _json(self, {
                "zbiorczo": mod_dziennik.zbiorczo(DB, dni=dni),
                "ostatnie": mod_dziennik.ostatnie(DB, limit=50),
            })

        # Strategia i przewidywany czas dla liczby zaznaczonych dokumentów.
        # Liczone po stronie serwera, żeby podpowiedź w interfejsie i droga,
        # którą system faktycznie pójdzie, pochodziły z JEDNEGO źródła
        # (`agent.strategia`, wartości zmierzone 15.08.2026).
        if sciezka == "/api/strategia":
            try:
                ile = int((zapytanie.get("dokumentow") or ["0"])[0])
            except ValueError:
                ile = 0
            return _json(self, agent.strategia(ile))

        if sciezka == "/api/audyt":
            wiersze = DB.execute(
                "SELECT * FROM audyt ORDER BY id DESC LIMIT 100"
            ).fetchall()
            ok, opis = baza.zweryfikuj_lancuch_audytu(DB)
            return _json(self, {"wpisy": [dict(w) for w in wiersze],
                                "lancuch_spojny": ok, "opis": opis})

        self.send_error(404)

    # ── POST ────────────────────────────────────────────────────────

    def do_POST(self):                           # noqa: N802
        sciezka = urlparse(self.path).path

        # ⚠️ WGRYWANIE PLIKU MUSI BYĆ ROZPATRZONE PRZED `_cialo()`.
        #    `_cialo` czyta całe żądanie i próbuje zdekodować je jako
        #    UTF-8 — na pliku binarnym zwróciłoby błąd, a strumień
        #    byłby już wyczerpany.
        m = re.fullmatch(r"/api/sprawy/(\d+)/dokumenty/plik", sciezka)
        if m:
            if (profil := self._wpuszczony(sciezka)) is False:
                return None
            return self._wgraj_plik(int(m.group(1)), profil)

        try:
            dane = self._cialo()
        except self.BledneCialo as e:
            return _json(self, {"blad": str(e)}, 400)

        # ── profile ─────────────────────────────────────────────────
        if sciezka == "/api/profil/rejestracja":
            try:
                profil = mod_profile.zaloz(
                    DB,
                    login=dane.get("login") or "",
                    haslo=dane.get("haslo") or "",
                    imie=dane.get("imie") or "",
                    nazwisko=dane.get("nazwisko") or "",
                    rola=dane.get("rola") or "",
                    zgody=dane.get("zgody") or [])
            except mod_profile.BladProfilu as e:
                return _json(self, {"blad": str(e)}, 400)
            # Rejestracja loguje od razu — ustalenie: bez potwierdzania
            # adresem, bo system nie ma i nie ma mieć poczty.
            token = mod_profile.otworz_sesje(DB, profil)
            # Wersja oświadczeń w audycie: bez niej wpis mówi „przyjął",
            # ale nie mówi CO przyjął, a to jest cała wartość dowodowa.
            baza.zapisz_audyt(
                DB, "profil.zalozenie",
                szczegol=(f"login={profil.login} rola={profil.rola} "
                          f"oswiadczenia={mod_profile.ZGODY_WERSJA}"))
            return _json(self, {"profil": {"login": profil.login,
                                           "imie": profil.imie,
                                           "nazwisko": profil.nazwisko,
                                           "rola": profil.rola}},
                         201, ciastko=token)

        if sciezka == "/api/profil/logowanie":
            # Dławienie serii nieudanych prób. 429, a nie 401, bo to inna
            # informacja: nie „złe hasło", tylko „nie sprawdzam teraz".
            # Komunikat jest identyczny dla loginu istniejącego i nie,
            # więc blokada nie zdradza, które konta istnieją.
            try:
                profil = mod_profile.uwierzytelnij(
                    DB, dane.get("login") or "", dane.get("haslo") or "")
            except mod_profile.BlokadaLogowania as e:
                baza.zapisz_audyt(DB, "profil.logowanie.dlawienie",
                                  szczegol=f"pozostalo_s={e.sekundy}")
                return _json(self, {"blad": str(e), "ponow_za_s": e.sekundy}, 429)
            if profil is None:
                # Jeden komunikat na oba przypadki — inaczej odpowiedź
                # zdradzałaby, które loginy istnieją.
                baza.zapisz_audyt(DB, "profil.logowanie.odmowa")
                return _json(self, {"blad": "Nieprawidłowy login lub hasło."}, 401)

            # ── drugi składnik ──────────────────────────────────────
            #
            # ⚠️ SESJA POWSTAJE DOPIERO PO OBU SKŁADNIKACH.
            #
            # Wydanie ciasteczka po samym haśle i sprawdzanie kodu
            # „w następnym kroku" dawałoby ważną sesję komuś, kto zna
            # wyłącznie hasło — drugi składnik byłby wtedy ekranem
            # do pominięcia, a nie składnikiem uwierzytelnienia.
            if mod_profile.wymaga_drugiego_skladnika(DB, profil):
                kod = (dane.get("kod") or "").strip()
                if not kod:
                    return _json(self, {"wymaga_kodu": True,
                                        "blad": "Podaj kod z aplikacji."}, 401)
                if not mod_profile.sprawdz_drugi_skladnik(DB, profil, kod):
                    mod_profile.zapisz_nieudana(DB, profil.login)
                    baza.zapisz_audyt(DB, "profil.mfa.odmowa",
                                      szczegol=f"login={profil.login}")
                    return _json(self, {"wymaga_kodu": True,
                                        "blad": "Kod nie pasuje."}, 401)
                mod_profile.wyczysc_proby(DB, profil.login)

            token = mod_profile.otworz_sesje(DB, profil)
            baza.zapisz_audyt(DB, "profil.logowanie",
                              szczegol=f"login={profil.login}")
            return _json(self, {"profil": {"login": profil.login,
                                           "imie": profil.imie,
                                           "nazwisko": profil.nazwisko,
                                           "rola": profil.rola}},
                         200, ciastko=token)

        # ── drugi składnik ──────────────────────────────────────────
        if sciezka in ("/api/profil/mfa/przygotuj", "/api/profil/mfa/wlacz",
                       "/api/profil/mfa/wylacz"):
            profil = self._profil()
            if profil is None:
                return _json(self, {"blad": "Wymagane zalogowanie.",
                                    "wymaga_logowania": True}, 401)

            if sciezka.endswith("przygotuj"):
                sekret, adres = mod_profile.przygotuj_mfa(DB, profil)
                baza.zapisz_audyt(DB, "profil.mfa.przygotowany",
                                  szczegol=f"login={profil.login}")
                # Sekret wraca RAZ, do pokazania w kodzie QR. Panel nie
                # udostępnia go ponownie — od tego są kody zapasowe.
                return _json(self, {"sekret": sekret, "adres": adres})

            if sciezka.endswith("wlacz"):
                try:
                    kody = mod_profile.wlacz_mfa(DB, profil,
                                                 dane.get("kod") or "")
                except mod_profile.BladProfilu as e:
                    return _json(self, {"blad": str(e)}, 400)
                baza.zapisz_audyt(DB, "profil.mfa.wlaczony",
                                  szczegol=f"login={profil.login}")
                return _json(self, {"kody_zapasowe": kody})

            mod_profile.wylacz_mfa(DB, profil)
            baza.zapisz_audyt(DB, "profil.mfa.wylaczony",
                              szczegol=f"login={profil.login}")
            return _json(self, {"wylaczony": True})

        if sciezka == "/api/profil/wylogowanie":
            mod_profile.zamknij_sesje(DB, self._token())
            return _json(self, {"wylogowano": True}, 200, skasuj_ciastko=True)

        if (profil := self._wpuszczony(sciezka)) is False:
            return None

        # ⚠️ TERMIN LICZY KOD, NIE MODEL (ADR-0005).
        #
        # Ten endpoint nie dotyka Ollamy ani jednym wywołaniem. Datę
        # zdarzenia wpisuje prawnik, resztę robi arytmetyka na regułach
        # z pliku YAML. To jedyna funkcja systemu, w której błąd ma
        # bezpośredni skutek prawny — i jedyna, z której model jest
        # celowo wyłączony.
        # ⚠️ KOPIA JEST SPRAWDZANA ODCZYTEM, NIE TYLKO ZAPISYWANA.
        #
        # `kopia.wykonaj` otwiera zapisany plik, sprawdza spójność
        # i porównuje liczniki z oryginałem. Niepowodzenie kasuje plik:
        # w dniu awarii nikt nie sprawdza, czy najnowszy plik w katalogu
        # jest dobry — bierze się najnowszy.
        if sciezka == "/api/kopie":
            try:
                wynik = mod_kopia.wykonaj(DB, KATALOG_KOPII)
            except mod_kopia.BladKopii as e:
                baza.zapisz_audyt(DB, "kopia.blad", szczegol=str(e)[:200])
                return _json(self, {"blad": str(e)}, 500)
            baza.zapisz_audyt(
                DB, "kopia.wykonana",
                szczegol=(f"plik={wynik.sciezka.name} mb={wynik.megabajtow} "
                          f"sekund={wynik.sekund} "
                          f"osoba={getattr(profil, 'login', '?')}"))
            return _json(self, {
                "nazwa": wynik.sciezka.name,
                "megabajtow": wynik.megabajtow,
                "sekund": wynik.sekund,
                "liczniki": wynik.liczniki,
            }, 201)

        # ── ODTWORZENIE Z KOPII ─────────────────────────────────────
        #
        # ⚠️ NAJBARDZIEJ NISZCZĄCA OPERACJA W CAŁYM PANELU: podmienia
        # całą bazę akt. Dlatego trzy niezależne warunki, z których
        # każdy blokuje osobno.
        #
        # Do 16.08.2026 `kopia.odtworz()` istniało i było przetestowane,
        # ale nie miało drogi z panelu — odtworzenie było czynnością
        # programistyczną. Deklarowane RTO ≤ 8 h nie miało pokrycia,
        # bo w dniu awarii nikt nie uruchamia Pythona z konsoli.
        m = re.fullmatch(r"/api/kopie/([\w.\-]+)/odtworz", sciezka)
        if m:
            nazwa = m.group(1)

            # 1. Rola. Sekretariat i aplikant nie nadpisują akt kancelarii.
            if getattr(profil, "rola", None) != "prawnik":
                return _json(self, {
                    "blad": "Odtworzenie bazy może wykonać wyłącznie "
                            "prawnik prowadzący."}, 403)

            # 2. Trwające zadanie. Podmiana bazy pod pracującą analizą
            #    zostawiłaby wynik zapisany do bazy, której już nie ma.
            if KOLEJKA.ile_czeka():
                return _json(self, {
                    "blad": "Trwa analiza. Odtworzenie jest możliwe "
                            "dopiero po jej zakończeniu."}, 409)

            # 3. Przepisanie nazwy pliku. Kliknięcie „OK" da się zrobić
            #    odruchowo; przepisanie nazwy — nie.
            if (dane.get("potwierdzenie") or "").strip() != nazwa:
                return _json(self, {
                    "blad": f"Aby potwierdzić, przepisz dokładnie nazwę "
                            f"pliku kopii: {nazwa}"}, 400)

            plik = KATALOG_KOPII / nazwa
            if not plik.exists() or plik.parent != KATALOG_KOPII:
                return _json(self, {"blad": "Nie ma takiej kopii."}, 404)

            przed = len(baza.lista_spraw(DB))
            try:
                # Połączenie musi być zamknięte PRZED podmianą pliku —
                # inaczej otwarty uchwyt wskazywałby nieistniejące już
                # dane, a Windows nie pozwoliłby nadpisać pliku.
                DB.close()
                liczniki = mod_kopia.odtworz(plik, SCIEZKA_DB)
            except mod_kopia.BladKopii as e:
                globals()["DB"] = baza.polacz(SCIEZKA_DB)
                baza.zapisz_audyt(DB, "kopia.odtworzenie.blad",
                                  szczegol=f"plik={nazwa} {str(e)[:160]}")
                return _json(self, {"blad": str(e)}, 400)

            globals()["DB"] = baza.polacz(SCIEZKA_DB)
            po = len(baza.lista_spraw(DB))
            baza.zapisz_audyt(
                DB, "kopia.odtworzenie",
                szczegol=(f"plik={nazwa} spraw_przed={przed} spraw_po={po} "
                          f"osoba={getattr(profil, 'login', '?')}"))
            return _json(self, {"odtworzono": nazwa, "liczniki": liczniki,
                                "spraw_przed": przed, "spraw_po": po})

        if sciezka == "/api/terminy/oblicz":
            try:
                wynik = mod_terminy.policz(
                    regula_id=dane.get("regula_id") or "",
                    data_zdarzenia=dane.get("data_zdarzenia") or "",
                    dokument_id=dane.get("dokument_id") or "",
                    poczatek=dane.get("poczatek") or 0,
                    koniec=dane.get("koniec") or 0)
            except mod_terminy.BladRegul as e:
                return _json(self, {"blad": str(e)}, 400)
            baza.zapisz_audyt(
                DB, "termin.policzony",
                self._int_lub_none(dane.get("sprawa_id")),
                f"regula={wynik['regula_id']} uplyw={wynik['data_uplywu']} "
                f"status={wynik['status']}")
            return _json(self, wynik)

        # ⚠️ EKSPORT WYNOSI TREŚĆ AKT POZA BAZĘ.
        #
        # Plik zapisany na pulpicie nie jest chroniony niczym poza
        # szyfrowaniem nośnika. To czynność, którą trzeba móc odtworzyć,
        # więc idzie do audytu — z liczbą ustaleń, nigdy z treścią (T-4).
        m = re.fullmatch(r"/api/sprawy/(\d+)/eksport", sciezka)
        if m:
            sprawa_id = int(m.group(1))
            wynik = dane.get("wynik")
            if not isinstance(wynik, dict):
                return _json(self, {"blad": "Brak wyniku do wyeksportowania."}, 400)

            sprawa = next((s for s in baza.lista_spraw(DB)
                           if int(s["id"]) == sprawa_id), None)
            if sprawa is None:
                return _json(self, {"blad": "Nie znaleziono sprawy."}, 404)

            format_ = (dane.get("format") or "md").lower()
            if format_ not in ("md", "html"):
                return _json(self, {"blad": "Format: md albo html."}, 400)

            osoba = getattr(profil, "podpis", "") if profil else ""
            tresc = (mod_eksport.do_html(wynik, sprawa["sygnatura"], osoba)
                     if format_ == "html"
                     else mod_eksport.do_markdown(wynik, sprawa["sygnatura"], osoba))

            baza.zapisz_audyt(
                DB, "analiza.eksport", sprawa_id,
                f"format={format_} ustalen={len(wynik.get('ustalenia') or [])} "
                f"osoba={getattr(profil, 'login', '?')}")
            return _json(self, {
                "nazwa": mod_eksport.nazwa_pliku(sprawa["sygnatura"], format_),
                "tresc": tresc,
                "typ": "text/html" if format_ == "html" else "text/markdown",
            })

        m = re.fullmatch(r"/api/sprawy/(\d+)/watki", sciezka)
        if m:
            sprawa_id = int(m.group(1))
            watek_id = baza.zaloz_watek(
                DB, sprawa_id,
                tytul=dane.get("tytul") or "",
                dokument_id=self._int_lub_none(dane.get("dokument_id")),
                profil_id=profil.id if profil else None)
            baza.zapisz_audyt(DB, "watek.zalozenie", sprawa_id,
                              szczegol=f"watek={watek_id}")
            return _json(self, {"watek": baza.pobierz_watek(
                DB, sprawa_id, watek_id)}, 201)

        m = re.fullmatch(r"/api/sprawy/(\d+)/watki/(\d+)", sciezka)
        if m:
            sprawa_id, watek_id = int(m.group(1)), int(m.group(2))
            zamkniety = dane.get("zamkniety")
            zmieniono = baza.zmien_watek(
                DB, sprawa_id, watek_id,
                tytul=dane.get("tytul"),
                zamkniety=None if zamkniety is None else bool(zamkniety))
            if not zmieniono:
                return _json(self, {"blad": "Nie znaleziono wątku w tej sprawie."}, 404)
            return _json(self, {"watek": baza.pobierz_watek(
                DB, sprawa_id, watek_id)})

        if sciezka == "/api/sprawy":
            sygnatura = (dane.get("sygnatura") or "").strip()
            nazwa = (dane.get("nazwa") or "").strip()
            if not sygnatura or not nazwa:
                return _json(self, {"blad": "Sygnatura i nazwa są wymagane."}, 400)

            # ⚠️ SYGNATURA IDENTYFIKUJE SPRAWĘ — DUPLIKAT TO ZWYKLE POMYŁKA.
            #
            # Wykryte przeglądem interfejsu 16.08.2026: lista pokazywała
            # kilka spraw o tej samej sygnaturze i nic tego nie sygnalizowało.
            # Dla prawnika oznacza to pytanie „która jest ta właściwa", a przy
            # zamknięciu zakresu w obrębie sprawy — realne ryzyko, że pytanie
            # trafi do niepełnego kompletu akt.
            #
            # NIE blokujemy na twardo: bywa, że kancelaria świadomie zakłada
            # drugi rekord (np. odrębne postępowanie o tej samej sygnaturze
            # przed innym organem). Wymagamy natomiast POTWIERDZENIA, żeby
            # duplikat powstawał świadomie, a nie przez przeoczenie.
            if not dane.get("mimo_duplikatu"):
                istniejace = [s for s in baza.lista_spraw(DB)
                              if (s["sygnatura"] or "").strip().casefold()
                              == sygnatura.casefold()]
                if istniejace:
                    return _json(self, {
                        "blad": (f"Sprawa o sygnaturze {sygnatura} już "
                                 f"istnieje: "
                                 f"„{istniejace[0]['nazwa']}”."),
                        "duplikat": True,
                        "istniejaca": {"id": istniejace[0]["id"],
                                       "nazwa": istniejace[0]["nazwa"]},
                    }, 409)

            sprawa_id = baza.dodaj_sprawe(
                DB, sygnatura, nazwa,
                organ=dane.get("organ", ""), rodzaj=dane.get("rodzaj", "karna"),
                etap=dane.get("etap", ""), prowadzacy=dane.get("prowadzacy", ""),
                poufnosc=dane.get("poufnosc", "standardowa"),
            )
            return _json(self, {"id": sprawa_id}, 201)

        m = re.fullmatch(r"/api/sprawy/(\d+)/dokumenty", sciezka)
        if m:
            sprawa_id = int(m.group(1))
            nazwa = (dane.get("nazwa") or "").strip()
            tresc = dane.get("tresc") or ""
            if not nazwa or not tresc.strip():
                return _json(self, {"blad": "Nazwa i treść są wymagane."}, 400)
            try:
                dok_id = baza.dodaj_dokument(
                    DB, sprawa_id, nazwa, tresc,
                    rodzaj=dane.get("rodzaj", "pismo"),
                    zrodlo_tekstu=mod_wczytywanie.ZRODLO_WKLEJONY)
            except ValueError as e:
                return _json(self, {"blad": str(e)}, 404)
            return _json(self, {"id": dok_id}, 201)

        m = re.fullmatch(r"/api/sprawy/(\d+)/czat", sciezka)
        if m:
            return self._czat(int(m.group(1)), dane, profil)

        m = re.fullmatch(r"/api/sprawy/(\d+)/analiza", sciezka)
        if m:
            return self._analiza(int(m.group(1)), dane, profil)

        if sciezka == "/api/przepisy":
            try:
                pid = mod_przepisy.dodaj(
                    DB,
                    akt=dane.get("akt", ""), jednostka=dane.get("jednostka", ""),
                    tresc=dane.get("tresc", ""), zrodlo=dane.get("zrodlo", ""),
                    zweryfikowal=dane.get("zweryfikowal", ""),
                )
            except ValueError as e:
                return _json(self, {"blad": str(e)}, 400)
            baza.zapisz_audyt(DB, "dodanie_przepisu", None,
                              f"{dane.get('akt')} {dane.get('jednostka')}")
            return _json(self, {"id": pid}, 201)

        self.send_error(404)

    def _analiza(self, sprawa_id: int, dane: dict, profil=None):
        """Głęboka analiza jako zadanie w tle.

        Zwraca natychmiast identyfikator zadania. Panel odpytuje
        /api/zadania/{id} o postęp — analiza stu dokumentów trwa
        i użytkownik musi widzieć, na którym dokumencie stoi praca.
        """
        if baza.pobierz_sprawe(DB, sprawa_id) is None:
            return _json(self, {"blad": "Sprawa nie istnieje."}, 404)

        pytanie = (dane.get("pytanie") or "").strip()
        if not pytanie:
            return _json(self, {"blad": "Puste pytanie."}, 400)

        dok_id = self._int_lub_none(dane.get("dokument_id"))
        if dok_id is not None and baza.pobierz_dokument(DB, sprawa_id, dok_id) is None:
            return _json(self, {"blad": "Dokument nie należy do tej sprawy."}, 404)

        # ── ZAMKNIĘCIE ZAKRESU — akta wyłącznie z tej sprawy ────────
        dokumenty = baza.tresci_dokumentow(DB, sprawa_id, dok_id)

        # ⚠️ ZAZNACZENIE KWADRACIKAMI JEST DECYZJĄ PRAWNIKA.
        #
        # Gdy panel poda listę `dokumenty_id`, zawężamy do niej i NIE
        # pozwalamy systemowi obciąć jej po swojemu. Prawnik, który
        # zaznaczył sześć dokumentów, ma dostać analizę z sześciu —
        # ciche obcięcie do czterech dałoby węższą, niż zamówił.
        #
        # Sprawdzenie przynależności każdego dokumentu do sprawy jest tu
        # warunkiem, nie ostrożnością: bez niego lista z żądania byłaby
        # drogą do akt innej sprawy, z pominięciem zamknięcia zakresu.
        wybrane_id = dane.get("dokumenty_id") or []
        if wybrane_id:
            dozwolone = set()
            obce = []
            for surowy in wybrane_id:
                did = self._int_lub_none(surowy)
                if did is None or baza.pobierz_dokument(DB, sprawa_id, did) is None:
                    obce.append(str(surowy))
                    continue
                dozwolone.add(str(did))
            # ⚠️ KOMUNIKAT MUSI MÓWIĆ, CO ZROBIĆ.
            #
            # Sama odmowa jest poprawna — to zamknięcie zakresu. Ale
            # „Dokument nie należy do tej sprawy" bez wskazówki zostawiało
            # prawnika bez wyjścia: zaznaczenie pochodziło z POPRZEDNIEJ
            # sprawy, więc w bieżącej nie było czego odznaczyć. Panel
            # czyści je teraz przy zmianie sprawy, a ten komunikat zostaje
            # dla wywołań spoza interfejsu.
            if obce:
                return _json(self, {
                    "blad": (f"{len(obce)} z zaznaczonych dokumentów nie należy "
                             f"do tej sprawy. Wyczyść zaznaczenie i wskaż "
                             f"dokumenty z bieżącej sprawy."),
                    "obce_dokumenty": obce[:10],
                    "wyczysc_zaznaczenie": True,
                }, 404)
            dokumenty = {k: v for k, v in dokumenty.items() if k in dozwolone}
            if not dokumenty:
                return _json(self, {"blad": "Zaznaczone dokumenty są puste."}, 400)

        nazwy = {str(d["id"]): d["nazwa"]
                 for d in baza.lista_dokumentow(DB, sprawa_id)}
        # Język rozpoznany przy wgraniu — steruje doborem modelu mapowania.
        jezyki = baza.jezyki_dokumentow(DB, sprawa_id)
        # Pochodzenie tekstu — trafia na każdy cytat, patrz `analiza.analizuj`.
        zrodla = baza.zrodla_dokumentow(DB, sprawa_id)
        # ────────────────────────────────────────────────────────────

        # Przepisy to ODRĘBNA przestrzeń — jawna, wspólna dla spraw,
        # przekazywana osobnym parametrem, weryfikowana osobno.
        uzyj_przepisow = bool(dane.get("uzyj_przepisow", True))
        wybrane_p = dane.get("przepisy_id") or None
        tresci_p = mod_przepisy.tresci(DB, wybrane_p) if uzyj_przepisow else None
        nazwy_p = mod_przepisy.nazwy(DB, wybrane_p) if uzyj_przepisow else None

        # Wątek opcjonalny — bez niego rozmowa idzie w dotychczasowy ciąg
        # sprawy, więc starsze wywołania działają bez zmian.
        watek_id = self._int_lub_none(dane.get("watek_id"))
        if watek_id is not None:
            watek = baza.pobierz_watek(DB, sprawa_id, watek_id)
            if watek is None:
                return _json(self, {"blad": "Wątek nie należy do tej sprawy."}, 404)
            if watek.get("zamkniety"):
                return _json(self, {"blad": "Wątek jest zamknięty. "
                                            "Wznów go, aby kontynuować."}, 409)

        baza.dodaj_wiadomosc(DB, sprawa_id, "uzytkownik", pytanie, dok_id,
                             profil_id=profil.id if profil else None,
                             watek_id=watek_id)
        profil_id = profil.id if profil else None

        def praca(melduj):
            _start = time.perf_counter()
            wynik = analiza.analizuj(
                pytanie, dokumenty, nazwy,
                przepisy=tresci_p or None, nazwy_przepisow=nazwy_p,
                postep=melduj, jezyki=jezyki, zrodla=zrodla,
            )
            slownik = wynik.na_slownik()
            if not wynik.blad:
                self._zapisz_analize(
                    sprawa_id, dok_id, slownik,
                    watek_id=watek_id, profil_id=profil_id,
                    pytanie=pytanie,
                    czas_ms=int((time.perf_counter() - _start) * 1000))
            return slownik

        zadanie_id = KOLEJKA.uruchom(praca)
        baza.zapisz_audyt(DB, "uruchomienie_analizy", sprawa_id,
                          f"dok={dok_id} zadanie={zadanie_id}")
        return _json(self, {"zadanie_id": zadanie_id}, 202)

    @staticmethod
    def _zapisz_analize(sprawa_id: int, dok_id: int | None, wynik: dict,
                        watek_id: int | None = None,
                        profil_id: int | None = None,
                        pytanie: str = "", czas_ms: int = 0):
        """Wynik analizy trafia do historii wątku jako wiadomość."""
        cytaty = [c for u in wynik.get("ustalenia", []) for c in u.get("cytaty", [])]
        streszczenie = (
            "\n".join(f"• {u['tekst']}" for u in wynik.get("ustalenia", []))
            or "Brak ustaleń z pokryciem w aktach."
        )
        baza.dodaj_wiadomosc(
            DB, sprawa_id, "asystent", streszczenie, dok_id,
            cytaty_json=json.dumps(cytaty, ensure_ascii=False),
            odrzucone_json=json.dumps(wynik.get("odrzucone", []),
                                      ensure_ascii=False),
            watek_id=watek_id, profil_id=profil_id,
        )
        # ⚠️ DZIENNIK MUSI WIDZIEĆ TOR, Z KTÓREGO KORZYSTA PANEL.
        #
        # Do 17.08.2026 wpis powstawał WYŁĄCZNIE w torze szybkim
        # (`_czat`), a przycisk „Analizuj akta" chodzi tą ścieżką.
        # Skutek: widok „Dziennik kontroli" pokazywał „Brak zapytań
        # w ostatnich 7 dniach" mimo realnej pracy na aktach — czyli
        # narzędzie mające wykrywać pogorszenie jakości nie obserwowało
        # drogi, którą system faktycznie chodzi. Wykryte przeklikaniem
        # panelu, nie testem.
        #
        # Ta sama ochrona co w torze szybkim: awaria dziennika nie może
        # zabrać prawnikowi gotowej analizy.
        try:
            mod_dziennik.zapisz(
                DB, pytanie or "(analiza)",
                mod_dziennik.z_odpowiedzi(
                    {"cytaty": cytaty, "odrzucone": wynik.get("odrzucone", [])},
                    sprawa_id, "gleboki",
                    model=wynik.get("model") or "", czas_ms=czas_ms))
        except Exception as e:                                # noqa: BLE001
            baza.zapisz_audyt(DB, "blad_dziennika", sprawa_id,
                              f"{type(e).__name__}: {e}"[:200])

        baza.zapisz_audyt(
            DB, "analiza_zakonczona", sprawa_id,
            f"ustaleń={len(wynik.get('ustalenia', []))} "
            f"wniosków={len(wynik.get('wnioski', []))} "
            f"odrzuconych={len(wynik.get('odrzucone', []))}",
        )

    def _czat(self, sprawa_id: int, dane: dict, profil=None):
        """Rozmowa zamknięta w obrębie jednej sprawy.

        Kluczowy fragment całego panelu: kontekst dla modelu i zbiór
        dla weryfikatora pochodzą z tego samego, zawężonego zapytania.
        Cytat z innej sprawy nie ma jak przejść — nie ma go w zbiorze,
        wobec którego prowadzona jest weryfikacja.
        """
        if baza.pobierz_sprawe(DB, sprawa_id) is None:
            return _json(self, {"blad": "Sprawa nie istnieje."}, 404)

        pytanie = (dane.get("pytanie") or "").strip()
        if not pytanie:
            return _json(self, {"blad": "Puste pytanie."}, 400)

        dok_id = self._int_lub_none(dane.get("dokument_id"))
        if dok_id is not None and baza.pobierz_dokument(DB, sprawa_id, dok_id) is None:
            return _json(self, {"blad": "Dokument nie należy do tej sprawy."}, 404)

        # Wątek jest opcjonalny: bez niego rozmowa idzie w dotychczasowy
        # ciąg sprawy, więc stare wywołania nadal działają.
        watek_id = self._int_lub_none(dane.get("watek_id"))
        if watek_id is not None:
            watek = baza.pobierz_watek(DB, sprawa_id, watek_id)
            if watek is None:
                return _json(self, {"blad": "Wątek nie należy do tej sprawy."}, 404)
            if watek.get("zamkniety"):
                return _json(self, {"blad": "Wątek jest zamknięty. "
                                            "Wznów go, aby kontynuować."}, 409)
            dok_id = watek.get("dokument_id")

        # ── ZAMKNIĘCIE ZAKRESU ──────────────────────────────────────
        dokumenty = baza.tresci_dokumentow(DB, sprawa_id, dok_id)
        pamiec = (baza.historia_watku(DB, sprawa_id, watek_id)
                  if watek_id is not None
                  else baza.historia(DB, sprawa_id, dok_id))
        # ────────────────────────────────────────────────────────────

        baza.dodaj_wiadomosc(DB, sprawa_id, "uzytkownik", pytanie, dok_id,
                             profil_id=profil.id if profil else None,
                             watek_id=watek_id)
        _t0 = time.perf_counter()
        wynik = agent.odpowiedz(pytanie, dokumenty, pamiec)
        _czas_ms = int((time.perf_counter() - _t0) * 1000)

        if wynik["blad"]:
            baza.zapisz_audyt(DB, "blad_modelu", sprawa_id, wynik["blad"][:200])
            return _json(self, wynik, 503)

        baza.dodaj_wiadomosc(
            DB, sprawa_id, "asystent", wynik["tekst"], dok_id,
            cytaty_json=json.dumps(wynik["cytaty"], ensure_ascii=False),
            odrzucone_json=json.dumps(wynik["odrzucone"], ensure_ascii=False),
            profil_id=profil.id if profil else None,
            watek_id=watek_id,
        )
        baza.zapisz_audyt(
            DB, "zapytanie_do_akt", sprawa_id,
            f"dok={dok_id} cytatów={len(wynik['cytaty'])} "
            f"odrzuconych={len(wynik['odrzucone'])}",
        )
        # Dziennik kontroli — same liczby i skrót pytania, nigdy treść.
        # Pozwala wykryć degradację po zmianie modelu bez czekania
        # na pełny przebieg benchmarku (T-4: log rejestruje dostęp,
        # nie kopiuje treści).
        #
        # ⚠️ ZAPIS DZIENNIKA NIE MOŻE ZABRAĆ PRAWNIKOWI GOTOWEJ ODPOWIEDZI.
        #
        # Wyjątek z dziennika leciałby tutaj w górę i zamieniał poprawną,
        # zweryfikowaną odpowiedź — już policzoną, po kilkunastu sekundach
        # pracy modelu — w błąd 500. Dziennik jest narzędziem obserwacji,
        # a narzędzie obserwacji nie ma prawa zatrzymać obserwowanej pracy.
        # Niepowodzenie trafia do audytu, bo cichy brak wpisu wyglądałby
        # potem jak brak zapytania.
        try:
            mod_dziennik.zapisz(
                DB, pytanie,
                mod_dziennik.z_odpowiedzi(
                    wynik, sprawa_id, "szybki",
                    model=wynik.get("model") or agent.MODEL,
                    czas_ms=_czas_ms))
        except Exception as e:                                # noqa: BLE001
            baza.zapisz_audyt(DB, "blad_dziennika", sprawa_id,
                              f"{type(e).__name__}: {e}"[:200])
        return _json(self, wynik)

    # ── DELETE ──────────────────────────────────────────────────────

    def do_DELETE(self):                         # noqa: N802
        trasa = urlparse(self.path)
        sciezka, zapytanie = trasa.path, parse_qs(trasa.query)

        if self._wpuszczony(sciezka) is False:
            return None

        m = re.fullmatch(r"/api/sprawy/(\d+)/dokumenty/(\d+)", sciezka)
        if m:
            usunieto = baza.usun_dokument(DB, int(m.group(1)), int(m.group(2)))
            return _json(self, {"usunieto": usunieto}, 200 if usunieto else 404)

        m = re.fullmatch(r"/api/sprawy/(\d+)/watki/(\d+)", sciezka)
        if m:
            usunieto = baza.usun_watek(DB, int(m.group(1)), int(m.group(2)))
            return _json(self, {"usunieto": usunieto}, 200 if usunieto else 404)

        m = re.fullmatch(r"/api/sprawy/(\d+)/czat", sciezka)
        if m:
            dok_id = self._int_lub_none((zapytanie.get("dokument_id") or [None])[0])
            ile = baza.wyczysc_historie(DB, int(m.group(1)), dok_id)
            return _json(self, {"usunieto": ile})

        m = re.fullmatch(r"/api/przepisy/(\d+)", sciezka)
        if m:
            usunieto = mod_przepisy.usun(DB, int(m.group(1)))
            return _json(self, {"usunieto": usunieto}, 200 if usunieto else 404)

        self.send_error(404)


def main() -> int:
    serwer = ThreadingHTTPServer((HOST, PORT), Uchwyt)
    print("═" * 66)
    print("  PANEL SPRAW SĄDOWYCH — kancelaria-lex")
    print("═" * 66)
    print(f"  Adres:        http://{HOST}:{PORT}")
    print(f"  Model:        {analiza.MODEL} (lokalnie, {analiza.OLLAMA})")
    print(f"  Baza:         {baza.SCIEZKA_BAZY}")
    print(f"  Przepisy:     {len(mod_przepisy.lista(DB))} jednostek w korpusie")
    print()
    print("  Zakres analizy jest zamknięty w obrębie wybranej sprawy.")
    print("  Przepisy są odrębną, jawną przestrzenią — cytaty nie mieszają się.")
    print("  Nasłuch tylko na 127.0.0.1 — panel nie wystawia się do sieci.")
    print()
    print("  Zatrzymanie: Ctrl+C")
    print("═" * 66)
    try:
        serwer.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymano.")
    finally:
        serwer.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
