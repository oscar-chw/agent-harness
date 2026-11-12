# Selection examples and counterexamples

These are authored acceptance examples, not a completed model/reader experiment.
They show the decision boundary; adapt to the actual audience and evidence.

| Request | Useful output | Failure to avoid |
|---|---|---|
| “Is the deployment running?” | Direct status plus its observed evidence | A new architecture report or decorative progress chart |
| “How do I restart this service?”; three straight steps | Short numbered steps and expected result; link rollback | A sprawling flowchart with no meaningful branches |
| “What happens when requests retry across three services?” | Sequence diagram with actors, timing and failure path | A component picture that hides retry order |
| “What is on this server and who owns each part?” | Overview of components/boundaries plus an ownership table | An unlabeled hairball, or invented live topology |
| “Compare these four provider options” | Relevant trade-off table; show unknowns | A radar chart with fabricated quality numbers |
| “Show the measured daily latency trend” | Time chart with units, source, period and relevant ranges | Smoothed fictional data, missing units or unsupported certainty |
| “Which of these noisy estimates is better?” | Ranges and a bounded interpretation, or explain why ranking is unsupported | Hiding overlap or claiming a win from point estimates alone |
| “Where is this setting?” | Current cropped/annotated screenshot plus a searchable label | A stale full-desktop image with tiny text or exposed private content |
| “Teach these changing protocol states” | Static state diagram first; controlled animation if motion explains something | Autoplay decoration or interaction with no learning purpose |
| “Make the server wiki usable” | First-screen purpose, current status and common actions; link deeper references | Replacing a long opaque page with a different long opaque page |
| “Prepare an executive presentation” | Clear takeaway per slide, legible visual evidence; detail in notes | Dense report paragraphs copied onto slides |
| “The full architecture is necessary” | Inspectable overview plus linked subsystem views | Hiding complexity, or shrinking all labels to fit one poster |

For future paired trials, preserve the prompts, source data and expected distinctions.
Compare task success, interpretation errors and time, not whether the answer happens
to contain a diagram. Include a reader correction and a cold follow-up on a new task.
Keep the unchanged baseline and report failures; no human trial or native replay has
been run for these examples.
