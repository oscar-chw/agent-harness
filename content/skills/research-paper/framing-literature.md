# Framing questions and reading literature

Use this reference to decide what is worth investigating and what would constitute an answer. The procedures below are synthesis and practical inference. Source categories identify their basis. Source IDs resolve to [the shared ledger](../../knowledge/RESEARCH-SOURCES.md).

## Make the question answerable

**Personal advice.** Hamming links important work to having a plausible way to attack the problem. His examples are retrospective observations with selection and survivorship limits. Use them to ask what a successful answer would change and which obstacle can actually be investigated. Their evidential scope supports a question-selection heuristic. [HAM, transcript on important problems](https://www.cs.virginia.edu/~robins/YouAndYourResearch.html).

**Practical inference.** Write the phenomenon, setting, unit of analysis, comparison and desired answer in ordinary language. Identify the contribution type. A descriptive map needs credible coverage and measurement. A causal claim needs a defensible source of variation and assumptions. A theorem needs explicit premises and a complete argument. A new method needs a comparison that isolates its claimed advantage. Explain why the chosen evidence can answer this particular question.

List plausible competing explanations and an observation that would separate them. A faster program could benefit from a better algorithm, extra memory or different hardware. A benchmark gain could reflect preprocessing or the evaluation protocol. Choose the smallest informative observation within the authorized budget. This avoids spending the project on a result that leaves its central ambiguity unresolved. [DESIGN, choosing by objective](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm).

## Read to support a decision

**Personal advice.** Keshav proposes successive passes for orientation, understanding and reconstruction. Use an initial pass to decide relevance, a closer read for the claim and evidence, and reconstruction when a proof or method bears the weight of your own work. Record which pass was completed and what remains unresolved. Reading the abstract establishes what the authors claim. Reconstructing a derivation or executing an artifact requires its own record. [KES, Sections 2 and 3](https://cs.uwaterloo.ca/~brecht/courses/854-http-video-2012/readings/keshav-paper-reading.pdf).

**Practical inference.** Search by the phenomenon, adjacent terminology, leading methods and contradictory findings. Follow references backward to original methods and forward to replications, criticism and subsequent corrections. Keep queries, dates and inclusion/exclusion reasons when coverage supports a review claim. Match search effort to the decision's stakes. An unresolved definition or missing relevant result is a concrete reason to continue. Search coverage supports bounded novelty language such as “within the literature and dates searched.”

Keep a comparison matrix with each source's question, data/population, assumptions, comparator, result, uncertainty, limitations and read extent. Organize the synthesis around agreements and conflicts. When apparently conflicting papers use different populations or metrics, reconcile those differences before choosing which conclusion transfers.

## Keep discovery and confirmation legible

**Methodological argument.** Nosek and colleagues explain how specifying predictions and analyses before observing outcomes helps distinguish prediction from post hoc explanation. Their 2018 article explicitly acknowledged limited experimental evidence for preregistration's reproducibility benefits at that time. Use a dated analysis plan where suitable, preserve deviations and label exploratory discoveries. The case for transparent sequencing supports this practice without assuming universal empirical efficacy. [NOSEK, introduction and preregistration sections](https://psychologicalsciences.unimelb.edu.au/__data/assets/pdf_file/0007/2888098/The-preregistration-revolution.pdf).

**Verified workflow lead.** The pinned `interview-me` file in `pedrohcgs/claude-code-my-workflow` provides a research-spec structure covering motivation, hypotheses, data, identification and open questions. Its existence and contents were inspected. Transfer the useful prompts according to the project and preserve their status as a workflow pattern. Scientific effectiveness would need separate evidence. Its causal-identification prompts need adaptation for descriptive, theoretical and qualitative work. [SPEC, pinned file](https://github.com/pedrohcgs/claude-code-my-workflow/blob/fe7077463c06e6d1572bb6c13d1b00525a4ff28e/.claude/skills/interview-me/SKILL.md).

Keep a decision note containing the current question, closest checked work, proposed contribution, decisive uncertainty and next discriminating observation. Change it when the evidence changes, retaining the original question and the reason for revision.
