#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜宝金钻 · 金钻池数据仓库
=================================
缓存最近 N 个交易日的「金钻池」快照，供「兜宝金钻」tab 做日期回溯与变动跟踪。

设计要点：
  - 单一真值源：复用 golden_diamond_viewer/server.py 的 analyze()，与每日扫描完全一致。
  - 优先级：金钻起涨(3) > 买入(2) > 红区黄柱连续(1)（与 golden_diamond_scan._primary 一致）。
  - 快照内容（每只股票）：{name, primary, signal_date, days_ago}
      primary     = 该交易日盘后该股票的主信号（最高优先级）
      signal_date = 主信号触发日（窗口内）
      days_ago    = 该交易日距 signal_date 的天数（0=当天触发）

两种用法：
  python build_gd_history.py --build [--days 20] [--force-fetch]
      从候选池历史 K 线截取出最近 N 个交易日的金钻池快照（重建数据仓库）。
      会按需拉取候选股 250 日 K 线并缓存在 output/kline_pool_raw.json。

  python build_gd_history.py --append
      读取当日 output/golden_diamond.json，把当天金钻池快照追加进数据仓库，
      并保留最近 N 个交易日（自动滚动裁剪）。供每日盘后更新调用。

产出 output/golden_diamond_history.json：
  {
    "built_at": "...", "pool_size": 64, "keep_days": 20,
    "trading_days": ["2026-06-13", ..., "2026-07-10"],
    "snapshots": {
       "2026-07-10": { "sh600345": {"name":"长江通信","primary":"金钻起涨","signal_date":"2026-07-09","days_ago":1}, ... },
       ...
    }
  }
"""
import os
import sys
import json
import time
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "golden_diamond_viewer"))
from server import analyze, fetch_kline  # noqa: E402

POOL_PATH = os.path.join(BASE, "candidate_pool.json")
KLINE_RAW_PATH = os.path.join(BASE, "output", "kline_raw.json")
KLINE_CACHE = os.path.join(BASE, "output", "kline_pool_raw.json")
HISTORY_PATH = os.path.join(BASE, "output", "golden_diamond_history.json")
TODAY_JSON = os.path.join(BASE, "output", "golden_diamond.json")

RANK = {"金钻起涨": 3, "买入": 2, "红区黄柱连续": 1}


def _slim(rows):
    """kline_raw 的 last→close 映射，与 golden_diamond_scan._slim 完全一致，保留 OHLCV 供 analyze。"""
    out = []
    for r in rows:
        out.append({
            "date": r.get("date"),
            "open": round(float(r.get("open", 0)), 2),
            "high": round(float(r.get("high", 0)), 2),
            "low": round(float(r.get("low", 0)), 2),
            "close": round(float(r.get("last", r.get("close", 0))), 2),
            "volume": round(float(r.get("volume", 0)), 2),
        })
    return out


def _rank(t: str) -> int:
    return RANK.get(t, RANK["红区黄柱连续"] if t.startswith("红区黄柱连续") else 0)


def _primary_of(res: dict):
    """返回 (primary_type, signal_date)。取最高优先级信号。"""
    best = None
    best_rank = -1
    best_date = None
    for s in res.get("signals", []):
        t = s.get("type", "")
        r = _rank(t)
        if r > best_rank:
            best_rank = r
            best = t
            best_date = s.get("date")
    return (best or ""), best_date


# ──────────────────────────────────────────────────────────────
# K 线获取（带缓存 / 重试）
# ──────────────────────────────────────────────────────────────
def load_pool_kline(force_fetch=False):
    # 重建门控：优先复用 TOP800 池的 250 日 K 线（kline_raw.json，与当前门控同源、
    # 已含完整历史），做 last→close 映射后与 analyze() 兼容，免重复拉取网络 K 线。
    if os.path.exists(KLINE_RAW_PATH) and not force_fetch:
        try:
            raw = json.load(open(KLINE_RAW_PATH, encoding="utf-8"))
            cache = {}
            if isinstance(raw, list):
                for it in raw:
                    code = it.get("code")
                    if not code:
                        continue
                    kline = it.get("kline") or []
                    cache[code] = {"name": it.get("name", code), "rows": _slim(kline)}
            elif isinstance(raw, dict):
                for code, info in raw.items():
                    kline = info.get("kline") or info.get("rows") or []
                    cache[code] = {"name": info.get("name", code), "rows": _slim(kline)}
            if cache:
                codes = list(cache.keys())
                print(f"  🎯 重建门控采用 TOP800 池（kline_raw.json）：{len(codes)} 只，K 线直接复用（免重拉）")
                return cache, codes
        except Exception as e:
            print(f"  ⚠️ 读取 kline_raw.json 失败，回退旧路径: {e}")
    # 回退路径：从 KLINE_CACHE / fetch_kline 拉取（旧 64 只候选池逻辑）
    cache = {}
    if os.path.exists(KLINE_CACHE) and not force_fetch:
        try:
            cache = json.load(open(KLINE_CACHE, encoding="utf-8"))
            print(f"  📂 已加载 K 线缓存：{len(cache)} 只")
        except Exception:
            cache = {}
    if os.path.exists(POOL_PATH):
        codes = json.load(open(POOL_PATH, encoding="utf-8"))
        print(f"  🔒 回退 candidate_pool.json：{len(codes)} 只")
    else:
        codes = list(cache.keys())
    need = [c for c in codes if c not in cache or len(cache[c].get("rows", [])) < 100]
    if need:
        print(f"  🌐 需拉取 {len(need)} 只候选股 K 线（250日）...")
        for i, code in enumerate(need):
            for attempt in range(3):
                try:
                    name, rows = fetch_kline(code, 250)
                    cache[code] = {"name": name, "rows": rows}
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"    ⚠️ {code} 拉取失败: {e}")
                    time.sleep(1.0)
            if (i + 1) % 10 == 0:
                print(f"    进度 {i + 1}/{len(need)}")
            time.sleep(0.12)
        json.dump(cache, open(KLINE_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  💾 K 线缓存已写入 {KLINE_CACHE}（{len(cache)} 只）")
    return cache, codes


# ──────────────────────────────────────────────────────────────
# 构建 20 日历史快照
# ──────────────────────────────────────────────────────────────
def build_history(keep_days=20, force_fetch=False):
    pool_kline, codes = load_pool_kline(force_fetch=force_fetch)

    # 全市场交易日并集
    all_dates = set()
    for d in pool_kline.values():
        for r in d.get("rows", []):
            all_dates.add(r["date"])
    trading_days = sorted(all_dates)[-keep_days:]
    print(f"  📅 最近 {keep_days} 个交易日：{trading_days[0]} … {trading_days[-1]}")

    snapshots = {}
    for D in trading_days:
        d0 = datetime.datetime.strptime(D, "%Y-%m-%d").date()
        snap = {}
        for code in codes:
            d = pool_kline.get(code)
            if not d:
                continue
            rows = [r for r in d["rows"] if r["date"] <= D]
            if len(rows) < 60:
                continue
            try:
                res = analyze(rows)
            except Exception:
                continue
            prim, sig_date = _primary_of(res)
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
        print(f"    {D}: 金钻池 {len(snap)} 只")

    history = {
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pool_size": len(codes),
        "keep_days": keep_days,
        "trading_days": trading_days,
        "snapshots": snapshots,
    }
    json.dump(history, open(HISTORY_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ 数据仓库已写入 {HISTORY_PATH}（{len(trading_days)} 个交易日）")
    return history


# ──────────────────────────────────────────────────────────────
# 每日追加（盘后）
# ──────────────────────────────────────────────────────────────
def append_today(keep_days=20):
    if not os.path.exists(TODAY_JSON):
        print(f"  ❌ 未找到 {TODAY_JSON}，请先运行 golden_diamond_scan.py")
        return None
    today = json.load(open(TODAY_JSON, encoding="utf-8"))
    data_date = today.get("data_date")
    if not data_date:
        print("  ❌ golden_diamond.json 缺少 data_date")
        return None

    snap = {}
    for st in today.get("stocks", []):
        code = st.get("code")
        if not code:
            continue
        prim, sig_date = _primary_of_from_signals(st.get("signals", []))
        if not prim:
            continue
        # 天→日，与 signals.json / 兜宝金钻 tab 显示保持一致
        if "天" in prim and "日" not in prim:
            prim = prim.replace("天", "日")
        days_ago = None
        if sig_date:
            try:
                days_ago = (datetime.datetime.strptime(data_date, "%Y-%m-%d").date()
                            - datetime.datetime.strptime(sig_date, "%Y-%m-%d").date()).days
            except Exception:
                days_ago = None
        snap[code] = {
            "name": st.get("name", code),
            "primary": prim,
            "signal_date": sig_date,
            "days_ago": days_ago,
        }

    # 读取既有历史
    history = {"snapshots": {}, "trading_days": []}
    if os.path.exists(HISTORY_PATH):
        history = json.load(open(HISTORY_PATH, encoding="utf-8"))
    history.setdefault("snapshots", {})
    history.setdefault("trading_days", [])
    history["snapshots"][data_date] = snap
    # 滚动裁剪到最近 keep_days
    all_days = sorted(history["snapshots"].keys())
    if len(all_days) > keep_days:
        for old in all_days[:-keep_days]:
            history["snapshots"].pop(old, None)
        all_days = all_days[-keep_days:]
    history["trading_days"] = all_days
    history["built_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    history["pool_size"] = max(history.get("pool_size", 0), len(snap))
    history["keep_days"] = keep_days

    # 自动补缺：检查最近 5 个交易日是否都进入了 trading_days，缺失的插入空 snap
    # 解决 cron 偶发漏触发导致日期跳断（如 08-11 漏过了 08-10→08-12 跳过一天）
    all_days_sorted = sorted(history["snapshots"].keys())
    if len(all_days_sorted) >= 2:
        from market_calendar import is_trading_day
        import datetime as _dt_b
        latest = all_days_sorted[-1]
        d0 = _dt_b.datetime.strptime(latest, "%Y-%m-%d").date()
        # 回看 5 个交易日，找出缺失
        for back in range(1, 6):
            check_date = (d0 - _dt_b.timedelta(days=back)).strftime("%Y-%m-%d")
            if is_trading_day(check_date) and check_date not in history["snapshots"]:
                history["snapshots"][check_date] = {}
                print(f"  🩹 自动补缺: {check_date}（cron 漏触发，插入空快照）")
        # 重新排序
        all_days_sorted = sorted(history["snapshots"].keys())

    json.dump(history, open(HISTORY_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ 已追加 {data_date} 金钻池快照（{len(snap)} 只），保留 {len(all_days_sorted)} 个交易日")
    return history


def _primary_of_from_signals(signals):
    best = None
    best_rank = -1
    best_date = None
    for s in signals:
        t = s.get("type", "")
        r = _rank(t)
        if r > best_rank:
            best_rank = r
            best = t
            best_date = s.get("date")
    return (best or ""), best_date


def main():
    args = sys.argv[1:]
    keep = 20
    force = False
    mode = "build"
    for a in args:
        if a == "--build":
            mode = "build"
        elif a == "--append":
            mode = "append"
        elif a.startswith("--days="):
            keep = int(a.split("=")[1])
        elif a == "--force-fetch":
            force = True

    print("═══ 兜宝金钻 · 金钻池数据仓库 ═══")
    if mode == "append":
        append_today(keep_days=keep)
    else:
        build_history(keep_days=keep, force_fetch=force)


if __name__ == "__main__":
    main()
