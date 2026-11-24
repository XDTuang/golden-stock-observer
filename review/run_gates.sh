#!/usr/bin/env bash
# 兜是宝 · 门禁一键运行（真鉴权密文化适配版）
#
# 为什么要这层：
#   14 道门禁直接 open() 根目录数据文件。核心数据已密文化（只剩 *.enc），
#   直接跑门禁会有两种坏结果：
#     ① 直接报「文件不存在」→ 大量门禁不可用
#     ② 更糟：某些门禁静默跳过该检查项 → **空转通过**（假绿）
#   故本脚本：解密到工作区（与改造前环境一致）→ 跑门禁 → 无论成败都清除明文。
#
# 用法: bash review/run_gates.sh [--keep]
#   --keep  跑完保留明文（排查用，务必随后 python3 tool/protect_assets.py --unstage-plain）
set -uo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-$HOME/.workbuddy/binaries/python/envs/default/bin/python}"
KEEP=0
for a in "$@"; do [ "$a" = "--keep" ] && KEEP=1; done

cleanup() {
  if [ "$KEEP" -eq 1 ]; then
    echo ""
    echo "⚠️  --keep：明文保留在工作区，复查后请执行"
    echo "     $PY tool/protect_assets.py --unstage-plain"
  else
    "$PY" tool/protect_assets.py --unstage-plain
  fi
}
trap cleanup EXIT

echo "🔓 临时解密受保护文件（仅供门禁）"
"$PY" tool/protect_assets.py --stage-plain || exit 1
echo ""

FAIL=0
run() {
  local name="$1"; shift
  printf "%-34s" "$name"
  if "$@" > /tmp/_gate.log 2>&1; then
    echo "✅"
  else
    echo "❌"
    FAIL=$((FAIL+1))
    sed -n '$p' /tmp/_gate.log | head -3
  fi
}

echo "── 内容 / 叙述 ──"
run "check_narrative_consistency" "$PY" review/check_narrative_consistency.py
run "check_analysis_style"        "$PY" review/check_analysis_style.py
run "check_review_dates"          "$PY" review/check_review_dates.py
run "check_sector_tech"           "$PY" review/check_sector_tech.py

echo "── 数据 / 面板 ──"
run "check_market_json"           "$PY" review/check_market_json.py
run "check_touzid_panel"          "$PY" review/check_touzid_panel.py
run "check_macro_freshness"       "$PY" review/check_macro_freshness.py

echo "── 渲染 / 样式 ──"
run "check_index_render"          "$PY" review/check_index_render.py
run "check_v3_style"              "$PY" review/check_v3_style.py
run "patch_dk_css --check"        "$PY" review/patch_dk_css.py --check
run "patch_news_pool --check"     "$PY" review/patch_news_pool.py --check
run "patch_v3_richtext --check"   "$PY" review/patch_v3_richtext.py --check
run "build_us_medical --check"    "$PY" review/build_us_medical.py --check

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全部门禁通过"
else
  echo "❌ $FAIL 道门禁未通过"
fi
exit $FAIL
