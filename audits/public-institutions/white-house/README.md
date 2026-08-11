# White House Public Replay Namespace

Administration-aware public knowledge replay lives here.

Corpus identity is interval-based, not administration-count based.

```text
white-house/
  administrations/
    WH_<president-number>_<NAME>_<start-date>_<end-date>/
```

Example identifiers:

```text
WH_32_FDR_1933-03-04_1945-04-12
WH_47_TRUMP_2025-01-20_
```

Each interval corpus independently owns:

```text
scope/
corpus/raw/
manifests/
receipts/gate1/
knowledge/
witnesses/
```

Replayability is scope-bound:

```text
REPLAYABLE(A,S) iff captured corpus C_A(S) exists and GATE1(C_A) = PASS
```

Knowledge divergence does not by itself establish contradiction, supersession, violation, or intent.
