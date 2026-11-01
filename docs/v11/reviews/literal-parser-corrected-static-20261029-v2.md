# Corrected literal parser: static review v2, 29 October 2026

Disposition: the two earlier parser findings are addressed in the current diff.
**Full guard/wrapper safety and installation readiness are not established.**
Direction3 remains sole writer/test executor; Beast alone owns later admission
and queueing. This review executed no parser, classifier, retry or workload.

## Exact read scope and proof binding

Read the current sanitized patch, OPERATOR_HANDOFF_20261029.md,
PROJECT_PARSER_CORRECTION_VERIFIED_20261029.json, test_literal_parser.py and
check_literal_parser.py. No private session source, withdrawn command or unrelated
record was read. Actual file hashes:

- Patch: `96b0cf40ec19cae09a75fcdf56e739434a5a679e9da2e2dde62a541a6e589176`.
- Tests: `221a646613732a27eb7d3fef5dcc3d6546ed7f8ca72066e29e02f7294d4f4062`.
- Checker: `bc4f84399ad6d4dc10ebc5f8e551d829c9e7294b8020dcc14434e10610a1e330`.

The last two match the supplied receipt. That receipt names current candidate
`b701894d5c108c47ae97735143aba12c1b2558e6a96ac357ef7a951d6550a9ba` and
reports 14 parser-only tests (8 case, 3 integration, 1 property, 2 eval), with
30 generated examples and two retained old-parser controls. I did not read/hash
the complete candidate guard or independently run these tests. The old f08f
26+427 passes are not acceptance evidence for b701. Current full-guard and
wrapped-negative acceptance remain NOT_RUN per this receipt.

## Findings

1. **Previous fixes confirmed at source level.** Raw input is preserved rather
   than stripped. Double-quoted backslashes now admit only quote/backslash;
   escaped dollar/backtick and backslash-newline fall back. The new cases name
   these regressions, including CR/NBSP. No additional unsafe parser acceptance
   was established in this bounded read. This is not a proof of the whole guard.

2. **Receipt binding still needs a frozen subject.** check_literal_parser.py
   hashes candidate/tests/checker after tier execution, but does not capture and
   compare their hashes before/through the run or test immutable copies. Each
   normalize call rereads the candidate. A concurrent edit could therefore make
   one final hash appear to qualify tests run on different bytes. No such edit
   was observed here. Before acceptance, pin these inputs before tests and verify
   unchanged afterward (or test immutable copies); a mid-run mutation control
   should fail the gate. Current test/checker hash agreement alone is insufficient.

3. **The printf oracle proves output bytes, not every argv boundary.** Fixed
   `%s` concatenates operands: distinct multi-argument lists and empty arguments
   can yield the same output. The empty-word lexical assertion helps but does
   not close this gap. Add harmless multiword/empty-argument cases with an
   independent argument count and unambiguous boundaries, such as fixed NUL
   framing for a known nonempty argument list. No dynamic fixture execution is
   proposed or performed by this reviewer.

4. **Wrapper/protected-path safety is still a separate acceptance condition.**
   The pure tests do not exercise env options/operands/terminators or split-string
   reinterpretation, nested interpreters, known remote wrappers/options, unknown
   remote wrappers, or protected-path denial behavior. Keep these current-hash
   tests required. Treat uncertain inner execution conservatively. A missing,
   errored or printed-only verdict cannot satisfy an asserted deny condition.
   Use only the approved synthetic fixtures; never reconstruct the removed text.

## Authority and operational lesson v2 (inactive)

The earlier one-shot submission remains consumed/refused. The renewed explicit
maintenance authorization is a distinct supported request, not permission to
bypass that denial or disable protections. Direction3 must resolve its exact
action under normal review; a fresh denial stops that action. This reviewer
does not repeat tests, install, create another queue or grant GPU admission.

Do not repeatedly ask for an unchanged action already covered by a valid current
approval; equally, do not reuse a consumed approval or transfer a parser-only
pass to another candidate hash. Record the precise action/source/approval state.
Only genuine full current-guard and wrapper acceptance, allowed maintenance,
baseline backup/hash verification and installed checks/rollback can establish
repair readiness. Beast then performs fresh admission and the registered queue/
canary path. No promise of issue-free future training or autonomous learning is
made by this note; no active skill or permission rule changed.
