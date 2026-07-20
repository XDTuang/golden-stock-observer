#!/bin/bash
# 把 diamond_site/ 部署到腾讯云 CloudBase 静态托管（国内访问镜像）
# 前置: npm i -g @cloudbase/cli && tcb login
# 用法: CLOUDBASE_ENV_ID=你的环境ID bash cloudbase/deploy_cloudbase.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_ID="${CLOUDBASE_ENV_ID:?未设置 CLOUDBASE_ENV_ID（CloudBase 环境ID）}"

if ! command -v tcb >/dev/null 2>&1; then
  echo "✗ 未找到 tcb CLI，请先执行: npm i -g @cloudbase/cli && tcb login"
  exit 1
fi

if [ ! -d "$ROOT/diamond_site" ]; then
  echo "✗ 缺少 diamond_site/ 目录，请先运行 _build_diamond.py 构建副站"
  exit 1
fi

# 复制到不含 .git 的临时目录：避免部署时读取/上传 git 内部文件触发权限错误
TMP="$(mktemp -d)"
tar -C "$ROOT/diamond_site" --exclude='.git' --exclude='.gitignore' -cf - . | tar -C "$TMP" -xf -

echo "▶ 部署 diamond_site/ → CloudBase 环境 $ENV_ID"
# hosting deploy <本地目录> <云端路径> ；云端路径 / 表示静态托管根
tcb hosting deploy "$TMP" / --env-id "$ENV_ID"

rm -rf "$TMP"

echo "✅ 完成。国内访问: https://$ENV_ID.tcloudbase.com"
