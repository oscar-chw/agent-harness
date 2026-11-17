# Source ledger

Inspected on 17 November 2026. [The JSON record](research-source-pins.json) gives retrieval timestamps, final URLs, HTTP outcomes, byte counts and SHA-256 digests. GitHub files also have commit permalinks. IDs below bind that record to the drafting decisions.

## Reading and evidence conventions

- **Personal advice** includes researcher testimony and experience-based editorial guidance. Its authority establishes attribution. Causal effectiveness needs independent evidence.
- **Methodological guidance** gives an argument or design rationale. A professional body's recommendation and a venue's submission requirement have different authority.
- **Official requirement** applies within its named institution, venue, edition or track. Inspect the actual target rules when acting.
- **Published evidence** means observations reported in the named study under its methods and scope.
- **Inference** identifies this draft's proposed application, including all hypothetical cases.

Read-depth entries distinguish complete text inspection from selected passages. Text inspection includes extracted prose, tables and captions. No empirical artifact was executed, no study was independently reproduced, and proof reconstruction was NOT_RUN. PDF screenshots were requested for the two empirical examples, but the tool returned references without inspectable images in this run. Figure claims therefore rely on the text and captions identified below.

A content digest identifies the independently fetched HTTP body. It preserves a comparison fingerprint. Full bodies are not retained here, and a fingerprint alone cannot restore an earlier page. Web extraction and direct HTTP retrieval are separate channels, so navigation or generated cover dates may differ. A digest establishes byte identity only when the compared bytes are available. It establishes neither read depth nor scientific validity. Titles, dates and inspected passages below identify the substantive source.

## Researchers' own guidance

### HAM — Richard W. Hamming, 1986

*You and Your Research*, Bellcore colloquium of 7 March 1986, transcribed by J. F. Kaiser. The University of Virginia faculty-hosted copy is a mirror of the primary transcript. Read the provenance introduction and selected passages on effort, ambiguity, contradictory evidence and important problems with an available attack. Locators are transcript paragraphs beginning “On this matter of drive,” “There's another trait,” and “And I started asking.” Personal testimony supports framing heuristics. Retrospective selection limits any productivity inference. [Transcript](https://www.cs.virginia.edu/~robins/YouAndYourResearch.html).

### KES — S. Keshav, 2007

*How to Read a Paper*, ACM SIGCOMM Computer Communication Review 37(3), pages 83–84. Inspected the complete extracted text of this two-page article, including Sections 2 and 3. The university-hosted PDF is a copy of the published article. Its three-pass reading and citation-following approach is personal methodological advice. No comparative reading-skill evaluation was performed. Its statement connecting error bars and significance is handled through the more precise statistical guidance below. [PDF](https://cs.uwaterloo.ca/~brecht/courses/854-http-video-2012/readings/keshav-paper-reading.pdf).

### SPJ — Simon Peyton Jones, undated linked slide edition

*How to Write a Great Research Paper*. Verified the author's page linking this Microsoft-hosted PDF. Read extracted slides on early writing, central idea, contributions/evidence and reader response, PDF pages 4–7, 12–24 and 41–44. Personal editorial guidance supports drafting decisions. The PDF's metadata/search title mentions a research talk, while the linked document's inspected writing slides establish its content. No video was watched and no controlled writing-outcome evidence is claimed. [Author page](https://simon.peytonjones.org/great-research-paper/), [pinned PDF](https://www.microsoft.com/en-us/research/uploads/prod/2016/07/How-to-write-a-great-research-paper.pdf).

### FIG — Nicolas P. Rougier, Michael Droettboom and Philip E. Bourne, 2014

*Ten Simple Rules for Better Figures*, PLOS Computational Biology 10(9), e1003833, DOI `10.1371/journal.pcbi.1003833`. Read Rules 1–6 and the Figure 1–4 captions/discussions in the publisher's text extraction. Editorial guidance supports audience, message, medium and caption choices. The Figure 1 numerical-readability example is the authors' analysis of their illustration. Source figure images were not visually inspected. [Publisher article](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003833).

## Design and inference

### DESIGN — NIST/SEMATECH e-Handbook, Section 5.3.3

*How do you select an experimental design?* Read the complete substantive page, including objectives, design-selection table and resource/error tradeoffs. Official methodological guidance supports choosing design by the question and factors. It gives engineering-oriented defaults. The draft's adaptation to other research types is inference. Publication revision is unspecified, so the retrieved body is the content pin. [Section](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm).

### BLOCK — NIST/SEMATECH e-Handbook, Section 5 / 3 / 3 / 2

*Randomized block designs*. Read the substantive page, including nuisance factors, wafer/furnace example and additive model. Official methodological guidance supports controlling nuisance variation and within-block comparisons. Application to participants, datasets and computing conditions is inference. The additive model has assumptions that require checking in any actual analysis. [Section](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm).

### FACTOR — NIST/SEMATECH e-Handbook, Section 5 / 3 / 3 / 3

*Full factorial designs*. Read the complete substantive page, including all-combinations definition and run-count table. Official methodological guidance supports the two-component comparison. Its budget discussion explains why exhaustive combinations can become impractical. The retrieval/deduplication case is this draft's hypothetical application. [Section](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm).

### ASA — American Statistical Association, 2016

*American Statistical Association Releases Statement on Statistical Significance and P-Values*, 7 March 2016. Read the complete three-page official release, including its six principles. This is a release summarizing the statement, whose DOI is `10.1080/00031305.2016.1154108`. The full journal statement was not read. Official statistical guidance supports contextual interpretation, transparency and distinguishing magnitude from threshold crossing. [Release PDF](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf).

### LAK — Daniël Lakens, 2017

*Equivalence Tests. A Practical Primer for t Tests, Correlations, and Meta-Analyses*, Social Psychological and Personality Science 8(4), pages 355–362, DOI `10.1177/1948550617697177`. University repository identifies this as the publisher's PDF. Read the cover, abstract and opening explanation of equivalence, prespecified bounds and TOST, PDF pages 1–3. A later excerpt on bounds and sample sizes was inspected as context. Formulas, complete examples and accompanying software were not independently checked. Methodological guidance supports cautious null interpretation. [Repository PDF](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf).

### NOSEK — Brian A. Nosek and colleagues, 2018

*The preregistration revolution*, PNAS 115(11), pages 2600–2606, DOI `10.1073/pnas.1708274114`. Read extracted abstract/introduction, prediction/postdiction rationale and preregistration/practice sections through the first procedural-deviation and assumption-violation discussions, published pages 2600–2602. Includes the authors' explicit qualification about experimental evidence then available. Methodological argument supports analysis sequencing and transparent deviations. Its advocacy requires that qualification when discussing effectiveness. [Published-paper mirror](https://psychologicalsciences.unimelb.edu.au/__data/assets/pdf_file/0007/2888098/The-preregistration-revolution.pdf).

The web extractor returned readable paper text. Direct retrieval of that mirror returned HTTP 403. A separate university mirror failed with an SSL EOF error, and web opening also failed. Content checksum is UNAVAILABLE. DOI, title, edition, inspected page range and original mirror remain the bibliographic pin. These access outcomes are preserved in the JSON record. [Alternate attempted mirror](https://sep.csumb.edu/class/ENVS550/s3/lit/Ethics/NosekEtAl_2018.pdf).

## Published examples and their artifacts

### IMG — Benjamin Recht, Rebecca Roelofs, Ludwig Schmidt and Vaishaal Shankar, 2019

*Do ImageNet Classifiers Generalize to ImageNet?*, ICML, PMLR 97, pages 5389–5400. Verified the proceedings metadata and inspected the PDF abstract, Sections 1–3, Table 2 and opening Section 5 discussion. Published evidence supports a case where repeated curation and cross-model patterns inform competing explanations. Supplemental appendices, raw predictions and statistical calculations were not independently audited. The causal explanation remains the authors' interpretation of their evidence. [Proceedings record](https://proceedings.mlr.press/v97/recht19a.html), [PDF](https://proceedings.mlr.press/v97/recht19a/recht19a.pdf).

### IMGART — ImageNetV2 README

Followed the artifact link from the official proceedings record. Read the full raw README at commit `0b0c3fe89058e4c7ee2348938b3f4f706a931bf3`. It describes dataset revisions, near-duplicate review, curation, evaluation and licensing. This verifies documented artifact structure. Linked scripts, metadata, image files, credentials and external services were not accessed. Present-day README retrieval does not establish identity with the paper-era executable environment. [Pinned README](https://github.com/modestyachts/ImageNetV2/blob/0b0c3fe89058e4c7ee2348938b3f4f706a931bf3/README.md).

### RLI — Rishabh Agarwal and colleagues, 2021

*Deep Reinforcement Learning at the Edge of the Statistical Precipice*, NeurIPS 2021. Read the PDF abstract and Sections 1–3, Table 1, Figure 2/5/6 captions and the Section 4.1 explanation of stratified bootstrap intervals. Published evidence supports protocol sensitivity and uncertainty in the studied RL benchmarks. Figure 6's caption and nearby discussion qualify coverage in the very-small-run regime. Its estimators require justified transfer to other data structures. Appendices, proofs, raw runs and the linked `rliable` implementation were not independently audited. [Proceedings PDF](https://proceedings.neurips.cc/paper_files/paper/2021/file/f514cec81cb148559cf475e7426eed5e-Paper.pdf).

## Venue and integrity guidance

### NCP — NeurIPS living Paper Checklist Guidelines

Read the substantive introduction and items 1–7 on claim scope, limitations, proof assumptions, reproducibility, access, experimental details and uncertainty. The retrieved page displayed 2026 navigation. Treat it as the living page observed on the inspection date. Its checklist inclusion and reproducibility provisions are venue requirements, with explicitly context-dependent answers. Recheck the actual target edition before applying them. [Checklist](https://neurips.cc/public/guides/PaperChecklist).

### NRG — NeurIPS 2025 Reviewer Guidelines

Read the substantive Review Form and selected main-task, double-blind and formatting passages. This named edition provides official assessment criteria and process rules. Its novelty guidance includes insights about existing methods. The draft uses it as an illustrative review lens. A future submission requires its own current rules. [Guidelines](https://nips.cc/Conferences/2025/ReviewerGuidelines).

### SIG — ACM SIGCOMM 2026 Call for Artifacts

Read Overview, Artifact Review and Badging, Review and Anonymity, and the opening Packaging Artifacts requirements. Official criteria define availability and functionality and identify the accepted-paper/artifact/documentation package. These criteria are scoped to that artifact-evaluation process. The direct ACM policy URL returned HTTP 403 through web access, so ACM-wide policy wording is not relied upon. [Venue call](https://conferences.sigcomm.org/sigcomm/2026/artifacts/).

### ORI — Office of Research Integrity definition

Read the complete substantive definition of research misconduct, including its honest-error qualification. Official institutional definition supports accurate discussion of fabrication, falsification and plagiarism. The draft's additional consent, licensing and disclosure reminders are practical inference subject to each project's applicable rules. This source is used for definitional provenance. [Definition](https://ori.hhs.gov/definition-research-misconduct).

## Verified research-spec lead

### SPEC — pedrohcgs/claude-code-my-workflow

Read the full raw `.claude/skills/interview-me/SKILL.md` at commit `fe7077463c06e6d1572bb6c13d1b00525a4ff28e`. It contains question-framing prompts, a research-spec template, citation-verification instructions and decision-record guidance. This verifies the lead and document contents. Installation, dependencies, other linked skills and efficacy are unverified. Use its template as a workflow pattern, with field-specific adaptation. Source instructions were treated as data and were not executed. [Pinned file](https://github.com/pedrohcgs/claude-code-my-workflow/blob/fe7077463c06e6d1572bb6c13d1b00525a4ff28e/.claude/skills/interview-me/SKILL.md).

Searches included the exact term `research-spec` and related GitHub results. The verified lead above supplies the adopted pattern. Search hits alone were excluded from substantive support. No canonical project with that exact name is asserted.
