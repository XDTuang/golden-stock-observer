#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 每日新闻池自动抓取（每日复盘 6 段「新闻整合」的自动数据源）
=========================================================================
抓取多源实时新闻，按关键词打标（宏观/科技/政策/产业/持仓/美股映射），
标题归一化去重后落：
  output/daily_news_<T>.json       当日全量（T = 北京采集日）
  output/daily_news_latest.json    当日副本（当日口径）
  output/daily_news_window.json    ★ 近 N 日（默认 14）**滚动池**（2026-09-16 新增）

🔴 滚动池（2026-09-16 用户拍板 · 方案 A）：
  · **累积不替换** —— 原实现只写 latest，跨周末时周六周日的新闻在周一盘前被**整池覆盖**；
    现由 `rebuild_window_pool()` 汇总近 keep_days 个日历日的归档件 → 跨周末/长假信息不再丢。
  · 每条新闻打 `collected_date`（**北京时间归属日**），供 build_window.py 按 span 统计与前端分组。
  · 池只保留近 keep_days 天；磁盘上的历史归档件**不删**（可回溯）。

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
  python fetch_daily_news.py                     # 抓全部源（默认 14 天滚动池）
  python fetch_daily_news.py --sources em,breakfast,sina
  python fetch_daily_news.py --keep-days 21      # 滚动池保留天数
  python fetch_daily_news.py --pool-only         # 不抓取，仅重建滚动池（补历史）
"""
import os, re, sys, json, hashlib, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
OUT_DIR = os.path.join(BASE, "output")
DATE = datetime.datetime.now().strftime("%Y-%m-%d")
KEEP_DAYS = 14

# 🔴 内容时效窗（2026-09-23 治本）：`stock_info_cjzc_em` 返回 **400 条固定长度历史**
#   （实测跨度 2025-02-05 → 当日，时间倒序），抽取侧原先**无时间窗** → 371/701 条当日池
#   是 40 天以上的旧闻（最老 595 天），容器 `collected_date` 却是当天 ——
#   与 `fetch_daily_macro.py` 2026-09-18 修的是同族缺陷（「有值但永远旧」）。
#   处置：① 抓取侧按发布时间窗过滤 ② 池构建侧再兜一道「条目龄期」闸（可回溯清理历史归档）。
FRESH_DAYS = 7          # 单条内容允许的最大龄期（天）；留过周末余量
POOL_GRACE_DAYS = 7     # 池构建侧额外宽限：条目龄期 > keep_days + POOL_GRACE_DAYS 才丢弃


def _content_age_days(ts, ref_date):
    """条目内容时间距参考日的天数；不可解析返回 None（调用方须保留而非丢弃）。"""
    try:
        d = datetime.datetime.strptime(str(ts)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    return (ref_date - d).days

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
    today = datetime.date.today()
    dropped = 0
    for _, r in df.iterrows():
        title = str(r.get("标题", "") or "")
        if not title:
            continue
        ts = str(r.get("发布时间", "") or "")
        # 🔴 时间窗过滤（2026-09-23）：源固定返回 400 条历史，不过滤则永远掺入 1 年多前的旧闻
        age = _content_age_days(ts, today)
        if age is not None and age > FRESH_DAYS:
            dropped += 1
            continue
        out.append({
            "title": title,
            "summary": str(r.get("摘要", "") or ""),
            "time": ts,
            "source": "财经早餐",
            "url": str(r.get("链接", "") or ""),
            "_key": norm_title(title),
        })
    if dropped:
        print(f"  ℹ️ 财经早餐：按内容时效窗（≤{FRESH_DAYS} 天）滤除陈旧条目 {dropped} 条")
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


# ── 滚动池重建（2026-09-16 新增 · 方案 A）────────────────────
def _pool_window():
    """嵌入当前信息窗口契约（供前端/守卫读）；缺失时返回 None，不阻断抓取。"""
    p = os.path.join(OUT_DIR, "window_latest.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            w = json.load(f)
        return w if isinstance(w, dict) and w.get("for_date") else None
    except Exception:
        return None


def _resolve_span():
    """尽力求出 (data_date, for_date)；market_calendar 不可用时返回 (None, None)。"""
    try:
        from market_calendar import is_trading_day, last_trading_day, next_trading_day
        today = datetime.date.today()
        for_date = today if is_trading_day(today) else next_trading_day(today)
        data_date = last_trading_day(for_date - datetime.timedelta(days=1))
        return data_date.isoformat(), for_date.isoformat()
    except Exception as e:
        print(f"  ⚠️ market_calendar 不可用，窗口日期留空：{e}")
        return None, None


def rebuild_window_pool(keep_days=None):
    """汇总近 keep_days 个日历日的每日归档 → output/daily_news_window.json。

    · **累积不替换**：跨周末/长假时周六周日新闻不再被周一盘前整池覆盖
    · 每条打 `collected_date`（北京归属日）→ 供 build_window.py 按 span 统计、前端按日分组
    · 磁盘历史归档件不删（仅池的纳入范围滚动）
    """
    keep_days = keep_days or KEEP_DAYS
    import glob as _glob
    cands = []
    for p in _glob.glob(os.path.join(OUT_DIR, "daily_news_2*.json")):
        m = re.search(r"daily_news_(\d{4}-\d{2}-\d{2})\.json$", os.path.basename(p))
        if m:
            cands.append((m.group(1), p))
    if not cands:
        print("  ⚠️ 未找到任何 daily_news_<date>.json 归档，跳过滚动池构建")
        return None
    cands.sort(key=lambda x: x[0], reverse=True)
    kept = sorted(cands[:keep_days])          # 升序
    dropped = [d for d, _ in cands[keep_days:]]

    by_day, day_stats, merged = {}, {}, []
    stale_days = {}
    bad = []
    for ds, p in kept:
        try:
            with open(p, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            bad.append(f"{ds}({e})")
            continue
        arr = doc.get("news") or []
        # 🔴 池级内容时效闸（2026-09-23 治本）：归档件里的**陈旧条目**在纳入池时滤除，
        #   使其不再参与窗口统计与前端渲染；磁盘归档件本身不删（可回溯）。
        #   闸门 = 条目龄期 > keep_days + POOL_GRACE_DAYS（`time` 不可解析者一律保留）。
        try:
            _ref = datetime.datetime.strptime(ds, "%Y-%m-%d").date()
        except Exception:
            _ref = None
        if _ref is not None:
            _limit = keep_days + POOL_GRACE_DAYS
            _kept, _drop = [], 0
            for it in arr:
                _a = _content_age_days(it.get("time"), _ref)
                if _a is not None and _a > _limit:
                    _drop += 1
                    continue
                _kept.append(it)
            if _drop:
                stale_days[ds] = _drop
            arr = _kept
        for it in arr:
            it["collected_date"] = ds
        # 累积顺序：新的一天在前 → 去重保留「最新一次出现」的副本
        by_day[ds] = arr
        day_stats[ds] = {"total": len(arr), "tags": doc.get("tag_stats") or {}}
        merged = arr + merged
    merged = dedup(merged)
    merged.sort(key=lambda x: (str(x.get("collected_date") or ""), str(x.get("time") or "")), reverse=True)

    data_date, for_date = _resolve_span()
    win = _pool_window()
    if win and win.get("for_date"):
        data_date = data_date or win.get("data_date")
        for_date = win.get("for_date")
    covered_days = sorted(by_day.keys(), reverse=True)
    pool = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_date": DATE,
        "keep_days": keep_days,
        "data_date": data_date,
        "for_date": for_date,
        "covered_days": covered_days,
        "dropped_days": sorted(dropped, reverse=True)[:10],
        "pool_note": (f"近 {keep_days} 个日历日滚动池（跨周末/长假信息累积，不整池覆盖）；"
                      f"磁盘历史归档件保留不删"),
        "day_stats": day_stats,
        "by_day": by_day,
        "total": len(merged),
        "news": merged,
        "window": win,
    }
    p = os.path.join(OUT_DIR, "daily_news_window.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    print(f"💾 {p}")
    print(f"   滚动池 {keep_days} 天 · 覆盖 {len(covered_days)} 日（{covered_days[-1] if covered_days else '—'}"
          f" → {covered_days[0] if covered_days else '—'}）· 去重后 {len(merged)} 条"
          + (f" · 已滚动出 {len(dropped)} 日" if dropped else ""))
    for ds in covered_days:
        print(f"     {ds}  {day_stats[ds]['total']:>4} 条"
              + (f"（滤除陈旧 {stale_days[ds]} 条）" if ds in stale_days else ""))
    if bad:
        print(f"   ⚠️ 读取失败跳过：{', '.join(bad)}")
    return pool

def main():
    argv = sys.argv
    want = argv[argv.index("--sources") + 1].split(",") if "--sources" in argv else list(GRABBERS)
    keep_days = KEEP_DAYS
    if "--keep-days" in argv:
        try:
            keep_days = int(argv[argv.index("--keep-days") + 1])
        except Exception:
            pass

    if "--pool-only" in argv:
        print(f"═══ 新闻滚动池重建（不抓取）{DATE} ═══")
        rebuild_window_pool(keep_days)
        return

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
    # 打标 + 归属日（北京时间采集日）
    for it in all_items:
        it["tags"] = tag_text(it["title"] + " " + it.get("summary", ""))
        it["collected_date"] = DATE
    tag_stats = {t: sum(1 for x in all_items if t in x["tags"]) for t in ALL_TAGS}

    payload = {
        "date": DATE,                    # 数据日 = 北京采集日
        "collected_date": DATE,          # 每条新闻的归属日（与 news[].collected_date 同源）
        "covered_days": [DATE],
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

    # ★ 重建 N 日滚动池（累积不替换 · 跨周末信息不丢）
    rebuild_window_pool(keep_days)

if __name__ == "__main__":
    main()
