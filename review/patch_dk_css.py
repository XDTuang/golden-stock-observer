#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dk-* 语义色样式补丁（2026-09-22 新增）

【为什么需要】
① 老站「每日复盘」tab 内的 `#drFeedReview` 富文本卡片，是 `#drAnalysis` 的**兄弟节点**。
   `.dk-*` 语义色原本只定义在 analysis.html 的 `<style>` 里，而该 style 经
   `drScopeInjectedStyles()` 作用域化到 `#drAnalysis`（防整站串色，见铁律 10）→
   `#drFeedReview` 内拿不到 `.dk-*` 定义 → **放行了标签也没有颜色**。
   V3 页同类：6 个类有定义，缺 `.dk-up`。
② 🔴 **容器规则会吃掉语义色**（2026-09-22 实测）：V3 有 `.dr-note b{color:var(--text)}`
   （特异性 0,1,1）> `.dk-main{…}`（0,1,0）→ `<b class="dk-main">` 被压回正文色，
   而 `SPAN.dk-caution`（不被该规则命中）却是好的 —— 表现为「同类不同色」的诡异现象。
   修法取**源头**（而非 `!important` 升级）：给该规则加 `:not([class*="dk-"])` 守卫 ——
   保留「裸 <b> 用正文色」的原意，语义色 <b> 自动豁免。
   （不用 `!important` 是为了不改变 `#drAnalysis` 内的配色：那里用 analysis.html 自己的色板，
     全局 `!important` 会把它换成主站色板 → 无谓的视觉变更。）

【归属约定（确定性，防双源）】
  · 老站 3 份：7 条规则**由标记块 `DK-SEMANTIC-CSS v1` 承载**（块外如有同名规则则删除）
  · V3 4 份：7 条规则**就地独立承载**（不留标记块；缺的插在 `.dk-dn` 之后）
取值唯一权威 = 本文件的 RULES；守卫 check_index_render [8/9] 断言各页与其逐字一致。

用法:
  python3 review/patch_dk_css.py            # 应用
  python3 review/patch_dk_css.py --check    # 只校验（不一致退出码 1）
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 权威取值（唯一来源）──
RULES = [
    ("dk-main", "color:var(--red);font-weight:600"),
    ("dk-caution", "color:var(--orange);font-weight:600"),
    ("dk-risk", "color:var(--green);font-weight:700"),
    ("dk-data", "color:var(--blue);font-weight:600"),
    ("dk-neutral", "color:var(--text-muted)"),
    ("dk-dn", "color:var(--green)"),
    ("dk-up", "color:var(--red);font-weight:600"),
]
DECL = dict(RULES)

# ── 容器规则的守卫化（2026-09-22）──
# V3 有 `.dr-note b{color:var(--text)}`（特异性 0,1,1）> `.dk-main{…}`（0,1,0）
# → `<b class="dk-main">` 被压回正文色，而 `SPAN.dk-caution` 不受该规则命中却是好的，
#   表现为「同类不同色」的诡异现象。
# 修法取**源头**而非 `!important`：给该规则加 `:not([class*="dk-"])`，
# 让「裸 <b> 用正文色」的原意保留、语义色 <b> 自动豁免。
# （不加 !important 是为了不改变 #drAnalysis 内的配色 —— 那里用的是 analysis.html 自己的色板）
GUARD_OLD = ".dr-note b{color:var(--text)}"
GUARD_NEW = '.dr-note b:not([class*="dk-"]){color:var(--text)}'
GUARD_RE = re.compile(r"\.(dr-note|dr-tag|dr-h|dr-wrap|rc-block)[^{,]*\b(b|span|i)\s*\{[^}]*color")

MARK_B = "/* ═══ DK-SEMANTIC-CSS v1（review/patch_dk_css.py 维护 · 勿手改）═══ */"
MARK_E = "/* ═══ /DK-SEMANTIC-CSS v1 ═══ */"
ANCHOR_OLD = (".dr-card{background:var(--bg-card);border:1px solid var(--border);"
              "border-radius:10px;padding:14px 16px;margin:12px 0}\n</style>")

TARGETS_OLD = ["index.html", "index_template.html", "deploy/index.html"]
TARGETS_V3 = ["review_v3/index.html", "review_v3/index_hide89.html",
              "deploy/review_v3/index.html", "deploy/review_v3/index_hide89.html"]

RULE_RE = lambda n: re.compile(r"\." + re.escape(n) + r"\s*\{[^}]*\}")
canon = lambda n: "." + n + "{" + DECL[n] + "}"


def block_all():
    lines = [MARK_B,
             "/* 语义色（A 股涨红跌绿）；冲突方（如 V3 .dr-note b）已加 :not([class*=dk-]) 守卫 */"]
    lines += [canon(n) for n, _ in RULES]
    lines.append(MARK_E)
    return "\n".join(lines)


def process_old(rel, apply=True):
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        return False, f"❌ {rel} 不存在"
    t = open(p, encoding="utf-8").read()
    orig = t

    if MARK_B in t:                       # 块承载：块内重建 + 清掉块外同名重复
        i = t.index(MARK_B)
        j = t.index(MARK_E, i) + len(MARK_E)
        head, tail = t[:i], t[j:]
        for n, _ in RULES:
            head = RULE_RE(n).sub("", head)
            tail = RULE_RE(n).sub("", tail)
        t = head.rstrip("\n") + "\n" + block_all() + "\n" + tail.lstrip("\n")
    else:                                 # 无块：全量插入
        if t.count(ANCHOR_OLD) != 1:
            return False, f"❌ {rel}: 锚点命中 {t.count(ANCHOR_OLD)} 次（应 1）"
        t = t.replace(ANCHOR_OLD, ANCHOR_OLD.replace("\n</style>", "\n" + block_all() + "\n</style>"), 1)

    changed = t != orig
    if apply and changed:
        open(p, "w", encoding="utf-8").write(t)
    return changed, f"{rel}：老站块承载 7 条" + ("（已归一化）" if changed else "（已是最新）")


def process_v3(rel, apply=True):
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        return False, f"❌ {rel} 不存在"
    t = open(p, encoding="utf-8").read()
    orig = t

    # ① 去掉标记块（V3 改为独立承载）
    if MARK_B in t:
        i = t.index(MARK_B)
        j = t.index(MARK_E, i) + len(MARK_E)
        t = t[:i].rstrip("\n") + "\n" + t[j:].lstrip("\n")

    # ② 容器规则守卫化（防 `.dr-note b` 之类压掉语义色）
    if GUARD_OLD in t:
        t = t.replace(GUARD_OLD, GUARD_NEW, 1)

    # ③ 逐条归一化；缺失的插到 .dk-dn 之后
    for n, _ in RULES:
        want = canon(n)
        m = RULE_RE(n).search(t)
        if m:
            if m.group(0) != want:
                t = t[:m.start()] + want + t[m.end():]
        else:
            anchor = canon("dk-dn")
            if anchor not in t:
                return False, f"❌ {rel}: 缺锚点 {anchor}，无法插入 .{n}"
            t = t.replace(anchor, anchor + "\n" + want, 1)

    changed = t != orig
    if apply and changed:
        open(p, "w", encoding="utf-8").write(t)
    return changed, f"{rel}：V3 独立承载 7 条" + ("（已归一化）" if changed else "（已是最新）")


def main():
    check = "--check" in sys.argv
    changed, problems = [], []
    for rel in TARGETS_OLD:
        try:
            ch, note = process_old(rel, apply=not check)
        except Exception as e:
            problems.append(f"{rel}: {type(e).__name__} {e}")
            continue
        if note.startswith("❌"):
            problems.append(note)
        elif ch:
            changed.append(note)
    for rel in TARGETS_V3:
        try:
            ch, note = process_v3(rel, apply=not check)
        except Exception as e:
            problems.append(f"{rel}: {type(e).__name__} {e}"); continue
        if note.startswith("❌"):
            problems.append(note)
        elif ch:
            changed.append(note)

    print(f"{'── 校验模式（未写盘）──' if check else '── 应用模式 ──'}")
    for c in changed:
        print("  " + ("⚠️ " if check else "✅ ") + c)
    if not changed:
        print("  （无变化 —— 7 份页面均已归一化）")
    if problems:
        print("\n❌ 问题：")
        for x in problems:
            print("   · " + x)
        return 1
    if check and changed:
        print(f"\n❌ --check：有 {len(changed)} 处未同步（跑 python3 review/patch_dk_css.py 应用）")
        return 1
    print("\n✅ dk-* 语义色已归一化（老站 3 块承载 + V3 4 独立承载 · 7 条规则）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
