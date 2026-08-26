#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘「重点观测股推演」回测脚本（一周准确度验证 + 调优）
==============================================================
数据契约：
  输入: data/daily_review_history/<T>/obs_deduce_<T>.json  (推演日 T 的技术位+推演)
        data/daily_review_history/<T>/tx_kline_<T>.json    (腾讯前复权 K 线, 含 T 日)
  验证: 用腾讯接口拉取 T 之后下一交易日 (T+1) 的 OHLC，对比推演结论

评分维度（每只股票）:
  1. 方向准确率: 推演方向(上涨/下跌/震荡/回调...) vs 实际 T+1 收盘相对 T 收盘涨跌
  2. 开盘方式准确率: 推演(高开/低开/平开) vs 实际 T+1 开盘相对 T 收盘
  3. 分推演类型 / 分板块汇总

用法:
  python3 backtest_daily_review.py [--date T]   # 默认扫描全部历史
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
HIST = BASE / "data" / "daily_review_history"
PY_BIN = "/Users/samt/.workbuddy/binaries/python/versions/3.13.12/bin/python3"

TREND_DIRECTION = {
    "强势上涨": "up", "震荡上行": "up", "震荡偏强": "up", "震荡": "flat",
    "高位震荡": "flat", "震荡回调": "down", "震荡偏弱": "down", "弱势反弹": "up",
    "超跌反弹": "up", "弱势下跌": "down",
}
OPEN_DIRECTION = {
    "高开延续": "up", "高开偏强": "up", "高开回吐压力": "up", "平开高走": "up",
    "平开震荡": "flat", "平开偏强": "flat", "平开偏弱": "flat", "低开反弹": "down",
    "低开偏弱": "down", "低开破位风险": "down",
}


def fetch_tx_next_day(code: str, anchor_date: str):
    """拉取 code 的日 K，找到 anchor_date 的下一个交易日"""
    if code.startswith("hk"):
        url = f"https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?param={code},day,,,30,qfq"
    else:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,30,qfq"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
        with urllib.request.urlopen(req, timeout=15) as r:
            txt = r.read().decode("utf-8", errors="ignore")
        data = json.loads(txt)
        for c, d in data.get("data", {}).items():
            if isinstance(d, dict):
                arr = d.get("qfqday") or d.get("day") or []
                rows = [(x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in arr if len(x) >= 5]
                rows.sort(key=lambda x: x[0])
                for i, row in enumerate(rows):
                    if row[0] >= anchor_date and i + 1 < len(rows):
                        nxt = rows[i + 1]
                        return {"date": nxt[0], "open": nxt[1], "close": nxt[2], "high": nxt[3], "low": nxt[4]}
        return None
    except Exception as e:
        return {"err": str(e)}


def score_one(item: dict, nxt: dict):
    """对单只打分：方向 + 开盘"""
    if not nxt or "err" in nxt:
        return None
    t_close = item.get("tx_last") or item.get("screenshot_close") or item.get("close")
    if not t_close:
        return None
    direction = TREND_DIRECTION.get(item["trend"], "flat")
    # 实际方向：T+1 收盘 vs T 收盘
    chg = (nxt["close"] - t_close) / t_close * 100
    actual_dir = "up" if chg > 0.3 else ("down" if chg < -0.3 else "flat")
    dir_hit = (direction == actual_dir)
    # 开盘方式：T+1 开盘 vs T 收盘
    open_chg = (nxt["open"] - t_close) / t_close * 100
    open_d = item["open_label"]
    open_dir = OPEN_DIRECTION.get(open_d, "flat")
    actual_open = "up" if open_chg > 0.2 else ("down" if open_chg < -0.2 else "flat")
    open_hit = (open_dir == actual_open)
    return {
        "date": nxt["date"], "chg_pct": round(chg, 2), "dir_hit": dir_hit,
        "open_hit": open_hit, "actual_dir": actual_dir, "actual_open": actual_open,
        "nxt_open": nxt["open"], "nxt_close": nxt["close"],
    }


def _us_env_chg(anchor_date: str):
    """推演日 anchor_date 之前最近美股交易日（隔夜）的涨跌 %；失败返回 None"""
    try:
        import akshare as ak
        df = ak.stock_us_daily(symbol=".DJI")
        rows = df[df["date"].astype(str).str[:10] < str(anchor_date)]  # 严格早于 T：取 T 开盘前看到的隔夜美股
        if len(rows) >= 2:
            l, p = float(rows.iloc[-1]["close"]), float(rows.iloc[-2]["close"])
            return round((l / p - 1) * 100, 2)
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="推演日 T（默认扫描全部）")
    ap.add_argument("--auto", action="store_true", help="回测 derive_obs.py 自动滚动推演（obs_deduce_auto_*.json）")
    args = ap.parse_args()

    # 收集所有 obs_deduce 文件（默认 agent 归档；--auto 用 derive_obs.py 滚动推演归档）
    files = sorted(HIST.glob("*/obs_deduce_*.json"))
    if args.auto:
        files = [f for f in files if "auto" in f.name]
    else:
        files = [f for f in files if "auto" not in f.name]
    if args.date:
        files = [f for f in files if args.date in f.name]
    if not files:
        print("未找到 obs_deduce 数据（先跑 backup_daily_review.sh 归档）")
        sys.exit(0)

    total = {"n": 0, "dir_hit": 0, "open_hit": 0, "by_trend": {}, "by_sector": {}}
    detail = []
    for f in files:
        date = f.parent.name
        data = json.loads(f.read_text(encoding="utf-8"))
        # 兼容两种归档：agent 的 list / derive_obs auto 的 {items, env}
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
            env = (data.get("env") or {}).get("sh_chg", None)
        else:
            items = data
            env = items[0].get("env", {}).get("sh_chg", None) if items else None
        # 隔夜美股环境：推演日 T 之前最近美股交易日涨跌（akshare .DJI）
        us_chg = _us_env_chg(date)
        print(f"\n=== 推演日 {date}: {len(items)} 只 | 环境: 上证 {env:+.2f}% | 隔夜美股 {us_chg:+.2f}% ==="
              if env is not None and us_chg is not None
              else f"\n=== 推演日 {date}: {len(items)} 只 ===")
        for item in items:
            code = item["code"]
            nxt = fetch_tx_next_day(code, date)
            if not nxt:
                print(f"  {item['name']}: 无 T+1 数据（跳过）")
                continue
            sc = score_one(item, nxt)
            if not sc:
                continue
            total["n"] += 1
            total["dir_hit"] += 1 if sc["dir_hit"] else 0
            total["open_hit"] += 1 if sc["open_hit"] else 0
            total["by_trend"].setdefault(item["trend"], {"n": 0, "dir_hit": 0, "open_hit": 0})
            total["by_trend"][item["trend"]]["n"] += 1
            total["by_trend"][item["trend"]]["dir_hit"] += 1 if sc["dir_hit"] else 0
            total["by_trend"][item["trend"]]["open_hit"] += 1 if sc["open_hit"] else 0
            total["by_sector"].setdefault(item["sector"], {"n": 0, "dir_hit": 0})
            total["by_sector"][item["sector"]]["n"] += 1
            total["by_sector"][item["sector"]]["dir_hit"] += 1 if sc["dir_hit"] else 0
            # 环境分组：弱市(<-1%) / 偏弱(-1~-0.3%) / 中性以上(>-0.3%)
            if env is not None:
                if env < -1.0:
                    env_grp = "弱市(<-1%)"
                elif env < -0.3:
                    env_grp = "偏弱(-1%~-0.3%)"
                else:
                    env_grp = "中性以上(>-0.3%)"
                total.setdefault("by_env", {}).setdefault(env_grp, {"n": 0, "dir_hit": 0, "open_hit": 0})
                total["by_env"][env_grp]["n"] += 1
                total["by_env"][env_grp]["dir_hit"] += 1 if sc["dir_hit"] else 0
                total["by_env"][env_grp]["open_hit"] += 1 if sc["open_hit"] else 0
            # 隔夜美股环境分组（验证"隔夜大跌→次日反弹日推演失灵"假设）
            if us_chg is not None:
                if us_chg < -0.3:
                    us_grp = "隔夜美股跌(<-0.3%)"
                elif us_chg > 0.3:
                    us_grp = "隔夜美股涨(>+0.3%)"
                else:
                    us_grp = "隔夜美股平(±0.3%)"
                total.setdefault("by_us_env", {}).setdefault(us_grp, {"n": 0, "dir_hit": 0, "open_hit": 0})
                total["by_us_env"][us_grp]["n"] += 1
                total["by_us_env"][us_grp]["dir_hit"] += 1 if sc["dir_hit"] else 0
                total["by_us_env"][us_grp]["open_hit"] += 1 if sc["open_hit"] else 0
            detail.append({
                "code": code, "name": item["name"], "trend": item["trend"],
                "open_label": item["open_label"],
                "t_close": item.get("tx_last") or item.get("screenshot_close") or item.get("close"),
                **sc,
            })
            mark = "✓" if sc["dir_hit"] else "✗"
            print(f"  {mark} {item['name']:8s} 推演[{item['trend']}] 实际{sc['actual_dir']}({sc['chg_pct']:+.2f}%) | 开盘推演[{item['open_label'][:8]}] 实际{sc['actual_open']}({sc['nxt_open']})")
            time.sleep(0.5)  # 低频

    # 汇总
    if total["n"] == 0:
        print("\n无有效样本")
        sys.exit(0)
    print("\n" + "=" * 60)
    print(f"【总体】样本 {total['n']} 只 | 方向准确率 {total['dir_hit']/total['n']*100:.1f}% | 开盘准确率 {total['open_hit']/total['n']*100:.1f}%")
    print("\n【大盘环境分组】")
    if "by_env" in total:
        for g, v in sorted(total["by_env"].items(), key=lambda x: -x[1]["n"]):
            print(f"  {g:18s} n={v['n']:3d} 方向 {v['dir_hit']/v['n']*100:5.1f}% 开盘 {v['open_hit']/v['n']*100:5.1f}%")
    print("\n【分推演类型】")
    for t, v in sorted(total["by_trend"].items(), key=lambda x: -x[1]["n"]):
        print(f"  {t:8s} n={v['n']:3d} 方向 {v['dir_hit']/v['n']*100:5.1f}% 开盘 {v['open_hit']/v['n']*100:5.1f}%")
    print("\n【分板块】")
    for s, v in sorted(total["by_sector"].items(), key=lambda x: -x[1]["n"]):
        print(f"  {s:18s} n={v['n']:3d} 方向 {v['dir_hit']/v['n']*100:5.1f}%")
    if "by_us_env" in total:
        print("\n【分隔夜美股环境】（验证'隔夜大跌后反弹日推演失灵'假设）")
        for g, v in sorted(total["by_us_env"].items(), key=lambda x: -x[1]["n"]):
            print(f"  {g:20s} n={v['n']:3d} 方向 {v['dir_hit']/v['n']*100:5.1f}% 开盘 {v['open_hit']/v['n']*100:5.1f}%")

    out = BASE / "data" / "daily_review_history" / "_backtest_report.json"
    out.write_text(json.dumps({"total": total, "detail": detail}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n明细已存: {out}")


if __name__ == "__main__":
    main()
