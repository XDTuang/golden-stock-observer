#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mahoro 私有仓冷备（2026-11-13）
================================================================
把 mahoro_store 里的 **slices/*.tar.gz + manifest/** 提交到 private GitHub 仓做异地冷备。
db/ digest/ claims/ attachments/ 一律不进 git（由 .gitignore 白名单保证）。

用法：
  python3 feed/mahoro_backup.py --check-size          # 只报体积与风险
  python3 feed/mahoro_backup.py                       # 本地 commit（不 push）
  python3 feed/mahoro_backup.py --push                # commit + push + 远端 size 核验
  python3 feed/mahoro_backup.py --push --only-missing # 只补缺失日
  python3 feed/mahoro_backup.py --init --remote git@github.com:XDTuang/golden-stock-mahoro-archive.git

退出码：0 成功 / 2 git 锁或冲突 / 3 push 失败 / 4 体积超阈值
"""
import os
import sys
import glob
import json
import time
import argparse
import subprocess
import datetime

STORE = os.path.expanduser("~/Library/Application Support/goldenstock/mahoro_store")
SLICES = os.path.join(STORE, "slices")
MANIFEST_SUMMARY = os.path.join(STORE, "manifest", "summary.json")
LOGS = os.path.join(STORE, "logs")


def sh(args, cwd=STORE, check=False):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"  ⚠️ {' '.join(args[:3])} rc={r.returncode}: {r.stderr.strip()[:160]}", file=sys.stderr)
    return r


def git(*args, check=False):
    return sh(["git", "-C", STORE] + list(args), cwd=STORE, check=check)


def init_repo(remote=""):
    os.makedirs(STORE, exist_ok=True)
    if not os.path.isdir(os.path.join(STORE, ".git")):
        git("init", "-q", check=True)
        git("checkout", "-q", "-b", "main", check=False)
        print("  ✓ git init（main）")
    if remote:
        cur = git("remote", "get-url", "private")
        if cur.returncode != 0:
            git("remote", "add", "private", remote, check=True)
            print(f"  ✓ remote private = {remote}")
        else:
            print(f"  · remote private 已存在：{cur.stdout.strip()}")
    write_gitignore()
    return 0


def write_gitignore():
    p = os.path.join(STORE, ".gitignore")
    content = """# ── 白名单式：任何未显式放行的文件都不进仓 ──
*
!README.md
!.gitignore
!slices/
!slices/**
!manifest/
!manifest/**

# 本机独有（显式冗余声明，防白名单误放行）
db/
digest/
claims/
logs/
attachments/
tmp/
*.sqlite3
*.sqlite3-wal
*.sqlite3-shm
*.tmp
"""
    if not os.path.exists(p) or open(p, encoding="utf-8").read() != content:
        open(p, "w", encoding="utf-8").write(content)
        print("  ✓ .gitignore（白名单式）已写")


def write_readme():
    p = os.path.join(STORE, "README.md")
    content = """# mahoro 私有归档（冷备）

> 🔴 本仓只为**异地冷备**：`slices/*.tar.gz` = 每日原文打包，`manifest/` = 行级元数据。
> 不含 sqlite / digest / 附件（本机独有，可由 slices+manifest 重建）。
> 版权：付费星球与订阅邮件二手汇总，**仅自用，禁止转发/分发/公开**。

## 恢复步骤

```bash
# 1) 取回日片
git clone <this-repo> /tmp/mahoro-restore && cd /tmp/mahoro-restore
# 2) 解包到原始层（保持 <date>/<file>.txt 结构）
for gz in slices/*/*.tar.gz; do tar xzf "$gz" -C "$HOME/Library/Application Support/goldenstock/feed_mahoro/"; done
# 3) 重建 sqlite
python3 feed/mahoro_ingest.py --rebuild-fts
# 4) 对账
python3 review/check_mahoro_store.py --quick
```

## 体积

- 日片 ~1.35–2.1 MB/日、~0.55–0.78 GB/年
- 超过 900 MB 触发按年切仓（`--warn-mb`）
"""
    if not os.path.exists(p) or open(p, encoding="utf-8").read() != content:
        open(p, "w", encoding="utf-8").write(content)
        print("  ✓ README.md 已写")


def store_size_mb() -> float:
    total = 0
    for p in glob.glob(os.path.join(SLICES, "*", "*.tar.gz")):
        total += os.path.getsize(p)
    for p in glob.glob(os.path.join(STORE, "manifest", "**", "*"), recursive=True):
        if os.path.isfile(p):
            total += os.path.getsize(p)
    return total / 1e6


def check_size(warn_mb=900):
    mb = store_size_mb()
    n = len(glob.glob(os.path.join(SLICES, "*", "*.tar.gz")))
    print(f"[size] 日片 {n} 个 ｜ 备份体积 {mb:.1f} MB（阈值 {warn_mb} MB）")
    if mb > warn_mb:
        print(f"⚠️ 超过阈值 → 建议按年切仓（新建 <repo>-{datetime.date.today().year}）")
        return 4
    return 0


def commit_and_push(push=False, only_missing=False, branch="main", retries=3):
    write_gitignore()
    write_readme()
    if not os.path.isdir(os.path.join(STORE, ".git")):
        print("❌ 尚未 git init：先跑 --init --remote <private-url>")
        return 2

    # 清锁
    for f in ("index.lock",):
        p = os.path.join(STORE, ".git", f)
        if os.path.exists(p):
            os.remove(p)

    git("add", "-A", "slices", "manifest", "README.md", ".gitignore", check=True)
    st = git("status", "--porcelain")
    if not st.stdout.strip():
        print("[backup] 无变更，跳过 commit")
    else:
        n = len([x for x in st.stdout.splitlines() if x.strip()])
        msg = f"mahoro archive {datetime.date.today().isoformat()}: {n} 项 / {store_size_mb():.1f} MB"
        r = git("-c", "user.name=goldenstock", "-c", "user.email=bot@local",
                "commit", "-q", "-m", msg, check=True)
        head = git("rev-parse", "--short", "HEAD").stdout.strip()
        print(f"[backup] commit {head}：{msg}")

    if not push:
        print("[backup] 仅本地 commit（未 push）")
        return 0

    for i in range(retries):
        r = git("push", "private", f"HEAD:{branch}")
        if r.returncode == 0:
            print(f"[backup] push 成功（第 {i+1} 次）")
            break
        wait = 20 * (i + 1)
        print(f"[backup] push 失败（rc={r.returncode}）：{r.stderr.strip()[:120]} → {wait}s 后重试")
        time.sleep(wait)
    else:
        log_fail("push 连续失败")
        return 3

    # 远端核验：取最新一天日片的 size
    days = sorted(glob.glob(os.path.join(SLICES, "*", "*.tar.gz")))
    if days:
        rel = os.path.relpath(days[-1], STORE)
        local = os.path.getsize(days[-1])
        out = git("ls-tree", "-l", f"private/{branch}", "--", rel)
        parts = out.stdout.split()
        remote = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else -1
        ok = (local == remote)
        print(f"[backup] 远端核验 {rel}: local={local} remote={remote} → {'✅' if ok else '❌'}")
        if not ok:
            log_fail(f"远端 size 不一致 {rel}")
            return 3
    return 0


def log_fail(msg):
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "backup.log"), "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] FAIL {msg}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--remote", default="")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--check-size", action="store_true")
    ap.add_argument("--warn-mb", type=float, default=900)
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    if args.init:
        return init_repo(args.remote)
    if args.check_size:
        return check_size(args.warn_mb)
    rc = check_size(args.warn_mb)
    if rc == 4:
        print("[backup] 体积超阈值，仍继续 commit（请尽快切仓）")
    return commit_and_push(args.push, args.only_missing, args.branch)


if __name__ == "__main__":
    sys.exit(main())
