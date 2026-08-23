# Context and goals

## The problem

The firm conducts cases in which the evidence and the procedural correspondence are covered by legal professional privilege. Some of them are non-public criminal proceedings. The files contain data under art. 9 GDPR (health, sex life, opinions among others) and art. 10 GDPR (convictions and offences), together with material covered by defence privilege, which not even a court can lift.

At the same time the volume of case files grows faster than lawyers' time. A typical criminal case runs to hundreds of pages: indictments, records of examination, expert opinions, court orders. Building a chronology by hand, hunting for contradictions between statements and keeping track of procedural deadlines can be partly automated, but only with a tool that never lets the content of a file leave the firm.

## The hard requirement

**Zero connectivity to external model providers.** The whole chain (OCR, parsing, embedding, answer generation) runs on the firm's own hardware, on models downloaded once and executed locally.

This is not an architectural preference but a condition of compliance with professional privilege. Sending a fragment of a case file to an external API constitutes disclosure of privileged information, whatever assurances the supplier gives in its terms.

**A standalone instance.** The system cannot be attached to ChatGPT, Claude Code or any external agent client. The fork removes the MCP server: it does not disable it through configuration, it removes it from the routing and from the dependencies.

## Goals

| # | Goal | Measure of success |
|---|---|---|
| C1 | Case files do not leave the firm's infrastructure | Zero outgoing packets in a capture during a full document run |
| C2 | Less time needed to get across a case file | Time to a first usable case chronology below 15 minutes from upload |
| C3 | Answers that are verifiable rather than merely plausible | Every statement points to an existing fragment of the source, checked mechanically |
| C4 | No procedural deadline missed through the system's fault | Deadlines are computed by a deterministic engine; the model never calculates them |
| C5 | Demonstrable compliance with the GDPR and art. 21 of the Polish KSC act | Complete documentation and a tamper-resistant audit log |

## What this system does not do

Bounding the scope is part of the specification:

- **It does not give legal advice.** It produces working material for a lawyer. Every analysis needs review by someone professionally accountable.
- **It does not replace checking a deadline in the file.** It proposes a deadline and shows the basis; the lawyer confirms it.
- **It is not a billing or invoicing system.** Out of scope for this phase.
- **It does not classify conduct legally.**

## Users

| Role | What they do in the system |
|---|---|
| Advocate or legal counsel conducting the case | Asks questions of the file, reviews the chronology, confirms deadlines |
| Trainee or assistant | Uploads documents, checks the OCR output, describes metadata |
| Firm administrator | Grants access, keeps the case register, watches the ethical walls |
| Data protection officer | Reads the audit log, keeps the record of processing, handles incidents |

## Assumptions and limitations accepted deliberately

1. **A local model is weaker than the best commercial ones.** We accept that as the price of confidentiality. We compensate for the weakness by construction: forced citation and mechanical coverage checks buy more here than swapping in a stronger model would.
2. **Local OCR is weaker on photocopies and handwriting.** Manual review of a sample and a measured character error rate act as a gate.
3. **Being cut off from the network makes patching harder.** It calls for a deliberate update procedure instead of automation; see [`operations/offline-updates.md`](operations/offline-updates.md).
4. **Maintaining a fork of a large Django application costs real effort.** Decision and reasoning: [`adr/0001-fork-opencontracts-with-own-layer.md`](adr/0001-fork-opencontracts-with-own-layer.md).

## Source document

The project starts from an internal report dated 13.08.2026, prepared before work began. Its direction is preserved. Reading the OpenContracts source, however, showed that the guarantee mechanism described there is insufficient; the corrections are gathered in [`isolation-and-network.md`](isolation-and-network.md).

> The report itself does not go into the public repository. It was a private document, prepared for a specific person, and it carries nothing that is not in this documentation. All of its findings have been carried over into these documents.
