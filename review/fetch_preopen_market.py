#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘前版 market.json 局部更新（us_kline + asia），A股 09:30 前专用。

背景（REVIEW_SOP.md 步骤 1 / daily-reasoning Step 1 硬约束）：
    盘前 09:30 前【禁止跑全量】review/fetch_daily_review_market.py —— 它会把 A股/商品/汇率
    刷成「开盘前未成交」的错误状态（quotes 变成昨收或空、comm 变成隔夜残值）。
    盘前只需滚动两项：
      1) us_kline —— 昨夜美股收盘（akshare stock_us_daily），每个标的必须同时给
                     prev.close 与 latest.close（不得为 null，否则 V3 页全页卡「加载中…」）
      2) asia     —— 今早亚太开盘（新浪 znb 日经225 / KOSPI）+ fengle 韩国存储双雄
    其余字段（quotes / comm / coverage / source）原样保留，不动。

用法：
    python3 review/fetch_preopen_market.py            # 更新并双写
    python3 review/fetch_preopen_market.py --dry-run  # 只打印，不落盘

退出码：0 = 成功；2 = us_kline 关键标的缺失 close（须人工补数据）
"""
import argparse
import re
import datetime
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MKTS = [ROOT / "data" / "daily_review" / "market.json",
        ROOT / "deploy" / "data" / "daily_review" / "market.json"]
KR_SCRIPT = ROOT / "review" / "fengle_kr.py"

# 与 fetch_daily_review_market.py 的 US_DAILY_MAP 保持一致
US_DAILY_MAP = {
    "us_dji": ".DJI", "us_inx": ".INX", "us_ixic": ".IXIC",
    "us_mu": "MU", "us_sndk": "SNDK", "us_lite": "LITE", "us_aaoi": "AAOI",
    "us_cohr": "COHR", "us_wdc": "WDC", "us_skhy": "SKHY", "us_mrvl": "MRVL",
    "us_nvda": "NVDA", "us_tsla": "TSLA",
}
# 盘前必须齐备的核心标的（缺 latest.close 即红灯）
CORE = ["us_dji", "us_inx", "us_ixic"]


def _get(url, headers=None, timeout=15, gbk=True):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    return raw.decode("gbk" if gbk else "utf-8", errors="ignore")


def fetch_us_kline():
    """akshare stock_us_daily：取最后两个已完成交易日（latest / prev）。"""
    import akshare as ak
    out, miss = {}, []
    for k, sym in US_DAILY_MAP.items():
        try:
            df = ak.stock_us_daily(symbol=sym)
            if df is None or len(df) < 2:
                miss.append(k)
                continue
            latest, prev = df.iloc[-1], df.iloc[-2]
            l_close, p_close = float(latest["close"]), float(prev["close"])
            out[k] = {
                "latest": {"date": str(latest["date"])[:10], "close": round(l_close, 2)},
                "prev": {"date": str(prev["date"])[:10], "close": round(p_close, 2),
                         "chg_pct": round((l_close / p_close - 1) * 100, 2) if p_close else None,
                         "chg_amt": round(l_close - p_close, 2)},
            }
        except Exception as e:
            miss.append("%s(%s)" % (k, type(e).__name__))
    return out, miss


US_GT_CODES = {
    "us_dji": "usDJI", "us_inx": "usINX", "us_ixic": "usIXIC",
    "us_mu": "usMU", "us_sndk": "usSNDK", "us_lite": "usLITE", "us_aaoi": "usAAOI",
    "us_cohr": "usCOHR", "us_wdc": "usWDC", "us_skhy": "usSKHY", "us_mrvl": "usMRVL",
    "us_nvda": "usNVDA", "us_tsla": "usTSLA",
}
# 腾讯美股字段位：2=现价 3=昨收 29=时间 30=涨跌额 31=涨跌幅 32=最高 33=最低
F_IDX = dict(close=2, prev=3, time=29, chg_amt=30, chg_pct=31, high=32, low=33)


def fetch_us_quotes():
    """只重抓美股行情行（gtimg），把 quotes.us_* 从「上一交易日晚间盘中值」滚动为「昨夜收盘值」。

    🚨 不碰 A股 / 港股 / 商品 / 汇率 —— 盘前禁跑全量脚本的原因就在那几类。
    注意：V3 页 1 段报价表只显示「收盘/涨跌幅/最高/最低」且无时间列，
    若沿用 22:15 的盘中值会被误读为收盘价，故必须随 us_kline 一并滚动。
    """
    codes = ",".join(US_GT_CODES.values())
    text = _get("https://qt.gtimg.cn/q=" + codes, timeout=25)
    out = {}
    for line in text.strip().split(";"):
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        # gtimg 美股返回形如 v_usDJI="200~道琼斯~.DJI~52064.10~52380.66~..."，
        # 首位 "200" 为市场标识、且分隔符为 "~"：剥掉首位后 2=现价 3=昨收 29=时间 30=涨跌额 31=涨跌幅 32=最高 33=最低
        m = re.match(r'\s*"?(\d+)~(.*?)"?\s*$', v.strip())
        f = (m.group(2) if m else v.strip().strip('"')).split("~")
        if len(f) < 34:
            continue
        code = k.replace("v_", "").strip()
        key = next((kk for kk, cc in US_GT_CODES.items() if cc == code), None)
        if not key:
            continue
        try:
            out[key] = {
                "name": f[0],
                "close": round(float(f[F_IDX["close"]]), 2),
                "prev": round(float(f[F_IDX["prev"]]), 2),
                "chg_pct": round(float(f[F_IDX["chg_pct"]]), 2),
                "high": round(float(f[F_IDX["high"]]), 2) if f[F_IDX["high"]] else None,
                "low": round(float(f[F_IDX["low"]]), 2) if f[F_IDX["low"]] else None,
                "time": f[F_IDX["time"]],
            }
        except Exception:
            continue
    return out


def fetch_asia():
    """新浪 znb_ 日韩指数（须带 Referer，否则返空）。f[0]名称 f[1]点位 f[3]涨跌幅% f[6]日期"""
    text = _get("https://hq.sinajs.cn/list=znb_NKY,znb_KOSPI",
                headers={"Referer": "https://finance.sina.com.cn",
                         "User-Agent": "Mozilla/5.0"}, timeout=15)
    out = {}
    for line in text.strip().splitlines():
        m = line.split("=", 1)
        if len(m) < 2 or "znb_" not in m[0]:
            continue
        code = m[0].replace("var hq_str_", "").strip()
        f = m[1].strip().strip('"').split(",")
        if len(f) < 7 or not f[1]:
            continue
        key = {"znb_NKY": "nikkei", "znb_KOSPI": "kospi"}.get(code)
        if not key:
            continue
        try:
            out[key] = {"name": f[0], "close": round(float(f[1]), 2),
                        "chg_pct": round(float(f[3]), 2), "date": f[6]}
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = datetime.datetime.now().astimezone()
    src = MKTS[0]
    if not src.exists():
        print("❌ 找不到 %s" % src); sys.exit(1)
    mkt = json.loads(src.read_text(encoding="utf-8"))
    old_uk = mkt.get("us_kline") or {}

    # ── 1) 韩国存储双雄（fengle，独立脚本会自动合并 asia.kr_stocks 进两个 market.json）──
    kr_ok = False
    if KR_SCRIPT.exists() and not args.dry_run:
        import subprocess
        r = subprocess.run([sys.executable, str(KR_SCRIPT)], capture_output=True, text=True, timeout=120)
        kr_ok = r.returncode == 0
        tail = (r.stdout or "").strip().splitlines()
        print("[preopen] fengle 韩存储: %s %s" % ("OK" if kr_ok else "FAIL",
                                                  tail[-1] if tail else ""))
        if kr_ok:
            mkt = json.loads(src.read_text(encoding="utf-8"))   # 重载（含新 kr_stocks）

    # ── 2) us_kline：昨夜美股收盘 ──
    try:
        us_kline, miss = fetch_us_kline()
        print("[preopen] us_kline %d/%d %s" % (len(us_kline), len(US_DAILY_MAP),
                                               ("缺: " + ",".join(miss)) if miss else ""))
    except Exception as e:
        print("[preopen] us_kline 拉取失败: %s %s" % (type(e).__name__, str(e)[:100]))
        us_kline, miss = {}, list(US_DAILY_MAP)

    # 缺失标的用旧值兜底（宁可旧值也不留 null → 防 V3 页卡死），并记录
    fallback = []
    for k in US_DAILY_MAP:
        if k not in us_kline:
            if k in old_uk and (old_uk[k].get("latest") or {}).get("close") is not None:
                us_kline[k] = old_uk[k]; fallback.append(k)
            else:
                us_kline[k] = {"latest": {"date": None, "close": None},
                               "prev": {"date": None, "close": None,
                                        "chg_pct": None, "chg_amt": None}}
    if fallback:
        print("[preopen] ⚠️ 沿用旧值: %s" % ",".join(fallback))

    latest_dates = sorted({(v.get("latest") or {}).get("date") for v in us_kline.values() if (v.get("latest") or {}).get("date")})
    print("[preopen] us_kline latest 日期: %s" % ",".join(latest_dates))

    # ── 3) asia：今早亚太开盘 ──
    asia_new = {}
    try:
        asia_new = fetch_asia()
        print("[preopen] asia 指数 %d 项 %s" % (len(asia_new),
              " ".join("%s %s %.2f%%" % (v["name"], v["close"], v["chg_pct"]) for v in asia_new.values())))
    except Exception as e:
        print("[preopen] asia 抓取失败: %s %s" % (type(e).__name__, str(e)[:100]))
    asia = dict(mkt.get("asia") or {})
    asia.update(asia_new)                      # 只覆盖指数，保留 kr_stocks
    kr = asia.get("kr_stocks") or {}
    if kr.get("stocks"):
        print("[preopen] asia.kr_stocks 交易日 %s" % kr.get("date"))

    # ── 4) quotes.us_*：由「上一交易日盘中值」滚动为「昨夜收盘值」（不碰 A股/港股/商品/汇率）──
    quotes = dict(mkt.get("quotes") or {})
    n_us = 0
    try:
        uq = fetch_us_quotes()
        for k, v in uq.items():
            if k in quotes:
                quotes[k].update({kk: v[kk] for kk in
                                  ("close", "prev", "chg_pct", "high", "low", "time") if v.get(kk) is not None})
                n_us += 1
        print("[preopen] quotes 美股行滚动 %d/%d 项（→ 9/10 收盘口径）" % (n_us, len(US_GT_CODES)))
    except Exception as e:
        print("[preopen] quotes 美股行滚动失败（保留原值）: %s %s" % (type(e).__name__, str(e)[:100]))

    mkt["quotes"] = quotes
    mkt["us_kline"] = us_kline
    mkt["asia"] = asia
    mkt["run_date"] = now.strftime("%Y-%m-%d")
    mkt["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    mkt["preopen_partial"] = True              # 标记：本次为盘前局部更新
    mkt["preopen_note"] = ("盘前局部更新：us_kline + quotes.us_* = 昨夜美股收盘（口径：完整交易日收盘价，非盘中）；"
                           "asia = 今早亚太开盘；A股/港股/商品/汇率/美债 沿用上一交易日值（09:30 前禁跑全量）")

    bad_core = [k for k in CORE if (us_kline.get(k, {}).get("latest") or {}).get("close") is None]
    if bad_core:
        print("❌ 核心美股指数缺 close: %s" % ",".join(bad_core))

    if args.dry_run:
        print("[preopen] --dry-run：未落盘")
        return 2 if bad_core else 0

    text = json.dumps(mkt, ensure_ascii=False, indent=1)
    for p in MKTS:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print("[preopen] 已写 %s" % p.relative_to(ROOT))
    return 2 if bad_core else 0


if __name__ == "__main__":
    sys.exit(main())
