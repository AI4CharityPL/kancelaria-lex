# ADR-0006. Mechanical citation verification instead of an LLM judge

**Status:** accepted, 14.08.2026.

## Context

A language model analysing criminal case files can produce a statement that sounds credible but has no basis in the documents. In a law firm the result is a wrong reading of the case, and in criminal defence the harm is often irreversible.

The risk is higher in the development profile: the Bielik model card warns explicitly that **quantisation lowers quality and increases the tendency to hallucinate**, and 8 GB of VRAM forces Q4.

## Options considered

| Option | Assessment |
|---|---|
| **A. Mechanical span verification** (chosen) | Deterministic, cheap, catches a fabricated citation with certainty |
| B. An LLM judge rating faithfulness | Prone to the same errors as the model it judges; **lets hallucinations through**, especially confidently phrased ones |
| C. Human review alone | Sound, but does not scale and cannot act as an automatic gate |
| D. No verification | Unacceptable in this application |

## Decision

**Option A as the automatic gate, option C as a mandatory step in the workflow.**

Every statement in an answer carries a document identifier and a character range. The code takes that range from the source and compares the text **character by character**. Statements without coverage are rejected before the lawyer sees them. Rejected statements go to the log as a measure of model quality over time.

The LLM judge was **deliberately rejected**. A model rating the faithfulness of an answer shares the weaknesses of the model being rated, and tends to be lenient exactly where the risk is greatest, namely with a confidently phrased answer. String comparison does not have that flaw: the fragment either exists and matches, or it does not.

## The limit of this method

**Verification confirms that the citation comes from the source. It does not confirm that the conclusion drawn from it is sound.**

The model can quote a record correctly and misread its meaning. No mechanical method catches that.

Hence:

- the project goal reads "verifiable answers", not "certain answers" (C3),
- review by a lawyer stays **mandatory**, not recommended,
- risk R-4 in the DPIA stays at medium, deliberately and openly,
- the interface must communicate the status of a working tool, not just the terms of use.

## Consequences

Positive:

- a fabricated citation does not get through,
- gate J-1 at 99% is attainable, because it measures a binary property,
- rejections are a measurable indicator of model quality,
- no dependency on a second model.

Negative:

- the model has to return structured citations, which constrains the format,
- at an 8k context retrieval has to be frugal,
- the method does not protect against misinterpretation.

## Related

Implementation: `src/aplikacje/agenci/weryfikator_cytatow.py`. Gate: J-1 in [`../testing-and-gates.md`](../testing-and-gates.md). Risk: R-4 in [`../compliance/gdpr-dpia.md`](../compliance/gdpr-dpia.md).
