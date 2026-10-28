# v1.1 development checkpoint — 28 October 2026

This is a runnable development checkpoint, not a v1.1 production release or
proof of autonomous improvement. Existing shared memory and the installed
package are preserved; the separately authorized local discovery timer is active.

## Completed and verified

| Capability | Evidence and scope |
| --- | --- |
| Four-family registry | Exact Luna/Terra/Sol/Astra IDs and supported efforts observed in the local client cache. Missing/unsupported pairs hold. Public vendor guidance is cited in DEVELOPMENT.md; local performance remains unmeasured. |
| Routing integration | A held profile resolves through the existing quick/standard/deep/review resolver. It does not overwrite live settings or enable automatic progression. |
| Daily discovery | Two approved official sources, two fetches maximum, 256 KiB per source, 12-second fetch process deadline, no model calls. Changed sources create proposals; no code or skill activation. |
| Local scheduler | User-scoped macOS launchd enable/readback/disable/reenable passed. Native job exit 0; interval 86,400 seconds. Frozen runner identity checked against final source and its pinned manifest. |
| Rotation after 31 hot rows | Exact older receipts are compressed, fsynced, read back and hash-bound before hot copies are removed. Latest attempt and successful baseline stay hot. Rollover tests recover every original receipt; corrupted archives and capacity exhaustion stop before fetching/deleting hot evidence. |
| Bounded retention | 32 MiB archive limit, 1 MiB encoded source-payload limit. Capacity exhaustion returns visible RETENTION_HOLD. History exposes archive pointers and hashes. |
| Preserved lifecycle | Discovery audit records unchanged across native runner refresh and disable/reenable. Previous bundles and disabled plists retained for rollback. No native login/guard/permission changes. |
| Skill lifecycle contracts | Existing prepare/draft/inspect/correct, stale-source refusal, withdrawal and caller-score rejection remain covered. Local frozen-case/binder receipts remain held and cannot silently activate advice. |

Final frozen-source gate: `bash scripts/check.sh` **exit 0** — **1,471 passed,
2 skipped, 2 xfailed**; privacy scan and disposable installation demo passed.
Focused final discovery/scheduler tests: **33 passed**. Related routing/procedure
independence gate: **53 passed**. Ruff and diff whitespace checks passed.
The earlier 1,455/1,466/1,468 results are historical iterations, not the final result.

Independent static review found fetch-deadline, malformed-cache, disabled-state,
runner-drift and absent-service-readback issues. Each was reproduced and fixed.
The final archive-pointer finding was refuted by current code and a rollover-to-CLI
assertion; it was withdrawn. Root owns the command results above.

## Measured pilot and budget stop

One native subscription call requested Luna/low on one synthetic extraction task:
correct response, zero tools, 6.736 seconds, provider-reported 26,461 input + 54
output tokens (26,515 total), zero cached input tokens. No process group remained.
The second call was skipped because the first exceeded the declared **soft**
20k observed-task-token threshold. The threshold is observable after completion,
not an enforceable pre-call token cap. No further model calls are authorized in
this closure slice.

The native lifecycle trace exposed no effective-model/provider identity. Therefore
this is a requested-pair task canary, not a verified model comparison, learning
transfer result or proof that the harness caused the input overhead. Remaining
subscription tokens are UNKNOWN; percentages were not converted into tokens.

## Held requirements and concrete missing inputs

| Requirement | Current disposition and missing input |
| --- | --- |
| Automatic discovery-to-skill improvement | Source changes are proposal evidence, not independent successful task episodes. Need a selected lawful experience corpus with task/source bindings and at least two relevant independent episodes before drafting a reusable method from it. No automatic skill generator is claimed complete. |
| Sandboxed promotion | Local binder computes hashes/scores, but `procedures.change` deliberately rejects promotion. A trusted native actor/oracle separation, effective-model/usage-to-artifact provenance, independently frozen grader and held-out comparison are not available. The native trace's missing identity fields are a concrete observability gap. Caller-written scores cannot fill it. |
| Promotion connector | The production activation path remains held/unimplemented pending that verifiable boundary and receipt contract. Existing active-state consumption/withdrawal fixtures are not proof that a real candidate was promoted. |
| Matched routing/learning gain | No matched baseline/assisted native pair completed. A future explicitly budgeted campaign needs reliable usage attribution and frozen unseen tasks; quality must be no worse per case and aggregate tokens no greater than baseline. No ranking or token-saving claim is established here. |
| All-link content research | All 108 candidates/110 variants retained. Fifteen individual links attempted in three bounded Luna-low batches; access failed, so no new full content was read. Thirteen items have prior-reference matches, three overlapping attempts; 83 have neither an attempt nor a prior-reference match. Untouched items are NOT_RUN, not known inaccessible. A Terra/medium synthesis used existing evidence only. Further broad intake is suspended for this closure slice. |
| Other devices / Windows scheduler | Registry/core code is portable; native scheduler implementation/readback is macOS only. No all-device rollout, Windows scheduling or logged-out/asleep daily execution is claimed. |

## Retention renewal and rollback

The old unconditional 31-run stop is removed. At archive capacity the registered
timer exits nonzero with RETENTION_HOLD before another fetch; it keeps all evidence.
Check `daily-discovery --history` and scheduler status. Disable the timer, retain a
verified database backup plus archive files/manifest, and agree a retained export
location before a tested renewal/migration. There is no automatic purge or blind
`--renew` command. Do not simply delete archive files to make a capacity check pass.

For local scheduler rollback, use `daily-discovery --disable-schedule`; this unloads
and verifies absence, archives the owned plist and keeps audit/bundles. A previous
retained plist pins its matching runner manifest. Re-enabling a previous bundle
requires its own hash/readback verification; never silently point a job at mutable
working code. The ordinary installed package was not upgraded by this checkpoint.
