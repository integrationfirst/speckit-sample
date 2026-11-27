#!/usr/bin/env bash
set -euo pipefail
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
EXT="$(dirname "$(dirname "$SELF")")"
export PYTHONPATH="$EXT/scripts${PYTHONPATH:+:$PYTHONPATH}"
exec uv run --no-project --quiet --with pyyaml python3 -m issue_flow "$@"
