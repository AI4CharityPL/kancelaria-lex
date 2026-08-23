# Runbook: deploying the environment

Two profiles. **The development profile never processes real case files.**

| | Development | Production |
|---|---|---|
| Hardware | Laptop, 64 GB RAM, 8 GB VRAM | Firm server, GPU ≥ 24 GB |
| Model | Bielik Q4_K_M, around 8k context | Bielik Q8_0 or FP16, 32k |
| Data | **Synthetic corpus only** | Real case files, after the gates |
| Network | `internal` segments, host on the LAN | `internal` segments, host disconnected |
| TLS | Own CA, local certificates | Own CA and mTLS |

## Development profile: installation

### Prerequisites

- Docker Desktop **running** (WSL2); the daemon has to be up
- Ollama ≥ 0.32
- around 30 GB of free space
- an NVIDIA driver with CUDA support

Verification:

```bash
docker info --format "{{.ServerVersion}} | {{.NCPU}} CPU | {{.MemTotal}}"
```

```bash
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

### Step 1: the language model

```bash
ollama pull SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M
```

After pulling, record the checksum in the manifest in `models/`:

```bash
ollama show SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M --modelfile
```

Pulling the model is the only step that needs the internet. In the production profile the weights arrive as an offline package; see [`offline-updates.md`](offline-updates.md).

### Step 2: the model tuned to the profile

The Modelfile in `models/Modelfile.bielik-dev` sets the context and generation parameters for 8 GB of VRAM:

```bash
ollama create bielik-lex-dev -f models/Modelfile.bielik-dev
```

The low temperature is deliberate, because in case file analysis creativity is a defect.

### Step 3: the fork and the patches

Clone upstream into `src/opencontracts/`, then apply the patches from `src/patche/`:

| Patch | State | Effect |
|---|---|---|
| `01-usun-sdk-chmurowe.patch` | applied | Removes the `anthropic`, `google` and `mcp` extras from `pydantic-ai-slim`, and removes `posthog` and `mcp`. **`openai` stays** as the transport to Ollama |
| `02-usun-mcp-i-discovery.patch` | applied | Removes MCP routing from **`config/asgi.py`** and the `discovery` app from `urls.py` and `INSTALLED_APPS`. The `opencontractserver/mcp/` and `opencontractserver/discovery/` directories are deleted from the tree (−14,726 lines) |
| `03-straznik-adresow.patch` | applied | Allowlist for `base_url` in `model_factory.py` and removal of the `anthropic` and `google-gla` branches |
| `04-embedder-pl.patch` | to do | `multilingual-e5-base`, 768 dimensions on the fork side (in compose the embedder is already a separate service) |
| `05-traefik-bez-acme.patch` | not applicable to the fork | We configure Traefik in our own `infra/compose/compose.yml`, not in upstream files |

**MCP routing lives in `config/asgi.py`, not in `urls.py`.** Upstream dispatches `/mcp`, `/mcp/*`, `/sse` and `/sse/*` to a separate ASGI application **before** Django. Two consequences worth remembering:

- `MCP_SERVER["enabled"]=False` **did not disable** the routing, because the router was created when the module was imported;
- MCP requests bypassed `ALLOWED_HOSTS` and `django-cors-headers`, because they never reached Django.

The `discovery` app additionally published `.well-known/mcp.json` and `llms.txt` with a ready configuration snippet for Claude Desktop, that is, it actively advertised the instance to agents.

**Before applying the patches, verify findings U-1 through U-8** from [`../isolation-and-network.md`](../isolation-and-network.md) against the current state of upstream. The findings date from 14.08.2026, and upstream changes; a patch applied to changed code can give the illusion of protection.

### Step 4: our own CA

```bash
bash infra/ca/utworz-ca.sh
```

### Step 5: start

```bash
docker compose -f infra/compose/compose.yml up -d
```

### Step 6: the verification gate

**This step is not optional.** An environment without passing isolation tests is not ready for use, even on the synthetic corpus, because habits carry over to production.

```bash
pytest tests/izolacja/ -v
```

It checks: no forbidden packages, a 404 on `GET /mcp/`, no DNS resolution, no TCP connections, the guard blocking an address outside the allowlist, and a database write rejected and logged.

**Any failing test stops the deployment.**

### Step 7: smoke run

Upload a document from `eval/korpus-syntetyczny/`, then OCR, indexing, a question, and an answer **whose citations pass verification**.

## Production profile: differences

1. **Weights from an offline package**, not through `ollama pull`, because the host has no internet access.
2. **The model in Q8_0 or FP16.** Q4 is not approved for real case files ([`../ai-stack.md`](../ai-stack.md)).
3. **mTLS between segments**, with certificates from our own CA and a renewal procedure (no ACME).
4. **Disk encryption** before first start, because it cannot be added later without a migration.
5. **A separate store and key for defence material** before the first case is entered.
6. **A backup configured and tested** before the first case is entered.
7. **A packet capture** during a full run as the final proof: zero outgoing packets.
8. The host disconnected from the internet at the level of the firm's network, independently of the Docker configuration.

## Conditions for admitting real case files

All of them together; the full list is in [`../compliance/gdpr-dpia.md`](../compliance/gdpr-dpia.md):

- [ ] Quality gates passed ([`../testing-and-gates.md`](../testing-and-gates.md))
- [ ] Isolation tests passed in the production environment
- [ ] Packet capture: zero outgoing packets
- [ ] Model in the production profile (Q8 or higher)
- [ ] Audit log working, checksum chain verifiable
- [ ] Defence material: separate store and key
- [ ] Backup restored in a test
- [ ] DPIA approved by the controller and the DPO
- [ ] Users trained, including in the duty of review

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| The model does not start | Not enough VRAM at 8 GB | Lower the context or increase CPU offload |
| Very slow answers | Layers went to the CPU | Reduce the context; check `nvidia-smi` while generating |
| A container cannot see Ollama | Ollama outside the Docker network | Check the address in `net_ai`; do not work around it by exposing it on the host |
| Isolation tests "pass" on everything | The tests are not really running | Check deliberately: add a route temporarily and make sure the test **fails** |
| OCR does not recognise Polish | `pol.traineddata` missing | Check the language pack in the docling container |

The fourth row is worth attention: a security test that always passes is worse than no test at all, because it gives false confidence. On first run you have to confirm that the test is capable of failing.
