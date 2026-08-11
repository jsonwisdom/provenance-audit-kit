# PUBLIC_REPLAY_PROTOCOL_v0.1

Shared protocol layer for replayable public-institution corpora.

This directory defines reusable acquisition, byte-integrity, versioning, knowledge-state, and witness boundaries. It must not contain institution-specific evidence.

```text
SOURCE BYTES
  -> GATE 1 / V01-V08
  -> CLAIMS
  -> POLICY GRAPH
  -> KNOWLEDGE STATE (L3.6)
  -> BATTLE RECEIPT
  -> OPTIONAL PUBLIC WITNESS
```

Core boundary:

```text
COMMON VERIFICATION PROTOCOL != COMMON INSTITUTIONAL AUTHORITY
```

No live corpus bytes belong here.
