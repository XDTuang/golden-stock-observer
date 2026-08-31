#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 实时盯盘 · 本地兜底（launchd 每 30 分钟驱动）
# ───────────────────────────────────────────────────────────
# 背景：GitHub Actions 的 schedule 触发器不稳定（官方已知：
#       触发可能延迟数十分钟甚至整个上午静默跳过，如 2026-08-27），
#       导致线上 realtime.json 盘中不更新。
# 本脚本作为本地兜底：与云端 realtime-monitor.yml 互补，
#       谁先成功提交都一样（同仓库同文件，按时间戳最新生效）。
#
# 流程:
#   1. fetch_realtime.py 抓取 + 计算五层信号（内部按 A股状态机拦截：
#      非交易日 / 未开盘 / 午休 / 收盘 → 不写文件不提交）
#   2. realtime.json 有变化才 commit + push（避免空提交）
#   3. 与云端 Actions 并发安全：无锁竞争，git push 幂等
# ═══════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-/Users/samt/.workbuddy/binaries/python/envs/default/bin/python}"

# ── 0. 午休时段固化上午快照 ──
# fetch_realtime.py 状态机在午休(11:30-13:00)不产文件 → 页面会一直显示"昨天"的数据。
# 此处检测：若当前为午休 且 realtime.json 的 data_date 不是今天（还是昨天旧数据），
# 用 --force 强制抓取一次（上午收盘快照），固化到 realtime.json，让午休期间可见。
# 若午休期间已固化过（data_date==今天），跳过强制抓取，避免重复拉取。
HOUR_MIN=$(date '+%H%M')
TODAY=$(date '+%Y-%m-%d')
CUR_DATE=$("$PYTHON" -c "
import json, os
try:
    d = json.load(open('realtime.json'))
    print(d.get('meta', {}).get('data_date', ''))
except Exception:
    print('')
" 2>/dev/null)
if [[ "$HOUR_MIN" -ge 1130 && "$HOUR_MIN" -lt 1300 && "$CUR_DATE" != "$TODAY" ]]; then
  echo "ℹ️  午休时段且 realtime.json 仍为 $CUR_DATE（旧数据），强制固化上午收盘快照..."
  "$PYTHON" fetch_realtime.py --out realtime.json --force 2>&1 | tail -6
fi

# ── 1. 抓取实时数据（非盘中时段脚本内部拦截，不产文件）──
echo "═══ 实时盯盘本地兜底 ═══"
"$PYTHON" fetch_realtime.py --out realtime.json 2>&1 | tail -6

# ── 2. 无新文件 → 非盘中时段，直接退出 ──
if [ ! -f realtime.json ]; then
  echo "ℹ️  非盘中时段（未开盘/午休/收盘/非交易日），脚本未产出新数据，跳过推送"
  exit 0
fi

# ── 3. 拉取远程（防与云端 Actions 并发 push 冲突）──
git fetch origin --quiet 2>/dev/null || true
if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
  echo "ℹ️  本地落后于远程，先 rebase 到 origin/main（吸收云端 Actions 的提交）"
  git rebase origin/main --quiet || { echo "⚠️  rebase 冲突，放弃本次推送（云端可能已更新）"; exit 0; }
fi

# ── 4. 有变化才提交推送 ──
if git diff --quiet realtime.json; then
  echo "ℹ️  数据无变化，跳过推送"
  exit 0
fi

git add -f realtime.json
git commit -m "实时盯盘数据(本地兜底): $(date '+%Y-%m-%d %H:%M')" -q
git push origin main 2>&1 | tail -2
echo "✅ 已推送 realtime.json（本地兜底）"
