# Plan and execute this task

For multi-step work, inspect `plan resume` in the project first. Continue an existing
matching graph; do not make a second plan in state_save. For a new authorized reversible
task, use `plan new <slug> "<goal>" --autonomous`; otherwise retain the approval boundary.

1. State the goal and a check that can fail. Retrieve only relevant memory, current
   sources and prior decisions; distinguish facts, assumptions and unknowns.
2. Inspect the existing code and relevant upstream methods. Record what was checked,
   what is reused and why. Preserve deferred sources rather than calling them analyzed.
3. Write analysis, research and plan sections in the graph. For each implementation
   node name dependencies, file ownership, inputs, output and an independent gate.
4. Sketch interfaces before broad changes. Use bounded parallel work only for disjoint
   tasks whose integration check is known. A worker report never completes a node.
5. Open a node with `plan context`; close it with `plan gate`. On failure return to
   the evidence, design or implementation that caused it. Preserve the failed result.
6. Keep the current graph, source revisions, next action and blockers on disk. Use
   state_save only for a compact pointer or unfinished work without a graph.
7. At completion, retain useful observed lessons. Draft a source-bound method only
   from independent task episodes; preparation is not promotion or proof of learning.

Optional artifact shapes are in the installed `content/templates/` directory.
Keep explanations concise. Task:
