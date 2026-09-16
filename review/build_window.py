#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""信息窗口构建器 —— 「每日复盘 / 推演」的信息窗口契约唯一权威（方案 A）
=========================================================================

用户口径（2026-09-16 拍板）：
  · **次日推演 = 前一收盘日的全部信息 + 当天盘前增量**
  · **跨周末 = 周五收盘 + 周六周日自动补齐 + 周一盘前** → 综合推演
  · **span 一律按北京时间日历日计**；「美东 T 日收盘」归入其**北京到达日 T+1**
  · **不早于「不早于」**：`next_trading_day` 含当日，取下一交易日须 +1 天

三层结构
--------
  L2 承接层 carry  —— 复盘基准日那份「收盘复盘」的冻结结论（prediction / ai_synthesis）
  L1 基准层 base   —— 复盘日 T 的收盘全套（行情·资金流·龙虎榜·门控·金钻·TOP10·温度计）
  L0 增量层 delta  —— `span = [T+1 … for_date]` 内**每一个日历日**的增量（隔夜美股/今早日韩/
                      商品汇率/当日新闻/当日投喂/当日研报/周末全部产出），连续无洞

窗口 = carry ∪ base ∪ delta

产出（**双写** root `output/` 与 `deploy/output/`，V3 线上以 deploy 为根）
-----------------------------------------------------------------------
  output/window_latest.json          当前窗口契约（所有页面/脚本读它）
  output/window_<for_date>.json      按指引日归档
  output/window_summary.md           人读摘要（可直接贴简报）

用法
----
  python3 review/build_window.py                      # 按当前时刻自动判定 session
  python3 review/build_window.py --session preopen    # 盘前：for_date=今天(交易日) span=[T+1…今天]
  python3 review/build_window.py --session close      # 收盘：data_date=今天 span=[T+1]
  python3 review/build_window.py --at "2026-09-21 08:50"   # 模拟时点（验证跨周末剧本，不落盘用 --dry-run）
  python3 review/build_window.py --dry-run            # 只打印，不写盘

退出码：0 正常 / 1 存在 missing（仍写盘，供页面红字提示）
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from market_calendar import is_trading_day, last_trading_day, next_trading_day  # noqa: E402

OUT_DIR = os.path.join(BASE, "output")
DEPLOY_OUT = os.path.join(BASE, "deploy", "output")
FEED_INDEX = os.path.join(BASE, "feed", "archive", "feed_index.json")
MAHORO_INDEX = os.path.expanduser("~/Library/Application Support/goldenstock/feed_mahoro/index.json")
MARKET = os.path.join(BASE, "data", "daily_review", "market.json")

WEEKDAY_CN = "一二三四五六日"

# 基准层（L1）快照型产物：值 < data_date 即视为「滞后的基准读数」
BASE_SNAPSHOTS = [
    ("market.json",            os.path.join(MARKET),                       "date"),
    ("signals.json",           os.path.join(BASE, "signals.json"),         "data_date"),
    ("gate_data.json",         os.path.join(OUT_DIR, "gate_data.json"),    "data_date"),
    ("golden_diamond.json",    os.path.join(OUT_DIR, "golden_diamond.json"), "data_date"),
    ("market_thermometer.json", os.path.join(OUT_DIR, "market_thermometer.json"), "date"),
    ("obs_deduce.json",        os.path.join(OUT_DIR, "obs_deduce_latest.json"), "date"),
    ("valuation_band.json",    os.path.join(OUT_DIR, "valuation_band.json"), "date"),
]


# ── 基础工具 ────────────────────────────────────────────────
def load(p, default=None):
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def daterange(a: _dt.date, b: _dt.date):
    """[a, b] 内每一个日历日（含端点）。b < a 时返回空。"""
    out, cur = [], a
    while cur <= b:
        out.append(cur)
        cur += _dt.timedelta(days=1)
    return out


def resolve_dates(session: str, now: _dt.datetime):
    """返回 (data_date, for_date, note)。

    close：复盘基准日 = 今天（须为已收盘交易日）；指引日 = 其下一交易日
    其余：指引日 = 今天（交易日）或下一交易日；基准日 = 指引日之前最近交易日

    🔴 降级保护（防「生成日 ≠ 数据日」bug 家族）：close 模式下若基准层行情
       （`market.json.date`）尚未更新到今天（收盘补抓未完成），则基准日回退到
       **数据实际到位的那个交易日**，避免窗口「超前」把没抓到的数据算成 missing。
    """
    today = now.date()
    note = ""
    if session == "close":
        data_date = last_trading_day(today)
        md = str((load(MARKET) or {}).get("date") or "")[:10]
        prev = last_trading_day(today - _dt.timedelta(days=1))
        if md and data_date.isoformat() > md >= prev.isoformat():
            note = (f"基准层行情仅到 {md}（收盘补抓未完成）→ 基准日由 {data_date.isoformat()} "
                    f"回退为 {md}")
            data_date = _dt.date.fromisoformat(md)
        for_date = next_trading_day(data_date + _dt.timedelta(days=1))
    else:
        for_date = today if is_trading_day(today) else next_trading_day(today)
        data_date = last_trading_day(for_date - _dt.timedelta(days=1))
    return data_date, for_date, note


def auto_session(now: _dt.datetime) -> str:
    today = now.date()
    if not is_trading_day(today):
        return "nontrade"
    return "preopen" if now.time() < _dt.time(15, 30) else "close"


def build_carry(data_date: _dt.date, for_date: _dt.date) -> dict:
    """L2 承接层：复盘基准日那份收盘复盘的冻结结论。

    找不到基准日那份时，回退到**最近一份不晚于基准日**的 feed_review，并标 stale。
    """
    exact = os.path.join(OUT_DIR, f"feed_review_{data_date.isoformat()}.json")
    ref, used, stale = "output/feed_review_%s.json" % data_date.isoformat(), None, False
    if os.path.exists(exact):
        used = load(exact)
    else:
        cands = sorted(
            [f for f in os.listdir(OUT_DIR)
             if f.startswith("feed_review_") and f.endswith(".json") and f != "feed_review_latest.json"],
            reverse=True)
        for f in cands:
            d = f[len("feed_review_"):-len(".json")]
            if d <= data_date.isoformat():
                used = load(os.path.join(OUT_DIR, f))
                ref = "output/" + f
                stale = (d != data_date.isoformat())
                break

    carry = {
        "from_data_date": data_date.isoformat(),
        "ref": ref,
        "exists": bool(used),
        # 日历日差：本次指引日 距 复盘基准日（= 承接结论所属日）的天数。普通日=1、跨周末=3、长假=8
        "gap_days": (for_date - data_date).days,
        "stale": stale,
    }
    if used:
        pred = used.get("prediction") or {}
        synth = used.get("ai_synthesis") or {}
        carry.update({
            "bias": pred.get("bias"),
            "bias_score": pred.get("bias_score"),
            "t1_focus": (pred.get("t1_focus") or [])[:6],
            "risks": [r.get("desc") if isinstance(r, dict) else str(r)
                      for r in (pred.get("risks") or [])][:6],
            "headline": (synth.get("headline") or synth.get("summary")
                         or synth.get("one_liner") or "")[:160] if isinstance(synth, dict) else "",
        })
    return carry


def collect_covered(days, data_date: _dt.date):
    """统计窗口内**每一天**「日级可归属」来源：news / feeds / reports / macro。

    days 传**展示窗口**（含基准日）→ 基准日的素材也计入，避免「承接层含量」被漏算。
    """
    pool = load(os.path.join(OUT_DIR, "daily_news_window.json")) or {}
    by_day = pool.get("by_day") or {}
    idx = load(FEED_INDEX, {"entries": []}) or {"entries": []}
    mah = load(MAHORO_INDEX) or {}
    day_key = "date" if isinstance(mah, dict) and "date" in str(list(mah.keys())[:1]) else None

    feed_by_day, maha_by_day = {}, {}
    for e in idx.get("entries", []):
        feed_by_day.setdefault(e.get("date"), []).append(e)
    if isinstance(mah, dict):
        for k, v in (mah.get("items") or {}).items() if isinstance(mah.get("items"), dict) else []:
            pass
    # mahoro 索引结构随版本变化：只做「按 collected_date / date 字段」的宽松统计
    if isinstance(mah, dict):
        for k in ("items", "reports", "entries"):
            arr = mah.get(k)
            if isinstance(arr, list):
                for it in arr:
                    if not isinstance(it, dict):
                        continue
                    d = str(it.get("date") or it.get("collected_date") or it.get("published_at") or "")[:10]
                    if d:
                        maha_by_day.setdefault(d, []).append(it)

    covered = []
    for d in days:
        ds = d.isoformat()
        news_day = by_day.get(ds)
        if news_day is None:
            f = os.path.join(OUT_DIR, f"daily_news_{ds}.json")
            doc = load(f) or {}
            news_n = (doc.get("total") if doc else None)
            if news_n is None and doc:
                news_n = len(doc.get("news") or [])
        else:
            news_n = len(news_day) if isinstance(news_day, list) else (news_day or {}).get("total")
        covered.append({
            "date": ds,
            "weekday": "周" + WEEKDAY_CN[d.weekday()],
            "is_trading_day": is_trading_day(d),
            "news": news_n if news_n is not None else 0,
            "feeds": len(feed_by_day.get(ds, [])),
            "reports": len(maha_by_day.get(ds, [])),
            "macro": os.path.exists(os.path.join(OUT_DIR, f"daily_macro_{ds}.json")),
        })
    return covered, feed_by_day


def detect_missing(span, covered, data_date: _dt.date, for_date: _dt.date, carry: dict,
                   today: _dt.date | None = None):
    """缺口清单（诚实标注，禁静默）：bench 读数滞后 + 交易日无新闻 + 跨周末空窗。

    🔴 2026-09-16 修：`close` 窗口的 `span` 含**未来日**（如 9/16 收盘后 for_date=9/17）——
       未来日的数据「尚未到达」属正常，**不得判为缺口**（否则每天收盘后必然刷出一堆假缺口）。
    """
    today = today or _dt.date.today()
    ts = today.isoformat()
    missing = []
    span_s = {c["date"] for c in covered}

    # ① 基准层快照滞后
    for name, p, key in BASE_SNAPSHOTS:
        doc = load(p)
        if doc is None:
            missing.append(f"{name} 缺失（{os.path.relpath(p, BASE)} 不存在）")
            continue
        v = str(doc.get(key) or "")[:10]
        if not v:
            missing.append(f"{name} 无 {key} 字段（无法判定数据日）")
        elif v < data_date.isoformat():
            missing.append(f"{name} 数据日 {v} 落后于基准日 {data_date.isoformat()}")

    # ② 交易日无新闻（仅对**已到达**的日子判定；未来日豁免）
    for c in covered:
        if c["is_trading_day"] and c["news"] == 0 and c["date"] <= ts:
            missing.append(f"{c['date']}（{c['weekday']}·交易日）新闻池 0 条")

    # ③ 跨周末/长假空窗：非交易日全为 0 条 → 可能整池被覆盖（同样只看已到达的日子）
    if len(span) > 1:
        off = [c for c in covered if not c["is_trading_day"] and c["date"] <= ts]
        if off and all(c["news"] == 0 for c in off):
            missing.append(
                "窗口内非交易日（" + "、".join(c["date"][5:] for c in off) + "）新闻池全为 0 → "
                "疑整池被覆盖，跨周末信息可能丢失")

    # ④ 承接层不可用
    if not carry.get("exists"):
        missing.append(f"承接层缺失：{carry['ref']} 不存在（段 0.5 无法机器化复核）")
    elif carry.get("stale"):
        missing.append(f"承接层滞后：{carry['ref']} 非基准日 {data_date.isoformat()} 那份（回退使用）")

    return missing


def build(session: str = "", at: str = ""):
    now = _dt.datetime.fromisoformat(at) if at else _dt.datetime.now()
    session = session or auto_session(now)
    data_date, for_date, dnote = resolve_dates(session, now)
    span = daterange(data_date + _dt.timedelta(days=1), for_date)
    span_is_cross = any(not is_trading_day(d) for d in span)

    carry = build_carry(data_date, for_date)
    covered, _ = collect_covered(span, data_date)
    missing = detect_missing(span, covered, data_date, for_date, carry, today=now.date())

    mkt = load(MARKET) or {}
    us = (mkt.get("us_kline") or {})
    asia = (mkt.get("asia") or {})
    win = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "session": session,
        "data_date": data_date.isoformat(),
        "for_date": for_date.isoformat(),
        "data_date_note": dnote,
        "warnings": [dnote] if dnote else [],
        "span": [d.isoformat() for d in span],
        "span_days": len(span),
        # 展示窗口 = [基准日] ∪ span —— 「前一收盘日的全部信息 + 当天盘前增量」的落地口径：
        # 投喂 / 新闻池按**展示窗口**累积（基准日素材不能丢），span 只表示纯增量部分。
        "display_days": [data_date.isoformat()] + [d.isoformat() for d in span],
        "display_text": "%s%s" % (data_date.strftime("%m/%d"),
                                  ("–" + for_date.strftime("%m/%d")) if len(span) > 1 else
                                  (" + " + for_date.strftime("%m/%d"))),
        "span_is_weekend_cross": span_is_cross,
        "span_text": "%s%s" % (span[0].strftime("%m/%d") if span else "—",
                               ("–" + span[-1].strftime("%m/%d")) if len(span) > 1 else ""),
        "carry": carry,
        "layers": {
            "base": f"{data_date.isoformat()} A股收盘（基准层）",
            "overnight": f"美东 {data_date.isoformat()} 收盘（北京 {span[0].isoformat() if span else '—'} 早间到达）"
                         if span else "",
            "premarket": (f"{span[-1].isoformat()} 今早日韩实时 + 盘前新闻/投喂增量"
                          if span else ""),
        },
        "market_state": {
            "date": mkt.get("date"),
            "run_date": mkt.get("run_date"),
            "preopen_partial": mkt.get("preopen_partial"),
            "us_kline": bool(us),
            "asia": bool(asia),
        },
        "covered": covered,
        "totals": {
            "news": sum(c["news"] for c in covered),
            "feeds": sum(c["feeds"] for c in covered),
            "reports": sum(c["reports"] for c in covered),
            "covered_days": len(covered),
        },
        "missing": missing,
    }
    return win


def render_summary(win: dict) -> str:
    c = win["carry"]
    lines = [
        f"# 信息窗口 · {win['for_date']}（{win['session']}）",
        "",
        f"- **基准层**：{win['layers']['base']}",
        f"- **承接层**：{c['ref']}（{'在位' if c.get('exists') and not c.get('stale') else '滞回退' if c.get('exists') else '缺失'}）"
        + (f" · 倾向 {c.get('bias')}" if c.get("bias") else ""),
        f"- **增量层**：span {win['span_text']}（{win['span_days']} 天"
        + ("，跨非交易日" if win["span_is_weekend_cross"] else "") + "）",
        "",
        "| 日 | 周 | 交易日 | 新闻 | 投喂 | 研报 | 宏观 |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in win["covered"]:
        lines.append(f"| {x['date'][5:]} | {x['weekday'][1]} | {'✓' if x['is_trading_day'] else '—'} "
                     f"| {x['news']} | {x['feeds']} | {x['reports']} | {'✓' if x['macro'] else '—'} |")
    t = win["totals"]
    lines.append(f"\n**窗口合计**：新闻 {t['news']} 条 · 投喂 {t['feeds']} 条 · 研报 {t['reports']} 条\n")
    if win["missing"]:
        lines.append("## ⚠️ 缺口（禁静默，页面须红字提示）\n")
        lines += [f"- {m}" for m in win["missing"]]
    else:
        lines.append("## ✅ 缺口\n\n- 无")
    return "\n".join(lines) + "\n"


def write_all(win: dict, dry: bool = False):
    outs = [os.path.join(OUT_DIR, "window_latest.json"),
            os.path.join(OUT_DIR, f"window_{win['for_date']}.json")]
    if os.path.isdir(DEPLOY_OUT):
        outs += [os.path.join(DEPLOY_OUT, "window_latest.json"),
                 os.path.join(DEPLOY_OUT, f"window_{win['for_date']}.json")]
    if dry:
        print("（dry-run 不落盘）")
        return outs
    os.makedirs(OUT_DIR, exist_ok=True)
    txt = json.dumps(win, ensure_ascii=False, indent=2)
    for p in outs:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)
    p = os.path.join(OUT_DIR, "window_summary.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(render_summary(win))
    outs.append(p)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="", choices=["", "preopen", "close", "intraday", "nontrade"])
    ap.add_argument("--at", default="", help="模拟时点 'YYYY-MM-DD HH:MM'（验证跨周末/长假剧本）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    win = build(args.session, args.at)
    mode = "（模拟 " + args.at + "）" if args.at else ""
    print(f"═══ 信息窗口构建 {win['generated_at']}{mode} ═══")
    print(f"  session   : {win['session']}")
    print(f"  data_date : {win['data_date']}   （基准层 = 复盘日）")
    print(f"  for_date  : {win['for_date']}   （指引日）")
    print(f"  span      : {win['span_text']} · {win['span_days']} 天"
          + ("  ⚠️ 跨非交易日" if win["span_is_weekend_cross"] else ""))
    print(f"  显示窗口  : {win['display_text']}（{len(win['display_days'])} 天，含基准日）")
    c = win["carry"]
    print(f"  carry     : {c['ref']}  exists={c.get('exists')} stale={c.get('stale')} gap={c['gap_days']}d")
    for x in win["covered"]:
        print(f"     {x['date']} {x['weekday']} {'交易日' if x['is_trading_day'] else '非交易'} "
              f"· 新闻 {x['news']:>4} · 投喂 {x['feeds']:>2} · 研报 {x['reports']:>2} "
              f"· 宏观 {'✓' if x['macro'] else '—'}")
    if win["missing"]:
        print(f"  ⚠️ 缺口 {len(win['missing'])} 项：")
        for m in win["missing"]:
            print(f"     - {m}")
    else:
        print("  ✅ 无缺口")

    outs = write_all(win, dry=args.dry_run)
    for p in outs:
        print(f"💾 {os.path.relpath(p, BASE)}")
    return 1 if win["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
