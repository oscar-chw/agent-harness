# Literal parser: bounded static review, 29 October 2026

Verdict: **request changes before installation**. Static findings, not an observed
guard bypass. Direction3 remains the sole writer and FYP coordinates the approved
inert-test retry. This review ran no guard, fixture, denied command or workload.

## Read scope and binding

Read only the sanitized `REPAIR_REVIEW_PACKET_20261029.md` and
`PROPOSED_LITERAL_PARSER.patch` supplied by FYP. Patch SHA-256 actually read:
`fae7564930048771700efbf1e50ee178b5a4e4709fe1287cf59909875144db9a`.
The packet reports baseline `125ab126...78b6`, candidate `f08fa55b...e849`,
26 focused and 427 existing cases passed. I did not independently run or inspect
those cases, candidate bytes, downstream guard, or the additional wrapped review.
The latter remains **NOT_RUN**. No private session file or removed command was read.

## Concrete findings

1. **The accepted double-quote escape subset is wider than the promised argv
   equivalence.** In the `char == '\\'` branch, the next-character restriction
   applies only outside double quotes. Inside double quotes any escaped character
   is skipped, so escaped dollar/backtick and backslash-newline reach
   `shlex.split(posix=True)`. POSIX double-quote processing removes the backslash
   before dollar/backtick and removes backslash-newline; Python shlex does not
   implement that complete processing. For example, an env value written as
   `"VALUE=\$NAME"` should contain literal `$NAME`, without a backslash. The
   reconstruction can instead preserve that backslash. A double-quoted word
   interrupted by backslash-newline has the same problem. This is a static
   equivalence defect; no candidate verdict was observed here.
   Narrow repair: fall back on double-quoted backslash forms except the proven
   quote/backslash subset, or demonstrate a correct independent parser for each
   additionally supported form. Do not use shlex as its own equivalence oracle.

2. **Unrestricted `source.strip()` changes literal data before screening.** A
   trailing unquoted carriage return or nonbreaking space attached to an argument
   is not an ordinary POSIX space/tab delimiter. Python strip removes it before
   the scan, so the carriage-return rejection can be skipped and the final argv
   changed. Example fixture data: a quoted `env` word followed by an argument
   ending in U+000D or U+00A0. Preserve raw bytes for screening; any trimming must
   be limited to independently justified shell delimiters. Unsupported forms
   should retain the original conservative treatment.

3. **Wrapper safety remains unresolved by this patch alone.** Outer argv
   equivalence does not classify execution inside `env -S`/`--split-string`,
   shell/interpreter command arguments, SSH options or remote command strings.
   Test the existing known wrappers and an unknown remote wrapper; uncertain
   executable payloads must not become allowed just because the outer command
   word is now unquoted. The packet identifies this risk, but the necessary
   same-wrapper negative review has not run. Existing downstream checks being
   unchanged does not prove the newly accepted input set is safe.

## Narrow regression matrix for the sole writer

These are proposals only; no test string is executed by this review.

- Positive: fully quoted literal env, ordinary assignments, an assignment with
  spaces, empty literal arguments, quoted paths with spaces and an `env --`
  terminator. Assert complete expected argv, preserving empty words and bytes.
- Equivalence negatives: double-quoted escaped dollar/backtick, double-quoted
  backslash-newline, trailing unquoted CR/NBSP, unfinished quote/backslash,
  unquoted expansion/control/redirection, and reserved command words. Assert
  conservative fallback or the exact independently specified argv.
- Wrapper/option negatives: env split-string options, option operands and
  terminators, nested interpreter/shell payloads, known remote wrappers/options
  and an unknown remote wrapper. Reuse only the already authorized synthetic
  denied-payload fixtures; do not reconstruct removed session content.
- Contrast inert classifier fixture data with the same approved bytes in an
  executable command position. The classifier harness may pass strings only
  through JSON stdin to guard verdicts; it must never evaluate or execute them.
  Assert every required denial and fail the gate on a missing verdict or a test
  error. Printing verdicts is not an acceptance assertion.
- Preserve protected-path and dangerous-command checks, including argument
  boundaries and representations handled by existing cases. No blanket allowlist.

Approval of the exact inert classification retry remains distinct from approval
to install a security change. A local parser correction cannot override a
platform/PreToolUse denial. Installation requires the separately approved exact
change, a current baseline hash, actual installed checks and a verified rollback.

## Final boundary update (bridge-reported)

The FYP bridge reports that the ONE specifically approved clean equivalent inert
classification retry was submitted through normal exec_command and refused by
PreToolUse before execution. Receipt pointer:
`research/staging-guard-20261028/APPROVED_CLEAN_RETRY_REFUSAL_20261029.json`.
This review did not open or independently verify that receipt. No classifier
verdicts were produced; dynamic acceptance remains unverified. The approval is
consumed: no retry, re-encoding or alternate route. Installation is not authorized
by the refused test. Native proposal training remains held until a distinct
reviewed operator/security maintenance path is explicitly resolved.
