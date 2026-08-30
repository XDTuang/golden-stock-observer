#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_push.py —— GitHub Pages 推送后「线上一致性」权威校验脚本

┌──────────────────────────────────────────────────────────────────────┐
│ 为什么需要它                                                          │
├──────────────────────────────────────────────────────────────────────┤
│ 1) 国内直连 raw.githubusercontent.com 下载文件（尤其 >1MB）经常被截断   │
│    —— 2026-08-30 实测 curl raw 直接 exit 137（SIGKILL），无法用于验证。 │
│ 2) GitHub API  `contents/{path}?ref=<branch>`  返回的                  │
│       size = 文件字节数                                               │
│       sha  = git blob SHA                                             │
│    这两个字段是服务端权威值：size 一致 = 字节数一致，sha 一致 = 内容      │
│    完全一致。故「size + sha 双字段」才是可信的线上验证，不要再用 raw。    │
│ 3) 本项目部署源是仓库根目录（.nojekyll 在根），deploy/ 也要同步更新，    │
│    两边都要验，否则会出现「JSON 新、HTML 旧」的假象。                    │
└──────────────────────────────────────────────────────────────────────┘

用法
────
    python3 review/verify_push.py                     # 校验 HEAD 提交涉及的全部文件
    python3 review/verify_push.py --commit HEAD~1     # 校验指定提交涉及的文件
    python3 review/verify_push.py -f a.html b.json    # 校验指定文件
    python3 review/verify_push.py -f index.html --ref main
    python3 review/verify_push.py --all-tracked       # 校验全部被跟踪文件（慢，慎用）

可选环境变量
────────────
    GITHUB_TOKEN=ghp_xxx    认证后 rate limit 从 60/h 提到 5000/h，
                            校验文件多时（尤其 --all-tracked）强烈建议设置。

依赖：python3 标准库 + 系统 curl + git（无需安装第三方包）
退出码：全部一致 = 0；存在不一致或异常 = 1
"""

import argparse
import json
import os
import subprocess
import sys
import time

API = "https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"

# ── 输出配色 ────────────────────────────────────────────────────────────────
if sys.stdout.isatty():
    OK, BAD, WARN, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
else:
    OK = BAD = WARN = DIM = BOLD = RESET = ""


def run(cmd, capture=True):
    """执行 shell 命令，返回 (returncode, stdout)"""
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return r.returncode, (r.stdout or "").strip()


def git_repo():
    """从 git remote 解析 owner/repo"""
    rc, url = run("git remote get-url origin")
    if rc != 0:
        return None
    url = url.strip()
    for pat in ("git@github.com:", "https://github.com/", "http://github.com/", "ssh://git@github.com/"):
        if url.startswith(pat):
            return url[len(pat):]
    if "github.com" in url:
        return url.split("github.com")[-1].lstrip(":/")
    return url.rstrip("/")


def api_get(repo, path, ref, retries=3, timeout=30):
    """调用 GitHub contents API，带重试（国内网络偶发瞬时失败）"""
    url = API.format(repo=repo, path=path.strip("/"), ref=ref)
    cmd = ["curl", "-s", "--max-time", str(timeout), url]
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        cmd += ["-H", "Authorization: Bearer %s" % token]
        cmd += ["-H", "Accept: application/vnd.github+json"]
    for attempt in range(1, retries + 1):
        r = subprocess.run(cmd, capture_output=True, text=True)
        raw = r.stdout or ""
        if not raw:
            time.sleep(2)
            continue
        try:
            d = json.loads(raw)
        except Exception:
            time.sleep(2)
            continue
        if not isinstance(d, dict):
            return {"_err": "unexpected response"}
        if "message" in d and "sha" not in d:
            # rate limit / 404 / 其他错误
            if "rate limit" in str(d.get("message", "")).lower():
                return {"_err": "rate limit exceeded（设置 GITHUB_TOKEN 可提高限额）"}
            if attempt < retries:
                time.sleep(2)
                continue
            return {"_err": str(d.get("message"))}
        return d
    return {"_err": "request failed after %d retries" % retries}


def local_blob_sha(path, ref="HEAD"):
    """本地 git blob SHA"""
    rc, out = run("git rev-parse %s:%s" % (ref, path))
    return out if rc == 0 else None


def head_commit_files(commit="HEAD"):
    """某提交涉及的文件列表（排除已删除的）"""
    rc, out = run("git show --name-only --pretty=format: %s" % commit)
    if rc != 0:
        return []
    files, seen = [], set()
    for line in out.splitlines():
        p = line.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        if not os.path.exists(p):   # 该提交中已删除的文件跳过
            continue
        files.append(p)
    return files


def all_tracked_files():
    """全部被跟踪文件（慢，文件多时慎用 API rate limit）"""
    rc, out = run("git ls-files")
    if rc != 0:
        return []
    return [p for p in out.splitlines() if p.strip() and os.path.exists(p)]


def short(s, n=7):
    return s[:n] if s and len(s) > n else (s or "—")


def main():
    ap = argparse.ArgumentParser(
        description="GitHub Pages 推送后线上一致性校验（API size + sha 双字段权威验证）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：python3 review/verify_push.py   |   python3 review/verify_push.py -f index.html deploy/index.html"
    )
    ap.add_argument("-f", "--files", nargs="+", help="指定要校验的文件路径")
    ap.add_argument("--commit", default="HEAD", help="校验该提交涉及的文件（默认 HEAD）")
    ap.add_argument("--ref", default="main", help="远程分支（默认 main）")
    ap.add_argument("--all-tracked", action="store_true", help="校验全部被跟踪文件（慎用 rate limit）")
    ap.add_argument("--no-sha", action="store_true", help="只校验字节数，不校验 SHA（更快）")
    args = ap.parse_args()

    repo = git_repo()
    if not repo:
        print(BAD + "✗ 无法从 git remote 解析仓库名（确认在 git 仓库内且已配置 origin）" + RESET)
        return 1
    repo = repo.rstrip("/").replace(".git", "")

    # 收集待校验文件
    if args.files:
        files = args.files
    elif args.all_tracked:
        files = all_tracked_files()
    else:
        files = head_commit_files(args.commit)

    files = [f for f in files if os.path.isfile(f)]
    if not files:
        print(WARN + "! 没有可校验的文件（提交可能只删除了文件）" + RESET)
        return 1

    print(BOLD + "🔍 线上一致性校验" + RESET + "  %s  @  %s" % (repo, args.ref))
    print(DIM + "   模式：GitHub API contents 的 size（字节数）+ sha（git blob SHA）双字段" + RESET)
    print(DIM + "   待校验：%d 个文件%s\n" % (len(files), "（--all-tracked）" if args.all_tracked else
                                              "（%s 提交涉及）" % args.commit if not args.files else "") + RESET)

    rows, ok_cnt, bad_cnt = [], 0, 0
    for path in files:
        local_size = os.path.getsize(path)
        remote = api_get(repo, path, args.ref)

        if "_err" in remote:
            rows.append((path, local_size, "—", "—", "—", "ERR: " + str(remote["_err"])[:40]))
            bad_cnt += 1
            continue

        api_size = remote.get("size")
        api_sha = remote.get("sha")
        local_sha = None if args.no_sha else local_blob_sha(path, args.commit if args.commit != "HEAD" else "HEAD")

        size_ok = (api_size == local_size)
        if args.no_sha or local_sha is None:
            sha_ok = None
        else:
            sha_ok = (api_sha == local_sha)

        if size_ok and (sha_ok is None or sha_ok):
            ok_cnt += 1
            rows.append((path, local_size, api_size, short(api_sha), "✅", ""))
        else:
            bad_cnt += 1
            note = []
            if not size_ok:
                note.append("字节数不符")
            if sha_ok is False:
                note.append("SHA 不符")
            rows.append((path, local_size, api_size, short(api_sha), "❌", "/".join(note)))

    # 输出表格
    w = max([len(r[0]) for r in rows] + [30])
    print("%-*s  %12s  %12s  %-9s  %s" % (w, "文件", "本地字节", "线上字节", "SHA(前7)", "状态"))
    print("-" * (w + 12 + 12 + 11 + 24))
    for path, ls, rs, sh, flag, note in rows:
        print("%-*s  %12s  %12s  %-9s  %s %s" % (w, path, ls, rs, sh, flag, note))

    print()
    if bad_cnt == 0:
        print(OK + "✅ 全部一致（%d/%d）—— 线上内容 = 本地内容" % (ok_cnt, len(rows)) + RESET)
        return 0
    else:
        print(BAD + "❌ %d 个文件不一致 / 校验失败（通过 %d/%d）" % (bad_cnt, ok_cnt, len(rows)) + RESET)
        print(WARN + "  排查：① 是否忘记 git add -f（deploy/ 与 output/ 被 .gitignore 忽略）"
                    "② 是否根目录与 deploy/ 只更新了一处 ③ 稍后重试（Pages 构建有延迟）" + RESET)
        return 1


if __name__ == "__main__":
    sys.exit(main())
