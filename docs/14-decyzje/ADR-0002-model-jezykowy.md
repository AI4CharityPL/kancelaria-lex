# ADR-0002 — Model językowy: Bielik-11B-v3.0-Instruct

**Status:** przyjęta · **Data:** 14.08.2026 · **Rewizja:** po M2 (pomiary z PoC)

## Kontekst

Potrzebny model językowy działający w pełni lokalnie, radzący sobie z polską terminologią prawniczą i składnią pism procesowych, na licencji dopuszczającej użycie komercyjne.

## Decyzja

**Bielik-11B-v3.0-Instruct** (SpeakLeash + ACK Cyfronet AGH, styczeń 2026), uruchamiany przez Ollamę.

| Kryterium | Ocena |
|---|---|
| Język polski | Trenowany z naciskiem na polski, ponad 20 mln instrukcji |
| Licencja wag | Apache 2.0 — pełna otwartość komercyjna |
| Dostępność | W bibliotece Ollamy w formacie GGUF, wiele wariantów kwantyzacji |
| Zaplecze | PLGrid, ACK Cyfronet AGH — projekt instytucjonalny, nie prywatny eksperyment |
| Rozmiar | 11 mld parametrów — mieści się w rozsądnym GPU |

## ⚠️ Warunek kwantyzacji

Karta modelu ostrzega wprost, że **modele kwantyzowane wykazują obniżoną jakość i podatność na halucynacje**.

| Profil | Kwantyzacja | Dopuszczalne dane |
|---|---|---|
| Rozwojowy (8 GB VRAM) | Q4_K_M | **wyłącznie korpus syntetyczny** |
| Produkcyjny | Q8_0 lub FP16 | akta rzeczywiste, po bramkach |

**Q4 nie jest dopuszczony do akt rzeczywistych.** To nie kwestia wygody — przy obronie karnej halucynacja jest błędem o realnych skutkach.

## Rozważane alternatywy

| Opcja | Powód odrzucenia |
|---|---|
| Modele ogólne (Llama, Mistral, Qwen) | Słabsze na polskiej terminologii prawniczej; część wersji ma licencje wymagające osobnej analizy komercyjnej |
| Model większy (30B+) | Nie mieści się w rozsądnym budżecie sprzętowym przy wymaganej równoległości; do rozważenia w wariancie C |
| Dostrajanie na aktach kancelarii | **Odrzucone zasadniczo** — ryzyko utrwalenia danych osobowych w wagach (RODO, tajemnica zawodowa) i przesunięcie kancelarii w stronę roli dostawcy w rozumieniu AI Act |
| Dowolny model chmurowy | Sprzeczne z wymogiem naczelnym |

## Konsekwencje

**Pozytywne:** dobre dopasowanie do polskiego · licencja bez zastrzeżeń komercyjnych · jedna komenda instalacji · dostępny wariant mniejszy do szybkich pętli rozwojowych.

**Negatywne:** jakość wnioskowania niższa niż największych modeli komercyjnych — kompensowana konstrukcyjnie (wymuszone cytowanie, weryfikacja maszynowa, obowiązkowa weryfikacja przez prawnika) · profil produkcyjny wymaga GPU ≥ 24 GB · aktualizacja modelu wymaga ponownego przejścia bramek jakościowych.

## Zasady eksploatacji

1. **Licencja wag weryfikowana przy każdej aktualizacji.** MIT dla kodu nie mówi nic o wagach — przypadek Suryi (kod Apache 2.0, wagi Open-RAIL-M z limitem komercyjnym) pokazuje, że to nie formalność.
2. **Sumy kontrolne wag w `models/`**, weryfikowane przy starcie (zagrożenie T-3).
3. **Wagi wnoszone paczką offline** — żadnego pobierania w czasie pracy.
4. **Nowszy model nie znaczy lepszy** dla polskich akt. Zmiana wyłącznie po pełnych bramkach jakościowych.

## Rewizja

Po M2, na podstawie rzeczywistych pomiarów: jakości na gold secie, przepustowości, zachowania przy 8k kontekstu. Jeśli jakość okaże się niewystarczająca, alternatywą jest większy model otwarty w wariancie sprzętowym B lub C — nie model chmurowy.
