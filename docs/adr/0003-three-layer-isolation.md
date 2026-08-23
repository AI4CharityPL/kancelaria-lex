# ADR-0003. Isolation in three layers instead of configuration

**Status:** accepted, 14.08.2026.

## Context

The source report proposed a guarantee based on configuration: do not set API keys in `.env`, point the provider at Ollama, restrict egress at the firewall.

Reading the OpenContracts code on 14.08.2026 revealed three problems:

- **U-1.** Ollama runs through `OpenAIProvider`, and the code substitutes a dummy key `"ollama"` when no key is present. The claim that "without a key the path is unavailable" is false. On top of that, the `openai` package cannot be removed, because it is the transport to the local model.
- **U-2.** Credentials can live in the database (`PipelineSettings`), under a rule where the database wins over the environment variable. A clean `.env` is not enough.
- **U-4.** No compose file defines any network. "Restricting egress at the Docker network level" is not a switch; the topology has to be written from scratch.

In addition, the Anthropic and Google SDKs, PostHog and the MCP server are hard dependencies (U-3), present in the image regardless of configuration.

## Decision

Three independent layers. **Each must work on its own when the other two fail.**

| | Layer | Mechanism |
|---|---|---|
| **A** | Build | Cloud SDKs, telemetry and MCP removed from the image. A CI gate blocks their return. |
| **B** | Process | `base_url` must belong to an allowlist, checked at startup **and on write to the database**. On violation the process refuses to start, or the write is rejected and logged. |
| **C** | Network | Four segments, three of them `internal: true`, that is with no route to the gateway. |

The point of control is **the address, not the key**. That follows directly from U-1.

## Rationale for the key choices

**Why `openai` stays while `anthropic` and `google` go.** Against the intuition in the report, removing `openai` would break the local model, because Ollama exposes an OpenAI-compatible API. Leaving the package in place creates no risk on its own; the risk is the address the client points at. `anthropic` and `google` have no local use, so they go at no cost.

**Why a hard stop rather than a warning.** A system that keeps running on a bad configuration and logs a warning will keep running, because nobody reads warnings. With criminal case files the cost of a false alarm is incomparably lower than the cost of an oversight.

**Why the block applies to database writes as well.** This is the direct answer to U-2. Without it, someone with access to the admin panel could point the model outwards without touching a single file.

**Why `net_parse` is separate from `net_app`.** LibreOffice inside gotenberg can fetch resources embedded in the file being converted. A letter from the opposing party with a linked image then becomes a read receipt at an address they control (threat I-2). Application-level control is unreliable here; only the absence of a route works.

## Consequences

Positive:

- no single failure leads to a leak,
- isolation is testable by execution,
- it produces evidence for an audit under art. 21(f) of the Polish KSC act.

Negative:

- harder merges from upstream,
- network configuration needs attention with every new service,
- a hard stop can block startup on a typo in an address.

## Verification

`tests/izolacja/` holds gates I-1 through I-9 plus a **negative test**: we must confirm that the tests can fail, by temporarily adding a route. A security test that always passes is worse than no test at all.

The final proof is a packet capture during a full document run, with the result of zero outgoing packets (O-1).
