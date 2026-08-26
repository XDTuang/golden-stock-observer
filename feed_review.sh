#!/bin/bash
# 兜来米金融 · 每日投喂复盘（本地定时主跑）
# 流程: 归档投喂 → 复盘分析 → 推送主站
set -euo pipefail
BASE="/Users/samt/golden_stock_observer"
PY="/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
cd "$BASE"

echo "═══ 兜来米投喂复盘 $(date '+%Y-%m-%d %H:%M') ═══"
echo "⓪ 三星/海力士收盘价抓取（fengle.me NAVER 实时，回填每日复盘 2 板块）..."
"$PY" fengle_kr.py || echo "  ⚠️ 韩股抓取失败（继续）"
echo "① 归档投喂箱..."
"$PY" feed_archive.py || echo "  ⚠️ 归档异常（继续）"
echo "② 复盘分析..."
"$PY" daily_feed_review.py
echo "③ 推送主站 deploy/output..."
"$PY" push_to_site.py
echo "✅ 投喂复盘完成"
