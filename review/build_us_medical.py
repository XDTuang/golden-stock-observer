#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""美股医疗 / CXO 映射段生成器（2026-09-18 新增）

【为什么是生成器而不是手写】
老站 analysis.html 的 3 段（隔夜美股复盘）**每天被盘前/夜间推演重写**，
手写的表格次日即被覆盖（同 7.1b / 7.2 的教训）。
因此本模块以「显式块标记 + 幂等注入」方式把医疗/CXO 映射表挂进 3 段末尾，
块由脚本生成、可重复运行、可入 CI 校验。

【数据源】data/daily_review/market.json
  · quotes    → 9/17 收盘价与涨跌幅（gtimg，2026-09-18 起含美股医疗组）
  · us_kline  → 双日（prev / latest）收盘，驱动「前一日 → 最新」对照

【对标口径】美股医疗各环节 → A股/港同环节标的（见 MED_LIST 的 cn 字段）

用法：
  python3 review/build_us_medical.py            # 注入 analysis.html（根 + deploy 双写）
  python3 review/build_us_medical.py --check    # 只校验块是否在位（不写盘，不一致退出 1）
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET = os.path.join(BASE, "data", "daily_review", "market.json")
TARGETS = [
    "data/daily_review/analysis.html",
    "deploy/data/daily_review/analysis.html",
]
BEGIN = "<!-- US-MEDICAL-BEGIN（由 review/build_us_medical.py 生成 · 勿手改） -->"
END = "<!-- US-MEDICAL-END -->"
ANCHOR = "<!-- 4 "  # 注入点：3 段末尾（4 段之前）

# (key, 显示名, 分组, A股/港对标)
MED_LIST = [
    ("us_crl",  "CRL 查尔斯河",  "CRO·临床前",  "昭衍新药 603127 / 美迪西 688202"),
    ("us_iqv",  "IQV 艾昆纬",    "CRO·临床",    "泰格医药 300347（临床 CRO + 数据）"),
    ("us_iclr", "ICLR 艾可龙",   "CRO·临床",    "泰格医药 300347 / 诺思格 301333"),
    ("us_medp", "MEDP 麦德派斯", "CRO·临床",    "泰格医药 300347（临床弹性）"),
    ("us_tmo",  "TMO 赛默飞",    "CDMO",        "凯莱英 002821 / 博腾股份 300363"),
    ("us_dhr",  "DHR 丹纳赫",    "生物工艺",    "药明生物 2269.HK / 东富龙 300171"),
    ("us_rgen", "RGEN 瑞普利金", "生物工艺",    "纳微科技 688690 / 东富龙 300171"),
    ("us_lh",   "LH 徕博科",     "诊断",        "金域医学 603882 / 迪安诊断 300244"),
    ("us_lly",  "LLY 礼来",      "参考·大药企", "诺泰生物 688076 / 翰宇药业 300199（GLP-1）"),
    ("us_wst",  "WST 西氏医药",  "参考·耗材",   "山东药玻 600529 / 康德莱 603987"),
]
CORE = [k for k, _, g, _ in MED_LIST if not g.startswith("参考")]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_block(mkt):
    q = mkt.get("quotes", {})
    k = mkt.get("us_kline", {})
    latest_date = prev_date = ""
    rows, stats = [], []
    for key, name, group, cn in MED_LIST:
        e = k.get(key) or {}
        lo, pr = e.get("latest") or {}, e.get("prev") or {}
        lc, pc = _f(lo.get("close")), _f(pr.get("close"))
        latest_date = latest_date or (lo.get("date") or "")
        prev_date = prev_date or (pr.get("date") or "")
        if lc is None or pc is None:
            rows.append((name, group, cn, "—", "—", None))
            continue
        chg = (lc / pc - 1) * 100 if pc else None
        rows.append((name, group, cn, f"{pc:,.2f}", f"{lc:,.2f}", chg))
        if key in CORE and chg is not None:
            stats.append((name, chg))

    def cls(v):
        return "dr-up" if (v or 0) >= 0 else "dr-dn"

    # ── 组内统计（仅核心 8 只）──
    n = len(stats)
    avg = sum(v for _, v in stats) / n if n else 0.0
    ups = sum(1 for _, v in stats if v > 0)
    best = max(stats, key=lambda x: x[1]) if stats else ("—", 0)
    worst = min(stats, key=lambda x: x[1]) if stats else ("—", 0)
    strong = "偏强" if avg > 1 else ("中性" if avg > -1 else "偏弱")
    tone = ("内部分化明显，未形成板块级共振" if ups in (3, 4, 5)
            else ("普涨，映射偏正向" if ups >= 6 else "普跌，映射偏负向"))

    h = [BEGIN]
    h.append(f'<div class="dr-tag" style="margin:12px 0 4px">美股医疗 / CXO 映射（{prev_date or "—"} → {latest_date or "—"} · 与 A股同环节对标）</div>')
    h.append('<div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--accent);padding:8px 12px;border-radius:6px;font-size:12.5px;line-height:1.6">')
    h.append(f'<b>组内读数（核心 {n} 只）：</b>均值 <span class="{cls(avg)}"><b>{avg:+.2f}%</b></span>，'
             f'上涨 {ups}/{n}（{tone}）→ 整体<b class="{cls(avg)}">{strong}</b>；'
             f'最强 <b>{best[0]}</b> <span class="{cls(best[1])}"><b>{best[1]:+.2f}%</b></span>、'
             f'最弱 <b>{worst[0]}</b> <span class="{cls(worst[1])}"><b>{worst[1]:+.2f}%</b></span>。'
             f'<br><b>映射提示：</b>CRO（临床前/临床）对应 A股 泰格医药·昭衍新药·美迪西；'
             f'CDMO（TMO）对应凯莱英·博腾；生物工艺（DHR·RGEN）对应纳微科技·东富龙；'
             f'诊断（LH）对应金域医学·迪安诊断。'
             f'<span class="dk-caution">医疗映射的外生性弱于科技（无算力资本开支式强联动），宜作「同环节情绪参照」而非直接线性外推。</span>')
    h.append('</div>')
    h.append('<table class="dr-tbl">')
    h.append(f'<thead><tr><th>标的</th><th>环节</th><th>{prev_date or "前一日"} 收盘</th>'
             f'<th>{latest_date or "最新"} 收盘</th><th>涨跌</th><th>A股/港同环节对标</th></tr></thead>')
    h.append('<tbody>')
    for name, group, cn, pc_s, lc_s, chg in rows:
        chg_html = (f'<td class="{cls(chg)}"><b>{chg:+.2f}%</b></td>' if chg is not None
                    else '<td>—</td>')
        h.append(f'      <tr><td><b>{name}</b></td><td>{group}</td><td>{pc_s}</td>'
                 f'<td><b>{lc_s}</b></td>{chg_html}<td class="dr-wrap">{cn}</td></tr>')
    h.append('</tbody></table>')
    h.append('<div class="dr-note" style="font-size:12.5px;line-height:1.6;margin-top:6px">'
             '<b>使用说明：</b>本表由 <code>review/build_us_medical.py</code> 从 '
             '<code>market.json</code>（quotes + us_kline）生成，随每日抓取自动更新；'
             '表中「涨跌」为 <b>最新已收盘交易日</b>相对前一交易日的变动，'
             '对应 A股 的 <b>次日</b> 映射源。<b class="dk-caution">单日涨跌不构成方向判断，'
             'CXO 板块宜结合订单/指引（如药明康德 585-605 亿指引）与政策（BINSA 法案）综合看。</b></div>')
    h.append(END)
    return "\n".join(h)


def inject(path, block):
    full = os.path.join(BASE, path)
    if not os.path.exists(full):
        return None, "❌ 文件不存在"
    src = open(full, encoding="utf-8").read()
    if BEGIN in src and END in src:
        s = src.index(BEGIN)
        e = src.index(END) + len(END)
        new = src[:s] + block + src[e:]
        act = "已更新块"
    else:
        i = src.find(ANCHOR)
        if i < 0:
            return None, f"❌ 未找到注入锚点 {ANCHOR!r}"
        new = src[:i] + block + "\n\n" + src[i:]
        act = "已插入块"
    return new, act


def main():
    check = "--check" in sys.argv
    mkt = json.load(open(MARKET, encoding="utf-8"))
    block = build_block(mkt)
    miss = [k for k, _, _, _ in MED_LIST if k not in (mkt.get("us_kline") or {})]
    print("=== 美股医疗 / CXO 映射段生成 ===")
    print(f"  标的 {len(MED_LIST)} 只（核心 {len(CORE)} + 参考 {len(MED_LIST)-len(CORE)}）"
          f" | us_kline 缺失 {len(miss)}{'：' + str(miss) if miss else ' ✓'}")
    print(f"  块长度 {len(block)} 字符")
    print()
    ok = True
    for p in TARGETS:
        full = os.path.join(BASE, p)
        cur = open(full, encoding="utf-8").read() if os.path.exists(full) else ""
        if check:
            hit = (BEGIN in cur and END in cur)
            print(f"  {'✅' if hit else '❌'} {p}：块{'在位' if hit else '缺失'}")
            ok = ok and hit
            continue
        new, act = inject(p, block)
        if new is None:
            print(f"  {act}（{p}）")
            ok = False
            continue
        if new != cur:
            open(full, "w", encoding="utf-8").write(new)
            print(f"  ✅ {act}（{p}）｜{len(cur)} → {len(new)} 字符")
        else:
            print(f"  ✅ 无变化（{p}）")
    print()
    print("✅ 校验通过" if ok else "❌ 校验未通过")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
