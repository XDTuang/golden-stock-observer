#!/usr/bin/env bash
# ============================================================================
# 早间链路哨兵 · 统一判据（2026-09-30 立）
# ----------------------------------------------------------------------------
# 存在理由：原「三秒判据」只看三处产物的写入时间 —— 会出现
#   「产物已写完、但推送失败」被误判为「已完成」→ 页面静默停留在旧版，
#   而哨兵一行退出、无人知晓（2026-09-30 实测确认该缺口）。
#   本脚本把判据收敛为**唯一实现**，4 个哨兵档统一调用，避免 4 份 prompt 各自维护。
#
# 用法（只读，不改任何仓库文件；唯一例外 = 清理自己 git status 可能留下的陈旧 index.lock）：
#   bash review/sentinel_check.sh
#
# 输出：第 1 行 = 状态 token（供 prompt 分支）；第 2 行 = 人读说明
#   NONTRADE        非交易日（**仅判周末**；法定节假日须 agent 自行判定）
#   RUNNING         早档位正在运行 / git 正被占用 → **本档退出，不干预**
#   NOT_DONE        早间链路未完成 → 需补跑（按 SOP 全流程）
#   DONE_UNPUSHED   产物已就绪但**未推送** → 本档**只执行发布**，不重做推演
#   DONE_PUSHED     产物已就绪且已推送 → 一行退出，无需动作
# ============================================================================
set -u
cd "$(dirname "$0")/.." || { echo "ERROR"; echo "无法进入仓库根"; exit 9; }

TODAY=$(date +%Y-%m-%d)
DOW=$(date +%u)                      # 1=周一 … 7=周日
case "$DOW" in
  6|7) echo "NONTRADE"; echo "非交易日（周末 $TODAY）"; exit 0 ;;
esac

# ── 1) git 被占用 → 判「发布进行中」，退出不干预（最安全分支，须最先判）──
if [ -e .git/index.lock ] || [ -d .git/rebase-merge ]; then
  echo "RUNNING"
  echo "git 正被占用（index.lock / rebase-merge 存在）→ 判定发布进行中，本档退出不干预"
  exit 0
fi

# ── 2) 截止时刻 = 今日 08:15（宽松下界，早于任何档位）──
CUT=$(date -j -f "%Y-%m-%d %H:%M:%S" "$TODAY 08:15:00" +%s 2>/dev/null || echo 0)
[ "$CUT" = "0" ] && CUT=$(date -j -f "%Y-%m-%d %H:%M" "$TODAY 08:15" +%s 2>/dev/null || echo 0)

mt() { stat -f %m "$1" 2>/dev/null || echo 0; }

M1=$(mt data/daily_review/analysis.html)
M2=$(mt output/v3_reasoning_latest.json)
M3=$(mt output/feed_review_latest.json)

# ── 3) 早档位运行中检测（产物近期写入 / automation 有 start 无 finished）──
NOW=$(date +%s); RECENT=$((NOW - 1200))     # 20 分钟窗
RUNNING=0
for f in data/daily_review/market.json output/daily_news_latest.json \
         output/daily_macro_latest.json data/daily_review/analysis.html; do
  [ "$(mt "$f")" -gt "$RECENT" ] && RUNNING=1
done
LOG="$HOME/.workbuddy/logs/automation.log"
if [ -f "$LOG" ]; then
  for ID in bd4b82c4 114b5ccd; do   # 推演发布档 / 早间数据准备档
    s=$(grep -ac "run start: id=$ID"  "$LOG" 2>/dev/null || echo 0)
    f=$(grep -ac "run finished: id=$ID" "$LOG" 2>/dev/null || echo 0)
    [ "$s" -gt "$f" ] && RUNNING=1
  done
fi

# ── 4) 三处产物是否均已就绪 ──
if [ "$M1" -gt "$CUT" ] && [ "$M2" -gt "$CUT" ] && [ "$M3" -gt "$CUT" ]; then
  git fetch -q origin main 2>/dev/null
  AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
  DIRTY=$(git status --porcelain -- data/daily_review output review_v3 2>/dev/null | wc -l | tr -d ' ')
  rm -f .git/index.lock 2>/dev/null   # 清掉本脚本 git status 可能留下的陈旧锁
  if [ "$AHEAD" = "0" ] && [ "$DIRTY" = "0" ]; then
    echo "DONE_PUSHED"
    echo "产物已就绪且已推送（HEAD $(git rev-parse --short HEAD) == origin/main · 无未提交推演产物）"
  else
    echo "DONE_UNPUSHED"
    echo "产物已就绪但**未推送**（领先远端 $AHEAD 个提交 · 未提交推演产物 $DIRTY 项）→ 只做发布，勿重做推演"
  fi
  exit 0
fi

if [ "$RUNNING" = "1" ]; then
  echo "RUNNING"
  echo "检测到早档位正在运行，本档退出不干预"
  exit 0
fi

echo "NOT_DONE"
echo "早间链路未完成（三处产物任一未晚于今日 08:15）→ 按 SOP 全流程补跑"
exit 0
