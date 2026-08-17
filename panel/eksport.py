"""Eksport wyniku analizy — dokument, który da się dołączyć do notatki.

════════════════════════════════════════════════════════════════════════
 PO CO
════════════════════════════════════════════════════════════════════════

Wynik analizy żył dotąd wyłącznie na ekranie. Prawnik, który chciał
przenieść ustalenia do pisma albo do notatki dla klienta, przepisywał
je ręcznie — a przy przepisywaniu ginie to, co w tym systemie jest
najcenniejsze: powiązanie twierdzenia z konkretnym miejscem w aktach.

════════════════════════════════════════════════════════════════════════
 CO EKSPORT MUSI ZACHOWAĆ, A CZEGO NIE WOLNO MU DODAĆ
════════════════════════════════════════════════════════════════════════

ZACHOWUJE:
  · cytat w brzmieniu ze źródła, ze wskazaniem dokumentu i zakresu znaków
  · stan kontroli każdego twierdzenia (sprawdzone / słabe / niezweryfikowane)
  · to, co system ODRZUCIŁ i dlaczego — bo brak tej sekcji zmienia
    wymowę całości
  · zastrzeżenie o roli materiału i o obowiązku sprawdzenia cytatu

NIE DODAJE:
  · żadnej treści, której nie ma w wyniku — eksport nie streszcza,
    nie porządkuje i nie wyciąga wniosków;
  · żadnej sugestii, że materiał jest opinią prawną.

⚠️ FORMAT: MARKDOWN I HTML, BEZ PDF-a.
   PDF wymagałby biblioteki zewnętrznej albo składu w przeglądarce.
   Markdown wkleja się do pisma, HTML otwiera się i drukuje do PDF-a
   jednym skrótem — a łańcuch dostaw zostaje pusty (art. 21 ust. 2
   lit. d ustawy o KSC).

⚠️ EKSPORT WYNOSI TREŚĆ AKT POZA BAZĘ.
   Plik zapisany na pulpicie nie jest już chroniony niczym poza
   szyfrowaniem nośnika. Stąd zastrzeżenie w stopce każdego dokumentu
   i wpis w logu audytowym po stronie serwera: kto, kiedy, z której
   sprawy. Sam eksport nie jest zapisywany — log rejestruje czynność,
   nie kopiuje treści (T-4).
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone

STOPKA = (
    "Materiał roboczy prawnika, nie opinia prawna. System wydobywa fakty "
    "z akt i wskazuje ich miejsce; nie ocenia sprawy, nie przewiduje "
    "rozstrzygnięcia i nie formułuje kwalifikacji prawnej. "
    "Każdy cytat należy sprawdzić w aktach przed użyciem w piśmie."
)

OPIS_STANU = {
    "prawda": "sprawdzone przez niezależną kontrolę",
    "niezweryfikowane": "NIE zweryfikowane niezależnie",
    "mocne": "wsparcie mocne (pokrycie leksykalne)",
    "slabe": "wsparcie słabe — sprawdź cytat",
}


def _stan(cytat: dict) -> str:
    """Jednolity opis stanu kontroli, w tej samej kolejności co w panelu."""
    if cytat.get("kontrola") in ("prawda", "niezweryfikowane"):
        return OPIS_STANU[cytat["kontrola"]]
    if cytat.get("stopien") in ("mocne", "slabe"):
        return OPIS_STANU[cytat["stopien"]]
    return ""


def _teraz() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%d.%m.%Y, %H:%M")


def nazwa_pliku(sprawa: str, rozszerzenie: str) -> str:
    """Nazwa bezpieczna dla systemu plików i czytelna w katalogu."""
    trzon = re.sub(r"[^\w\-]+", "-", f"{sprawa}", flags=re.UNICODE).strip("-")
    znacznik = datetime.now().strftime("%Y-%m-%d-%H%M")
    return f"analiza-{trzon or 'sprawa'}-{znacznik}.{rozszerzenie}"


# ════════════════════════════════════════════════════════════════════
#  MARKDOWN
# ════════════════════════════════════════════════════════════════════

def do_markdown(wynik: dict, sprawa: str = "", osoba: str = "") -> str:
    w: list[str] = []
    w.append(f"# Analiza akt — {sprawa or 'sprawa'}")
    w.append("")
    w.append(f"**Pytanie:** {wynik.get('pytanie', '').strip()}")
    w.append("")
    naglowek = [f"Sporządzono: {_teraz()}"]
    if osoba:
        naglowek.append(f"Osoba: {osoba}")
    dokumenty = wynik.get("przeanalizowane_dokumenty") or []
    if dokumenty:
        naglowek.append(f"Przeanalizowano dokumentów: {len(dokumenty)}")
    w.append("  \n".join(naglowek))
    w.append("")

    ustalenia = wynik.get("ustalenia") or []
    if ustalenia:
        w.append("## Ustalenia z akt")
        w.append("")
        for numer, u in enumerate(ustalenia, start=1):
            w.append(f"**{numer}.** {u.get('tekst', '').strip()}")
            w.append("")
            for c in u.get("cytaty") or []:
                stan = _stan(c)
                zrodlo = (f"{u.get('dokument', 'dokument')}, "
                          f"znaki {c.get('poczatek')}–{c.get('koniec')}")
                w.append(f"> {c.get('fragment', '').strip()}")
                w.append(">")
                w.append(f"> — {zrodlo}" + (f" · {stan}" if stan else ""))
                if c.get("ostrzezenie"):
                    w.append(f">")
                    w.append(f"> ⚠️ {c['ostrzezenie']}")
                w.append("")

    for klucz, tytul in (("wnioski", "Wnioski"),
                         ("rozbieznosci", "Rozbieżności"),
                         ("luki", "Luki w aktach")):
        pozycje = wynik.get(klucz) or []
        if not pozycje:
            continue
        w.append(f"## {tytul}")
        w.append("")
        for p in pozycje:
            tresc = p if isinstance(p, str) else (p.get("tekst") or p.get("opis", ""))
            oparte = "" if isinstance(p, str) else ", ".join(
                str(n) for n in (p.get("oparte_na") or []))
            w.append(f"- {tresc}" + (f" *(z ustaleń: {oparte})*" if oparte else ""))
        w.append("")
        if klucz == "rozbieznosci":
            w.append("*System wskazuje rozbieżności. Nie rozstrzyga, która "
                     "wersja jest prawdziwa, i nie ocenia wiarygodności osób.*")
            w.append("")

    podstawa = wynik.get("podstawa_prawna") or []
    if podstawa:
        w.append("## Podstawa prawna")
        w.append("")
        for p in podstawa:
            w.append(f"**{p.get('tekst', '').strip()}**")
            cytat = p.get("cytat") or {}
            w.append(f"> {cytat.get('fragment', '').strip()}")
            w.append(">")
            w.append(f"> — {cytat.get('nazwa', '')}")
            w.append("")

    # ⚠️ Sekcja odrzuconych NIE JEST opcjonalna przy eksporcie.
    # Wynik bez niej wygląda na pełniejszy, niż jest: czytelnik nie wie,
    # że system coś rozważył i odsiał, ani dlaczego.
    odrzucone = wynik.get("odrzucone") or []
    if odrzucone:
        w.append("## Odrzucone w kontroli")
        w.append("")
        w.append("Twierdzenia, które system rozważył i odsiał — cytat bez "
                 "pokrycia w źródle albo cytat, który nie popiera twierdzenia.")
        w.append("")
        for o in odrzucone:
            w.append(f"- ~~{o.get('tekst', '').strip()}~~  ")
            w.append(f"  *{o.get('powod', '')}"
                     + (f" — {o['szczegol']}" if o.get("szczegol") else "") + "*")
        w.append("")

    if not ustalenia and not (wynik.get("wnioski") or []):
        w.append("## Wynik")
        w.append("")
        w.append("W aktach tej sprawy nie znaleziono podstawy do odpowiedzi. "
                 "Odmowa jest poprawnym wynikiem — system nie uzupełnia "
                 "braków własnymi domysłami.")
        w.append("")

    w.append("---")
    w.append("")
    w.append(STOPKA)
    return "\n".join(w)


# ════════════════════════════════════════════════════════════════════
#  HTML
# ════════════════════════════════════════════════════════════════════

_STYL = """
body{font:15px/1.6 Georgia,'Times New Roman',serif;color:#1c2430;
     max-width:46rem;margin:2.5rem auto;padding:0 1.5rem}
h1{font-size:1.5rem;margin:0 0 .2rem} h2{font-size:1.05rem;margin:1.8rem 0 .6rem;
   border-bottom:1px solid #dfe3e8;padding-bottom:.25rem}
.meta{color:#5d6b7a;font-size:.85rem;margin-bottom:1.4rem}
.ustalenie{margin:0 0 1.1rem}
.nr{font-weight:700;margin-right:.35rem}
blockquote{margin:.5rem 0 .5rem 0;padding:.5rem .9rem;border-left:3px solid #1f4e79;
   background:#f5f7fa;font-size:.94rem}
.zrodlo{display:block;margin-top:.4rem;font-size:.78rem;color:#5d6b7a;
   font-family:ui-monospace,Consolas,monospace}
.uwaga{color:#8a5a00;font-size:.82rem;margin-top:.3rem}
.odrzucone{color:#a02020;font-size:.88rem;margin:.3rem 0}
.odrzucone s{color:#7a5050}
.stopka{margin-top:2.5rem;padding-top:.8rem;border-top:1px solid #dfe3e8;
   font-size:.8rem;color:#5d6b7a}
@media print{body{margin:0;max-width:none} blockquote{background:none}}
"""


def do_html(wynik: dict, sprawa: str = "", osoba: str = "") -> str:
    e = html.escape
    w: list[str] = [
        "<!doctype html><html lang=\"pl\"><head><meta charset=\"utf-8\">",
        f"<title>Analiza akt — {e(sprawa or 'sprawa')}</title>",
        f"<style>{_STYL}</style></head><body>",
        f"<h1>Analiza akt — {e(sprawa or 'sprawa')}</h1>",
        f"<div class=\"meta\"><b>{e(wynik.get('pytanie', ''))}</b><br>"
        f"Sporządzono: {e(_teraz())}"
        + (f" · {e(osoba)}" if osoba else "")
        + (f" · dokumentów: {len(wynik.get('przeanalizowane_dokumenty') or [])}"
           if wynik.get("przeanalizowane_dokumenty") else "")
        + "</div>",
    ]

    ustalenia = wynik.get("ustalenia") or []
    if ustalenia:
        w.append("<h2>Ustalenia z akt</h2>")
        for numer, u in enumerate(ustalenia, start=1):
            w.append(f"<div class=\"ustalenie\"><span class=\"nr\">{numer}.</span>"
                     f"{e(u.get('tekst', ''))}")
            for c in u.get("cytaty") or []:
                stan = _stan(c)
                w.append(
                    f"<blockquote>{e(c.get('fragment', ''))}"
                    f"<span class=\"zrodlo\">{e(u.get('dokument', ''))} · "
                    f"znaki {c.get('poczatek')}–{c.get('koniec')}"
                    + (f" · {e(stan)}" if stan else "") + "</span>"
                    + (f"<div class=\"uwaga\">⚠ {e(c['ostrzezenie'])}</div>"
                       if c.get("ostrzezenie") else "")
                    + "</blockquote>")
            w.append("</div>")

    for klucz, tytul in (("wnioski", "Wnioski"),
                         ("rozbieznosci", "Rozbieżności"),
                         ("luki", "Luki w aktach")):
        pozycje = wynik.get(klucz) or []
        if not pozycje:
            continue
        w.append(f"<h2>{tytul}</h2><ul>")
        for p in pozycje:
            tresc = p if isinstance(p, str) else (p.get("tekst") or p.get("opis", ""))
            w.append(f"<li>{e(tresc)}</li>")
        w.append("</ul>")
        if klucz == "rozbieznosci":
            w.append("<div class=\"meta\">System wskazuje rozbieżności. "
                     "Nie rozstrzyga, która wersja jest prawdziwa, i nie "
                     "ocenia wiarygodności osób.</div>")

    podstawa = wynik.get("podstawa_prawna") or []
    if podstawa:
        w.append("<h2>Podstawa prawna</h2>")
        for p in podstawa:
            cytat = p.get("cytat") or {}
            w.append(f"<div class=\"ustalenie\">{e(p.get('tekst', ''))}"
                     f"<blockquote>{e(cytat.get('fragment', ''))}"
                     f"<span class=\"zrodlo\">{e(cytat.get('nazwa', ''))}</span>"
                     f"</blockquote></div>")

    odrzucone = wynik.get("odrzucone") or []
    if odrzucone:
        w.append("<h2>Odrzucone w kontroli</h2>")
        w.append("<div class=\"meta\">Twierdzenia, które system rozważył "
                 "i odsiał — cytat bez pokrycia w źródle albo cytat, który "
                 "nie popiera twierdzenia.</div>")
        for o in odrzucone:
            w.append(f"<div class=\"odrzucone\"><s>{e(o.get('tekst', ''))}</s><br>"
                     f"<small>{e(o.get('powod', ''))}"
                     + (f" — {e(o['szczegol'])}" if o.get("szczegol") else "")
                     + "</small></div>")

    if not ustalenia and not (wynik.get("wnioski") or []):
        w.append("<h2>Wynik</h2><p>W aktach tej sprawy nie znaleziono podstawy "
                 "do odpowiedzi. Odmowa jest poprawnym wynikiem — system nie "
                 "uzupełnia braków własnymi domysłami.</p>")

    w.append(f"<div class=\"stopka\">{e(STOPKA)}</div></body></html>")
    return "\n".join(w)
