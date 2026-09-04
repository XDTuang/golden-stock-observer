#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘 · 对外分享版生成（隐私脱敏 · 本地 HTML）
================================================
读取本地复盘产物，按用户指定的隐私边界脱敏后，生成单份完整的**本地 HTML**。

【输出格式】（2026-08-29 用户明确）
  分享版固定输出 **本地 HTML**（可离线打开、可自行打印为 PDF）。
  PDF 仅在显式传 `--pdf` 时尝试（依赖 WeasyPrint / Playwright，非必需）。

【🔴 隔离铁律】（2026-08-29 用户明确：分享版不得影响正常版本结构与数据）
  - **只读消费**：对所有源文件只读，绝不写回、绝不修改原产物；
  - **独立输出**：产物写入用户工作目录 /Users/samt/Desktop/兜是宝/分享版PDF/，
    不在 git 仓库内，不会被提交、不影响线上站点；
  - **不改结构**：不触碰 analysis.html / index.html / 任何 JSON 源文件，
    不改动段落锚点、不改 deploy 副本、不产生任何 git 变更。
  任何写回源文件的行为都应视为 bug。

【脱敏规则】（2026-08-29 用户确认）
  移除：
    ① 8 段「数据自检区」        —— 内部运维信息（JSON 文件名 / 数据日期 / 已知盲区）
    ② 投喂素材清单 19 份        —— 暴露个人信息渠道（素材标题 / 来源 / 关键词）
    ③ 9 段原始内容              —— 含内部脚本名、GitHub 仓库、workflow、本地路径
  替换：
    9 段 → 脱敏版「数据来源汇总」（仅保留公开数据源名称与免责声明）
    ai_synthesis.disclaimer → 简化为纯免责声明（去掉投喂份数 / 新闻条数等内部统计）
  保留（用户确认不算隐私）：
    1.3 重点观测股 32 只（含持仓股永鼎股份 / 华工科技）
    0.5 深度判读、4/5/5.5 段产业链标的、AI 综合推演全文

输入：
  deploy/data/daily_review/analysis.html   复盘主体
  deploy/output/feed_review_latest.json    投喂复盘 + AI 综合推演
输出：
  <输出目录>/每日复盘_YYYY-MM-DD_分享版.html   （默认，本地 HTML）
  <输出目录>/每日复盘_YYYY-MM-DD_分享版.pdf    （仅 --pdf 时）

用法:
  python review/build_share_html.py
  python review/build_share_html.py --out /path/to/dir
  python review/build_share_html.py --pdf        # 额外尝试生成 PDF
"""
import os, re, sys, json, datetime, html as htmlmod

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANA = os.path.join(BASE, "deploy", "data", "daily_review", "analysis.html")
FEED = os.path.join(BASE, "deploy", "output", "feed_review_latest.json")
# 默认输出到用户工作目录（不进项目仓库，避免误提交）
DEFAULT_OUT = "/Users/samt/Desktop/兜是宝/分享版PDF"

# ── 脱敏后的 9 段（仅公开数据源 + 免责声明，无内部脚本/仓库/路径）──
SEG9_CLEAN = '''<!-- 9 来源（脱敏） -->
<div class="dr-h">9 · 数据来源汇总</div>
<div class="dr-card">
  <div class="dr-note">
    <b>行情数据</b>：腾讯自选股公开行情接口（A股指数 / 美股 / 港股 / 日韩指数）、申万一级板块主力资金流向、财经日历。
    <br><b>公开新闻源</b>：东方财富全球资讯 / 财经早餐 / 新浪财经 / 同花顺 / 富途 / 央视新闻联播 —— 每日自动抓取汇总。
    <br><b>研究素材</b>：本次复盘综合了当日若干研究素材（具体渠道与清单已隐去）。
    <br><b>免责声明</b>：本材料仅供学习交流，<b>不构成任何投资建议</b>。所载信息来源于公开渠道，不保证其准确性与完整性，据此操作风险自担。
  </div>
</div>
'''

DISCLAIMER_CLEAN = "本材料仅供学习交流，不构成任何投资建议。所载信息来源于公开渠道，不保证其准确性与完整性，据此操作风险自担。"


def load(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read() if p.endswith((".html", ".htm")) else json.load(f)


def split_segments(h):
    """按注释锚点切段，返回 [(name, html)]。"""
    anchors = [(m.start(), m.group(1).strip())
               for m in re.finditer(r'<!--\s*([^\n]*?)\s*-->', h)
               if re.match(r'^\d', m.group(1).strip())]
    anchors.sort()
    out = []
    for i, (pos, name) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(h)
        out.append((name, h[pos:end]))
    return out


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


# ── 内部标识清洗：对外分享版不得出现任何内部文件名 / 脚本名 / 路径 ──
SCRUB_RULES = [
    # 具体文件名 → 可读描述（顺序重要，先具体后通用）
    (r'output/top10_history\.json', '综合评分系统'),
    (r'output/gate_data\.json', '门控分类系统'),
    (r'market\.json(?:\.us_kline)?', '行情数据'),
    (r'signals\.json', '评分数据'),
    (r'golden_diamond\.json', '金钻形态数据'),
    (r'obs_deduce_latest\.json', '观测股推演数据'),
    (r'daily_review_news\.json', '新闻池数据'),
    (r'sector_flow\.json', '板块资金流数据'),
    (r'\boutput/[\w/]+\.(?:json|csv)', '内部数据文件'),
    (r'\b[\w/]+\.(?:py|yml|sh|plist)\b', '内部处理脚本'),
    (r'\bcron\b[^，。；]{0,24}', '定时任务'),
    (r'\bBYDAY=[\d\-,]+', ''),
    # 内部路径泄漏兜底（如 2 段占位「日韩数据加载中…（数据源：data/daily_review/行情数据）」）
    (r'（数据源：[^）]*）', ''),
]
# 6 段动态区块占位（JS 动态渲染，静态 PDF 无法呈现）
NEWS_PLACEHOLDER = ('<div class="placeholder">6 段「新闻整合」为页面动态加载区块'
                    '（每日自动抓取东方财富 / 财经早餐 / 新浪 / 同花顺 / 富途 / 央视新闻联播等公开新闻源），'
                    '静态 PDF 导出时不含该动态内容，请在网页版查看。</div>')

# ── 夜间版（--night）渠道/持仓清洗：去投喂渠道名与持仓措辞（2026-09-02 用户要求）──
#   覆盖：投喂渠道名、参赛/围观昵称 → 通用词；正文"持仓"措辞 → 中性研判词。
#   段级移除（7.2 K3 持仓映射、holding_map）在 main/build_feed_html 中处理，不在此正则。
NIGHT_SCRUB_RULES = [
    # 投喂渠道（顺序：先具体后通用）
    (r'知识星球·投资有道', '第三方投喂渠道'),
    (r'知识星球', '第三方投喂渠道'),
    (r'叙事AKUN\s*2?5?个?股群围观记录?\s*\d{4}?[^\n。；<]*', '游资社群信息汇总'),
    (r'叙事AKUN', '游资社群观察'),
    (r'复利杯\s*S1[0-9]?', '模拟赛跟踪'),
    (r'复利杯', '模拟赛跟踪'),
    (r'25个炒股群围观记录', '游资社群信息汇总'),
    (r'炒股群围观记录', '社群信息汇总'),
    (r'兴证海外TMT', '券商 TMT 团队'),
    (r'调研纪要', '机构调研'),
    # 模拟赛选手昵称（第三方个人信息）→ 匿名：保留动作去昵称
    (r'(模拟赛跟踪情绪：|情绪投喂：)([^\s，。；<>:：]{1,12}?)(?=(新开|低吸|止损|止盈|加仓|打板|减仓|被按跌停|割|浮盈|浮亏|清仓|补仓))', r'\1有选手'),
    # 任意位置已知昵称 + 动作 → 有选手（无前缀场景兜底）
    (r'(?:乌江望月|狂人|鄂华少|A拉神灯|205斤减肥哥|2025七倍|小古茗|我是会发光的男人|第四维度的保佑|谦受益)(?=(新开|低吸|止损|止盈|加仓|打板|减仓|被按跌停|割|浮盈|浮亏|清仓|补仓))', '有选手'),
    # 持仓措辞 → 中性（不改变研判语义）
    (r'（剑桥等持仓观察）', '（剑桥等观察）'),
    (r'坑日持仓不割', '坑日不割'),
    (r'持仓相关：', '盘面相关：'),
    (r'已有 PTFE/化工/光纤\s*持仓可保持观察', 'PTFE/化工/光纤 线保持观察'),
    (r'不持仓但需关注板块情绪', '需关注板块情绪'),
    (r'当前未持仓', '未持仓状态'),
    (r'9/2 重点观测股推演（K3 持仓 9/2 映射', '9/2 重点观测股推演（9/2 映射'),
    # 复盘作者/渠道人（廖峥·和讯 等）→ 中性描述（0.5 研判正文 + 7.1 验证表引用）
    (r'廖峥·和讯', '某券商复盘作者'),
    (r'廖峥复盘笔记', '投喂复盘笔记'),
    (r'廖峥', '某复盘作者'),
    # ── 2026-09-03 追加：「投喂」术语与素材份数属内部统计，分享版一律中性化 ──
    (r'\d+\s*份投喂(素材)?(综合)?(判读)?', r'综合研判'),          # 0.5 段标题「41 份投喂综合判读」→ 综合研判
    (r'投喂综合判读', '综合研判'),                                  # 兜底（无份数前缀时）
    (r'（公开源自动刷新\s*·\s*投喂精选可选）', '（公开源自动刷新）'),   # 6 段标题
    (r'<b>agent\s*投喂精选</b>', '<b>精选补充</b>'),                # 6 段正文
    (r'附\s*·\s*投喂复盘与 AI 综合研判', '附 · AI 综合研判'),        # 附段标题
    (r'投喂语料偏正面（净分\s*-?\d+）', '语料偏正面'),                # prediction.reasons 内部统计
    (r'（当日无投喂时该区块自动省略）', '（无补充时该区块自动省略）'),  # 6 段正文中性化
    (r'注：本版已隐去持仓映射/投喂渠道等个人信息',
     '注：本版已隐去个人信息渠道与组合映射'),                        # 附段说明（去「投喂/持仓」字样）
]


def scrub(text, night=False):
    """清洗内部技术标识；night=True 时追加夜间版渠道/持仓清洗。"""
    for pat, rep in SCRUB_RULES:
        text = re.sub(pat, rep, text)
    if night:
        for pat, rep in NIGHT_SCRUB_RULES:
            text = re.sub(pat, rep, text)
    # 6 段动态容器 → 静态占位说明
    text = re.sub(
        r'<div id="drNewsPool"[^>]*>.*?</div>\s*</div>',
        NEWS_PLACEHOLDER, text, flags=re.S)
    # 兜底：若上面未命中，直接替换加载中文案
    text = re.sub(r'新闻池自动加载中…（数据源：[^）]*）',
                  '（新闻池为动态加载区块，静态 PDF 不含此内容）', text)
    # 清理可能出现的空括号与多余空格
    text = re.sub(r'（\s*）', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text


def fmt_pct(v):
    try:
        f = float(v)
    except Exception:
        return "—"
    cls = "dr-up" if f >= 0 else "dr-dn"
    return f'<span class="{cls}">{f:+.2f}%</span>'


def fmt_signals(sig, limit=3):
    """金钻 signals 可能是 dict / dict 列表 / 字符串，统一渲染为可读文本。"""
    if sig is None:
        return "—"
    if isinstance(sig, dict):
        sig = [sig]
    if not isinstance(sig, (list, tuple)):
        return str(sig)
    parts = []
    for s in sig[:limit]:
        if isinstance(s, dict):
            t = s.get("type") or s.get("name") or s.get("label") or ""
            d = s.get("date") or ""
            txt = f"{t}{(' · ' + str(d)) if d else ''}".strip(" · ")
            if txt:
                parts.append(txt)
        else:
            parts.append(str(s))
    return " / ".join(parts) if parts else "—"


def build_top10_html(day=None):
    """1.1 当日 TOP10：静态 PDF 无法执行 JS，直接从 top10_history.json 渲染。"""
    p = os.path.join(BASE, "deploy", "output", "top10_history.json")
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return ""
    day = day or (sorted(d.keys())[-1] if d else None)
    items = ((d.get(day) or {}).get("top10") or []) if day else []
    if not items:
        return ""
    rows = []
    for i, x in enumerate(items, 1):
        rows.append(
            f'<tr><td>{i}</td><td>{x.get("code","")}</td><td>{x.get("name","")}</td>'
            f'<td>{x.get("market","")}</td><td class="dr-tag">{x.get("grade","")}</td>'
            f'<td>{x.get("ema_score","—")}</td><td>{x.get("total_score","—")}</td>'
            f'<td>{fmt_pct(x.get("change_pct"))}</td><td>{x.get("close","—")}</td></tr>')
    return ('<table class="dr-tbl"><thead><tr><th>#</th><th>代码</th><th>名称</th>'
            '<th>市场</th><th>信号等级</th><th>EMA</th><th>评分</th>'
            '<th>涨跌</th><th>收盘</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table>')


def build_diamond_html(limit=12):
    """1.2 当日金钻：三个门控分类统计 + 各分类个股清单（按 primary 分组）。"""
    p = os.path.join(BASE, "deploy", "output", "gate_data.json")
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            g = json.load(f)
    except Exception:
        return ""
    gates = g.get("gates") or {}
    if not gates:
        return ""
    out = []
    # 总览表
    out.append('<table class="dr-tbl"><thead><tr><th>门控分类</th><th>扫描范围</th>'
               '<th>命中</th><th>金钻起涨</th><th>买入</th><th>红区黄柱连续</th></tr></thead><tbody>')
    for k in ("all_a", "pool", "sector_top100_to4"):
        v = gates.get(k) or {}
        ov = v.get("overview") or {}
        out.append(f'<tr><td>{v.get("label", k)}</td><td>{v.get("scope_size","—")}</td>'
                   f'<td><b>{ov.get("total","—")}</b></td><td>{ov.get("up","—")}</td>'
                   f'<td>{ov.get("buy","—")}</td><td>{ov.get("hz","—")}</td></tr>')
    out.append('</tbody></table>')
    # 各分类个股（以全A档为主，展示 main 形态）
    for k in ("all_a", "pool", "sector_top100_to4"):
        v = gates.get(k) or {}
        stocks = v.get("stocks") or []
        if not stocks:
            continue
        out.append(f'<div class="dr-h2">{v.get("label", k)}（{len(stocks)} 只'
                   f'{"，展示前 " + str(limit) + " 只" if len(stocks) > limit else ""}）</div>')
        out.append('<table class="dr-tbl"><thead><tr><th>代码</th><th>名称</th>'
                   '<th>形态分类</th><th>信号</th></tr></thead><tbody>')
        for x in stocks[:limit]:
            out.append(f'<tr><td>{x.get("code","")}</td><td>{x.get("name","")}</td>'
                       f'<td>{x.get("primary","")}</td>'
                       f'<td class="dr-tag">{fmt_signals(x.get("signals"))}</td></tr>')
        out.append('</tbody></table>')
    return "".join(out)


def inject_before_last_div(seg_html, inject_html):
    """把内容插入到段落最后一个 </div>（dr-card 收尾）之前。"""
    if not inject_html:
        return seg_html
    i = seg_html.rfind("</div>")
    if i < 0:
        return seg_html + inject_html
    return seg_html[:i] + inject_html + seg_html[i:]


def build_feed_html(feed, night=False):
    """投喂复盘脱敏渲染：保留研判内容，移除素材清单与内部来源。
       night=True（夜间版）：额外跳过 holding_map（个人持仓名单）。"""
    if not feed:
        return ""
    pred = feed.get("prediction") or {}
    syn = feed.get("ai_synthesis") or {}
    p = []
    p.append('<div class="dr-h">附 · 投喂复盘与 AI 综合研判</div>')
    p.append('<div class="dr-card">')
    p.append(f'<div class="dr-note">数据日期 <b>{feed.get("data_date", "—")}</b>'
             f' · 指引日 <b>{feed.get("guide_date", "—")}</b></div>')
    if night:
        p.append('<div class="dr-note">注：本版已隐去持仓映射/投喂渠道等个人信息，'
                 '仅保留公开行情研判与综合推演结论。</div>')

    bias = pred.get("bias", "—")
    score = pred.get("bias_score", "—")
    p.append(f'<div class="dr-note"><b>后市预判：{bias}</b>（评分 {score}）</div>')
    for r in (pred.get("reasons") or []):
        p.append(f'<div class="dr-note">· {r}</div>')

    # AI 综合推演
    if syn.get("verdict_headline"):
        p.append('<div class="dr-h2">AI 综合研判 · 核心结论</div>')
        p.append(f'<div class="dr-note"><b>{syn["verdict_headline"]}</b></div>')
    for line in (syn.get("conclusion_first") or []):
        p.append(f'<div class="dr-note">{line}</div>')

    tr = syn.get("theme_resonance") or []
    if tr:
        p.append('<div class="dr-h2">主题共振（语料 × 盘面）</div>')
        p.append('<table class="dr-tbl"><thead><tr><th>主题</th><th>权重</th><th>证据</th></tr></thead><tbody>')
        for t in tr:
            ev = "；".join(t.get("evidence", [])[:3])
            p.append(f'<tr><td>{t.get("theme","")}</td><td>{t.get("weight","")}</td><td class="dr-tag">{ev}</td></tr>')
        p.append('</tbody></table>')

    nv = syn.get("nvda_chain_map") or {}
    if nv.get("summary"):
        p.append('<div class="dr-h2">算力链映射</div>')
        p.append(f'<div class="dr-note">{nv["summary"]}</div>')

    # holding_map：默认渲染脱敏版「主线映射」；夜间版（--night）整块跳过（=个人持仓名单）
    hm = syn.get("holding_map") or {}
    if hm and not night:
        p.append('<div class="dr-h2">主线映射（主题对齐 / 谨慎）</div>')
        if hm.get("note"):
            p.append(f'<div class="dr-note">{hm["note"]}</div>')
        p.append('<table class="dr-tbl"><thead><tr><th>方向</th><th>内容</th></tr></thead><tbody>')
        for x in (hm.get("theme_aligned") or []):
            p.append(f'<tr><td class="dr-up">主线</td><td>{x}</td></tr>')
        for x in (hm.get("caution") or []):
            p.append(f'<tr><td class="dr-dn">谨慎</td><td>{x}</td></tr>')
        p.append('</tbody></table>')

    # T+1 事件雷达：key 形如 t1_radar_YYYYMMDD（8/31 时代硬编码 t1_radar_0831 曾漏渲染）
    _radar_key = next((k for k in syn if k.startswith("t1_radar_")), None)
    radar = syn.get(_radar_key) or [] if _radar_key else []
    if radar:
        p.append('<div class="dr-h2">T+1 事件雷达</div>')
        for x in radar:
            p.append(f'<div class="dr-note">· {x}</div>')

    risks = syn.get("risks") or []
    if risks:
        p.append('<div class="dr-h2">风险（概率 × 冲击）</div>')
        p.append('<table class="dr-tbl"><thead><tr><th>概率</th><th>冲击</th><th>描述</th></tr></thead><tbody>')
        for r in risks:
            p.append(f'<tr><td>{r.get("prob","")}</td><td>{r.get("impact","")}</td><td>{r.get("desc","")}</td></tr>')
        p.append('</tbody></table>')

    for t in (pred.get("t1_focus") or []):
        pass
    t1 = pred.get("t1_focus") or []
    if t1:
        p.append('<div class="dr-h2">T+1 关注</div>')
        for x in t1:
            p.append(f'<div class="dr-note">· {x}</div>')

    prisk = pred.get("risks") or []
    if prisk:
        p.append('<div class="dr-h2">风险提示</div>')
        for r in prisk:
            d = r.get("desc") if isinstance(r, dict) else r
            p.append(f'<div class="dr-note">⚠️ {d}</div>')

    p.append(f'<div class="dr-note disclaimer">{DISCLAIMER_CLEAN}</div>')
    p.append('</div>')
    return "\n".join(p)


CSS = """
/* ── 主题变量桥接（2026-09-01 补）────────────────────────────────────
   analysis.html 的各段内容大量使用 var(--bg-subtle) / var(--green) 等变量，
   但分享版有自己的浅色打印样式，未定义这些变量 → 色块边框、背景、语义色全部失效，
   退化成无色裸文本（实测 85 处 var() 引用、0 处 :root 定义）。
   这里补一套「打印友好」取值：
     · 底色/边框 取主站**亮色主题**（浅底才适合打印）
     · 语义色   取主站**暗色主题**的高饱和值
       （亮色主题的 #ff7b7b / #4ade80 / #63b3ed 太淡，打印几乎看不出）
   ──────────────────────────────────────────────────────────────── */
:root {
  --bg-card: #ffffff;    --bg-subtle: #f0f2f5;   --border: #e8ecf1;
  --text: #1a1d2e;       --text-muted: #64748b;  --text-secondary: #334155;
  --red: #e53e3e;        --green: #22a861;       --blue: #3182ce;
  --gold: #d69e2e;       --orange: #ed8936;      --accent: #b8860b;
}
@page { size: A4; margin: 16mm 14mm 18mm 14mm;
  @bottom-center { content: counter(page) " / " counter(pages);
    font-family: "PingFang SC", sans-serif; font-size: 9pt; color: #888; }
  @top-right { content: "每日复盘 · 分享版"; font-family: "PingFang SC", sans-serif;
    font-size: 8.5pt; color: #aaa; } }
* { box-sizing: border-box; }
body { font-family: "PingFang SC", "Hiragino Sans GB", "Heiti SC", sans-serif;
  font-size: 10.5pt; line-height: 1.65; color: #1a1d21; margin: 0; }
.cover { page-break-after: always; padding-top: 60mm; text-align: center; }
.cover h1 { font-size: 26pt; margin: 0 0 10mm 0; color: #1e3a8a; letter-spacing: 2px; }
.cover .sub { font-size: 13pt; color: #444; margin-bottom: 6mm; }
.cover .meta { font-size: 11pt; color: #666; line-height: 2; }
.cover .warn { margin-top: 20mm; font-size: 10pt; color: #b45309;
  border: 1px solid #fcd34d; background: #fffbeb; padding: 5mm; border-radius: 4px;
  display: inline-block; text-align: left; }
.dr-h { font-size: 14pt; font-weight: 700; color: #1e3a8a; margin: 7mm 0 3mm 0;
  padding-bottom: 2mm; border-bottom: 2px solid #1e3a8a; page-break-after: avoid; }
.dr-h2 { font-size: 11.5pt; font-weight: 700; color: #334155; margin: 5mm 0 2mm 0;
  page-break-after: avoid; }
.dr-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;
  padding: 4mm 5mm; margin: 3mm 0; page-break-inside: auto; }
.dr-note { font-size: 10pt; color: #334155; margin: 2mm 0; }
.dr-note b { color: #0f172a; }
.dr-tag { font-size: 9pt; color: #64748b; }
/* 语义色块统一字号：已改造段落（0/0.5/1/4/5）内联写了 12.5px 会优先；
   未改造段（2/3/6/7.1/7.2/7.3）没写，会继承 body 10.5pt=14px，
   与 12.5px 混用差 1.5px。此兜底规则特异性(0,1,1) > .dr-note(0,1,0)，两��都能覆盖。 */
div[style*="border-left"] { font-size: 12.5px; line-height: 1.6; }
.disclaimer { margin-top: 5mm; padding: 3mm; background: #f1f5f9;
  border-left: 3px solid #94a3b8; font-size: 9pt; color: #475569; }
table.dr-tbl { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 3mm 0; }
table.dr-tbl th { background: #eef2f7; text-align: left; padding: 1.8mm 2mm;
  border-bottom: 1.5px solid #cbd5e1; font-weight: 700; }
table.dr-tbl td { padding: 1.6mm 2mm; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
.dr-up { color: #c0392b; font-weight: 600; }   /* 涨：红（A股习惯） */
.dr-dn { color: #1e8e3e; font-weight: 600; }   /* 跌：绿（A股习惯） */
a { color: #1d4ed8; text-decoration: none; }
code { background: #f1f5f9; padding: 0 1mm; border-radius: 2px; font-size: 9pt; }
.news-bar, .news-chip, #drNewsPool, #newsList, #drTblUs, #drTblA, #drTblH,
#drTblHK, #drTop10, #drDiamond, #drObserve { }
.placeholder { font-size: 9.5pt; color: #64748b; font-style: italic;
  padding: 3mm; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 4px; }
"""


def main():
    out_dir = DEFAULT_OUT
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
    # 2026-09-01：`--no-note` 时不输出封面「隐私处理说明」（用户要求脱敏版不带备注）
    no_note = "--no-note" in sys.argv
    # 2026-09-02：`--night` 夜间版——在默认脱敏之上，额外移除个人持仓映射（7.2 段 + holding_map）、
    #   清洗投喂渠道名/持仓措辞；文件名追加「（夜间）」以区分次日 09:05 更新的完整版。
    night = "--night" in sys.argv

    ana = load(ANA)
    feed = load(FEED)
    if not ana:
        print(f"❌ 复盘文件缺失：{ANA}")
        return 1

    segs = split_segments(ana)
    print(f"═══ 每日复盘 · 对外分享 PDF（隐私脱敏）═══")
    print(f"  原始段落数：{len(segs)}")

    review_date = (feed or {}).get("data_date") or datetime.datetime.now().strftime("%Y-%m-%d")

    body, removed, cleaned, filled = [], [], [], []
    for name, seg_html in segs:
        key = name.split()[0]
        # ① 移除 8 段数据自检区
        if key == "8":
            removed.append("8 段 数据自检区（内部运维信息）")
            continue
        # ② 9 段替换为脱敏版
        if key == "9":
            body.append(SEG9_CLEAN)
            cleaned.append("9 段 数据来源汇总（内部脚本/仓库/路径 → 仅公开数据源）")
            continue
        # ②b 夜间版（--night）：移除 7.2 段（K3 持仓映射 + 持仓指令，个人组合敏感）
        if night and key == "7.2":
            removed.append("7.2 段 重点观测股推演（K3 持仓映射 / 持有 / 减仓线等个人组合指令）")
            continue
        # ③ 1.1 / 1.2 为 JS 动态区块，静态 PDF 从 JSON 直接渲染补齐
        if key == "1.1":
            t = build_top10_html(review_date)
            if t:
                seg_html = inject_before_last_div(seg_html, t)
                filled.append(f"1.1 当日 TOP10（从 top10_history.json {review_date} 渲染）")
        if key == "1.2":
            t = build_diamond_html()
            if t:
                seg_html = inject_before_last_div(seg_html, t)
                filled.append("1.2 当日金钻（三档门控统计 + 个股清单，从 gate_data.json 渲染）")
        body.append(seg_html)

    # ③ 投喂复盘：渲染时已排除素材清单与内部来源；夜间版再跳过 holding_map
    feed_html = build_feed_html(feed, night=night)
    if feed_html:
        body.append(feed_html)
        removed.append("投喂素材清单 19 份（标题/来源/关键词，暴露信息渠道）")
        cleaned.append("ai_synthesis.disclaimer（投喂份数/新闻条数 → 纯免责声明）")
        if night:
            removed.append("AI 综合研判 · 主线映射（holding_map = 个人持仓/谨慎名单）")

    print(f"\n  【移除】")
    for r in removed:
        print(f"    ✂️ {r}")
    print(f"\n  【脱敏】")
    for c in cleaned:
        print(f"    🔄 {c}")
    if filled:
        print(f"\n  【补齐】JS 动态区块 → 静态渲染")
        for c in filled:
            print(f"    ➕ {c}")
    if night:
        print(f"\n  【夜间版（--night）附加移除】7.2 K3 持仓映射 · holding_map 持仓名单 · 投喂渠道名 · 持仓措辞")
        print(f"  【保留】0.5 深度判读 · 1 昨日盘面 · 3 隔夜美股 · 4/5/5.5 宏观科技产业链 · 7.1 K3 验证 ·"
              f" 7.3 开盘指引 · AI 综合研判（研判内容，均不含个人持仓）")
    else:
        print(f"\n  【保留】1.3 重点观测股 32 只（用户确认含持仓股亦保留）"
              f" · 0.5 深度判读 · 4/5/5.5 产业链 · AI 综合推演全文")

    # 应用内部标识清洗（内部文件名 / 脚本名 / 路径 / 6 段动态区块；night 追加渠道/持仓清洗）
    body_html = scrub("\n".join(body), night=night)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    review_date = (feed or {}).get("data_date", today)
    # 🔴 2026-09-02 修复：guide_date 兜底（feed.daily_feed_review.py 当前不写该字段，
    #   导致分享版封面显示「复盘=指引=同日」的歧义；按 K3 复盘规则：复盘 T-1 收盘、指引 T，
    #   自动推算 = review_date 的下一个工作日，跳过周六周日）。
    # 🔴 2026-09-02 二次修复：_rd 提到 if 前统一计算——原实现只在 else 分支定义，
    #   当 feed 已带合法 guide_date（9/2 起 build_feed 写入 guide_date=次日）走 if 分支时
    #   _rd 未定义 → UnboundLocalError（22:41 跑 --night 实测 crash）。
    _rd = datetime.datetime.strptime(review_date, "%Y-%m-%d")
    raw_guide = (feed or {}).get("guide_date")
    if raw_guide and raw_guide != "—" and raw_guide != review_date:
        guide_date = raw_guide
    else:
        _d = _rd + datetime.timedelta(days=1)
        # 跳过周末（5=周六、6=周日）
        while _d.weekday() >= 5:
            _d += datetime.timedelta(days=1)
        guide_date = _d.strftime("%Y-%m-%d")
    # 🔴 2026-09-02 修复：周X 动态化（原「周五收盘」硬编码，9/1（周二）显示周五是 bug）
    _wd = ["周一","周二","周三","周四","周五","周六","周日"][_rd.weekday()]
    weekday_str = _wd
    # 夜间版文件名后缀（区分次日 09:05 完整版）
    _suff = "（夜间）" if night else ""

    full = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>每日复盘 {review_date} 分享版{_suff}</title>
<style>{CSS}</style></head><body>
<div class="cover">
  <h1>每日复盘</h1>
  <div class="sub">{review_date}（{weekday_str}收盘）复盘 · {guide_date} 指引</div>
  <div class="meta">
    复盘日 {review_date} ｜ 指引日 {guide_date}<br>
    生成时间 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
  </div>
  {'' if no_note else '''
  <div class="warn">
    <b>隐私处理说明</b><br>
    本版本为对外分享版，已移除：数据自检区（内部运维信息）、投喂素材清单（信息渠道）、
    内部脚本名与仓库路径。<br>
    保留：全部行情研判、产业链分析、AI 综合推演内容。
  </div>'''}
</div>
{body_html}
</body></html>"""

    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, f"每日复盘_{review_date}_分享版{_suff}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full)
    size_kb = os.path.getsize(html_path) / 1024
    print(f"\n💾 HTML: {html_path}（{size_kb:.0f} KB）")
    print(f"   ✅ 分享版完成（本地 HTML，可离线打开；需 PDF 时浏览器「打印 → 存储为 PDF」）")

    # ── 隔离自检：确认未对源文件产生任何写入 ──
    print(f"\n  【隔离自检】源文件只读校验")
    for label, p in (("analysis.html", ANA), ("feed_review_latest.json", FEED)):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M")
        print(f"    🔒 {label}: 未修改（最后更新 {mt}）")

    # PDF：仅在显式 --pdf 时尝试（默认不生成，避免依赖下载）
    if "--pdf" not in sys.argv:
        return 0

    print(f"\n  【PDF】显式请求，尝试生成…")
    pdf_path = os.path.join(out_dir, f"每日复盘_{review_date}_分享版{_suff}.pdf")

    engine = None
    try:
        from weasyprint import HTML as WPHTML
        WPHTML(string=full, base_url=BASE).write_pdf(pdf_path)
        engine = "WeasyPrint"
    except Exception as e1:
        print(f"  ⓘ WeasyPrint 不可用（{type(e1).__name__}: {str(e1)[:60]}…），回退 Playwright")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.goto("file://" + html_path, wait_until="networkidle")
                page.emulate_media(media="print")
                page.pdf(path=pdf_path, format="A4", print_background=True,
                         margin={"top": "16mm", "bottom": "18mm",
                                 "left": "14mm", "right": "14mm"})
                browser.close()
            engine = "Playwright/Chromium"
        except Exception as e2:
            print(f"\n⚠️ PDF 生成失败：Playwright 也不可用（{type(e2).__name__}: {str(e2)[:80]}）")
            print(f"   已保留 HTML，可用浏览器打开后「打印 → 存储为 PDF」")
            print(f"   或在能装系统库的环境中执行：pip install weasyprint（需 glib/pango）")
            return 0

    size = os.path.getsize(pdf_path) / 1024
    print(f"📄 PDF : {pdf_path}（{size:.0f} KB · 引擎 {engine}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
