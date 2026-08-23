# Hardware and costs

## Development profile: the current machine

| Component | State | Assessment |
|---|---|---|
| CPU | i7-10875H, 8 cores / 16 threads | Sufficient; OCR and embeddings run on the CPU |
| RAM | 64 GB | With room to spare; allows offloading model layers |
| GPU | Quadro RTX 4000 Max-Q, **8 GB VRAM**, CUDA 7.5 | **The bottleneck** |
| Disk | 169 GB free on C: | Sufficient (around 30 GB needed) |
| Docker | 28.3.0, WSL2 | The daemon has to be started |
| Ollama | 0.32.9 | Ready |

### What fits in 8 GB of VRAM

| Configuration | VRAM | Context | Assessment |
|---|---|---|---|
| Bielik-11B **Q4_K_M** | around 6.7 GB | around 8k | Fits, tightly; the development profile |
| Bielik-11B Q4 with a larger context | over 8 GB | 16k and above | Needs CPU offload, markedly slower |
| Bielik-11B **Q8_0** | around 12 GB | | **Does not fit** |
| Bielik-11B FP16 | around 22 GB | | Does not fit |

The embedder (`multilingual-e5-base`) and OCR run on the CPU, so they do not compete for VRAM. That split of resources is deliberate.

**Conclusion: the current machine is enough for the proof of concept and for nothing beyond it.** The limit is not convenience but quality: Q4 raises the tendency to hallucinate, which is unacceptable with criminal case files.

## Production profiles

Three variants for the firm to choose between. The figures are **indicative** (August 2026 level, net, hardware only) and need a current quotation.

### Variant A: small firm *(2 to 5 lawyers)*

| Component | Specification |
|---|---|
| GPU | 1 × 24 GB (RTX 4090 or RTX 5000 Ada class) |
| CPU | 12 to 16 cores |
| RAM | 128 GB |
| Disk | 2 × 2 TB NVMe (RAID 1), encrypted |
| Model | Bielik-11B **Q8_0**, 32k context |
| Concurrency | 2 to 3 simultaneous queries |
| Hardware cost | around 25,000 to 35,000 PLN |

The minimum variant admissible for real case files. Q8 meets the production profile requirement.

### Variant B: medium firm *(5 to 15 lawyers)*, recommended

| Component | Specification |
|---|---|
| GPU | 1 × 48 GB (RTX 6000 Ada or L40S class) |
| CPU | 16 to 24 cores |
| RAM | 256 GB |
| Disk | 2 × 4 TB NVMe (RAID 1) plus backup storage |
| Model | Bielik-11B **FP16**, 32k and above; room for a reserve model |
| Concurrency | 5 to 8 simultaneous queries |
| Hardware cost | around 60,000 to 90,000 PLN |

Recommended, because 48 GB of VRAM leaves headroom to **change the model without changing the hardware**. Given the pace at which open models develop, that matters: hardware sized exactly to one model ages with it.

### Variant C: large firm *(15 and above)*

| Component | Specification |
|---|---|
| GPU | 2 × 48 GB or 1 × 80 GB |
| RAM | 512 GB |
| Disk | A redundant array |
| Model | A larger model alongside Bielik for Polish-language work |
| Hardware cost | around 150,000 to 250,000 PLN |

## Costs beyond hardware

| Item | Nature | Notes |
|---|---|---|
| Implementation work | One-off | The main cost of the project: the case module, integrations, tests |
| **Maintaining the fork** | **Ongoing** | Most often underestimated; see below |
| Maintenance windows | Ongoing | Around one day per quarter, plus extraordinary windows |
| Approving the deadline rules | One-off plus reviews | A lawyer's time, not an engineer's |
| Training | One-off plus turnover | A shared KSC and AI Act programme |
| DPIA and documentation | One-off plus annual reviews | The DPO's time |
| Audit (if an essential entity) | Every two years | By 03.04.2028 |
| Electricity | Ongoing | A GPU server under load is a material item |

### Maintaining the fork, a cost worth separating out

A fork means taking on responsibility for the security of the whole base stack. Upstream ships fixes; somebody has to review them, apply them, and check that they have not undone the removal of the cloud paths.

The CI gate on the lockfile lowers that cost but does not remove it. Realistically it is **several to a dozen hours a month** of steady engineering work. A project without assured maintenance should not go to production: an unpatched system in a law firm is a risk rather than a saving.

## What not to buy

| | Reason |
|---|---|
| A GPU with 8 to 16 GB of VRAM "to start with" | It forces Q4 quantisation, which is inadmissible for real case files. A false economy. |
| A server in the cloud, even a "private" one | The data leaves the firm's control, which is a problem of professional privilege rather than of the GDPR |
| Consumer GPUs without ECC for variant C | Under continuous load and with large memory, memory errors stop being theoretical |
| Hardware sized exactly to the current model | The model will change sooner than the hardware |

## A decision to take after the proof of concept

Choosing a variant needs data we do not yet have: the real number of concurrent users, the volume of case files, and an acceptable response time. **The proof of concept will supply the measurements**, of throughput, OCR time and retrieval quality, and only on that basis is it worth choosing hardware.

Ordering a server before the proof of concept is guesswork.
