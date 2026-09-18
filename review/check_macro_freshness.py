#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观日志时效守卫（每日复盘 4 段「宏观日志」）
===========================================================================
背景（2026-09-18 立）:
  用户报障：4 段「美国宏观（新闻源抽取）」长期显示过期信息 —— 实测抽到
  8/13 的「7月CPI」与 7/3 的「6月非农」，而 9/11 公布的 8 月 CPI（3.4%）
  与 9/4 公布的 8 月非农（16.2 万）全被漏掉。
  根因：新闻源 stock_info_cjzc_em 返回 400 条历史（回溯至 2025-01），
  抽取侧无时间窗 → 「有值但永远旧」的静默冻结（改版自检第九节家族）。

守卫内容（任一不通过 → 退出码 1）:
  [1] 产物存在且 date/generated_at 齐备
  [2] 轨A（经济日历）非空，且**关键月频指标**（CPI 同比 / 非农）必须在位
  [3] 轨A 各指标龄期 ≤ 其频率上限（月频 40 天 / 周频 14 天 / 日频 7 天）
  [4] 轨B（新闻抽取）每条龄期 ≤ US_NEWS_WINDOW_DAYS（7 天）—— 窗口失效即红灯
  [5] 「未更新」指标必须在 stale 列表显式登记（禁拿旧闻充数）
  [6] 根 output 与 deploy/output 双写 md5 一致

用法:
  python review/check_macro_freshness.py          # 校验（红灯退出码 1）
  python review/check_macro_freshness.py -v       # 打印全部指标明细
"""
import os, sys, json, hashlib, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["output/daily_macro_latest.json", "deploy/output/daily_macro_latest.json"]

FRESH_WINDOW_DAYS = 7          # 新闻轨窗口（须与 fetch_daily_macro.py 一致）
# 指标 → 频率上限（天）。月频留 40 天余量（间隔约 30 天 + 调度抖动）
MAX_AGE = {
    "CPI 同比": 40, "核心 CPI": 40, "CPI 月率": 40, "核心CPI月率": 40,
    "非农": 40, "失业率": 40, "ADP 就业": 40, "核心 PCE": 40,
    "GDP": 100, "零售销售": 40, "ISM 制造业": 40, "利率决议": 60,
    "初请失业金": 14,          # 周频
}
KEY_INDICATORS = ["CPI 同比", "非农"]     # 缺一即红灯（覆盖两大最重要月频数据）


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def main():
    verbose = "-v" in sys.argv
    errs, warns, notes = [], [], []
    today = datetime.date.today()

    p = os.path.join(BASE, FILES[0])
    if not os.path.exists(p):
        print(f"❌ [0/6] 产物不存在: {FILES[0]}")
        return 1
    d = json.load(open(p, encoding="utf-8"))

    # ── [1] 基本字段 ──
    ok1 = bool(d.get("date")) and bool(d.get("generated_at"))
    if not ok1:
        errs.append("缺 date / generated_at")
    print(f"{'✅' if ok1 else '❌'} [1/6] 产物基本字段（date={d.get('date')} · generated_at={d.get('generated_at')}）")

    us = d.get("us") or {}
    cal = (us.get("calendar") or {}).get("indicators") or {}

    # ── [2] 轨A 非空 + 关键指标在位 ──
    missing_key = [k for k in KEY_INDICATORS if k not in cal]
    ok2 = bool(cal) and not missing_key
    if not cal:
        errs.append("轨A（经济日历）为空 —— 主源失效未降级标注？")
    if missing_key:
        errs.append(f"关键月频指标缺失: {missing_key}")
    print(f"{'✅' if ok2 else '❌'} [2/6] 轨A 关键指标在位（共 {len(cal)} 指标；缺 {missing_key or '无'}）")
    if cal and not us.get("stale") and not (us.get("indicators") or {}):
        warns.append("轨A 有数据但轨B 与 stale 皆空 —— 请确认新闻抽取是否真的执行")

    # ── [3] 轨A 龄期 ──
    ok3, over = True, []
    for k, items in cal.items():
        lim = MAX_AGE.get(k, 40)
        for it in items:
            age = it.get("days_ago")
            if age is None:
                over.append(f"{k}(无龄期字段)")
                continue
            if age > lim:
                over.append(f"{k}({age}天 > {lim}天)")
                ok3 = False
    if over:
        errs.extend(over)
    print(f"{'✅' if ok3 else '❌'} [3/6] 轨A 龄期合规（上限：月频 40 / 周频 14 天）"
          + (f" — 超标 {over}" if over else ""))

    # ── [4] 轨B 窗口 ──
    ind = us.get("indicators") or {}
    ok4, bad_b = True, []
    for k, items in ind.items():
        for it in items:
            age = it.get("days_ago")
            if age is None or age > FRESH_WINDOW_DAYS:
                bad_b.append(f"{k}({age}天)")
                ok4 = False
    if bad_b:
        errs.append(f"轨B 出现超窗口条目（>{FRESH_WINDOW_DAYS}天）: {bad_b}")
    print(f"{'✅' if ok4 else '❌'} [4/6] 轨B 时效窗口 ≤ {FRESH_WINDOW_DAYS} 天（{len(ind)} 指标）"
          + (f" — 超标 {bad_b}" if bad_b else ""))

    # ── [5] stale 自洽性 ──
    #   注意：轨A（日历标签，如「GDP」「核心 PCE」）与轨B（新闻关键词，如「美国GDP」）
    #   命名口径不同，故**不做跨轨差集比对**（会产出无意义告警 —— 2026-09-18 实测）。
    #   只断言同一轨内的自相矛盾：某指标既被标「未更新」又有数据。
    stale = us.get("stale") or []
    conflict = [k for k in stale if k in ind]
    ok5 = not conflict
    if conflict:
        errs.append(f"stale 与 indicators 自相矛盾（同指标既有数据又标未更新）: {conflict}")
    print(f"{'✅' if ok5 else '❌'} [5/6] 指标登记自洽（calendar {len(cal)} · 新闻 {len(ind)} · stale {len(stale)}"
          + (f" — 冲突 {conflict}" if conflict else "）"))

    # ── [6] 双写一致 ──
    pa, pb = os.path.join(BASE, FILES[0]), os.path.join(BASE, FILES[1])
    if not os.path.exists(pb):
        ok6 = False
        errs.append(f"deploy 副本缺失: {FILES[1]}")
        detail = "deploy 缺"
    else:
        ha, hb = md5(pa), md5(pb)
        ok6 = ha == hb
        detail = f"{ha[:8]} vs {hb[:8]}"
        if not ok6:
            errs.append("根 output 与 deploy/output 不一致（须 cp 同步）")
    print(f"{'✅' if ok6 else '❌'} [6/6] 双写一致（{detail}）")

    if verbose:
        print("\n── 轨A 明细 ──")
        for k, items in cal.items():
            for it in items:
                print(f"  {k:12s} {it.get('value',''):>8s} · {it.get('release_date')} · "
                      f"{it.get('days_ago')} 天前 · 重要性 {it.get('importance')}")
        print("── 轨B 明细 ──")
        for k, items in ind.items():
            for it in items:
                print(f"  {k:12s} {it.get('days_ago')} 天前 · {(it.get('evidence') or [''])[0][:60]}")
        if stale:
            print(f"── 未更新（stale）──\n  {', '.join(stale)}")

    print()
    for w in warns:
        print(f"⚠️  {w}")
    if errs:
        print(f"\n❌ 宏观时效守卫未通过（{len(errs)} 项）：")
        for e in errs:
            print(f"   · {e}")
        return 1
    print("✅ 宏观时效守卫全部通过（6/6）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
