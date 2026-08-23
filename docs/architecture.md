# Architecture

## Level 1: context

```
    +--------------+        +-------------------------------+
    |  Lawyer      |------->|                               |
    |  Trainee     |        |        kancelaria-lex         |
    |  Admin       |<-------|  (one machine, the firm's LAN,|
    |  DPO         |        |   no internet)                |
    +--------------+        +-------------------------------+
                                     ^          |
                             scans,  |          | backups
                             letters |          v (encrypted, offline)
                            +--------+---+  +--------------+
                            | Scanner /  |  | Backup       |
                            | case files |  | medium       |
                            +------------+  +--------------+

    NO outbound connections. Updates arrive only as an offline package,
    carried in by hand during a maintenance window
    (operations/offline-updates.md).
```

## Level 2: containers and network segments

```
=== net_edge (the only segment reachable from the LAN) ========================
  traefik -- own CA, mTLS, NO ACME          frontend (React, Polish UI)
==============================================================================
                                   |
=== net_app (internal: true, no route outwards) ==============================
  django          celeryworker      celerybeat       flower (not exposed)
  postgres+pgvector      redis      minio

  -- our own Django applications --
  sprawy    agenci    audyt    dostep    anonimizacja
==============================================================================
        |                                           |
=== net_ai (internal) =========    === net_parse (internal) ==================
  ollama    (Bielik-11B)            docling + tesseract + rapidocr
  embedder  (e5-base, 768)          gotenberg   docxodus
==============================      privacy_filter
                                  ============================================
```

**The rule:** only `net_edge` is reachable from the firm's network. The other three segments are `internal: true`, so Docker creates no route to the gateway for them; a container has no way out even with working DNS and a correct application configuration.

`django` is the only container belonging to more than one internal segment. It acts as the meeting point between the application, the models and the parsers.

## Level 3: our own components

```
                          +---------------------------+
    lawyer's question --->|  agenci.orkiestrator      |
                          |  (no network tools)       |
                          +-----------+---------------+
                                      | context = data only
                    +-----------------+-----------------+
                    v                 v                 v
             +------------+    +------------+    +------------+
             | retrieval  |    |  ollama    |    | domain     |
             | (pgvector  |    |  (Bielik)  |    | tools      |
             |  + FTS)    |    |            |    | (deadlines)|
             +------------+    +-----+------+    +------------+
                                     | answer + declared citations
                                     v
                      +-----------------------------+
                      | agenci.weryfikator_cytatow  |  <-- key component
                      | compares the declared span  |
                      | with the source, char by char|
                      +-------------+---------------+
                                    | uncovered statements are dropped
                                    v
                       answer for the lawyer + audit log entry
```

### Our own applications

| Application | Responsibility |
|---|---|
| `sprawy` | Domain model: case, reference number, authority, party, stage, deadline, hearing. Links to the fork's document set (`Corpus`). |
| `agenci` | Agent orchestration, the tool catalogue (an allowlist), the citation verifier, the deterministic deadline engine. |
| `audyt` | An append-only log with a chain of checksums, held outside the application database. |
| `dostep` | Named permissions, ethical walls, separate keying for defence material. |
| `anonimizacja` | Pseudonymisation before export and before using material in evaluation. |

## Key differences from upstream (OpenContracts)

| Area | Upstream | Here | Reason |
|---|---|---|---|
| Networks | none defined, default bridge | 4 segments, 3 of them `internal` | egress has to be cut at the routing level |
| Cloud SDKs | `anthropic`, `google` as `pydantic-ai-slim` extras | removed from the build | code that is not there cannot call out |
| `openai` | base dependency | **stays** | it is the transport to Ollama; see below |
| MCP server | `/mcp/` active | removed from routing and dependencies | the standalone-instance requirement |
| Telemetry | `posthog==7.35.4` | removed from the build | metadata leak |
| TLS | Traefik with ACME (Let's Encrypt) | own CA with mTLS | ACME requires reaching outwards |
| Embedder | `all-MiniLM-L6-v2`, 384 dims, English | `multilingual-e5-base`, 768 dims | retrieval quality on Polish documents |
| Images | `latest` tags from private namespaces | pinned by `sha256`, local mirror | supply chain for criminal case files |
| Port 5555 | exposed | closed inside the segment | it reveals Celery task metadata |

### Why the `openai` package stays

Reading the code showed that **Ollama is served through `OpenAIProvider`** rather than a dedicated client, because Ollama exposes an OpenAI-compatible API. The fork's code explicitly substitutes a dummy key (`"ollama"`) when none is present.

The consequence matters and runs against the intuition in the source report: **removing the `openai` package would break the local model, while leaving it in place creates no risk in itself.** The risk is the address that client points at. The guarantee is therefore not the absence of a key (a key is substituted anyway) but **pinning `base_url` to an allowlist**, enforced at process start and on writes to the database, together with the absence of a network route.

Details and the remaining findings: [`isolation-and-network.md`](isolation-and-network.md).

## Data flow: upload and query

```
UPLOAD
  file --> django --> minio (encrypted store)
                 \--> celery --> gotenberg (conversion where needed)
                             \-> docling + tesseract/rapidocr (OCR + layout)
                             \-> human preview and OCR correction        <-- gate
                             \-> embedder e5-base --> pgvector
                             \-> metadata agent --> proposed reference,
                                   authority, dates --> human confirmation <-- gate

QUERY
  question --> hybrid retrieval --> context (as DATA, not instructions)
           --> ollama/Bielik --> answer + declared citations
           --> citation verifier (comparison with the source)            <-- gate
           --> answer for the lawyer + audit log entry
```

The three human gates are deliberate: OCR is unreliable on photocopies, metadata is sometimes wrong, and the model's answer is working material rather than a finding.

## Architecture decisions

The reasoning lives in [`adr/`](adr/): ADR-0001 the foundation, ADR-0002 the language model, ADR-0003 the isolation strategy, ADR-0004 the embedder, ADR-0005 deterministic deadlines, ADR-0006 citation verification instead of an LLM judge, ADR-0007 citation by sentence number.
