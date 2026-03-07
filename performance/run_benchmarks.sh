#!/usr/bin/env bash
# Run performance benchmarks manually (not in CI).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

cd "${ROOT_DIR}"

echo "Running performance benchmarks..."
export STORAGE_MODE=memory
export API_KEY=dev-api-key

python -m pytest performance/ \
  --benchmark-only \
  --benchmark-sort=mean \
  --benchmark-columns=min,max,mean,stddev,rounds,iterations \
  -v

echo "Benchmarks complete."
