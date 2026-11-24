#!/usr/bin/env bash
# 兜是宝 · CI 加密后重整暂存区
#
# 背景：各 workflow 的 `git add <明文路径>` 在 protect_assets.py --purge 之前执行，
#       此时明文仍在，`git add` 不会失败。随后本脚本把「明文删除」与「新 .enc」
#       补进索引，使本次提交呈现为「明文下线 + 密文上架」的原子替换。
#
# 禁用 range 写法：git add -u 只作用于受保护产物所在目录，避免误暂存无关文件。
set -euo pipefail

echo "[ci_restage] 暂存明文删除"
git add -u -- deploy data output 2>/dev/null || true

echo "[ci_restage] 暂存新增密文"
git ls-files --others --exclude-standard deploy \
  | grep -E '\.enc$' \
  | while IFS= read -r f; do git add -f "$f"; done

echo "[ci_restage] 暂存凭据与工具"
for f in deploy/auth/admin.json deploy/auth/vip.json deploy/auth/accounts.enc \
         tool/ddb_auth.py tool/protect_assets.py tool/ci_restage.sh .gitignore; do
  [ -e "$f" ] && git add -f "$f"
done

echo "[ci_restage] 当前暂存概览"
git diff --cached --name-only | wc -l | awk '{print "  暂存文件数: " $1}'
