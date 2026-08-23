#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日复盘 — 云端行情抓取（GitHub Actions 运行）

数据源: 腾讯公开行情接口 qt.gtimg.cn（无需 API Key）
覆盖: A股指数5 + 持仓7 + 美股指数3 + 美股映射8 + 参考2 = 25 标的
输出: data/daily_review/market.json（行情段）

分工说明:
  - 本文件由云端 Actions 每交易日 08:15(北京) 自动运行并 push → 云端自动更新行情段
  - 日韩指数 / 知识星球摘要 / AI 分析区(结论·宏观·科技·指引) → 依赖本机 agent
    （neodata token、星球权限、AI 分析均在本机；费半 SOX 公开源亦不稳定）
用法:
    python3 fetch_daily_review_market.py
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "daily_review" / "market.json"

QUOTES = [
    # (key, code, 名称, 分组)
    ("a_sh",  "sh000001", "上证指数", "A股指数"),
    ("a_sz",  "sz399001", "深证成指", "A股指数"),
    ("a_cyb", "sz399006", "创业板指", "A股指数"),
    ("a_kcb", "sh000688", "科创50",   "A股指数"),
    ("a_bj",  "bj899050", "北证50",   "A股指数"),
    ("h_ys",  "sh603399", "永杉锂业",  "持仓股"),
    ("h_jq",  "sh603083", "剑桥科技",  "持仓股"),
    ("h_hg",  "sz000988", "华工科技",  "持仓股"),
    ("h_hh",  "sh600378", "昊华科技",  "持仓股"),
    ("h_yd",  "sh600105", "永鼎股份",  "持仓股"),
    ("h_wb",  "sz002082", "ST万邦",    "持仓股"),
    ("h_cx",  "sh688825", "长鑫科技",  "持仓股"),
    ("us_dji", "usDJI",  "道琼斯",   "美股指数"),
    ("us_inx", "usINX",  "标普500",  "美股指数"),
    ("us_ixic","usIXIC", "纳斯达克", "美股指数"),
    ("us_mu",   "usMU",   "MU美光",      "美股映射"),
    ("us_sndk", "usSNDK", "SNDK闪迪",    "美股映射"),
    ("us_lite", "usLITE", "LITE朗美通",  "美股映射"),
    ("us_aaoi", "usAAOI", "AAOI",        "美股映射"),
    ("us_cohr", "usCOHR", "COHR",        "美股映射"),
    ("us_wdc",  "usWDC",  "WDC西部数据", "美股映射"),
    ("us_skhy", "usSKHY", "SKHY海力士",  "美股映射"),
    ("us_mrvl", "usMRVL", "MRVL迈威尔",  "美股映射"),
    ("us_nvda", "usNVDA", "NVDA",        "美股映射·参考"),
    ("us_tsla", "usTSLA", "TSLA",        "美股映射·参考"),
]

# 统一字段（group(3) split 后）: 0=名称 1=代码 2=现价 3=昨收 4=今开 29=时间
#   30=涨跌额 31=涨跌幅 32=最高 33=最低 34=币种 35=量 36=额 37=换手
F_IDX = dict(close=2, prev=3, open=4, time=29, chg_amt=30, chg_pct=31,
             high=32, low=33, currency=34, vol=35, amt=36, turn=37)


def fetch():
    url = "https://qt.gtimg.cn/q=" + ",".join(q[1] for q in QUOTES)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("gbk", errors="ignore")
    by_code = {}
    for line in raw.split(";"):
        m = re.match(r'v_(\w+)="(\d+)~(.*)"', line.strip())
        if not m:
            continue
        by_code[m.group(1)] = m.group(3).split("~")

    quotes = {}
    for key, code, name, group in QUOTES:
        f = by_code.get(code)
        if not f or len(f) <= 34:
            quotes[key] = {"code": code, "name": name, "group": group, "error": "unavailable"}
            continue
        quotes[key] = {
            "code": code, "name": name, "group": group,
            "close": f[F_IDX["close"]], "prev": f[F_IDX["prev"]], "open": f[F_IDX["open"]],
            "chg_amt": f[F_IDX["chg_amt"]], "chg_pct": f[F_IDX["chg_pct"]],
            "high": f[F_IDX["high"]], "low": f[F_IDX["low"]],
            "currency": f[F_IDX["currency"]] if len(f) > F_IDX["currency"] else "",
            "vol": f[F_IDX["vol"]] if len(f) > F_IDX["vol"] else "",
            "amt": f[F_IDX["amt"]] if len(f) > F_IDX["amt"] else "",
            "turn": f[F_IDX["turn"]] if len(f) > F_IDX["turn"] else "",
            "time": f[F_IDX["time"]],
        }

    now = datetime.datetime.now().astimezone()
    # 数据日期 = 美股指数时间戳日期（如 2026-08-21），回退运行日
    data_date = now.strftime("%Y-%m-%d")
    dji = quotes.get("us_dji", {})
    t = str(dji.get("time", ""))
    if t[:4].isdigit() and "-" in t:
        data_date = t[:10]
    out = {
        "date": data_date,
        "run_date": now.strftime("%Y-%m-%d"),
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source": "tencent-gtimg(公开接口,无Key)",
        "coverage": "A股指数/持仓/美股指数/美股映射(云端自动); 日韩·费半·商品汇率·星球·AI分析=本机agent",
        "quotes": quotes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for v in quotes.values() if "error" not in v)
    print(f"[daily-review] OK {ok}/{len(QUOTES)} -> {OUT}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if fetch() > 20 else 1)
