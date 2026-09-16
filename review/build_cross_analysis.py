#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投喂复盘 Tab · cross_analysis（机制 × 语料交叉验证）自动构建
==============================================================
输入（全部为公开/本地自动数据源，无需投喂）：
  output/daily_news_latest.json   公开新闻池（fetch_daily_news.py 抓取）
  output/sector_flow.json         板块主力资金流（本地/云端自动）
  data/daily_review/market.json   指数行情（腾讯源）
输出：output/cross_analysis.json（前端投喂复盘 Tab 消费）

验证机制（语料热度 × 资金流向 四象限 · 字面值以 QUADRANTS 为准）：
  新闻热度高 + 资金净流入 → 「共振」    语料与资金同向，主线成立（显示名「真共振」）
  新闻热度高 + 资金净流出 → 「背离」    语料热但资金撤，警惕高位分歧/利好出尽
  新闻热度低 + 资金净流入 → 「暗线」    主力提前布局，语料尚未发酵（潜伏机会）
  新闻热度低 + 资金净流出 → 「双冷」    无题材无资金，回避

设计原则：
  - 公开数据源必选（新闻池 + 资金流 + 行情），全流程可自动；
  - 投喂非必需：本脚本不依赖任何投喂素材；
  - 失败不阻断：任一数据源缺失时降级为空条目，前端显示提示。

用法:
  python review/build_cross_analysis.py
"""
import os, re, json, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "output")
NEWS = os.path.join(OUT_DIR, "daily_news_latest.json")
FLOW = os.path.join(OUT_DIR, "sector_flow.json")
MARKET = os.path.join(BASE, "data", "daily_review", "market.json")
OUT_PATH = os.path.join(OUT_DIR, "cross_analysis.json")

# 板块 → 新闻命中关键词（板块名本身自动作为兜底关键词）
SECTOR_KW = {
    "电子":     ["芯片", "半导体", "存储", "PCB", "光模块", "CPO", "覆铜板", "HBM", "DRAM",
               "英伟达", "NVDA", "台积电", "算力", "晶圆", "封测", "长鑫", "长存", "兆易", "澜起"],
    "有色金属": ["黄金", "有色", "稀土", "铜", "铝", "贵金属", "白银", "锂", "钴", "小金属"],
    "基础化工": ["化工", "氟", "制冷剂", "PTFE", "化肥", "农药", "聚氨酯", "化纤", "聚酯",
               "煤化工", "氯碱", "纯碱", "巨化", "万华"],
    "计算机":   ["AI", "算力", "软件", "信创", "国产替代", "大模型", "Agent", "数据要素", "鸿蒙"],
    "通信":     ["光通信", "CPO", "5G", "6G", "光模块", "光纤", "运营商", "卫星", "海缆"],
    "医药生物": ["医药", "创新药", "疫苗", "CXO", "医疗器械", "中药", "集采", "减肥药", "抗体"],
    "电力设备": ["光伏", "电池", "锂电", "储能", "电网", "特高压", "风电", "逆变器", "固态电池"],
    "农林牧渔": ["农业", "种业", "粮食", "玉米", "大豆", "生猪", "猪价", "转基因", "农机", "厄尔尼诺"],
    "房地产":   ["房地产", "楼市", "房贷", "地产", "住房", "公积金", "保障房", "现房", "房企"],
    "国防军工": ["军工", "国防", "导弹", "军贸", "航空", "卫星", "无人机"],
    "汽车":     ["汽车", "新能源车", "智驾", "自动驾驶", "固态电池", "充电桩", "特斯拉", "比亚迪"],
    "机械设备": ["机械", "机器人", "人形", "减速器", "丝杠", "机床", "工程机械", "具身智能"],
    "传媒":     ["传媒", "游戏", "影视", "短剧", "AI应用", "营销", "出版", "IP"],
    "煤炭":     ["煤炭", "焦煤", "动力煤", "原煤"],
    "石油石化": ["石油", "原油", "油气", "石化", "OPEC", "炼化"],
    "钢铁":     ["钢铁", "钢材", "铁矿石", "特钢"],
    "银行":     ["银行", "LPR", "存款", "信贷", "社融", "不良"],
    "非银金融": ["券商", "保险", "非银", "两融", "IPO", "公募"],
    "食品饮料": ["白酒", "食品", "饮料", "消费", "乳业", "调味品"],
    "公用事业": ["电力", "燃气", "水务", "电价"],
}
# 热度阈值（新闻命中条数）：≥ 该值视为"语料热"
HOT_MIN = 8

# ── 判定象限「字面值」唯一权威（2026-09-16 治本 · 铁律：数据侧与渲染侧字面值不得漂移）──
#   背景：verdict_of 原先对第一象限返回「真共振」，而 summary 的键与前端渲染的过滤条件都用「共振」
#   → V3 第 7 段 `items.filter(x => x.verdict === '共振')` 永远命中 0 条（共振明细静默漏空，
#     只是长期被「当日共振=0」掩盖）。现统一为「共振」，原显示名另存 verdict_raw 以便追溯。
#   🔴 新增/改名象限时：只需改本元组 + verdict_of 的返回，前端与守卫会自动对齐。
QUADRANTS = ("共振", "背离", "暗线", "双冷")
# 对外显示名（仅用于文案与追溯；前端 chips / 过滤一律用 QUADRANTS 内的规范字面值）
VERDICT_RAW = {"共振": "真共振", "背离": "背离", "暗线": "暗线", "双冷": "双冷"}


def load(p):
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ 读取失败 {p}: {e}")
        return None


def count_news(items, sector):
    kws = SECTOR_KW.get(sector, []) + [sector]
    n = 0
    hit_titles = []
    for it in items:
        text = (str(it.get("title", "")) + " " + str(it.get("summary", ""))).upper()
        for kw in kws:
            if str(kw).upper() in text:
                n += 1
                if len(hit_titles) < 3:
                    hit_titles.append(str(it.get("title", ""))[:38])
                break
    return n, hit_titles


def verdict_of(news_n, flow_yi):
    """四象限判定：语料热度 × 资金流向。返回值一律取自 QUADRANTS（禁另起字面值）。"""
    hot = news_n >= HOT_MIN
    inflow = flow_yi > 0
    if hot and inflow:
        return "共振", "ok", "语料与资金同向，主线成立"
    if hot and not inflow:
        return "背离", "warn", "语料热但资金撤，警惕高位分歧 / 利好出尽"
    if not hot and inflow:
        return "暗线", "info", "主力提前布局，语料尚未发酵（潜伏观察）"
    return "双冷", "mute", "无题材无资金，回避"


def pick_trade_day(hist):
    """取最近交易日（跳过周六日）。周末落盘的是上一交易日收盘数据的副本。"""
    if not hist:
        return "—", []
    keys = sorted(hist.keys(), reverse=True)
    for k in keys:
        try:
            if datetime.datetime.strptime(k, "%Y-%m-%d").weekday() < 5:  # 0~4 = 周一~五
                return k, hist[k].get("sectors", []) or []
        except Exception:
            continue
    k = keys[0]
    return k, hist[k].get("sectors", []) or []


def main():
    print("═══ cross_analysis（机制 × 语料交叉验证）构建 ═══")
    news = load(NEWS) or {}
    flow = load(FLOW) or {}
    mkt = load(MARKET) or {}

    items = news.get("news", []) or []
    hist = flow.get("history", {}) or {}
    # 取"最近交易日"的板块资金流。
    # ⚠️ 坑（2026-08-29 实测）：周末脚本也会落盘，且复用上一交易日收盘数据
    #    （8/29 与 8/28 的 top_out 完全相同：电子 -186.85 / 通信 -63.42）。
    #    若直接取 sorted(keys)[-1] 会把周末键当作新数据，造成"周六有资金流"的误导。
    #    故此处跳过周六日，回退到最近的工作日键。
    raw_latest = sorted(hist.keys())[-1] if hist else "—"
    latest_day, sectors = pick_trade_day(hist)

    print(f"  📰 新闻池 {news.get('date','—')} · {len(items)} 条")
    print(f"  💰 资金流 {latest_day} · {len(sectors)} 个板块")

    rows = []
    for s in sectors:
        name = s.get("name", "")
        if not name:
            continue
        flow_yi = (s.get("main_net_flow") or 0) / 1e8
        n, titles = count_news(items, name)
        v, lvl, desc = verdict_of(n, flow_yi)
        rows.append({
            "sector": name,
            "news_count": n,
            "flow_yi": round(flow_yi, 2),
            "verdict": v,
            # 原显示名（仅追溯用）；前端过滤/归类一律用 verdict（= QUADRANTS 规范字面值）
            "verdict_raw": VERDICT_RAW.get(v, v),
            "level": lvl,
            "desc": desc,
            "sample_titles": titles,
        })

    # 自检：判定字面值必须全部落在 QUADRANTS 内（否则前端某类明细会静默漏空）
    _bad = sorted({r["verdict"] for r in rows} - set(QUADRANTS))
    assert not _bad, f"verdict 字面值越界（不在 QUADRANTS 内）：{_bad}"

    # 排序：先按 |flow| 量级，再按新闻热度
    rows.sort(key=lambda x: (abs(x["flow_yi"]), x["news_count"]), reverse=True)

    # 指数上下文
    q = (mkt.get("quotes") or {})
    idx_ctx = {}
    for k, nm in (("a_sh", "上证指数"), ("a_sz", "深证成指"), ("a_cyb", "创业板指"), ("a_kcb", "科创50")):
        e = q.get(k) or {}
        if e.get("close"):
            idx_ctx[nm] = {"close": e.get("close"), "chg_pct": e.get("chg_pct")}

    payload = {
        "date": news.get("date", datetime.datetime.now().strftime("%Y-%m-%d")),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "news_date": news.get("date", ""),
        "flow_date": latest_day,
        # 资金流原始最新键（可能为非交易日的周末副本），用于追溯与排错
        "flow_raw_latest": raw_latest,
        "flow_is_weekend_copy": (raw_latest != latest_day),
        "hot_threshold": HOT_MIN,
        "index_context": idx_ctx,
        # summary 的键 = QUADRANTS，计数口径与前端 filter 完全同源
        #（原先第一象限按 "真共振" 计数、键名却写 "共振"，两套口径是漏空的温床）
        "summary": {q: sum(1 for r in rows if r["verdict"] == q) for q in QUADRANTS},
        "items": rows,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  📊 判定分布: {payload['summary']}")
    for r in rows[:8]:
        print(f"     {r['sector']:<6} 新闻 {r['news_count']:>3} 条 · 资金 {r['flow_yi']:>8.2f} 亿 → {r['verdict']}")
    print(f"💾 {OUT_PATH}")


if __name__ == "__main__":
    main()
