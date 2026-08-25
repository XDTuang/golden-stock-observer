#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘前综合判断 → 收盘自动验证（与 backtest_daily_review.py 同源的"预判-验证"体系）

输入:
  盘前 JSON:  data/daily_review_history/<T>/preopen_<T>.json   （盘前判断结构化契约）
  实际行情:   data/daily_review/market.json 的 quotes（A股指数+持仓股 open/close/prev）

输出:
  1. 终端对照报告：路径判定 / 证伪线 / Kando 判据 / 个股低开区间+关键位 / 环境因子
  2. 台账: data/daily_review_history/_preopen_report.json（累积，供周/月命中率统计）

用法:
  python3 verify_preopen.py --date 2026-08-25     # 指定推演日
  python3 verify_preopen.py                        # 全部已归档盘前
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
HIST = BASE / "data" / "daily_review_history"
MARKET = BASE / "data" / "daily_review" / "market.json"

# 持仓 code → market.json quotes key
CODE2KEY = {
    "sh603083": "h_jq", "sh603399": "h_ys", "sz000922": None,
    "sh600378": "h_hh", "sh600105": "h_yd", "sz002082": "h_wb",
    "sh688825": "h_cx", "sz000988": "h_hg",
}
IDX_KEY = {"sh000001": "a_sh", "sz399001": "a_sz", "sz399006": "a_cyb", "sh000688": "a_kcb", "bj899050": "a_bj"}


def load_quotes():
    if not MARKET.exists():
        return {}
    return json.loads(MARKET.read_text(encoding="utf-8")).get("quotes", {})


def verify(po, quotes):
    r = {"date": po["date"], "scenario": po.get("scenario", {}).get("name", ""), "checks": []}
    today = po["date"]

    # 1. 指数：低开幅度 + 收盘涨跌 + 证伪线
    fl = po.get("scenario", {}).get("falsify_line", {})
    idx_code = fl.get("index", "sh000001")
    q = quotes.get(IDX_KEY.get(idx_code, "a_sh"), {})
    if q and "error" not in q:
        try:
            o, c, p = float(q["open"]), float(q["close"]), float(q["prev"])
            gap = (o / p - 1) * 100
            chg = (c / p - 1) * 100
            verdict = "低开高走" if (gap < 0 and chg > gap) else ("低开低走" if chg < gap else "低开震荡")
            r["index"] = {"open_gap": round(gap, 2), "close_chg": round(chg, 2), "verdict": verdict}
            r["checks"].append({
                "metric": f"证伪线 {idx_code} 收盘 vs {fl.get('level')}",
                "expected": f"> {fl.get('level')}",
                "actual": c,
                "hit": c > fl.get("level", 0) if fl.get("level") else None,
            })
            # Kando: 指数低开≥1.5%
            r["checks"].append({
                "metric": "Kando·指数低开≥1.5%", "expected": "≥1.5%",
                "actual": f"{gap:+.2f}%", "hit": gap <= -1.5,
            })
        except Exception:
            pass

    # 2. 个股：低开区间 + 关键位
    for s in po.get("stocks", []):
        key = CODE2KEY.get(s.get("code"))
        q = quotes.get(key, {}) if key else {}
        if not q or "error" in q:
            r["checks"].append({"metric": f"个股·{s['name']}", "expected": "实际数据缺失", "actual": "—", "hit": None})
            continue
        try:
            o, c, p = float(q["open"]), float(q["close"]), float(q["prev"])
            gap = (o / p - 1) * 100
            chg = (c / p - 1) * 100
            ge = s.get("gap_expected")
            gap_hit = (ge[0] <= gap <= ge[1]) if ge else None
            kl = s.get("key_level")
            kl_hit = (c > kl) if kl else None
            r["checks"].append({
                "metric": f"个股·{s['name']}",
                "expected": f"低开{ge} 关键位{kl}" if ge else f"关键位{kl}",
                "actual": f"低开{gap:+.2f}% 收{chg:+.2f}% 收价{c}",
                "hit": (gap_hit if gap_hit is not None else True) and (kl_hit if kl_hit is not None else True),
                "detail": {"gap": round(gap, 2), "close_chg": round(chg, 2), "close": c,
                           "gap_hit": gap_hit, "key_level_hit": kl_hit},
            })
        except Exception:
            pass

    # 3. 环境因子（VIX/黄金可用则对照）
    env = po.get("env", {})
    if env.get("vix") is not None:
        r["checks"].append({"metric": "Kando·VIX<18", "expected": "<18",
                            "actual": f"{env['vix']}（盘前）", "hit": env["vix"] < 18})
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    files = sorted(HIST.glob("*/preopen_*.json"))
    if args.date:
        files = [f for f in files if args.date in f.name]
    if not files:
        print("未找到 preopen 盘前判断 JSON")
        sys.exit(0)
    quotes = load_quotes()
    report_path = HIST / "_preopen_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {"records": []}
    for f in files:
        po = json.loads(f.read_text(encoding="utf-8"))
        res = verify(po, quotes)
        report["records"] = [x for x in report["records"] if x["date"] != res["date"]]
        report["records"].append(res)
        # 终端输出
        print(f"\n═══ 盘前验证 {res['date']}：{res['scenario']} ═══")
        if res.get("index"):
            i = res["index"]
            print(f"指数: 低开 {i['open_gap']:+.2f}% → 收 {i['close_chg']:+.2f}% | 判定 {i['verdict']}")
        for c in res["checks"]:
            mark = "✓" if c["hit"] else ("✗" if c["hit"] is False else "○")
            print(f"  {mark} {c['metric']}: 期望[{c['expected']}] 实际[{c['actual']}]")
        # 汇总
        scored = [c for c in res["checks"] if c["hit"] is not None]
        hits = sum(1 for c in scored if c["hit"])
        print(f"  → 命中 {hits}/{len(scored)}（未判定 {len(res['checks']) - len(scored)} 项）")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    # 历史命中率
    recs = report["records"]
    if len(recs) > 1:
        all_c = [c for r in recs for c in r["checks"] if c["hit"] is not None]
        h = sum(1 for c in all_c if c["hit"])
        print(f"\n【台账】累计 {len(recs)} 个交易日 | 判据命中率 {h}/{len(all_c)} = {h / len(all_c) * 100:.1f}%")


if __name__ == "__main__":
    main()
