#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘 6 段「新闻整合」自动构建（窗口切片版 · 2026-09-16 方案 A 改造）
=======================================================================
输入：output/daily_news_window.json（N 日滚动池，首选）
      output/daily_news_latest.json（回退：滚动池缺失时用当日副本）
输出：output/daily_review_news.json（前端「6·新闻整合」直接消费）

🔴 本次改造（用户 2026-09-16 拍板）：
  · **按信息窗口切片** —— 只取 `collected_date ∈ window.span` 的条目（跨周末时自动含周六周日）；
    原先取「全池 top-12」，池被覆盖时窗口内条目会凭空消失。
  · **按日期分组** —— `by_day[]` 给出窗口内每一天的条目，前端每天**收敛展示**（show_n 起步）
    + 「更多」按钮递增展开；不再一次铺开全量。
  · **窗口契约随产物落盘** —— `window` 字段，供守卫与页面渲染「承接/指引/增量」信息条。

设计原则（2026-08-29 用户明确要求，保留）：
  - **公开数据源是必选**：全自动读取公开链接；
  - **投喂可有可无**：投喂素材附在末尾，无投喂时该区块自动省略；
  - 失败不阻断：池缺失时输出空结构，前端降级显示，不白屏；
  - 来源可溯：每条带 source + url + time + tags。

用法:
  python review/build_news_section.py             # 按 window.span 切片
  python review/build_news_section.py --top 15    # 每标签展示上限（默认 12）
  python review/build_news_section.py --show-n 8  # 每组默认收敛展示条数（默认 6）
  python review/build_news_section.py --window-from 2026-09-19 --window-to 2026-09-21   # 覆盖 span
"""
import os, re, sys, json, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "output")
POOL = os.path.join(OUT_DIR, "daily_news_window.json")   # 首选：N 日滚动池
NEWS_SRC = os.path.join(OUT_DIR, "daily_news_latest.json")  # 回退：当日副本
OUT_PATH = os.path.join(OUT_DIR, "daily_review_news.json")
WINDOW = os.path.join(OUT_DIR, "window_latest.json")
# 投喂精选（可选）：若 agent 生成了该文件，则附在 6 段末尾
FEED_PICKS = os.path.join(OUT_DIR, "news_feed_picks.json")

# 标签展示顺序（与 fetch_daily_news.py TAG_RULES 对应）
TAGS = ["宏观", "政策", "科技", "产业", "美股映射", "持仓"]
TAG_CLS = {
    "宏观": "t-macro", "政策": "t-policy", "科技": "t-tech",
    "产业": "t-ind", "美股映射": "t-us", "持仓": "t-hold",
}
WEEKDAY_CN = "一二三四五六日"


def parse_args():
    def _int(flag, dflt):
        if flag in sys.argv:
            try:
                return int(sys.argv[sys.argv.index(flag) + 1])
            except Exception:
                return dflt
        return dflt

    def _str(flag, dflt=""):
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else dflt

    return _int("--top", 12), _int("--show-n", 6), _str("--window-from"), _str("--window-to")


def load_json(p, default=None):
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ 读取失败 {p}: {e}")
        return default


def resolve_window(wf="", wt=""):
    """求当前信息窗口：优先读 window_latest.json；缺则按交易日历自行推导（失败返回 None）。"""
    w = load_json(WINDOW)
    if not w:
        try:
            sys.path.insert(0, BASE)
            from market_calendar import is_trading_day, last_trading_day, next_trading_day
            today = datetime.date.today()
            for_date = today if is_trading_day(today) else next_trading_day(today)
            data_date = last_trading_day(for_date - datetime.timedelta(days=1))
            span, cur = [], data_date + datetime.timedelta(days=1)
            while cur <= for_date:
                span.append(cur.isoformat())
                cur += datetime.timedelta(days=1)
            w = {"session": "preopen", "data_date": data_date.isoformat(),
                 "for_date": for_date.isoformat(), "span": span,
                 "display_days": [data_date.isoformat()] + span,
                 "source": "derived(market_calendar)"}
        except Exception as e:
            print(f"  ⚠️ 窗口推导失败（{e}）→ 回退为「不过滤」")
            return None
    if wf or wt:
        span = list(w.get("span") or [])
        if wf:
            span = [d for d in span if d >= wf] or [wf]
        if wt:
            span = [d for d in span if d <= wt] or [wt]
        w = dict(w, span=sorted(span), overridden=True)
    return w


def norm_time(t):
    """统一时间格式为 MM/DD HH:MM（兼容 '2026-08-29 15:41' 等）。"""
    if not t:
        return ""
    s = str(t).strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})[ T]?(\d{2}:\d{2})?", s)
    if not m:
        return s[:16]
    date, hm = m.group(1), m.group(2) or ""
    return f"{date[5:].replace('-', '/')} {hm}".strip()


def clean_summary(s, limit=90):
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def day_of(n):
    """条目归属日：优先 collected_date，回退 time 前 10 字符。"""
    v = str(n.get("collected_date") or "")[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v
    m = re.search(r"(\d{4}-\d{2}-\d{2})", str(n.get("time") or ""))
    return m.group(1) if m else ""


def to_item(n):
    return {
        "title": n.get("title", ""),
        "summary": clean_summary(n.get("summary", "")),
        "time": norm_time(n.get("time", "")),
        "source": n.get("source", ""),
        "url": n.get("url", ""),
        "tags": n.get("tags") or [],
        "collected_date": day_of(n),
    }


def build_by_day(items, span, show_n):
    """按窗口内每一天分组（倒序），每天收敛展示 show_n 条（前端「更多」按钮递增）。"""
    out = []
    for ds in sorted(set(span), reverse=True):
        arr = [n for n in items if day_of(n) == ds]
        if not arr:
            continue
        arr.sort(key=lambda x: str(x.get("time") or ""), reverse=True)
        d = datetime.date.fromisoformat(ds)
        tag_cnt = {t: sum(1 for x in arr if t in (x.get("tags") or [])) for t in TAGS}
        out.append({
            "date": ds,
            "weekday": "周" + WEEKDAY_CN[d.weekday()],
            "is_trading_day": d.weekday() < 5,
            "count": len(arr),
            "show_n": show_n,
            "tag_stats": tag_cnt,
            "items": [to_item(x) for x in arr],
        })
    return out


def build_by_tag(items, top):
    """按标签分组（窗口切片后），保留原 6 段版式。"""
    groups = {}
    for tag in TAGS:
        hit = [n for n in items if tag in (n.get("tags") or [])]
        hit.sort(key=lambda x: str(x.get("time") or ""), reverse=True)
        groups[tag] = {
            "label": tag,
            "cls": TAG_CLS.get(tag, ""),
            "count": len(hit),
            "items": [to_item(n) for n in hit[:top]],
        }
    return groups


def main():
    top, show_n, wf, wt = parse_args()
    print("═══ 6 段「新闻整合」构建（窗口切片 + 按日收敛）═══")

    win = resolve_window(wf, wt)
    span = (win or {}).get("span") or []
    # 展示/累积口径 = display_days（[基准日] ∪ span）：用户口径「次日推演 = 前一收盘日的
    # **全部**信息 + 当天盘前增量」→ 基准日的新闻池不能被切掉，否则"前一收盘日信息"缺失。
    days = (win or {}).get("display_days") or span
    if win:
        print(f"  🪟 窗口：承接 {(win.get('data_date') or '—')} → 指引 {(win.get('for_date') or '—')} "
              f"｜ span {span[0][5:] if span else '—'}"
              + (f"–{span[-1][5:]}" if len(span) > 1 else "")
              + f"（{len(span)} 天）｜ 展示窗口 {len(days)} 天")

    pool = load_json(POOL)
    used = "daily_news_window.json（N 日滚动池）"
    if not pool:
        pool = load_json(NEWS_SRC)
        used = "daily_news_latest.json（回退·当日副本）"
    if not pool:
        print(f"  ❌ 新闻池缺失：{POOL} / {NEWS_SRC}")
        print("     请先运行 fetch_daily_news.py 抓取公开新闻源")
        pool = {"date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "generated_at": "", "sources": {}, "total": 0, "tag_stats": {}, "news": []}
        used = "（缺失·降级空结构）"

    all_items = pool.get("news", []) or []
    items = [n for n in all_items if day_of(n) in days] if days else list(all_items)
    print(f"  📰 池：{used} · 共 {len(all_items)} 条 → 展示窗口内 {len(items)} 条")

    by_day = build_by_day(items, days or sorted({day_of(n) for n in items if day_of(n)}), show_n)
    groups = build_by_tag(items, top)
    picks = load_json(FEED_PICKS)

    payload = {
        "date": pool.get("date", ""),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pool_generated_at": pool.get("generated_at", ""),
        "pool_source": used,
        "sources": pool.get("sources", {}),
        "pool_total": len(all_items),
        "total": len(items),
        "window": win,
        "span": span,
        "display_days": days,
        "window_is_cross": bool((win or {}).get("span_is_weekend_cross")),
        "show_n": show_n,
        "top_per_tag": top,
        "by_day": by_day,
        "groups": groups,
        "tag_stats": pool.get("tag_stats", {}),
        # 投喂精选（可选）：没有投喂时为 null，前端自动省略该区块
        "feed_picks": picks,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  📅 按日分组（默认每组展示 {show_n} 条 · 前端「更多」递增）：")
    for g in by_day:
        print(f"     {g['date']} {g['weekday']} {'交易日' if g['is_trading_day'] else '非交易'} "
              f"· {g['count']:>4} 条")
    if not by_day:
        print("     （窗口内无条目 → 页面须红字提示，勿静默）")
    print(f"  🏷 按标签（窗口内 · 每标签上限 {top} 条）：")
    for tag in TAGS:
        g = groups[tag]
        print(f"     {tag:<6} 命中 {g['count']:>4} 条 · 展示 {len(g['items'])} 条")
    print(f"  📥 投喂精选: {'有' if picks else '无（自动省略该区块）'}")
    print(f"💾 {OUT_PATH}")


if __name__ == "__main__":
    main()
