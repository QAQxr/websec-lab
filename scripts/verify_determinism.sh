#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

./scripts/reset.sh >/dev/null
snapshot_one="$(docker compose exec -T web python -m backend.seed_snapshot)"

./scripts/reset.sh >/dev/null
snapshot_two="$(docker compose exec -T web python -m backend.seed_snapshot)"

if [ "${snapshot_one}" != "${snapshot_two}" ]; then
    echo "deterministic seed snapshot mismatch" >&2
    exit 1
fi

echo "Deterministic seed verification passed."
