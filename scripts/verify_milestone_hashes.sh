#!/usr/bin/env bash
set -euo pipefail

declare -A EXPECTED
EXPECTED[M-2026-000]="e039da02fd89bd6c3aa22289a34905116c5c953f118b031e766be3cef9a7cd01"
EXPECTED[M-2026-001]="de1a571969944790a362c7d56f681ce2a3c9d81741bc9ab462a3a82b928ae323"

FAIL=0

for MID in "${!EXPECTED[@]}"; do
  FILE="registry/milestones/${MID}.json"

  if [[ ! -f "$FILE" ]]; then
    echo "MISSING: $FILE"
    FAIL=1
    continue
  fi

  ACTUAL="$(python3 scripts/calc_hash.py "$FILE" | awk '/canonical_hash:/ {print $2}')"

  if [[ "$ACTUAL" != "${EXPECTED[$MID]}" ]]; then
    echo "DRIFT: $MID"
    echo "expected: ${EXPECTED[$MID]}"
    echo "actual:   $ACTUAL"
    FAIL=1
  else
    echo "$MID: MATCH"
  fi
done

exit "$FAIL"
