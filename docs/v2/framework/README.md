# Framework contract for v2 integration

2 November 2026. Design/reconciliation deliverable; no runtime, installation or
native permission change. Root owns `plan/v2-completion.md` and qualification.

- [Runtime contract](runtime-contract.md): authority, correlation, joins,
  recovery, ownership and coordination. `CURRENT` describes inspected source;
  `REQUIRED` is an acceptance obligation; `PROPOSED` is unimplemented glue.
- [Capability matrix](capability-matrix.json): independent source,
  locally-installed and native-qualification axes; missing behavior stays explicit.
- [Acceptance cases](acceptance-cases.json): executable-oracle specifications
  and controls for root implementation. A specified case is not a passed test.
- [Verification](verification.json): source identities, commands actually run,
  results and limits for this bounded worker output.

Done for this worker means the matrix parses, has unique IDs and valid local
source references, every case maps to a capability, and the contract covers
all assigned seams. Source regressions may support the existing mechanisms;
they do not implement the proposed correlation manifest or qualify native use.
The original root requirements gate remains separate.

Existing reuse checked: `bin/harness`; `workgraph/plan.py` and `versions.py`;
`operational_state.py`; `method_control.py`; `handoff.py`; `permission_profiles.py`;
`content/skills/work-loop/recovery.md`; session-memory/work-loop/standards skills;
`docs/v2/second-brain-contract.md`; retained dev2 install/native evidence.
No additional orchestration engine or external package is needed for the
specified DAG, retry, join and file-handoff cases. Hierarchical communicating
statecharts would require a demonstrated unmet case and separate authority.
