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

ROOT = Path(__file__).resolve().parent.parent
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
    # 港股/亚太（08:15 北京 = 首尔/东京 09:15 已开盘 15 分钟，可抓盘中）
    ("hk_hsi",   "hkHSI",   "恒生指数",   "港股指数"),
    ("hk_hstech","hkHSTECH", "恒生科技",  "港股指数"),
]

# 统一字段（group(3) split 后）: 0=名称 1=代码 2=现价 3=昨收 4=今开 29=时间
#   30=涨跌额 31=涨跌幅 32=最高 33=最低 34=币种 35=量 36=额 37=换手
F_IDX = dict(close=2, prev=3, open=4, time=29, chg_amt=30, chg_pct=31,
             high=32, low=33, currency=34, vol=35, amt=36, turn=37)

# 美股标的：腾讯实时 code -> akshare stock_us_daily symbol（前一日+最新两日）
US_DAILY_MAP = {
    "us_dji": ".DJI", "us_inx": ".INX", "us_ixic": ".IXIC",
    "us_mu": "MU", "us_sndk": "SNDK", "us_lite": "LITE", "us_aaoi": "AAOI",
    "us_cohr": "COHR", "us_wdc": "WDC", "us_skhy": "SKHY", "us_mrvl": "MRVL",
    "us_nvda": "NVDA", "us_tsla": "TSLA",
}


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
    # 数据日期 = A股指数时间戳日期（如 20260824 → 2026-08-24），回退美股时间戳，再回退运行日
    data_date = now.strftime("%Y-%m-%d")
    for key in ("a_sh", "us_dji"):
        q = quotes.get(key, {})
        t = str(q.get("time", ""))
        if len(t) >= 8 and t[:8].isdigit():          # A股: 20260824161402
            data_date = f"{t[:4]}-{t[4:6]}-{t[6:8]}"
            break
        if t[:4].isdigit() and "-" in t[:10]:         # 美股: 2026-08-21 ...
            data_date = t[:10]
            break
    # ── 美股日 K 双日快照（隔夜复盘双日表数据源，根治硬编码滞后） ──
    us_kline = {}
    try:
        import akshare as _ak
        for k, sym in US_DAILY_MAP.items():
            try:
                df = _ak.stock_us_daily(symbol=sym)
            except Exception:
                continue
            if df is None or len(df) < 2:
                continue
            # 取最后两个交易日（latest=最新已收盘，prev=前一交易日，跳过周末自动）
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            try:
                l_close = float(latest["close"])
                p_close = float(prev["close"])
                us_kline[k] = {
                    "latest": {"date": str(latest["date"])[:10], "close": round(l_close, 2)},
                    "prev":   {"date": str(prev["date"])[:10],   "close": round(p_close, 2),
                                "chg_pct": round((l_close / p_close - 1) * 100, 2) if p_close else None,
                                "chg_amt": round(l_close - p_close, 2)},
                }
            except Exception:
                continue
        print(f"[daily-review] us_kline 双日: {len(us_kline)}/{len(US_DAILY_MAP)}")
    except Exception as _e:
        print(f"[daily-review] us_kline 拉取失败（非致命）: {type(_e).__name__} {str(_e)[:80]}")

    # ── 商品·利率·汇率（comm 字段，根治 analysis.html 里 agent 写死的 8/21 口径） ──
    comm = {}
    try:
        import requests as _req
        # 腾讯 hf_ 国际商品（现货黄金/COMEX金/WTI/布伦特）
        hf_codes = {"hf_XAU": "gold_spot", "hf_GC": "gold_comex", "hf_CL": "wti", "hf_OIL": "brent"}
        hf_names = {"gold_spot": "现货黄金", "gold_comex": "COMEX 黄金", "wti": "WTI 原油", "brent": "布伦特"}
        r = _req.get("https://qt.gtimg.cn/q=" + ",".join(hf_codes.keys()), timeout=12)
        r.encoding = "gbk"
        for line in r.text.strip().split(";"):
            m = line.split("=", 1)
            if len(m) < 2:
                continue
            code = m[0].replace("v_", "").strip()
            if code not in hf_codes:
                continue
            f = m[1].strip().strip('"').split(",")
            if len(f) < 13 or not f[0]:
                continue
            try:
                val = float(f[0]); chg = float(f[1])
                comm[hf_codes[code]] = {"name": hf_names[hf_codes[code]], "value": round(val, 2),
                                        "chg_pct": round(chg, 2), "date": f[12] if len(f) > 12 else ""}
            except Exception:
                pass
        # 美债 10Y/30Y（bond_zh_us_rate 最新日）
        try:
            import akshare as _ak
            bd = _ak.bond_zh_us_rate()
            bd = bd.dropna(subset=["美国国债收益率10年"])
            row = bd.iloc[-1]
            d10 = str(row["日期"])[:10]
            comm["us10y"] = {"name": "10Y 美债", "value": round(float(row["美国国债收益率10年"]), 3),
                             "chg_pct": None, "date": d10}
            if "美国国债收益率30年" in row.index and row["美国国债收益率30年"] == row["美国国债收益率30年"]:
                comm["us30y"] = {"name": "30Y 美债", "value": round(float(row["美国国债收益率30年"]), 3),
                                 "chg_pct": None, "date": d10}
        except Exception:
            pass
        # 人民币中间价（中行当日）
        try:
            import akshare as _ak
            cny = _ak.currency_boc_sina(symbol="美元", start_date="20260801", end_date="20260831")
            if cny is not None and len(cny):
                cr = cny.dropna(subset=["央行中间价"]).iloc[-1]
                comm["cny"] = {"name": "人民币中间价", "value": round(float(cr["央行中间价"]) / 100, 4),
                               "chg_pct": None, "date": str(cr["日期"])[:10]}
        except Exception:
            pass
        # 碳酸锂（广期所主连 LC0）
        try:
            import akshare as _ak
            lc = _ak.futures_main_sina(symbol="LC0", start_date="20260801", end_date="20260831")
            if lc is not None and len(lc):
                lr = lc.iloc[-1]
                comm["lithium"] = {"name": "碳酸锂（广期所主连）", "value": round(float(lr["收盘价"]), 0),
                                   "chg_pct": None, "date": str(lr["日期"])[:10]}
        except Exception:
            pass
        print(f"[daily-review] comm 商品利率汇率: {len(comm)} 项")
    except Exception as _e:
        print(f"[daily-review] comm 抓取失败（非致命）: {type(_e).__name__} {str(_e)[:80]}")

    # ── 日韩指数（新浪 znb 接口：日经225 / 首尔综合KOSPI；韩股个股无免费实时源留待本机） ──
    asia = {}
    try:
        r = _req.get("https://hq.sinajs.cn/list=znb_NKY,znb_KOSPI",
                     headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}, timeout=12)
        r.encoding = "gbk"
        for line in r.text.strip().splitlines():
            m = line.split("=", 1)
            if len(m) < 2 or "znb_" not in m[0]:
                continue
            code = m[0].replace("var hq_str_", "").replace("=", "").strip()
            f = m[1].strip().strip('"').split(",")
            if len(f) < 7 or not f[1]:
                continue
            key = {"znb_NKY": "nikkei", "znb_KOSPI": "kospi"}.get(code)
            if not key:
                continue
            try:
                asia[key] = {"name": f[0], "close": round(float(f[1]), 2),
                             "chg_pct": round(float(f[3]), 2), "date": f[6]}
            except Exception:
                pass
        print(f"[daily-review] asia 日韩指数: {len(asia)} 项")
    except Exception as _e:
        print(f"[daily-review] asia 日韩抓取失败（非致命）: {type(_e).__name__} {str(_e)[:80]}")

    out = {
        "date": data_date,
        "run_date": now.strftime("%Y-%m-%d"),
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source": "tencent-gtimg(实时) + akshare stock_us_daily(双日历史) + 腾讯hf商品/中行中间价 + 新浪znb日韩(免费无key)",
        "coverage": "A股指数/持仓/美股实时(腾讯) + 美股双日(akshare) + 商品利率汇率(腾讯hf/中行/乐咕) + 日韩指数(新浪znb); 韩股个股·星球·AI分析=本机agent",
        "quotes": quotes,
        "us_kline": us_kline,
        "comm": comm,
        "asia": asia,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1)
    OUT.write_text(text, encoding="utf-8")
    # 双写 deploy/（本地预览用；云端 deploy 由 git checkout 保证，try 容错）
    try:
        from pathlib import Path as _P
        deploy = _P(__file__).resolve().parent.parent / "deploy" / "data" / "daily_review" / "market.json"
        deploy.parent.mkdir(parents=True, exist_ok=True)
        deploy.write_text(text, encoding="utf-8")
    except Exception as _e:
        print(f"[daily-review] 双写 deploy/ 跳过: {_e}")
    ok = sum(1 for v in quotes.values() if "error" not in v)
    print(f"[daily-review] OK {ok}/{len(QUOTES)} -> {OUT}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if fetch() > 20 else 1)
