# Loading case files and OCR: what was measured, and on what

This document sets out **what data** the document loading path was checked against, **in what quantity**, and where its limits lie. It was written on 19.08.2026, before the repository was published.

> **The overriding rule of this path.** Text extracted from a file becomes the **source of citations**: the verifier compares a citation against it character by character. Faulty extraction therefore breaks the entire chain of guarantees quietly, because the citation passes verification against a corrupted source. That is why every path ends at a quality gate, and why **a refusal is a correct outcome**.

## 1. The measurement corpus

| Property | Value |
|---|---|
| Number of files | **173 PDFs** |
| Origin | the `Downloads` folder of the development machine: real documents, not synthetic ones |
| Kinds | contracts and NDAs, letters of intent, commercial offers, invoices and accounting printouts, technical documentation, CVs, letters bearing handwritten signatures |
| Languages | Polish and English, some documents mixed |
| Size range | 35 kB to 9.1 MB |

**These files are not in the repository and never will be.** They are the private and business documents of the person running the project; they served only as measurement material on a local machine. What stays in the repository is **the numbers alone**, per requirement T-6.

The corpus is arbitrary, and that is its strength: it was not chosen to suit the parser. It contains exactly what arrives at a law firm, namely stamped letters, scans of signed contracts and printouts from accounting systems.

## 2. Final result

| Category | Files | Share |
|---|---:|---:|
| **Read from the text layer** | **87** | 50.3% |
| **Read through OCR** | **16** | 9.2% |
| Rejected with an explanation | 70 | 40.5% |
| **Usable in total** | **103** | **59.5%** |

OCR handled **147 pages** and 39,175 characters, of which 1,127 were diacritics (2.9%), in a total of **2.9 minutes**, or around 1.2 seconds per page.

## 3. How that result was reached: three defects, each measured

At the start of the measurement, 75 files out of 173 could be read. Three fixes raised that to 87 on the text layer alone.

### 3.1. The image filter was discarding the text of whole pages

The condition `b"/Image" in cialo` looked for the string in **the entire object including the compressed stream**. The intent was to skip images; the effect was to discard **the whole content stream of a page** whenever the string `/Image` appeared anywhere in it. And it always appears when a page carries a logo, a stamp, a signature or a background.

Procedural documents almost always have a firm letterhead and a seal, so the defect struck the **typical case rather than the edge case**.

The first fix changed nothing, because it looked for the pair `/Subtype` and `/Image` in the dictionary, and that dictionary carries `/ProcSet [/PDF /Text /ImageB /ImageC]`, where `/Image` is a prefix of `/ImageB`. Only matching the **pair `/Subtype /Image`** worked.

### 3.2. The `/ToUnicode` maps were built and never used

A PDF stores no text, only glyph numbers. It is the `/ToUnicode` map that says what a given glyph means. Binding a resource name (`/F4`) to a map went through a regular expression over `/Font`, and the resource dictionary is **nested**, so the non-greedy match stopped at the first closing pair of angle brackets, usually the wrong one.

Measured on a test file: **10 maps built, 10 fonts used, zero bindings**. Every character went down the cp1252 fallback path and came out as an arbitrary byte. Binding now runs across the whole document.

### 3.3. Every positioning operator was breaking the line

Treating `Td` unconditionally as a new line produced text scattered into individual letters, because PDF generators set the position **separately for each character**. A new line occurs if and only if the vertical coordinate changes.

While there, the distribution of horizontal offsets was measured (3,294 samples, 12 to 13 point type):

| quantile | 0.10 | 0.50 | 0.75 | 0.97 |
|---|---:|---:|---:|---:|
| offset | 3.15 | 6.41 | 7.14 | 10.38 |

Inter-letter and inter-word spacing **do not separate at any threshold**, because the distribution is unimodal: this generator inserts spaces as separate glyphs. Adding spaces at a threshold of 1.2 broke 6,053 characters against 3,524 correct ones, giving `C o n t a c t` instead of `Contact`. The threshold is now a fraction of the type size and adds a space only where the jump is clearly wider than a character.

## 4. OCR: configuration and limits

| Element | State |
|---|---|
| Engine | Tesseract 5.4.0, invoked as a **separate process** |
| Language data | `models/tessdata/` with `pol`, `eng` and `osd`, pinned by `sha256` in [`../models/manifest.md`](../models/manifest.md) |
| Python dependencies | **none**; images are extracted with `zlib` and `struct` from the standard library |
| Privileges | no administrator rights needed: `TESSDATA_PREFIX` points at the project directory |

### Polish is required; English is not a substitute

Measured on a sentence from a Polish court order:

```
pol:  Sąd Okręgowy … oddalił wniosek obrońcy o dopuszczenie
eng:  Sad Okregowy … oddalit wniosek obroncy 0 dopuszezenie
```

English **"works"** and returns text that looks plausible, with not a single diacritic, a zero in place of the letter `o`, and `dopuszezenie` mangled. A missing Polish pack is therefore a **refusal**, not a fallback to English.

### What OCR will not do here

Images are **extracted from the PDF**, not rendered. A scan saved as a PDF has a page that is an image, so it is enough to take that image out (`/DCTDecode` is a ready JPEG; `/FlateDecode` we assemble into a PNG). Rendering would require an engine such as poppler or Ghostscript, which is one more program to pin and watch.

The consequence is that **70 files remain unread**. They are vector PDFs with a text layer that cannot be deciphered without a full analysis of PDF encodings, and they contain no image to recognise. The panel says so plainly instead of returning an empty document.

## 5. OCR changes the nature of the main guarantee

The system promises that *a citation leads to a specific character in the case file*. For a document that came through OCR, the true sentence reads differently:

> a citation leads to a specific character **in the reading of the scan**

An example from the measurement: the heading of a letter of intent was recognised correctly (`dotyczący utworzenia spółki kapitałowej`), but a date filled in by hand came out as **`4 9.03.2026`**. In the context of a procedural deadline that is the difference between meeting it and losing it.

Hence:

- a document loaded through OCR receives a **permanent marker** `zrodlo_tekstu = "ocr"` in the database, visible in the document list;
- **every citation** from such a document carries an `z OCR` marker and a warning to check it against the original, especially case references, amounts and dates;
- the marker is applied **unconditionally**, outside the support control switches, because a warning that disappears when an unrelated switch is flipped would be worse than no warning at all;
- OCR **does not start by itself**. It is the last resort after a document has been rejected by the quality gate, and it requires a click on "Rozpoznaj pismo".

The provenance of text is tracked for **every** route in: `wklejony` (pasted straight into the panel), `plik` (TXT, MD, DOCX, RTF, PDF with a text layer) and `ocr`.

## 6. Repeating the measurement

The measurement is not part of the test run, because it needs a directory of real PDFs, which the repository does not contain and will not. The unit tests (`tests/test_ocr.py`, `tests/test_wczytywanie.py`) do check the behaviour on files built in code, including **refusal when the Polish pack is missing** and **provenance marking**.

To repeat the measurement on your own set, point at a directory and call `wczytaj(nazwa, dane)` and `wczytaj(nazwa, dane, ocr_dozwolony=True)` for each file; see `panel/wczytywanie.py`.
