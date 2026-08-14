#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/external-benchmarks/ToolSandbox"
COMMIT="165848b9a78cead7ca7fe7c89c688b58e6501219"

if [[ ! -d "$DEST/.git" ]]; then
  mkdir -p "$(dirname "$DEST")"
  git clone https://github.com/apple/ToolSandbox.git "$DEST"
fi

git -C "$DEST" fetch --all --tags
git -C "$DEST" checkout --detach "$COMMIT"
actual="$(git -C "$DEST" rev-parse HEAD)"
[[ "$actual" == "$COMMIT" ]] || {
  echo "ToolSandbox commit mismatch: expected $COMMIT, got $actual" >&2
  exit 1
}
echo "ToolSandbox ready at $actual"

