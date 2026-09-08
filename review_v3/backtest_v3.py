#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V3 大盘结论回测（ai_synthesis.meta 版）
==============================================================
输入: output/v3_reasoning_YYYY-MM-DD.json（data_date=T，需含 ai_synthesis.meta）
验证: T+1 沪指实际（腾讯日 K 拉取，anchor=T 的下一个交易日 OHLC）
评分:
  1. 方向准确率: meta.direction(偏多/中性偏多/中性/中性偏空/偏空) vs T+1 沪指实际涨跌
     - 方向映射: 偏多/中性偏多 → up；中性 → flat；中性偏空/偏空 → down
     - 命中= 方向类别与 T+1 实际涨跌(±0.3%阈值) 相符
  2. 开盘准确率: meta.open_call(高开/平开/低开) vs T+1 沪指开盘相对 T 收盘
无 meta 的旧档（9-7/9-8）跳过并提示；自 R5 起累计。
用法: python3 review_v3/backtest_v3.py [--date T]
"""
import argparse
import json
import urllib.request
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
OUT = BASE / "output"

DIR_MAP = {"偏多": "up", "中性偏多": "up", "中性": "flat", "中性偏空": "down", "偏空": "down"}
OPEN_DIR = {
    "高开延续": "up", "高开偏强": "up", "高开回吐压力": "up", "平开高走": "up",
    "平开震荡": "flat", "平开偏强": "flat", "平开偏弱": "flat", "低开反弹": "down",
    "低开偏弱": "down", "低开破位风险": "down",
}


def fetch_next_sh(date: str):
    """拉上证指数日 K（sh000001），返回 anchor_date 的下一交易日 {date,open,close,chg}"""
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,,30,qfq"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
        with urllib.request.urlopen(req, timeout=15) as r:
            txt = r.read().decode("utf-8", errors="ignore")
        data = json.loads(txt)
        for c, d in data.get("data", {}).items():
            if isinstance(d, dict):
                arr = d.get("qfqday") or d.get("day") or []
                rows = [(x[0], float(x[1]), float(x[2])) for x in arr if len(x) >= 3]  # date, open, close
                rows.sort(key=lambda x: x[0])
                for i, row in enumerate(rows):
                    if row[0] == date and i + 1 < len(rows):
                        nxt = rows[i + 1]
                        prev_close = row[2]
                        return {
                            "date": nxt[0],
                            "open": nxt[1], "close": nxt[2],
                            "chg_pct": round((nxt[2] / prev_close - 1) * 100, 2),
                            "open_chg_pct": round((nxt[1] / prev_close - 1) * 100, 2),
                        }
        return None
    except Exception as e:
        return {"err": str(e)}


def settle_one(v: dict, nxt: dict):
    """v = v3_reasoning 的 {data_date, meta}；nxt = T+1 实际"""
    if not nxt or "err" in nxt:
        return None
    meta = v["meta"]
    # 方向命中
    dir_goal = DIR_MAP.get(meta.get("direction", ""), None)
    actual = "up" if nxt["chg_pct"] > 0.3 else ("down" if nxt["chg_pct"] < -0.3 else "flat")
    dir_hit = (dir_goal == actual)
    # 开盘命中
    open_goal = OPEN_DIR.get(meta.get("open_call", ""), None)
    actual_open = "up" if nxt["open_chg_pct"] > 0.2 else ("down" if nxt["open_chg_pct"] < -0.2 else "flat")
    open_hit = (open_goal == actual_open)
    return {
        "date": v["data_date"], "t1_date": nxt["date"],
        "direction": meta.get("direction"), "open_call": meta.get("open_call"),
        "sh_index_close": meta.get("sh_index_close"),
        "t1_chg_pct": nxt["chg_pct"], "t1_open_pct": nxt["open_chg_pct"],
        "dir_hit": dir_hit, "open_hit": open_hit,
        "note": "方向: 推演[%s]实际[%s] | 开盘: 推演[%s]实际[%s]" % (
            dir_goal or '?', actual, open_goal or '?', actual_open),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="只结算指定推演日（默认扫描全部含 meta 的档）")
    args = ap.parse_args()

    files = sorted(OUT.glob("v3_reasoning_*.json"))
    files = [f for f in files if "_latest" not in f.name and "_public" not in f.name]
    settled, skipped = [], []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        date = d.get("data_date", "")
        if args.date and args.date not in date:
            continue
        meta = (d.get("ai_synthesis") or {}).get("meta") or {}
        if not meta.get("direction") or not meta.get("open_call"):
            skipped.append((date, "无 meta（9-8 之前旧档，R5 起才有）" if date <= "2026-09-08" else "meta 不全"))
            continue
        nxt = fetch_next_sh(date)
        if not nxt:
            skipped.append((date, "无 T+1 数据（当日推演需次日收盘后）"))
            continue
        r = settle_one({"data_date": date, "meta": meta}, nxt)
        if r:
            settled.append(r)
            print("✓ %s → T+1 %s 沪指 %+.2f%% %s" % (date, r["t1_date"], r["t1_chg_pct"], r["note"]))
    for dt, why in skipped:
        print("· %s 跳过: %s" % (dt, why))

    # 落盘 output/backtest_v3.json
    total = {"n": len(settled), "dir_hit": sum(1 for x in settled if x["dir_hit"]), "open_hit": sum(1 for x in settled if x["open_hit"])}
    out = {
        "updated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "V3 大盘结论回测：ai_synthesis.meta 方向/开盘 vs T+1 沪指实际（自 R5 起累计；9-8 前旧档无 meta 跳过）",
        "periods": [{
            "date": x["date"], "t1_date": x["t1_date"], "direction": x["direction"], "open_call": x["open_call"],
            "t1_chg_pct": x["t1_chg_pct"], "dir_hit": x["dir_hit"], "open_hit": x["open_hit"],
        } for x in settled],
        "total": {"n": total["n"], "dir_acc": round(total["dir_hit"] / total["n"] * 100, 1) if total["n"] else None,
                  "open_acc": round(total["open_hit"] / total["n"] * 100, 1) if total["n"] else None},
    }
    (OUT / "backtest_v3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    # deploy 镜像
    (BASE / "deploy" / "output" / "backtest_v3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if total["n"]:
        print("📊 backtest_v3 落盘: 样本 %d · 方向 %.1f%% · 开盘 %.1f%%" % (total["n"], total["dir_hit"] / total["n"] * 100, total["open_hit"] / total["n"] * 100))
    else:
        print("📊 backtest_v3 落盘: 无样本（等待 R5+ 生成 meta 后累计）")


if __name__ == "__main__":
    main()
