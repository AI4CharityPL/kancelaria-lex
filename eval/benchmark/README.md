# Benchmark kancelaria-lex

**Dwujęzyczna, ilościowa ocena wierności cytatu i odmowy — bez sędziego LLM.**
**Bilingual quantitative benchmark for citation fidelity and refusal — no LLM judge.**

---

## 🇵🇱 Po co to powstało

### Problem, który rynek ma i nie umie zmierzyć

Stanford RegLab przebadał wiodące komercyjne narzędzia do badań prawniczych.
Wynik, opublikowany później w *Journal of Empirical Legal Studies*:

| Narzędzie | Halucynacje |
|---|---:|
| Lexis+ AI | **ponad 17%** |
| Westlaw AI-Assisted Research | **ponad 34%** |

LexisNexis reklamował wówczas „100% hallucination-free linked legal citations".
Thomson Reuters — że ich narzędzia „unikają halucynacji, opierając się na
zaufanej treści". Badanie pokazało, że oba twierdzenia są na wyrost.

Niezależny przegląd z 2026 r., w którym oceniono 3 000 odpowiedzi, dał liczbę
jeszcze bardziej wymowną: **24% odpowiedzi powoływało lub stosowało przepis,
który nie popierał tezy**. Nie „model się pomylił" — model podał cytat, który
nie mówi tego, co mu przypisano.

**To jest dokładnie ta klasa błędu, której nie wykryje ani sędzia LLM, ani
ocena ekspercka na 150 pytaniach.** Wykrywa ją porównanie ciągu znaków ze
źródłem — mechanicznie, na tysiącach przypadków.

### Czego brakuje

| Benchmark | Zakres | Metoda oceny | Polski |
|---|---|---|:--:|
| LegalBench-RAG | retrieval w aktach (EN) | anotacja ludzka | ✗ |
| LRAGE | całościowa ocena RAG (EN/KO/ZH) | **sędzia LLM** | ✗ |
| LexGLUE | klasyfikacja prawnicza (EN/EU) | etykiety | ✗ |
| Harvey LAB | 1 200 zadań agentowych, 24 dziedziny | 75 tys. kryteriów eksperckich | ✗ |
| Multi-Legal-Bench | 6 jurysdykcji, w tym Polska | metadane rejestrów | częściowo |
| LEPISZCZE / LLMzSzŁ | ogólny NLP / egzaminy | etykiety | ✓ |

**Nie istnieje benchmark mierzący wierność cytatu w polskich aktach sprawy.**
Multi-Legal-Bench obejmuje Polskę, ale w zadaniach klasyfikacyjnych
(rodzaj sądu, forma orzeczenia), a nie w pytaniach do akt z cytatem.
Ta luka jest tu wypełniana.

### Dlaczego nie sędzia LLM

Bo model oceniający dzieli słabości z ocenianym i bywa pobłażliwy dokładnie
tam, gdzie ryzyko jest największe — przy odpowiedzi sformułowanej pewnie
(ADR-0006).

Stanowisko to ma niezależne potwierdzenie na gruncie **polskiego prawa**:
recenzowana praca w *Artificial Intelligence and Law* (Springer, 2026),
oparta na egzaminie kwalifikacyjnym na członka Krajowej Izby Odwoławczej,
nosi tytuł wprost — *„LLM-as-a-Judge is Bad"*.

Warto zauważyć, że LRAGE, dziś wiodące narzędzie do oceny prawniczego RAG-a,
opiera punktację właśnie na sędzim LLM z rubrykami. Ten benchmark idzie
świadomie w przeciwną stronę.

---

## 🇵🇱 Na czym polega metoda

### Pary dopasowane

Każdy przypadek odpowiadalny ma **bliźniaka identycznego co do formy**,
różniącego się wyłącznie wartością kotwicy:

```
A.  „Czego dotyczy kwota 12 500 zł w aktach tej sprawy?"    kwota JEST
B.  „Czego dotyczy kwota 12 840 zł w aktach tej sprawy?"    kwoty NIE MA
```

Zdanie zawierające 12 500 zł jest znane co do znaku — prawda wzorcowa
powstaje bez udziału człowieka. Kwota z bliźniaka została sprawdzona
wyszukiwaniem po całych aktach i nie występuje, więc jedyną poprawną
odpowiedzią jest odmowa.

**Bliźniak musi być wiarygodny.** Pierwsza wersja generatora produkowała
„16 kwietnia 7029 r." — taki przypadek mierzy reakcję na absurdalny rok,
a nie sprawdzenie akt. Przesunięcia są więc zależne od typu: w datach
zmienia się dzień i miesiąc, rok zostaje; w kwotach zachowany jest rząd
wielkości.

### Miara naczelna: rozróżnialność par

Para liczy się **tylko** wtedy, gdy system zacytował właściwy fragment
w przypadku odpowiadalnym **oraz** odmówił w bliźniaku.

| Zachowanie | J-3 (odmowa poprawna) | J-4 (odmowa fałszywa) | **Rozróżnialność par** |
|---|---:|---:|---:|
| Zawsze odmawiaj | 100% ✅ | 100% ❌ | **0%** |
| Zawsze odpowiadaj | 0% ❌ | 0% ✅ | **0%** |
| Rozróżnia | wysokie | niskie | **> 0%** |

Klasyczne metryki dają się oszukać zachowaniem zdegenerowanym i trzeba je
oglądać parami. Ta miara nie daje się — obie degeneracje dostają zero.
Pytania w parze mają identyczną formę, więc różnicy nie da się wytłumaczyć
trudnością pytania. To zwykły eksperyment z grupą kontrolną, przeniesiony
na grunt oceny RAG-a.

> ⚠️ Wynik 50% **nie** znaczy „w połowie dobrze". Znaczy, że w połowie par
> system zachował się tak samo wobec pytania z odpowiedzią i bez odpowiedzi —
> czyli w tych parach akt nie sprawdzał.

### Co to daje w praktyce

- **Skaluje się z korpusem, nie z czasem prawnika.** Gold set wymagający
  weryfikacji ludzkiej rośnie do ~150 pytań i tam się zatrzymuje. Ten
  generator robi tysiące przypadków z tych samych akt.
- **Nie zastępuje gold setu.** Mierzy wierność cytatu i odmowę, a nie
  poprawność merytoryczną. Obie miary są potrzebne, do różnych rzeczy.
- **Jest powtarzalny.** Ziarno losowe w wyniku — ten sam przebieg da te same
  przypadki, więc różnica między wydaniami jest różnicą systemu.

---

## 🇬🇧 What this is

### The problem the market has and cannot measure

Stanford RegLab's preregistered study, later published in the *Journal of
Empirical Legal Studies*, found that Lexis+ AI hallucinated in **over 17%**
of queries and Westlaw AI-Assisted Research in **over 34%** — while vendors
advertised "100% hallucination-free linked legal citations".

A 2026 independent review that graded 3 000 answers found that **24% cited or
applied law that did not support the claim**. That is not a model getting a
fact wrong; that is a citation that does not say what it is claimed to say.

Neither an LLM judge nor a 150-question expert gold set reliably catches this
class of error. Character-level comparison against the source does, at scale.

### The gap

No benchmark measures citation fidelity over **Polish** case files.
LegalBench-RAG and LRAGE are English/Asian; LexGLUE is EN/EU classification;
Harvey LAB is English agentic work product; Multi-Legal-Bench covers Poland but
only for registry-metadata classification tasks. LEPISZCZE and LLMzSzŁ are
general-purpose Polish NLP.

### Why no LLM judge

A judge model shares the failure modes of the model it grades and is most
lenient exactly where the risk is highest — confidently phrased answers
(ADR-0006). This position has independent support in the Polish legal setting:
a peer-reviewed paper in *Artificial Intelligence and Law* (Springer, 2026),
built on the Polish National Appeal Chamber qualification exam, is titled
*"LLM-as-a-Judge is Bad"*.

Notably, LRAGE — currently the leading legal-RAG evaluation tool — scores with
a rubric-based LLM judge. This benchmark deliberately goes the other way.

### Method in one paragraph

Every answerable case has a **form-identical twin** that differs only in the
anchor value and is verified absent from the case files by exhaustive search.
Ground truth for answerable cases is an exact character span. A pair counts as
discriminated only if the system cites the correct span **and** refuses the
twin, so "always answer" and "always refuse" both score zero. Twins are kept
*plausible* — dates shift day and month but keep the year — because an absurd
value would test sanity rather than grounding.

---

## Uruchomienie / Running

```bash
python -m eval.benchmark.przebieg --sprawa 3 --sprawa 4 --par 25
```

| Parametr | Znaczenie / Meaning |
|---|---|
| `--sprawa N` | sprawa w bazie panelu; można wielokrotnie / case id, repeatable |
| `--par N` | par dopasowanych na sprawę / matched pairs per case |
| `--dokumenty N` | ogranicz liczbę dokumentów / cap documents loaded |
| `--ziarno N` | ziarno losowe / random seed (default 42) |
| `--bez-szczelnosci` | pomiń test przecieku między sprawami / skip cross-case leakage |

Wynik trafia do `eval/wyniki/benchmark-<data>.{md,json}` — raport dwujęzyczny
i pełne dane do dalszej analizy.

## Kategorie przypadków / Case categories

| Kategoria | Oczekiwanie | Co mierzy |
|---|---|---|
| `fakt_zakotwiczony` | cytat | wierność cytatu, trafienie w zakres |
| `bez_pokrycia` | odmowa | odporność na zmyślenie (J-3) |
| `pulapka_liczbowa` | odmowa | wrażliwość na bliską, ale inną wartość |
| `szczelnosc` | odmowa | **przeciek między sprawami — próg zerowy** |

Szczelność ma próg zerowy, nie procentowy. Jedno trafienie to naruszenie
tajemnicy zawodowej, a nie spadek metryki.

## Zasada danych / Data policy

Benchmark uruchamiamy wyłącznie na korpusie syntetycznym i publicznym
(wymaganie T-6, `docs/09-compliance/tajemnica-zawodowa.md`). Sprawy 3 i 4 to
publiczne orzeczenia SAOS i jawne akta federalne USA. **Rzeczywiste akta
klienta nie wchodzą do żadnego przebiegu ewaluacyjnego.**

---

## Źródła / Sources

- Stanford RegLab, *Hallucination-Free? Assessing the Reliability of Leading AI
  Legal Research Tools* — <https://reglab.stanford.edu/publications/hallucination-free-assessing-the-reliability-of-leading-ai-legal-research-tools/>
- *LLM-as-a-Judge is Bad*, Artificial Intelligence and Law (Springer, 2026) —
  <https://link.springer.com/article/10.1007/s10506-026-09505-w>
- LegalBench-RAG — <https://www.semanticscholar.org/paper/3daedc1e0a9db8c4dda7e06724b0b556f64c0752>
- LRAGE — <https://arxiv.org/html/2504.01840>
- Multi-Legal-Bench — <https://arxiv.org/html/2605.29738v1>
- Harvey LAB — <https://github.com/harveyai/harvey-labs>
- LLMzSzŁ — <https://arxiv.org/abs/2501.02266>
