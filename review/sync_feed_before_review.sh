#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 推演前置同步（按需执行，非常驻轮询）
# -----------------------------------------------------------
# 何时跑：agent 收到推演命令时（本机或手机端）先跑一次
# 做什么：
#   1) git pull 拉取仓库最新（拿到浏览器/手机端投喂与推演请求）
#   2) 归档 feed/inbox/ 新投喂（feed_archive.py → feed/archive/）
#   2.5) 脱敏守卫 check_feed_desensitize.py（红灯自动 --fix 掩码，复扫确认）
#   3) 读取 commands/pending/ 的推演请求（打印出来给 agent 看），归档到 done/
# 不做什么：不做系统通知、不自动 git push（推演流程末尾统一提交）
# 用法：bash review/sync_feed_before_review.sh
# ═══════════════════════════════════════════════════════════
REPO="/Users/samt/golden_stock_observer"
PY="/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
cd "$REPO" || exit 1

echo "─── 1/3 拉取仓库 ───"
# 有未提交改动时 rebase 会被拒 → 跳过 pull（推演产物往往尚未提交，属正常）
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
  git pull -q --rebase origin main 2>&1 | tail -3
  echo "✅ 已拉取最新"
else
  echo "⚠️ 工作区有未提交改动，跳过 pull（推演结束后统一提交时会一并 rebase）"
fi

echo "─── 2/3 归档投喂 inbox ───"
"$PY" feed/feed_archive.py 2>&1 | grep -v "跳过附件副本" | tail -8

echo "─── 2.5 脱敏守卫（私域人物名称 / 微信ID / 本机路径 / 手机号 / 个人邮箱）───"
# 2026-11-12 用户拍板：私域聊天归档中一切可识别人物的信息一律脱敏；存量发现即清理。
if "$PY" review/check_feed_desensitize.py >/tmp/feed_desens_scan.txt 2>&1; then
  echo "✅ 归档件已脱敏（6 类检查全绿）"
else
  echo "⚠️ 检出未脱敏残留 → 自动掩码（root+deploy 双写）"
  tail -12 /tmp/feed_desens_scan.txt
  "$PY" review/check_feed_desensitize.py --fix 2>&1 | tail -3
  if "$PY" review/check_feed_desensitize.py >/tmp/feed_desens_scan2.txt 2>&1; then
    echo "✅ 掩码后复扫全绿"
  else
    echo "❌ 仍有残留，需人工判断后再入库："
    tail -10 /tmp/feed_desens_scan2.txt
  fi
fi

echo "─── 3/3 读取推演请求 ───"
shopt -s nullglob
PENDING=(commands/pending/*.md)
shopt -u nullglob
if [ ${#PENDING[@]} -eq 0 ]; then
  echo "（无待处理推演请求）"
else
  for f in "${PENDING[@]}"; do
    [ -f "$f" ] || continue
    echo "📋 请求文件：$(basename "$f")"
    cat "$f"
    echo "---"
    mv "$f" commands/done/ 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(basename "$f") 已受理" >> commands/cmd_history.log
  done
fi
echo "✅ 前置同步完成"
