#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重点观测股推演引擎（正式版 v2）
================================
输入: tx_kline_<date>.json（腾讯前复权 K 线）
输出: obs_deduce_<date>.json（技术位 + 走势推演 + 开盘方式）

v2 调优（基于 8/21 推演 vs 8/24 实际回测，2026-08-24）:
  R1. 去掉"震荡"中间态：强制二选一（偏强/偏弱），消除"没观点"推演
      （首批回测：震荡型 7 只仅 14.3% 方向命中）
  R2. "超跌反弹"加环境门槛：仅当大盘当日不弱（sh_chg > -0.5%）才允许推反弹
      （8/24 大跌日超跌反弹 3 只 0 命中）
  R3. "震荡偏强"需高置信门槛：dev_ma5 > 3% 且 vol_ratio > 1.2，否则降级
      （首批：偏强 2 只 0 命中 = 门槛过低）

用法:
  python deduce_obs.py --date 2026-08-24 [--sh-chg -0.59]
    --sh-chg 上证当日涨跌幅（默认 0，用于超跌反弹环境门槛）
"""
import argparse
import json
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer/data/daily_review")


def analyze(klines):
    """10 日窗口计算技术位"""
    if not klines:
        return None
    kl = klines[-10:]
    closes = [k["close"] for k in kl if k["close"]]
    highs = [k["high"] for k in kl if k["high"]]
    lows = [k["low"] for k in kl if k["low"]]
    vols = [k["vol"] for k in kl if k["vol"] is not None]
    n = len(closes)
    if n < 3:
        return None
    last = closes[-1]
    ma5 = sum(closes[-min(5, n):]) / min(5, n)
    ma10 = sum(closes[-min(10, n):]) / min(10, n)
    high10 = max(highs)
    low10 = min(lows)
    vol_last = vols[-1] if vols else 0
    vol_ma5 = sum(vols[-min(5, n):]) / min(5, n) if len(vols) >= 5 else vol_last
    vol_ratio = vol_last / vol_ma5 if vol_ma5 > 0 else 1
    last5 = closes[-min(5, n):]
    up5 = sum(1 for i in range(1, len(last5)) if last5[i] > last5[i-1])
    dev_ma5 = (last - ma5) / ma5 * 100
    chg5 = (last / last5[0] - 1) * 100 if last5[0] > 0 else 0
    chg_last = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 and closes[-2] else None
    if last > ma5 > ma10:
        pattern = "多头排列"
    elif last < ma5 < ma10:
        pattern = "空头排列"
    elif last > ma5:
        pattern = "MA5 上穿"
    else:
        pattern = "震荡纠缠"
    return {
        "last": last, "ma5": round(ma5, 2), "ma10": round(ma10, 2),
        "high10": round(high10, 2), "low10": round(low10, 2),
        "vol_ratio": round(vol_ratio, 2), "up5": up5,
        "pattern": pattern, "dev_ma5": round(dev_ma5, 2), "chg5": round(chg5, 2),
        "chg_last": round(chg_last, 2) if chg_last is not None else None,
    }


def deduce(t, sh_chg=0.0):
    """
    推演次日走势 + 开盘方式（v2 规则）
    sh_chg: 上证当日涨跌幅%，用于超跌反弹环境门槛（R2）
    """
    if not t:
        return ("—", "—")
    pat, dev, chg5, vol = t["pattern"], t["dev_ma5"], t["chg5"], t["vol_ratio"]
    chg_last = t["chg_last"] or 0

    if pat == "多头排列":
        if dev > 5 and chg5 > 3:
            return ("强势上涨", "高开延续（量价齐升）")
        if chg_last > 3:
            return ("震荡上行", "高开偏强")
        if chg_last < -3:
            return ("高位回调", "低开或平开偏弱（涨幅过大回吐）")
        return ("震荡偏强", "平开高走")

    if pat == "空头排列":
        if chg5 < -8:
            return ("弱势下跌", "低开破位风险")
        if chg_last > 2:
            return ("弱势反弹", "高开反弹（超跌修复）")
        return ("震荡偏弱", "低开或平开偏弱")

    if pat == "MA5 上穿":
        return ("震荡偏强", "平开偏强（5 日线支撑）")

    # ── 震荡纠缠（v2 重写：R1 去中间态 / R2 环境门槛 / R3 置信门槛）──
    # R2: 超跌反弹仅当大盘不弱
    if chg5 < -8 and sh_chg > -0.5:
        return ("超跌反弹", "低开反弹（关注 5 日线压力）")
    if chg5 < -8:  # 大盘弱 → 不推反弹，改弱势
        return ("弱势下跌", "低开破位风险（大盘拖累）")
    if chg5 > 5:
        return ("高位震荡", "高开回吐压力")
    if chg5 < -3:
        return ("震荡回调", "低开偏弱")
    # R3: 偏强需高置信（dev_ma5>3 且 vol>1.2），否则偏弱
    if chg_last > 3 and dev > 3 and vol > 1.2:
        return ("震荡上行", "高开延续或平开偏强")
    if chg_last > 3:
        return ("震荡偏强", "平开高走（置信一般）")
    if chg_last < -3:
        return ("震荡回调", "低开或平开偏弱")
    # R1: 无中间态——按偏弱处理（熊市日默认偏弱）
    return ("震荡偏弱", "平开震荡（中性偏弱）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="数据日期 YYYY-MM-DD")
    ap.add_argument("--sh-chg", type=float, default=0.0, help="上证当日涨跌幅%（超跌反弹环境门槛）")
    args = ap.parse_args()

    src = BASE / f"tx_kline_{args.date}.json"
    out = BASE / f"obs_deduce_{args.date}.json"
    raw = json.loads(src.read_text(encoding="utf-8"))

    result = []
    for code, info in raw.items():
        klines = info.get("klines") or []
        t = analyze(klines)
        trend, open_label = deduce(t, args.sh_chg) if t else ("—", "—")
        result.append({
            "code": code, "name": info.get("name"), "sector": info.get("sector"),
            "close": t["last"] if t else None, "chg_last": t["chg_last"] if t else None,
            "ma5": t["ma5"] if t else None, "ma10": t["ma10"] if t else None,
            "high10": t["high10"] if t else None, "low10": t["low10"] if t else None,
            "pattern": t["pattern"] if t else None, "dev_ma5": t["dev_ma5"] if t else None,
            "chg5": t["chg5"] if t else None, "vol_ratio": t["vol_ratio"] if t else None,
            "trend": trend, "open_label": open_label,
            "env": {"sh_chg": args.sh_chg},
        })

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[deduce_obs v2] {len(result)} 只 -> {out}")
    print(f"  环境: 上证 {args.sh_chg:+.2f}%")
    from collections import Counter
    cnt = Counter(r["trend"] for r in result)
    for k, v in cnt.most_common():
        print(f"    {k}: {v}")
    return result


if __name__ == "__main__":
    main()
