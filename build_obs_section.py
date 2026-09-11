#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7.2 段「重点观测股推演」生成器（分层版 v1）
================================================
把 analysis.html 的 7.2 段由「agent 手写静态大表」升级为
「脚本机械生成 + 原生 <details> 可折叠卡片（分层 L1/L2）」。

分层设计（用户 2026-09-11 拍板）：
  L1 · 全池关键位（32 只）   = 从 obs_deduce_latest.json **机械计算**，零人工估计、日期自动滚动
  L2 · 重点票完整三情景(5-8) = agent 提供 output/obs_scenarios.json（机制路径 + 推测专家操作）

交互实现：原生 <details> + 纯 CSS —— 不依赖 JS。
  原因：analysis.html 经 `ana.innerHTML = t` 注入后 <script> 不执行，但 <style>
  会被 drScopeInjectedStyles 作用域化后生效 → 纯 CSS 方案可行且零铁律风险。

红线处理（用户拍板「委婉处理」）：
  L1 的触发线 = 纯客观技术表述（"失守 MA5 看 MA10"），不含动作词；
  L2 的动作列标题为「推测专家操作」，主语明确为专家，段首声明不构成对读者的建议。

输入：
  output/obs_deduce_latest.json    观测池客观读数（或 --data-date 指定的历史快照）
  output/obs_scenarios.json        L2 情景（可选；缺失则只出 L1）
输出：
  data/daily_review/analysis.html  7.2 段替换（+ deploy 副本同步）
  output/obs_section.html          生成片段（调试/预览用）
  output/obs_panel.json            🔴 V3 第 6 段专用**配对载荷**（+ deploy 副本）
                                   = {data_date, for_date, scen_data_date, items, picks}
                                   由「本次运行实际用的那份 obs_deduce 快照」+「obs_scenarios.picks」
                                   **同一次运行配对**产出 → V3 只读这一个文件，L1/L2 数据日必然一致。
                                   起因（2026-09-11）：V3 原本自己在运行时分别读 latest 与 scenarios，
                                   而 obs_deduce_latest 会被盘后任务刷成当日、情景却是上一交易日口径
                                   → 卡片上「9/11 的收盘价」配「9/10 的情景价位」。配对责任交给生成端。

用法：
  python3 build_obs_section.py               # 生成并替换（root + deploy）
  python3 build_obs_section.py --dry-run     # 只写 output/obs_section.html，不动 analysis.html
  python3 build_obs_section.py --panel-only  # 只产出 obs_panel.json，不动 analysis.html
  python3 build_obs_section.py --no-deploy   # 只改 root，不同步 deploy

🔴 盘前推演必须带 --data-date <上一交易日>：obs_deduce_latest.json 永远是最新交易日，
   而盘前页面用上一交易日口径；不带参数会数据日错位（脚本已内置「scen.data_date ≠ obs.date 即报错退出」防呆）。
"""
import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
OBS_JSON = BASE / "output" / "obs_deduce_latest.json"
HIST = BASE / "data" / "daily_review_history"
SCEN_JSON = BASE / "output" / "obs_scenarios.json"
ROOT_HTML = BASE / "data" / "daily_review" / "analysis.html"
DEPLOY_HTML = BASE / "deploy" / "data" / "daily_review" / "analysis.html"
FRAG_OUT = BASE / "output" / "obs_section.html"
PANEL_OUT = BASE / "output" / "obs_panel.json"
PANEL_DEPLOY = BASE / "deploy" / "output" / "obs_panel.json"

# V3 第 6 段渲染实际用到的字段（超集即冗余 → 载荷只带这些，明确契约、顺带瘦身）
PANEL_FIELDS = ("code", "name", "sector", "close", "chg_last", "ma5", "ma10",
                "high10", "low10", "pattern", "dev_ma5", "chg5", "vol_ratio",
                "trend", "open_label")

START_ANCHOR = "<!-- 7.2 重点观测股"
# 2026-09-11 修正：原为 "<!-- 7.4 操作预案" —— 那是**迁就错误顺序**（7.2→7.4→7.3）。
#   已把 analysis.html 重排为 7.1→7.2→7.3→7.4（用户报「7 段排在 7.4 后、7.3 未见」），
#   故结束锚点随之改为 7.2 的**下一段** = 7.3。两者必须同时改，否则切片会吃掉错内容。
END_ANCHOR = "<!-- 7.3 次日开盘指引"
CSS_MARK = "/* OBS-FOLD-CSS v1"

# ---------------------------------------------------------------- CSS

OBS_CSS = """
/* OBS-FOLD-CSS v1 · 7.2 段可折叠卡片（纯 CSS，不依赖 JS） */
.obs-sec{font-size:12.5px;font-weight:600;color:var(--text-secondary);margin:14px 0 6px;
  padding-left:8px;border-left:3px solid var(--accent);line-height:1.4}
.obs-list{display:flex;flex-direction:column;gap:5px}
.obs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:5px;align-items:start}
details.obs-fold{background:var(--bg-subtle);border:1px solid var(--border);border-radius:7px;overflow:hidden}
details.obs-fold>summary{cursor:pointer;list-style:none;display:flex;align-items:center;
  gap:6px;flex-wrap:wrap;font-size:12.5px;padding:6px 10px;user-select:none}
details.obs-fold>summary::-webkit-details-marker{display:none}
details.obs-fold>summary:hover{background:var(--bg-card)}
details.obs-fold[open]>summary{border-bottom:1px solid var(--border);background:var(--bg-card)}
.obs-cv,.obs-cd,.obs-sc,.obs-bd,.obs-px,.ob-tag{font-size:11.5px}
.obs-nm{font-weight:700;color:var(--text)}
.obs-cv{margin-left:auto;color:var(--text-muted);line-height:1;transition:transform .15s ease}
details.obs-fold[open] .obs-cv{transform:rotate(90deg)}
.obs-cd{color:var(--text-muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.obs-sc{color:var(--text-muted)}
.obs-bd{border-radius:3px;padding:1px 5px;white-space:nowrap;line-height:1.5}
.obs-bd.b-up{background:rgba(231,76,60,.13);color:var(--red)}
.obs-bd.b-dn{background:rgba(22,163,74,.13);color:var(--green)}
.obs-bd.b-ms{background:rgba(245,158,11,.15);color:var(--orange)}
.obs-px{color:var(--text-secondary);font-variant-numeric:tabular-nums}
.obs-kl,.obs-line{font-size:12.5px}
.obs-body{padding:9px 11px 11px;font-size:12.5px}
.obs-kl{display:flex;flex-wrap:wrap;gap:5px 12px;color:var(--text-secondary);
  padding:7px 9px;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;margin-bottom:8px}
.obs-kl b{font-variant-numeric:tabular-nums}
.obs-kl .kl-s{border-left:3px solid var(--green);padding-left:6px}
.obs-kl .kl-r{border-left:3px solid var(--red);padding-left:6px}
.obs-kl .kl-n{border-left:3px solid var(--blue);padding-left:6px}
.obs-line{color:var(--text-secondary);line-height:1.65;
  background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:7px 9px}
.obs-rsn{color:var(--text-muted);margin-bottom:7px}
table.obs-stbl{margin:0;table-layout:fixed;width:100%}
table.obs-stbl col.cc1{width:17%}
table.obs-stbl col.cc2{width:7%}
table.obs-stbl col.cc3{width:46%}
table.obs-stbl col.cc4{width:30%}
table.obs-stbl th,table.obs-stbl td{text-align:left;font-size:12.5px}
table.obs-stbl td{vertical-align:top;line-height:1.6}
table.obs-stbl td.ob-p{text-align:center;white-space:nowrap;font-weight:700;font-variant-numeric:tabular-nums}
.ob-tag{display:inline-block;min-width:13px;text-align:center;border-radius:3px;
  font-weight:700;padding:0 4px;margin-right:5px;line-height:1.7}
.ob-tag-a{background:rgba(231,76,60,.15);color:var(--red)}
.ob-tag-b{background:rgba(245,158,11,.18);color:var(--orange)}
.ob-tag-c{background:rgba(22,163,74,.15);color:var(--green)}
.obs-sum{font-size:12.5px;color:var(--text-secondary);line-height:1.6;margin-top:6px;
  background:var(--bg-subtle);border-radius:6px;padding:8px 11px;border-left:3px solid var(--accent)}
"""

# ---------------------------------------------------------------- 计算

def _f(v, nd=2):
    """安全格式化数字"""
    if v is None:
        return "—"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def _cls_pct(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    return "dr-up" if x > 0 else ("dr-dn" if x < 0 else "")


def _sgn(v, nd=2):
    try:
        return f"{float(v):+.{nd}f}%"
    except (TypeError, ValueError):
        return "—"


def badge_class(pattern):
    if pattern == "多头排列":
        return "b-up"
    if pattern == "空头排列":
        return "b-dn"
    return "b-ms"


def short_badge(pattern):
    return {"多头排列": "多头", "空头排列": "空头"}.get(pattern, "震荡")


def key_levels(x):
    """从 obs_deduce 原始字段机械推导关键位（零人工估计）"""
    close, ma5, ma10 = x.get("close"), x.get("ma5"), x.get("ma10")
    low10, high10 = x.get("low10"), x.get("high10")
    pattern = x.get("pattern", "")

    if pattern == "多头排列":
        break_line, bl_note = ma10, "失守 MA10"
    elif pattern == "空头排列":
        break_line, bl_note = low10, "跌破近 10 日低"
    else:
        break_line, bl_note = low10, "跌破区间下沿"

    return {
        "close": close, "ma5": ma5, "ma10": ma10,
        "low10": low10, "high10": high10,
        "break_line": break_line, "break_note": bl_note,
        "dev_ma5": x.get("dev_ma5"),
    }


def trigger_line(x, k):
    """纯客观技术触发线（不含任何动作词）——红线安全表述"""
    pattern = x.get("pattern", "")
    ma5, ma10 = _f(k["ma5"]), _f(k["ma10"])
    low10, high10 = _f(k["low10"]), _f(k["high10"])
    if pattern == "多头排列":
        return (f"守 <b>{ma5}</b>(MA5) 则形态延续 ｜ 失守下看 <b>{ma10}</b>(MA10) "
                f"｜ 跌破 <b>{low10}</b>（近 10 日低）结构转弱")
    if pattern == "空头排列":
        return (f"站上 <b>{ma5}</b>(MA5) 才算修复启动 ｜ <b>{ma10}</b>(MA10) 为反弹压力 "
                f"｜ 跌破 <b>{low10}</b> 创近 10 日新低")
    return (f"区间 <b>{low10}</b>~<b>{high10}</b> ｜ 上破 <b>{high10}</b> 转强 "
            f"｜ 下破 <b>{low10}</b> 转弱")


def kl_html(x, k):
    """关键位色块（支撑绿 / 压力红 / 偏离蓝）"""
    dev = k["dev_ma5"]
    dev_s = _sgn(dev) if dev is not None else "—"
    dev_cls = "kl-r" if (dev or 0) > 3 else ("kl-s" if (dev or 0) < -3 else "kl-n")
    return (
        '<div class="obs-kl">'
        f'<span class="kl-s">支撑 <b>{_f(k["ma5"])}</b> MA5 ／ <b>{_f(k["ma10"])}</b> MA10</span>'
        f'<span class="kl-r">压力 <b>{_f(k["high10"])}</b> 近 10 日高</span>'
        f'<span class="kl-s">结构位 <b>{_f(k["low10"])}</b> 近 10 日低</span>'
        f'<span class="{dev_cls}">MA5 偏离 <b>{dev_s}</b></span>'
        f'<span class="kl-n">5 日 <b>{_sgn(x.get("chg5"))}</b></span>'
        f'<span class="kl-n">量比 <b>{_f(x.get("vol_ratio"))}</b></span>'
        '</div>'
    )


# ---------------------------------------------------------------- HTML

def build_l2(picks, by_code, data_date, for_date):
    """L2 · 重点票完整三情景（details 折叠）"""
    if not picks:
        return ""
    rows = []
    for p in picks:
        code = p["code"]
        x = by_code.get(code)
        if not x:
            continue
        k = key_levels(x)
        scs = p.get("scenarios", [])
        trs = []
        for s in scs:
            tag = s.get("tag", "")
            tg = tag[:1].upper()
            trs.append(
                f'<tr><td><span class="ob-tag ob-tag-{tg.lower()}">{tg}</span>{s.get("name","")}</td>'
                f'<td class="ob-p">{s.get("prob","")}%</td>'
                f'<td class="dr-wrap">{s.get("path","")}</td>'
                f'<td class="dr-wrap">{s.get("action","")}</td></tr>'
            )
        rsn = p.get("reason", "")
        rsn_html = f'<div class="obs-rsn">入选理由：{rsn}</div>' if rsn else ""
        rows.append(
            f'<details class="obs-fold">'
            f'<summary>'
            f'<span class="obs-nm">{x["name"]}</span>'
            f'<span class="obs-cd">{code[2:]}</span>'
            f'<span class="obs-sc">{x.get("sector","")}</span>'
            f'<span class="obs-bd {badge_class(x.get("pattern",""))}">{x.get("pattern","")} · {x.get("trend","")}</span>'
            f'<span class="obs-px">收 {_f(x.get("close"))} <b class="{_cls_pct(x.get("chg_last"))}">{_sgn(x.get("chg_last"))}</b></span>'
            f'<span class="obs-cv">▶</span>'
            f'</summary>'
            f'<div class="obs-body">{rsn_html}{kl_html(x, k)}'
            f'<table class="dr-tbl obs-stbl">'
            f'<colgroup><col class="cc1"><col class="cc2"><col class="cc3"><col class="cc4"></colgroup>'
            f'<thead><tr>'
            f'<th>情景</th><th>概率</th><th>路径（机制 + 价位）</th><th>推测专家操作</th>'
            f'</tr></thead><tbody>{"".join(trs)}</tbody></table>'
            f'</div></details>'
        )
    if not rows:
        return ""
    return (
        f'<div class="obs-sec">L2 · 重点票完整情景推演（{len(rows)} 只 · 点开看三情景 · 概率为主观判断）</div>'
        f'<div class="obs-list">{"".join(rows)}</div>'
    )


def build_l1(items, l2_codes):
    """L1 · 全池关键位（grid mini details；L2 票仍列出，标注「已在上方展开」）"""
    order = {"多头排列": 0, "震荡纠缠": 1, "空头排列": 2}
    srt = sorted(items, key=lambda x: (order.get(x.get("pattern", ""), 3), -(x.get("dev_ma5") or -99)))
    cards = []
    for x in srt:
        k = key_levels(x)
        code = x.get("code", "")
        mark = ' <span class="obs-cd">L2</span>' if code in l2_codes else ""
        cards.append(
            f'<details class="obs-fold">'
            f'<summary>'
            f'<span class="obs-nm">{x.get("name","")}</span>'
            f'<span class="obs-cd">{code[2:]}</span>{mark}'
            f'<span class="obs-bd {badge_class(x.get("pattern",""))}">{short_badge(x.get("pattern",""))}</span>'
            f'<span class="obs-px">{_f(x.get("close"))} <b class="{_cls_pct(x.get("chg_last"))}">{_sgn(x.get("chg_last"))}</b></span>'
            f'<span class="obs-cv">▶</span>'
            f'</summary>'
            f'<div class="obs-body">'
            f'<div class="obs-rsn">{x.get("sector","")} · {x.get("trend","")} · 开盘姿态「{x.get("open_label","—")}」</div>'
            f'{kl_html(x, k)}'
            f'<div class="obs-line">{trigger_line(x, k)}</div>'
            f'</div></details>'
        )
    return (
        f'<div class="obs-sec">L1 · 全池关键位总览（{len(items)} 只 · 点开看关键位与触发线）</div>'
        f'<div class="obs-grid">{"".join(cards)}</div>'
    )


def build_section(obs, scen):
    items = obs.get("items", [])
    by_code = {x["code"]: x for x in items}
    data_date = obs.get("date", "")
    for_date = (scen or {}).get("for_date", "")
    picks = (scen or {}).get("picks", [])
    l2_codes = {p["code"] for p in picks}

    n_l2 = len([p for p in picks if p["code"] in by_code])
    n_multi = sum(1 for x in items if x.get("pattern") == "多头排列")
    n_empty = sum(1 for x in items if x.get("pattern") == "空头排列")
    n_hk = sum(1 for x in items if x.get("code", "").startswith("hk"))

    head = (
        f'<!-- 7.2 重点观测股 -->\n'
        f'<div class="dr-h">7.2 · 重点观测股推演（obs_deduce 池 {len(items)} 只 · '
        f'数据日 {data_date} 收盘 · 分层 L1/L2 · 其他专家持股参考 · 非本人）</div>\n'
    )

    note = (
        '<div class="dr-note" style="font-size:12.5px">'
        '<b>口径：</b>价格 / 均线 / 技术位来自 <code>obs_deduce_latest.json</code>'
        f'（<b>数据日 {data_date} 收盘</b>）；<b>关键位全部由 MA5 / MA10 / 近 10 日高低点机械计算，'
        '无人工估计</b>；隔夜映射来自 <code>market.json.us_kline</code> 与 <code>review_v3/preopen_ext.json</code>。'
        '<br><b>分层：</b>L2 为重点票完整三情景（含机制路径与概率，概率为主观判断）；'
        'L1 为全池关键位与客观触发线。'
        '<br><b class="dk-risk">红线声明：本段全部标的均为「其他专家持股参考（非本人）」，'
        '内容为客观读数与对该类标的持有者常规操作的推测，仅用于理解其在盘中的可能行为，'
        '不构成对读者的任何买卖建议。</b>'
        '</div>'
    )

    l2 = build_l2(picks, by_code, data_date, for_date)
    l1 = build_l1(items, l2_codes)

    tail = (
        f'<div class="obs-sum"><b>池内结构：</b>{len(items)} 只（'
        f'{len(items)-n_hk} 只 A股 + {n_hk} 只港股）｜'
        f'<b class="dk-main">多头排列 {n_multi} 只</b>'
        f'｜震荡纠缠 {len(items)-n_multi-n_empty} 只'
        f'｜<b class="dk-risk">空头排列 {n_empty} 只（占比 {n_empty*100//max(len(items),1)}%）</b>。'
        f'形态与关键位为机械读数，未做方向性判断。</div>'
    )

    return head + '<div class="dr-card" style="margin-top:4px">' + note + l2 + l1 + tail + '</div>\n\n'


# ---------------------------------------------------------------- 配对载荷（V3 专用）

def build_panel(obs, scen, data_date, obs_src):
    """产出 V3 第 6 段用的配对载荷。

    关键：items 来自**本次运行实际用的那份快照**（可能是 --data-date 指定的历史文件），
    picks 来自 obs_scenarios —— 两者由同一次运行配对，V3 那边就不必再猜该用哪一天的数据。
    """
    items = obs.get("items", [])
    codes = {x.get("code") for x in items}
    picks_in = (scen or {}).get("picks", [])
    picks = [p for p in picks_in if p.get("code") in codes]
    dropped = [p.get("code") for p in picks_in if p.get("code") not in codes]

    slim = [{k: x.get(k) for k in PANEL_FIELDS} for x in items]
    return {
        "_schema": "obs_panel v1 · V3 第 6 段专用配对载荷（由 build_obs_section.py 产出）",
        "_howto": ("V3 读 ../output/obs_panel.json 即可，不要再分别读 obs_deduce_latest 与 obs_scenarios；"
                   "items 与 picks 已由同一次运行配对，data_date 即两者共同的数据日。"
                   "picks[].scenarios[].path/action 含 <b> 富文本，前端须「先整体转义再放行白名单标签」。"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": data_date,
        "for_date": (scen or {}).get("for_date", ""),
        "scen_data_date": (scen or {}).get("data_date", ""),
        "obs_source": str(obs_src.relative_to(BASE)) if str(obs_src).startswith(str(BASE)) else str(obs_src),
        "derive_engine": obs.get("derive_engine") or obs.get("source") or "",
        "count": len(items),
        "picks_count": len(picks),
        "dropped_picks": dropped,
        "items": slim,
        "picks": picks,
    }


def write_panel(panel, no_deploy=False):
    """写 obs_panel.json（root + deploy），返回 (root 路径, deploy 路径或 None)"""
    PANEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    PANEL_OUT.write_text(json.dumps(panel, ensure_ascii=False, indent=1), encoding="utf-8")
    dep = None
    if not no_deploy and PANEL_DEPLOY.parent.exists():
        PANEL_DEPLOY.write_text(PANEL_OUT.read_text(encoding="utf-8"), encoding="utf-8")
        dep = PANEL_DEPLOY
    return PANEL_OUT, dep


# ---------------------------------------------------------------- 注入

def ensure_css(html):
    """把 OBS 样式块插入 / 更新到 analysis.html 自包含 <style>（幂等且可迭代）"""
    start = html.find(CSS_MARK)
    if start >= 0:
        # 已有 → 整块替换（保证脚本迭代后样式同步更新）
        end = html.find("</style>", start)
        if end < 0:
            raise RuntimeError("OBS 样式块未找到收尾 </style>")
        return html[:start] + OBS_CSS.lstrip("\n") + html[end:], "updated"
    i = html.find("</style>")
    if i < 0:
        raise RuntimeError("analysis.html 未找到 </style>，无法注入样式")
    return html[:i] + OBS_CSS + html[i:], "added"


def replace_section(html, frag):
    i = html.find(START_ANCHOR)
    j = html.find(END_ANCHOR)
    if i < 0 or j < 0 or j <= i:
        raise RuntimeError(f"锚点定位失败：START={i} END={j}")
    return html[:i] + frag + html[j:]


def load_obs(data_date=None):
    """加载观测池。
    默认读 output/obs_deduce_latest.json（永远是最新交易日）。
    ⚠️ 盘前推演时「最新」可能已滚动到当日（如 9/11 盘前页面，观测池已被盘后任务刷成 9/11）→
       此时必须用 --data-date 显式指定，否则 L1 关键位会与页面其他段落的数据日不一致。
    """
    if not data_date:
        return json.loads(OBS_JSON.read_text(encoding="utf-8")), OBS_JSON
    d = HIST / data_date
    cands = sorted(d.glob("obs_deduce_*.json")) if d.exists() else []
    if not cands:
        raise SystemExit(f"✗ 未找到 {data_date} 的 obs_deduce（目录 {d} 不存在或无文件）")
    return json.loads(cands[-1].read_text(encoding="utf-8")), cands[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-date", help="指定观测池数据日（YYYY-MM-DD），从 data/daily_review_history/ 读取；"
                                        "默认用 output/obs_deduce_latest.json")
    ap.add_argument("--allow-mismatch", action="store_true",
                    help="允许 L2 情景数据日与观测池不一致（默认报错退出，防用错数据日）")
    ap.add_argument("--dry-run", action="store_true", help="只写片段，不改 analysis.html")
    ap.add_argument("--panel-only", action="store_true",
                    help="只产出 obs_panel.json（V3 配对载荷），不动 analysis.html")
    ap.add_argument("--no-deploy", action="store_true", help="不同步 deploy 副本")
    args = ap.parse_args()

    obs, obs_src = load_obs(args.data_date)
    od = obs.get("date", "")
    print(f"· 观测池：{obs_src.relative_to(BASE)}（数据日 {od} · {len(obs.get('items', []))} 只）")

    scen = None
    if SCEN_JSON.exists():
        scen = json.loads(SCEN_JSON.read_text(encoding="utf-8"))
        sd = scen.get("data_date", "")
        if sd != od and not args.allow_mismatch:
            raise SystemExit(
                f"\n✗ 数据日不一致，已中止（防用错数据日）：\n"
                f"   L2 情景 data_date = {sd}\n"
                f"   观测池      date     = {od}\n"
                f"   → 请把 {SCEN_JSON.name} 的情景与 data_date 一起更新到 {od}；\n"
                f"     或加 --allow-mismatch 显式接受不匹配（不推荐，会导致 L1 与 L2 口径不一致）。")
        print(f"✓ L2 情景已加载：{len(scen.get('picks', []))} 只（数据日 {sd}）")
    else:
        print(f"· 未找到 {SCEN_JSON.name}（只生成 L1）")

    frag = build_section(obs, scen)
    FRAG_OUT.write_text(frag, encoding="utf-8")

    # ---- 自检 ----
    items = obs.get("items", [])
    codes = {x["code"] for x in items}
    picks = (scen or {}).get("picks", [])
    n_l2 = len([p for p in picks if p["code"] in codes])
    missing = [p["code"] for p in picks if p["code"] not in codes]
    n_cards = frag.count("<details")
    ok = (n_cards == len(items) + n_l2)
    print(f"✓ 片段已生成：{len(frag)} 字符 → {FRAG_OUT.relative_to(BASE)}")
    print(f"· 自检：L1 全池 {len(items)} 只 + L2 重点 {n_l2} 只 = 折叠卡 {n_cards} 个 {'✓' if ok else '✗ 数量不匹配'}")
    if missing:
        print(f"⚠ L2 code 不在观测池中（已跳过，请核对）：{missing}")
    bad = [x["name"] for x in items if x.get("ma5") is None or x.get("low10") is None]
    if bad:
        print(f"⚠ 以下标的缺 ma5/low10，关键位将显示 —：{bad}")

    # ---- 配对载荷（V3 第 6 段用）----
    if not args.dry_run:
        panel = build_panel(obs, scen, od, obs_src)
        p_root, p_dep = write_panel(panel, no_deploy=args.no_deploy)
        where = p_root.relative_to(BASE)
        if p_dep:
            where = f"{where} + {p_dep.relative_to(BASE)}"
        print(f"✓ 配对载荷已写出：{where}（{p_root.stat().st_size} B）")
        _sd = panel["scen_data_date"]
        _paired = (not _sd) or (_sd == panel["data_date"])
        print(f"· 载荷自检：items {panel['count']} 只 / picks {panel['picks_count']} 只 ｜ "
              f"数据日 {panel['data_date']}"
              + (f"（L2 情景日 {_sd} {'✓ 一致' if _paired else '⚠️ 不一致，V3 会显式告警'}）" if _sd else "（无 L2）"))
        if panel["picks_count"] != n_l2:
            print(f"✗ 载荷 picks 数（{panel['picks_count']}）与片段 L2 数（{n_l2}）不一致")
        if panel["dropped_picks"]:
            print(f"⚠ 载荷已剔除 code 不在观测池的 picks：{panel['dropped_picks']}")

    if args.dry_run:
        print("· --dry-run：未改动 analysis.html、未写 obs_panel.json")
        return
    if args.panel_only:
        print("· --panel-only：未改动 analysis.html")
        return

    html = ROOT_HTML.read_text(encoding="utf-8")
    old_len = len(html)
    html, css_state = ensure_css(html)
    html = replace_section(html, frag)
    ROOT_HTML.write_text(html, encoding="utf-8")
    print(f"✓ 7.2 段已替换（root）：{old_len} → {len(html)} 字符（CSS {css_state}）")

    if not args.no_deploy:
        if DEPLOY_HTML.exists():
            shutil.copy2(ROOT_HTML, DEPLOY_HTML)
            print("✓ deploy 副本已同步")
        else:
            print(f"⚠ 未找到 deploy 副本：{DEPLOY_HTML}")


if __name__ == "__main__":
    main()
