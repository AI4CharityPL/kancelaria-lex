# ADR-0004. Embedder: multilingual-e5-base instead of all-MiniLM-L6-v2

**Status:** accepted, 14.08.2026. Review after M2.

## Context

The default embedder in OpenContracts is `all-MiniLM-L6-v2`: 384 dimensions, trained on an English corpus (finding U-7).

Retrieval is the system's foundational operation, because the agent answers only from the fragments it finds. **Bad retrieval ruins everything above it.** The best language model will not answer correctly from a document it never found.

An English-language model applied to Polish procedural documents, with their inflection, legal terminology and characteristic syntax, undermines the whole chain.

## Decision

**`multilingual-e5-base`, 768 dimensions.**

| Criterion | Rationale |
|---|---|
| Multilingual | Trained multilingually, clearly better on Polish |
| **768 dimensions** | Falls within the supported set of dimensions, so it needs no change to the pgvector schema |
| CPU | Runs at acceptable speed without a GPU, so it does not compete with the language model for VRAM |
| Licence | Open, without commercial restrictions |

Choosing 768 over a larger model is deliberate: it lets us swap the embedder **without migrating the database schema**, which markedly lowers the cost and risk of change in a fork.

## Alternatives considered

| Option | Assessment |
|---|---|
| `all-MiniLM-L6-v2` (default) | Rejected: English corpus, weak on Polish |
| `bge-m3` (1024 dimensions, long context) | **Candidate, deferred.** 1024 would require schema changes. Worth revisiting after measurement if e5-base proves insufficient |
| Cloud embeddings (1536 or 3072) | Contrary to the overriding requirement |

## Accompanying decision: hybrid search

Retrieval combines vector search with full-text search.

The reason is concrete: **vector search loses case reference numbers and figures**. A query for "II K 123/26" is an exact search, in which semantic similarity actively hurts, because reference numbers that are similar as vectors are usually different reference numbers. Conversely, full-text search loses paraphrase ("who testified that they saw the vehicle" against "the witness noticed the car").

Procedural documents contain both kinds of query, often within one question.

## Consequences

Positive:

- clearly better retrieval on Polish documents,
- no schema changes,
- no competition for VRAM,
- hybrid search covers both query patterns.

Negative:

- a larger embedder than the default, so indexing takes longer,
- reindexing if we ever move to `bge-m3`,
- a patch on the embedder layer at every upstream merge.

## Review

After M2, on the basis of retrieval quality measured on the gold set. If e5-base proves insufficient, `bge-m3` follows together with a schema migration, costed separately.
