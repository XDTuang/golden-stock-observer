#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场温度计 / 估值趋势 / CBOE VIX 面板 守卫（2026-09-23 立）

为什么需要它
------------
2026-09-23 用户报「主站主页的市场温度计、全市场估值趋势、CBOE VIX 恐慌指数未正确自动更新」。
实查为两个独立缺陷：

① 🔴 **块解析互斥（代码缺陷，静默）**：`fetch_touzid_data.py` 的 main 原为
   `if VIX_ONLY: build_vix() / elif THERMO_ONLY: build_thermometer()` 链式判断 →
   同时传 `--thermo-only --vix-only` 时 **VIX 胜出、温度计整块不执行且不报错**。
   而云端 `daily-update`（update_data.sh 的 GITHUB_ACTIONS 分支）与本机盘前缺口补跑
   正是这条组合命令 → **温度计在云端与盘前永远补不上**：窗口缺口天天报、补跑天天
   "成功"、产物却停在上一交易日。**只比对日期是抓不住它的**（数据日期落后 1 天
   既可能是源滞后、也可能是没跑）→ 故本脚本第 ① 项为**行为级断言**。

② **VIX 源发布滞后**：CBOE `VIX_History.csv` 实测在美股收盘 3.5h 后仍未含当日
   （北京 09-23 07:32 末行仍是 09-21），而已有当日收盘的官方延时报价接口。
   已加兜底；本脚本第 ③ 项以 `market.json:us_kline.*.latest.date` 为美股锚做交叉校验。

判据纪律
--------
- ① 是**硬门禁**（代码契约，确定性）→ 失败必须修代码。
- ②③ 是**容差门禁**：数据源发布时点不由我们控制（乐咕当日行约在北京 07:30 后才出、
  CBOE CSV 更晚），故「落后 1 个交易日」记 ⚠️ 警告、**落后 ≥2 个交易日才判错**。
  这样夜间 22:00 链（源尚未发布当日）不会误伤，而「链路整段没跑」会被抓住。
  （本次 ① 的真实缺陷由第 ① 项硬拦，不依赖容差项。）

用法:  python3 review/check_touzid_panel.py [--verbose]
       退出码 1 = 有硬错（或 --strict 下的警告）
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
OUT = os.path.join(BASE, "output")
DEPLOY_OUT = os.path.join(BASE, "deploy", "output")
PY = sys.executable

THERMO = "market_thermometer.json"
VIX = "vix_panel.json"
MARKET = os.path.join(BASE, "data", "daily_review", "market.json")


def load(p):
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def last_closed_trading_day():
    """最近一个『已收盘』交易日（与 fetch_touzid_data.py::_data_date_str 同口径）。"""
    try:
        from market_calendar import is_trading_day, last_trading_day
        now = dt.datetime.now()
        d = now.date()
        if is_trading_day(d) and now.hour >= 15:
            return d
        return last_trading_day(d - dt.timedelta(days=1))
    except Exception:
        return dt.date.today()


def biz_days_between(a, b):
    """a → b 之间的交易日数（近似：按 A 股日历逐日数，b 早于 a 时为负）。"""
    try:
        from market_calendar import is_trading_day
    except Exception:
        return None
    if a == b:
        return 0
    sign = 1 if b > a else -1
    lo, hi = (a, b) if b > a else (b, a)
    n = 0
    d = lo
    while d < hi:
        d += dt.timedelta(days=1)
        if is_trading_day(d):
            n += 1
    return sign * n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--strict", action="store_true", help="把 ⚠️ 警告也当失败")
    args = ap.parse_args()

    # 错误按检查项独立归集：避免「有任何错误就把每项都标 ❌」的归因错误
    #（2026-09-23 反向测试揪出：原实现 [1/4] 的判据写成 `if not errs`，
    #  温度计出错时会把块解析项一并标红 —— 显示错项，比不显示更误导）
    E = {"blocks": [], "thermo": [], "vix": [], "dup": []}
    errs, warns = [], []

    def _all_errs():
        return E["blocks"] + E["thermo"] + E["vix"] + E["dup"]

    # ── ① 块解析（行为级）：--thermo-only --vix-only 必须两块都跑 ──
    cases = [
        (["--thermo-only", "--vix-only"], {"thermometer", "vix"}, "云端链 / 盘前缺口补跑"),
        (["--vix-only"], {"vix"}, "--vix-only"),
        ([], {"thermometer", "valuation", "vix"}, "默认全量"),
    ]
    for argv, want, label in cases:
        try:
            r = subprocess.run([PY, "fetch_touzid_data.py", *argv, "--list-blocks"],
                               cwd=BASE, capture_output=True, text=True, timeout=90)
            got = set((r.stdout or "").strip().splitlines()[-1].split(",")) if r.stdout.strip() else set()
        except Exception as e:
            E["blocks"].append(f"块解析调用失败（{label}）：{type(e).__name__}")
            continue
        if got != want:
            E["blocks"].append(
                f"🔴 块解析错误（{label}）：`--list-blocks {' '.join(argv)}` → {sorted(got) or '空'}，"
                f"应为 {sorted(want)} —— 这会静默跳过整块（2026-09-23 温度计不更新的根因）")

    # ── ② 温度计新鲜度 + 自洽 ──
    th = load(os.path.join(OUT, THERMO))
    if th is None:
        E["thermo"].append(f"{THERMO} 缺失或不可解析")
    else:
        date = str(th.get("date") or "")[:10]
        hist = th.get("history") or []
        snap = th.get("snapshot") or {}
        exp = last_closed_trading_day()
        if not date:
            E["thermo"].append(f"{THERMO} 无 date 字段")
        else:
            d = dt.date.fromisoformat(date)
            lag = biz_days_between(exp, d) or 0
            if lag <= -2:
                E["thermo"].append(f"温度计数据日 {date} 落后最近已收盘交易日 {exp} {abs(lag)} 个交易日 → 链路未跑或整块被跳过")
            elif lag == -1:
                warns.append(f"温度计数据日 {date} 落后 {exp} 1 个交易日（乐咕当日行约北京 07:30 后才发布：夜间档属正常，盘中档须复查）")
        if not hist:
            E["thermo"].append("温度计 history 为空")
        else:
            dates = [str(x.get("date"))[:10] for x in hist]
            if dates != sorted(dates):
                E["thermo"].append("温度计 history 未按日期升序（前端曲线会乱序）")
            if dates[-1] != date:
                E["thermo"].append(f"温度计自洽性：history 末条 {dates[-1]} ≠ 顶层 date {date}")
        if snap.get("date") and str(snap["date"])[:10] != date:
            E["thermo"].append(f"温度计自洽性：snapshot.date {snap['date']} ≠ 顶层 date {date}")

    # ── ③ VIX 面板：锚自洽 + 与美股 K 线交叉校验 ──
    vx = load(os.path.join(OUT, VIX))
    if vx is None:
        E["vix"].append(f"{VIX} 缺失或不可解析")
    else:
        vdate = str(vx.get("date") or "")[:10]
        cv = vx.get("cboe_vix") or {}
        cdate = str(cv.get("date") or "")[:10]
        a_anchor, us_anchor = str(vx.get("a_anchor") or "")[:10], str(vx.get("us_anchor") or "")[:10]
        if not vdate:
            E["vix"].append(f"{VIX} 无 date 字段")
        if not cdate:
            E["vix"].append("vix_panel.cboe_vix.date 缺失（CBOE CSV 与延时报价兜底均失败？）")
        if a_anchor and us_anchor and vdate != max(a_anchor, us_anchor):
            E["vix"].append(f"vix_panel 锚不自洽：date {vdate} ≠ max(a {a_anchor}, us {us_anchor})")
        h = vx.get("vix_history") or []
        if not h:
            E["vix"].append("vix_history 为空（近1年曲线无数据）")
        else:
            hd = [str(x.get("date"))[:10] for x in h]
            if hd != sorted(hd):
                E["vix"].append("vix_history 未按日期升序")
            if cdate and hd[-1] != cdate:
                E["vix"].append(f"vix 自洽性：vix_history 末条 {hd[-1]} ≠ cboe_vix.date {cdate}")

        # 精确判据（首选）：直接探 CBOE 官方延时报价 ——
        # 若官方**已发布**某日收盘（结算时刻 16:15 已过）而产物 date 仍早于它，
        # 说明「兜底未生效 / vix 块没跑」属实。这比用 us_kline 推断更准确
        # （反向测试实测：用 us_kline 只算出 1 个交易日差，落在容差内会漏判）。
        _probe = None
        try:
            import requests
            _r = requests.get("https://cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json",
                              timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            _qd = (_r.json() or {}).get("data") or {}
            _lt = str(_qd.get("last_trade_time") or "")
            if _lt[:10] and _lt[11:16] >= "16:15":
                _probe = (_lt[:10], _qd.get("current_price"), _lt)
        except Exception as e:
            warns.append(f"CBOE 官方报价探测失败（{type(e).__name__}）→ VIX 新鲜度改按容差判定")

        if _probe and cdate and cdate < _probe[0]:
            E["vix"].append(
                f"🔴 CBOE 官方已发布 {_probe[0]} 收盘 {_probe[1]}（结算 {_probe[2]}），"
                f"而产物 cboe_vix.date={cdate} → 延时报价兜底未生效或 vix 块未跑"
                f"（用户可见症状：页面「CBOE VIX 恐慌指数」停在上一交易日）")

        # 容差判据（兜底）：官方不可达时，用 market.json 的美股 K 线做交叉校验
        mkt = load(MARKET) or {}
        us_dates = []
        for k, v in (mkt.get("us_kline") or {}).items():
            ld = str(((v or {}).get("latest") or {}).get("date") or "")[:10]
            if ld:
                us_dates.append(ld)
        if not _probe and us_dates and cdate:
            us_latest = max(us_dates)
            if cdate < us_latest:
                lag = biz_days_between(dt.date.fromisoformat(cdate), dt.date.fromisoformat(us_latest))
                msg = (f"CBOE VIX 数据日 {cdate} 落后美股 K 线最新 {us_latest}"
                       f"（{lag} 个交易日）→ 延时报价兜底未生效或 vix 块未跑")
                (E["vix"] if (lag or 0) >= 2 else warns).append(msg)
        elif not _probe and not us_dates:
            warns.append("market.json 无 us_kline 最新日 → 跳过 VIX 与美股锚的交叉校验")

    # ── ④ root / deploy 双写一致 ──
    for name in (THERMO, VIX):
        a, b = os.path.join(OUT, name), os.path.join(DEPLOY_OUT, name)
        if not os.path.exists(b):
            E["dup"].append(f"deploy/output/{name} 不存在（线上会 404）")
        elif hashlib.md5(open(a, "rb").read()).hexdigest() != hashlib.md5(open(b, "rb").read()).hexdigest():
            E["dup"].append(f"{name} 根副本与 deploy 副本 md5 不一致（漏 cp / 只跑了一半）")

    # ── 输出 ──
    exp = last_closed_trading_day()
    print("═══ touzid 面板守卫（温度计 / 估值趋势 / CBOE VIX）═══")
    print(f"  基准：最近已收盘交易日 {exp}")
    if th:
        print(f"  温度计   date={th.get('date')} · history {len(th.get('history') or [])} 条")
    if vx:
        print(f"  VIX 面板 date={vx.get('date')} · CBOE {((vx.get('cboe_vix') or {}).get('date'))}"
              f" · 源={((vx.get('cboe_vix') or {}).get('source'))}")
    print()
    print(f"{'✅' if not E['blocks'] else '❌'} [1/4] 块解析（--thermo-only --vix-only 必须两块都跑）")
    print(f"{'✅' if not E['thermo'] else '❌'} [2/4] 温度计新鲜度与自洽")
    print(f"{'✅' if not E['vix'] else '❌'} [3/4] VIX 面板锚与美股交叉校验")
    print(f"{'✅' if not E['dup'] else '❌'} [4/4] root / deploy 双写一致")
    if warns:
        print()
        for w in warns:
            print(f"  ⚠️ {w}")
    all_errs = _all_errs()
    if all_errs:
        print()
        for e in all_errs:
            print(f"  ❌ {e}")
    ok = not all_errs and not (args.strict and warns)
    print()
    print(f"{'✅ touzid 面板守卫通过' if ok else '❌ touzid 面板守卫未通过'}"
          f"（硬错 {len(all_errs)} · 警告 {len(warns)}）")
    if not ok:
        print("   → 修法：① 块解析错 → 修 fetch_touzid_data.py 的 _resolve_blocks()；"
              "② 日期滞后 → 跑 `python3 fetch_touzid_data.py --thermo-only --vix-only`")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
