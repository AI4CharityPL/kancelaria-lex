# 06 — Lokalny stos AI

## Zasada

Wszystko lokalnie: model językowy, embeddingi, OCR. Wagi pobierane **raz**, w kontrolowanym oknie, weryfikowane sumą kontrolną, przenoszone do strefy zamkniętej. W czasie pracy system nie pobiera niczego.

---

## Model językowy

**Bielik-11B-v3.0-Instruct** (SpeakLeash + ACK Cyfronet AGH, styczeń 2026, wagi Apache 2.0), uruchamiany przez Ollamę.

Uzasadnienie wyboru: dopasowanie do polskiej terminologii prawniczej i składni, w pełni otwarta licencja komercyjna wag, dostępność w bibliotece Ollamy w formacie GGUF, zaplecze instytucjonalne (PLGrid, ACK Cyfronet). Alternatywy i odrzucone opcje: [`14-decyzje/ADR-0002-model-jezykowy.md`](14-decyzje/ADR-0002-model-jezykowy.md).

### ⚠️ Kwantyzacja a wiarygodność

Karta modelu zawiera wprost ostrzeżenie, że **modele kwantyzowane wykazują obniżoną jakość odpowiedzi i podatność na halucynacje**.

To ostrzeżenie ma tu wagę większą niż w typowym zastosowaniu. Halucynacja w analizie akt karnych to nie niedogodność — to potencjalny błąd w obronie.

| Profil | Kwantyzacja | VRAM modelu | Kontekst | Dopuszczalne dane |
|---|---|---|---|---|
| **Rozwojowy** (ten laptop, 8 GB) | Q4_K_M | ~6,7 GB | ~8k | **wyłącznie korpus syntetyczny** |
| **Produkcyjny minimalny** (24 GB) | Q8_0 | ~12 GB | 32k | akta rzeczywiste, po bramkach |
| **Produkcyjny zalecany** (48 GB) | FP16 | ~22 GB | 32k+, równoległość | akta rzeczywiste |

**Zasada twarda: profil rozwojowy nigdy nie dotyka rzeczywistych akt.** Nie z powodu izolacji — ta działa tak samo — tylko dlatego, że Q4 na 8 GB VRAM nie daje jakości, którą można odpowiedzialnie zastosować do sprawy karnej.

### Konfiguracja profilu rozwojowego

Quadro RTX 4000 Max-Q ma 8 GB VRAM. Bielik Q4_K_M zajmuje ~6,7 GB, więc na cache KV zostaje ~1 GB → realny kontekst ok. 8k tokenów.

Przy 64 GB RAM dostępna jest alternatywa: częściowy offload warstw na CPU pozwala podnieść kontekst kosztem szybkości. Parametry w `models/Modelfile.bielik-dev`; pomiar przepustowości obu wariantów należy do Fazy 3.

Konsekwencja praktyczna: przy 8k kontekstu retrieval musi być oszczędny — kilka precyzyjnych fragmentów zamiast wrzucania całych dokumentów. Wzmacnia to zresztą wymóg cytowania.

---

## Embeddingi

**`multilingual-e5-base`**, 768 wymiarów, zamiast domyślnego `all-MiniLM-L6-v2` (384 wym., korpus angielski — ustalenie U-7).

Powody:
- retrieval na polskich pismach procesowych to podstawowa operacja systemu — wybór modelu anglojęzycznego psuje wszystko powyżej,
- 768 mieści się we wspieranym zestawie wymiarów, więc **nie wymaga operacji na schemacie pgvector**,
- działa na CPU z akceptowalną wydajnością, nie konkuruje z modelem językowym o VRAM.

Rozważany `bge-m3` (1024 wym., dłuższy kontekst) odłożony — wymagałby zmian w schemacie. Do rozważenia po pomiarach jakości retrievalu. Zapis: [`14-decyzje/ADR-0004-embedder.md`](14-decyzje/ADR-0004-embedder.md).

**Wyszukiwanie jest hybrydowe** — wektorowe plus pełnotekstowe. Wyszukiwanie wektorowe gubi sygnatury i numery; pełnotekstowe gubi parafrazy. W pismach procesowych występują oba rodzaje zapytań.

---

## OCR

OpenContracts nie ma własnego OCR — parsowaniem PDF kieruje **Docling**, który jest orkiestratorem, a rozpoznawanie tekstu wykonuje podpięty silnik.

| Silnik | Licencja | Rola | Uzasadnienie |
|---|---|---|---|
| **Tesseract 5.x + `pol.traineddata`** | Apache 2.0 | domyślny | Dojrzały, lekki (~10 MB), bez GPU, dobry pakiet polski, strona poniżej sekundy |
| **RapidOCR** | Apache 2.0 | zapasowy | ONNX, PP-OCR pod spodem; lepszy na słabych kserokopiach i nietypowych układach, wciąż bez GPU |
| PaddleOCR / PaddleOCR-VL | Apache 2.0 | opcja skrajna | Najwyższa dokładność, ale kosztowna obliczeniowo — do pojedynczych trudnych spraw |
| EasyOCR | Apache 2.0 | alternatywa | Wspierany natywnie przez Docling |
| ~~Surya~~ | kod Apache 2.0, **wagi Open-RAIL-M** | **do unikania** | Licencja wag ogranicza użycie komercyjne powyżej progu przychodu — dla kancelarii komercyjnej wymaga odrębnej licencji |

Wszystkie wybrane silniki działają w 100% lokalnie, bez wywołania sieciowego.

### Bramka jakości OCR

OCR jest **pierwszym** ogniwem łańcucha — błąd tutaj propaguje się na embeddingi, retrieval i odpowiedź agenta. Dlatego:

- CER mierzony na próbce stratyfikowanej wg jakości skanu (bramki N-14, N-15),
- dokumenty powyżej progu błędu trafiają do kolejki weryfikacji ręcznej, nie do indeksu,
- prawnik może obejrzeć i poprawić wynik OCR przed indeksowaniem (F-03).

Realistycznie: lokalny OCR wypada gorzej od komercyjnych usług chmurowych na kserokopiach i piśmie odręcznym. To cena poufności i jest akceptowana — pod warunkiem, że jakość jest **mierzona**, a nie zakładana.

---

## Konwersja formatów

Formaty inne niż PDF/DOCX/TXT (stare `.doc`, ODF, obrazy, HTML i ponad 120 innych) idą przez **Gotenberg** (LibreOffice).

⚠️ **Gotenberg musi być w segmencie `internal`.** LibreOffice potrafi próbować pobierać zasoby osadzone w plikach — linkowane obrazy, encje XML. Przy piśmie od strony przeciwnej jest to kanał potwierdzenia odbioru pod kontrolowanym adresem (zagrożenie I-2). Kontrola na poziomie aplikacji jest tu zawodna; działa dopiero brak trasy sieciowej.

---

## Zarządzanie wagami

Katalog `models/` przechowuje **manifesty i sumy kontrolne**, nie same wagi.

Dla każdego modelu:
- nazwa, wersja, kwantyzacja, źródło,
- suma kontrolna wag,
- **licencja wag** wraz z datą weryfikacji,
- data wniesienia do strefy zamkniętej i osoba odpowiedzialna.

**Licencja kodu nie jest licencją wag.** MIT dla OpenContracts nie mówi nic o Bieliku. Każda aktualizacja modelu wymaga ponownej weryfikacji licencji — przypadek Suryi (kod Apache 2.0, wagi Open-RAIL-M z limitem komercyjnym) pokazuje, że to nie jest formalność.

Sumy kontrolne są weryfikowane przy starcie (warstwa B izolacji, zagrożenie T-3).

---

## Czego świadomie nie robimy

| Odrzucone | Powód |
|---|---|
| Dostrajanie modelu na aktach kancelarii | Ryzyko utrwalenia danych osobowych w wagach; RODO i tajemnica zawodowa. Retrieval daje podobny efekt bez tego ryzyka. |
| Model chmurowy „tylko do zadań nieczułych" | Nie ma sposobu, by trwale zagwarantować, że dane nieczułe nie zawierają czułych. Granica byłaby fikcją. |
| Ranker/reranker jako model zewnętrzny | Ta sama zasada — wszystko lokalnie albo wcale. |
| Automatyczne pobieranie modeli w czasie pracy | Byłoby połączeniem wychodzącym. Wagi wnoszone wyłącznie paczką offline. |
