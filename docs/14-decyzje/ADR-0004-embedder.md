# ADR-0004 — Embedder: multilingual-e5-base zamiast all-MiniLM-L6-v2

**Status:** przyjęta · **Data:** 14.08.2026 · **Rewizja:** po M2

## Kontekst

Domyślny embedder w OpenContracts to `all-MiniLM-L6-v2` — 384 wymiary, trenowany na korpusie angielskim (ustalenie U-7).

Retrieval jest podstawową operacją systemu: agent odpowiada wyłącznie na podstawie znalezionych fragmentów. **Zły retrieval psuje wszystko powyżej** — najlepszy model językowy nie odpowie poprawnie na podstawie nieznalezionego dokumentu.

Model anglojęzyczny na polskich pismach procesowych — z fleksją, terminologią prawniczą i charakterystyczną składnią — to wybór, który podważa cały łańcuch.

## Decyzja

**`multilingual-e5-base`, 768 wymiarów.**

| Kryterium | Uzasadnienie |
|---|---|
| Wielojęzyczność | Trenowany wielojęzycznie, wyraźnie lepszy na polskim |
| **768 wymiarów** | Mieści się we wspieranym zestawie wymiarów — **bez operacji na schemacie pgvector** |
| CPU | Działa z akceptowalną wydajnością bez GPU — nie konkuruje z modelem językowym o VRAM |
| Licencja | Otwarta, bez ograniczeń komercyjnych |

Wybór 768 zamiast większego modelu jest świadomy: pozwala zmienić embedder **bez migracji schematu bazy**, co przy forku znacząco obniża koszt i ryzyko zmiany.

## Rozważane alternatywy

| Opcja | Ocena |
|---|---|
| `all-MiniLM-L6-v2` (domyślny) | Odrzucony — korpus angielski, słaby na polskim |
| `bge-m3` (1024 wym., długi kontekst) | **Kandydat, odłożony** — 1024 wymagałoby zmian w schemacie. Do rozważenia po pomiarach, jeśli e5-base okaże się niewystarczający |
| Embeddingi chmurowe (1536/3072) | Sprzeczne z wymogiem naczelnym |

## Wyszukiwanie hybrydowe — decyzja towarzysząca

Retrieval łączy wyszukiwanie wektorowe z pełnotekstowym.

Powód konkretny: **wyszukiwanie wektorowe gubi sygnatury i numery**. Zapytanie o „II K 123/26" to wyszukiwanie dokładne, w którym podobieństwo semantyczne szkodzi — sygnatury podobne wektorowo to zwykle sygnatury różne. Odwrotnie, wyszukiwanie pełnotekstowe gubi parafrazy („kto zeznał, że widział pojazd" vs. „świadek dostrzegł samochód").

W pismach procesowych występują oba rodzaje zapytań, często w jednym pytaniu.

## Konsekwencje

**Pozytywne:** wyraźnie lepszy retrieval na polskich dokumentach · brak zmian w schemacie · brak konkurencji o VRAM · wyszukiwanie hybrydowe pokrywa oba wzorce zapytań.

**Negatywne:** embedder większy niż domyślny — dłuższe indeksowanie · ponowne indeksowanie przy ewentualnej zmianie na `bge-m3` · patch na warstwę embedderów przy merge'u z upstreamem.

## Rewizja

Po M2, na podstawie pomiarów jakości retrievalu na gold secie. Jeśli e5-base okaże się niewystarczający — `bge-m3` z migracją schematu, wyceniona osobno.
