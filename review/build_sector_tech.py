#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块技术分析（共振置信度分级 + 三维技术面）

背景（2026-09-17 用户指令）：
  原「共振」判定 = 新闻日均热度 × 主力净流入 的**布尔四象限**，三个硬伤：
    ① 无强度分级（9/16「共振」7 个板块：电子 +227.03 亿 ↔ 医药生物 +0.45 亿，同标签不同量级）
    ② 零技术面（不看板块自身走势：突破 or 滞涨？压力？支撑？量能配合？）
    ③ 单日截面（sector_flow 已有 20 天历史，可判连续性，原未用）
  本脚本补齐这三项。

输入:
  output/cross_analysis.json   四象限判定（板块 / 新闻热度 / 资金 / verdict）
  output/sector_flow.json      20 天历史资金流（→ 连续性 streak）

输出:
  output/sector_tech.json      （双写 deploy/output/）
    {data_date, generated_at, thresholds, summary{L4..L1}, items[], missing[]}

数据源（本脚本唯一新增依赖 = akshare，项目已在用）:
  ak.index_hist_sw(symbol=<申万一级代码>, period="day")  → 申万一级指数日 K
  ✅ 实测 31/31 全部可用、末条 = 最新已收盘交易日；分类体系与 cross_analysis 完全同源
  （对比：东财 push2his 板块 K 线在部分网络环境被拦；腾讯 pt 码只给当日 1 条 → 均不采用）

分级（**本脚本是档位的唯一权威**，前端不得另起一套字面值）:
  L4 核心共振 = 资金分位>=80 且 连续>=2 日净流入 且 热度达标 且 技术面不破位
  L3 强共振   = (资金分位>=60 且 热度达标) 或 (资金分位>=80 且 连续>=2) ，且 技术面不破位
  L2 弱共振   = verdict ∈ {共振, 暗线} 但未达 L4/L3，或技术面破位降档
  L1 观察     = verdict ∈ {背离, 双冷}，或资金净流出
  技术面不破位 = 收盘 > EMA20 且 EMA 7/7 评分 >= 5（破位→降档，技术面为**否决项**）

用法:
  python review/build_sector_tech.py                 # 全量（拉 31 板块 K 线，约 40s）
  python review/build_sector_tech.py --no-fetch      # 只用已有缓存（离线自检）
  python review/build_sector_tech.py --sectors 电子,通信   # 指定板块（调试）
"""
import argparse
import datetime as _dt
import json
import os
import socket
import sys
import time

socket.setdefaulttimeout(25)  # akshare 底层 urllib3 无默认超时（2026-09-15 教训）

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "output")
DEPLOY_DIR = os.path.join(BASE, "deploy", "output")

CROSS = os.path.join(OUT_DIR, "cross_analysis.json")
FLOW = os.path.join(OUT_DIR, "sector_flow.json")
CACHE = os.path.join(OUT_DIR, "sector_kline_cache.json")
OUT_PATH = os.path.join(OUT_DIR, "sector_tech.json")

# ── 申万一级行业：名称 → 指数代码（31 个，与 sector_flow.SW1_SECTORS / cross_analysis 同源）──
SW1 = {
    "农林牧渔": "801010", "基础化工": "801030", "钢铁": "801040", "有色金属": "801050",
    "电子": "801080", "家用电器": "801110", "食品饮料": "801120", "纺织服饰": "801130",
    "轻工制造": "801140", "医药生物": "801150", "公用事业": "801160", "交通运输": "801170",
    "房地产": "801180", "商贸零售": "801200", "社会服务": "801210", "综合": "801230",
    "建筑材料": "801710", "建筑装饰": "801720", "电力设备": "801730", "国防军工": "801740",
    "计算机": "801750", "传媒": "801760", "通信": "801770", "银行": "801780",
    "非银金融": "801790", "汽车": "801880", "机械设备": "801890", "煤炭": "801950",
    "石油石化": "801960", "环保": "801970", "美容护理": "801980",
}

# ── 阈值（唯一权威；与 build_cross_analysis.HOT_PER_DAY 同源口径）──
PCT_L4 = 80        # 资金分位线：L4
PCT_L3 = 60        # 资金分位线：L3
PCT_REVERSAL = 95  # 「反转首日」判据：连续流入中断后首日回归，但资金分位须极高
STREAK_MIN = 2     # 连续净流入天数门槛
HOT_PER_DAY = 8    # 与 build_cross_analysis.HOT_PER_DAY 同源（日均口径）
EMA20_LINE = 20     # 技术面否决线：**收盘 < EMA20 才算破位**（见下）
KLINE_KEEP = 300   # K 线保留根数（覆盖 EMA 200 + 缓冲）

# 🔴 2026-09-17 实跑校准（首版判据过严，会把框架打成哑火）：
#   ① 技术面否决线只用 EMA20（短期结构），**不叠加 ema_score>=5** ——
#      实测电子 EMA 仅 2/7，因其仍处中期下跌趋势中的反弹（现价距 60 日高 -28%）；
#      若以 ema_score 作否决项，全市场几乎所有板块都会被降为 L2 → 框架失效。
#      → 改为**区分趋势类型**（uptrend / rebound / broken）并在输出中显式标注，
#        把「反弹」与「趋势突破」分开呈现，而不是一刀切否决。
#   ② 连续性加「反转首日」通道 —— 资金刚反转的日子（如 9/15 全面流出 → 9/16 全面流入）
#      streak 必然 = 1，若只认 streak>=2 则该类日子 L4 恒为空 → 加「streak==1 且分位>=95」。

QUADRANTS = ("共振", "背离", "暗线", "双冷")  # 与 build_cross_analysis.QUADRANTS 同源
LEVELS = ("L4", "L3", "L2", "L1")           # 档位字面值唯一权威

# 趋势类型字面值唯一权威（四态 · 2026-09-17 实跑第 3 轮定案）
TREND_TYPES = ("uptrend", "uptrend_pullback", "downtrend_rebound", "downtrend", "unknown")
TREND_LABELS = {
    "uptrend": "趋势向上",
    "uptrend_pullback": "上升回踩",
    "downtrend_rebound": "下跌反弹",
    "downtrend": "下跌破位",
    "unknown": "无数据",
}

# EMA 7/7 体系（对齐 references/ema-trend-system.md，**禁放宽**）
EMA_GROUPS = [(3, 6, 12), (6, 12, 24), (12, 26, 50), (20, 50, 100),
              (34, 68, 136), (50, 100, 150), (72, 144, 200)]


# ══════════════════════ 工具 ══════════════════════
def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_both(name, obj):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    for d in (OUT_DIR, DEPLOY_DIR):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(txt)


def ema(vals, n):
    """指数移动平均（首值用首个样本初始化，与通达信 EMA 语义一致：EMA_t = 2/(n+1)*x + (n-1)/(n+1)*EMA_{t-1}）"""
    if not vals:
        return []
    k = 2.0 / (n + 1)
    out = [vals[0]]
    for x in vals[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def pct_rank(values, v):
    """v 在 values 中的百分位（0-100）；并列取中位秩"""
    if not values:
        return 50.0
    n = len(values)
    if n == 1:
        return 100.0
    below = sum(1 for x in values if x < v)
    equal = sum(1 for x in values if x == v)
    return round((below + (equal - 1) / 2.0) / (n - 1) * 100.0, 1)


def fmt_price(x):
    return round(float(x), 2)


# ══════════════════════ 1. 拉取申万指数 K 线 ══════════════════════
def fetch_klines(names, no_fetch=False):
    """返回 {板块名: [{date, open, close, high, low, volume, amount}, ...]}；失败项进 missing"""
    cache = load(CACHE, {}) or {}
    missing = []
    need = [n for n in names if n not in cache or not cache.get(n)]
    if no_fetch or not need:
        if need:
            for n in need:
                missing.append(f"{n}：无本地缓存（--no-fetch 模式）")
        return {n: cache.get(n) for n in names if cache.get(n)}, missing

    try:
        import akshare as ak
    except ImportError:
        return {n: cache.get(n) for n in names if cache.get(n)}, ["akshare 未安装 → 全部走缓存"] + \
               [f"{n}：无缓存" for n in need if not cache.get(n)]

    import warnings
    warnings.filterwarnings("ignore")

    for i, name in enumerate(need, 1):
        code = SW1.get(name)
        if not code:
            missing.append(f"{name}：无申万代码映射")
            continue
        bars = None
        for att in range(2):
            try:
                df = ak.index_hist_sw(symbol=code, period="day")
                if df is None or df.empty:
                    raise ValueError("empty")
                bars = []
                for _, r in df.tail(KLINE_KEEP).iterrows():
                    bars.append({
                        "date": str(r["日期"])[:10],
                        "open": fmt_price(r["开盘"]), "close": fmt_price(r["收盘"]),
                        "high": fmt_price(r["最高"]), "low": fmt_price(r["最低"]),
                        "volume": float(r["成交量"]), "amount": float(r["成交额"]),
                    })
                break
            except Exception as e:
                if att == 1:
                    missing.append(f"{name}（{code}）K 线获取失败：{type(e).__name__}")
                else:
                    time.sleep(1.0)
        if bars:
            cache[name] = bars
            print(f"  [{i}/{len(need)}] {name:<6} {code}  {len(bars)} 根  末条 {bars[-1]['date']}")
        time.sleep(0.35)

    save_both("sector_kline_cache.json", cache)
    return {n: cache.get(n) for n in names if cache.get(n)}, missing


# ══════════════════════ 2. 技术面三维计算 ══════════════════════
def tech_analysis(bars, flow_yi, upto):
    """bars = 升序 K 线；flow_yi = 当日主力净流入(亿)；upto = 数据日（只用到该日）"""
    rows = [b for b in bars if b["date"] <= upto]
    if len(rows) < 60:
        return None, f"K 线不足 60 根（实际 {len(rows)}）"

    close = [r["close"] for r in rows]
    high = [r["high"] for r in rows]
    low = [r["low"] for r in rows]
    vol = [r["volume"] for r in rows]
    last = rows[-1]
    c = close[-1]
    n = len(rows)

    out = {"as_of": last["date"], "close": fmt_price(c)}

    # ── 维度 0 · 趋势定级（EMA 7/7 + 均线排列 + 区间分位）──
    score, groups = 0, []
    for (a, b_, cc) in EMA_GROUPS:
        if n < cc:
            groups.append(False)
            continue
        ea, eb, ec = ema(close, a)[-1], ema(close, b_)[-1], ema(close, cc)[-1]
        up = ea > eb > ec
        groups.append(up)
        score += 1 if up else 0
    out["ema_score"] = score
    out["ema_groups"] = groups
    out["ema_strong"] = score >= 5
    out["ema_perfect"] = score == 7

    def ma(period, arr):
        return sum(arr[-period:]) / period if n >= period else None

    ma5, ma10, ma20, ma60 = ma(5, close), ma(10, close), ma(20, close), ma(60, close)
    ema20 = ema(close, 20)[-1] if n >= 20 else None
    ema60 = ema(close, 60)[-1] if n >= 60 else None
    out["ma_bullish"] = bool(ma5 and ma10 and ma20 and ma60 and ma5 > ma10 > ma20 > ma60)
    out["above_ema20"] = bool(ema20 and c > ema20)
    out["ema20"] = fmt_price(ema20) if ema20 else None
    out["ema60"] = fmt_price(ema60) if ema60 else None

    hi60, lo60 = max(high[-60:]), min(low[-60:])
    out["hi60"] = fmt_price(hi60)
    out["lo60"] = fmt_price(lo60)
    out["range_pos"] = round((c - lo60) / (hi60 - lo60) * 100, 1) if hi60 > lo60 else 50.0
    # 距 60 日高点回撤（负数 = 已回落）——「反弹 vs 趋势突破」的关键佐证
    out["dd_from_hi60"] = round((c - hi60) / hi60 * 100, 1)

    # ── 维度 1 · 量价关系 ──
    v_ma5 = sum(vol[-6:-1]) / 5 if n >= 6 else vol[-1]     # 前 5 日均量（不含当日）
    v_ma20 = sum(vol[-21:-1]) / 20 if n >= 21 else v_ma5
    vr = round(vol[-1] / v_ma5, 2) if v_ma5 else None
    out["vol_ratio_5"] = vr
    out["vol_ratio_20"] = round(vol[-1] / v_ma20, 2) if v_ma20 else None
    chg = (c - close[-2]) / close[-2] * 100 if n >= 2 else 0.0
    out["chg_pct"] = round(chg, 2)

    if vr is None:
        state, lvl = "未知", "mute"
    elif chg > 0 and vr >= 1.1:
        state, lvl = "放量上涨·健康推进", "up"
    elif chg > 0 and vr < 0.9:
        state, lvl = "缩量上涨·动能衰减", "warn"
    elif chg < 0 and vr >= 1.1:
        state, lvl = "放量下跌·派发嫌疑", "down"
    elif chg < 0 and vr < 0.9:
        state, lvl = "缩量回调·洗盘观察", "info"
    else:
        state, lvl = "平量整理", "mute"
    out["vol_price_state"], out["vol_price_level"] = state, lvl

    # 量价背离：当日为近 20 日收盘新高，但量 < 前 20 日内最高收盘日的量
    if n >= 21:
        win = rows[-20:]
        hi_row = max(win, key=lambda r: r["close"])
        out["vol_price_diverge"] = bool(c >= max(r["close"] for r in win) and vol[-1] < hi_row["volume"])
    else:
        out["vol_price_diverge"] = False

    # 量能结构与资金方向一致性（价涨而主力净流出 = 派发嫌疑）
    out["flow_aligned"] = bool((flow_yi > 0) == (chg > 0))

    # ── 维度 2 · 压力位 ──
    resist = []
    h20 = max(high[-20:]) if n >= 20 else max(high)
    if h20 > c * 1.002:
        resist.append({"price": fmt_price(h20), "src": "近20日高点"})
    if hi60 > c * 1.002 and abs(hi60 - h20) / h20 > 0.005:
        resist.append({"price": fmt_price(hi60), "src": "近60日高点"})
    for period, label in ((20, "EMA20"), (60, "EMA60")):
        if n >= period:
            e = ema(close, period)[-1]
            if e > c * 1.002:
                resist.append({"price": fmt_price(e), "src": f"上方{label}"})
    # 斐波那契（近 60 日 低→高 的回撤位中位于现价上方者）
    if hi60 > lo60:
        for ratio, tag in ((0.382, "斐波38.2%"), (0.5, "斐波50%"), (0.618, "斐波61.8%")):
            p = lo60 + (hi60 - lo60) * ratio
            if p > c * 1.002:
                resist.append({"price": fmt_price(p), "src": tag})
        ext = hi60 + (hi60 - lo60) * 0.618
        resist.append({"price": fmt_price(ext), "src": "斐波161.8%延伸"})

    # ── 维度 3 · 支撑位 ──
    support = []
    l20 = min(low[-20:]) if n >= 20 else min(low)
    if l20 < c * 0.998:
        support.append({"price": fmt_price(l20), "src": "近20日低点"})
    if lo60 < c * 0.998 and abs(lo60 - l20) / max(l20, 1e-9) > 0.005:
        support.append({"price": fmt_price(lo60), "src": "近60日低点"})
    for period, label in ((20, "EMA20"), (60, "EMA60")):
        if n >= period:
            e = ema(close, period)[-1]
            if e < c * 0.998:
                support.append({"price": fmt_price(e), "src": f"{label}支撑"})
    if hi60 > lo60:
        for ratio, tag in ((0.618, "斐波61.8%"), (0.5, "斐波50%"), (0.382, "斐波38.2%")):
            p = lo60 + (hi60 - lo60) * ratio
            if p < c * 0.998:
                support.append({"price": fmt_price(p), "src": tag})

    def dedup_sort(items, desc):
        items = sorted(items, key=lambda x: -x["price"] if desc else x["price"])
        keep = []
        for it in items:
            if all(abs(it["price"] - k["price"]) / k["price"] > 0.005 for k in keep):
                keep.append(it)
        return keep[:3]

    out["resistance"] = dedup_sort(resist, desc=False)   # 压力：由近及远 = 升序
    out["support"] = dedup_sort(support, desc=True)      # 支撑：由近及远 = 降序
    return out, None


# ══════════════════════ 3. 分级 ══════════════════════
def trend_type(tech):
    """趋势四态（2026-09-17 实跑校准第 3 轮：原三态把两种截然不同的情况混为 broken ——
       「长期上升但短期跌破 EMA20」与「长期下跌且短期破位」风险完全不同，
       实测煤炭/石油石化 EMA 5/7 却因破 EMA20 被判 broken，语义失真）。

       uptrend            = EMA 7/7 >=5 且 站上 EMA20  → 多周期共振向上
       uptrend_pullback   = EMA 7/7 >=5 但跌破 EMA20  → **长期上升中的回踩**（破位仍降档，但背景向好）
       downtrend_rebound  = EMA 7/7 < 5 但站上 EMA20  → **中期下跌趋势中的反弹**（须显式风险标注）
       downtrend          = EMA 7/7 < 5 且跌破 EMA20  → 最弱
    """
    if not tech:
        return "unknown"
    strong = bool(tech.get("ema_strong"))
    above = bool(tech.get("above_ema20"))
    if strong and above:
        return "uptrend"
    if strong and not above:
        return "uptrend_pullback"
    if not strong and above:
        return "downtrend_rebound"
    return "downtrend"


def classify(verdict, pct, streak, hot, tech, flow_yi):
    """返回 (档位, 理由)。**本函数是档位唯一权威**。"""
    if verdict in ("背离", "双冷") or flow_yi <= 0:
        return "L1", f"{verdict}·资金{'净流出' if flow_yi <= 0 else '不足'}"

    tt = trend_type(tech)
    # 破位降档：收盘 < EMA20（纪律 = 技术破位优先于资金面论证，不因 ema_score 高而豁免）
    if tt in ("downtrend", "unknown", "uptrend_pullback"):
        if not tech:
            why = "K 线缺失"
        elif tt == "uptrend_pullback":
            why = f"跌破 EMA20（{tech.get('ema20')}）——长期趋势仍向上（EMA {tech.get('ema_score')}/7），属回踩"
        else:
            why = f"破位（收盘 < EMA20 {tech.get('ema20')}，EMA {tech.get('ema_score')}/7）"
        return "L2", "技术面降档：" + why

    # 资金强度：连续 >=2 日，或「反转首日」（连续中断后首日 + 分位极高）
    reversal = (streak == 1 and pct >= PCT_REVERSAL)
    strong_flow = (pct >= PCT_L4) and (streak >= STREAK_MIN or reversal)
    hot_ok = bool(hot)

    r = []
    if streak >= STREAK_MIN:
        r.append(f"连续{streak}日净流入")
    elif reversal:
        r.append(f"反转首日(分位{pct})")
    if hot_ok:
        r.append(f"热度达标(日均≥{HOT_PER_DAY})")
    tail = "｜趋势" + ("向上" if tt == "uptrend" else "为反弹（中期趋势未反转）")

    if strong_flow and hot_ok:
        return "L4", "资金分位%d(≥%d)+%s%s" % (pct, PCT_L4, "+".join(r), tail)
    if (pct >= PCT_L3 and hot_ok) or strong_flow:
        return "L3", "资金分位%d+%s%s" % (pct, "+".join(r) or "—", tail)
    return "L2", "未达门槛（资金分位%d、连续%d日、热度%s）%s" % (
        pct, streak, "达标" if hot_ok else "不足", tail)


# ══════════════════════ 4. 页面呈现：7.1b 段 + CSS（幂等注入）══════════════════════
# 设计要点（2026-09-17）：
#   · 段落 =「7.1b · 板块技术研判」，插在 `<!-- 7.2 重点观测股` **之前**
#     （该锚点是 build_obs_section.py 的 START_ANCHOR，其替换区间为 [7.2, 7.3) → 插在 7.2 之前**不在**区间内，安全）
#   · 本段**由本脚本生成**（生成式代码纪律：脚本是唯一权威，手改会被下次注入覆盖）
#   · 一律用**显式起止标记**（铁律 30：禁宽正则定位代码块）
#   · CSS 同步写入 analysis.html 自包含 style（铁律 11：类名必须有定义）
ANALYSIS = os.path.join(BASE, "data", "daily_review", "analysis.html")
ANALYSIS_DEPLOY = os.path.join(BASE, "deploy", "data", "daily_review", "analysis.html")

SEC_BEGIN = "<!-- ═══ 7.1b SECTOR-TECH-BEGIN（由 review/build_sector_tech.py 生成 · 勿手改）═══ -->"
SEC_END = "<!-- ═══ 7.1b SECTOR-TECH-END ═══ -->"
CSS_BEGIN = "/* ═══ SECTOR-TECH-CSS v1 ═══ */"
CSS_END = "/* ═══ /SECTOR-TECH-CSS v1 ═══ */"
INSERT_BEFORE = "<!-- 7.2 重点观测股"


def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_css():
    return "\n".join([
        CSS_BEGIN,
        ".st-sum{font-size:12.5px;color:var(--text-muted);margin-bottom:6px;line-height:1.75}",
        ".st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(272px,1fr));gap:6px;align-items:start}",
        ".st-card{border:1px solid var(--border);border-radius:5px;padding:6px 8px;background:var(--bg-subtle)}",
        ".st-hd{font-size:13px;margin-bottom:4px;line-height:1.6}",
        ".st-lv{display:inline-block;font-size:11px;padding:1px 5px;border-radius:3px;font-weight:700;margin-right:4px;vertical-align:1px}",
        ".st-lv4{background:rgba(231,76,60,.16);color:var(--red)}",
        ".st-lv3{background:rgba(245,158,11,.18);color:var(--orange)}",
        ".st-tr{font-size:11px;color:var(--text-muted);margin-left:2px}",
        ".st-tr-weak{color:var(--orange)}",
        ".st-kv{width:100%;font-size:12.5px;border-collapse:collapse}",
        ".st-kv td{padding:1px 0;vertical-align:top;line-height:1.65}",
        ".st-kv td:first-child{color:var(--text-muted);white-space:nowrap;width:46px}",
        ".st-kv td.st-res{color:var(--red)}",
        ".st-kv td.st-sup{color:var(--green)}",
        ".st-why{font-size:11.5px;color:var(--text-muted);margin-top:4px;border-top:1px dashed var(--border);padding-top:3px;line-height:1.65}",
        ".st-note{font-size:11.5px;color:var(--orange);margin-top:6px;line-height:1.7}",
        CSS_END,
    ])


def _price_line(items, cls):
    if not items:
        return "—"
    return " ／ ".join(f'<b>{x["price"]}</b>（{esc(x["src"])}）' for x in items)


def render_section(d: dict) -> str:
    """生成 7.1b 段 HTML"""
    s, td, LAB = d.get("summary") or {}, d.get("trend_dist") or {}, d.get("trend_labels") or {}
    focus = [r for r in (d.get("items") or []) if r.get("level") in ("L4", "L3")]
    trend_txt = " ｜ ".join(f"{LAB.get(k, k)} {v}" for k, v in td.items())
    lv_txt = " ｜ ".join(
        f'<span class="st-lv st-lv4">{k} {s.get(k, 0)}</span>' if k == "L4"
        else f'<span class="st-lv st-lv3">{k} {s.get(k, 0)}</span>' if k == "L3"
        else f"{k} {s.get(k, 0)}" for k in LEVELS)

    parts = [
        SEC_BEGIN,
        '<div class="dr-h">7.1b · 板块技术研判（申万一级 31 · 数据日 '
        f'{esc(d.get("data_date"))} · 共振置信度分级 + 量价/压力/支撑 · 自动生成）</div>',
        '<div class="dr-card" style="margin-top:4px">',
        f'<div class="st-sum">分级：{lv_txt}<br>趋势结构：{trend_txt}'
        f'<br>阈值：资金分位 ≥{d["thresholds"]["pct_L4"]}/{d["thresholds"]["pct_L3"]}'
        f' ｜ 连续 ≥{d["thresholds"]["streak_min"]} 日（或反转首日 ≥{d["thresholds"]["pct_reversal"]}）'
        f' ｜ 热度日均 ≥{d["thresholds"]["hot_per_day"]} ｜ 破位线 EMA{d["thresholds"]["ema20_line"]}'
        '（技术面为**否决项**：跌破即降档）</div>',
    ]
    if not focus:
        parts.append('<div class="st-note">本日无 L4/L3 板块'
                     '（资金未能同时满足「分位达标 + 连续/反转首日」且未破位）—— '
                     '属正常结果，不代表无机会，仅表示无高置信度共振。</div>')
    else:
        parts.append('<div class="st-grid">')
        for r in focus:
            t = r.get("tech") or {}
            lv_cls = "st-lv4" if r["level"] == "L4" else "st-lv3"
            tr_cls = "st-tr st-tr-weak" if r.get("trend") in ("downtrend_rebound",) else "st-tr"
            vol = t.get("vol_price_state", "—")
            vr = t.get("vol_ratio_5")
            parts += [
                '<div class="st-card">',
                f'<div class="st-hd"><span class="st-lv {lv_cls}">{r["level"]}</span>'
                f'<b>{esc(r["sector"])}</b>'
                f'<span class="{tr_cls}">{LAB.get(r.get("trend"), "")}</span></div>',
                '<table class="st-kv"><tbody>',
                f'<tr><td>现价</td><td class="dr-wrap" colspan="3"><b>{t.get("close", "—")}</b>'
                f' ｜ EMA {t.get("ema_score", "—")}/7 ｜ 区间分位 {t.get("range_pos", "—")}%'
                f' ｜ 距 60 日高 <b>{t.get("dd_from_hi60", "—")}%</b></td></tr>',
                f'<tr><td>压力</td><td class="st-res dr-wrap" colspan="3">{_price_line(t.get("resistance"), "res")}</td></tr>',
                f'<tr><td>支撑</td><td class="st-sup dr-wrap" colspan="3">{_price_line(t.get("support"), "sup")}</td></tr>',
                f'<tr><td>量价</td><td class="dr-wrap" colspan="3">{esc(vol)}'
                + (f'（量比 5 日 {vr}）' if vr else '')
                + (' ｜ <b>量价背离</b>' if t.get("vol_price_diverge") else '')
                + (' ｜ 资金与价格同向' if t.get("flow_aligned") else ' ｜ ⚠️ 资金与价格反向')
                + '</td></tr>',
                '</tbody></table>',
                f'<div class="st-why">依据：{esc(r.get("why"))}</div>',
                '</div>',
            ]
        parts.append('</div>')
    if d.get("missing"):
        parts.append(f'<div class="st-note">⚠️ 数据缺口 {len(d["missing"])} 项：'
                     + esc("；".join(d["missing"][:3])) + '</div>')
    parts.append('</div>')
    parts.append(SEC_END)
    return "\n".join(parts)


def _block_replace(text, begin, end, new_block):
    """幂等整块替换（显式标记；标记缺失则返回 None 表示未命中）"""
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0 or j < i:
        return None
    return text[:i] + new_block + text[j + len(end):]


def inject_analysis(d: dict, dry_run=False):
    """把 7.1b 段 + CSS 注入 analysis.html 及其 deploy 副本（幂等）"""
    if not os.path.exists(ANALYSIS):
        return False, f"analysis.html 不存在：{ANALYSIS}"
    msgs = []
    sec = render_section(d)
    css = render_css()
    for path in (ANALYSIS, ANALYSIS_DEPLOY):
        if not os.path.exists(path):
            msgs.append(f"跳过（不存在）{os.path.relpath(path, BASE)}")
            continue
        t = open(path, encoding="utf-8").read()   # 注意：'utf-8' 保留 BOM 字符，勿用 utf-8-sig
        n_css = t.count(CSS_BEGIN)
        # ① CSS：幂等替换；缺失则插到 </style> 前
        new = _block_replace(t, CSS_BEGIN, CSS_END, css)
        if new is None:
            k = t.find("</style>")
            if k < 0:
                msgs.append(f"❌ {os.path.relpath(path, BASE)} 无 </style>，CSS 未注入")
                continue
            new = t[:k] + css + "\n" + t[k:]
            css_action = "插入"
        else:
            css_action = "替换"
        # ② 段落：幂等替换；缺失则插到 INSERT_BEFORE 前
        new2 = _block_replace(new, SEC_BEGIN, SEC_END, sec)
        if new2 is None:
            k = new.find(INSERT_BEFORE)
            if k < 0:
                msgs.append(f"❌ {os.path.relpath(path, BASE)} 未找到锚点 {INSERT_BEFORE!r}，段落未注入")
                continue
            new2 = new[:k] + sec + "\n\n" + new[k:]
            sec_action = "插入"
        else:
            sec_action = "替换"
        if not dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new2)
        msgs.append(f"{os.path.relpath(path, BASE)}：CSS {css_action}(旧块{n_css}) · 段落 {sec_action}")
    return True, " ｜ ".join(msgs)


# ══════════════════════ main ══════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="只用本地 K 线缓存（离线自检）")
    ap.add_argument("--no-html", action="store_true", help="只出 JSON，不注入 analysis.html")
    ap.add_argument("--dry-run", action="store_true", help="只打印将做的注入，不落盘")
    ap.add_argument("--sectors", default="", help="只处理指定板块（逗号分隔，调试用）")
    args = ap.parse_args()

    print("═══ 板块技术分析（置信度分级 + 三维）构建 ═══")
    cross = load(CROSS, {}) or {}
    flow = load(FLOW, {}) or {}

    items_in = cross.get("items") or []
    if not items_in:
        print("  ❌ cross_analysis.json 无 items，退出"); sys.exit(1)

    # 数据日：一律取 cross_analysis 的 flow_date（= 最近已收盘交易日），禁 datetime.now()（铁律 23）
    data_date = cross.get("flow_date") or cross.get("data_date") or ""
    hot_per_day = cross.get("hot_per_day", HOT_PER_DAY)
    print(f"  📅 数据日 {data_date} ｜ 新闻窗口 {cross.get('news_window')} ｜ 热度阈值 日均{hot_per_day}")

    # 资金流历史（→ 连续性）
    hist = flow.get("history") or {}
    flow_days = sorted(d for d in hist if d <= data_date)

    names = [it.get("sector") for it in items_in if it.get("sector")]
    if args.sectors:
        want = {s.strip() for s in args.sectors.split(",") if s.strip()}
        names = [n for n in names if n in want]

    klines, missing = fetch_klines(names, no_fetch=args.no_fetch)

    # 资金分位（当日 31 个板块内）
    flows = [it.get("flow_yi") or 0 for it in items_in]

    rows = []
    for it in items_in:
        name = it.get("sector")
        if not name or (args.sectors and name not in names):
            continue
        flow_yi = it.get("flow_yi") or 0
        pct = pct_rank(flows, flow_yi)
        # 连续性：从数据日往前，连续净流入天数
        streak = 0
        for d in reversed(flow_days):
            secs = (hist.get(d) or {}).get("sectors") or []
            v = next((s.get("main_net_flow") or 0 for s in secs if s.get("name") == name), 0)
            if v > 0:
                streak += 1
            else:
                break
        hot = (it.get("news_per_day") or 0) >= hot_per_day
        tech, terr = (None, "无K线")
        if klines.get(name):
            tech, terr = tech_analysis(klines[name], flow_yi, data_date)
        if terr and not tech:
            missing.append(f"{name}：{terr}")
        lvl, why = classify(it.get("verdict"), pct, streak, hot, tech, flow_yi)
        rows.append({
            "sector": name, "level": lvl, "why": why,
            "trend": trend_type(tech),
            "verdict": it.get("verdict"), "level_quad": it.get("level"),
            "flow_yi": flow_yi, "flow_pct": pct, "flow_streak": streak,
            "news_count": it.get("news_count"), "news_per_day": it.get("news_per_day"),
            "hot": hot, "tech": tech,
        })

    order = {v: i for i, v in enumerate(LEVELS)}
    rows.sort(key=lambda r: (order.get(r["level"], 9), -abs(r["flow_yi"] or 0)))

    summary = {lv: sum(1 for r in rows if r["level"] == lv) for lv in LEVELS}
    trend_dist = {t: sum(1 for r in rows if r["trend"] == t) for t in TREND_TYPES}
    payload = {
        "data_date": data_date,
        "generated_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "news_window": cross.get("news_window"),
        "flow_date": cross.get("flow_date"),
        "thresholds": {"pct_L4": PCT_L4, "pct_L3": PCT_L3, "streak_min": STREAK_MIN,
                       "pct_reversal": PCT_REVERSAL, "hot_per_day": hot_per_day,
                       "ema20_line": EMA20_LINE},
        "levels": list(LEVELS),          # 档位字面值唯一权威（守卫断言前端 ⊆ 此）
        "trend_types": list(TREND_TYPES),  # 趋势类型唯一权威（含中文说明供前端直接用）
        "trend_labels": TREND_LABELS,
        "summary": summary,
        "trend_dist": trend_dist,
        "items": rows,
        "missing": sorted(set(missing)),
    }
    save_both("sector_tech.json", payload)

    print(f"\n  📊 分级： " + " ｜ ".join(f"{k} {v}" for k, v in summary.items()))
    print(f"  📈 趋势： " + " ｜ ".join(f"{TREND_LABELS[k]} {v}" for k, v in trend_dist.items()))
    for r in rows:
        t = r["tech"] or {}
        rp = (t.get("resistance") or [{}])[0].get("price")
        sp = (t.get("support") or [{}])[0].get("price")
        print(f"   {r['level']}  {r['sector']:<6} 资金{r['flow_yi']:>8.2f}亿(分位{r['flow_pct']:>5}) "
              f"连续{r['flow_streak']}  {TREND_LABELS[r['trend']]:<12} EMA{t.get('ema_score','-')}/7  "
              f"现价{t.get('close','-')} 压{rp or '-'} 撑{sp or '-'} 距高{t.get('dd_from_hi60','-')}%")
    if payload["missing"]:
        print(f"\n  ⚠️ 缺口 {len(payload['missing'])} 项：")
        for m in payload["missing"][:8]:
            print(f"     · {m}")
    print(f"\n  💾 output/sector_tech.json + deploy 副本")

    # ── 页面呈现：7.1b 段 + CSS（幂等注入）──
    if args.no_html:
        print("  ⏭  --no-html：跳过 analysis.html 注入")
    else:
        ok, msg = inject_analysis(payload, dry_run=args.dry_run)
        print(f"  {'🖼 7.1b 注入' + ('（dry-run）' if args.dry_run else '')}：{'✅' if ok else '❌'} {msg}")


if __name__ == "__main__":
    main()
