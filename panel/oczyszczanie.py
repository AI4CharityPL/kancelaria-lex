"""Oczyszczanie treści dokumentu przy wczytaniu — usuwanie znaczników.

ZMIERZONA PRZYCZYNA DOMINUJĄCEJ KLASY BŁĘDÓW (14.08.2026)

Orzeczenia pobrane z SAOS niosą surowy HTML. Skala:

    dokumentów z HTML            320 z 320   (100%)
    znaków będących znacznikami  2 508 613 z 16 317 895   (15,4%)
    zdań odrzuconych przez filtr jakości          78%
    z tego odrzuconych PRZEZ HTML                 75%

Skutek: **polski korpus tracił 78% zdań, zanim model je zobaczył.**
Nie dlatego, że były bezwartościowe — dlatego, że tonęły w znacznikach,
a filtr jakości słusznie uznawał je za śmieć.

Przykład zdania, które przepadało (niesie datę i sygnaturę wyroku SN):

    603 – 604 teza 3, także wyrok Sądu Najwyższego z dnia 23 lipca
    1974 r., sygn. akt V KR 212/74).</p></td></tr><tr>

Śledzenie pojedynczego przypadku z benchmarku doprowadziło do tego
przez trzy fałszywe tropy: najpierw wyglądało to na wadę modelu, potem
na zbyt ostre zakotwiczenie, potem na wadę wyszukiwarki. Dopiero
sprawdzenie, czy zdanie ze wzorcową datą w ogóle trafia do wsadu,
pokazało, że jest odsiewane wcześniej — na filtrze jakości.

DLACZEGO PRZY WCZYTANIU, A NIE PRZY ODCZYCIE

Cytat jest zakresem znaków w treści dokumentu (ADR-0006, ADR-0007).
Oczyszczanie przy odczycie przesuwałoby offsety względem tego, co jest
w bazie, i każdy zapisany cytat wskazywałby w złe miejsce. Treść musi
być czysta ZANIM powstaną jakiekolwiek offsety.
"""

from __future__ import annotations

import html
import re

# Znacznik musi mieć po „<" literę, ukośnik albo wykrzyknik — inaczej
# skasowalibyśmy „kwota < 1000 zł" albo „a < b" z opinii biegłego.
ZNACZNIK = re.compile(r"<[/!]?[a-zA-Z][^>]{0,400}>")

# Komentarze HTML — regexp znacznika ich nie łapie, bo po „<!" stoi
# myślnik, a nie litera. W eksportach z SAOS zostają jako „<!-- -->".
KOMENTARZ = re.compile(r"<!--.*?-->", re.DOTALL)

# Bloki, których treść jest bezwartościowa dla akt.
BLOK_DO_USUNIECIA = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

# Znaczniki, po których należy wymusić przerwę zdania — inaczej treść
# dwóch komórek tabeli sklei się w jedno bezsensowne zdanie.
PRZERWA_PO = re.compile(
    r"</(p|div|tr|td|th|li|h[1-6]|blockquote)\s*>|<br\s*/?>", re.IGNORECASE)


def zawiera_znaczniki(tekst: str) -> bool:
    return bool(ZNACZNIK.search(tekst))


def oczysc(tekst: str) -> str:
    """Usuwa znaczniki i encje, zachowując strukturę akapitów.

    Nie próbuje być parserem HTML — dokumenty procesowe to nie strony
    internetowe, tylko tekst z resztkami znaczników po eksporcie.
    Zależność od biblioteki zewnętrznej byłaby tu kosztem bez pokrycia
    (art. 21 ust. 2 lit. d ustawy o KSC — łańcuch dostaw).
    """
    if not tekst:
        return ""
    if not zawiera_znaczniki(tekst) and "&" not in tekst and "<!--" not in tekst:
        return tekst                       # nic do roboty — częsty przypadek

    t = KOMENTARZ.sub(" ", tekst)
    t = BLOK_DO_USUNIECIA.sub(" ", t)
    t = PRZERWA_PO.sub("\n", t)            # granica zdania, nie spacja
    t = ZNACZNIK.sub(" ", t)
    t = html.unescape(t)

    # Sprzątanie po usunięciu: spacje przed interpunkcją i puste linie.
    t = t.replace(" ", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" +([,.;:)])", r"\1", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def statystyka(tekst: str) -> dict:
    """Ile dana treść zyskuje na oczyszczeniu — do dziennika i testów."""
    czysty = oczysc(tekst)
    return {
        "przed": len(tekst),
        "po": len(czysty),
        "usuniete": len(tekst) - len(czysty),
        "udzial_usunietych": (len(tekst) - len(czysty)) / len(tekst) if tekst else 0.0,
        "mial_znaczniki": zawiera_znaczniki(tekst),
    }
