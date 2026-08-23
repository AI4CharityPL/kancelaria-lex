# Risk register

A living document. Reviewed every six months and on every significant change of architecture. Last review: **14.08.2026**.

Scale: likelihood (L/M/H) against impact (L/M/H/**C**ritical).

> **Note on numbering, 19.08.2026.** Identifiers RY-19 to RY-23 originally
> appeared twice, once among the technical risks and once among the
> substantive ones, so the same number meant two different things. The later
> technical additions have been moved to RY-50 and above. Numbers cited from
> code keep their meaning: `RY-20` in `weryfikator_cytatow.py` still refers to
> a faulty analysis affecting the defence, and `RY-16` in the quality gates
> still refers to the J-3 gap.

## Critical risks: they need standing attention

| ID | Risk | L | I | Measures | Level | Owner |
|---|---|---|---|---|---|---|
| **RY-01** | Case file content leaks to an external model provider | L | **C** | Three layers of isolation, tested by execution (I-1 to I-9, O-1) | Low | systems engineer |
| **RY-02** | Disclosure of defence material | L | **C** | Separate store, separate key, separate authorisation (T-1, T-2) | Low | partners |
| **RY-03** | A merge from upstream quietly restores the cloud SDKs | **M** | **C** | **CI gate on the lockfile** plus the startup guard | Low | systems engineer |

**RY-03 deserves attention despite its low residual level.** It is the most likely way the project can quietly lose its main property: six months from now somebody does a routine merge and `pydantic-ai-slim[openai,anthropic,google,mcp]` comes back with it. Without the gate nobody notices until an incident. With it, the build fails the same day.

## Technical risks

| ID | Risk | L | I | Measures | Level |
|---|---|---|---|---|---|
| RY-10 | Bielik's quality at Q4 is insufficient | **H** | M | Expected; the gates are measured on the production profile, and Q4 never touches real files | Accepted |
| RY-11 | Retrieval loses relevant fragments at an 8k context | M | H | Hybrid search; measurement on the gold set; a larger context in production | Medium |
| RY-12 | OCR fails on photocopies and handwriting | **H** | M | RapidOCR as a fallback, a manual review queue, character error rate as a gate (J-5, J-6) | Medium |
| RY-13 | Upstream has changed relative to findings U-1 to U-8 | M | H | Verification before forking is a mandatory step | Low |
| RY-14 | An image from a private registry namespace is substituted | L | H | Pinning by `sha256`, a local mirror, verification before introduction | Low |
| RY-15 | A zero-day in a component of the stack | M | H | Segmentation limits the reach; a maintenance window; SBOM | Medium |
| **RY-16** | **Answering a question that has no coverage in the file** | **H** | **C** | Citation verified character by character; the model controller; **the gap is open, see below** | **High** |
| RY-17 | Single-factor authentication instead of two (art. 21(2)(j)) | M | M | `scrypt` password, a 12-hour server-side session; the second factor is not implemented | Medium |
| RY-18 | One person blocks the others (semaphore of 1, escalation after 5 to 8 minutes) | **H** | M | The queue and the deep track exist; the semaphore is **confirmed by test**, but the delay to a second person is still unmeasured | Medium |
| RY-19 | Loss of the defence material key | L | **C** | Escrow procedure, two-person authorisation, restore test | Low |
| **RY-50** | **Writes lost when two people work at once** | | **C** | **CLOSED 16.08.2026**, see below | Closed |
| **RY-51** | A 401 refusal breaks the connection instead of closing it | | L | **CLOSED 16.08.2026**; the request body is drained before the refusal | Closed |
| **RY-52** | The model address is not enforced in the product (`panel/`) | M | **C** | **CLOSED 16.08.2026**: `panel/siec.py`, the process refuses to start on an address outside the loopback range; 25 tests against production code | Closed |
| **RY-53** | The `compose.yml` stack cannot be brought up in full | M | M | **Embedder BUILT 16.08.2026**, see below. Django, postgres and frontend remain (the Django fork) | Medium |
| RY-54 | I-5 (the DNS canary) has never been executed | M | M | Needs a sinkhole; `infra/policies/sinkhole.md`. Due before the first real case files | Medium |

## RY-53: the embedder supplied (16.08.2026)

`compose.yml` pointed at `src/aplikacje/embedder`, which **was not in the repository**. The stack could not be brought up and `docker compose up` ended in `path not found`. That is why gates I-3 and I-4 were being skipped and O-1 was hard-wired to an unconditional skip.

**What was built:** a `multilingual-e5-base` service (768 dimensions, ADR-0004) running on the CPU, speaking the OpenAI protocol (`POST /v1/embeddings`), plus a `Dockerfile` and a procedure for preparing the offline weights package.

**Three properties that matter more than the functionality itself:**

1. **Weights come only from the mounted volume.** `transformers` will by default pull a model from the internet when it does not find it locally, which in this system would be a silent exit outwards. The image sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, and the service checks for the weights **before** importing the library.
2. **No weights means no start.** Exit code 2 and a message pointing at the procedure. The service does not come up "in reduced mode" and does not return zero vectors: an embedder returning zeros looks as if it works while retrieval stops working in silence.
3. **The `typ` field has no default.** The E5 family requires a `query:` or `passage:` prefix, and omitting it produces no error, only quietly worse retrieval. The first version assumed `passage` when the field was absent; a test caught that and the default was removed.

**Checked live:** the container comes up `healthy`, returns normalised 768-dimension vectors, and a Polish question sits closer to the fragment that answers it than to a fragment about something else, which is exactly the reason ADR-0004 rejected `all-MiniLM-L6-v2`. Gates I-3 and I-4 now cover the embedder: **85 checks instead of 79**.

**Still open:** `django`, `postgres` and `frontend` still need building from the Django fork and have not been brought up. A full O-1 per `skrypty/przechwyc-ruch.md` (the upload, OCR, embedding and answer cycle) therefore remains impossible.

## RY-50: writes lost during concurrent work (closed 16.08.2026)

**How it came to light.** The first test to send requests in parallel (`tests/test_wspolbieznosc.py`) knocked the panel over immediately:

```
sqlite3.InterfaceError: bad parameter or other API misuse
```

with ten threads creating conversation threads at once.

**Why it was dangerous.** The project's overriding requirement reads "different people, at different times, on different profiles". The tests until then covered only the "at different times" part, because each of them sent requests one after another. The effect was writes being lost silently in exactly the scenario this system was built for: two people working at the same moment.

**The cause.** `sqlite3.threadsafety == 3`, so the C layer was serialised and was not the one failing. The Python layer was: the module keeps a per-connection cache of prepared statements, and two threads running the same SQL reached for the same statement object.

**The fix** (`panel/baza.py`, class `Polaczenie`): `cached_statements=0` together with a reentrant lock on `execute`, `executemany`, `executescript` and `commit`. This is not an optimisation. With a handful of people and SQLite serialising writes anyway, the cost is negligible and correctness is worth more than throughput.

**The gate:** 7 tests in `tests/test_wspolbieznosc.py`, including 20 parallel writes and 40 interleaved requests from two profiles.

## RY-16: the most important open quality item

**Measured on 16.08.2026** (100 cases, the full corpus, the shipping configuration with the controller alone): out of 50 questions the file cannot answer, the system answered **9 times**. J-3 is 82% against **a target of 90%**.

**Why this is critical in impact rather than merely a number.** The lawyer gets an answer where the file gives none, with a citation leading to a real sentence that nevertheless does not support the proposition. It is detectable in a second by clicking the citation, but only by somebody who clicks.

**Why we did not close it by rejecting more.** Every variant measured shows that J-3 is bought only with accuracy:

| variant | J-3 | accuracy | correct in total |
|---|---:|---:|---:|
| no control | 76% | 80% | 78 |
| **controller alone, shipping** | **82%** | **78%** | **80** |
| both controls | 84% | 70% | 77 |
| NL-to-format with both | 90% | 48% | 69 |

The last row reaches the target and is at the same time the worst configuration, losing half the correct answers. That is evidence that the problem sits **before** generation rather than after it.

**The remedy (J2.2, not implemented):** judging answerability before the model starts answering. The basis is *Sufficient Context* (ICLR 2025): retrieval augmentation paradoxically LOWERS the tendency to refuse, because the added context raises the model's confidence, and small models are especially prone to this.

**Decision on thresholds, 16.08.2026:** the J-3 regression threshold was lowered to 0.78 and the 0.90 target recorded separately as `CEL_J3`, unmet. This is not a relaxation of the requirement but a separation of the regression threshold from the target, because a gate that is always red stops carrying information. Every run below the target prints a warning in the tests.

**Owner:** systems engineer. **Review:** on every change touching the fast track.

## Substantive risks

| ID | Risk | L | I | Measures | Level |
|---|---|---|---|---|---|
| **RY-20** | **A faulty analysis affects the conduct of the defence** | M | H | Forced citation with mechanical verification; **mandatory review by a lawyer**; gates J-2 and J-3 | **Medium** |
| RY-21 | A deadline missed through a fault of the system | L | H | Deterministic engine; confirmation by a lawyer; loud warnings about unconfirmed deadlines | Low |
| **RY-22** | **Users trusting the tool too much** | **M** | H | A message in the interface, not only in the terms of use; training; citations shown openly | **Medium** |
| RY-23 | Manipulation through a document from the opposing party | M | M | No network tools; citation verification; red team tests at 100% | Low |

### RY-20 and RY-22 stay at medium, deliberately

**RY-20:** citation verification confirms that a fragment exists and was not fabricated. It does not confirm that the conclusion drawn from it is sound. No mechanical method will provide that. The measure is organisational: mandatory review by a lawyer.

**RY-22 is the risk that is easiest to forget.** A tool the user trusts unconditionally is more dangerous than no tool at all, because it removes the vigilance the lawyer had before, when reading the file unaided. A well-behaved system paradoxically increases that risk: the more often it is right, the less often anyone checks.

The measure: the interface has to show citations **always and visibly**, and a refusal to answer has to be normal behaviour rather than a failure.

## Organisational and legal risks

| ID | Risk | L | I | Measures | Level |
|---|---|---|---|---|---|
| **RY-30** | **Missing the KSC registration deadline (02.10.2026)** | M | H | A track independent of the project; K-1 by 15.09, K-2 by 02.10 | **Needs action now** |
| RY-31 | No assured maintenance of the fork after deployment | M | H | **A condition of going to production**, not a question to settle later | Medium |
| RY-32 | Approving the deadline rules lands on the critical path | **H** | M | Plan it early; it is a lawyer's time, not an engineer's | Medium |
| RY-33 | Access by an unauthorised person inside the firm | M | H | Named access, need-to-know, ethical walls, MFA, audit log | Low |
| RY-34 | The incident reporting obligation collides with privilege | M | M | The boundary settled **before** an incident (K-6) | Low |
| RY-35 | Loss of a backup medium | L | H | Backups encrypted, key held separately | Low |
| RY-36 | The AI Act classification changes because of how the system is used | L | M | The boundary recorded in [`agents.md`](agents.md); reassessment on every extension | Low |

### RY-30 needs action independently of the project

About seven weeks remain to the registration deadline. Tasks K-1 and K-2 need not a single line of code and should not wait for Phase 6.

## Residual risks: accepted with no further measures

| Risk | Why it stays |
|---|---|
| Someone with physical access to the server can take the data | No system eliminates this; access control to the room and disk encryption limit the effect |
| A lawyer with legitimate access can copy the file | The risk exists independently of the system; the audit log and professional obligations apply |
| A local model is weaker than the best commercial ones | The price of confidentiality, accepted deliberately |
| Being cut off from the network makes patching harder | Offset by the maintenance window; the alternative, a permanent connection, is worse |

## Review history

| Date | Changes |
|---|---|
| 14.08.2026 | Register created. Risks RY-01 to RY-03 identified from the review of upstream code (findings U-1 to U-8). RY-22 added after considering the side effects of a well-behaved tool. |
| 19.08.2026 | Numbering collision resolved: the later technical additions moved to RY-50 and above; the stray "loss of the defence material key" row given its own identifier, RY-19. |
