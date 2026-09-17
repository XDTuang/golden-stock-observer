#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sector_tech.json 守卫（板块技术分析产物自检）

校验（任一 err 即退出码 1）：
  1. 产物存在且可解析；data_date 非空、非未来日
  2. 档位/趋势类型字面值 ⊆ 唯一权威集合（防「有枚举无对齐」）
  3. 🔴 **价格单调性**：support < 现价 < resistance（压力必在现价上方、支撑必在现价下方）
  4. 🔴 L4/L3 必须带**具体价位**（压力与支撑各 >=1 项，且为正数）——「无数字即红灯」
  5. summary / trend_dist 计数与 items 实际一致
  6. L1 行不得出现 L4/L3 档位；L4/L3 不得出现 trends=unknown
  7. thresholds 完整且与脚本常量一致
  8. 归档副本（deploy/output）与根副本 md5 一致
  9. 数据日新鲜度（warn，不阻断）：data_date < market.json 的 date 时提示

用法: python review/check_sector_tech.py
"""
import hashlib
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "output", "sector_tech.json")
P_DEPLOY = os.path.join(BASE, "deploy", "output", "sector_tech.json")
MARKET = os.path.join(BASE, "data", "daily_review", "market.json")

sys.path.insert(0, os.path.join(BASE, "review"))
try:
    from build_sector_tech import LEVELS, TREND_TYPES, PCT_L4, PCT_L3, STREAK_MIN, PCT_REVERSAL
    _AUTH = True
except Exception as e:
    print(f"  ⚠️ 无法导入 build_sector_tech 常量（{type(e).__name__}）→ 字面值校验降级为内置清单")
    LEVELS = ("L4", "L3", "L2", "L1")
    TREND_TYPES = ("uptrend", "uptrend_pullback", "downtrend_rebound", "downtrend", "unknown")
    _AUTH = False


def main():
    errs, warns = [], []
    print("═══ 守卫：sector_tech.json（板块技术分析）═══")

    if not os.path.exists(P):
        print("  ❌ output/sector_tech.json 不存在 → 先跑 review/build_sector_tech.py")
        sys.exit(1)
    try:
        d = json.load(open(P, encoding="utf-8"))
    except Exception as e:
        print(f"  ❌ 解析失败：{e}")
        sys.exit(1)

    # 1. 数据日
    dd = d.get("data_date") or ""
    if not dd:
        errs.append("data_date 为空")
    else:
        import datetime as _dt
        today = _dt.date.today().isoformat()
        if dd > today:
            errs.append(f"data_date={dd} 为未来日（今天 {today}）")
        mk = {}
        try:
            mk = json.load(open(MARKET, encoding="utf-8"))
        except Exception:
            pass
        if mk.get("date") and dd < mk["date"]:
            warns.append(f"data_date={dd} 落后于 market.json 的 date={mk['date']}（需重跑脚本）")
    if not d.get("generated_at"):
        warns.append("generated_at 缺失")

    # 2. 字面值
    items = d.get("items") or []
    if not items:
        errs.append("items 为空（无板块）")
    bad_lv = sorted({i.get("level") for i in items} - set(LEVELS))
    if bad_lv:
        errs.append(f"level 出现未定义字面值：{bad_lv}（权威={list(LEVELS)}）")
    bad_tr = sorted({i.get("trend") for i in items} - set(TREND_TYPES))
    if bad_tr:
        errs.append(f"trend 出现未定义字面值：{bad_tr}（权威={list(TREND_TYPES)}）")

    # 3+4. 价格单调性 / L4-L3 必带价位
    checked = 0
    for it in items:
        nm, lv = it.get("sector"), it.get("level")
        t = it.get("tech")
        if not t:
            if lv in ("L4", "L3"):
                errs.append(f"[{nm}] {lv} 但缺 tech（无技术面不得进 L4/L3）")
            continue
        c = t.get("close")
        resist, sup = t.get("resistance") or [], t.get("support") or []
        if c is None:
            errs.append(f"[{nm}] tech.close 缺失")
            continue
        for r in resist:
            if not (r.get("price") or 0) > c:
                errs.append(f"[{nm}] 压力位 {r.get('price')} 未高于现价 {c}（单调性违反）")
        for s in sup:
            if not 0 < (s.get("price") or 0) < c:
                errs.append(f"[{nm}] 支撑位 {s.get('price')} 未低于现价 {c}（单调性违反）")
        if lv in ("L4", "L3"):
            if not resist:
                errs.append(f"[{nm}] {lv} 但无压力位（须带具体价位）")
            if not sup:
                errs.append(f"[{nm}] {lv} 但无支撑位（须带具体价位）")
            if t.get("trend") == "unknown":
                errs.append(f"[{nm}] {lv} 但 trend=unknown")
        checked += 1

    # 5. 计数一致
    for lv, n in (d.get("summary") or {}).items():
        real = sum(1 for i in items if i.get("level") == lv)
        if n != real:
            errs.append(f"summary[{lv}]={n} ≠ items 实际 {real}")
    for tr, n in (d.get("trend_dist") or {}).items():
        real = sum(1 for i in items if i.get("trend") == tr)
        if n != real:
            errs.append(f"trend_dist[{tr}]={n} ≠ items 实际 {real}")

    # 6. 一致性
    l1 = [i for i in items if i.get("level") == "L1"]
    if any(i.get("flow_yi", 0) > 0 and i.get("verdict") not in ("背离", "双冷") for i in l1):
        warns.append("L1 中存在「资金净流入且四象限非背离/双冷」的行（请复核降级理由）")

    # 7. thresholds
    th = d.get("thresholds") or {}
    need = ("pct_L4", "pct_L3", "streak_min", "pct_reversal", "hot_per_day")
    miss = [k for k in need if k not in th]
    if miss:
        errs.append(f"thresholds 缺字段：{miss}")
    if _AUTH and th.get("pct_L4") != PCT_L4:
        errs.append(f"thresholds.pct_L4={th.get('pct_L4')} ≠ 脚本常量 {PCT_L4}（产物与代码不同步）")

    # 8. 副本一致
    if os.path.exists(P_DEPLOY):
        a = hashlib.md5(open(P, "rb").read()).hexdigest()
        b = hashlib.md5(open(P_DEPLOY, "rb").read()).hexdigest()
        if a != b:
            errs.append("deploy/output/sector_tech.json 与根副本 md5 不一致")
    else:
        warns.append("deploy/output/sector_tech.json 不存在（V3/线上会 404）")

    # 9. 页面呈现（7.1b 段 + CSS，2026-09-17 新增）
    #    生成式代码纪律：本段由 build_sector_tech.py 注入 → 须防「块缺失（段消失）」与「块重复（多次注入）」
    try:
        from build_sector_tech import SEC_BEGIN, SEC_END, CSS_BEGIN, CSS_END, INSERT_BEFORE
        sec_marks = (SEC_BEGIN, SEC_END, CSS_BEGIN, CSS_END)
    except Exception:
        sec_marks = ()
    if not sec_marks:
        warns.append("无法导入 7.1b 段标记常量 → 页面呈现校验降级跳过")
    else:
        for path, tag in ((os.path.join(BASE, "data", "daily_review", "analysis.html"), "根"),
                          (os.path.join(BASE, "deploy", "data", "daily_review", "analysis.html"), "deploy")):
            if not os.path.exists(path):
                errs.append(f"analysis.html（{tag}）不存在")
                continue
            t = open(path, encoding="utf-8").read()
            for mk, label in ((SEC_BEGIN, "段BEGIN"), (SEC_END, "段END"),
                              (CSS_BEGIN, "CSS-BEGIN"), (CSS_END, "CSS-END")):
                n = t.count(mk)
                if n != 1:
                    errs.append(f"analysis.html（{tag}）7.1b {label} 标记出现 {n} 次（须=1）")
            if t.count(SEC_BEGIN) == 1 and t.count(SEC_END) == 1:
                i, j = t.find(SEC_BEGIN), t.find(SEC_END)
                if not (0 < i < j):
                    errs.append(f"analysis.html（{tag}）7.1b 段标记顺序颠倒")
                # 位置断言：须在 7.1 标题之后、7.2 锚点之前
                h71, anchor = t.find(">7.1 ·"), t.find(INSERT_BEFORE)
                if not (0 < h71 < i and (anchor < 0 or i < anchor)):
                    errs.append(f"analysis.html（{tag}）7.1b 段位置异常（应在 7.1 之后、7.2 之前）")
        # 根 vs deploy md5
        pa = os.path.join(BASE, "data", "daily_review", "analysis.html")
        pb = os.path.join(BASE, "deploy", "data", "daily_review", "analysis.html")
        if os.path.exists(pa) and os.path.exists(pb):
            if hashlib.md5(open(pa, "rb").read()).hexdigest() != hashlib.md5(open(pb, "rb").read()).hexdigest():
                errs.append("analysis.html 根副本与 deploy 副本 md5 不一致")

    # 输出
    s = d.get("summary") or {}
    print(f"  数据日 {dd} ｜ 分级 " + " ".join(f"{k}={s.get(k, 0)}" for k in LEVELS))
    print(f"  趋势 " + " ｜ ".join(f"{k}={v}" for k, v in (d.get("trend_dist") or {}).items()))
    print(f"  校验板块 {checked}/{len(items)} ｜ 阈值 {th}")
    if d.get("missing"):
        print(f"  ⚠️ 产物内记录缺口 {len(d['missing'])} 项")
    for w in warns:
        print(f"  ⚠️ {w}")
    for e in errs:
        print(f"  ❌ {e}")
    ok = not errs
    print(f"\n{'✅' if ok else '❌'} sector_tech 守卫：{'通过' if ok else f'未通过（{len(errs)} 项）'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
