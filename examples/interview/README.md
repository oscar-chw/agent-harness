# Interview demonstration

Open **guide.html** first. It contains the architecture, a five-minute run order,
observed results and expandable technical answers. It works offline.

## Run the actual demo

Requirements are Python 3.9+, Git and an existing agent-harness 3.0.0rc2 installation with
`lib/agent_harness`. No model account, internet connection or paid usage is used.
From this folder run the following command, choosing a new output folder each time.

```sh
python3 demo.py --output demo-run
```

If the installation is elsewhere, add `--runtime /path/to/agent-harness`.
The default is `HARNESS_HOME`, or `~/.agent-harness`.

Expect five PASS lines followed by DEMO PASS. Inspect `demo-run/demo-proof.json`,
`commands.json`, `reader-a.txt`, `reader-b.txt` and the generated project.
An existing output folder is refused. Every run retains its evidence.
Exported text normalizes fixture, owner-home and runtime paths to placeholders.
Process IDs, exit codes and assertion evidence remain in the receipt and logs.

The program reads installed code and creates a disposable project and separate
home under its output directory. It uses real CLI and MCP processes. The named
readers are software sessions. No native model is called. Native client settings,
real task boards and user memories are outside the demo's write scope.

## Explain what the interviewer is seeing

1. A writer publishes the shipping task and next action to a local SQLite board.
2. MCP reader A receives that state during initialization.
3. The real work-graph gate rejects a shipping-boundary bug and retains pending.
4. Reader B starts independently and receives the failure and next action.
5. A writer using an old task version is rejected. Current state survives.
6. The script applies the prepared fix. The same tests pass and the graph settles.
7. Reader B receives the changed board once. Its next unchanged boundary adds zero board bytes.

The code change is scripted so the transport and gate demonstration is repeatable.
An interviewer can inspect the tiny feature and unchanged tests directly.
Model reasoning quality is evaluated separately in the historical paired study.

## Optional native-model follow-up

A native follow-up requires a fresh temporary MCP connection whose working
directory is demo-run/project and whose HARNESS_HOME is demo-run/home/harness.
Its PYTHONPATH must resolve the existing runtime's lib directory. Use absolute
paths in that client's connection settings and keep its normal connection intact.
Project directory and harness home jointly identify the disposable board.

Then ask the model to inspect that board, state what passed, locate the dated
gate evidence and explain the next action. This optional client-specific setup
remains NOT_RUN. It uses included account quota. The deterministic receipt covers
the two fresh MCP processes invoked by demo.py. The guide includes a separate
historical native-model study with its own qualification scope.

## Files to bring

- guide.html for presenting and offline reading.
- architecture.svg for a sharp, editable visual and architecture.mmd for Mermaid.
- architecture.pdf for a one-page printable architecture when present.
- technical-notes.md for source-backed technical Q&A.
- demo.py and check_pack.py for the runnable demonstration and receipt checks.
- recorded-demo-proof.json and recorded-commands.json for the observed rehearsal.

The published release remains3.0.0rc2. Mac Studio and the research account passed
installed readback. MacBook rollout and broader self-learning efficacy remain open.
