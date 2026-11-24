#!/usr/bin/env bash
# 兜是宝 · CI 加密后重整暂存区
#
# 背景（2026-11-24 修正）：GitHub Pages 服务的是 **main 分支根目录**，
#   deploy/ 只是构建产物。因此加密必须覆盖两处：
#     ① deploy/  —— 构建产物，明文下线
#     ② 根目录   —— 真正被 Pages 服务的目录，密文上架
#   漏掉 ② 的后果是双重的：明文仍可直取 + 根 index.html 的拦截层改写为 *.enc 后 404。
#
# 各 workflow 的 `git add <明文路径>` 在加密之前执行（此时明文仍在，不会失败），
# 随后本脚本：同步根目录 → 记录明文删除 → 补入新密文 → 追加凭据与工具。
set -euo pipefail

PY="${PYTHON:-python}"

echo "[ci_restage] 同步密文到站点根目录"
"$PY" tool/protect_assets.py --sync-root

echo "[ci_restage] 暂存明文删除（deploy + 根目录）"
git add -u -- deploy data output auth 2>/dev/null || true
git add -u -- signals.json lh_calendar.json realtime.json index.html 2>/dev/null || true

echo "[ci_restage] 暂存全部密文"
# 根目录与 deploy 下的 .enc 均被 .gitignore 覆盖，必须逐个 -f 点名
find . -name '*.enc' -not -path './.git/*' -not -path './_backups/*' -print0 \
  | while IFS= read -r -d '' f; do git add -f "$f"; done

echo "[ci_restage] 暂存凭据与工具"
for f in deploy/auth/admin.json deploy/auth/vip.json deploy/auth/accounts.enc deploy/auth/protected.json \
         auth/admin.json auth/vip.json auth/accounts.enc auth/protected.json \
         tool/ddb_auth.py tool/protect_assets.py tool/ci_restage.sh .gitignore; do
  [ -e "$f" ] && git add -f "$f"
done

echo "[ci_restage] 当前暂存概览"
git diff --cached --name-only | wc -l | awk '{print "  暂存文件数: " $1}'
