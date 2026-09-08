#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 观测股滚动推演 + 回测（独立轻量任务，与 update_data.sh 全量解耦）
# 何时跑：交易日 16:40（launchd com.goldenstock.backtest）
# 做什么：
#   1) derive_obs.py          → 归档当日 obs_deduce_auto_<T>.json
#   2) backtest_daily_review.py --auto  → 结算全部 T ≤ 昨日（T+1 已有实际）
#   3) 双写 deploy 镜像
# 为什么独立：update_data.sh(17:45) 全量 fetch_pool 重、易挂；回测 45s 内可完成
# ═══════════════════════════════════════════════════════════════
REPO="/Users/samt/golden_stock_observer"
PY="/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
cd "$REPO" || exit 1

LOG="logs/backtest_daily.log"
mkdir -p logs
echo "─── $(date '+%Y-%m-%d %H:%M') backtest_daily.sh 开始 ───" >> "$LOG"

echo "─── 1/3 derive_obs.py（归档当日观测股推演）───"
if "$PY" derive_obs.py >> "$LOG" 2>&1; then
  echo "  ✓ derive_obs 完成" >> "$LOG"
else
  echo "  ⚠️ derive_obs 失败（跳过，backtest 仍可跑历史）" >> "$LOG"
fi

echo "─── 2/3 backtest_daily_review.py --auto（结算 T-1）───"
if "$PY" backtest_daily_review.py --auto >> "$LOG" 2>&1; then
  echo "  ✓ backtest --auto 完成" >> "$LOG"
else
  echo "  ⚠️ backtest 失败（退出码 $?）" >> "$LOG"
  exit 1
fi

echo "─── 3/3 双写 deploy ───"
cp output/backtest_daily.json deploy/output/backtest_daily.json
A=$(md5 -q output/backtest_daily.json)
B=$(md5 -q deploy/output/backtest_daily.json)
if [ "$A" = "$B" ]; then
  echo "  ✓ deploy 镜像已同步 ($A)" >> "$LOG"
else
  echo "  ⚠️ md5 不一致 ($A vs $B)" >> "$LOG"
fi

echo "─── 4/4 V3 大盘结论回测（backtest_v3.py · meta 口径）───"
if "$PY" review_v3/backtest_v3.py >> "$LOG" 2>&1; then
  echo "  ✓ backtest_v3 完成（含 deploy 双写）" >> "$LOG"
else
  echo "  ⚠️ backtest_v3 失败（退出码 $?，不影响 obs 回测）" >> "$LOG"
fi

echo "✅ backtest_daily.sh 完成 $(date '+%H:%M')" >> "$LOG"
echo "" >> "$LOG"
