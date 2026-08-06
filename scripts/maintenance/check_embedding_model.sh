#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "❌ 未找到 .env，请先配置项目环境变量"
  exit 1
fi

EMBED_MODEL_NAME=$(grep -E '^EMBED_MODEL_NAME=' .env | tail -n1 | cut -d'=' -f2-)
EMBED_MODEL_SOURCE=$(grep -E '^EMBED_MODEL_SOURCE=' .env | tail -n1 | cut -d'=' -f2-)
EMBED_MODEL_SOURCE=${EMBED_MODEL_SOURCE:-modelscope}
DEFAULT_MODEL="BAAI/bge-small-zh-v1.5"

echo "=========================================="
echo "  嵌入模型完整性检查"
echo "=========================================="
echo "EMBED_MODEL_SOURCE=$EMBED_MODEL_SOURCE"
echo "EMBED_MODEL_NAME=$EMBED_MODEL_NAME"

if [ -z "${EMBED_MODEL_NAME}" ]; then
  echo "❌ EMBED_MODEL_NAME 为空"
  echo "建议: 在 .env 中设置 EMBED_MODEL_NAME=$DEFAULT_MODEL"
  exit 1
fi

print_fix_commands() {
  cat <<'EOF'
一键修复（逐行执行）:
source .venv/bin/activate
pip install -U modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
sed -i '' 's|^EMBED_MODEL_NAME=.*|EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5|' .env
if grep -q '^EMBED_MODEL_SOURCE=' .env; then
  sed -i '' 's|^EMBED_MODEL_SOURCE=.*|EMBED_MODEL_SOURCE=modelscope|' .env
else
  echo 'EMBED_MODEL_SOURCE=modelscope' >> .env
fi
./scripts/maintenance/rebuild-index.sh 10
python - <<'PY'
from app import app
c=app.test_client()
r=c.get('/api/health')
print(r.status_code)
print(r.get_json().get("components", {}).get("embedding_model"))
PY
EOF
}

# 本地目录模式: 必须有权重文件
if [ -d "$EMBED_MODEL_NAME" ]; then
  if [ -f "$EMBED_MODEL_NAME/model.safetensors" ] || [ -f "$EMBED_MODEL_NAME/pytorch_model.bin" ]; then
    echo "✅ 本地模型目录完整（检测到权重文件）"
    exit 0
  fi

  echo "❌ 本地模型目录存在，但权重文件缺失"
  echo "缺少: model.safetensors 或 pytorch_model.bin"
  print_fix_commands
  exit 2
fi

# 模型名模式: 尝试检查 ModelScope 本地缓存
if [ "$EMBED_MODEL_SOURCE" = "modelscope" ]; then
  CACHE_DIR="$ROOT_DIR/models/modelscope_cache/$EMBED_MODEL_NAME"
  if [ -f "$CACHE_DIR/model.safetensors" ] || [ -f "$CACHE_DIR/pytorch_model.bin" ]; then
    echo "✅ ModelScope 缓存已存在权重: $CACHE_DIR"
    exit 0
  fi
  echo "⚠️ 当前为模型名模式，尚未检测到本地缓存权重"
  echo "首次运行重建时会自动下载到: $CACHE_DIR"
  echo "建议执行: ./scripts/maintenance/rebuild-index.sh 10"
  exit 0
fi

echo "ℹ️ 当前为模型名模式（source=$EMBED_MODEL_SOURCE）"
echo "建议确认网络可达并执行: ./scripts/maintenance/rebuild-index.sh 10"
