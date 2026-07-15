#!/bin/bash
# ════════════════════════════════════════════════════════════
# 金股观测 — 本机每日定时更新 + 发布（由 launchd 在盘后调用）
# 链路: fetch_pool(腾讯 gtimg·跨平台) → data_pipeline → update_lhb(机游共振龙虎榜) → slim → 部署 GitHub Pages
# 注意:
#   - fetch_pool.py 用腾讯 gtimg 取 K线（东方财富 push2 在本机网络被屏蔽）。
#   - update_data.sh 内已接入 update_lhb.py，每日盘后自动补当日机游共振(龙虎榜)日历。
#   - 任意装有 Python+git 的 Mac/Windows/Linux 均可运行。
# ════════════════════════════════════════════════════════════
set -e
cd "/Users/samt/golden_stock_observer"
LOG="/tmp/goldenstock_update.log"
echo "[$(date '+%Y-%m-%d %H:%M')] ===== 开始每日更新 =====" >> "$LOG"

if bash update_data.sh >> "$LOG" 2>&1; then
  echo "[$(date)] ✓ update_data 成功" >> "$LOG"
else
  echo "[$(date)] ✗ update_data 失败，中止发布（详见 $LOG）" >> "$LOG"
  exit 1
fi

if bash github_pages_deploy.sh --no-fetch >> "$LOG" 2>&1; then
  echo "[$(date)] ✓ 已发布到 GitHub Pages" >> "$LOG"
else
  echo "[$(date)] ✗ 发布失败（详见 $LOG）" >> "$LOG"
  exit 1
fi

echo "[$(date)] 构建并发布钻石副站..." >> "$LOG"
if bash _build_diamond.py >> "$LOG" 2>&1; then
  # 失效 index stat 缓存，防止 racy-git：_build_diamond.py 写入与 git add 落在同一秒时，
  # git 按 stat 误判文件未变而漏提交数据更新（曾导致副站演化历史停在昨日）
  git -C diamond_site update-index --really-refresh 2>/dev/null || true
  git -C diamond_site add -A
  git -C diamond_site add -f output/golden_pool_*.json output/golden_pool_meta.json output/golden_pool_manifest.json
  if git -C diamond_site diff --cached --quiet; then
    echo "[$(date)] 钻石副站无新更改，跳过推送" >> "$LOG"
  else
    git -C diamond_site commit -m "数据更新: $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    git -C diamond_site push origin main >> "$LOG" 2>&1
    echo "[$(date)] ✓ 钻石副站已发布" >> "$LOG"
  fi
else
  echo "[$(date)] ✗ 钻石副站构建失败（详见 $LOG）" >> "$LOG"
fi
echo "[$(date)] ===== 完成 =====" >> "$LOG"
