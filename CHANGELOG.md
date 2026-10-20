# Changelog

## 3.0.0-rc.2 — 2026-10-20

- Fixed bounded Gateway stdout capture after an oversized frame: later chunks no longer grow the incomplete receipt beyond `MAX_FRAME_BYTES + 65536`.
- Revalidated the v3 Gateway, routing, skill surface, installer fixtures, Open Design, and Python regression gates.
- Completed the live Codex → Claude → Hermes rollout with installed hash/mode readback and rollback artifacts.
- Verified a real-provider no-write Gateway canary with controller acceptance and proof.
