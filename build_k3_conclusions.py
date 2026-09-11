#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_k3_conclusions.py —— 7.1 段「结论句」语义色生成器

背景（2026-09-11 用户反馈）：
  7.1 段每行「内容」格的最后一句是结论句，原先只用 <b> 加粗，不够醒目，
  且无法区分「可执行 / 有条件 / 风险回避 / 待验证」四种不同性质的结论。

设计：结论句沿用 7.1 表格第二列已有的 dr-up(红)/dr-caution(橙)/dr-dn(绿) 色系，
      再加蓝色承载「待验证·方法论」，形成四类语义色，与行内验证徽章呼应：

  k3c-go     可执行·相对占优    → 红（呼应 ✅ 真共振）
  k3c-cond   有条件·待确认      → 橙（呼应 ⚠️）
  k3c-risk   风险·回避          → 绿（呼应 ❌ 伪共振）
  k3c-verify 待验证变量·方法论  → 蓝（跨行，无对应徽章）

用法（SOP「步骤 3.6 · 7.1 段结论句上色」）：
  python3 build_k3_conclusions.py            # 生成 + 替换 root 与 deploy 副本（幂等）
  python3 build_k3_conclusions.py --dry-run  # 只报告分类结果，不写文件

幂等：已带 k3c 类的行自动跳过；CSS 块已存在则整块替换（不重复插入）。

⚠️ 分类为关键词规则，脚本会打印每一行的判定依据与未匹配告警，
   如新内容语气特殊导致误判，请人工在 analysis.html 里直接改 class 后重跑校验。
"""
import argparse
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
FILES = [BASE / "data" / "daily_review" / "analysis.html",
         BASE / "deploy" / "data" / "daily_review" / "analysis.html"]

CSS_MARK = "/* K3C-CONCLUSION-CSS v1"
K3C_CSS = """
/* K3C-CONCLUSION-CSS v1 · 7.1 段结论句语义色（四类，两主题通用） */
.k3c{display:block;margin:6px 0 1px;padding:5px 10px 5px 9px;border-radius:5px;
  border-left:3px solid;font-size:12.5px;line-height:1.62;font-weight:600}
.k3c-go{color:var(--red);background:rgba(231,76,60,.13);border-left-color:var(--red)}
.k3c-cond{color:var(--orange);background:rgba(245,158,11,.15);border-left-color:var(--orange)}
.k3c-risk{color:var(--green);background:rgba(22,163,74,.14);border-left-color:var(--green)}
.k3c-verify{color:var(--blue);background:rgba(76,139,245,.15);border-left-color:var(--blue)}
@media (prefers-color-scheme:dark){
  .k3c-go{background:rgba(231,76,60,.17)}
  .k3c-cond{background:rgba(245,158,11,.16)}
  .k3c-risk{background:rgba(22,163,74,.17)}
  .k3c-verify{background:rgba(76,139,245,.17)}
}
.k3c-legend{font-size:11.5px;color:var(--text-muted);margin:0 0 6px;
  display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.k3c-legend i{font-style:normal;display:inline-flex;align-items:center;gap:4px}
.k3c-legend i::before{content:"";width:9px;height:9px;border-radius:2px;display:inline-block}
.k3c-legend i.l-go::before{background:var(--red)}
.k3c-legend i.l-cond::before{background:var(--orange)}
.k3c-legend i.l-risk::before{background:var(--green)}
.k3c-legend i.l-verify::before{background:var(--blue)}
"""

LEGEND = ('<div class="k3c-legend">结论色标：'
          '<i class="l-go">可执行·相对占优</i>'
          '<i class="l-cond">有条件·待确认</i>'
          '<i class="l-risk">风险·回避</i>'
          '<i class="l-verify">待验证变量·方法论</i></div>')

# 分类规则：顺序敏感（宽泛的「但」放最后兜底）
RULES = [
    ("verify", ["验证变量", "需以", "不能用挂牌价当结论", "待验证条件"]),
    ("risk",   ["不追高", "不补仓", "不接刀", "反向压力", "资金流出",
                "不成立", "同步承压", "风险", "回避"]),
    ("go",     ["可作为", "可低吸", "可参与"]),
    ("cond",   ["但", "尚需", "未确认"]),
]


def classify(text):
    for cls, kws in RULES:
        for k in kws:
            if k in text:
                return cls, k
    return None, None


def section_bounds(html):
    i = html.find("7.1 · K3")
    j = html.find("<!-- 7.2 重点观测股")
    if i < 0 or j < 0 or j <= i:
        raise RuntimeError("定位 7.1 段失败（锚点 `7.1 · K3` / `<!-- 7.2 重点观测股` 缺失）")
    return i, j


def ensure_css(html):
    """CSS 幂等：已存在 → 从标记到 </style> 整块替换；不存在 → 插到 </style> 前"""
    if CSS_MARK in html:
        i = html.find(CSS_MARK)
        j = html.find("</style>", i)
        return html[:i] + K3C_CSS.strip() + "\n" + html[j:], False
    i = html.find("</style>")
    if i < 0:
        raise RuntimeError("analysis.html 未找到 </style>，无法注入样式")
    return html[:i] + K3C_CSS + html[i:], True


def apply_section(html, stats):
    i, j = section_bounds(html)
    seg = html[i:j]

    # 图例：插在 <table> 之前（必须在 table 外，否则被 foster-parent 移出）
    if "k3c-legend" not in seg:
        tb = seg.find('<table class="dr-tbl">')
        if tb < 0:
            raise RuntimeError('7.1 段未找到 <table class="dr-tbl">，无法插入图例')
        seg = seg[:tb] + LEGEND + "\n  " + seg[tb:]
        stats["legend"] = True

    def fix_row(m):
        row = m.group(0)
        tds = list(re.finditer(r"<td[^>]*>(.*?)</td>", row, re.S))
        if len(tds) < 3:
            return row
        td = tds[2]
        stats["rows"] += 1
        if 'class="k3c k3c-' in td.group(1):
            stats["already"] += 1
            stats["colored"] += 1
            return row
        bs = list(re.finditer(r"<b>(.*?)</b>", td.group(1), re.S))
        if not bs:
            stats["skip"].append(re.sub(r"<[^>]+>", "", tds[0].group(1))[:16])
            return row
        last = bs[-1]
        cls, hit = classify(last.group(1))
        if not cls:
            stats["unmatched"].append(last.group(1)[:40])
            return row
        new_b = f'<span class="k3c k3c-{cls}"><b>{last.group(1)}</b></span>'
        new_inner = td.group(1)[:last.start()] + new_b + td.group(1)[last.end():]
        m_open = re.match(r"<td[^>]*>", td.group(0))
        new_td = m_open.group(0) + new_inner + "</td>"
        stats[cls] += 1
        stats["colored"] += 1
        stats["hits"].append((cls, hit, last.group(1)[:26]))
        return row[:td.start()] + new_td + row[td.end():]

    seg = re.sub(r"<tr>.*?</tr>", fix_row, seg, flags=re.S)
    # 表头行（<th>）不计入数据行
    return html[:i] + seg + html[j:], seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    for p in FILES:
        if not p.exists():
            print(f"· 跳过（不存在）：{p}")
            continue
        html = p.read_text(encoding="utf-8")
        n0 = len(html)
        html, css_added = ensure_css(html)
        stats = {"go": 0, "cond": 0, "risk": 0, "verify": 0, "rows": 0,
                 "already": 0, "colored": 0, "skip": [], "unmatched": [],
                 "hits": [], "legend": False}
        html, seg = apply_section(html, stats)
        data_rows = len([1 for r in re.findall(r"<tr>(.*?)</tr>", seg, re.S)
                         if len(re.findall(r"<td", r)) >= 3])
        print(f"\n[{p.relative_to(BASE)}] {n0} → {len(html)} 字符"
              f" | CSS {'注入' if css_added else '已存在(整块替换)'}"
              f" | 图例 {'新增' if stats['legend'] else '已存在'}")
        print(f"   数据行 {data_rows} | 已上色 {stats['colored']}"
              f"（其中本次新增 {sum(stats[c] for c in ('go','cond','risk','verify'))}、"
              f"原有 {stats['already']}）")
        print(f"   分类：go={stats['go']} cond={stats['cond']} "
              f"risk={stats['risk']} verify={stats['verify']}")
        for cls, hit, txt in stats["hits"]:
            print(f"     {cls:6s} ← 「{hit}」 {txt}…")
        if stats["unmatched"]:
            print(f"   ⚠️ 未匹配 {len(stats['unmatched'])} 条（需人工指定 class）：")
            for u in stats["unmatched"]:
                print(f"      · {u}")
        if stats["skip"]:
            print(f"   ⚠️ 无 <b> 结论句、已跳过 {len(stats['skip'])} 行：{stats['skip']}")
        if not args.dry_run:
            p.write_text(html, encoding="utf-8")

    a = FILES[0].read_text(encoding="utf-8")
    b = FILES[1].read_text(encoding="utf-8")
    print(f"\n自检：root==deploy = {a == b} | K3C CSS 块数 = {a.count(CSS_MARK)}（须=1）"
          f" | k3c 结论条 = {a.count('class=\"k3c k3c-')}")
    if args.dry_run:
        print("（--dry-run：未写入）")


if __name__ == "__main__":
    main()
