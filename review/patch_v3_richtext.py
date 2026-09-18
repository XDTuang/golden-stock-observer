#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V3 富文本白名单渲染补丁（2026-09-18 新增）

【背景 / 为什么有这个脚本】
review_v3/index.html 对 ai_synthesis 的全部内容统一走 esc() 转义
（esc 定义：& → &amp;，< → &lt;，> → &gt;）。
但 conclusion_first / theme_resonance / t1_radar / risks / holding_map
这些字段是**本机 agent 手写**的，含 <b> 强调与 <span class="dk-*"> 语义色
（与老站 analysis.html 同风格）。
→ 结果：标签被转义成 &lt;b&gt;，页面上直接显示字面「<b>…</b>」文字。
   2026-09-18 用户报「V3 线上版本有大量的 <b>  </b>」即此因。

【治本方案】
新增 rich()：先 esc() 整体转义，再**仅放行白名单标签**（b / i / br /
span[class=dk-*]），其余（含 <script>、带属性的任意标签）一律保持转义。
· agent 手写内容 → rich()（可着色、可加粗）
· 机器数据（日期 / 价格 / 代码 / 新闻标题）→ 仍用 esc()（不解析标签）

【幂等 & 门禁】
重复运行不产生变化；`--check` 只校验不写盘，不一致时退出码 1（可入 CI /
check_v3_style.py）。

【副本】
4 份同源：review_v3/index.html、review_v3/index_hide89.html、
deploy/review_v3/index.html、deploy/review_v3/index_hide89.html。
漏一份 = 线上（以 deploy/ 为根）仍是旧版。

用法：
  python3 review/patch_v3_richtext.py          # 应用补丁
  python3 review/patch_v3_richtext.py --check  # 只校验
"""
import os
import sys
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = [
    "review_v3/index.html",
    "review_v3/index_hide89.html",
    "deploy/review_v3/index.html",
    "deploy/review_v3/index_hide89.html",
]

MARK_BEGIN = "/* ═══════════ V3-RICHTEXT-BEGIN ═══════════ */"
MARK_END = "/* ═══════════ V3-RICHTEXT-END ═══════════ */"

# ── 插入块（锚点 = esc 定义行的下一行；显式标记，禁宽正则定位）──
BLOCK = MARK_BEGIN + r'''
/* 富文本白名单渲染（由 review/patch_v3_richtext.py 维护 · 勿手改）
   esc() 整体转义后，仅放行受控强调标签；其余一律保持转义（防 XSS）。
   dk-* 色板本页已定义（.dk-main/.dk-caution/.dk-risk/.dk-data/.dk-dn）。 */
const DKCLS = /^dk-(main|caution|risk|data|up|dn|neutral)$/;
const rich = (s) => esc(s == null ? '' : s)
  .replace(/&lt;(\/?)(b|i)&gt;/g, '<$1$2>')
  .replace(/&lt;br\s*\/?&gt;/g, '<br>')
  .replace(/&lt;span class="(dk-[a-z0-9-]+)"&gt;/g, (m, c) => (DKCLS.test(c) ? '<span class="' + c + '">' : m))
  .replace(/&lt;\/span&gt;/g, '</span>');
''' + MARK_END + "\n"

# ── 替换规则：(旧, 新, 预期出现次数) ──
#    只改「渲染 agent 手写内容」的调用点；机器数据的 esc() 一律不动。
RULES = [
    # renderConclusion（结论先行卡：标题 / 首句 / 正文）
    ("esc(title)", "rich(title)", 1),
    ("esc(lead)", "rich(lead)", 1),
    ("esc(rest)", "rich(rest)", 1),
    # 推演开盘格（正文取自 conclusion_first）
    ("esc(firstSentence)", "rich(firstSentence)", 1),
    # chips（related_stocks / holding_map.us 等，us 项含 <b>）
    ("esc(asTxt(x))", "rich(asTxt(x))", 1),
    # theme_resonance / t1_radar 的字符串项（2 处：主题共振 + 事件雷达）
    ("h += '<div class=\"dr-note\">· ' + esc(t) + '</div>';",
     "h += '<div class=\"dr-note\">· ' + rich(t) + '</div>';", 2),
    # theme_resonance 名称 / 描述
    ("esc(t.desc)", "rich(t.desc)", 1),
    ("esc(t.name || t.theme || '')", "rich(t.name || t.theme || '')", 1),
    # t1_radar 事件正文
    ("esc(t.event || t.text || t.desc || t.name || '')",
     "rich(t.event || t.text || t.desc || t.name || '')", 1),
    # risks 字符串项 / 描述
    ("if (typeof r === 'string') { h += '<div class=\"dr-note\">· ' + esc(r) + '</div>'; return; }",
     "if (typeof r === 'string') { h += '<div class=\"dr-note\">· ' + rich(r) + '</div>'; return; }", 1),
    ("esc(r.desc || '')", "rich(r.desc || '')", 1),
]

MIN_RICH = 12  # 渲染侧 rich( 调用点下限（不含定义行）


def patch_one(path, apply=True):
    """返回 (changed: bool, note: str)"""
    full = os.path.join(BASE, path)
    if not os.path.exists(full):
        return False, "❌ 文件不存在"
    src = open(full, encoding="utf-8").read()
    orig = src

    # ① 插入 rich() 定义（幂等：标记已在则跳过）
    if MARK_BEGIN not in src:
        lines = src.split("\n")
        idx = None
        for i, ln in enumerate(lines):
            if ln.startswith("const esc = "):
                idx = i
                break
        if idx is None:
            return False, "❌ 未找到 esc 定义锚点（结构可能已变）"
        # 兼容 CRLF/无尾随换行
        lines.insert(idx + 1, BLOCK.rstrip("\n"))
        src = "\n".join(lines)
        inserted = True
    else:
        inserted = False

    # ② 替换调用点
    applied, already, missing = 0, 0, []
    for old, new, expect in RULES:
        n_old = src.count(old)
        n_new = src.count(new)
        if n_old == 0:
            if n_new >= expect:
                already += 1
            else:
                missing.append((old, n_old, expect))
            continue
        src = src.replace(old, new)
        applied += 1

    if missing:
        detail = "；".join(f"{o!r} 期望{exp}处实际0处" for o, _, exp in missing)
        return False, f"❌ 锚点缺失：{detail}"

    # ③ 完整性：rich( 数量下限（定义行写作 `const rich = (s) =>`，不匹配 \brich\( ）
    n_rich = len(re.findall(r"\brich\(", src))
    if n_rich < MIN_RICH:
        return False, f"❌ rich( 调用点仅 {n_rich} 处（< {MIN_RICH}），补丁不完整"

    changed = src != orig

    if apply:
        if changed:
            open(full, "w", encoding="utf-8").write(src)
        tag = "已应用" if changed else "已是最新"
        return True, f"✅ {tag}（{path}｜rich 调用点 {n_rich} 处）"

    # ── 校验模式：必须基于**原文件**状态判定（不能在内存改完后自评，否则永远通过）──
    n_rich_orig = len(re.findall(r"\brich\(", orig))
    if changed:
        return False, f"❌ 未应用（{path}｜rich 调用点 {n_rich_orig} 处，应为 {MIN_RICH}）"
    if MARK_BEGIN not in orig or n_rich_orig < MIN_RICH:
        return False, f"❌ 定义/调用点不完整（{path}｜rich {n_rich_orig} 处）"
    return True, f"✅ 已应用（{path}｜rich 调用点 {n_rich_orig} 处）"


def main():
    check = "--check" in sys.argv
    print("=== V3 富文本白名单渲染补丁 ===")
    print("模式:", "校验（不写盘）" if check else "应用")
    print()
    bad = 0
    for p in TARGETS:
        ok, note = patch_one(p, apply=not check)
        print(" ", note)
        if not ok:
            bad += 1
    # 副本一致性（4 份应同源）
    import hashlib
    digests = {}
    for p in TARGETS:
        full = os.path.join(BASE, p)
        if os.path.exists(full):
            digests[p] = hashlib.md5(open(full, "rb").read()).hexdigest()
    uniq = set(digests.values())
    print()
    if len(uniq) == 1:
        print(f"  副本一致性：✅ 4 份同源（md5 {list(uniq)[0][:12]}）")
    else:
        print("  副本一致性：⚠️ 4 份不同源")
        for p, h in digests.items():
            print(f"    {p}: {h[:12]}")
    print()
    if bad or len(uniq) != 1:
        print("❌ 补丁校验未通过")
        return 1
    print("✅ 补丁校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
