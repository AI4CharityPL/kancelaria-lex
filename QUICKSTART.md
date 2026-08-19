# Setup guide

Written for someone who has never used a command line. Follow it top to bottom.

**Time:** about 30 minutes, most of it waiting for downloads.

After setup, **the system never needs the internet again.**

> Every step tells you **what you should see** when it worked. If you see
> something else, jump to [When something goes wrong](#when-something-goes-wrong).

---

## Step 0 - Will it run on your computer?

**Read this before downloading 9 GB.** The model is what needs the hardware, and
the difference between a suitable and unsuitable machine is not subtle.

### The short answer

| You have | What happens |
|---|---|
| **A graphics card with ≥ 6 GB of free VRAM** | The model runs entirely on the card. Answers in **10–30 seconds**. This is what everything below assumes. |
| **A graphics card with 4 GB** | Part of the model runs on the card, the rest on the processor. Works, noticeably slow. |
| **No graphics card (or an integrated one)** | Runs on the processor. **Measured 13× slower** - see below. Usable for trying it out; painful for daily work. |
| **Less than 16 GB of RAM and no graphics card** | **Do not.** The model alone needs 5,4 GB of RAM in this mode, before the system and your browser. |

### Minimum and recommended

| | Minimum | Recommended |
|---|---|---|
| **VRAM** (graphics memory) | 6 GB free | 8 GB |
| **RAM** | 16 GB | 32 GB |
| **Processor** | 4 cores | 8 cores |
| **Free disk** | 15 GB | 25 GB |
| **Operating system** | Windows 10/11, macOS 12+, or Linux | - |

Disk breakdown: **9,4 GB** for the two models, ~3 MB for the project itself, and
the rest for your case files, the database and backups.

> **Apple Silicon** (M1/M2/M3/M4) shares memory between processor and graphics,
> so the VRAM row does not apply - a 16 GB Mac behaves like the fast path.

### The measurement, so you can judge for yourself

Identical prompt, identical model, same machine - only the processor/graphics
choice differs:

| Where the model runs | Time |
|---|---:|
| Graphics card (Quadro RTX 4000, 8 GB) | **2,6 s** |
| Processor only (Core i7-10875H, 8 cores) | **33,7 s** |

**13,2× slower**, and that was a one-sentence question. A real question about a
case file takes 10–30 seconds on the card - so expect **several minutes** on a
processor, and longer on a weaker one than this.

The system does not break without a graphics card. It gets slow. Knowing which
one you are facing before you download 9 GB is the point of this section.

### The machine every published number comes from

The accuracy figures in the README were measured here, and nowhere else:

| | |
|---|---|
| Graphics | NVIDIA Quadro RTX 4000 Max-Q, **8 GB VRAM** (driver 580.92) |
| Processor | Intel Core i7-10875H, 8 cores / 16 threads |
| RAM | 64 GB |
| System | Windows 11 |
| Context window | 8192 tokens (set in the `Modelfile`s - do not change it) |

**Different hardware does not change the accuracy**, as long as the model fits
and you use the same models and settings - the quantisation, the context size and
the fixed seed are what determine the answer, not the card. Hardware changes the
speed. **Different models change everything**, which is why Step 3 pins exact
versions.

---

## Step 1 - Install Python

Download from **[python.org/downloads](https://www.python.org/downloads/)**
and run the installer.

> ### ⚠️ On the first screen, tick **"Add python.exe to PATH"**
> It is at the bottom and easy to miss. Without it, nothing below will work.

Then open a terminal:
- **Windows** - press `Win`, type `powershell`, press Enter
- **macOS** - press `Cmd+Space`, type `terminal`, press Enter
- **Linux** - you know where it is

Type this and press Enter:

```bash
python --version
```

**You should see:** `Python 3.12.x` or higher.
If you see "not recognised", Python was installed without PATH - reinstall and
tick the box.

## Step 2 - Install Ollama

This is the program that runs the AI model on your own machine.

Download from **[ollama.com/download](https://ollama.com/download)**, install it,
and start it. It runs quietly in the background (look for the icon in your system
tray or menu bar).

Check it:

```bash
ollama --version
```

**You should see:** a version number like `ollama version 0.12.x`.

## Step 3 - Download the two language models

This downloads about **9 GB**. It takes a while. You only do it once.

```bash
ollama pull SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M
```

```bash
ollama pull llama3.1:8b-instruct-q4_K_M
```

**You should see:** a progress bar, ending with `success`.

Why two models: the Polish one (Bielik, made in Poland) reads Polish documents,
the other reads English ones. **Using the wrong language model on a document
measurably wrecks the results** - so the system picks automatically per document.

### Check you got the same weights we measured

The tags above can be re-pointed at new builds by their publishers. If you want
your results to be comparable with the README, verify the identifiers:

```bash
ollama list
```

**You should see** these two lines, and the ID column must match **exactly**:

| Model | ID |
|---|---|
| `SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M` | `6660954d0758` |
| `llama3.1:8b-instruct-q4_K_M` | `46e0c10c039e` |

<details>
<summary>Full digests</summary>

```
sha256:6660954d075803e09b7b1e281b1879cb19719d5e40c2e8c516383b3d9c368c10
  SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M   (4,5 GB, verified 17.08.2026)

sha256:46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e
  llama3.1:8b-instruct-q4_K_M                          (4,9 GB, verified 17.08.2026)
```
</details>

**A different ID is not a fault** - it means the publisher shipped a new build.
The system will still work. But **the accuracy figures no longer apply to your
installation**, because they were never measured on those weights. If that
matters to you, re-run the measurement yourself: [`eval/README.md`](eval/README.md).

> **Quantisation matters as much as the model.** `Q4_K_M` is not a detail to
> improvise on. SpeakLeash's own model card warns that quantised models show
> reduced quality and more hallucination - every number we publish already
> includes that cost. Pulling a different quantisation makes your system
> incomparable to ours in both directions.

## Step 4 - Download this project

If you have Git:

```bash
git clone https://github.com/AI4CharityPL/kancelaria-lex.git
cd kancelaria-lex
```

If you do not: open the project page, click the green **Code** button →
**Download ZIP**, unpack it, then in the terminal type `cd ` (with the space) and
drag the unpacked folder onto the terminal window, then press Enter.

**You should see:** the terminal prompt now shows the project folder.

## Step 5 - Build the two working models

These add the instructions and settings the system needs.

```bash
ollama create bielik-lex-map -f models/Modelfile.bielik-map
```

```bash
ollama create llama-lex-map -f models/Modelfile.llama-map
```

**You should see:** `success` after each.

Confirm both exist:

```bash
ollama list
```

**You should see:** `bielik-lex-map` and `llama-lex-map` in the list.

## Step 6 - Tell Ollama to answer one question at a time

**Do not skip this.** With the default setting, the memory cache grows eightfold
and pushes the model onto the CPU, making everything several times slower. We
measured this.

**Windows** (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
```

**macOS / Linux** - add to `~/.bashrc` or `~/.zshrc`:

```bash
export OLLAMA_NUM_PARALLEL=1
```

Then **restart Ollama** (quit it from the tray/menu bar and start it again).
Settings only apply to a fresh start.

## Step 7 - Start the system

```bash
python panel/serwer.py
```

**You should see:** a few lines ending with an address like
`http://127.0.0.1:8713`.

**Leave this window open.** Closing it stops the system. To stop it deliberately,
click the window and press `Ctrl+C`.

## Step 8 - Open it and create your profile

Open your browser and go to:

```
http://127.0.0.1:8713
```

**You should see:** a dark blue login screen with a `§` mark.

1. Click **"Załóż nowy profil"** (create new profile).
2. Fill in login, password (at least 10 characters), first name, surname, role.
3. **Read the six statements at the bottom.** They describe obligations that stay
   with you and your firm - no software can do them for you. The button stays
   disabled until you have ticked all six. This is intentional.
4. Click **"Załóż profil i wejdź"**.

**You should see:** the main screen with the case list.

## Step 9 - Your first case

1. On the left, fill in **Sygnatura** (e.g. `II K 147/26`) and a working name,
   then click **+ Nowa sprawa**.
2. Drag a document onto the upload area, or click **"albo wklej treść ręcznie"**
   and paste text.
3. Type a question in Polish in the box on the right, e.g.
   *„Jakie zdarzenie akta wiążą z datą 13 stycznia 2025 roku?"*
4. Click **Analizuj akta**.

**You should see:** after 10–30 seconds, findings - each with a citation.

**Now click a citation.** The document opens with that exact passage highlighted.
**This is the whole point of the system.** Get into the habit: an answer you have
not clicked through is not yet a finding.

## Step 10 - Confirm your installation matches ours (optional, 2 minutes)

Everything above can appear to work while something is quietly wrong. The test
suite is how you check, and it is the same suite we run.

```bash
pip install pytest
```

```bash
python -m pytest tests/ -q --dozwol-pominiecie
```

**You should see**, after about two minutes:

```
577 passed, 123 skipped, 1 warning
```

**All three numbers are normal.** What they mean:

- **577 passed** - if any fail, something is genuinely wrong; do not load real
  case files until you know what.
- **123 skipped** - tests needing Docker, the OpenContracts fork or the
  measurement corpora, none of which this guide installs. Skipped is the
  correct outcome here, not a failure.
- **1 warning** - deliberate. It reads:

  > *J-3 = 82.0% - powyżej progu regresji 66%, ale PONIŻEJ CELU 90%.*

  The system refuses to answer correctly 82% of the time, against a target of
  90%. **We publish this as a warning on every single run rather than lowering
  the target to match reality.** The gap is real and open. Nothing is broken.

### Why `--dozwol-pominiecie`

Without that flag you will see **14 failures**, and they are not bugs.

The isolation gates (I-1, I-2, I-3) check the OpenContracts fork for cloud SDKs,
and further gates need a running Docker daemon. This guide installs neither.
Those gates **fail rather than skip on purpose**: a security gate that quietly
passes when it could not run is worse than no gate at all, because it reports
success it never verified.

`--dozwol-pominiecie` ("allow skipping") is how you say *I know these gates did
not run.* Use it while following this guide. Do **not** use it on the machine
that will hold real case files - there, the fork and Docker must be present and
the gates must actually pass.

> **These tests do not need the model, the internet or your documents.** They
> check the code. To reproduce the *accuracy* figures you also need the corpora
> and a 70–80 minute run - [`eval/README.md`](eval/README.md) explains how, and
> why we require the full 100 cases rather than a faster subset.

---

## When something goes wrong

**"python is not recognised"**
Python was installed without PATH. Reinstall and tick *"Add python.exe to PATH"*.

**The page will not open / "connection refused"**
The window from Step 7 must stay open. Check it for a red error message.

**"Model lokalny jest niedostępny"**
Ollama is not running. Start it and check with `ollama list`. If the list is
empty or missing `bielik-lex-map`, redo Steps 3 and 5.

**Port 8713 already in use**
Something else is using it - most often an older copy of this system still
running. Close it, or change `PORT` at the top of `panel/serwer.py`.

**"PDF nie zawiera tekstu, a jedynie obraz - to skan"**
Correct behaviour, not a fault. **This system has no OCR.** A scan without a text
layer is refused rather than loaded as empty - an empty document would produce a
case with no citations and no explanation why. Run OCR elsewhere first, then
upload the result.

**An answer takes several minutes**
Two different causes - check which one you have:

```bash
ollama ps
```

Look at the **PROCESSOR** column while a question is running.

- **`100% GPU`** - the model is on the graphics card, so this is the other cause:
  a question about a whole large case makes the system read document by document.
  **Tick a single document instead** - measured four times more accurate and four
  times faster. Selecting less genuinely gives you more.
- **`100% CPU` or a split like `40%/60% CPU/GPU`** - the model did not fit on your
  card. This is a hardware limit, not a setting; see
  [Step 0](#step-0--will-it-run-on-your-computer). Close other programs using the
  graphics card (browsers with hardware acceleration, games, video calls) and
  restart Ollama - that alone often frees enough.

**"model requires more system memory than is available" / Ollama crashes on load**
Not enough memory for the model. On a machine without a suitable graphics card
the model needs **5,4 GB of RAM** on top of everything else you are running -
16 GB total is the realistic floor. Close other programs and try again; if it
still fails, this machine cannot run it. See
[Step 0](#step-0--will-it-run-on-your-computer).

**Answers are poor quality**
Three things to check, in this order:

1. Step 6 was applied **and Ollama restarted afterwards**.
2. `ollama list` shows the IDs from [Step 3](#step-3--download-the-two-language-models).
   A different model is a different system.
3. You did not edit `num_ctx` in the `Modelfile`s. 8192 is measured, not
   arbitrary - raising it costs VRAM and pushes the model onto the processor.

---

## Before you load real case files

> ## ⚠️ What this guide installs is the **development profile**
>
> Everything above builds the system on **Q4_K_M quantisation with 8 GB of
> VRAM**. That is the configuration every published measurement was taken on -
> and it is **the configuration this project's own compliance documents do not
> approve for real case files.**
>
> | | Quantisation | VRAM | Approved for |
> |---|---|---|---|
> | **Development** - what this guide installs | Q4_K_M | 8 GB | **synthetic corpus only** |
> | **Production, minimum** | Q8_0 | 24 GB | real case files, after the gates |
> | **Production, recommended** | FP16 | 48 GB | real case files |
>
> The reason is in the model card, not in our opinion: **quantised models show
> reduced answer quality and greater susceptibility to hallucination.** The
> citation cannot be fabricated at any quantisation - that property is structural
> - but *which* sentence the model picks, and whether it should have answered at
> all, both get worse. The measured 82% correct refusal already reflects that.
>
> Sources, so you can check rather than take our word:
> [`docs/06-stos-ai.md`](docs/06-stos-ai.md) (profile table),
> [`docs/09-compliance/rodo-dpia.md`](docs/09-compliance/rodo-dpia.md) (point 106),
> [`SECURITY.md`](SECURITY.md) (known limitations).
>
> **This is not a reason to avoid the system.** It is a reason to know which
> profile you are on. Evaluate on the development profile - it is exactly what
> the setup above gives you, and it is honest about its own limits. Move to Q8_0
> on hardware that can hold it before a real criminal case file goes in, and
> re-run the quality gates there, because the numbers in this repository were
> not measured on it.

The system is local and verifies its citations. **These remain your firm's job,
and no software will do them for you:**

- [ ] **Decide which profile you are on** - see the warning above. This is the
      first decision, not the last, because it determines whether the rest of
      this list is even worth working through.

- [ ] **Encrypt the drive.** The system protects the network path, not your disk.
- [ ] **Take a backup and put it on a separate drive.** The *Kopie zapasowe*
      view has a button. A backup on the same disk does not survive that disk.
- [ ] **Practise a restore once**, before the first real case - the stated
      recovery times are assumptions until you have measured them yourself.
- [ ] **Turn on the second factor (MFA)** in *Kopie zapasowe* - password alone
      is one factor, and the KSC requirement stays unmet without it.
- [ ] **Assess whether your firm falls under KSC** and register if it does -
      self-identification, and absence of an entry is not neutral.
- [ ] **Have your DPO approve the data protection impact assessment.**
- [ ] **Train everyone who will use it** - AI Act art. 4 requires it, and it is
      an obligation, not a recommendation.

Details in [`docs/09-compliance/`](docs/09-compliance/) (Polish).

---

## Removing it

Delete the project folder, then:

```bash
ollama rm bielik-lex-map llama-lex-map
```

Your case files live in `panel/dane/` inside the project folder. **Deleting the
folder deletes the case files** - take a backup first if you need them.

---

*If this saved you time, please consider
[the Wrocław shelter](https://www.ratujemyzwierzaki.pl/schroniskowroclaw). 🐕*
