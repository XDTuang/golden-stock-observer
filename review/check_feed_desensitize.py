#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投喂归档脱敏守卫（2026-11-12 立 · 用户拍板「私域聊天中人物名称归档一律脱敏」）
================================================================================
扫描 feed/archive/**/*.txt（+ deploy 镜像），检查是否残留**可识别人物/账号**的信息。

判定 6 类（任一命中即红灯）：
  1. 发送者署名   `·<名字>` 且下一行是日期 → 名字必须在白名单（群友/群友A…/超级专家/对话方/某大V…）
  2. 微信 ID      wxid_xxxx
  3. 本机路径     /Users/<用户名>/…（泄漏用户名与本地目录；可放宽为「仅 /Users 前缀」）
  4. 手机号       1[3-9]xxxxxxxxx（研报免责声明里的联系人手机同样算）
  5. 个人邮箱     local-part 非机构白名单（如 liusj@ / zhuxiaoyun@）→ 须掩码；机构邮箱（research@/service@）放行
  6. @ 提及       @<非泛称>（如 @91jerry）→ 须改 @群友

设计原则（对齐项目既有守卫风格）：
  · 只读扫描，**不改文件**；`--fix` 才落盘（掩码策略见 fix_text）
  · 纯标准库、无副作用；退出码 0 = 全绿 / 1 = 有残留（可入 CI / 每日链路）
  · 白名单集中在本文件顶部，新增泛称只改一处

用法：
  python3 review/check_feed_desensitize.py            # 扫描并报告
  python3 review/check_feed_desensitize.py --fix      # 掩码后落盘（root + deploy 双写）
  python3 review/check_feed_desensitize.py --limit 5  # 每类最多列 5 条样例
"""
import os
import re
import sys
import glob
import argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(BASE, "feed", "archive")
MIRROR = os.path.join(BASE, "deploy", "feed", "archive")

# ── 白名单（泛称）──────────────────────────────────────────────────────────
NAME_WHITELIST = {
    "群友", "群友A", "群友B", "群友C", "群友D", "群友E", "群友F", "群友G",
    "群友H", "群友I", "群友J", "群友K", "群友L", "群友M", "群友N", "群友O",
    "群友P", "群友Q", "群友R", "群友S", "群友T", "群友U", "群友V", "群友W",
    "群友X", "群友Y", "群友Z",
    "某群友", "某大V", "超级专家", "对话方", "专家", "分析师", "作者",
}
EMAIL_LOCAL_WHITELIST = {
    "research", "researchsh", "researchbj", "researchsz", "researchgz",
    "service", "support", "info", "sales", "contact", "ir", "master",
    "postmaster", "noreply", "no-reply", "admin", "office", "hr", "media",
}

# ── 正则 ─────────────────────────────────────────────────────────────────
RE_SENDER = re.compile(r"^([ \t]*)·(\S{1,20})[ \t]*\r?\n[ \t]*(\d{4}年\d{1,2}月\d{1,2}日)", re.M)
RE_GENERIC_NAME = re.compile(r"^群友[A-Z]{0,2}$")   # 群友 / 群友A / 群友AB
RE_WXID = re.compile(r"wxid_[A-Za-z0-9_-]{4,}")
RE_HOMEDIR = re.compile(r"/Users/[A-Za-z0-9._-]+/")
RE_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
RE_EMAIL = re.compile(r"([\w.+-]+)@([\w-]+\.[\w.]+)")
# @ 提及只认「ASCII 微信号式」handle：@91jerry / @abc_01；纯数字、带点（邮箱）、中文短语一律不算
RE_AT = re.compile(r"@([A-Za-z0-9_]{3,20})(?![A-Za-z0-9_.:-])")
AT_ALLOW = {"群友"} | {f"群友{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}


def is_generic_name(name: str) -> bool:
    return name in NAME_WHITELIST or bool(RE_GENERIC_NAME.match(name))


def iter_files():
    root = sorted(glob.glob(os.path.join(ARCHIVE, "**", "*.txt"), recursive=True))
    mirror = sorted(glob.glob(os.path.join(MIRROR, "**", "*.txt"), recursive=True))
    return root, mirror


def scan_text(text):
    """返回 [(kind, matched, line_no)]"""
    out = []
    for m in RE_SENDER.finditer(text):
        name = m.group(2)
        if not is_generic_name(name):
            out.append(("发送者署名", "·" + name, text[: m.start()].count("\n") + 1))
    for m in RE_WXID.finditer(text):
        out.append(("微信ID", m.group(0), text[: m.start()].count("\n") + 1))
    for m in RE_HOMEDIR.finditer(text):
        out.append(("本机路径", m.group(0), text[: m.start()].count("\n") + 1))
    for m in RE_PHONE.finditer(text):
        out.append(("手机号", m.group(0), text[: m.start()].count("\n") + 1))
    for m in RE_EMAIL.finditer(text):
        if m.group(1).lower() not in EMAIL_LOCAL_WHITELIST:
            out.append(("个人邮箱", m.group(0), text[: m.start()].count("\n") + 1))
    for m in RE_AT.finditer(text):
        h = m.group(1)
        if h.isdigit() or is_generic_name(h):
            continue
        out.append(("@提及", m.group(0), text[: m.start()].count("\n") + 1))
    return out


def fix_text(text):
    """就地掩码；返回 (新文本, 替换计数)"""
    n = 0

    text, k = re.subn(r"/Users/[A-Za-z0-9._-]+/(?:Library/[^\s\]\)]*|\.workbuddy/[^\s\]\)]*)",
                      "[本地路径已省略]", text)
    n += k
    text, k = re.subn(r"/Users/[A-Za-z0-9._-]+/Desktop/兜是宝/", "", text)
    n += k
    text, k = re.subn(r"/Users/[A-Za-z0-9._-]+/", "", text)
    n += k

    text, k = re.subn(r"wxid_[A-Za-z0-9_-]{4,}", "wxid_***", text)
    n += k

    def _phone(m):
        s = m.group(0)
        return s[:3] + "******" + s[-2:]
    text, k = re.subn(r"(?<!\d)1[3-9]\d{9}(?!\d)", _phone, text)
    n += k

    def _email(m):
        if m.group(1).lower() in EMAIL_LOCAL_WHITELIST:
            return m.group(0)
        return "***@" + m.group(2)
    text, k = re.subn(r"([\w.+-]+)@([\w-]+\.[\w.]+)", _email, text)
    n += k

    def _at(m):
        h = m.group(1)
        if h.isdigit() or is_generic_name(h):
            return m.group(0)
        return "@群友"
    text, k = re.subn(RE_AT.pattern, _at, text)
    n += k

    return text, n


def fix_sender_names(text):
    """把白名单外的发送者署名替换为 ·群友（保留后续日期行）"""
    n = 0

    def _sub(m):
        nonlocal n
        if is_generic_name(m.group(2)):
            return m.group(0)
        n += 1
        # 保留原缩进（嵌套发言用 4 空格缩进）
        return m.group(1) + "·群友\n" + m.group(3)
    return RE_SENDER.sub(_sub, text), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="掩码并落盘（root + deploy 双写）")
    ap.add_argument("--limit", type=int, default=3, help="每类样例条数")
    args = ap.parse_args()

    root_files, mirror_files = iter_files()
    if not root_files:
        print("❌ 未找到 feed/archive/**/*.txt")
        return 1

    total, per_file, kinds = 0, [], {}
    for f in root_files:
        text = open(f, encoding="utf-8", errors="ignore").read()
        hits = scan_text(text)
        if not hits:
            continue
        total += len(hits)
        rel = os.path.relpath(f, BASE)
        per_file.append((rel, len(hits), hits))
        for kind, _, _ in hits:
            kinds[kind] = kinds.get(kind, 0) + 1

    print(f"[1/2] 归档件 {len(root_files)}（deploy 镜像 {len(mirror_files)}）｜命中文件 {len(per_file)}｜命中项 {total}")

    if total:
        for kind, cnt in sorted(kinds.items(), key=lambda x: -x[1]):
            print(f"   · {kind}: {cnt}")
        for rel, cnt, hits in per_file:
            print(f"   → {rel}（{cnt}）")
            seen = set()
            for kind, s, ln in hits:
                if kind in seen:
                    continue
                seen.add(kind)
                print(f"        [{kind}] L{ln}  {s[:60]}")
                if len(seen) >= args.limit:
                    break

    if not args.fix:
        print("\n[2/2] 仅扫描（未改动）")
        if total:
            print("❌ 存在未脱敏残留 → 按「私域聊天人物名称一律脱敏」须先清理再入库")
            return 1
        print("✅ 全部归档件已脱敏")
        return 0

    # --fix
    changed = 0
    for f in root_files:
        text = open(f, encoding="utf-8", errors="ignore").read()
        new, n1 = fix_sender_names(text)
        new, n2 = fix_text(new)
        if new != text:
            open(f, "w", encoding="utf-8").write(new)
            changed += 1
            rel = os.path.relpath(f, BASE)
            mp = os.path.join(MIRROR, os.path.relpath(f, ARCHIVE))
            if os.path.exists(mp):
                open(mp, "w", encoding="utf-8").write(new)
                print(f"   ✎ {rel}（{n1 + n2} 处，root+deploy）")
            else:
                print(f"   ✎ {rel}（{n1 + n2} 处，仅 root）")
    print(f"\n[2/2] --fix 完成：改动 {changed} 件")

    # 复核
    remain = 0
    for f in root_files:
        if scan_text(open(f, encoding="utf-8", errors="ignore").read()):
            remain += 1
    if remain:
        print(f"❌ 仍有 {remain} 件残留（可能需人工判断）")
        return 1
    print("✅ 复扫全绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
