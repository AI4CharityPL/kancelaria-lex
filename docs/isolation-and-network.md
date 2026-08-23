# Isolation: three layers of guarantee

This is the decisive document for the whole project. Everything else can be corrected after deployment; a leak of criminal case files cannot.

## The claim

**Isolation based on configuration is not isolation.** Configuration can be undone with one entry, deliberately, by mistake, or during a merge from upstream. The source report proposed a guarantee resting on the absence of API keys in `.env`. Reading the code showed that this guarantee does not hold (findings U-1 and U-2 below).

In its place, three layers, **each of which works on its own** when the other two fail:

| | Layer | Mechanism | What it prevents |
|---|---|---|---|
| **A** | Build | The cloud providers' code is not in the image | A call that cannot be written |
| **B** | Process | The model address must be on an allowlist, or the process does not start | Configuration changed by error or intent |
| **C** | Network | `internal: true` segments, with no route to the gateway | Everything above, should it fail |

## Findings from reading the OpenContracts code

Reviewed against `main` as at 14.08.2026. **Repeat this before forking**, because upstream changes.

### U-1. Ollama runs through the OpenAI client

`model_factory` supports the providers `openai`, `ollama`, `anthropic` and `google-gla`. **Ollama is routed through `OpenAIProvider`**, because it exposes an OpenAI-compatible API. The code comments explicitly that the OpenAI client needs *some* key even when the server ignores it, and **substitutes a dummy value `"ollama"`** when none is present.

> **Consequence:** the claim that "without a key those paths are unavailable" is false for the local path, because the key is substituted automatically. What is more, the `openai` package **has to stay** in the image, because the local model will not work without it. The point of control is therefore not the key but **the address**.

### U-2. Credentials can live in the database

`PipelineSettings` stores `api_key` and `base_url` in the database, under a rule where **the database wins and the environment variable is the fallback**.

> **Consequence:** a clean `.env` guarantees nothing. Someone with access to the admin panel can enter a cloud provider's key and an external `base_url` straight into the database without touching a file. What is needed is a block at the point of writing to the model, not only validation of variables.

### U-3. The cloud SDKs and MCP are hard dependencies

In `requirements/base.txt`:
```
openai>=2.52.0,<3
pydantic-ai-slim[openai,anthropic,google,mcp]>=1.107.1,<2
posthog==7.35.4
mcp>=1.28.1,<2
```

> **Consequence:** the Anthropic and Google SDKs, the telemetry library and the MCP server all land in the production image. Disabling them through configuration leaves live, importable code behind.

### U-4. No compose file defines any network

Neither `local.yml` nor `production.yml` contains a `networks` section. Every service lands on the default bridge, which **has a route to the internet**.

> **Consequence:** "restricting egress at the Docker network level", as the report put it, is not a switch to flip. The topology has to be written from scratch.

### U-5. Images tagged `latest` from private namespaces

`jscrudato/docsling-local`, `jscrudato/vector-embedder-microservice`, `ghcr.io/jsv4/vectorembeddermicroservice:latest`, `ghcr.io/open-source-legal/privacy-filter:latest`.

> **Consequence:** unacceptable with criminal case files. `latest` means the contents of an image can change between one `pull` and the next, leaving no trace in the repository.

### U-6. Traefik uses ACME

Certificates through Let's Encrypt, with a `production_traefik` volume for the ACME data.

> **Consequence:** ACME **requires an outbound connection by definition**, along with a publicly resolvable domain. In a closed environment it cannot work at all. The report did not catch this.

### U-7. The default embedder is English-language

`all-MiniLM-L6-v2`, 384 dimensions, trained on an English corpus.

> **Consequence:** a question of quality rather than security, but a significant one, because retrieval on Polish procedural documents will be poor. Replaced by `multilingual-e5-base` (768 dimensions).

### U-8. Port 5555 is exposed

The Celery and flower panel, in both compose files.

> **Consequence:** it reveals task names and their arguments, and therefore document and case identifiers. Metadata is covered by privilege too.

## Layer A: the build

The aim: **code that is not in the image cannot make a connection.**

### Dependency changes

| Package | Action | Reasoning |
|---|---|---|
| `pydantic-ai-slim[openai,anthropic,google,mcp]` | becomes `pydantic-ai-slim[openai]` | We drop the `anthropic`, `google` and `mcp` extras. **The `openai` extra stays**, per U-1. |
| `openai` | **stays** | The transport to local Ollama. Removing it would break the local model. |
| `posthog==7.35.4` | removed | Telemetry, I-3 |
| `mcp>=1.28.1` | removed | The standalone-instance requirement, I-4 |

### Code changes

- Remove the `/mcp/` routing from `urls.py`; a test checks that `GET /mcp/` returns 404.
- Remove the `anthropic` and `google-gla` provider branches from `model_factory`. Not disabled but deleted, so that the import is impossible.
- Traefik: the ACME configuration is replaced by certificates from our own CA (`infra/ca/`).

### The CI gate, the most important part of this layer

The build **fails** if any of `anthropic`, `google-genai`, `google-generativeai`, `posthog` or `mcp` appears in the lockfile.

This guards against the most likely failure mode of the project: **six months from now somebody merges from upstream and quietly restores the extras.** Without the gate nobody notices until it is too late. With it, the build fails the same day.

Implementation: `tests/izolacja/test_czystosc_builda.py`.

## Layer B: the process

The aim: **a process with an incorrect model address must not start.**

### The address allowlist

The only permitted base addresses:
```
http://ollama:11434/v1        # language model
http://embedder:8000          # embeddings
```

### The startup guard

In `AppConfig.ready()` of the `agenci` application, every configured `base_url`, whether from an environment variable or from the database, is compared against the allowlist. An address outside the list raises `ImproperlyConfigured` and **the process does not start**.

A hard stop was chosen deliberately over a warning in the log. A system that keeps running on a bad configuration and logs a warning will keep running, because nobody reads warnings.

### The database write block (answering U-2)

A `pre_save` signal on `PipelineSettings`:
- an address outside the allowlist raises an exception and the write is rejected,
- the attempt itself produces an audit log entry identifying the user,
- setting a non-empty `api_key` for any provider other than the local one is rejected.

This closes the path that a clean `.env` leaves open.

### Weight checksum verification

At startup the checksums of the model weights are compared with the manifest in `models/`. A mismatch stops the process (T-3).

## Layer C: the network

The aim: **even a correctly formed request has no way out.**

### Topology (answering U-4)

| Segment | `internal` | Services | Reasoning |
|---|---|---|---|
| `net_edge` | no | traefik, frontend | The only point of contact with the firm's LAN |
| `net_app` | **yes** | django, celery (2), postgres, redis, minio, flower | The application core and the data |
| `net_ai` | **yes** | ollama, embedder | The models, U-1 |
| `net_parse` | **yes** | docling, gotenberg, docxodus, privacy_filter | The parsers, I-2 |

`internal: true` makes Docker **create no route to the gateway**. A container in such a segment will not reach the outside even with working DNS and a correct application configuration.

`net_parse` is separate from `net_app` because of I-2: LibreOffice inside gotenberg may try to fetch resources embedded in the file it is converting. A letter from the opposing party with a linked image then becomes a read receipt at an address they control. Application-level control is unreliable here; there simply is no route.

Port 5555 comes off the exposed list (U-8).

### Supply chain (answering U-5)

- Every image pinned by `sha256` rather than by tag.
- A local registry mirror; the target environment pulls nothing from the internet.
- An SBOM (CycloneDX) generated at build time and stored with the release.
- Review and checksum verification before the package enters the closed zone; see [`operations/offline-updates.md`](operations/offline-updates.md).

### Container hardening

No root, a read-only rootfs wherever possible, seccomp profiles, no access to the Docker socket, resource limits (D-1), and `no-new-privileges`.

## Proof, not assertion

Isolation is tested rather than described. `tests/izolacja/` checks, for **every** container:

1. **DNS does not resolve** external names.
2. **TCP does not connect** outwards (by raw IP address, bypassing DNS).
3. **A DNS canary**: a unique name whose query never appears in the sinkhole.
4. **`GET /mcp/` returns 404.**
5. **The lockfile is clean** of the forbidden packages.
6. **The guard works**: a substituted `base_url` blocks startup, and a write to the database is rejected and logged.
7. **A packet capture** on the host bridge during a full document run gives **zero outgoing packets**.

Point 7 is the final proof: it does not inspect configuration, it observes reality.

## What lies beyond the reach of these layers

An honest closing note: the three layers protect against a leak **through the system**. They do not protect against someone with legitimate access copying files onto a USB stick, nor against physical seizure of the server. Those risks are addressed by access control to the room, disk encryption, the audit log and professional obligations; see [`threat-model.md`](threat-model.md), residual risks.
