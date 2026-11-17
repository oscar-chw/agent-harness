# Node 5 — Execute bounded native iteration and require an earned improvement

plan: research-reasoning-20261117
gate: `python3 .harness-work/reasoning-eval/check-outcome.py`
ctx: (none)

## Attempt 2026-11-17T06:29:31Z — agent@redacted-host — 0s — exit 1

```
{"error": "frozen instrument, input or runtime changed", "promotion": "NOT_GRANTED", "status": "HOLD"}
```

## Attempt 2026-11-17T06:35:10Z — agent@redacted-host — 0s — exit 1

```
{"baseline_tokens": 149713, "candidate_tokens": 150194, "ceiling_policy": "Stop before the next call at the observed ceiling. An in-flight call can overshoot.", "consumed_calls": 12, "evidence": "NATIVE_RECEIPT_REPLAY", "holds": ["candidate_cost_increase", "no_strict_improvement"], "known_consumed_tokens": 299907, "orphan_receipts": [], "paired_quality_differences": [0, 0, 0, 0, 0, 0], "paired_token_differences": [99, 78, 45, 70, 100, 89], "partial_tokens_lower_bound": 0, "promotion": "NOT_GRANTED", "quality_difference_se": 0.0, "scope": "Six paired batches of authored closed-world decisions, fresh-thread upstream inference tokens including cached input and reasoning subsets once. Preparation, selection history, whole-project cost and general intelligence are unmeasured.", "status": "HOLD", "token_difference_se": 8.506533436783231, "uncertainty": "Six authored batch pairs, descriptive differences and standard errors only. No population confidence or generalization claim.", "unknown_attempts": [], "usage_complete": true}
```

## Attempt 2026-11-17T07:03:07Z — agent@redacted-host — 0s — exit 0

```
{"baseline_tokens": 155643, "candidate_tokens": 150194, "ceiling_policy": "Stop before the next call at the observed ceiling. An in-flight call can overshoot.", "consumed_calls": 12, "evidence": "NATIVE_RECEIPT_REPLAY", "holds": [], "known_consumed_tokens": 305837, "orphan_receipts": [], "paired_quality_differences": [0, 0, 0, 0, 0, 0], "paired_token_differences": [-884, -870, -913, -901, -908, -973], "partial_tokens_lower_bound": 0, "promotion": "NOT_GRANTED", "quality_difference_se": 0.0, "scope": "Six paired batches of authored closed-world decisions, fresh-thread upstream inference tokens including cached input and reasoning subsets once. Preparation, selection history, whole-project cost and general intelligence are unmeasured.", "status": "PASS_BOUNDED", "token_difference_se": 14.513020973518152, "uncertainty": "Six authored batch pairs, descriptive differences and standard errors only. No population confidence or generalization claim.", "unknown_attempts": [], "usage_complete": true}
```
