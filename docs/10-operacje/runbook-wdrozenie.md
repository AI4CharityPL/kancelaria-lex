# Runbook — wdrożenie środowiska

Dwa profile. **Rozwojowy nigdy nie przetwarza rzeczywistych akt.**

| | Rozwojowy | Produkcyjny |
|---|---|---|
| Sprzęt | Laptop, 64 GB RAM, 8 GB VRAM | Serwer kancelarii, GPU ≥ 24 GB |
| Model | Bielik Q4_K_M, ~8k kontekstu | Bielik Q8_0 lub FP16, 32k |
| Dane | **Wyłącznie korpus syntetyczny** | Akta rzeczywiste, po bramkach |
| Sieć | Segmenty `internal`, host w LAN | Segmenty `internal`, host odcięty |
| TLS | Własne CA, certyfikaty lokalne | Własne CA + mTLS |

---

## Profil rozwojowy — instalacja

### Wymagania wstępne

- Docker Desktop **uruchomiony** (WSL2) — demon musi działać
- Ollama ≥ 0.32
- ~30 GB wolnego miejsca
- Sterownik NVIDIA z obsługą CUDA

Weryfikacja:

```bash
docker info --format "{{.ServerVersion}} | {{.NCPU}} CPU | {{.MemTotal}}"
```

```bash
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

### Krok 1 — model językowy

```bash
ollama pull SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M
```

Po pobraniu — zapisz sumę kontrolną do manifestu w `models/`:

```bash
ollama show SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M --modelfile
```

⚠️ Pobranie modelu to jedyna czynność wymagająca internetu. W profilu produkcyjnym wagi wnosi się paczką offline — patrz [`runbook-aktualizacje.md`](runbook-aktualizacje.md).

### Krok 2 — model dostosowany do profilu

Modelfile w `models/Modelfile.bielik-dev` ustala kontekst i parametry generowania pod 8 GB VRAM:

```bash
ollama create bielik-lex-dev -f models/Modelfile.bielik-dev
```

Niska temperatura jest celowa — w analizie akt kreatywność jest wadą.

### Krok 3 — fork i patche

Klon upstreamu do `src/opencontracts/`, następnie zastosowanie patchy z `src/patche/`:

| Patch | Stan | Działanie |
|---|---|---|
| `01-usun-sdk-chmurowe.patch` | ✅ nałożony | Ekstras `anthropic`, `google`, `mcp` z `pydantic-ai-slim`; usunięcie `posthog` i `mcp`. **`openai` zostaje** — transport do Ollamy |
| `02-usun-mcp-i-discovery.patch` | ✅ nałożony | Usunięcie routingu MCP z **`config/asgi.py`** oraz aplikacji `discovery` z `urls.py` i `INSTALLED_APPS`. Katalogi `opencontractserver/mcp/` i `opencontractserver/discovery/` usunięte z drzewa (−14 726 linii) |
| `03-straznik-adresow.patch` | ✅ nałożony | Allowlista `base_url` w `model_factory.py` + usunięcie gałęzi `anthropic` i `google-gla` |
| `04-embedder-pl.patch` | ⬜ do zrobienia | `multilingual-e5-base`, 768 wymiarów po stronie forka (w compose embedder jest już osobną usługą) |
| `05-traefik-bez-acme.patch` | ⬜ nie dotyczy forka | Traefik konfigurujemy we własnym `infra/compose/compose.yml`, nie w plikach upstreamu |

⚠️ **Routing MCP siedzi w `config/asgi.py`, nie w `urls.py`.** Upstream dispatchuje `/mcp`, `/mcp/*`, `/sse`, `/sse/*` do osobnej aplikacji ASGI **przed** Django. Dwie konsekwencje warte zapamiętania:

- `MCP_SERVER["enabled"]=False` **nie wyłączało** routingu — router powstawał przy imporcie modułu;
- żądania MCP omijały `ALLOWED_HOSTS` i `django-cors-headers`, bo nigdy nie docierały do Django.

Aplikacja `discovery` publikowała dodatkowo `.well-known/mcp.json` i `llms.txt` z gotowym fragmentem konfiguracji dla Claude Desktop — czyli aktywnie ogłaszała instancję agentom.

**Przed zastosowaniem patchy zweryfikuj ustalenia U-1…U-8** z [`../05-izolacja-i-siec.md`](../05-izolacja-i-siec.md) wobec bieżącego stanu upstreamu. Ustalenia pochodzą z 14.08.2026 — upstream się zmienia, a patch nałożony na zmieniony kod może dać złudzenie ochrony.

### Krok 4 — własne CA

```bash
bash infra/ca/utworz-ca.sh
```

### Krok 5 — uruchomienie

```bash
docker compose -f infra/compose/compose.yml up -d
```

### Krok 6 — bramka weryfikacyjna 🚦

**To nie jest krok opcjonalny.** Środowisko bez zaliczonych testów izolacji nie jest gotowe do użycia — nawet na korpusie syntetycznym, bo nawyki przenoszą się na produkcję.

```bash
pytest tests/izolacja/ -v
```

Sprawdza: brak zakazanych pakietów · `GET /mcp/` → 404 · DNS nie rozwiązuje · TCP nie łączy · strażnik blokuje adres spoza allowlisty · zapis do bazy odrzucony i zalogowany.

**Każdy niezaliczony test zatrzymuje wdrożenie.**

### Krok 7 — przebieg dymny

Wgranie dokumentu z `eval/korpus-syntetyczny/` → OCR → indeksowanie → pytanie → odpowiedź **z cytatami przechodzącymi weryfikację**.

---

## Profil produkcyjny — różnice

1. **Wagi z paczki offline**, nie przez `ollama pull` — host nie ma dostępu do internetu.
2. **Model w Q8_0 lub FP16** — Q4 nie jest dopuszczony do akt rzeczywistych ([`../06-stos-ai.md`](../06-stos-ai.md)).
3. **mTLS między segmentami**, certyfikaty z własnego CA z procedurą odnawiania (bez ACME).
4. **Szyfrowanie nośnika** przed pierwszym uruchomieniem — nie da się dodać później bez migracji.
5. **Odrębny magazyn i klucz materiału obrończego** przed wprowadzeniem pierwszej sprawy.
6. **Kopia zapasowa skonfigurowana i przetestowana** przed wprowadzeniem pierwszej sprawy.
7. **Przechwycenie ruchu** podczas pełnego przebiegu — dowód końcowy, zero pakietów wychodzących.
8. Host odcięty od internetu na poziomie sieci kancelarii, niezależnie od konfiguracji Dockera.

## Warunki dopuszczenia do rzeczywistych akt

Wszystkie łącznie — pełna lista w [`../09-compliance/rodo-dpia.md`](../09-compliance/rodo-dpia.md):

- [ ] Bramki jakościowe zaliczone ([`../11-testy-i-bramki.md`](../11-testy-i-bramki.md))
- [ ] Testy izolacji zaliczone na środowisku produkcyjnym
- [ ] Przechwycenie ruchu: zero pakietów wychodzących
- [ ] Model w profilu produkcyjnym (Q8+)
- [ ] Log audytowy działa, łańcuch sum weryfikowalny
- [ ] Materiał obrończy: odrębny magazyn i klucz
- [ ] Kopia zapasowa odtworzona testowo
- [ ] DPIA zatwierdzona przez administratora i IOD
- [ ] Użytkownicy przeszkoleni, w tym w zakresie obowiązku weryfikacji

## Typowe problemy

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| Model nie startuje | Za mało VRAM przy 8 GB | Obniż kontekst albo zwiększ offload na CPU |
| Bardzo wolne odpowiedzi | Warstwy poszły na CPU | Zmniejsz kontekst; sprawdź `nvidia-smi` w trakcie generowania |
| Kontener nie widzi Ollamy | Ollama poza siecią Dockera | Sprawdź adres w `net_ai`; nie obchodź tego wystawieniem na host |
| Test izolacji „przechodzi" na wszystkim | Testy nie działają naprawdę | Sprawdź celowo: dodaj tymczasowo trasę i upewnij się, że test **pada** |
| OCR nie rozpoznaje polskiego | Brak `pol.traineddata` | Sprawdź pakiet językowy w kontenerze docling |

Wiersz czwarty jest wart uwagi: test bezpieczeństwa, który zawsze przechodzi, jest gorszy niż brak testu — daje fałszywą pewność. Przy pierwszym uruchomieniu należy sprawdzić, że test potrafi paść.
