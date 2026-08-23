# The road to an enterprise product

> **A planning document.** It sets out what separates the current state from a system a law firm can put to work on real case files. Every number comes from a measurement rather than an estimate, with the source given alongside. Position as at 15.08.2026.

## 0. The principle of this document

Every item states **what**, **what it connects to**, and **how to check that it works**. An item without a checkable criterion is a wish rather than a task.

Three weeks of work on this system taught one thing forcefully: **a declaration that something works is not proof that it works.** In this session four consecutive fixes each had a sensible justification and changed not a single digit in the measurement. That is why the plan below is built around gates rather than around a list of features.

## 1. The factual position: what has been measured

### 1.1 Working and measured

| Area | State | Evidence |
|---|---|---|
| Citation by sentence number | works | ADR-0007; the `enum` grammar forces a number from the set of sentences shown |
| Character-by-character citation verification | works | `weryfikator_cytatow.py`, 17 tests |
| Confinement within a single case | works | `test_panel_izolacja_spraw.py`, 13 tests |
| Resistance to injection | 100% | `tests/injection/`, 15 structural tests |
| Deadline engine | works, **not wired in** | 14 tests, no use in the panel |
| Map-reduce analysis (the deep track) | works | 320 judgments, 16.3 million characters, in around 265 s |
| Benchmark v2 with stage attribution | works | `eval/benchmark/v2.py` |
| Control journal without case content | works | `test_dziennik.py`, 10 tests |
| Unit tests | **318 green** | `pytest -m "not behawioralny"` |

### 1.2 Answer quality: numbers, not impressions

Measurement v2, `--par 25`, seed 42, the full corpus (320 SAOS judgments and 402 documents from USA v. Lacey):

| Measure | Value | Note |
|---|---:|---|
| Accuracy | **68.0%** | the citation hits one of the true occurrences |
| Retrieval recall | **90.0%** | the reference sentence reaches the model |
| Mean occurrences of an anchor | 5.9 | v1 knew of one and penalised the rest |
| False refusals | 16 of 50 | dominated by `zakotwiczenie` (9) |

**The 22-point gap between recall and accuracy** is loss after retrieval: the sentence reaches the model and does not turn into a citation.

### 1.3 Measured causes of the losses

| Cause | Measurement | Status |
|---|---|---|
| "Lost in the middle": 12 documents in one call | 12 documents give **2 of 9**, 1 document gives **8 of 9** | fixed by the cascade |
| Escalation on questions with no coverage | refusals took 141 to 350 s | fixed by the discriminator gate (down to 10 to 24 s) |
| HTML inside the case 3 file | **42.5% of the content is markup** | **open** |
| Support control | cost 6.2 points of accuracy | disabled, awaiting a set to judge it on |

### 1.4 What does not exist at all

| Missing | Requirement | Consequence |
|---|---|---|
| Accounts, login, roles | F-30, F-36 | the panel runs on `127.0.0.1` only, single-user working |
| A person in the audit log | **F-33** | the log is not evidence of due diligence (T-4) |
| File upload and OCR | F-01 to F-03 | content is pasted by hand; **11% of the Lacey file is scans** |
| Deadlines in the interface | F-21 to F-24 | the engine is ready and unused |
| Ethical walls | F-32 | a conflict of interest is undetectable |
| A separate key for defence material | T-1, T-2 | a flag in the database instead of encryption |
| Export into a procedural document | F-35 | the lawyer retypes by hand |
| Backups and restore | `operations/backup-and-recovery.md` | no executable procedure |
| Images pinned by `sha256` | **I-8** | the only red gate unrelated to Docker |

## 2. Definition of readiness: what "enterprise" means

The system is ready when **all of the following are true at the same time**. Not "most", not "broadly".

### 2.1 Quality gates

| Gate | Threshold | Today |
|---|---|---:|
| J-1, citation fidelity | ≥ 99% | around 100% (sentence number) |
| J-2, substantive correctness | ≥ 85% on the gold set | **unmeasured**; the gold set has 6 questions |
| J-3, refusal where there is no coverage | ≥ 90% | 87.5%, below target |
| J-4, false refusal | ≤ 10% | 12.5%, above limit |
| Anchored accuracy | ≥ 85% | 68.0%, below target |
| Leakage between cases | **0** | 0 |

### 2.2 Isolation gates

All of I-1 to I-9 green, including **I-8** (images pinned by `sha256`) and **O-1** (packet capture: zero outgoing packets across a full cycle).

### 2.3 Compliance gates

| | Deadline |
|---|---|
| K-1, KSC scope assessment | **15.09.2026** |
| K-2, KSC registration | **02.10.2026** |
| DPIA approved by the DPO | before the first real case files |
| Deadline rules approved by a lawyer | before deadlines are switched on |

**K-1 and K-2 do not depend on code and wait for nothing.** They are the only items in this document with a statutory deadline.

### 2.4 Operational gates

- A restore from backup carried out and **documented with the time it took**
- The incident runbook exercised, not merely written
- Assured maintenance: several to a dozen hours a month (`hardware-and-costs.md`)

## 3. Target architecture: what connects to what

```
+- INPUT -----------------------------------------------------------+
|  scan/PDF/DOCX -> pliki.py -> ocr.py -> oczyszczanie.py            |
|                                  |                                 |
|                          HUMAN GATE: preview and correct the OCR   |
|                                  v                                 |
|                            baza.dodaj_dokument                     |
|                            (language, hash, defence material?)     |
+------------------------------+------------------------------------+
                               v
+- RETRIEVAL -------------------------------------------------------+
|  wyszukiwarka.dokumenty_trafne   <- BM25 over documents            |
|  wyszukiwarka.wybierz_zdania     <- BM25 over sentences, per lang. |
|  zdania.podziel_na_zdania        <- offsets into the ORIGINAL      |
+------------------------------+------------------------------------+
                               v
+- GENERATION ------------------------------------------------------+
|  CASCADE:  4 documents -> no anchoring? -> one document at a time  |
|            (gate: is the discriminator in the file at all)         |
|  schematy.py -> enum grammar -> the model indicates a sentence NO.  |
+------------------------------+------------------------------------+
                               v
+- CONTROL (6 layers) ----------------------------------------------+
|  1. weryfikator_cytatow   citation exists, char by char    free    |
|  2. sentence numbers      the CODE rebuilds the citation    free    |
|  3. wyrozniki             the answer is on the question     free    |
|  4. wsparcie              the citation SUPPORTS the claim   free    |
|  5. kontrola              a clean yes/no query              ~3 s   |
|  6. glosowanie            self-consistency over numbers     N times|
+------------------------------+------------------------------------+
                               v
+- OUTPUT ----------------------------------------------------------+
|  answer + confidence + reason for rejection                        |
|  -> dziennik.py    (counts and a digest, NEVER content)            |
|  -> baza.zapisz_audyt (who, when, what)                            |
|  -> eksport.py     (DOCX/MD with citations, pseudonymised)         |
+--------------------------------------------------------------------+
```

### 3.1 Integration points: where systems meet

| Connection | Direction | What flows | Correctness condition |
|---|---|---|---|
| `pliki` to `ocr` to `baza` | one way | text and metadata | offsets computed AFTER cleaning, not before |
| `konta` to `baza` | cuts across everything | `uzytkownik_id` | **no query for documents without it** |
| `konta` to `audyt` | one way | the person performing the operation | the checksum material is versioned |
| `zdania` to `schematy` | one way | sentence numbers into `enum` | **they must come from the same call** |
| `wybor` to `weryfikator` | one way | offsets into the original | the same document set on both sides |
| `terminy` to `kalendarz` to `skrzynka` | a chain | event, date, warning | an unconfirmed deadline **is not binding** |
| `dziennik` to the DPO panel | read only | counters | **no case content whatsoever** |

**Three connections that fail quietly:**

1. **`zdania` to `schematy`.** The numbers have to come from the same call. A mismatch turns the safeguard into an error generator: confirmed by experiment, the model will indicate a number that does not exist, because it is the only one permitted.
2. **`oczyszczanie` and the offsets.** Cleaning HTML shifts every offset. Documents uploaded before the change carry citations in the conversation history that will stop matching. This needs a migration, not a switch.
3. **`konta` to `audyt`.** Adding the person to the checksum material invalidates the chain backwards. Versioning the entry is a condition, not an improvement.

## 4. Phases

The order follows from dependencies rather than preference. Phase E1 blocks half of the rest.

### E1. Identity, roles, an audit log with a person

**Why it comes first:** without `uzytkownik_id` there is no way to build ethical walls, defence material handling, the inbox or a credible audit trail. F-33 is unmet today, and T-4 calls the log evidence of due diligence.

| Task | Connects to | Criterion |
|---|---|---|
| `konta.py`: users, `scrypt`, sessions | `baza`, `serwer` | registration then login, with no email confirmation |
| Three roles: lawyer, secretariat, trainee | every API route | the permission matrix lives in tests, not in documentation |
| `dostep_do_sprawy` | `baza.tresci_dokumentow` | **no function returns documents without a `uzytkownik_id`** |
| Audit with a person, plus chain versioning | `baza.zapisz_audyt` | `lancuch_spojny=true` across the migration boundary |
| WAL plus a connection per thread | `baza.polacz` | two people at once with no "database is locked" |
| Profile switching | `index.html` | changing person on one computer takes under 5 s |

**Gate E1:** lawyer A's case is indistinguishable from a non-existent one for lawyer B; the secretariat is refused in the chat; a trainee cannot confirm a deadline; an audit entry carries a name.

### E2. Input: files, OCR, quality

**Why it comes second:** today content is pasted by hand, and 11% of the Lacey file is scans with no text layer. This is the secretariat's work and the largest functional hole.

| Task | Connects to | Criterion |
|---|---|---|
| `pliki.py`: multipart upload | `serwer`, `konta` | PDF, DOCX, TXT, a size limit, type checked by content |
| `ocr.py`: Tesseract with `pol.traineddata` | `pliki` | a SYSTEM dependency, not a Python package |
| A human gate for OCR correction | `index.html` | a document does not enter the index before acceptance |
| **HTML cleaning on import** | `baza.dodaj_dokument` | measured: 42.5% of the case 3 content is markup |
| A sentence quality filter in the panel | `zdania.zdanie_uzyteczne` | `n/d` and table fragments never become a citation |
| Character error rate measured on a sample | `eval/` | gates N-14 and N-15 |

**Offset migration.** Cleaning changes character positions. Documents already uploaded carry citations saved in the conversation history. Either the migration recomputes both, or cleaning applies only to new documents. There is no third option.

### E3. Deadlines: the highest return on work already done

**Why:** `SilnikTerminow` is written, tested (14 of 14) and **unused**. A missed deadline is the one place in the system where an error has a direct legal consequence, namely the loss of the right of appeal.

| Task | Connects to | Criterion |
|---|---|---|
| `terminy.py`: wiring the engine into the panel | `sprawy.silnik_terminow` | trap G-030: service on 12.08, not issue on 05.08 |
| Recognising the triggering event | the fast track | the model indicates the event **with a citation** and does not compute the date |
| Calendar and advance warnings | `skrzynka` | an **unconfirmed** deadline warns more loudly |
| Confirmation by a lawyer | `konta` | the secretariat role **cannot** confirm |

**The flow across three roles:** the secretariat enters the service, the model recognises the event, the engine computes deterministically (ADR-0005), the lawyer confirms. Without the last step the deadline is not binding.

### E4. Answer quality up to the gate thresholds

Today 68.0% against a threshold of 85%. Measured directions, in order of return:

| Direction | Basis | Expectation |
|---|---|---|
| Completing the cascade | 12 documents give 2 of 9, 1 document gives 8 of 9 | the largest single gain |
| Cleaning HTML | 42.5% of the input is markup | free space in the context |
| Growing the gold set to around 150 questions | six today | **J-2 is unmeasurable today** |
| Assessing the support control | it cost 6.2 points | needs a set that measures unfaithfulness |
| BM25 and vector hybrid | `polacz_rankingi` is ready and unused | recall above 90% |

**The support control is not rejected; it is unmeasured.** Benchmark v2 scores range overlap and is structurally unable to reward a layer that catches "a true citation supporting a false claim". What is needed is a set in which the claims deliberately contradict true citations.

### E5. Teamwork and output

| Task | Connects to | Criterion |
|---|---|---|
| A "what happened" inbox | `konta`, `terminy`, `zadania` | deadlines, finished analyses, documents from the secretariat |
| A durable queue with two tracks | `zadania.py` | an analysis ordered in the evening survives a restart |
| `eksport.py`: DOCX and MD with citations | `analiza`, `anonimizacja` | a citation carries the document reference and the character range |
| Pseudonymisation before export | F-35 | export outside the firm with no personal data |
| Ethical walls | `dostep`, `konta` | a wall is breached only by a decision with a justification |

### E6. Defence material

**The hardest item, and the only one that cannot be done "almost".**

Art. 178 pt 1 of the Polish Code of Criminal Procedure: defence privilege **cannot be lifted**. T-1 says it plainly: a flag in the database is changed by one `UPDATE`, a backup contains everything regardless of flags, and seizure of the hardware gives access to all of it.

| Task | Criterion |
|---|---|
| A separate store with a separate key | a dump of the main database **does not contain** defence material readably |
| The key outside the system (T-2) | a hardware carrier or two-person authorisation |
| A procedure for a demand from an authority | **settled by the firm's lawyer**, not by an engineer |

### E7. Operations

| Task | Criterion |
|---|---|
| **I-8**: images pinned by `sha256` | `skrypty/pobierz-digesty.sh` plus a review |
| **O-1**: packet capture | zero outgoing packets across a full cycle |
| Backups and restore | carried out, with **the time documented** |
| Incident runbook | exercised, not merely written |
| Disk encryption (N-22) | a precondition for logical access control |

### E8. Compliance

| | Deadline | Depends on code |
|---|---|---|
| K-1, KSC scope assessment | 15.09.2026 | **no** |
| K-2, KSC registration | 02.10.2026 | **no** |
| DPIA and DPO approval | before real case files | no |
| AI Act assessment | before deployment | no |
| Training (KSC and AI Act) | at deployment | no |

## 4A. The product layer: what the system is for a lawyer

> Sections 1 to 4 describe engineering. This one describes **the product**. Without it the system has good gates and nobody uses it.

### 4A.0 A finding that changes the priorities

A study of AI assistants in law firms found that **usefulness and fit with the legal context weigh more than the raw accuracy of the algorithm**. Firms shortlist three platforms, Harvey (38 of 50), CoCounsel (37 of 50) and Legora (35 of 50), and the differences in the scoring rubric are smaller than the differences in how they are used.

**The conclusion for us:** 68% accuracy in a tool that shows exactly where every citation came from is worth more in a law firm than 85% in a tool that asks to be taken on trust. That does not excuse us from raising accuracy; it sets the proportions.

### 4A.1 What is missing that daily work rests on

Today the panel keeps conversation history in the database (`wiadomosci`, split between a case thread and a document thread) but **does not surface it in the interface**: a thread cannot be named, yesterday's cannot be reopened, and there is no list.

A lawyer works a case for weeks. A conversation that cannot be resumed forces them to start from nothing on every return.

| Missing | What it means in practice |
|---|---|
| A list of threads | no way to know what has already been asked |
| A thread name | "conversation 3" instead of "discrepancies in the statements" |
| Resuming a thread | coming back after a week means starting over |
| Search within the history | "I asked about this, but when?" |
| A thread attached to a document | the data model has it, the interface does not show it |

### 4A.2 The thread data model

```sql
CREATE TABLE watki (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sprawa_id     INTEGER NOT NULL REFERENCES sprawy(id) ON DELETE CASCADE,
    uzytkownik_id INTEGER NOT NULL REFERENCES uzytkownicy(id),
    dokument_id   INTEGER REFERENCES dokumenty(id),   -- NULL = case thread
    nazwa         TEXT NOT NULL,        -- from the first question, editable
    przypiety     INTEGER DEFAULT 0,
    utworzono     TEXT NOT NULL,
    ostatnia_aktywnosc TEXT NOT NULL
);
```

`wiadomosci` gains a `watek_id`. Migration: existing messages go into a thread named "Rozmowa z <date>" per case and document, so **none is lost**.

**A thread belongs to a user, not to a case.** Two lawyers on the same case have separate threads; what they share is the material, not the conversation. That follows from F-30 (need-to-know) and from the fact that someone else's conversation can itself be information about litigation strategy.

### 4A.3 Citation navigation: an advantage competitors cannot copy

**This is where the architecture of this system yields a product advantage that is not available to others.**

A citation here is **a character range in the source document**, verified mechanically (ADR-0006, ADR-0007). Not "a source", not "document number 3", not "page 12", but an exact `poczatek:koniec`.

Competitors give a pointer to a document, because their citation is not faithful to the character. We can do this:

```
  answer --click the citation--> the document opens at that place,
                                 the fragment HIGHLIGHTED to the character
```

That turns verification from a task into a reflex. Research on legal user experience says it plainly: the interface has to **help verify sources efficiently**, because otherwise the lawyer stops verifying.

Extensions from the same mechanism:

- **the whole chain of reasoning clickable**: conclusion, finding numbers, citations, ranges in the file, with every link leading to a place in the file;
- **an extract of citations from a thread**: every confirmed fragment in one view, ready for a document.

### 4A.4 Showing what was rejected: transparency as a feature

The panel already collects reasons for rejection (`odrzucone` with `powod` and `szczegol`) and **does not show them to the lawyer**.

Competitors do not do this, because it looks bad. Here it is the other way round: it is the evidence that the system is working.

```
  OK  The witness testified that the vehicle was silver.
      [doc. 106, characters 8580-8976]                confidence: strong

  NO  The witness identified the driver.
      rejected: the sentence says they were NOT able to identify them
```

The second line matters more than the first. The lawyer sees that the system **rejected a claim that sounded credible**, and only that gives grounds to trust the first.

The confidence levels come from the control layers (`wsparcie`, `kontrola`), which are built and tested. **Their value is a product value, not only a measurement one:** benchmark v2 cannot reward a layer that catches "a true citation supporting a false claim", while the lawyer sees that information and uses it.

### 4A.5 Continuity over time: a feature nobody else has

`dziennik.py` records **a digest of the question**. From that comes a possibility I have not seen in any product of this class:

> **"You asked about this three weeks ago. The answer was different then, and four documents have joined the case since."**

Case files grow. An answer given before an expert opinion arrived may be out of date today, and the lawyer has no way of noticing. A system that knows the digest of the question and the dates of the documents gets this for free.

Variants:

- **a repeated question**: show the previous answer and the difference;
- **a new document arrived**: "3 threads may need rerunning";
- **a change of model**: "answers from before the update are marked".

The last point matters for compliance: `models/manifest.md` requires the gates to be passed on every change of model. Tagging answers with the model version makes that traceable.

### 4A.6 A working folder: from answer to document

Today the analysis ends on the screen. The lawyer retypes the findings by hand, losing the citations on the way, which is the most valuable thing the system produces.

```
  thread --> mark findings --> working folder --> export
                                      |
                                      +- DOCX with citations and references
                                      +- Markdown for further work
                                      +- pseudonymisation (F-35)
```

The folder is a **cross-section through threads**, not another thread: the lawyer gathers findings from five conversations about the same case into one body of material for a document.

### 4A.7 Interface rules for a non-technical user

The audience is a lawyer, not an engineer. Six rules, each with a consequence:

**1. No model jargon.** Not "temperature", "context", "embedding" or "chunk". Instead of "num_ctx exceeded", say "the document is too long, indicate a fragment".

**2. The number of documents tells you about time and quality.** `agent.strategia(n)` computes this from measured values:

```
  1 document      ~5 s    fastest and most accurate
  4 documents    ~13 s
  12 documents   ~3 min   selecting fewer will give an answer
                          faster AND more accurately
```

The last line **runs against the user's intuition** and therefore has to be said outright. Measured: 12 documents in one call gives 2 of 9, one document gives 8 of 9. Without that information the lawyer selects everything "just in case" and gets the worst possible result.

**3. A refusal is an answer, not a failure.** "There is no basis in this case file for an answer" needs different typography from a connection error. The lawyer should see that the system **checked and did not find**.

**4. Progress with the name of the stage.** An analysis takes minutes. "Analysing document 4 of 12: expert opinion" says more than a bar.

**5. Nothing is lost when the browser closes.** An analysis ordered in the evening waits in the inbox in the morning. That needs the durable queue (E5).

**6. Three roles, three different landing screens.** The secretariat sees the upload queue and the deadline calendar. The lawyer sees their own cases and the inbox. The trainee sees the cases they are assigned to. One screen for everyone means it is good for nobody.

### 4A.8 Comparison with the market

| Feature | Harvey, CoCounsel, Legora | LQ.AI | Here |
|---|---|---|---|
| Case workspace | yes, matters or workspaces | yes, projects | to do, **E5** |
| Threads with history | yes | yes | to do, **4A.2** |
| Citation as a **character range** | no, a pointer to a document | partly | yes, **by construction** |
| Rejected statements shown | no | no | to do, **4A.4**; we have the data |
| Verification without an LLM judge | no | no, stages 3 and 4 are judges | yes, ADR-0006 |
| Published quality figures | no | none | yes, benchmark v2 |
| A repeated question over time | no | no | to do, **4A.5** |
| Working without a network | no | partly | yes, by design |
| Polish criminal case files | no | no | yes |

**The three items where we stand alone** (citation to the character, no LLM judge, published figures) follow from the architecture and cannot be retrofitted; a competitor would have to rebuild the core.

**The four items where we are behind** (workspace, threads, rejected statements, continuity) are interface work measured in weeks, not quarters.

That is the whole product thesis: **we have what cannot be copied, and lack what can be added.**

### 4A.9 Order of product work

| # | Task | Depends on | Why here |
|---|---|---|---|
| P1 | Threads: list, name, resume | E1 | without it, working a case is impossible |
| P2 | Clickable citation with highlighting in the document | | **the largest advantage, and the data already exists** |
| P3 | Rejected statements and confidence levels | E4 | transparency as evidence of diligence |
| P4 | Document selection with a time hint | | `agent.strategia` is ready |
| P5 | The "what happened" inbox | E1, E5 | working at different times |
| P6 | Working folder and export | P1 | it closes the path to a document |
| P7 | Continuity over time | `dziennik` | a differentiator nobody else has |

**P2 before P3 is not an accident.** A clickable citation works on data the system already produces. It is a week of interface work and the largest jump in perceived trustworthiness.

## 5. Dependency matrix: what blocks what

```
E1 accounts ---+--> E3 deadlines (confirmation by role)
               +--> E5 inbox, ethical walls
               +--> E6 defence material (authorisation)
               +--> audit with a person (F-33)

E2 input ------+--> E4 quality (cleaning frees context)
               +--> E3 deadlines (date of service from a scan)

E4 quality --------> admission of real case files (DPIA)

E7 operations -----> production deployment

E8 compliance -----> INDEPENDENT, runs in parallel, statutory deadline
```

**The practical conclusion:** E1 and E8 start immediately and in parallel. E8 needs not a single line of code and carries the only hard deadlines.

## 6. What this plan deliberately does not do

| Rejected | Reason |
|---|---|
| An LLM judge rating faithfulness | ADR-0006; confirmed independently by *"LLM-as-a-Judge is Bad"*, Springer 2026, on material from the Polish public procurement board examination |
| Fine-tuning the model on case files | risk of fixing data in the weights; retrieval gives the same effect without it |
| A cloud model "for non-sensitive tasks" | the boundary would be fiction; there is no way to guarantee that non-sensitive data contains nothing sensitive |
| A shared database on the LAN | the user chose an installation per computer; the route to a server stays open and **needs no rewrite of E1** |
| GitHub Actions on the private instance | that repository contains the threat model and the topology of an instance processing criminal case files |
| Extending benchmark v1 | it scores against a single reference while there are 5.9 true occurrences, which is systematic bias rather than noise |

## 7. Risks that have to be named

| Risk | Consequence | Mitigation |
|---|---|---|
| **Q4 on 8 GB of VRAM** | the DPIA does not admit real case files | the profile is a switch; buying a GPU rewrites nothing |
| Maintaining the fork | an unpatched system is a risk, not a saving | several to a dozen hours a month, assured **before** deployment |
| A profile protects against a colleague, not against a disk | logical control, not cryptographic | full disk encryption (N-22) plus E6 |
| Installation per computer | no shared files between lawyers | a deliberate choice; the way out is a server on the LAN |
| A gold set of six questions | **J-2 is unmeasurable** | a lawyer's time, to be planned early |
| Degradation after a model change | quiet, unlike a crash | `dziennik.py` plus the full gates on every change |

## 8. Order of starting

If work began tomorrow, in this order:

1. **K-1, the KSC scope assessment**: a statutory deadline, no code
2. **E1, accounts and an audit log with a person**: unblocks half the rest
3. **E2, input: files and OCR**: the secretariat's work, and 11% of the file is scans
4. **E3, deadlines**: work already done, the highest return, and an error here has legal consequences
5. **E4, quality up to the gate thresholds**: measured by v2, with a short loop of around 4 minutes
6. The rest according to the dependency matrix

**Item 1 before item 2 is not a mistake.** K-1 and K-2 are the only things in this document that cannot be made up for by working harder: they have a statutory deadline and do not depend on whether the code is ready.
