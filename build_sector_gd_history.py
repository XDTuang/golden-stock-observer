#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块前100·换手≥4% 门控 · 金钻池数据仓库（与 build_gd_history.py 平行，独立建档）
==============================================================================
为「板块前100·换手≥4%」(sector_top100_to4) 门控单独维护一份
「金钻池 · 近 20 交易日演化」数据仓库，与「当前门控（成交额TOP800）」的门控
跟踪彼此独立、互不干扰。

单一真值源：复用 golden_diamond_viewer/server.py 的 analyze()（与每日扫描一致）。

数据来源：
  - 每日 --append：从 output/golden_pool_meta.json 的 sector 档提取当日金钻池
    （每只股票已含 primary 主信号 + signals[].date 触发日，与主站展示口径一致）。
  - 一次性 --build（回填）：直接复用 meta.sector.stocks 内嵌的 250 日 K线，
    对「今日板块范围」逐日重算金钻主信号，回填近 keep_days 个交易日。
    （板块范围逐日变动，回填采用固定今日范围，等价于「跟踪同一篮子近 20 日信号演化」，
      与 pool 档 build 采用固定 TOP800 范围重算的思路一致；每日 --append 为精确值。）

产出 output/sector_golden_diamond_history.json：
  {
    "built_at": "...", "gate": "sector_top100_to4", "pool_size": 614,
    "keep_days": 20, "data_date": "2026-07-20",
    "trading_days": ["...", "2026-07-20"],
    "snapshots": { "2026-07-20": { "sz002167": {"name":..., "primary":..., "signal_date":..., "days_ago":...} } }
  }
"""
import os
import sys
import json
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "golden_diamond_viewer"))
from server import analyze  # noqa: E402  唯一经实盘校验的真值源

META = os.path.join(BASE, "output", "golden_pool_meta.json")
HISTORY = os.path.join(BASE, "output", "sector_golden_diamond_history.json")
RANK = {"金钻起涨": 3, "买入": 2, "红区黄柱连续": 1}
GATE = "sector_top100_to4"


def _rank(t):
    return RANK.get(t, RANK["红区黄柱连续"] if (t or "").startswith("红区黄柱连续") else 0)


def _primary_of(signals):
    """返回 (primary_type, signal_date)。取最高优先级信号。"""
    best = None
    best_rank = -1
    best_date = None
    for s in signals or []:
        t = s.get("type", "")
        r = _rank(t)
        if r > best_rank:
            best_rank = r
            best = t
            best_date = s.get("date")
    return (best or ""), best_date


def _load_meta_sector():
    if not os.path.exists(META):
        return None, None
    meta = json.load(open(META, encoding="utf-8"))
    sec = meta.get("sector") or {}
    stocks = sec.get("stocks") or []
    return meta.get("data_date"), stocks


# ──────────────────────────────────────────────────────────────
# 每日追加（盘后，由 update_data.sh 调用）
# ──────────────────────────────────────────────────────────────
def append_today(keep_days=20):
    data_date, stocks = _load_meta_sector()
    if not data_date:
        print("  ❌ golden_pool_meta.json 缺少 data_date")
        return None
    if not stocks:
        print("  ⚠️  sector 档当日无金钻命中（仍写入空快照，保持交易日连续）")
    snap = {}
    for s in stocks:
        code = s.get("code")
        if not code:
            continue
        prim = (s.get("primary") or "").replace("天", "日")
        sigs = s.get("signals") or []
        if not prim:
            prim, sd = _primary_of(sigs)
            if not prim:
                continue
        else:
            sd = sigs[0].get("date") if sigs else None
        days_ago = s.get("days_ago")
        if days_ago is None and sd:
            try:
                days_ago = (datetime.datetime.strptime(data_date, "%Y-%m-%d").date()
                            - datetime.datetime.strptime(sd, "%Y-%m-%d").date()).days
            except Exception:
                days_ago = None
        snap[code] = {
            "name": s.get("name", code),
            "primary": prim,
            "signal_date": sd,
            "days_ago": days_ago,
        }

    history = {"snapshots": {}, "trading_days": []}
    if os.path.exists(HISTORY):
        history = json.load(open(HISTORY, encoding="utf-8"))
    history.setdefault("snapshots", {})
    history.setdefault("trading_days", [])
    history["snapshots"][data_date] = snap
    all_days = sorted(history["snapshots"].keys())
    if len(all_days) > keep_days:
        for old in all_days[:-keep_days]:
            history["snapshots"].pop(old, None)
        all_days = all_days[-keep_days:]
    history["trading_days"] = all_days
    history["built_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    history["gate"] = GATE
    history["pool_size"] = max(history.get("pool_size", 0), len(stocks))
    history["keep_days"] = keep_days
    history["data_date"] = data_date
    json.dump(history, open(HISTORY, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ 已追加 {data_date} 板块门控金钻池快照（{len(snap)} 只），保留 {len(all_days)} 个交易日")
    return history


# ──────────────────────────────────────────────────────────────
# 一次性回填（基于 meta.sector.stocks 内嵌 250 日 K线，固定今日范围逐日重算）
# ──────────────────────────────────────────────────────────────
def build_history(keep_days=20):
    data_date, stocks = _load_meta_sector()
    if not stocks:
        print("  ❌ sector 档无股票，无法回填")
        return None
    # 全市场交易日并集（取自内嵌 K线）
    all_dates = set()
    klines = {}
    for s in stocks:
        code = s.get("code")
        kl = s.get("kline") or []
        if not kl:
            continue
        klines[code] = {
            "name": s.get("name", code),
            "rows": [{"date": r.get("date"), "open": float(r.get("open", 0)),
                      "high": float(r.get("high", 0)), "low": float(r.get("low", 0)),
                      "close": float(r.get("last", r.get("close", 0))),
                      "volume": float(r.get("volume", 0))} for r in kl],
        }
        for r in kl:
            if r.get("date"):
                all_dates.add(r["date"])
    trading_days = sorted(all_dates)[-keep_days:]
    print(f"  📅 板块门控回填最近 {keep_days} 个交易日：{trading_days[0]} … {trading_days[-1]}（范围 {len(klines)} 只）")

    snapshots = {}
    for D in trading_days:
        d0 = datetime.datetime.strptime(D, "%Y-%m-%d").date()
        snap = {}
        for code, d in klines.items():
            rows = [r for r in d["rows"] if r["date"] <= D]
            if len(rows) < 60:
                continue
            try:
                res = analyze(rows)
            except Exception:
                continue
            prim, sig_date = _primary_of(res.get("signals", []))
            if not prim:
                continue
            days_ago = None
            if sig_date:
                try:
                    days_ago = (d0 - datetime.datetime.strptime(sig_date, "%Y-%m-%d").date()).days
                except Exception:
                    days_ago = None
            snap[code] = {
                "name": d.get("name", code),
                "primary": prim,
                "signal_date": sig_date,
                "days_ago": days_ago,
            }
        snapshots[D] = snap
        print(f"    {D}: 板块门控金钻池 {len(snap)} 只")

    history = {
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "gate": GATE,
        "pool_size": len(klines),
        "keep_days": keep_days,
        "data_date": data_date,
        "trading_days": trading_days,
        "snapshots": snapshots,
    }
    json.dump(history, open(HISTORY, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ 板块门控数据仓库已写入 {HISTORY}（{len(trading_days)} 个交易日，固定今日范围回填）")
    return history


def main():
    args = sys.argv[1:]
    keep = 20
    mode = "append"
    for a in args:
        if a == "--build":
            mode = "build"
        elif a == "--append":
            mode = "append"
        elif a.startswith("--days="):
            keep = int(a.split("=")[1])

    print("═══ 板块前100·换手≥4% 门控 · 金钻池数据仓库 ═══")
    if mode == "build":
        build_history(keep_days=keep)
    else:
        append_today(keep_days=keep)


if __name__ == "__main__":
    main()
