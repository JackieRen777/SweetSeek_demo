#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
echo "⚠️  restart-local-5050.sh 已废弃，统一转发到 5001。"
exec "$ROOT_DIR/scripts/maintenance/restart-local-5001.sh"
