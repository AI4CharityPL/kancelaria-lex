# ADR-0005. Procedural deadlines computed deterministically

**Status:** accepted, 14.08.2026.

## Context

Keeping track of procedural deadlines is one of the most valuable uses of the system, and at the same time the most dangerous.

A missed deadline means losing the right of appeal: harm to the client, usually irreversible, and professional liability for the lawyer. It is the only area of this system where an error has direct, measurable legal consequences.

## Options considered

| Option | Assessment |
|---|---|
| **A. The model recognises the event, the code computes the deadline** (chosen) | Plays to the strengths of each; the arithmetic is testable and auditable |
| B. The model recognises and computes | A probabilistic model performing arithmetic with legal consequences, which is unacceptable |
| C. Everything by hand | Safe, but then the system adds no value here |

## Decision

**Option A, that is, a split of responsibility.**

```
  MODEL          recognises the triggering event and quotes the source
                 ("the judgment with reasons was served on 12.08.2026")
                 a language task the model is suited to
     |
     v
  RULE ENGINE    legal basis, length, counting method, non-working days
                 arithmetic: code, testable, auditable
     |
     v
  LAWYER         confirms. Without confirmation the deadline is not binding.
```

## Details

**The rules are data, not code** (`reguly_terminow.yaml`). A lawyer has to be able to review them without reading Python. That is the condition for anyone in the firm taking responsibility for them.

**Every rule requires approval** by a lawyer, with a signature and date in the file. An unapproved rule runs in "proposal with a warning" mode only.

**Every deadline carries its legal basis and a quotation** from the triggering event. The lawyer sees where the deadline came from and can check it in the document.

**The warning for an unconfirmed deadline is louder** than for a confirmed one, because an unrecognised deadline is more dangerous than a known one.

## Consequences

Positive:

- deadline arithmetic is unit-testable,
- a change in the law is a change of data, not of code,
- the rules are open to legal review,
- risk R-5 is brought down to low,
- a full audit trail: what, on what basis, and from which document.

Negative:

- the rule catalogue has to be built and maintained,
- amendments to the law require review,
- the model can miss a triggering event, hence gate J-8 at 90% and loud warnings about unprocessed documents.

## Boundary of responsibility

The system **supports** keeping the deadline diary. **It does not release the lawyer from the duty to check the deadline in the case file.**

That has to be communicated in the interface, not only in the terms of use. A tool the user trusts unconditionally removes the vigilance they had before.

## Related

Agent A-2 in [`../agents.md`](../agents.md). Domain model in [`../case-domain-model.md`](../case-domain-model.md). Risk R-5 in [`../compliance/gdpr-dpia.md`](../compliance/gdpr-dpia.md). Gate J-8.
