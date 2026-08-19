#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜宝金钻 · 每日选股扫描（三子形态）
=====================================
锁定策略（与 golden_diamond_viewer 验证版完全一致）：
  - 买入 (XG)            —— 时间窗口：最新交易日含当日，连续前5个交易日内任意一天
  - 金钻起涨 (XG2)       —— 同上
  - 红区黄柱连续 (≥3天)  —— 最近5日窗口内连续≥3天
                           红区 = 金钻趋势>金牛2；黄柱 = 金钻趋势>LOW×1.025

实现：直接复用 golden_diamond_viewer/server.py 的 analyze()（唯一经实盘校验的真值源），
      避免逻辑漂移。遍历 fetch_pool 已拉取的 output/kline_raw.json（不额外消耗 API 配额）。

产出 output/golden_diamond.json：
  {
    data_date, updated_at,
    overview: { total, buy, up, hz, analysis },
    stocks: [ {code,name,market,primary,signals,kline,golden_bull,golden_trend,gt2,red_zone,yellow_bar} ]
  }

用法:
  python golden_diamond_scan.py                 # 扫描并写 output/golden_diamond.json
  python golden_diamond_scan.py --dry-run       # 仅统计命中数，不写文件
"""
import os
import sys
import json
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
KLINE_RAW = os.path.join(BASE, "output", "kline_raw.json")
OUT = os.path.join(BASE, "output", "golden_diamond.json")

# ── 复用验证版分析引擎（唯一真值源）──
sys.path.insert(0, os.path.join(BASE, "golden_diamond_viewer"))
from server import analyze  # noqa: E402  仅导入，不会触发 __main__ 的 HTTP 服务

# 三子形态优先级（同一只同时命中多个时取主类型）
RANK = {"金钻起涨": 3, "买入": 2, "红区黄柱连续": 1}


def _primary(signals: list) -> str:
    if not signals:
        return ""
    best = None
    best_rank = -1
    for s in signals:
        t = s.get("type", "")
        # 红区黄柱连续 前缀匹配
        r = RANK.get(t, RANK.get("红区黄柱连续") if t.startswith("红区黄柱连续") else 0)
        if r > best_rank:
            best_rank = r
            best = t
    return best or ""


def _slim(rows):
    """kline_raw 的 last→close 映射，并保留 OHLCV 供主图渲染。"""
    out = []
    for r in rows:
        out.append({
            "date": r.get("date"),
            "open": round(float(r.get("open", 0)), 2),
            "close": round(float(r.get("last", r.get("close", 0))), 2),
            "high": round(float(r.get("high", 0)), 2),
            "low": round(float(r.get("low", 0)), 2),
            "volume": round(float(r.get("volume", 0)), 2),
        })
    return out


def _round_arr(arr, nd=3):
    return [None if x is None else round(float(x), nd) for x in arr]


def scan(dry_run=False):
    if not os.path.exists(KLINE_RAW):
        print(f"  ❌ 未找到 {KLINE_RAW}，请先运行 fetch_pool.py")
        return None

    with open(KLINE_RAW, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # ── K线新鲜度自检：kline_raw 最新交易日（防 19:59/20:11 时序错位 → 伪 0 命中）──
    from market_calendar import last_trading_day  # noqa: 本地模块，非外部数据源
    try:
        _latest_in_raw = sorted({
            (stock.get("kline") or [{}])[-1].get("date", "")
            for stock in raw if (stock.get("kline") or [])
        }, reverse=True)
        _raw_date = _latest_in_raw[0] if _latest_in_raw else ""
        _expected = str(last_trading_day())
        if _raw_date != _expected:
            print(f"  ⚠️  K线新鲜度警告: kline_raw 最新日期={_raw_date}（期望 {_expected}）")
            print(f"     —— 上次 fetch_pool 可能未完整刷新 K线，金钻扫描结果将基于不完整数据！")
            if not dry_run:
                print("  ⚠️  建议先重跑 fetch_pool.py 再扫描（update_data.sh 已强制顺序）")
    except Exception as _e:
        print(f"  ⚠️  新鲜度自检跳过: {_e}")

    # ── 扫描宇宙：与主站“stock”信号池保持一致（2026-07-14 起生效）──
    # 用户要求 diamond 当前门控采用与主站股票池门控一致的策略：
    # 主站 data_pipeline.py 对 fetch_pool 拉取的「成交额 TOP-800」全量扫描，
    # 此处同样扫描完整 kline_raw.json（TOP800），不再冻结 candidate_pool.json，
    # 使 diamond 当前门控的候选池范围与主站逐只对齐、策略一致。
    # （注：金钻三子形态分析引擎 server.analyze 保持不变，仅候选池范围放开。）
    print(f"  📦 候选池（成交额 TOP-800 全量）: {len(raw)} 只，开始金钻三子形态扫描...")

    hits = []
    for stock in raw:
        code = stock.get("code")
        name = stock.get("name", code)
        market = stock.get("market", "")
        kline = stock.get("kline") or []
        if len(kline) < 60:
            continue
        rows = _slim(kline)
        try:
            res = analyze(rows)
        except Exception as e:
            continue
        if not res.get("signals"):
            continue
        # 仅保留最近五日窗口内的买入/金钻起涨（analyze 已按此窗口产出）；红区黄柱连续也保留
        entry = {
            "code": code,
            "name": name,
            "market": market,
            "primary": _primary(res["signals"]),
            "signals": res["signals"],
            "kline": rows,
            "golden_bull": _round_arr(res["golden_bull"]),
            "golden_trend": _round_arr(res["golden_trend"]),
            "gt2": _round_arr(res["gt2"]),
            "red_zone": res["red_zone"],
            "yellow_bar": res["yellow_bar"],
            "count": res["count"],
            "last_date": rows[-1]["date"] if rows else "",
        }
        hits.append(entry)

    # 排序：金钻起涨 > 买入 > 红区黄柱连续；同类型按代码
    hits.sort(key=lambda e: (-RANK.get(e["primary"], 1), e["code"]))

    # 总览统计
    buy = sum(1 for e in hits if e["primary"] == "买入")
    up = sum(1 for e in hits if e["primary"] == "金钻起涨")
    hz = sum(1 for e in hits if e["primary"].startswith("红区黄柱连续"))
    total = len(hits)
    data_date = hits[0]["last_date"] if hits else ""
    if not data_date and raw:
        # 0 命中时兜底：取 kline_raw 最新交易日，避免 overview.data_date 显示空串
        try:
            data_date = sorted({
                (stock.get("kline") or [{}])[-1].get("date", "")
                for stock in raw if (stock.get("kline") or [])
            }, reverse=True)[0]
        except Exception:
            pass

    analysis = _make_analysis(total, up, buy, hz, data_date)

    overview = {
        "total": total, "buy": buy, "up": up, "hz": hz,
        "data_date": data_date,
        "analysis": analysis,
    }

    result = {
        "data_date": data_date,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "overview": overview,
        "stocks": hits,
    }

    if dry_run:
        print(f"  ✓ [dry-run] 命中 {total} 只 | 金钻起涨 {up} / 买入 {buy} / 红区黄柱连续 {hz}")
        return result

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    size_kb = os.path.getsize(OUT) / 1024
    print(f"  ✓ 已写入 {OUT} ({size_kb:.0f} KB)")
    print(f"  ✓ 命中 {total} 只 | 金钻起涨 {up} / 买入 {buy} / 红区黄柱连续 {hz}")
    return result


def _make_analysis(total, up, buy, hz, data_date):
    if total == 0:
        return f"{data_date} 金钻三子形态暂无命中，市场处震荡筑底阶段，建议观望。"
    parts = []
    parts.append(f"{data_date} 金钻策略共命中 {total} 只个股（基于成交额 TOP 池扫描）。")
    if up:
        parts.append(f"其中「金钻起涨」{up} 只，为强势启动信号，资金面（DY2）与量价配合达标，可优先跟踪；")
    if buy:
        parts.append(f"「买入」{buy} 只，属回调结束、金钻趋势上穿高位后的回补买点；")
    if hz:
        parts.append(f"「红区黄柱连续」{hz} 只，处红区（金钻趋势>金牛2）且连续筑底企稳，偏蓄势待发。")
    parts.append("提示：金钻为技术共振信号，须结合大盘环境与个股基本面，勿单一依赖。")
    return "".join(parts)


def main():
    dry = "--dry-run" in sys.argv
    print("═══ 兜宝金钻 · 每日选股扫描 ═══")
    scan(dry_run=dry)


if __name__ == "__main__":
    main()
