#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 每日宏观数据抓取（每日复盘 4 段「重点宏观信息」的自动数据源）
===========================================================================
中国宏观（akshare 主源，实测新鲜）:
  macro_china_pmi / macro_china_gdp / macro_china_cpi / macro_china_lpr

美国宏观（2026-09-18 重构 · 修复「信息过期且不自更新」）:
  ── 原缺陷（实测证据）──────────────────────────────────────────
  ① 仅从新闻池抽取，而 stock_info_cjzc_em（财经早餐）返回 400 条历史
     （时间从当日一路回溯到 2025-01-23），抽取侧**无任何时间窗**；
  ② 未按时间排序，取列表前 N 条 → 命中 8/13 的 CPI、7/3 的非农
     （实测龄期 36 天 / 77 天），属于「有值但永远旧」的静默冻结；
  ③ 证据句质量门缺失 → 「非农」命中 2/12 那条，证据却是
     「国办印发《关于完善全国统一电力市场体系的实施意见》」（完全无关）；
  ④ 无时效标注，前端无从判断新鲜度。
  ── 现方案（三轨）──────────────────────────────────────────────
  A. 主源 = 百度经济日历 news_economic_baidu（按公布日逐日拉取）
     返回「日期/时间/地区/事件/公布/预期/前值/重要性」→ 权威且自带发布日期。
     窗口策略：先拉最近 US_CAL_FAST_DAYS 天；关键月频指标（CPI 同比 / 非农）
     若窗口内无命中，自动回看至多 US_CAL_MAX_LOOKBACK 天（覆盖月频公布节奏）。
     实测：9/11 公布美国8月CPI 3.4%（核心 2.4%）、9/4 公布非农 16.2 万 —— 均被原实现漏掉。
  B. 兜底 = 新闻抽取（东财全球 + 财经早餐），🔴 强制时间窗 + 时间倒序 + 证据质量门；
     仅当轨 A 失败或某指标 A 无覆盖时启用。
  C. 时效标注 = 每条带 release_date / days_ago / is_fresh；前端显示「M/D 公布 · N 天前」。

落盘:
  output/daily_macro_<T>.json
  output/daily_macro_latest.json（前端 fetch 用）

用法:
  python fetch_daily_macro.py
  python fetch_daily_macro.py --no-us        # 跳过美国宏观
  python fetch_daily_macro.py --cal-only     # 只跑日历轨（跳新闻抽取，调试用）
"""
import os, re, sys, json, time, socket, datetime

socket.setdefaulttimeout(25)

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "output")
NOW = datetime.datetime.now()
DATE = NOW.strftime("%Y-%m-%d")
TODAY = NOW.date()

# ══════════════════════════════════════════════════════════════════
# 美国宏观 · 轨 A：经济日历（主源）
# ══════════════════════════════════════════════════════════════════
US_CAL_FAST_DAYS = 7          # 首轮窗口（天）
US_CAL_MAX_LOOKBACK = 30      # 关键指标未命中时的回看上界（天）——须 > 月频间隔
US_CAL_SLEEP = 0.25           # 逐日请求间隔（礼貌限速）
US_CAL_FRESH_DAYS = 10        # 前端「新鲜」阈值：公布日距今 ≤ 此值视为当期
# 日历事件名正则 → 展示标签（顺序 = 展示顺序）
# 🔴 注意：(?!.*核心) 负向断言必不可少 —— 否则「美国8月核心CPI年率未季调」
#    会同时被「CPI 同比」与「核心 CPI」两条规则命中，导致 CPI 同比显示成核心值
#    （2026-09-18 实测：CPI 同比曾误显 2.4，实为 3.4）。
US_CAL_INDICATORS = [
    ("CPI 同比",    r"美国(?!.*核心).*CPI年率未季调"),
    ("核心 CPI",    r"美国.*核心CPI年率"),
    ("CPI 月率",    r"美国(?!.*核心).*CPI月率季调后"),
    ("核心CPI月率",  r"美国.*核心CPI月率季调后"),
    ("非农",        r"美国.*非农就业人口变动季调后"),
    ("失业率",      r"美国.*失业率\(%\)"),
    ("ADP 就业",    r"美国.*ADP就业"),
    ("核心 PCE",    r"美国.*核心PCE"),
    ("初请失业金",   r"美国.*初请失业金"),
    ("GDP",        r"美国.*GDP"),
    ("零售销售",    r"美国.*零售销售月率"),
    ("ISM 制造业",   r"美国.*ISM制造业"),
    ("利率决议",    r"美国.*利率决定"),
]
# 回看触发判据：这些**月频**指标须**全部**在窗口内命中才停止回看。
# 🔴 原实现用「任一命中即停」→ CPI 命中后立即停止，导致 14 天前公布的非农被漏掉
#    （2026-09-18 实测）。故改为 all(...)，上限 US_CAL_MAX_LOOKBACK 天。
US_CAL_KEY_PATS = [
    r"美国(?!.*核心).*CPI年率未季调",
    r"美国.*非农就业人口变动季调后",
]

# ══════════════════════════════════════════════════════════════════
# 美国宏观 · 轨 B：新闻抽取（兜底）
# ══════════════════════════════════════════════════════════════════
US_NEWS_WINDOW_DAYS = 7       # 🔴 时效窗口（原实现缺此参数 = 头号 bug）
US_NEWS_MAX_PER_IND = 3       # 每指标最多保留条数
US_INDICATORS = {
    "核心PCE":    ["核心PCE", "核心PCE物价"],
    "整体PCE":    ["PCE物价", "PCE价格", "个人消费支出"],
    "CPI":       ["CPI", "消费者物价"],
    "非农":       ["非农", "新增就业"],
    "初请失业金":  ["初请失业金", "初请"],
    "耐用品订单":  ["耐用品订单"],
    "美国GDP":    ["美国GDP", "GDP初值", "GDP修正"],
    "美联储/利率": ["美联储", "利率决议", "降息", "加息", "点阵图", "鲍威尔", "沃什"],
    "美债收益率":  ["美债收益率", "10年期美债", "10Y"],
}


def _s(v):
    """归一化单元格：nan / None / 空 → ''。"""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat", "") else s


def _age(date_str):
    """距今天数；不可解析返回 None。"""
    try:
        d = datetime.date(*map(int, str(date_str)[:10].split("-")))
        return (TODAY - d).days
    except Exception:
        return None


def fetch_baidu_calendar(day, log):
    """拉取单日百度经济日历的美国行。"""
    import akshare as ak
    try:
        df = ak.news_economic_baidu(date=day.strftime("%Y%m%d"))
    except Exception as e:
        log.append(f"日历 {day} 失败: {type(e).__name__}")
        return []
    if df is None or df.empty:
        return []
    rows = []
    for _, r in df.iterrows():
        if _s(r.get("地区")) != "美国":
            continue
        imp = 0
        try:
            imp = int(float(r.get("重要性") or 0))
        except Exception:
            pass
        rows.append({
            "event": _s(r.get("事件")),
            "value": _s(r.get("公布")),
            "forecast": _s(r.get("预期")),
            "previous": _s(r.get("前值")),
            "importance": imp,
            "time": _s(r.get("时间")),
            "date": _s(r.get("日期"))[:10] or day.isoformat(),
        })
    return rows


def build_us_calendar(log):
    """轨 A：逐日拉日历 → 关键指标「最近一次公布」值。"""
    pool = []          # 全部美国行
    days_fetched = []
    # ① 首轮：最近 US_CAL_FAST_DAYS 天
    for i in range(US_CAL_FAST_DAYS):
        d = TODAY - datetime.timedelta(days=i)
        rows = fetch_baidu_calendar(d, log)
        pool.extend(rows)
        days_fetched.append(d.isoformat())
        time.sleep(US_CAL_SLEEP)
    # ② 关键月频指标未**全部**命中 → 回看（月频间隔约 30 天，故上限 30 天）
    def key_hit(rows):
        return all(any(re.search(p, r["event"]) for r in rows) for p in US_CAL_KEY_PATS)
    lookback_to = None
    if not key_hit(pool):
        for i in range(US_CAL_FAST_DAYS, US_CAL_MAX_LOOKBACK):
            d = TODAY - datetime.timedelta(days=i)
            rows = fetch_baidu_calendar(d, log)
            pool.extend(rows)
            days_fetched.append(d.isoformat())
            time.sleep(US_CAL_SLEEP)
            if key_hit(pool):
                lookback_to = d.isoformat()
                break

    # ③ 归集到标签：同一标签取「最近公布日」的行，按重要性降序，最多 2 条
    indicators = {}
    for label, pat in US_CAL_INDICATORS:
        cand = [r for r in pool if re.search(pat, r["event"])]
        if not cand:
            continue
        cand.sort(key=lambda r: (r["date"], r["importance"]), reverse=True)
        latest_day = cand[0]["date"]
        same = [r for r in cand if r["date"] == latest_day]
        same.sort(key=lambda r: r["importance"], reverse=True)
        # 🔴 只保留同日**最高重要性档**：否则「失业率」会同时带出 U6 失业率(%)
        #    （重要性 1）这类次要口径（2026-09-18 实测）。
        _top_imp = same[0]["importance"]
        same = [r for r in same if r["importance"] == _top_imp]
        out = []
        for r in same[:2]:
            age = _age(r["date"])
            out.append({
                "event": r["event"],
                "value": r["value"],
                "forecast": r["forecast"],
                "previous": r["previous"],
                "importance": r["importance"],
                "release_date": r["date"],
                "release_time": r["time"],
                "days_ago": age,
                "is_fresh": (age is not None and age <= US_CAL_FRESH_DAYS),
            })
        indicators[label] = out

    return {
        "source": "百度经济日历 news_economic_baidu",
        "window_days": US_CAL_FAST_DAYS,
        "lookback_days": US_CAL_MAX_LOOKBACK,
        "lookback_used_to": lookback_to,
        "days_fetched": len(days_fetched),
        "as_of": NOW.strftime("%Y-%m-%d %H:%M"),
        "indicators": indicators,
    }


# ══════════════════════════════════════════════════════════════════
# 美国宏观 · 轨 B：新闻抽取（兜底 · 已修时间窗）
# ══════════════════════════════════════════════════════════════════
def grab_news():
    """抓取新闻池（东财全球 + 财经早餐）。"""
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


def _evidence(text, kws):
    """🔴 证据质量门：句子须含数字，且须含指标关键词之一（避免无关错配）。"""
    out = []
    for sent in re.split(r"[。；\n]", text):
        if not re.search(r"\d", sent):
            continue
        if not any(kw in sent for kw in kws):
            continue
        out.append(sent.strip()[:90])
    return out


def extract_us(news, log=None):
    """按指标关键词过滤新闻 —— 🔴 2026-09-18 修复：时间窗 + 强制时间倒序 + 证据质量门。"""
    # ① 时效窗口过滤（原实现缺此步 → 抽到 36/77 天前的旧闻）
    pool = []
    for it in news:
        age = _age(str(it.get("time", ""))[:10])
        if age is None or age < 0 or age > US_NEWS_WINDOW_DAYS:
            continue
        it = dict(it)
        it["_age"] = age
        it["_date"] = str(it.get("time", ""))[:10]
        pool.append(it)
    # ② 强制按时间倒序（不依赖上游返回顺序）
    pool.sort(key=lambda x: x["_age"])

    # ③ 逐指标抽取（去掉原 `break`：一条新闻可同时归多个指标）
    hits = {}
    for ind, kws in US_INDICATORS.items():
        items = []
        for it in pool:
            text = it["title"] + " " + it["summary"]
            if not any(kw in text for kw in kws):
                continue
            evs = _evidence(text, kws)
            if not evs:
                continue      # 证据质量门不通过 → 丢弃
            items.append({
                "title": it["title"][:60],
                "evidence": evs[:3],
                "date": it["_date"],
                "days_ago": it["_age"],
                "is_fresh": it["_age"] <= US_NEWS_WINDOW_DAYS,
                "time": it["time"],
                "source": it["source"],
            })
            if len(items) >= US_NEWS_MAX_PER_IND:
                break
        if items:
            hits[ind] = items

    # ④ 窗口内无命中的指标 → 显式登记（前端显示「近 N 日无更新」而非拿旧闻充数）
    stale = [k for k in US_INDICATORS if k not in hits]
    if log is not None:
        log.append(f"新闻池 {len(news)} 条 → 窗口内({US_NEWS_WINDOW_DAYS}日) {len(pool)} 条；命中 {len(hits)} 指标")
    return hits, stale, len(pool)


# ══════════════════════════════════════════════════════════════════
# 中国宏观（akshare）
# ══════════════════════════════════════════════════════════════════
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

    log = []
    us = {
        "note": "主源=百度经济日历(带公布日/预期/前值)；兜底=新闻抽取(近 %d 日)" % US_NEWS_WINDOW_DAYS,
        "calendar": {},
        "indicators": {},
        "stale": [],
    }
    if "--no-us" not in sys.argv:
        # ── 轨 A：经济日历（主源）──
        print(f"· [轨A] 拉取百度经济日历（首轮 {US_CAL_FAST_DAYS} 天，必要时回看至 {US_CAL_MAX_LOOKBACK} 天）...")
        try:
            cal = build_us_calendar(log)
            us["calendar"] = cal
            n_cal = sum(len(v) for v in cal["indicators"].values())
            print(f"  ✅ 日历命中 {len(cal['indicators'])} 个指标 / {n_cal} 条 | 拉取 {cal['days_fetched']} 天"
                  + (f" | 回看至 {cal['lookback_used_to']}" if cal["lookback_used_to"] else ""))
            for k, v in cal["indicators"].items():
                r = v[0]
                print(f"     {k:10s} {r['value']:>8s} (预期 {r['forecast'] or '—':>6s} / 前值 {r['previous'] or '—':>6s})"
                      f" · {r['release_date']} · {r['days_ago']} 天前")
        except Exception as e:
            print(f"  ❌ 轨A 失败（将降级为纯新闻抽取）: {type(e).__name__}: {str(e)[:90]}")
            log.append(f"轨A异常: {type(e).__name__}")
            us["calendar"] = {"error": f"{type(e).__name__}: {str(e)[:120]}", "indicators": {}}

        # ── 轨 B：新闻抽取（兜底 + 补充定量外信息）──
        if "--cal-only" not in sys.argv:
            print(f"· [轨B] 抓取新闻池供美国宏观兜底抽取 ...")
            news = grab_news()
            hits, stale, pool_n = extract_us(news, log)
            us["indicators"] = hits
            us["stale"] = stale
            print(f"  新闻池 {len(news)} 条 → 近 {US_NEWS_WINDOW_DAYS} 日 {pool_n} 条；命中 {len(hits)} 指标")
            for k, v in hits.items():
                print(f"     {k:12s} {len(v)} 条 | 龄期 {[x['days_ago'] for x in v]} 天")
            if stale:
                print(f"  ⚠️ 近 {US_NEWS_WINDOW_DAYS} 日无命中（前端将标注「无更新」）: {', '.join(stale[:6])}"
                      + (" …" if len(stale) > 6 else ""))

    us["log"] = log
    payload = {
        "date": DATE,
        "generated_at": NOW.strftime("%Y-%m-%d %H:%M"),
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
