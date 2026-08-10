# -*- coding: utf-8 -*-
"""
CloudBase 云函数入口（Python 3.10）
功能: 定时(盘后) 拉取金钻数据 -> 构建副站 -> 推送到 GitHub 部署仓库
      （CloudBase 静态托管已授权该仓库，推送即自动部署到国内默认子域）

⚠️ 超时约束: 免费体验版/个人版云函数仅 3s，跑不了本管线。
   需在【标准版及以上】环境运行，并把本函数超时设为 900s（常规函数），
   或改用 HTTP 函数（上限 7200s）。付费但稳定。

两种运行模式:
  PACKAGED=0 (默认): 运行时 git clone 源码仓库（需腾讯云能访问 GitHub）
  PACKAGED=1        : 直接用地函数包内已打好的脚本（推荐，避免 GitHub 依赖）
"""
import os
import sys
import shutil
import subprocess
import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
SOURCE_REPO = os.environ.get("SOURCE_REPO", "XDTuang/golden-stock-observer")
DEPLOY_REPO = os.environ.get("DEPLOY_REPO", "XDTuang/golden-diamond-observer")
PACKAGED = os.environ.get("PACKAGED", "0") == "1"
WORK = "/tmp/gdsync"


def run(cmd, cwd=None):
    print(f"[run] {cmd}")
    r = subprocess.run(cmd, cwd=cwd, shell=True, executable="/bin/bash")
    if r.returncode != 0:
        raise SystemExit(f"命令失败({r.returncode}): {cmd}")


def clone_and_build_from_github():
    """模式A: clone 源码 -> 跑管线 -> 构建"""
    auth = f"https://{GITHUB_TOKEN}@github.com"
    run(f"git clone --depth 1 {auth}/{SOURCE_REPO}.git src", cwd=WORK)
    if os.path.exists(f"{WORK}/src/requirements.txt"):
        run("pip install -q -r requirements.txt", cwd=f"{WORK}/src")
    run("python3 fetch_pool.py", cwd=f"{WORK}/src")
    run("python3 golden_diamond_scan.py", cwd=f"{WORK}/src")
    run("python3 _build_diamond.py", cwd=f"{WORK}/src")
    return f"{WORK}/src"


def build_from_packaged():
    """模式B: 函数包内已含脚本（部署时把 fetch_pool.py 等打进 zip）"""
    base = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(base, "fetch_pool.py")):
        raise SystemExit("PACKAGED=1 但函数包内未找到 fetch_pool.py，请部署时打进 zip")
    if os.path.exists(os.path.join(base, "requirements.txt")):
        run("pip install -q -r requirements.txt", cwd=base)
    run("python3 fetch_pool.py", cwd=base)
    run("python3 golden_diamond_scan.py", cwd=base)
    run("python3 _build_diamond.py", cwd=base)
    return base


def push_to_deploy_repo(site_dir):
    """把构建好的 diamond_site/ 推到部署仓库（CloudBase GitHub 集成自动部署）"""
    auth = f"https://{GITHUB_TOKEN}@github.com"
    run(f"git clone --depth 1 {auth}/{DEPLOY_REPO}.git dst", cwd=WORK)
    # 仅清掉站点文件（保留 .git），再拷入新产物（天然隔离: 不含 gate_data）
    run("rm -rf ./*", cwd=f"{WORK}/dst")
    run(f"cp -R {site_dir}/diamond_site/. .", cwd=f"{WORK}/dst")
    today = datetime.date.today().isoformat()
    run(f'git add -A && git commit -m "auto: {today}" && git push', cwd=f"{WORK}/dst")
    print("OK 已推送，CloudBase 静态托管将自动同步")


def main():
    if not GITHUB_TOKEN:
        raise SystemExit("缺少环境变量 GITHUB_TOKEN（需 repo 写权限的 PAT）")
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)

    site_base = build_from_packaged() if PACKAGED else clone_and_build_from_github()
    push_to_deploy_repo(site_base)
    print("DONE")


if __name__ == "__main__":
    main()
