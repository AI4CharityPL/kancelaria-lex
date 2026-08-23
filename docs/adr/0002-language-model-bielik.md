# ADR-0002. Language model: Bielik-11B-v3.0-Instruct

**Status:** accepted, 14.08.2026. Review after M2, once measurements from the proof of concept are in.

## Context

We need a language model that runs fully locally, copes with Polish legal terminology and the syntax of procedural documents, and carries a licence that permits commercial use.

## Decision

**Bielik-11B-v3.0-Instruct** (SpeakLeash and ACK Cyfronet AGH, January 2026), run through Ollama.

| Criterion | Assessment |
|---|---|
| Polish | Trained with an emphasis on Polish, over 20 million instructions |
| Weights licence | Apache 2.0, fully open for commercial use |
| Availability | In the Ollama library in GGUF format, several quantisation variants |
| Backing | PLGrid, ACK Cyfronet AGH: an institutional project rather than a private experiment |
| Size | 11 billion parameters, fits on a reasonable GPU |

## The quantisation condition

The model card warns explicitly that **quantised models show reduced quality and a greater tendency to hallucinate**.

| Profile | Quantisation | Data permitted |
|---|---|---|
| Development (8 GB VRAM) | Q4_K_M | **synthetic corpus only** |
| Production | Q8_0 or FP16 | real case files, after the gates |

**Q4 is not approved for real case files.** The reason is not procedural caution: in criminal defence a hallucination is an error with real consequences.

## Alternatives considered

| Option | Reason for rejection |
|---|---|
| General models (Llama, Mistral, Qwen) | Weaker on Polish legal terminology; some versions carry licences that need separate commercial analysis |
| A larger model (30B and above) | Does not fit a reasonable hardware budget at the required concurrency; worth revisiting in hardware variant C |
| Fine-tuning on the firm's case files | **Rejected on principle.** Risk of fixing personal data in the weights (GDPR, professional privilege) and of moving the firm towards the role of provider under the AI Act |
| Any cloud model | Contrary to the overriding requirement |

## Consequences

Positive:

- a good fit for Polish,
- a licence with no commercial reservations,
- installation in a single command,
- a smaller variant available for fast development loops.

Negative:

- reasoning quality below the largest commercial models, offset by construction: forced citation, mechanical verification and mandatory review by a lawyer,
- the production profile needs a GPU with at least 24 GB,
- changing the model means passing the quality gates again.

## Operating rules

1. **The weights licence is verified at every update.** MIT for the code says nothing about the weights. The Surya case (Apache 2.0 code, Open-RAIL-M weights with a commercial threshold) shows this is not a formality.
2. **Checksums of the weights live in `models/`** and are verified at startup (threat T-3).
3. **Weights are brought in as an offline package.** Nothing is downloaded during operation.
4. **A newer model is not automatically better** for Polish case files. Changes only after the full quality gates.

## Review

After M2, on the basis of real measurements: quality on the gold set, throughput, and behaviour at an 8k context. If quality proves insufficient, the alternative is a larger open model in hardware variant B or C, not a cloud model.
