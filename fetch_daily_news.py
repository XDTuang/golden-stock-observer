#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 每日新闻池自动抓取（每日复盘 6 段「新闻整合」的自动数据源）
=========================================================================
抓取多源实时新闻，按关键词打标（宏观/科技/政策/产业/持仓/美股映射），
标题归一化去重后落：
  output/daily_news_<T>.json      当日全量
  output/daily_news_latest.json   当日副本（前端 fetch 用）

数据源（2026-08-28 实测全部可用、实时）：
  主源: 东财全球资讯 stock_info_global_em（200 条/实时）
        财经早餐   stock_info_cjzc_em（隔夜要闻汇总，最适合盘前口径）
  备用: 新浪全球   stock_info_global_sina（快讯流）
        同花顺全球 stock_info_global_ths
        富途全球   stock_info_global_futu
  政策: 央视新闻联播 news_cctv(date)（当日全文）

设计原则（2026-08-28 审计）：
  - 只增不覆盖：落独立 JSON，本机 agent 推演（analysis.html / feed_review_*.json）不受影响；
  - 失败不阻断：单个源失败仅警告，不整体退出；
  - 来源可溯：每条新闻带 source + url。

用法:
  python fetch_daily_news.py               # 抓全部源
  python fetch_daily_news.py --sources em,breakfast,sina
"""
import os, re, sys, json, hashlib, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "output")
DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# ── 标签关键词（按优先级匹配）─────────────────────────────
TAG_RULES = {
    "宏观":   ["PCE", "CPI", "PMI", "GDP", "非农", "初请", "美联储", "降息", "加息", "央行",
              "LPR", "社融", "M2", "关税", "通胀", "利率", "国债", "美债", "欧央行", "日央行",
              "鲍威尔", "沃什", "经济数据", "景气"],
    "科技":   ["NVDA", "英伟达", "算力", "GPU", "AI芯片", "芯片", "半导体", "光模块", "CPO",
              "数据中心", "存储", "HBM", "财报", "Marvell", "迈威尔", "博通", "AMD", "台积电",
              "英伟达", "微软", "苹果", "Meta", "大模型", "液冷", "PCB", "铜缆"],
    "政策":   ["证监会", "央行", "国务院", "发改委", "政治局", "政策", "监管", "IPO", "注册制",
              "降准", "降息", "反垄断", "审查"],
    "产业":   ["新能源", "锂", "电池", "光伏", "风电", "机器人", "汽车", "医药", "创新药",
              "军工", "稀土", "煤炭", "贵金属", "工业金属", "有色", "石油", "黄金"],
    "美股映射": ["SNDK", "MU", "LITE", "AAOI", "COHR", "WDC", "SKHY", "MRVL", "美光",
              "闪迪", "Coherent", "Lumentum", "Marvell"],
    "持仓":   ["永杉", "昊华", "华工", "永鼎", "剑桥", "长鑫", "万邦"],
}
ALL_TAGS = list(TAG_RULES.keys())

def tag_text(text):
    t = text.upper()
    tags = []
    for tag, kws in TAG_RULES.items():
        for kw in kws:
            if kw.upper() in t:
                tags.append(tag)
                break
    return tags

def norm_title(title):
    """标题归一化（去空白/去常见符号），用于去重。"""
    s = re.sub(r"[\s\u3000【】\[\]（）()\"'“”]+", "", title)
    return s

def dedup(items):
    seen, out = set(), []
    for it in items:
        k = it.get("_key", norm_title(it.get("title", "")))
        if k in seen:
            continue
        seen.add(k)
        it.pop("_key", None)
        out.append(it)
    return out

# ── 各源抓取（akshare）───────────────────────────────────
def _ak(fn, **kw):
    try:
        import akshare as ak
        f = getattr(ak, fn)
        return f(**kw)
    except Exception as e:
        print(f"  ⚠️ {fn}: {type(e).__name__}: {str(e)[:80]}")
        return None

def grab_em():
    df = _ak("stock_info_global_em")
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        title = str(r.get("标题", "") or "")
        if not title:
            continue
        out.append({
            "title": title,
            "summary": str(r.get("摘要", "") or ""),
            "time": str(r.get("发布时间", "") or ""),
            "source": "东财全球",
            "url": str(r.get("链接", "") or ""),
            "_key": norm_title(title),
        })
    return out

def grab_breakfast():
    df = _ak("stock_info_cjzc_em")
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        title = str(r.get("标题", "") or "")
        if not title:
            continue
        out.append({
            "title": title,
            "summary": str(r.get("摘要", "") or ""),
            "time": str(r.get("发布时间", "") or ""),
            "source": "财经早餐",
            "url": str(r.get("链接", "") or ""),
            "_key": norm_title(title),
        })
    return out

def grab_sina():
    df = _ak("stock_info_global_sina")
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        content = str(r.get("内容", "") or "")
        if not content:
            continue
        out.append({
            "title": content[:40],
            "summary": content,
            "time": str(r.get("时间", "") or ""),
            "source": "新浪全球",
            "url": "",
            "_key": norm_title(content[:40]),
        })
    return out

def grab_ths():
    df = _ak("stock_info_global_ths")
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        title = str(r.get("标题", "") or "")
        if not title:
            continue
        out.append({
            "title": title,
            "summary": str(r.get("内容", "") or ""),
            "time": str(r.get("发布时间", "") or ""),
            "source": "同花顺全球",
            "url": str(r.get("链接", "") or ""),
            "_key": norm_title(title),
        })
    return out

def grab_futu():
    df = _ak("stock_info_global_futu")
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        content = str(r.get("内容", "") or "")
        title = str(r.get("标题", "") or "") or content[:40]
        if not content and not title:
            continue
        out.append({
            "title": title,
            "summary": content,
            "time": str(r.get("发布时间", "") or ""),
            "source": "富途全球",
            "url": str(r.get("链接", "") or ""),
            "_key": norm_title(title),
        })
    return out

def grab_cctv():
    df = _ak("news_cctv", date=datetime.datetime.now().strftime("%Y%m%d"))
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        title = str(r.get("title", "") or "")
        if not title:
            continue
        out.append({
            "title": title,
            "summary": str(r.get("content", "") or "")[:200],
            "time": str(r.get("date", "") or ""),
            "source": "央视联播",
            "url": "",
            "_key": norm_title(title),
        })
    return out

GRABBERS = {
    "em": ("东财全球", grab_em),
    "breakfast": ("财经早餐", grab_breakfast),
    "sina": ("新浪全球", grab_sina),
    "ths": ("同花顺全球", grab_ths),
    "futu": ("富途全球", grab_futu),
    "cctv": ("央视联播", grab_cctv),
}

def main():
    want = sys.argv[sys.argv.index("--sources") + 1].split(",") if "--sources" in sys.argv else list(GRABBERS)
    print(f"═══ 每日新闻池抓取 {DATE} ═══")
    all_items, src_stat = [], {}
    for key in want:
        name, fn = GRABBERS[key]
        print(f"· 抓取 {name} ...")
        items = fn()
        print(f"  ✅ {name}: {len(items)} 条")
        src_stat[name] = len(items)
        all_items.extend(items)

    all_items = dedup(all_items)
    # 打标
    for it in all_items:
        it["tags"] = tag_text(it["title"] + " " + it.get("summary", ""))
    tag_stats = {t: sum(1 for x in all_items if t in x["tags"]) for t in ALL_TAGS}

    payload = {
        "date": DATE,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sources": src_stat,
        "total": len(all_items),
        "tag_stats": tag_stats,
        "news": all_items,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in (f"daily_news_{DATE}.json", "daily_news_latest.json"):
        p = os.path.join(OUT_DIR, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"💾 {p}（{len(all_items)} 条）")
    print(f"标签统计: {tag_stats}")

if __name__ == "__main__":
    main()
