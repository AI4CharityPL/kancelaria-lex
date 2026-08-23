# ADR-0001. Fork OpenContracts with our own layer on top

**Status:** accepted, 14.08.2026. Review after M6.

## Context

We need a document management system with annotations, search and a browsing interface, on top of which we can put the agent layer and the case module. Building that from scratch takes months.

OpenContracts (MIT, Django/React/PostgreSQL/Celery) provides the document core: parsing that preserves page layout, annotations, corpora, hybrid search, field extraction and a user interface.

## Options considered

| Option | Advantages | Disadvantages |
|---|---|---|
| **A. Fork with our own layer** (chosen) | Ready core; full control over changes; ability to physically cut code out | We maintain the whole base stack |
| B. Fork unchanged, configuration only | Fastest; easy merges from upstream | **Isolation rests on configuration that one entry can undo** |
| C. Greenfield | Minimal attack surface; exactly what we need | Months of work to reproduce the DMS and the interface; high risk |

## Decision

**Option A.**

Option B fell away once we read the code. Findings U-1 and U-2 showed that the guarantee proposed in the source report ("do not set API keys") does not hold: with Ollama the key is substituted automatically, and credentials can live in the database under a rule where the database wins over the environment variable. Configuration is not a security boundary here.

Option C fell away on cost and risk, not on principle.

The scope of upstream modification is deliberately narrow: removing cloud SDKs, MCP and telemetry, the address guard, changing the embedder, and TLS without ACME. Everything else goes into our own Django applications (`sprawy`, `agenci`, `audyt`, `dostep`, `anonimizacja`), which do not collide with upstream during merges.

## Consequences

Positive:

- a ready document core,
- the ability to remove code rather than merely disable it,
- our own applications are immune to merge conflicts.

Negative:

- we take on responsibility for the security of the entire base stack,
- several to a dozen hours a month of maintenance,
- the risk that a merge quietly reverts our changes.

**Mitigation for the last point.** A CI gate on the lockfile: the build fails if `anthropic`, `google-genai`, `posthog` or `mcp` return. Without it, the most likely failure mode of this project is a merge six months from now that nobody notices.

## Condition for keeping this decision

**Assured maintenance after deployment is a condition of going to production.** A fork without a maintainer becomes a liability for a law firm rather than a saving. If maintenance turns out to cost markedly more than assumed, this decision is revisited at M6.
