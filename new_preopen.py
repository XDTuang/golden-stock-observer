#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘前判断契约模板生成器 —— 生成当日 preopen_<T>.json（可编辑后供 verify_preopen 收盘验证）

用法:
  python3 new_preopen.py                  # 生成今日模板 data/daily_review_history/<T>/preopen_<T>.json
  python3 new_preopen.py --date 2026-08-26

模板已预填：
  - scenario: 路径 A/B/C（低开高走/震荡/低走）+ 证伪线 3860 占位
  - kando: 剑桥低开/德明利/指数低开/恒生科技/VIX/收盘 六项骨架
  - stocks: 全部 A 股持仓（从 market.json 读）+ 德明利 + 黄金期货（key_level 待填）
  - env: 环境因子占位

生成后请编辑填写：路径概率 / Kando 阈值 / 个股 gap_expected+key_level / env 实际值，
然后收盘后自动被 verify_preopen.py 验证（已接入 update_data.sh Step 3.8）。
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
HIST = BASE / "data" / "daily_review_history"
MARKET = BASE / "data" / "daily_review" / "market.json"

# 持仓 code -> 名称（market.json quotes 优先，缺则用此表）
HOLDINGS_FALLBACK = {
    "sh603083": "剑桥科技", "sh603399": "永杉锂业", "sz000988": "华工科技",
    "sh600378": "昊华科技", "sh600105": "永鼎股份", "sz002082": "ST万邦",
    "sh688825": "长鑫科技",
}
EXTRA_STOCKS = {
    "sz000922": {"name": "德明利", "sector": "存储模组", "action": "观察不操作"},
    "GC": {"name": "黄金期货", "sector": "贵金属", "action": "持仓不动·等回踩"},
}
KANDO_DEFAULT = [
    {"metric": "剑桥低开≤4%且5分钟内止跌", "target": "jq_low_gap_5m", "expected": "≤-4%内企稳"},
    {"metric": "德明利不跌停", "target": "dml_low", "expected": "非跌停"},
    {"metric": "指数低开≥1.5%", "target": "sh_gap", "expected": "≥1.5%"},
    {"metric": "恒生科技期货+0.3%以上", "target": "hti", "expected": "+0.3%"},
    {"metric": "VIX<18", "target": "vix", "expected": "<18"},
    {"metric": "收盘vs证伪线", "target": "sh_close", "expected": ">3860"},
]


def build_stocks():
    stocks = []
    names = {}
    if MARKET.exists():
        try:
            q = json.loads(MARKET.read_text(encoding="utf-8")).get("quotes", {})
            for v in q.values():
                if isinstance(v, dict) and v.get("group") == "持仓股" and not v.get("error"):
                    names[v["code"]] = v["name"]
        except Exception:
            pass
    for code, fb_name in HOLDINGS_FALLBACK.items():
        name = names.get(code, fb_name)
        stocks.append({"code": code, "name": name, "gap_expected": None, "key_level": None,
                       "key_level_basis": "", "action": ""})
    for code, meta in EXTRA_STOCKS.items():
        stocks.append({"code": code, "name": meta["name"], "gap_expected": None, "key_level": None,
                       "key_level_basis": "", "action": meta["action"]})
    return stocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(datetime.date.today()))
    args = ap.parse_args()
    d = args.date
    out_dir = HIST / d
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"preopen_{d}.json"
    if out.exists():
        print(f"⚠️ 已存在（不覆盖）: {out}")
        sys.exit(0)
    tmpl = {
        "date": d,
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "",
        "scenario": {
            "name": "",
            "paths": {
                "A": {"name": "低开高走（剧本兑现）", "prob": None, "trigger": ""},
                "B": {"name": "低开震荡（剧本打折）", "prob": None, "trigger": ""},
                "C": {"name": "低开低走（剧本失效）", "prob": None, "trigger": ""},
            },
            "falsify_line": {"index": "sh000001", "level": 3860, "basis": "收盘有效跌破=投降线"},
        },
        "kando": KANDO_DEFAULT,
        "stocks": build_stocks(),
        "env": {"us30y": None, "dxy": None, "vix": None, "gold": None,
                "nq": None, "hti": None, "kospi": None, "skhynix": None, "note": ""},
        "holdings_covered": [],
        "holdings_missing": [],
    }
    out.write_text(json.dumps(tmpl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 已生成盘前契约模板: {out}")
    print("  请编辑填写：scenario.paths 概率 / kando 阈值 / stocks 的 gap_expected+key_level / env 值")
    print("  收盘后 verify_preopen.py 自动验证（update_data.sh Step 3.8 已接入）")


if __name__ == "__main__":
    main()
