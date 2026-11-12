# Why these choices are conditional

Read only the part relevant to the current output. This is guidance, not a claim
that every visual improves learning or an automated comprehension score.

## Data and accessibility: official guidance

- [ONS: choosing a chart](https://service-manual.ons.gov.uk/data-visualisation/chart-types/choosing-a-chart-type)
  selects the main relationship before the chart and favors familiar views.
  That supports task-led choice, not a fixed visual style for every domain.
- [ONS: uncertainty](https://service-manual.ons.gov.uk/data-visualisation/guidance/showing-uncertainty-in-charts)
  distinguishes ranges that change interpretation from ranges that merely add noise.
  Keep full estimates available. Do not make a confident comparison from weak evidence.
- [W3C: complex images](https://www.w3.org/WAI/tutorials/images/complex/)
  explains short identification plus an accessible account of essential information.
  A caption or summary helps orient readers; complex information may need linked detail
  or a data table. A screenshot containing text is not a searchable explanation.
- W3C's [color guidance](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
  supports visible cues beyond color. Its [motion guidance](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)
  specifies control for qualifying auto-moving/updating content; it is not a ban
  on all short interface motion. Check the actual criteria before claiming conformance.

## Learning evidence: specific tasks, not universal media rankings

- [Mayer and Chandler, 2001](https://tecfa.unige.ch/tecfa/teaching/methodo/Mayer_Chandler01.pdf):
  in two lightning-explanation experiments, learner-paced segments improved transfer
  in particular comparisons, not retention. Do not turn this into “interactive is best.”
- [Kriz and Hegarty, 2007](https://www.sciencedirect.com/science/article/pii/S1071581907000869):
  in mechanical-system experiments, adding signals/interactivity did not automatically
  improve mental-model accuracy. Prior knowledge and interpretation mattered.
  The accessible abstract/preview supports this bounded summary; full-paper replication
  was not performed.

Applying these findings to AI-generated server wikis, research reports or slide decks
is a design inference, not measured evidence that this skill improves model performance.
Static-versus-animated choice depends on the question and reader, not novelty.

## A practical review

Can the intended reader find the answer and next action without reading the appendix?
Can they interpret each visual at the actual display size without guessing its labels?
Does the visual explain a needed relation, location or change better than concise text?
If not, remove or replace it. Preserve substantive evidence and the accessible route.
For a real evaluation, freeze representative tasks and compare reader comprehension,
errors, task time and aggregate usage against a baseline. Include simple no-visual cases;
do not grade success by page count, keywords, pictures or the author's own approval.
