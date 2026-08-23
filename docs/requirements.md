# Requirements

Priorities follow MoSCoW: **M** must have (without it the project has no point), **S** should have, **C** could have, **W** outside this phase.

## Functional requirements

### Document flow

| ID | Requirement | Prio |
|---|---|---|
| F-01 | Upload a document into a case (PDF, DOCX, TXT, images, legacy formats through conversion) | M |
| F-02 | OCR of Polish-language scans, preserving page layout | M |
| F-03 | The OCR result can be previewed and corrected by hand before indexing | M |
| F-04 | Automatic classification of document type (indictment, court order, judgment, record, expert opinion, procedural letter) | S |
| F-05 | Metadata extraction: case reference, authority, parties, dates, date of service | M |
| F-06 | Document versioning and change history | S |

### Working with the file

| ID | Requirement | Prio |
|---|---|---|
| F-10 | A natural-language question about the case file, answered **always with citations** | M |
| F-11 | Every citation leads to a specific place in a document (document plus character range) | M |
| F-12 | Refusal to answer when the file gives no basis, in place of a plausible answer | M |
| F-13 | A chronology of case events built from the documents | S |
| F-14 | Detection of discrepancies between accounts (witness statements, explanations) | S |
| F-15 | Combined search: semantic and full-text | M |
| F-16 | Bulk extraction of a single field across many documents at once | C |

### Cases and deadlines

| ID | Requirement | Prio |
|---|---|---|
| F-20 | Case register: reference, authority, stage, parties, lawyer in charge | M |
| F-21 | **Procedural deadlines computed deterministically** from the triggering event | M |
| F-22 | The model may *propose* the triggering event; the deadline is computed by code, not by the model | M |
| F-23 | Every deadline needs a lawyer's confirmation before it counts as binding | M |
| F-24 | A calendar of deadlines and hearings with advance warnings | M |
| F-25 | Recognition of Polish case reference patterns (`II K 123/26`, `III Kp 45/26`, `PO I Ds 12.2026`) | S |
| F-26 | A draft letter from a template, always for the lawyer to edit | C |

### Confidentiality and access

| ID | Requirement | Prio |
|---|---|---|
| F-30 | Access to a case granted by name, on a need-to-know basis | M |
| F-31 | **Defence material in a separate store with its own key** | M |
| F-32 | Ethical walls: access blocked where there is a conflict of interest | M |
| F-33 | Audit log: who, when, which document, what operation | M |
| F-34 | The audit log resists tampering (a chain of checksums) | M |
| F-35 | Pseudonymisation before any export out of the system | S |
| F-36 | Multi-factor authentication | M |

## Non-functional requirements

### Isolation: the decisive requirements

| ID | Requirement | Verification |
|---|---|---|
| N-01 | No container opens a connection outside its segment | `tests/izolacja/`: DNS and TCP fail for every container |
| N-02 | A full document run generates no outgoing traffic | Capture on the host bridge, asserting zero packets |
| N-03 | The production image contains no cloud provider SDKs | Lockfile scan in CI; the build fails on detection |
| N-04 | No MCP server | `GET /mcp/` returns 404 |
| N-05 | A model address outside the allowlist stops the process from starting | Startup test with a substituted variable |
| N-06 | Writing an address outside the allowlist to the database is rejected and logged | Integration test on `PipelineSettings` |
| N-07 | No telemetry in the image | `posthog` absent from the lockfile |
| N-08 | Every image pinned by `sha256` | Compose scan in CI |

### Answer quality

| ID | Requirement | Threshold |
|---|---|---|
| N-10 | Citation accuracy (the citation exists and the text matches), checked mechanically | ≥ 99% |
| N-11 | Substantive correctness on the gold set, judged by a human | ≥ 85% |
| N-12 | Correct refusal when a question has no basis in the file | ≥ 90% |
| N-13 | Resistance to instruction injection in document content | 100%, zero instructions executed |
| N-14 | OCR character error rate on good-quality scans | ≤ 2% |
| N-15 | OCR character error rate on poor photocopies | ≤ 10%, flagged for manual review |

Thresholds N-10 to N-15 are **gates**: until they are met, the system does not touch real case files.

### The rest

| ID | Requirement | Value |
|---|---|---|
| N-20 | Agent response to a question about the file | under 60 s (development profile), under 20 s (production) |
| N-21 | OCR of one page | under 3 s (Tesseract), under 10 s (RapidOCR) |
| N-22 | Encryption at rest | full disk encryption plus a key for each case |
| N-23 | Restore from backup | RPO ≤ 24 h, RTO ≤ 8 h, restore tested quarterly |
| N-24 | Polish-language interface | full localisation |
| N-25 | Retention in line with the rules on keeping case files | configurable, ten years by default |

## Outside this phase (W)

Billing and invoicing, integration with the courts' information portal, qualified electronic signatures, e-delivery, a mobile application, multi-office operation with replication, an external penetration test, migration of historical data.
