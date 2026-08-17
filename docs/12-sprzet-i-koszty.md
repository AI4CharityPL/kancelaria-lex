# 12 — Sprzęt i koszty

## Profil rozwojowy — maszyna obecna

| Element | Stan | Ocena |
|---|---|---|
| CPU | i7-10875H, 8 rdzeni / 16 wątków | Wystarcza — OCR i embeddingi na CPU |
| RAM | 64 GB | Z zapasem; umożliwia offload warstw modelu |
| GPU | Quadro RTX 4000 Max-Q, **8 GB VRAM**, CUDA 7.5 | **Wąskie gardło** |
| Dysk | 169 GB wolnego na C: | Wystarcza (~30 GB potrzebne) |
| Docker | 28.3.0, WSL2 | ⚠️ Demon wymaga uruchomienia |
| Ollama | 0.32.9 | Gotowe |

### Co się mieści w 8 GB VRAM

| Konfiguracja | VRAM | Kontekst | Ocena |
|---|---|---|---|
| Bielik-11B **Q4_K_M** | ~6,7 GB | ~8k | Mieści się, ciasno — profil rozwojowy |
| Bielik-11B Q4 + większy kontekst | > 8 GB | 16k+ | Wymaga offloadu na CPU, wyraźnie wolniej |
| Bielik-11B **Q8_0** | ~12 GB | — | **Nie mieści się** |
| Bielik-11B FP16 | ~22 GB | — | Nie mieści się |

Embedder (`multilingual-e5-base`) i OCR działają na CPU, więc nie konkurują o VRAM — to świadomy podział zasobów.

**Wniosek: maszyna obecna wystarcza do PoC i wyłącznie do PoC.** Ograniczeniem nie jest wygoda pracy, tylko jakość: Q4 zwiększa skłonność do halucynacji, co przy aktach karnych jest niedopuszczalne.

---

## Profile produkcyjne

Trzy warianty do decyzji kancelarii. Kwoty są **orientacyjne** (poziom sierpnia 2026, netto, sprzęt) i wymagają aktualnej wyceny.

### Wariant A — mała kancelaria *(2–5 prawników)*

| Element | Specyfikacja |
|---|---|
| GPU | 1× 24 GB (klasa RTX 4090 / RTX 5000 Ada) |
| CPU | 12–16 rdzeni |
| RAM | 128 GB |
| Dysk | 2× 2 TB NVMe (RAID 1), szyfrowane |
| Model | Bielik-11B **Q8_0**, 32k kontekstu |
| Równoległość | 2–3 zapytania jednocześnie |
| Koszt sprzętu | ~25–35 tys. zł |

Wariant minimalny dopuszczalny do akt rzeczywistych. Q8 spełnia wymóg profilu produkcyjnego.

### Wariant B — średnia kancelaria *(5–15 prawników)* ⭐ zalecany

| Element | Specyfikacja |
|---|---|
| GPU | 1× 48 GB (klasa RTX 6000 Ada / L40S) |
| CPU | 16–24 rdzenie |
| RAM | 256 GB |
| Dysk | 2× 4 TB NVMe (RAID 1) + magazyn na kopie |
| Model | Bielik-11B **FP16**, 32k+; miejsce na model rezerwowy |
| Równoległość | 5–8 zapytań jednocześnie |
| Koszt sprzętu | ~60–90 tys. zł |

Zalecany, bo 48 GB VRAM daje zapas na **zmianę modelu bez wymiany sprzętu**. Przy tempie rozwoju modeli otwartych to istotne — sprzęt dobrany dokładnie pod jeden model starzeje się razem z nim.

### Wariant C — duża kancelaria *(15+)*

| Element | Specyfikacja |
|---|---|
| GPU | 2× 48 GB lub 1× 80 GB |
| RAM | 512 GB |
| Dysk | Macierz z redundancją |
| Model | Większy model + Bielik do zadań polskojęzycznych |
| Koszt sprzętu | ~150–250 tys. zł |

---

## Koszty poza sprzętem

| Pozycja | Charakter | Uwagi |
|---|---|---|
| Praca wdrożeniowa | Jednorazowo | Główny koszt projektu — moduł spraw, integracje, testy |
| **Utrzymanie forka** | **Ciągły** | Najczęściej niedoszacowany — patrz niżej |
| Okna serwisowe | Ciągły | ~1 dzień na kwartał + okna nadzwyczajne |
| Zatwierdzenie reguł terminów | Jednorazowo + przeglądy | Czas prawnika, nie inżyniera |
| Szkolenia | Jednorazowo + rotacja | Wspólny program KSC + AI Act |
| DPIA i dokumentacja | Jednorazowo + przeglądy roczne | Czas IOD |
| Audyt (jeśli podmiot kluczowy) | Co 2 lata | Do 3.04.2028 |
| Energia | Ciągły | Serwer z GPU pod obciążeniem: istotna pozycja |

### Utrzymanie forka — koszt wart wyodrębnienia

Fork oznacza przejęcie odpowiedzialności za bezpieczeństwo całego stosu bazowego. Upstream wydaje poprawki; ktoś musi je przejrzeć, nałożyć i sprawdzić, że nie cofnęły wycięcia ścieżek chmurowych.

Bramka CI na lockfile obniża ten koszt, ale go nie usuwa. Realistycznie: **kilka–kilkanaście godzin miesięcznie** stałej pracy inżynierskiej. Projekt bez zapewnionego utrzymania nie powinien wejść na produkcję — nieaktualizowany system w kancelarii jest ryzykiem, nie oszczędnością.

---

## Czego nie kupować

| | Powód |
|---|---|
| GPU z 8–16 GB VRAM „na start" | Wymusza kwantyzację Q4, niedopuszczalną dla akt rzeczywistych. Fałszywa oszczędność. |
| Serwer w chmurze, choćby „prywatnej" | Dane opuszczają kontrolę kancelarii — problem z tajemnicą zawodową, nie z RODO |
| GPU konsumenckie bez ECC do wariantu C | Przy pracy ciągłej i dużej pamięci błędy pamięci przestają być teoretyczne |
| Sprzęt dobrany dokładnie pod obecny model | Model się zmieni szybciej niż sprzęt |

## Decyzja do podjęcia po PoC

Wybór wariantu wymaga danych, których jeszcze nie mamy: rzeczywistej liczby użytkowników równoczesnych, objętości akt, akceptowalnego czasu odpowiedzi. **PoC dostarczy pomiarów** — przepustowości, czasu OCR, jakości retrievalu — i dopiero na tej podstawie warto wybierać sprzęt.

Zamawianie serwera przed PoC to zgadywanie.
