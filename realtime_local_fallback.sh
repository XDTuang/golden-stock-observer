#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 实时盯盘 · 本地兜底（WorkBuddy 自动化驱动：交易日 10:30 / 14:15 各一次且仅一次）
# ───────────────────────────────────────────────────────────
# 定位（2026-08-31 重新梳理，替代旧的"盘中每小时"方案）：
#   - 主力：GitHub Actions realtime-monitor.yml，交易日 9:30-15:00 每 30 分钟
#     schedule 触发（官方已知不稳定，可能整段静默跳过，如 2026-08-31 上午全部静默）
#   - 兜底：本脚本仅由自动化在交易日 10:30 与 14:15 触发，各执行一次且仅一次，
#     一天最多两次，绝不 24h 轮询
#   - 幂等：执行前先查云端 realtime.json（origin/main）——若云端当日已成功更新
#     且时段满足，直接跳过，避免重复抓取/推送
#
# 流程:
#   1. 周末/非交易日 → 直接退出
#   2. 云端健康检查：云端当日已成功更新（上午>=09:00 / 下午>=12:30）→ 跳过
#   3. fetch_realtime.py 抓取 + 计算五层信号（内部按 A股状态机拦截：
#      非交易日 / 未开盘 / 午休 / 收盘 → 不写文件不提交）
#   4. 先 commit 实时数据（仅 realtime.json，不碰其他任务产物）
#   5. rebase + push（失败自动重试 1 轮；rebase 冲突则保留本地 commit 并明确告警）
# ═══════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-/Users/samt/.workbuddy/binaries/python/envs/default/bin/python}"
TODAY=$(date '+%Y-%m-%d')

echo "═══ 实时盯盘本地兜底 ═══"
echo "⏱ $(date '+%Y-%m-%d %H:%M:%S') 开始"

# ── 补推函数：rebase + push（失败自动重试 1 轮；rebase 冲突则保留本地 commit 并明确告警）──
try_push() {
  local i
  # ── rebase 前必须工作区干净 ──────────────────────────────────────────
  # 🔴 2026-09-01 修复：git rebase 要求无 unstaged changes。
  #    此前只要本机有任何无关改动（如改了 review/build_share_html.py 未提交），
  #    rebase 就报 "cannot rebase: You have unstaged changes" → 推送被拒
  #    → 兜底数据抓到了却推不上去（stderr 里 19 条同样报错）。
  #    现改为：rebase/push 前自动 stash 无关改动，事后 pop 恢复，
  #    兜底不再被其他任务的残留产物阻塞。
  local STASHED=0
  if ! git diff --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
    if git stash push --include-untracked -m "realtime-fallback-autostash" >/dev/null 2>&1; then
      STASHED=1
      echo "ℹ️  已临时 stash 无关改动（含 untracked），推送后自动恢复"
    fi
  fi

  for i in 1 2; do
    git fetch origin --quiet 2>/dev/null || true
    if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
      echo "ℹ️  本地落后于远程，rebase 到 origin/main（第 $i 轮）"
      if ! git rebase origin/main --quiet 2>/dev/null; then
        local LOCAL_SHA
        LOCAL_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
        git rebase --abort 2>/dev/null || true
        echo "⚠️  rebase 失败：本地提交（$LOCAL_SHA）未推送。"
        echo "   ⚠️  请稍后手动处理：git fetch && git rebase origin/main && git push"
        [ "$STASHED" = "1" ] && git stash pop 2>/dev/null || true
        return 1
      fi
    fi
    local PUSH_OUT=/tmp/lhb_push_$$.log
    if git push origin main >"$PUSH_OUT" 2>&1; then
      rm -f "$PUSH_OUT"
      [ "$STASHED" = "1" ] && git stash pop 2>/dev/null && echo "ℹ️  已恢复 stash 的改动"
      return 0
    else
      echo "⚠️  推送被拒（第 $i 轮）："; tail -2 "$PUSH_OUT"; rm -f "$PUSH_OUT"
    fi
  done
  echo "⚠️  推送连续失败，本地提交（$(git rev-parse --short HEAD)）待人工处理"
  [ "$STASHED" = "1" ] && git stash pop 2>/dev/null || true
  return 1
}

# ── 0. 非交易日（周末）直接退出 ──
DOW=$(date '+%u')   # 1=周一 ... 7=周日
if [ "$DOW" -ge 6 ]; then
  echo "ℹ️  非交易日（周末），跳过"
  exit 0
fi

# ── 1. 午休固化（保留：11:30-13:00 且本地 realtime.json 仍为昨日 → 强制固化上午快照）──
HOUR_MIN=$(date '+%H%M')
# 🔴 2026-09-01 修复：bash 的 [[ N -ge M ]] 会把 **以 0 开头的数字当八进制**。
#    上午 09:02 时 $(date '+%H%M') 输出 "0902"，9 不是合法八进制数字 →
#    报错 "[[: 0902: value too great for base"，整个判断失效
#    （stderr 里 08:28/08:31/08:45/08:58/09:02/09:32 全部中招）。
#    用 10# 前缀强制十进制解析。
HOUR_MIN_DEC=$((10#$HOUR_MIN))
CUR_DATE=$("$PYTHON" -c "
import json
try:
    d = json.load(open('realtime.json'))
    print(d.get('meta', {}).get('data_date', ''))
except Exception:
    print('')
" 2>/dev/null)
if [[ "$HOUR_MIN_DEC" -ge 1130 && "$HOUR_MIN_DEC" -lt 1300 && "$CUR_DATE" != "$TODAY" ]]; then
  echo "ℹ️  午休时段且 realtime.json 仍为 $CUR_DATE（旧数据），强制固化上午收盘快照..."
  "$PYTHON" fetch_realtime.py --out realtime.json --force 2>&1 | tail -6
fi

# ── 2. 云端健康检查：云端当日已成功 → 兜底跳过 ──
git fetch origin --quiet 2>/dev/null || true
CLOUD_CHECK=$("$PYTHON" -c "
import json, subprocess
try:
    out = subprocess.run(['git','show','origin/main:realtime.json'],
                         capture_output=True, text=True, timeout=30).stdout
    m = json.loads(out).get('meta', {})
    print((m.get('data_date','') or '') + '|' + (m.get('updated_at','') or ''))
except Exception:
    print('|')
" 2>/dev/null)
CLOUD_DATE="${CLOUD_CHECK%%|*}"
CLOUD_TS="${CLOUD_CHECK##*|}"
if [ -n "$CLOUD_DATE" ] && [ "$CLOUD_DATE" = "$TODAY" ] && [ -n "$CLOUD_TS" ]; then
  CLOUD_EPOCH=$("$PYTHON" -c "
import datetime
try:
    print(int(datetime.datetime.strptime('$CLOUD_TS','%Y-%m-%d %H:%M:%S').timestamp()))
except Exception:
    print('0')
")
  # 阈值：上午兜底要求云端 >= 今日 09:00；下午兜底要求 >= 今日 12:30
  # ── 云端 vs 本地的职责边界（2026-09-01 用户明确）──────────────────
  #   云端主力（.github/workflows/realtime-monitor.yml）每交易日 8 个时间点：
  #       9:45  10:15  10:45  11:15   13:15  13:45  14:15  14:45
  #   本地兜底（本脚本，plist 调度）严格一天 2 次：10:30 / 14:30
  #   阈值推导：
  #     10:30 兜底 → 云端 9:45 首档已跑 → 阈值 09:00 可正确判定云端是否成功
  #     14:30 兜底 → 云端 13:15 已跑（11:30-13:00 午休不产数据）→ 阈值 12:30 同理
  #   云端成功则本脚本直接 exit 0，不重复抓取、不重复推送。
  HOUR_NUM=$(date '+%H')
  THRESHOLD_EPOCH=$("$PYTHON" -c "
import datetime
h = '09:00:00' if int('$HOUR_NUM') < 12 else '12:30:00'
print(int(datetime.datetime.strptime('$TODAY '+h,'%Y-%m-%d %H:%M:%S').timestamp()))
")
  if [ "$CLOUD_EPOCH" -ge "$THRESHOLD_EPOCH" ]; then
    echo "ℹ️  云端已成功更新（data_date=$CLOUD_DATE, updated_at=$CLOUD_TS），本地兜底跳过"
    exit 0
  fi
  echo "ℹ️  云端当日更新已过期/缺失（updated_at=$CLOUD_TS），执行本地兜底..."
else
  echo "ℹ️  云端 realtime.json 非当日数据（data_date=${CLOUD_DATE:-空}），执行本地兜底..."
fi

# ── 2.5 补推遗留：若本地存在未推送的实时提交（如上次兜底推送受阻），先尝试补推 ──
AHEAD_N=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
if [ "${AHEAD_N:-0}" -gt 0 ]; then
  echo "ℹ️  检测到本地有 ${AHEAD_N} 个未推送提交，先补推..."
  if try_push; then
    echo "✅ 已补推本地遗留提交"
  fi
fi

# ── 3. 抓取实时数据（非盘中时段脚本内部拦截，不产文件）──
"$PYTHON" fetch_realtime.py --out realtime.json 2>&1 | tail -6

# ── 4. 确认抓取产出了"本次新数据"（realtime.json 为常驻文件，必须校验 updated_at 新鲜度）──
# fetch_realtime.py 在非盘中不写文件 → updated_at 停留在旧时间戳（如昨日前收盘快照），
# 不能以"文件存在"判断，否则会把工作区残留的旧版本误当新数据提交。
if [ ! -f realtime.json ]; then
  echo "ℹ️  未产出 realtime.json，跳过提交与推送"
  exit 0
fi
FRESH=$("$PYTHON" -c "
import json, datetime
try:
    u = json.load(open('realtime.json'))['meta']['updated_at']
    ut = datetime.datetime.strptime(u, '%Y-%m-%d %H:%M:%S')
    now = datetime.datetime.now()
    print('1' if 0 <= (now - ut).total_seconds() < 600 else '0')
except Exception:
    print('0')
")
if [ "$FRESH" != "1" ]; then
  echo "ℹ️  非盘中时段，未产生新数据（updated_at 为旧快照，保留上次数据），跳过提交与推送"
  exit 0
fi

# ── 5. 先提交实时数据（仅 realtime.json，保证数据入库，不影响其他任务产物）──
if git diff --quiet realtime.json; then
  echo "ℹ️  数据无变化，跳过提交与推送"
  exit 0
fi
git add -f realtime.json
# 🔴 2026-09-01：同步 deploy 副本（本地预览根目录是 deploy/，不同步就看不到更新）。
#    与 workflow 里 daily-review-market.yml 犯的是同一个错（脚本写了两份却只 add 一份）。
#    注意：只 add 不 cp 是没用的——必须先真正把文件同步过去。
cp -f realtime.json deploy/realtime.json 2>/dev/null || true
if [ -f deploy/realtime.json ]; then git add -f deploy/realtime.json; fi
git commit -m "实时盯盘数据(本地兜底): $(date '+%Y-%m-%d %H:%M')" -q
echo "✅ 实时数据已提交到本地"

# ── 6. rebase + push（复用 try_push，失败保留本地 commit 并明确告警）──
if try_push; then
  echo "✅ 已推送 realtime.json（本地兜底）"
fi
exit 0
