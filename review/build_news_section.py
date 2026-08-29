#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘 6 段「新闻整合」自动构建（公开新闻源必选 + agent 投喂可选）
=====================================================================
输入：output/daily_news_latest.json（由 fetch_daily_news.py 抓取的多源公开新闻池）
输出：output/daily_review_news.json（前端 6 段 JS 直接消费）

设计原则（2026-08-29 用户明确要求）：
  - **公开数据源是必选**：东财全球/财经早餐/新浪/同花顺/富途/央视联播，全自动读取公开链接；
  - **投喂可有可无**：投喂素材作为「投喂精选」附在末尾，没有投喂时该区块自动省略，
    不影响主体新闻流的自动更新；
  - 失败不阻断：新闻池缺失时输出空结构，前端降级显示提示，不白屏；
  - 来源可溯：每条带 source + url + time。

用法:
  python review/build_news_section.py            # 构建 6 段数据
  python review/build_news_section.py --top 15   # 每个标签取 15 条（默认 12）
"""
import os, re, sys, json, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "output")
NEWS_SRC = os.path.join(OUT_DIR, "daily_news_latest.json")
OUT_PATH = os.path.join(OUT_DIR, "daily_review_news.json")
# 投喂精选（可选）：若 agent 生成了该文件，则附在 6 段末尾
FEED_PICKS = os.path.join(OUT_DIR, "news_feed_picks.json")

# 标签展示顺序（与 fetch_daily_news.py TAG_RULES 对应）
TAGS = ["宏观", "政策", "科技", "产业", "美股映射", "持仓"]
# 标签配色（前端类名）
TAG_CLS = {
    "宏观": "t-macro", "政策": "t-policy", "科技": "t-tech",
    "产业": "t-ind", "美股映射": "t-us", "持仓": "t-hold",
}


def parse_args():
    top = 12
    if "--top" in sys.argv:
        try:
            top = int(sys.argv[sys.argv.index("--top") + 1])
        except Exception:
            pass
    return top


def load_json(p):
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ 读取失败 {p}: {e}")
        return None


def norm_time(t):
    """统一时间格式为 HH:MM（兼容 '2026-08-29 15:41' / '2026-08-29 15:41:00' 等）。"""
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


def build(news_pool, top):
    items = news_pool.get("news", []) or []
    groups = {}
    for tag in TAGS:
        hit = [n for n in items if tag in (n.get("tags") or [])]
        # 按时间倒序（新闻池内已是新的在前，此处再稳一次）
        hit.sort(key=lambda x: str(x.get("time") or ""), reverse=True)
        groups[tag] = {
            "label": tag,
            "cls": TAG_CLS.get(tag, ""),
            "count": len(hit),
            "items": [
                {
                    "title": n.get("title", ""),
                    "summary": clean_summary(n.get("summary", "")),
                    "time": norm_time(n.get("time", "")),
                    "source": n.get("source", ""),
                    "url": n.get("url", ""),
                }
                for n in hit[:top]
            ],
        }
    return groups


def main():
    top = parse_args()
    print(f"═══ 6 段「新闻整合」构建（公开源必选 + 投喂可选）═══")

    pool = load_json(NEWS_SRC)
    if not pool:
        print(f"  ❌ 新闻池缺失：{NEWS_SRC}")
        print("     请先运行 fetch_daily_news.py 抓取公开新闻源")
        # 仍输出空结构，前端降级显示，不阻断
        pool = {"date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "generated_at": "", "sources": {}, "total": 0,
                "tag_stats": {}, "news": []}

    groups = build(pool, top)
    picks = load_json(FEED_PICKS)

    payload = {
        "date": pool.get("date", ""),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pool_generated_at": pool.get("generated_at", ""),
        "sources": pool.get("sources", {}),
        "total": pool.get("total", 0),
        "tag_stats": pool.get("tag_stats", {}),
        "top_per_tag": top,
        "groups": groups,
        # 投喂精选（可选）：没有投喂时为 null，前端自动省略该区块
        "feed_picks": picks,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  📰 新闻池 {pool.get('date','—')} · 共 {pool.get('total',0)} 条 · 来源 {pool.get('sources',{})}")
    for tag in TAGS:
        g = groups[tag]
        print(f"     {tag:<6} 命中 {g['count']:>4} 条 · 展示 {len(g['items'])} 条")
    print(f"  📥 投喂精选: {'有（' + str(len(picks.get('picks', [])) if isinstance(picks, dict) else len(picks)) + ' 条）' if picks else '无（自动省略该区块）'}")
    print(f"💾 {OUT_PATH}")


if __name__ == "__main__":
    main()
