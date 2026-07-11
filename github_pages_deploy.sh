#!/bin/bash
# ════════════════════════════════════════════════════════════
# 金股观测 — GitHub Pages 部署（分支模式：发布 deploy/ 到仓库根目录）
# 用法: bash github_pages_deploy.sh [--force] [--no-fetch]
#   --force    跳过数据新鲜度闸门
#   --no-fetch 不重新抓取，直接发布现有 deploy/（仅重新发布时用）
#
# 发布模型:
#   - GitHub Pages 直接服务分支(main)根目录
#   - 构建产物在 deploy/，发布时同步到根目录（index.html/signals.json/output/...）
#   - 根目录站点文件被 .gitignore 忽略，仅由本脚本 -f 强制发布，避免误提交本地 36MB 全量
# ════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

PYTHON="/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
DEPLOY="deploy"
FORCE=0
NOFETCH=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --no-fetch) NOFETCH=1 ;;
  esac
done

# ── Step 1: 构建（含数据更新 + 精简 + 生成 fetch 版页面）──
if [ "$NOFETCH" -eq 0 ]; then
  echo "📊 Step 1: 更新并构建站点产物（deploy/）..."
  # 透传 --force 给 update_data.sh（绕过交易日闸门，用于非交易日补发）
  if [ "$FORCE" -eq 1 ]; then
    bash update_data.sh --force
  else
    bash update_data.sh
  fi
else
  echo "ℹ️  Step 1: 跳过抓取，重建现有 deploy/"
  "$PYTHON" slim_signals.py
fi

# ── Step 2: 新鲜度 / 完整性闸门 ──
echo ""
echo "🔍 Step 2: 发布前校验（新鲜度 + 完整性）..."
if [ "$FORCE" -eq 0 ]; then
  GATE=$("$PYTHON" - "$DEPLOY/signals.json" <<'PY'
import json, sys, os
p = sys.argv[1]
if not os.path.exists(p):
    print("FAIL:deploy/signals.json 不存在，请先运行 update_data.sh"); sys.exit(1)
try:
    d = json.load(open(p, encoding="utf-8"))
    fr = d.get("freshness", {})
except Exception as e:
    print("FAIL:无法解析 deploy/signals.json: %s" % e); sys.exit(1)
stocks = d.get("stocks", [])
if len(stocks) < 50:
    print("FAIL:股票数量异常(%d)，疑似抓取不完整" % len(stocks)); sys.exit(1)
if not fr.get("is_fresh"):
    print("STALE:数据不新鲜 status=%s latest=%s expected=%s" % (
        fr.get("status"), fr.get("latest_data_date"), fr.get("expected_date")))
    sys.exit(2)
print("FRESH:latest=%s, stocks=%d" % (fr.get("latest_data_date"), len(stocks)))
PY
)
  echo "  闸门: $GATE"
  if [[ "$GATE" == FAIL* ]] || [[ "$GATE" == STALE* ]]; then
    echo "  ❌ 校验未通过，已中止发布（避免把过期/不完整数据上线）。"
    echo "     若确认要重新发布旧数据，可加 --force。"
    exit 1
  fi
else
  echo "  闸门: force 模式，跳过新鲜度校验"
fi

# ── Step 3: 同步 deploy/ → 仓库根目录（分支模式站点源）──
echo ""
echo "📁 Step 3: 同步 deploy/ → 根目录 ..."
cp -R "$DEPLOY/index.html" .
cp -R "$DEPLOY/signals.json" .
cp -R "$DEPLOY/lh_calendar.json" .
# 清空根 output/ 后仅复制前端真正 fetch 的 3 个精简文件，避免把 kline_raw 等重型文件带上 Pages
rm -rf output
cp -R "$DEPLOY/output" .
cp -R "$DEPLOY/build_manifest.json" .
touch .nojekyll
echo "  ✓ 已同步站点文件到根目录"

# ── Step 4: 提交并推送（GitHub Pages 直接服务分支根目录）──
echo ""
echo "🚀 Step 4: 提交并推送 ..."
git add -A
git add -f index.html signals.json lh_calendar.json \
  output/top10_history.json output/sector_flow.json output/national_team_etf.json \
  output/golden_diamond.json output/golden_diamond_history.json \
  build_manifest.json .nojekyll
if git diff --cached --quiet; then
  echo "  无新更改需要提交"
else
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
  git commit -m "数据更新: $TIMESTAMP"
  echo "  ✓ 已提交"
fi
git push origin main
echo "  ✓ 已推送"

PAGE_URL="https://xdtuang.github.io/golden-stock-observer/"
echo ""
echo "═══ 部署完成 ═══"
echo "🌐 访问地址: $PAGE_URL"
echo "⏱️  GitHub Pages 通常在推送后数十秒自动更新"
echo "💡 后续每次数据更新: bash github_pages_deploy.sh"
