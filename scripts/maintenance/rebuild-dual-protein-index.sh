#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo "❌ 未找到 .venv，请先创建并安装依赖"
  exit 1
fi

source .venv/bin/activate

echo "=========================================="
echo "  重建 Dual-Protein 索引（单命令）"
echo "=========================================="
echo "项目目录: $ROOT_DIR"
echo "文献目录: $ROOT_DIR/Dual_Protein_related_paper/papers"
echo "索引目录: $ROOT_DIR/storage_dual_protein"
echo ""

python - <<'PY'
from app import dual_protein_rag

print("[1/2] 开始重建 dual-protein 索引...")
ok = dual_protein_rag.rebuild_index()
print("rebuild_ok=", ok)
print("stats=", dual_protein_rag.get_stats())
if not ok:
    raise SystemExit(1)
PY

python - <<'PY'
from app import app
c = app.test_client()
r = c.get('/api/dual-protein/health')
print("[2/2] dual-protein health:", r.status_code, r.get_json())
if r.status_code != 200:
    raise SystemExit(1)
PY

python - <<'PY'
from app import app
c = app.test_client()
_ = c.post('/api/dual-protein/init')
r = c.post('/api/dual-protein/ask', json={
    "question": "请总结卵白蛋白与溶菌酶相互作用机制",
    "similarity_threshold": 0.2,
    "max_results": 10,
})
print("[3/3] dual-protein ask smoke:", r.status_code)
try:
    data = r.get_json() or {}
except Exception:
    data = {}
if r.status_code != 200 or not data.get("success", False):
    print("❌ 冒烟测试失败:", data)
    raise SystemExit(1)
refs = data.get("references", [])
print("✅ 冒烟测试通过，references_count=", len(refs))
PY

echo ""
echo "✅ Dual-Protein 索引更新完成"
echo "可访问: http://127.0.0.1:5001/dual-protein"
