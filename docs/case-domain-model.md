# Domain model: cases

> **Disclaimer.** This document describes the data model and how the system behaves. All procedural rules, deadlines above all, need **approval by the firm's lawyer** before deployment and review whenever the law is amended. The author of this document is not a source of law; the statutes are, together with verification by someone professionally accountable.

## Data model

```
  Case --1:1-- Corpus (the fork's document set)
    |
    +-- CaseReference   (several; a case travels between instances and authorities)
    +-- Authority       (court, prosecutor's office, other)
    +-- Party           (procedural role, details, representative)
    +-- Stage           (pre-trial, first instance, appeal, and so on)
    +-- Deadline        (procedural, with its basis and triggering event)
    +-- Hearing         (date, courtroom, attendance)
    +-- LeadLawyer      (assigned by name)
    +-- ConfidentialityMarking (level, and whether it is defence material)
```

### Case

| Field | Notes |
|---|---|
| `rodzaj` | criminal, civil, commercial, administrative, family |
| `tryb` | for criminal cases: public prosecution, private prosecution, expedited |
| `stan` | active, suspended, closed, archived |
| `poziom_poufnosci` | standard, raised, **defence material** |
| `data_wszczecia`, `data_zakonczenia` | |
| `prowadzacy` | by name, required |

### Case reference

A case usually has **several references**: one at the prosecutor's office, another at the court of first instance, another on appeal. This is a common modelling mistake: the reference is not an attribute of the case but a separate entity tied to an authority and a stage.

Patterns recognised (to be approved and extended by a lawyer):

| Pattern | Example | Context |
|---|---|---|
| `<roman> K <no>/<year>` | `II K 123/26` | district court, criminal case |
| `<roman> Ka <no>/<year>` | `IV Ka 45/26` | regional court, criminal appeal |
| `<roman> Kp <no>/<year>` | `III Kp 12/26` | pre-trial proceedings, judicial review |
| `<roman> C <no>/<year>` | `I C 890/26` | civil |
| `Ds` and `PO … Ds` | `PO I Ds 12.2026` | prosecutor's office |

Validation is done **by pattern, not by the model**, because a case reference is structured data rather than a language task. The model may point at a candidate in the text; the pattern decides whether it is correct.

## Procedural deadlines

### Division of responsibility

```
  MODEL           recognises the triggering event in the document, with a quote
     |            (a language task the model is suited to)
     v
  RULE ENGINE     computes the deadline: basis, length, counting method,
     |            public holidays
     |            (arithmetic: code, testable, auditable)
     v
  LAWYER          confirms. Without confirmation the deadline is not binding.
```

### Why it is arranged this way

A missed procedural deadline means losing the right of appeal: harm to the client, usually irreversible, and professional liability for the lawyer. A probabilistic model is not the right tool for arithmetic whose result carries that consequence.

The division plays to the strengths of each. The model reads the sentence *"the judgment with reasons was served on 12 August 2026"* and recognises the event. The code computes the deadline and checks the holidays. The lawyer confirms.

### Structure of a rule

The rules are **data** (`src/aplikacje/sprawy/reguly_terminow.yaml`), not code, so a lawyer can review them without reading Python.

```yaml
- id: apelacja_karna
  zdarzenie: doreczenie_wyroku_z_uzasadnieniem
  dlugosc_dni: 14
  liczenie: od_dnia_nastepnego
  dni_wolne: przesun_na_nastepny_roboczy
  podstawa: "art. 445 § 1 k.p.k."
  wymaga_potwierdzenia: true
  uwaga: "Zatwierdzone przez: ______  data: ______"
```

Every rule needs its approval field filled in before deployment. An unapproved rule runs in "proposal with a warning" mode only.

The starting catalogue covers the most common criminal and civil deadlines, among them interlocutory appeals, appeals, requests for written reasons, and objections to a payment order. **The catalogue is a draft for verification, not a source of law**; the full list and the exact wording of the legal bases are subject to approval by a lawyer in Phase 5.

### Warnings

Deadlines are signalled repeatedly in advance, at shrinking intervals. The warning for an unconfirmed deadline is **louder** than for a confirmed one, because an unrecognised deadline is more dangerous than a known one.

## Confidentiality in the domain model

### Defence material lives in a separate store

Defence privilege (art. 178 pt 1 of the Polish Code of Criminal Procedure) is different in kind from advocate privilege. The latter a court may lift under art. 180 § 2; the former it may not.

**The technical consequence: defence material cannot be an ordinary record with a flag.** A flag can be changed with a SQL query. Defence material goes into:

- a separate object store,
- encrypted with **its own key**, unavailable to the process serving the other cases,
- behind separate authorisation.

The practical effect is that a dump of the main database, whether from a failure, a backup or a seizure, **does not contain defence material in readable form**.

### Ethical walls

Access is blocked where there is a conflict of interest, at the level of the permission layer: a register of connections between cases and people, a check when access is granted, a warning when a lead lawyer is assigned, and an audit entry whenever a wall is breached, which is possible only by decision of the administrator, with a justification.

### Audit trail

An append-only log with a chain of checksums, held outside the application database. It records who, when, which document or case, what operation, and from which address.

It has to be able to answer the question "who had sight of the file in case X". In a dispute over professional privilege that is the evidence of due diligence. A log open to modification is not evidence.

## Retention

Ten years by default, configurable. The tension is set out in [`compliance/gdpr-register-and-art32.md`](compliance/gdpr-register-and-art32.md): the right to erasure (art. 17 GDPR) against the obligation to retain case files and professional privilege. In practice the retention obligation usually prevails (art. 17(3)(b) and (e) GDPR), but **each case needs assessment**, so the system has to be able to place a legal hold rather than only delete once the period expires.
