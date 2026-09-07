#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_v3/fetch_preopen.py — V3 推演扩展数据一把抓（盘前/夜间模式专用，独立脚本）

定位：v3-daily-review skill Phase 2 数据层的本地主动抓取组件。
- 🚨 不写 market.json、不碰老站任何数据文件（盘前禁跑全量 fetch_daily_review_market.py 的替代方案）
- 产出：review_v3/preopen_ext.json + deploy/review_v3/preopen_ext.json（双写）
- 覆盖：隔夜美股收盘/盘中（腾讯 gtimg us 全量，GBK）+ 日韩（新浪 znb_）+ VIX（CBOE 官方 CSV）
       + 债汇币（联动 review_v3/fetch_global_ext.py）+ 美股 DST 判定 + 复盘模式分类
- 商品/利率/汇率/美债：不在本脚本范围 → 读 data/daily_review/market.json 的 comm（云端每日已刷）

用法：python3 review_v3/fetch_preopen.py
实测：2026-09-04 全部源无 key、国内可达（详见 ~/.workbuddy/skills/daily-reasoning/references/data-sources.md）
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # golden_stock_observer/
OUT_ROOT = os.path.join(ROOT, "review_v3", "preopen_ext.json")
OUT_DEPLOY = os.path.join(ROOT, "deploy", "review_v3", "preopen_ext.json")

# ── 美股代码表（与 V3 页 nameMap 31 项对齐；费半指数 gtimg 无代码 → usSOXX 代理，黑名单见速查表）──
US_MAP = {
    "us_dji": ("us.DJI", "道琼斯"), "us_inx": ("us.INX", "标普500"), "us_ixic": ("us.IXIC", "纳斯达克"),
    "us_sox": ("usSOXX", "费城半导体(代理:SOXX)"),
    "us_nvda": ("usNVDA", "英伟达"), "us_mu": ("usMU", "美光"), "us_sndk": ("usSNDK", "闪迪"),
    "us_lite": ("usLITE", "朗美通"), "us_aaoi": ("usAAOI", "应用光电"), "us_cohr": ("usCOHR", "COHR"),
    "us_wdc": ("usWDC", "西部数据"), "us_mrvl": ("usMRVL", "迈威尔"), "us_skhy": ("usSKHY", "海力士(美股)"),
    "us_tsla": ("usTSLA", "特斯拉"), "us_aapl": ("usAAPL", "苹果"), "us_msft": ("usMSFT", "微软"),
    "us_meta": ("usMETA", "META"), "us_googl": ("usGOOGL", "谷歌-A"), "us_amzn": ("usAMZN", "亚马逊"),
    "us_amd": ("usAMD", "AMD"), "us_avgo": ("usAVGO", "博通"), "us_tsm": ("usTSM", "台积电"),
    "us_arm": ("usARM", "安谋"), "us_intc": ("usINTC", "英特尔"), "us_smci": ("usSMCI", "超微电脑"),
    "us_dell": ("usDELL", "戴尔"), "us_crm": ("usCRM", "赛富时"), "us_pltr": ("usPLTR", "Palantir"),
    "us_snow": ("usSNOW", "Snowflake"), "us_okta": ("usOKTA", "OKTA"), "us_crwd": ("usCRWD", "CrowdStrike"),
    "us_panw": ("usPANW", "派拓网络"),
}


def _get(url, headers=None, timeout=18, gbk=True):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    return raw.decode("gbk" if gbk else "utf-8", errors="ignore")


def fetch_us():
    """腾讯 gtimg us 批量。字段位（0-based）：f[1]名称 f[3]现价 f[4]昨收 f[30]时间 f[31]涨跌额 f[32]涨跌幅%"""
    codes = ",".join(c for c, _ in US_MAP.values())
    text = _get("http://qt.gtimg.cn/q=" + codes, timeout=25)
    raw = {}
    for line in text.strip().split(";"):
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        f = v.strip().strip('"').split("~")
        if len(f) < 35:
            continue
        raw[k.replace("v_", "").strip()] = f
    out = {}
    for key, (code, name) in US_MAP.items():
        f = raw.get(code)
        if not f:
            continue
        try:
            out[key] = {
                "name": f[1] or name, "price": float(f[3]),
                "chg_pct": round(float(f[32]), 2) if f[32] else None,
                "src_time": f[30], "proxy": key == "us_sox",
            }
        except Exception:
            pass
    return out


def fetch_asia():
    """新浪 znb_ 日韩。字段位：f[0]名称 f[1]收盘 f[3]涨跌幅% f[6]日期。必须带 Referer 否则返空。"""
    text = _get("https://hq.sinajs.cn/list=znb_NKY,znb_KOSPI",
                headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}, timeout=15)
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


def fetch_vix():
    """CBOE 官方 CSV（日频，T-0 有延迟 → 须标注「前一交易日收盘值」）"""
    text = _get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
                timeout=20, gbk=False)
    lines = [l for l in text.strip().splitlines() if l and not l.startswith("Date")]
    if not lines:
        return None
    f = lines[-1].split(",")
    return {"date": f[0], "close": float(f[4]), "note": "CBOE 日频·前一交易日收盘值"}


def us_dst(d):
    """美国夏令时：3 月第 2 个周日 ~ 11 月第 1 个周日"""
    mar1 = date(d.year, 3, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = date(d.year, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    return dst_start <= d < dst_end


def classify_mode(now):
    """复盘模式分类（北京时间）。返回 (mode, 说明)。DST 双保险：硬规则 + 调用方可再用 gtimg src_time 校验。"""
    wd = now.weekday()
    hm = now.hour * 60 + now.minute
    open_bj = 21 * 60 + 30 if us_dst(now.date()) else 22 * 60 + 30
    if wd >= 5:
        return "nontrade", "周末（法定节假日未判，以 market.json.date 复核）"
    if hm < 6 * 60 + 30:
        return "night", "凌晨（属上一夜间盘窗口延续）"
    if hm < 9 * 60 + 25:
        return "preopen", "盘前窗口：隔夜美股收盘 + 日韩开盘"
    if hm < 15 * 60:
        return "intraday", "A股盘中（数据不全，不建议跑；坚持则出半场版并显著标注）"
    if hm < open_bj:
        return "close_transition", "收盘过渡版：A股收盘全量，美股未开盘沿用隔夜"
    return "night", "夜间盘窗口：A股收盘 + 美股盘中实时（须标注盘中·非收盘价）"


def main():
    now = datetime.now()
    mode, mode_note = classify_mode(now)
    print(f"[preopen] 北京 {now:%Y-%m-%d %H:%M} · 模式 {mode}（{mode_note}）")

    out = {"generated_at": now.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode, "mode_note": mode_note,
           "us_dst": us_dst(now.date()),
           "us_open_bj": "21:30" if us_dst(now.date()) else "22:30",
           "us": {}, "asia": {}, "vix": None, "global_ext": None, "errors": []}

    try:
        out["us"] = fetch_us()
        print(f"[preopen] 美股 {len(out['us'])}/{len(US_MAP)} 项")
    except Exception as e:
        out["errors"].append(f"us: {type(e).__name__} {str(e)[:80]}")
        print(f"[preopen] 美股抓取失败: {e}")
    try:
        out["asia"] = fetch_asia()
        print(f"[preopen] 日韩 {len(out['asia'])} 项")
    except Exception as e:
        out["errors"].append(f"asia: {type(e).__name__} {str(e)[:80]}")
        print(f"[preopen] 日韩抓取失败: {e}")
    try:
        out["vix"] = fetch_vix()
        print(f"[preopen] VIX {out['vix']}")
    except Exception as e:
        out["errors"].append(f"vix: {type(e).__name__} {str(e)[:80]}")
        print(f"[preopen] VIX 抓取失败: {e}")

    # 债汇币联动（独立脚本已实测；失败不致命）
    try:
        fx_script = os.path.join(ROOT, "review_v3", "fetch_global_ext.py")
        r = subprocess.run([sys.executable, fx_script], capture_output=True, text=True, timeout=90)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "[preopen] global_ext 无输出")
        gx_path = os.path.join(ROOT, "review_v3", "global_ext.json")
        if os.path.exists(gx_path):
            gx = json.load(open(gx_path))
            out["global_ext"] = {"date": gx.get("date"), "items": gx.get("items")}
    except Exception as e:
        out["errors"].append(f"global_ext: {type(e).__name__} {str(e)[:80]}")
        print(f"[preopen] 债汇币联动失败: {e}")

    # 双写（根 + deploy 预览副本）
    for p in (OUT_ROOT, OUT_DEPLOY):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fp:
            json.dump(out, fp, ensure_ascii=False, indent=1)
    print(f"[preopen] 已写出 {OUT_ROOT}（+deploy 副本），errors={len(out['errors'])}")


if __name__ == "__main__":
    main()
