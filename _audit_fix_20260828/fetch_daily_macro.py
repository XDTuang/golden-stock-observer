#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 每日宏观数据抓取（每日复盘 4 段「重点宏观信息」的自动数据源）
===========================================================================
中国宏观（akshare，实测新鲜，作主源）:
  macro_china_pmi / macro_china_gdp / macro_china_cpi / macro_china_lpr
美国宏观（akshare 已停更至 2025-09，不可直接使用）:
  改从新闻源（东财全球 + 财经早餐）按指标关键词过滤，抽取当日落地值，
  每条保留原始文本与来源（best-effort，命中即记，不编造）。

落盘:
  output/daily_macro_<T>.json
  output/daily_macro_latest.json（前端 fetch 用）

用法:
  python fetch_daily_macro.py
  python fetch_daily_macro.py --no-us   # 跳过美国宏观新闻抽取
"""
import os, re, sys, json, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "output")
DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# 美国宏观指标 → 新闻关键词（命中即记，含原始文本）
US_INDICATORS = {
    "核心PCE":   ["核心PCE", "核心PCE物价"],
    "整体PCE":   ["PCE物价", "PCE价格", "个人消费支出"],
    "CPI":       ["CPI", "消费者物价"],
    "非农":      ["非农", "新增就业"],
    "初请失业金": ["初请失业金", "初请"],
    "耐用品订单": ["耐用品订单"],
    "美国GDP":   ["美国GDP", "GDP初值", "GDP修正"],
    "美联储/利率": ["美联储", "利率决议", "降息", "加息", "点阵图", "鲍威尔", "沃什"],
    "美债收益率": ["美债收益率", "10年期美债", "10Y"],
}


def grab_news():
    """抓取新闻池（东财全球 + 财经早餐），供美国宏观抽取。"""
    import akshare as ak
    out = []
    for fn in ("stock_info_global_em", "stock_info_cjzc_em"):
        try:
            df = getattr(ak, fn)()
            if df is None or df.empty:
                continue
            for _, r in df.iterrows():
                title = str(r.get("标题", "") or "")
                summary = str(r.get("摘要", "") or "")
                if title or summary:
                    out.append({
                        "title": title,
                        "summary": summary,
                        "time": str(r.get("发布时间", "") or ""),
                        "source": "东财全球" if fn == "stock_info_global_em" else "财经早餐",
                        "url": str(r.get("链接", "") or ""),
                    })
        except Exception as e:
            print(f"  ⚠️ {fn}: {type(e).__name__}: {str(e)[:80]}")
    return out


def extract_us(news):
    """按指标关键词过滤新闻，抽取含百分比的句子作为证据。"""
    hits = {k: [] for k in US_INDICATORS}
    for it in news:
        text = it["title"] + " " + it["summary"]
        for ind, kws in US_INDICATORS.items():
            if any(kw in text for kw in kws):
                # 抽含 % 的片段（今值等数字证据）
                evs = re.findall(r"[^。；\n]{0,28}?[+-]?\d+\.\d+%[^。；\n]{0,18}", text)
                evidence = evs[:3]
                hits[ind].append({
                    "title": it["title"][:60],
                    "evidence": evidence or [text[:60]],
                    "time": it["time"],
                    "source": it["source"],
                })
                break
    # 每个指标最多保留 5 条
    return {k: v[:5] for k, v in hits.items() if v}


def grab_china():
    """中国宏观：akshare 4 接口，取最新一条。"""
    import akshare as ak
    res = {}
    try:
        df = ak.macro_china_pmi()
        res["pmi"] = {"latest": df.iloc[0].to_dict() if len(df) else None, "rows": len(df)}
    except Exception as e:
        res["pmi"] = {"error": str(e)[:100]}
    try:
        df = ak.macro_china_gdp()
        res["gdp"] = {"latest": df.iloc[0].to_dict() if len(df) else None, "rows": len(df)}
    except Exception as e:
        res["gdp"] = {"error": str(e)[:100]}
    try:
        df = ak.macro_china_cpi()
        res["cpi"] = {"latest": df.iloc[0].to_dict() if len(df) else None, "rows": len(df)}
    except Exception as e:
        res["cpi"] = {"error": str(e)[:100]}
    try:
        df = ak.macro_china_lpr()
        # LPR 接口为升序（最早在前），取最后一行 = 最新
        res["lpr"] = {"latest": df.iloc[-1].to_dict() if len(df) else None, "rows": len(df)}
    except Exception as e:
        res["lpr"] = {"error": str(e)[:100]}
    return res


def main():
    print(f"═══ 每日宏观抓取 {DATE} ═══")
    china = grab_china()
    print(f"· 中国宏观: PMI={china.get('pmi',{}).get('rows')} GDP={china.get('gdp',{}).get('rows')} "
          f"CPI={china.get('cpi',{}).get('rows')} LPR={china.get('lpr',{}).get('rows')}")

    us = {"note": "akshare 美国宏观已停更(最新2025-09)，以下为新闻源抽取(best-effort)", "indicators": {}}
    if "--no-us" not in sys.argv:
        print("· 抓取新闻池供美国宏观抽取 ...")
        news = grab_news()
        print(f"  新闻池: {len(news)} 条")
        us["indicators"] = extract_us(news)
        hit_n = sum(len(v) for v in us["indicators"].values())
        print(f"  美国宏观命中: {hit_n} 条 / {len(us['indicators'])} 个指标")

    payload = {
        "date": DATE,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "china": china,
        "us": us,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    # default=str: akshare 返回的 DataFrame 含 datetime.date 等类型（如 LPR 的 TRADE_DATE）
    for name in (f"daily_macro_{DATE}.json", "daily_macro_latest.json"):
        p = os.path.join(OUT_DIR, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        print(f"💾 {p}")


if __name__ == "__main__":
    main()
