# Roadmap

## Two parallel tracks

The compliance track **does not wait** for the technical one. The KSC registration deadline runs regardless of whether the system is ever built.

```
  COMPLIANCE  K-1 assessment --> K-2 registration --> K-3 contracts --> K-4 training
              15.09               02.10                31.10             31.12
              ------------------------------------------------------------------>

  TECHNICAL   P0 --> P1-2 --> P3-4 --> P5 --> P6 --> P7 --> P8 --> pilot
              docs   isolation  AI PoC  cases  compl. gates  E2E
              ------------------------------------------------------------------>
```

## Compliance track: externally fixed dates

| # | Task | Deadline | Owner |
|---|---|---|---|
| K-1 | KSC scope assessment | 15.09.2026 | lawyer and partners |
| **K-2** | **Registration, if in scope** | **02.10.2026** | partners |
| K-3 | Review of contracts for supply chain requirements | 31.10.2026 | lawyer |
| K-4 | Management training (KSC and AI Act art. 4) | 31.12.2026 | partners |
| K-6 | The boundary of an incident report | before the pilot | lawyer |
| P-2 | DPIA approval | before the pilot | controller and DPO |
| K-5 | Art. 21 measures implemented | 02.04.2027 | team |

**K-1 and K-2 start now.** They need not a single line of code.

## Technical track

| Phase | Scope | State | Output |
|---|---|---|---|
| **0** | Documentation, decisions, structure | done | Complete `docs/`, the ADRs |
| **1** | Cutting the cloud paths out of the build | in progress | Patches and the CI gate |
| **2** | Network segmentation, supply chain | in progress | Compose with four networks, isolation tests |
| **3** | The local AI stack | in progress | Bielik, Polish embedder, OCR, measurements |
| **4** | The agent layer | in progress | Citation verifier, question agent |
| **5** | The case module | to do | Domain model, deadline engine |
| **6** | Security and audit | to do | Checksum-chained log, defence store, ethical walls |
| **7** | Evaluation | to do | Gold set, gate results |
| **8** | End-to-end offline | to do | Packet capture, proof O-1 |
| **9** | Pilot | to do | Selected cases, a narrow group of users |

### The order is not accidental

Phases 1 and 2 come **before** the AI stack, even though the model is the more attractive thing to build. The reason: running the model in an environment without isolation creates working habits that are hard to undo afterwards, and isolation tests written after the fact tend to check what already works rather than what ought to be blocked.

Phase 6 (security) precedes phase 7 (evaluation), because evaluating a system with no audit log leaves no trace that could later be presented.

## Milestones

| Milestone | Criterion, executable rather than descriptive |
|---|---|
| **M1, isolation proven** | `pytest tests/izolacja/` green; the negative test confirms the tests can fail |
| **M2, the AI stack works** | A document from the synthetic corpus: OCR, index, an answer with citations |
| **M3, citations verifiable** | The verifier rejects a fabricated citation in a test |
| **M4, deterministic deadlines** | The rule engine passes its tests; a model proposal requires confirmation |
| **M5, confidentiality in place** | Defence material unreadable in a dump of the main database (O-4) |
| **M6, quality gates** | J-1 to J-8 passed **on the production profile** |
| **M7, the final proof** | Packet capture: zero outgoing packets (O-1) |
| **M8, admission** | The full list of conditions from the DPIA ticked off |

**Only M8 opens the way to real case files.**

## Decision points

| When | Decision | Basis |
|---|---|---|
| After M2 | Is Bielik's quality sufficient? | Measurements from the proof of concept; the alternative is another open model |
| After M2 | Is `multilingual-e5-base` sufficient? | Retrieval quality; the alternative is `bge-m3` with a schema change |
| After M6 | Choice of hardware variant | Real throughput measurements rather than estimates |
| After M6 | Does the fork hold up? | Maintenance cost in practice against the assumptions in ADR-0001 |
| Before M8 | Scope of the pilot | Which cases, how many lawyers |

The fourth point is meant honestly: if maintaining the fork turns out to cost markedly more than assumed, ADR-0001 is open to revision. An architectural decision is not irreversible. Only a data leak is.

## Schedule risks

| Risk | Response |
|---|---|
| The K-2 deadline collides with technical work | The tracks are separate; K-1 and K-2 need no technical staff |
| Quality gates fail on Q4 | Expected; the gates are measured on the production profile |
| Upstream has changed relative to findings U-1 to U-8 | Verification before forking is a mandatory step, not a formality |
| Approving the deadline rules lands on the critical path | It needs a lawyer's time, so plan it early; it is not an engineering task |
| No assured maintenance after deployment | **A condition of going to production**, not a question to settle later |
