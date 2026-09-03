#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 每日复盘引擎（定时任务：本地 19:30 / 云端 08:15）
=========================================================
汇总当日投喂（feed_index.json）+ 拉取当日盘面（signals.json /
golden_diamond.json / market.json 可选）→ 交叉分析 → 输出后市预测。

产出:
  output/feed_review_<T>.json      — 完整复盘（含当日投喂、盘面摘要、交叉分析、预测）
  output/feed_review_latest.json   — 前端「每日复盘」页动态加载的最新版

用法:
  python daily_feed_review.py                 # 跑当日（date=最新交易日）
  python daily_feed_review.py --date 2026-08-26
  python daily_feed_review.py --no-feed       # 无投喂时仍输出盘面复盘
"""
import os, sys, json, re, argparse, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(BASE, "feed", "archive", "feed_index.json")
SIGNALS = os.path.join(BASE, "signals.json")
GD = os.path.join(BASE, "output", "golden_diamond.json")
MARKET = os.path.join(BASE, "deploy", "data", "market.json")
OUT_DIR = os.path.join(BASE, "output")

# 情绪词典（简单可解释规则，不替代 AI 分析）
POS = ["上修", "涨价", "需求", "催化", "放量", "突破", "超预期", "景气", "增持", "中标", "订单", "回暖", "新高", "共振"]
NEG = ["减持", "风险", "下跌", "破位", "利空", "暴雷", "亏损", "处罚", "下调", "退市", "警示", "调查"]


def load_json(p, default=None):
    if not os.path.exists(p):
        return default
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def feeds_of_day(date):
    idx = load_json(INDEX, {"entries": []})
    return [e for e in idx["entries"] if e.get("date") == date]


def read_feed_content(e):
    p = os.path.join(BASE, e.get("file", ""))
    if os.path.exists(p):
        try:
            return open(p, encoding="utf-8", errors="ignore").read(1500)
        except Exception:
            return ""
    return ""


def sentiment(text):
    pos = sum(1 for w in POS if w in text)
    neg = sum(1 for w in NEG if w in text)
    return {"pos": pos, "neg": neg, "score": pos - neg}


def market_summary():
    sig = load_json(SIGNALS)
    gd = load_json(GD)
    market = load_json(MARKET)
    out = {}
    if sig:
        st = sig.get("stats", {})
        out["signals"] = {
            "data_date": sig.get("data_date"),
            "total": st.get("total_stocks", 0),
            "ema_strong": (st.get("ema_7_7", 0) or 0) + (st.get("ema_5_6", 0) or 0),
            "ema_perfect": st.get("ema_7_7", 0),
            "grades": {k: st.get(k, 0) for k in ["四喜临门", "三线共振", "双线", "单信号"]},
        }
        th = sig.get("top10_history", {})
        dates = sorted(th.keys(), reverse=True)
        if dates:
            out["top10"] = th[dates[0]].get("top10", [])[:5]
    if gd:
        ov = gd.get("overview", {})
        out["golden"] = {"data_date": gd.get("data_date"), "total": ov.get("total", 0),
                         "up": ov.get("up", 0), "buy": ov.get("buy", 0), "hz": ov.get("hz", 0)}
    if market:
        out["market_date"] = market.get("date")
    return out


def cross_analyze(feeds, mkt):
    """投喂关键词 × 盘面信号标的 交叉验证"""
    # 构建信号标的池：TOP10 + 金钻命中 + 观测池
    pool = []
    for r in mkt.get("top10", []):
        pool.append((r.get("name", ""), r.get("code", ""), "TOP" + str(mkt["top10"].index(r) + 1)))
    gd = load_json(GD)
    if gd:
        for s in gd.get("stocks", []):
            pool.append((s.get("name", ""), s.get("code", ""), s.get("primary", "金钻")))
    pool = list({(n, c, t): None for n, c, t in pool}.keys())

    rows = []
    for e in feeds:
        content = read_feed_content(e)
        # 用信号池股票名称/6位代码全集 匹配 投喂标题+全文（避免关键词切碎丢名）
        haystack = (e.get("title", "") + " " + content).lower()
        hits = []
        for n, c, t in pool:
            raw = c.lower().replace("sh", "").replace("sz", "")
            if n.lower() in haystack or raw in haystack:
                hits.append(f"{n}({c}·{t})")
        se = sentiment(content)
        rows.append({
            "feed": f"{e['category']}·{e['source']}·{e['title']}",
            "content": content.strip()[:120],
            "keywords": e.get("keywords", [])[:6],
            "related_stocks": hits[:5],
            "sentiment": se,
            "verdict": "共振" if hits and se["score"] >= 0 else ("背离" if hits and se["score"] < 0 else "无匹配"),
        })
    return rows


def predict(date, mkt, crosses):
    """规则预测（机械可解释；深度预测由 AI 挂点补充）"""
    reasons, bias_score = [], 0

    s = mkt.get("signals", {})
    if s:
        ratio = (s.get("ema_strong", 0) / s.get("total", 1)) if s.get("total") else 0
        if ratio >= 0.2:
            bias_score += 1; reasons.append(f"EMA 强趋势占比 {ratio:.0%}，结构偏强")
        elif ratio <= 0.1:
            bias_score -= 1; reasons.append(f"EMA 强趋势占比仅 {ratio:.0%}，结构偏弱")

    g = mkt.get("golden", {})
    if g.get("total"):
        if g.get("up", 0) >= 3:
            bias_score += 1; reasons.append(f"金钻起涨 {g['up']} 只，启动信号活跃")
        if g.get("total", 0) >= 15:
            reasons.append(f"金钻命中 {g['total']} 只，信号面正常")

    feed_score = sum(c["sentiment"]["score"] for c in crosses)
    if feed_score > 0:
        bias_score += 1; reasons.append(f"投喂语料偏正面（净分 {feed_score}）")
    elif feed_score < 0:
        bias_score -= 1; reasons.append(f"投喂语料偏负面（净分 {feed_score}）")

    bias = "偏多" if bias_score >= 2 else ("偏空" if bias_score <= -2 else "中性")

    t1 = []
    if g.get("up"):
        t1.append(f"跟踪金钻起涨 {g['up']} 只回踩确认")
    for c in crosses[:3]:
        if c["verdict"] == "共振":
            t1.append(f"{c['feed']} 与信号共振，重点跟踪 {c['related_stocks'][:2]}")
    if not t1:
        t1.append("无新增共振，维持既有持仓观察")

    risks = []
    if g.get("hz", 0) > g.get("total", 1) * 0.4:
        risks.append({"prob": "中", "impact": "高", "desc": "金钻命中多为红区黄柱（蓄势非启动），大盘转弱易集体哑火"})
    if any(c["sentiment"]["neg"] > 0 for c in crosses):
        risks.append({"prob": "中", "impact": "中", "desc": "投喂语料含负面信息，注意相关个股避险"})

    return {
        "bias": bias, "bias_score": bias_score, "reasons": reasons,
        "t1_focus": t1, "risks": risks,
        "pending_ai": True,  # AI 深度预测挂点：本机 agent / 专家对话补全
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--no-feed", action="store_true", help="无投喂时仍生成盘面复盘")
    args = ap.parse_args()

    mkt = market_summary()
    date = args.date or mkt.get("signals", {}).get("data_date") or mkt.get("market_date") or \
           datetime.date.today().strftime("%Y-%m-%d")
    feeds = [] if args.no_feed else feeds_of_day(date)
    crosses = cross_analyze(feeds, mkt)
    pred = predict(date, mkt, crosses)

    result = {
        "data_date": date,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "local" if os.environ.get("GITHUB_ACTIONS") != "true" else "cloud",
        "feeds": feeds,
        "feed_count": len(feeds),
        "market": mkt,
        "cross_analysis": crosses,
        "prediction": pred,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out_full = os.path.join(OUT_DIR, f"feed_review_{date}.json")
    out_latest = os.path.join(OUT_DIR, "feed_review_latest.json")
    # ── 字段级合并（2026-08-28 审计修复）────────────────────────────
    # 背景：此处原为整文件 json.dump，云端 cron 以 --no-feed 重跑时会全量覆写，
    #       抹掉本机 agent 产出的 feeds[] / ai_synthesis / synthesis_sources。
    # 规则：① 仅同日（data_date 一致）才合并，跨日视为全新一天不继承；
    #       ② ai_synthesis / synthesis_sources 为本机独占，存在即保护；
    #       ③ feeds 为空（--no-feed 模式）时保留本机已有投喂，不置空。
    LOCAL_ONLY = ("ai_synthesis", "synthesis_sources")
    for p in (out_full, out_latest):
        existing = {}
        try:
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    existing = json.load(f) or {}
        except Exception:
            existing = {}
        protected = []
        if existing.get("data_date") == date:
            payload = dict(existing)
            payload.update(result)
            for k in LOCAL_ONLY:
                if existing.get(k):
                    payload[k] = existing[k]
                    protected.append(k)
            if not result.get("feeds") and existing.get("feeds"):
                payload["feeds"] = existing["feeds"]
                payload["feed_count"] = len(existing["feeds"])
                protected.append("feeds[]")
        else:
            payload = dict(result)
            # 2026-09-03 防呆补充：盘前推演产物 data_date=T-1 / guide_date=T，
            # 次日晚间以 T 重跑属跨日，但 guide_date 匹配即为本日推演结论，仍须保留
            if existing.get("guide_date") == date:
                for k in LOCAL_ONLY:
                    if existing.get(k):
                        payload[k] = existing[k]
                        protected.append(f"{k}(跨日·guide_date匹配)")
        if protected:
            print(f"   🔒 {os.path.basename(p)} 保留本机产物: {', '.join(protected)}")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 复盘完成 {date} | 投喂 {len(feeds)} 条 | 预测: {pred['bias']} (score {pred['bias_score']})")
    print(f"   {out_full}")
    print(f"   {out_latest}")
    for r in pred["reasons"]:
        print(f"   · {r}")


if __name__ == "__main__":
    main()
