# Setup guide

Written for someone who has never used a command line. Follow it top to bottom.

**Time:** about 30 minutes, most of it waiting for downloads.
**You need:** ~15 GB of free disk, and a graphics card with 8 GB of VRAM if you
want fast answers (it works without one — just slower).

After setup, **the system never needs the internet again.**

> Every step tells you **what you should see** when it worked. If you see
> something else, jump to [When something goes wrong](#when-something-goes-wrong).

---

## Step 1 — Install Python

Download from **[python.org/downloads](https://www.python.org/downloads/)**
and run the installer.

> ### ⚠️ On the first screen, tick **"Add python.exe to PATH"**
> It is at the bottom and easy to miss. Without it, nothing below will work.

Then open a terminal:
- **Windows** — press `Win`, type `powershell`, press Enter
- **macOS** — press `Cmd+Space`, type `terminal`, press Enter
- **Linux** — you know where it is

Type this and press Enter:

```bash
python --version
```

**You should see:** `Python 3.12.x` or higher.
If you see "not recognised", Python was installed without PATH — reinstall and
tick the box.

## Step 2 — Install Ollama

This is the program that runs the AI model on your own machine.

Download from **[ollama.com/download](https://ollama.com/download)**, install it,
and start it. It runs quietly in the background (look for the icon in your system
tray or menu bar).

Check it:

```bash
ollama --version
```

**You should see:** a version number like `ollama version 0.12.x`.

## Step 3 — Download the two language models

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
measurably wrecks the results** — so the system picks automatically per document.

## Step 4 — Download this project

If you have Git:

```bash
git clone https://github.com/AI4CharityPL/kancelaria-lex.git
cd kancelaria-lex
```

If you do not: open the project page, click the green **Code** button →
**Download ZIP**, unpack it, then in the terminal type `cd ` (with the space) and
drag the unpacked folder onto the terminal window, then press Enter.

**You should see:** the terminal prompt now shows the project folder.

## Step 5 — Build the two working models

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

## Step 6 — Tell Ollama to answer one question at a time

**Do not skip this.** With the default setting, the memory cache grows eightfold
and pushes the model onto the CPU, making everything several times slower. We
measured this.

**Windows** (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
```

**macOS / Linux** — add to `~/.bashrc` or `~/.zshrc`:

```bash
export OLLAMA_NUM_PARALLEL=1
```

Then **restart Ollama** (quit it from the tray/menu bar and start it again).
Settings only apply to a fresh start.

## Step 7 — Start the system

```bash
python panel/serwer.py
```

**You should see:** a few lines ending with an address like
`http://127.0.0.1:8713`.

**Leave this window open.** Closing it stops the system. To stop it deliberately,
click the window and press `Ctrl+C`.

## Step 8 — Open it and create your profile

Open your browser and go to:

```
http://127.0.0.1:8713
```

**You should see:** a dark blue login screen with a `§` mark.

1. Click **"Załóż nowy profil"** (create new profile).
2. Fill in login, password (at least 10 characters), first name, surname, role.
3. **Read the six statements at the bottom.** They describe obligations that stay
   with you and your firm — no software can do them for you. The button stays
   disabled until you have ticked all six. This is intentional.
4. Click **"Załóż profil i wejdź"**.

**You should see:** the main screen with the case list.

## Step 9 — Your first case

1. On the left, fill in **Sygnatura** (e.g. `II K 147/26`) and a working name,
   then click **+ Nowa sprawa**.
2. Drag a document onto the upload area, or click **"albo wklej treść ręcznie"**
   and paste text.
3. Type a question in Polish in the box on the right, e.g.
   *„Jakie zdarzenie akta wiążą z datą 13 stycznia 2025 roku?"*
4. Click **Analizuj akta**.

**You should see:** after 10–30 seconds, findings — each with a citation.

**Now click a citation.** The document opens with that exact passage highlighted.
**This is the whole point of the system.** Get into the habit: an answer you have
not clicked through is not yet a finding.

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
Something else is using it — most often an older copy of this system still
running. Close it, or change `PORT` at the top of `panel/serwer.py`.

**"PDF nie zawiera tekstu, a jedynie obraz — to skan"**
Correct behaviour, not a fault. **This system has no OCR.** A scan without a text
layer is refused rather than loaded as empty — an empty document would produce a
case with no citations and no explanation why. Run OCR elsewhere first, then
upload the result.

**An answer takes several minutes**
Normal for a question about a whole large case: the system falls back to reading
document by document. **Tick a single document instead** — measured four times
more accurate and four times faster. Selecting less genuinely gives you more.

**Answers are poor quality**
Check that Step 6 was applied and Ollama was restarted afterwards.

---

## Before you load real case files

The system is local and verifies its citations. **These remain your firm's job,
and no software will do them for you:**

- [ ] **Encrypt the drive.** The system protects the network path, not your disk.
- [ ] **Take a backup and put it on a separate drive.** The *Kopie zapasowe*
      view has a button. A backup on the same disk does not survive that disk.
- [ ] **Practise a restore once**, before the first real case — the stated
      recovery times are assumptions until you have measured them yourself.
- [ ] **Turn on the second factor (MFA)** in *Kopie zapasowe* — password alone
      is one factor, and the KSC requirement stays unmet without it.
- [ ] **Assess whether your firm falls under KSC** and register if it does —
      self-identification, and absence of an entry is not neutral.
- [ ] **Have your DPO approve the data protection impact assessment.**
- [ ] **Train everyone who will use it** — AI Act art. 4 requires it, and it is
      an obligation, not a recommendation.

Details in [`docs/09-compliance/`](docs/09-compliance/) (Polish).

---

## Removing it

Delete the project folder, then:

```bash
ollama rm bielik-lex-map llama-lex-map
```

Your case files live in `panel/dane/` inside the project folder. **Deleting the
folder deletes the case files** — take a backup first if you need them.

---

*If this saved you time, please consider
[the Wrocław shelter](https://www.ratujemyzwierzaki.pl/schroniskowroclaw). 🐕*
