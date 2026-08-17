"""Usługa embeddingów — `multilingual-e5-base`, 768 wymiarów (ADR-0004).

════════════════════════════════════════════════════════════════════════
 DLACZEGO TA USŁUGA ISTNIEJE
════════════════════════════════════════════════════════════════════════

Domyślny embedder OpenContracts to `all-MiniLM-L6-v2` — 384 wymiary,
korpus angielski (ustalenie U-7). Retrieval jest podstawową operacją
tego systemu: agent odpowiada wyłącznie na podstawie znalezionych
fragmentów, więc **zły retrieval psuje wszystko powyżej**. Model
anglojęzyczny na polskich pismach procesowych podważa cały łańcuch.

Stąd `multilingual-e5-base`: 768 wymiarów mieści się we wspieranym
zestawie, więc zmiana nie wymaga operacji na schemacie pgvector.

════════════════════════════════════════════════════════════════════════
 ⚠️ TRZY WŁASNOŚCI, KTÓRE SĄ TU WAŻNIEJSZE OD FUNKCJONALNOŚCI
════════════════════════════════════════════════════════════════════════

1. WAGI WYŁĄCZNIE Z ZAMONTOWANEGO WOLUMENU.
   `transformers` domyślnie DOCIĄGA model z internetu, gdy nie znajdzie
   go lokalnie. W systemie, którego jedyną obietnicą jest „akta nie
   opuszczają urządzenia", takie zachowanie jest niedopuszczalne —
   i najgorsze z możliwych, bo ciche. Obraz ustawia więc
   `HF_HUB_OFFLINE=1` i `TRANSFORMERS_OFFLINE=1`, a ta usługa
   dodatkowo sprawdza obecność wag PRZED próbą wczytania.

2. BRAK WAG = BRAK STARTU.
   Usługa bez modelu nie wstaje i mówi dlaczego. Nie wstaje „w trybie
   ograniczonym", nie zwraca wektorów zerowych — bo embedder zwracający
   zera wygląda na działający, a retrieval przestaje działać w ciszy.
   Ta sama zasada, co przy bramkach izolacji: awaria nie może oznaczać
   zgody.

3. PREFIKSY `query:` I `passage:` SĄ OBOWIĄZKOWE DLA RODZINY E5.
   Model był trenowany z nimi. Ich pominięcie nie daje błędu — daje
   CICHO GORSZY retrieval, czyli usterkę, której nikt nie zauważy poza
   spadkiem trafności o kilka punktów. Dlatego `typ` jest w API polem
   jawnym, a nie domyślnym.

Zależności są tu dozwolone — zasada „zero zależności" dotyczy `panel/`,
który przetwarza akta w procesie prawnika. To jest osobny kontener
w segmencie bez trasy na zewnątrz.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("embedder")

SCIEZKA_MODELU = Path(os.environ.get("MODEL_PATH", "/modele/e5-base"))
NAZWA_MODELU = os.environ.get("MODEL_NAME", "intfloat/multilingual-e5-base")
PORT = int(os.environ.get("PORT", "8000"))
WYMIARY = 768

# Maksymalna liczba tekstów w jednym żądaniu. Ogranicznik pamięci:
# przy braku limitu jedno żądanie z całym tomem akt wywróciłoby kontener.
MAKS_TEKSTOW = 128


def _sprawdz_wagi() -> None:
    """Brak wag = brak startu, z komunikatem mówiącym, co zrobić.

    ⚠️ Sprawdzenie MUSI stać przed importem `transformers`. Biblioteka
    przy wczytaniu nieznalezionego modelu próbuje go pobrać — a w tym
    systemie próba wyjścia do sieci jest zdarzeniem, a nie szczegółem
    implementacyjnym.
    """
    wymagane = ["config.json"]
    wagi = ["model.safetensors", "pytorch_model.bin"]

    if not SCIEZKA_MODELU.is_dir():
        log.error(
            "Brak katalogu z wagami: %s\n"
            "  Wagi wnosi się PACZKĄ OFFLINE, nie pobiera przy starcie.\n"
            "  Przygotowanie paczki: src/aplikacje/embedder/README.md\n"
            "  Model: %s (768 wymiarów, ADR-0004)",
            SCIEZKA_MODELU, NAZWA_MODELU)
        raise SystemExit(2)

    brakujace = [p for p in wymagane if not (SCIEZKA_MODELU / p).exists()]
    if not any((SCIEZKA_MODELU / w).exists() for w in wagi):
        brakujace.append(" albo ".join(wagi))

    if brakujace:
        log.error(
            "Katalog %s istnieje, ale nie zawiera modelu — brakuje: %s\n"
            "  Usługa NIE wstaje. Embedder zwracający cokolwiek innego niż "
            "prawdziwe wektory\n  wygląda na działający, a retrieval "
            "przestaje działać w ciszy.",
            SCIEZKA_MODELU, ", ".join(brakujace))
        raise SystemExit(2)


_MODEL = None
_TOKENIZER = None


def _wczytaj_model():
    """Wczytanie modelu z dysku, bez sięgania do sieci."""
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return

    import torch                                       # noqa: PLC0415
    from transformers import AutoModel, AutoTokenizer   # noqa: PLC0415

    log.info("Wczytuję %s z %s (CPU)", NAZWA_MODELU, SCIEZKA_MODELU)
    _TOKENIZER = AutoTokenizer.from_pretrained(
        str(SCIEZKA_MODELU), local_files_only=True)
    _MODEL = AutoModel.from_pretrained(
        str(SCIEZKA_MODELU), local_files_only=True)
    _MODEL.eval()
    torch.set_num_threads(int(os.environ.get("WATKI_CPU", "4")))
    log.info("Model wczytany. Wymiarów: %d", WYMIARY)


def _osadz(teksty: list[str], typ: str) -> list[list[float]]:
    """Wektory dla listy tekstów.

    `typ` steruje prefiksem wymaganym przez rodzinę E5:
      · `query`   — pytanie użytkownika,
      · `passage` — fragment dokumentu wchodzący do indeksu.

    Pominięcie prefiksu nie daje błędu, tylko cicho gorszy retrieval —
    dlatego pole jest jawne i walidowane.
    """
    import torch                                       # noqa: PLC0415

    _wczytaj_model()
    prefiks = "query: " if typ == "query" else "passage: "
    wsad = [prefiks + t for t in teksty]

    with torch.no_grad():
        tokeny = _TOKENIZER(wsad, padding=True, truncation=True,
                            max_length=512, return_tensors="pt")
        wyjscie = _MODEL(**tokeny)

        # Uśrednianie po tokenach z maską — sposób zalecany dla E5.
        # Zwykłe uśrednienie po całej długości liczyłoby dopełnienie
        # i psuło wektor krótkich fragmentów.
        maska = tokeny["attention_mask"].unsqueeze(-1).float()
        suma = (wyjscie.last_hidden_state * maska).sum(dim=1)
        wektory = suma / maska.sum(dim=1).clamp(min=1e-9)
        wektory = torch.nn.functional.normalize(wektory, p=2, dim=1)

    return wektory.tolist()


class Uchwyt(BaseHTTPRequestHandler):
    server_version = "kancelaria-lex-embedder/1.0"

    def log_message(self, format, *args):            # noqa: A002
        # Treść akt nigdy nie trafia do logu dostępowego.
        pass

    def _odpowiedz(self, dane: dict, kod: int = 200) -> None:
        tresc = json.dumps(dane).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(tresc)))
        self.end_headers()
        self.wfile.write(tresc)

    def do_GET(self):                                # noqa: N802
        if self.path in ("/zdrowie", "/health"):
            return self._odpowiedz({
                "stan": "gotowy" if _MODEL is not None else "wczytywanie",
                "model": NAZWA_MODELU,
                "wymiary": WYMIARY,
                "zrodlo_wag": str(SCIEZKA_MODELU),
            })
        self.send_error(404)

    def do_POST(self):                               # noqa: N802
        if self.path not in ("/v1/embeddings", "/embeddings"):
            return self.send_error(404)

        dlugosc = int(self.headers.get("Content-Length") or 0)
        try:
            zadanie = json.loads(self.rfile.read(dlugosc) or b"{}")
        except json.JSONDecodeError as e:
            return self._odpowiedz({"blad": f"Niepoprawny JSON: {e}"}, 400)

        wejscie = zadanie.get("input")
        if isinstance(wejscie, str):
            wejscie = [wejscie]
        if not isinstance(wejscie, list) or not wejscie:
            return self._odpowiedz(
                {"blad": "Pole `input` musi być tekstem albo listą tekstów."},
                400)
        if len(wejscie) > MAKS_TEKSTOW:
            return self._odpowiedz(
                {"blad": f"Najwyżej {MAKS_TEKSTOW} tekstów w jednym żądaniu; "
                         f"otrzymano {len(wejscie)}."}, 413)

        # ⚠️ BEZ WARTOŚCI DOMYŚLNEJ — ŚWIADOMIE.
        #
        # Pierwsza wersja przyjmowała `passage`, gdy pola brakowało.
        # Wyłapał to test: pominięcie pola dawało 200 i wektor, mimo że
        # dokumentacja mówiła „obowiązkowe". Skutek byłby dokładnie tą
        # usterką, przed którą ostrzega README — zapytanie osadzone jako
        # fragment obniża trafność retrievalu i NIE daje żadnego sygnału.
        # Domyślna wartość jest tu wygodą kosztem poprawności, więc jej
        # nie ma: wywołujący musi wiedzieć, co osadza.
        typ = str(zadanie.get("typ") or zadanie.get("input_type") or "")
        if typ not in ("query", "passage"):
            return self._odpowiedz(
                {"blad": "Pole `typ` jest obowiązkowe i musi być `query` "
                         "(pytanie) albo `passage` (fragment akt). Rodzina "
                         "E5 wymaga prefiksu, a jego pominięcie cicho "
                         "pogarsza retrieval — dlatego nie ma wartości "
                         "domyślnej."}, 400)

        try:
            wektory = _osadz([str(t) for t in wejscie], typ)
        except Exception as e:                       # noqa: BLE001
            log.exception("Błąd osadzania")
            return self._odpowiedz({"blad": f"{type(e).__name__}: {e}"}, 500)

        # Kształt odpowiedzi zgodny z OpenAI — klient forka rozmawia tym
        # protokołem także z Ollamą (ustalenie U-1).
        return self._odpowiedz({
            "object": "list",
            "model": NAZWA_MODELU,
            "data": [{"object": "embedding", "index": i, "embedding": w}
                     for i, w in enumerate(wektory)],
        })


def main() -> None:
    _sprawdz_wagi()
    _wczytaj_model()
    serwer = ThreadingHTTPServer(("0.0.0.0", PORT), Uchwyt)
    log.info("Embedder nasłuchuje na :%d (segment net_ai, bez trasy na "
             "zewnątrz)", PORT)
    try:
        serwer.serve_forever()
    except KeyboardInterrupt:
        log.info("Zatrzymano")
    finally:
        serwer.server_close()


if __name__ == "__main__":
    sys.exit(main())
