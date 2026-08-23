# AI Act: preliminary assessment

> **Disclaimer.** A preliminary assessment from the technical side, to be confirmed by a lawyer. Regulation (EU) 2024/1689 enters into force in stages and the practice of applying it is still taking shape. Position as at 14.08.2026; check that it is still current.

## The firm's role: deployer

The firm deploys the system for its own internal use. It does not place it on the market or supply it under its own brand, so as a rule it **is not a provider** but a deployer.

**Watch for crossing that line.** If the firm began to make the system available to other firms or to clients, even free of charge, it could become a provider, with a substantially wider set of obligations. This matters if the project is ever commercialised or shared.

## Is this a high-risk system?

**Preliminary answer: no.**

Annex III, point 8(a) covers systems intended to be used **by a judicial authority or on its behalf** in researching and interpreting facts and the law, and in applying the law to a specific set of facts.

The firm is not a judicial authority and does not act on behalf of one; it acts as a party's representative. The tool supports the lawyer's own work rather than adjudication.

**Arguments that strengthen this assessment:**

| Feature of the system | Significance |
|---|---|
| The output is working material, not a decision | No automatic legal effect |
| Mandatory review by a lawyer | The human is a condition of use, not a formality |
| No assessment of individuals, no profiling | Outside the scope of the other Annex III entries |
| No fine-tuning on personal data | No training-related risks |

**For the lawyer to settle:** whether the way the system is actually used brings it closer to the scope of Annex III, for instance if analyses went straight into procedural documents without genuine review. **Classification is determined by actual use, not by a declaration in the documentation.**

## Obligations that apply even without high risk

### 1. AI literacy (art. 4): applies

Deployers must ensure a sufficient level of AI literacy among staff operating AI systems, appropriate to their knowledge, experience and the context of use.

**This is an obligation, not a recommendation.** In practice: a training programme covering the limits of language models, the tendency to hallucinate, the significance of quantisation, how to read citations, and the boundaries of mechanical verification (what it confirms and what it does not; see R-4 in the DPIA).

The training combines with the training obligation from the amended KSC act: one programme, two obligations.

### 2. Transparency towards individuals

People whose data is processed should know that an AI tool is in use. GDPR information notices deliver that (task P-4).

### 3. Prohibited practices (art. 5): none present

Verified negatively: no social scoring, no emotion recognition, no biometric identification, no prediction of criminal offences based on profiling an individual.

The last point needs care in design. The discrepancy agent (A-5) **points out inconsistencies between accounts and always supplies citations**, but it does not assess a person's credibility or predict their behaviour. That boundary has to hold in future development as well; a shift towards "assessing witness credibility" would change the legal classification of the tool.

## General-purpose AI models

Bielik is an open model, downloaded and run locally. The obligations of a GPAI provider fall on the model's author (SpeakLeash), not on the firm.

The firm remains a deployer **as long as it does not fine-tune the model**. Not fine-tuning is a design decision with a double effect: it removes the risk of fixing data in the weights (GDPR) and it does not move the firm towards the role of provider (AI Act).

## Conclusion

| Question | Preliminary answer |
|---|---|
| The firm's role | Deployer |
| High risk (Annex III) | Probably not |
| Prohibited practices | None present |
| Art. 4, AI literacy | **Applies; training obligation** |
| GPAI provider obligations | Do not apply |
| Conformity assessment, CE marking, registration | Do not apply under the above classification |

## Tasks

| # | Task | Deadline |
|---|---|---|
| AI-1 | Classification confirmed by a lawyer | before the pilot |
| AI-2 | Training programme (shared with KSC) | before the pilot |
| AI-3 | Record the boundary: the system does not assess the credibility of individuals | written into [`../agents.md`](../agents.md), done |
| AI-4 | Reassessment whenever functionality is extended | ongoing |
| AI-5 | Reassessment if the system were ever made available outside the firm | conditional |
