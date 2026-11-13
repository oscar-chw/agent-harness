# Delivery practices for GitHub and development

Reviewed against the linked primary documentation on13November2026. Use the repository's actual stack, supported versions and existing commands. The checks below are selected by the change and its failure modes. Small edits can use a small path.

## What the harness currently supplies

| Area | Current mechanism | Evidence boundary |
|---|---|---|
| Coding and tests | work-loop, production-code, write-tests-first, standards | Installed guidance and tested tooling; model adherence needs behavioral checks |
| Review | Fresh-context review guidance and code-bound review gate | Findings, artifact binding and gate result have separate checks |
| Task ownership | Shared board, graph claims, checkpoints and dated gate evidence | Local project coordination; external side effects need their own ownership control |
| CI | Python3.9/3.12 tests, Ruff, secret scanning and an isolated demo in this repository | Workflow execution is checked per commit |
| Ticket, branch and PR conventions | This on-demand guide and the examples below | Documentation; automatic issue/PR creation stays within the user's authorization |
| Branch protections and deployment approvals | Repository and environment settings | Inspect actual settings before claiming enforcement; the harness grants no new permission |
| Other languages | Stack selection below | Examples require adaptation and execution in the target repository |

Repository settings readback on13November2026 returned `Branch not protected` for main and an empty ruleset list. The publication process waits for CI explicitly. Repository-level required-check and reviewer enforcement remains unconfigured. Repository merge policy is a separate configurable control.

## Select the amount of process

- A tiny correction needs its reproduction or targeted check and a readable diff.
- A material change needs acceptance criteria, task ownership, affected tests and review.
- Public APIs, authentication, money, data migrations or deployments need the relevant integration, permission, compatibility and recovery checks.
- A new issue is useful for ownership, discussion or work that outlives the current change. A routine change can link an existing task or describe its acceptance directly in the PR.

These are engineering choices. A checklist item contributes only when its failure would matter.

## A complete change

1. **Define the request.** Record user outcome, acceptance, affected surface, constraints and evidence. Separate confirmed requirements from assumptions.
2. **Recover the project.** Read existing issue/task state, contribution rules, manifests, lockfiles, workflow files and supported runtime versions. Identify the current owner before parallel work.
3. **Make the change.** Use a scoped branch, reproduce the defect where applicable, preserve unrelated work, and keep the implementation readable. Add a migration or compatibility path when old data/callers need it.
4. **Verify the outcome.** Run relevant unit, integration, property or end-to-end checks, plus configured static checks. A compiler error, missing tool or empty collection is an explicit failure or unrun prerequisite.
5. **Review the PR.** Explain purpose, behavior, evidence, risks and recovery. Link the actual issue when one exists. Resolve review findings with reproductions and current checks. Validate changes made during review.
6. **Admit and merge.** Inspect checks on the exact current head/merge candidate. Required checks, ownership reviews and branch rules are repository settings. A local pass alone cannot settle those requirements.
7. **Release and observe.** Build once, identify the artifact, verify installation/runtime entrypoints, exercise the actual user flow, inspect operational signals and retain a working recovery route. Release notes state compatibility changes and known limits.

GitHub supplies PR templates, issue linking, code owners, protected branches and rulesets for these conventions. Choose settings that fit the repository's ownership and risk. [GitHub PR standardization](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests)

## Choose checks for the stack

Prefer the project's checked-in commands and lockfile. The examples describe a starting set and grant no authority to install arbitrary dependencies or modify production systems.

| Stack | Existing project signals | Candidate checks |
|---|---|---|
| Python | pyproject.toml, pytest configuration, dependency lock, supported Python range | Configured formatter/linter, selected type checker, pytest, package build/install smoke, supported-version matrix |
| JavaScript / TypeScript | package.json scripts, package-manager lock, runtime/version declarations | Frozen-lock install, configured lint/type checks, unit/integration tests and production build; browser/accessibility checks for UI changes |
| Rust | Cargo.toml, Cargo.lock, rust-toolchain.toml, feature flags | cargo fmt check, configured Clippy, cargo test, feature/platform combinations relevant to the supported surface |
| Go | go.mod, go.sum and supported Go version | Formatting/static checks, go test ./..., relevant integration tests; race detector for supported concurrent code paths |
| C / C++ | CMake/presets or existing build system, compiler targets and test registration | Warnings/static analysis, build, CTest or the configured runner; supported sanitizers for memory/concurrency risk |
| SQL / database | Migration framework, engine/version, schema constraints and representative fixtures | Forward migration in an isolated database, constraints, old/new application compatibility, query plans and recovery/rehearsal appropriate to the engine |
| Infrastructure | IaC and deployment manifests, policy and environment definitions | Validation, plan/diff, policy checks, limited integration/staging checks, readback and recovery within existing permissions |
| AI / research | Frozen data/task split, model/tool/context identity and evaluator | Independent case outcomes, held-out leakage controls, complete measured overhead, failure retention and confidence/variance assessment |

Set runtime versions explicitly in CI and use the repository's package scripts and dependency workflow. TypeScript's noEmit supports type-checking separately from output generation. [Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), [Node.js CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs), [TypeScript noEmit](https://www.typescriptlang.org/tsconfig/noEmit.html)

Test collection, selected features and database behavior affect what a pass means. Cargo supports unit/integration testing. CTest can reject an empty run with --no-tests=error. Schema changes require engine-specific care, including locks, table rewrites, defaults and constraints. [pytest invocation](https://docs.pytest.org/en/stable/how-to/usage.html), [Cargo tests](https://doc.rust-lang.org/cargo/commands/cargo-test.html), [Go tests](https://go.dev/doc/tutorial/add-a-test), [CTest](https://cmake.org/cmake/help/latest/manual/ctest.1.html), [PostgreSQL schema changes](https://www.postgresql.org/docs/current/ddl-alter.html)

## CI/CD controls

- Give CI tokens only the permissions required by the job. Treat fork code, PR titles and other event content as untrusted input.
- Pin reviewed actions to full commit SHAs, or an independently verified supported dependency-lock mechanism. Updating a pin still requires compatibility and workflow checks.
- Keep privileged release/deployment contexts separate from untrusted PR execution. Review any privileged trigger before checking out and running contributor code.
- Reproduce dependencies from the project's lock or constraints. Review dependency and tool updates through the same checks as other changes.
- Preserve failed tests and meaningful skips. Give required checks stable, unambiguous identities and inspect the exact commit they qualify.
- Cache only rebuildable data with appropriate trust separation. Retain artifacts and reports needed to diagnose a failure.
- A deployment needs artifact identity, target configuration, health/readback checks and recovery. Keep sensitive environments and secrets within their existing authorization boundary.

GitHub recommends least-privilege tokens and immutable action references, and documents the hazards of privileged workflows executing untrusted code. [Secure workflow use](https://docs.github.com/en/actions/reference/security/secure-use)

## Small draft templates

### Task or issue

```text
User outcome
Current behavior and reproduction
Required behavior and acceptance check
Affected surface, constraints and consequential unknowns
Owner, dependencies and next action
```

### Pull request

```text
Purpose and linked task
Behavior changed
Verification commands, results and relevant unrun checks
Compatibility/data/security implications when applicable
Deployment and recovery when applicable
```

### Release record

```text
Source revision and artifact digest
Checks bound to that revision/artifact
Target, installation and actual runtime readback
User-flow result and operational observations
Recovery route and known limits
```

## Freshness and adoption

The guide is a dated source-backed reference. Before changing a repository's toolchain, action versions, security policy or production workflow, check the actual versioned documentation and local constraints. Changes enter through the relevant tests and review. A reference update supplies guidance; improved model performance still needs its own evaluation.

## Pending CI hardening

The current repository workflows still reference action tags. A locally checked patch pins the existing reviewed action revisions to full SHAs and adds a corresponding test. GitHub rejected publication because the OAuth connection lacks workflow scope. That patch and its passing local test are retained separately. This documentation update preserves the existing workflow configuration and records the pending improvement.
