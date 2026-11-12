# Consumed pair: recorded evidence exposure

3 November 2026. Base directory (all suffixes below resolve here):
/Users/me/Documents/Codex/2026-10-26/agent-harness-v1/.harness-work/retrieval/completeness-pair

Packets: arm-A/source-packet.json and arm-B/source-packet.json.
Both are 32,918 bytes; SHA256 equals freeze.json's packet_sha256:
ced658c360fbd107623ec9dd5b5128293669067c1d2919481676df3473c260b4

Recorded streams and SHA256:
receipts-A/stdout.jsonl
ea2a41804feda4e5e2c58e57faabab2b70524c2fe782222114cac2362f21cbd4
receipts-B/stdout.jsonl
22f4868d035ee5b1ebb7777f68e0aca20048431ece175d4f1755cbe79f1a4eda

Each stream has one completed command_execution at JSONL line 5:
/bin/zsh -lc 'cat source-packet.json', exit_code 0.
Its decoded aggregated_output has 32,898 characters; UTF-8 encoding yields
32,918 bytes, exactly equal to its arm's complete packet bytes and the packet
SHA256 above. No truncation notice is present. This is byte equality of the
recorded tool output, stronger evidence than exit status or a length alone.
The inspection command parsed existing JSONL and compared bytes; exit 0 with
exact_packet_bytes=true for both arms. No trial was run or repeated.

Limits: the events contain no independent attestation of the exact internal
model context, downstream transport/compaction, attention, comprehension or use
of every span. Complete recorded output cannot prove complete model ingestion
or semantic coverage. The packet itself contains selected source windows, not
all originals. No answer regrade, effectiveness or original16 acceptance claim;
no model calls, input/default/gate edits or live changes performed here.
