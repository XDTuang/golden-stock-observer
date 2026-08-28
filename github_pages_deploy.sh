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
  GATE=$("$PYTHON" - "$DEPLOY/signals_full.json" <<'PY'
import json, sys, os
p = sys.argv[1]
if not os.path.exists(p):
    print("FAIL:deploy/signals_full.json 不存在，请先运行 update_data.sh"); sys.exit(1)
try:
    d = json.load(open(p, encoding="utf-8"))
    fr = d.get("freshness", {})
except Exception as e:
    print("FAIL:无法解析 deploy/signals_full.json: %s" % e); sys.exit(1)
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

# ── Step 2.5: 本机产物完整性闸门（2026-08-28 审计新增）──
# 背景：rebuild_html.py 由 index_template.html 全量重建页面，若补注链未跑完，
#       本机 agent 产物（投喂复盘卡片 + ai_synthesis 渲染块）会被静默抹掉后直接上线。
# 说明：此闸门不受 --force 影响 —— --force 只放行"旧数据"，不放行"覆盖本机产物"。
echo ""
echo "🔒 Step 2.5: 本机产物完整性校验（投喂卡片 / ai_synthesis 渲染块）..."
PROD_GATE=$("$PYTHON" - <<'PY'
import os, json
miss, warn = [], []
p = os.path.join("deploy", "index.html")
if os.path.exists(p):
    s = open(p, encoding="utf-8").read()
    if "drFeedReview" not in s:
        miss.append("投喂复盘卡片(drFeedReview)")
    if "ai_synthesis" not in s:
        miss.append("AI综合推演渲染块(ai_synthesis)")
else:
    miss.append("deploy/index.html 不存在")
fr = os.path.join("output", "feed_review_latest.json")
if os.path.exists(fr):
    try:
        d = json.load(open(fr, encoding="utf-8"))
        if not d.get("ai_synthesis"):
            warn.append("feed_review_latest.json 无 ai_synthesis（当日若无本机推演则属正常）")
    except Exception as e:
        warn.append("feed_review_latest.json 解析失败: %s" % e)
if miss:
    print("FAIL:" + "、".join(miss))
elif warn:
    print("WARN:" + "；".join(warn))
else:
    print("OK")
PY
)
echo "  闸门: $PROD_GATE"
if [[ "$PROD_GATE" == FAIL* ]]; then
  echo "  ❌ 校验未通过，已中止发布 —— 页面缺少本机产物，重建后未重注入。"
  echo "     请先补跑注入链："
  echo "       python inject_daily_review_tab.py && python inject_feed_review.py"
  exit 1
elif [[ "$PROD_GATE" == WARN* ]]; then
  echo "  ⚠️  提示（不阻断发布）"
fi

# ── Step 3: 同步 deploy/ → 仓库根目录（分支模式站点源）──
echo ""
echo "📁 Step 3: 同步 deploy/ → 根目录 ..."
cp -R "$DEPLOY/index.html" .
# ✅ 根 signals.json 用精简版（~100KB，不含 stocks）：前端 fetch 秒下、免截断；
#    stocks 由前端异步补拉 output/stocks.json（大文件单独走 CDN，带重试）。
#    signals_full.json 仍保留在 deploy/ 供 Step 2 新鲜度闸门使用。
if [ -f "$DEPLOY/signals.json" ]; then
  cp "$DEPLOY/signals.json" signals.json
fi
cp -R "$DEPLOY/lh_calendar.json" .
# 清空根 output/ 后仅复制前端真正 fetch 的精简文件，避免把 kline_raw 等重型文件带上 Pages
# 先保留门控数据（gate_scan.py 产出，slim_signals 不处理；否则会被下方 rm -rf 清掉）
cp -R output/gate_data.json "$DEPLOY/output/gate_data.json" 2>/dev/null || true
# 保留投喂复盘产物（本机 agent 的 feeds[] / ai_synthesis 唯一落点；slim_signals 不处理，
# 否则会被下方 rm -rf output 清掉 → 前端 fetch output/feed_review_latest.json 直接 404）
cp output/feed_review_*.json "$DEPLOY/output/" 2>/dev/null || true
# 保留日韩行情（fengle_kr.py 产出，slim_signals 不处理，同理会被 rm -rf 清掉）
cp output/kr_stocks.json "$DEPLOY/output/" 2>/dev/null || true
# 保留兜宝金钻分片（build_diamond_pool.py 产出，含 K线，供点开个股渲染；slim_signals 不处理）
cp output/golden_pool_*.json "$DEPLOY/output/" 2>/dev/null || true
cp output/golden_pool_meta.json "$DEPLOY/output/" 2>/dev/null || true
cp output/golden_pool_manifest.json "$DEPLOY/output/" 2>/dev/null || true
# 保留 gate_scan 缓存（kline_all.json ~34MB），否则次日全量重建会卡死
cp output/kline_all.json "$DEPLOY/output/kline_all.json" 2>/dev/null || true
# 保留 K线原始数据（周线金钻等复用），避免每次重新拉取 TOP800 K线
cp output/kline_raw.json "$DEPLOY/output/kline_raw.json" 2>/dev/null || true
# 2026-08-28 审计修复：原为 `rm -rf output` + `cp -R deploy/output .`，
#   一次性删除 60+ 文件会触发批量删除安全护栏，导致发布流程中断（已实际发生）。
#   根 output/ 已被 .gitignore 的 `/output/` 规则排除，重型文件（kline_raw/kline_all）
#   本就不会误入提交，因此无需清空 —— 改为覆盖式同步即可，语义等价且更安全。
mkdir -p output
cp -R "$DEPLOY/output/." output/
cp -R "$DEPLOY/build_manifest.json" .
touch .nojekyll
echo "  ✓ 已同步站点文件到根目录"

# ── Step 4: 提交并推送（GitHub Pages 直接服务分支根目录）──
echo ""
echo "🚀 Step 4: 提交并推送 ..."
# 失效 index stat 缓存，防止 racy-git 漏提交（与主站 history / 副站数据同理）
git update-index --really-refresh 2>/dev/null || true
git add -A
git add -f index.html signals.json lh_calendar.json \
  output/top10_history.json output/sector_flow.json output/national_team_etf.json \
  output/golden_diamond.json output/golden_diamond_history.json output/sector_golden_diamond_history.json \
  output/observation_pool.json \
  output/gate_data.json \
  output/report_analysis.json \
  output/event_calendar_*.json \
  output/golden_pool_*.json output/golden_pool_meta.json output/golden_pool_manifest.json \
  output/stocks.json \
  output/kr_stocks.json \
  output/feed_review_latest.json output/feed_review_*.json \
  output/sh_index_kline.json output/sz_index_kline.json output/cyb_index_kline.json output/kc50_index_kline.json output/hs300_index_kline.json \
  output/market_thermometer.json output/valuation_band.json output/vix_panel.json output/institutional_flow.json \
  deploy/output/market_thermometer.json deploy/output/valuation_band.json deploy/output/vix_panel.json deploy/output/institutional_flow.json \
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
