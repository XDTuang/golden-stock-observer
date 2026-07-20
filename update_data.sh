#!/bin/bash
# ════════════════════════════════════════════════════════════
# 兜金观测 — 一键数据更新（统一编排）
# 用法:
#   bash update_data.sh              # 交易日+盘后才会真正更新
#   bash update_data.sh --force      # 跳过交易日/盘后校验（手动强制）
#   bash update_data.sh --limit=500  # 自定义候选池规模
#
# 流程:
#   1. 闸门校验（非交易日 / 盘中 → 跳过，保证「发布的数据」是收盘后完整数据）
#   2. fetch_pool.py → 候选池 + 250日K线 + 信号计算（data_pipeline）
#   3. golden_diamond_scan.py → 金钻三子形态每日扫描（复用验证版引擎，产出 golden_diamond.json）
#   4. 辅助数据刷新（ETF / 板块 / 龙虎榜，best-effort，失败不阻断）
#   5. slim_signals.py → 精简 + 生成 fetch 版页面（单一构建路径，含 golden_diamond.json 复制）
# ════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

PYTHON="/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
FORCE=0
LIMIT=800

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --limit=*) LIMIT="${arg#*=}" ;;
    --no-pipeline) NO_PIPELINE="--no-pipeline" ;;
  esac
done

echo "═══ 兜金观测数据更新 ═══"

# ── 闸门：只在交易日且收盘后更新 ──
if [ "$FORCE" -eq 0 ]; then
  GUARD=$("$PYTHON" -c "from market_calendar import should_update_now; ok,reason=should_update_now(); print(('OK' if ok else 'SKIP')+':'+reason)")
  echo "  闸门: $GUARD"
  if [[ "$GUARD" == SKIP* ]]; then
    echo "  ℹ️  当前不适合更新（非交易日或盘中）。如需强制运行请加 --force"
    exit 0
  fi
else
  echo "  闸门: force 模式，跳过校验"
fi

echo ""
echo "📊 Step 1: 获取候选池 + K线 + 计算信号"
"$PYTHON" fetch_pool.py --limit "$LIMIT" ${NO_PIPELINE:-}

echo ""
echo "💎 Step 2: 金钻三子形态每日扫描（基于 kline_raw.json，复用验证版引擎）"
"$PYTHON" golden_diamond_scan.py || echo "  ⚠️  金钻扫描失败（跳过，不影响主流程）"

echo ""
echo "💾 Step 2.5: 金钻池快照追加进数据仓库（保留最近20交易日，供变动跟踪）"
"$PYTHON" build_gd_history.py --append || echo "  ⚠️  金钻池历史追加失败（跳过，不影响主流程）"

echo ""
echo "💠 Step 2.6: 门控扫描（pool + 板块前100·换手≥4%，复用金钻真值 + 缠论按门控）"
"$PYTHON" gate_scan.py --daily || echo "  ⚠️  门控扫描失败（跳过，不影响主流程）"

echo ""
echo "💠 Step 2.7: 生成兜宝金钻分片（主站 output/ + 钻石副站 diamond_site/output/，含 K线，供点开个股渲染主图/副图/四量图）"
"$PYTHON" build_diamond_pool.py || echo "  ⚠️  金钻分片生成失败（跳过，不影响主流程）"

echo ""
echo "💾 Step 2.8: 板块门控(板块前100·换手≥4%)金钻池快照追加进独立数据仓库（与 TOP800 跟踪互不干扰）"
"$PYTHON" build_sector_gd_history.py --append || echo "  ⚠️  板块门控金钻池历史追加失败（跳过，不影响主流程）"

echo ""
echo "📈 Step 3: 刷新辅助数据（ETF / 板块 / 龙虎榜，best-effort）"
"$PYTHON" fetch_national_team_etf.py 2>/dev/null || echo "  ⚠️  ETF 数据刷新失败（跳过）"
"$PYTHON" fetch_sector_flow.py 2>/dev/null || echo "  ⚠️  板块资金流刷新失败（跳过）"
"$PYTHON" fetch_sector_fund_flow.py 2>/dev/null || echo "  ⚠️  板块资金流(细分)刷新失败（跳过）"
"$PYTHON" update_lhb.py 2>/dev/null || echo "  ⚠️  机游共振(龙虎榜)日历刷新失败（跳过）"
bash update_calendar_js.py 2>/dev/null || echo "  ⚠️  日历JS模板刷新失败（跳过）"

echo ""
echo "🧹 Step 4: 精简数据 + 生成 fetch 版页面（单一构建路径）"
"$PYTHON" slim_signals.py

echo ""
echo "═══ 更新完成 ═══"
echo "📁 产出: index.html（fetch 版） + deploy/（精简版，可直接发布）"
echo "💡 本地预览: 浏览器打开 index.html"
echo "💡 发布上线: bash github_pages_deploy.sh"
