# Documentation

> **Language.** This documentation is in English so the project can be evaluated
> from outside. **The application itself is Polish**: the interface, the case
> material, the code comments and the identifiers. That is deliberate. It is a
> product for Polish advocates and legal counsel, working on Polish case files
> under Polish procedure. Names such as `panel/wyszukiwarka.py`,
> `reguly_terminow.yaml` and `szukaj_w_sprawie` therefore stay as they are.

## Start here

| Document | What it answers |
|---|---|
| [Context and goals](context-and-goals.md) | Why this exists, for whom, and what it deliberately does not do |
| [Requirements](requirements.md) | The full list, prioritised, with verification for each |
| [Architecture](architecture.md) | What connects to what, and how it differs from upstream |
| [Measured results](measured-results.md) | The numbers, including the unflattering ones |

## The core argument

Two properties carry the whole project. Everything else rests on them.

| Document | Property |
|---|---|
| [Isolation and network](isolation-and-network.md) | **Nothing leaves the device.** Three independent layers, and the findings from reading the upstream code |
| [ADR-0007, citation by sentence number](adr/0007-citation-by-sentence-number.md) | **A fabricated citation is inexpressible**, not merely detectable |
| [Threat model](threat-model.md) | STRIDE, plus instruction injection through a document, which has a motivated adversary here |
| [Testing and gates](testing-and-gates.md) | How each of the above is proven rather than asserted |

## Building the system

| Document | Subject |
|---|---|
| [The AI stack](ai-stack.md) | Models, embeddings, OCR, and the quantisation profiles |
| [Agents](agents.md) | The agent catalogue, the tool allowlist, red team tests |
| [Case domain model](case-domain-model.md) | Cases, references, deadlines, confidentiality |
| [The panel](panel.md) | What is running today, and what it still lacks |
| [Bilingual documents](bilingual-documents.md) | Language detection and engine selection |
| [Document loading and OCR](document-loading-and-ocr.md) | Measured on 173 real PDFs |
| [Hardware and costs](hardware-and-costs.md) | Three production profiles, and what not to buy |

## Planning

| Document | Subject |
|---|---|
| [Roadmap](roadmap.md) | Phases, milestones, decision points |
| [Road to product](road-to-product.md) | What separates the current state from a deployable product |
| [Risk register](risk-register.md) | Open risks, named honestly |

## Architecture decisions

Numbered in the convention used by `adr-tools`. Each records the context, the options considered, the decision and its consequences.

| ADR | Decision |
|---|---|
| [0001](adr/0001-fork-opencontracts-with-own-layer.md) | Fork OpenContracts with our own layer on top |
| [0002](adr/0002-language-model-bielik.md) | Bielik-11B-v3.0-Instruct as the language model |
| [0003](adr/0003-three-layer-isolation.md) | Isolation in three layers instead of configuration |
| [0004](adr/0004-embedder-multilingual-e5.md) | multilingual-e5-base as the embedder |
| [0005](adr/0005-deterministic-procedural-deadlines.md) | Procedural deadlines computed deterministically |
| [0006](adr/0006-mechanical-citation-verification.md) | Mechanical citation verification instead of an LLM judge |
| [0007](adr/0007-citation-by-sentence-number.md) | Citation by sentence number with a decoding grammar |

## Compliance

| Document | Subject |
|---|---|
| [Legal professional privilege](compliance/legal-professional-privilege.md) | Why this matters more than the GDPR here |
| [GDPR: DPIA](compliance/gdpr-dpia.md) | The impact assessment, with risks and conditions of admission |
| [GDPR: record and art. 32](compliance/gdpr-register-and-art32.md) | The processing record and the technical measures |
| [NIS2 and the Polish KSC act](compliance/nis2-ksc-mapping.md) | Scope assessment and the mapping of art. 21 |
| [AI Act](compliance/ai-act-assessment.md) | Preliminary classification and the obligations that apply |

## Operations

| Document | Subject |
|---|---|
| [Deployment](operations/deployment.md) | Both profiles, step by step, with the verification gate |
| [Backup and recovery](operations/backup-and-recovery.md) | Targets, keys, the quarterly restore test |
| [Incident response](operations/incident-response.md) | Clocks, stages, and reporting without disclosing privilege |
| [Offline updates](operations/offline-updates.md) | Patching an environment that is cut off from the internet |

## Conventions

**Identifiers are stable and referenced from code.** `U-1` to `U-8` are findings from the upstream review, `T-1` to `T-7` are privilege requirements, `R-1` to `R-8` are DPIA risks, `RY-*` are entries in the risk register, `I-*` are isolation gates, `J-*` are quality gates, `O-*` are operational gates, `F-*` and `N-*` are requirements, `K-*`, `P-*` and `AI-*` are compliance tasks, `C1` to `C5` are project goals, and `A-1` to `A-7` are agents.

**Numbers come from measurements.** Where a document states a figure, it names where it was measured. A figure without a source is a defect in the document.
