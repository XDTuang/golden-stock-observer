#!/bin/bash
# ============================================================================
# 每日复盘数据快照备份（回测素材归档）
#   把当日 每日复盘 全部数据快照到 data/daily_review_history/<T>/
#   供后续"回测一周分析准确度"使用（推演 vs 实际走势对照）
#
# 归档内容:
#   - analysis.html         当日完整复盘（含 1.1 TOP10 / 1.2 金钻 / 1.3 重点观测股推演）
#   - market.json           云端行情快照
#   - obs_tech_<T>.json     31 只技术位（MA/支撑/压力/量比/形态）
#   - obs_deduce_<T>.json   31 只推演结论（走势 + 开盘方式）
#   - tx_kline_<T>.json     腾讯前复权 K 线（10 日）
#   - raw_kline_<T>.json    neodata 原始 K 线
#   - zsxq_digest_<T>.md    知识星球摘要（若存在）
#
# 用法: bash backup_daily_review.sh [日期]   默认日期 = 今天
# ============================================================================
set -u

MAIN_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$MAIN_DIR/data/daily_review"
BK_ROOT="$MAIN_DIR/data/daily_review_history"
DATE="${1:-$(date +%Y-%m-%d)}"
BK_DIR="$BK_ROOT/$DATE"

mkdir -p "$BK_DIR"
COPIED=0

# 1. 当日主站产物（analysis.html + market.json 若与日期匹配则复制）
for f in analysis.html market.json; do
  if [ -f "$SRC/$f" ]; then
    cp -f "$SRC/$f" "$BK_DIR/$f" && COPIED=$((COPIED+1))
  fi
done

# 2. 回测素材（按日期后缀匹配）
for pat in "obs_tech_${DATE}.json" "obs_deduce_${DATE}.json" "tx_kline_${DATE}.json" "raw_kline_${DATE}.json" "zsxq_digest_${DATE}.md" "daily_${DATE}.json"; do
  if [ -f "$SRC/$pat" ]; then
    cp -f "$SRC/$pat" "$BK_DIR/$pat" && COPIED=$((COPIED+1))
  fi
done

# 3. 兜是宝每日复盘系统产物（若存在）
DSB="/Users/samt/Desktop/兜是宝/AI 构架研究/每日复盘系统"
if [ -d "$DSB/data" ]; then
  for pat in "zsxq_digest_${DATE}.md" "daily_${DATE}.json"; do
    if [ -f "$DSB/data/$pat" ]; then
      cp -f "$DSB/data/$pat" "$BK_DIR/$pat" && COPIED=$((COPIED+1))
    fi
  done
  if [ -f "$DSB/daily-review-${DATE}.html" ]; then
    cp -f "$DSB/daily-review-${DATE}.html" "$BK_DIR/daily-review-${DATE}.html" && COPIED=$((COPIED+1))
  fi
fi

echo "[backup] $DATE -> $BK_DIR （$COPIED 个文件）"
ls -1 "$BK_DIR" 2>/dev/null | head -20
