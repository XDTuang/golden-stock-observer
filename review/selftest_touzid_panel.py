#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_touzid_panel 守卫的**反向自检**（2026-09-23 立 · 铁律「守卫自身须反向测试」）

为什么必须存在
--------------
本守卫的第 ① 项是**行为级**断言（`--list-blocks` 真的会跑哪些块），它专门用于拦住
2026-09-23 那个「`--thermo-only --vix-only` 只跑 VIX、温度计被静默跳过」的缺陷 ——
这类缺陷**只比对日期永远抓不住**（落后 1 天既可能是源滞后、也可能是没跑）。

实测战果（首次运行）：揪出守卫自身两处问题 ——
  · [1/4] 的判据写成了 `if not errs`（任何错误都把块解析项标红）→ 归因错误，已改为按项独立归集；
  · 反向测试未双写 deploy 副本 → 产物类场景会连带触发 [4/4]，无法隔离 → 已改为双写。

隔离策略：产物类场景**同步写 root + deploy**，使 [4/4] 保持绿，从而确认红灯来自被测项本身。

用法:  python3 review/selftest_touzid_panel.py     # 退出码 1 = 有漏网
"""
import io
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
P = sys.executable
GATE = "review/check_touzid_panel.py"

SC = "fetch_touzid_data.py"
TH, THD = "output/market_thermometer.json", "deploy/output/market_thermometer.json"
VX, VXD = "output/vix_panel.json", "deploy/output/vix_panel.json"
FILES = [SC, TH, THD, VX, VXD]
ORIG = {f: io.open(f, encoding="utf-8").read() for f in FILES}


def run():
    r = subprocess.run([P, GATE], capture_output=True, text=True, timeout=240)
    errs = [l.strip() for l in (r.stdout or "").splitlines() if l.strip().startswith("❌")]
    return r.returncode, errs[:1]


def wr(f, s):
    io.open(f, "w", encoding="utf-8").write(s)


def wr2(f, s):
    """同写 root + deploy（保持 [4/4] 绿，隔离被测项）"""
    wr(f, s)
    wr("deploy/" + f, s)


def case_blocks():
    """① 把 _resolve_blocks 退回旧 elif 语义（VIX 胜出、温度计不跑）"""
    t = ORIG[SC]
    old = ('    if not (THERMO_ONLY or VIX_ONLY or INST_ONLY):\n'
           '        return ["thermometer", "valuation", "vix"]      # 默认（主站日更全量）\n'
           '    out = []\n'
           '    if THERMO_ONLY:\n'
           '        out.append("thermometer")\n'
           '    if VIX_ONLY:\n'
           '        out.append("vix")\n'
           '    if INST_ONLY:\n'
           '        out.append("inst")\n'
           '    return out')
    new = ('    if VIX_ONLY:\n        return ["vix"]\n'
           '    if INST_ONLY:\n        return ["inst"]\n'
           '    if THERMO_ONLY:\n        return ["thermometer"]\n'
           '    return ["thermometer", "valuation", "vix"]')
    assert t.count(old) == 1, "块解析锚点未命中"
    wr(SC, t.replace(old, new, 1))


def _thermo(mut):
    d = json.loads(ORIG[TH])
    mut(d)
    wr2(TH, json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def case_thermo_stale():
    """② 温度计落后 5 个交易日"""
    def m(d):
        d["date"] = "2026-09-15"
        d["snapshot"]["date"] = "2026-09-15"
    _thermo(m)


def case_thermo_mismatch():
    """③ 顶层 date 与 history 末条不自洽"""
    def m(d):
        d["date"] = "2026-09-19"
    _thermo(m)


def case_vix_stale():
    """④ VIX 落后美股 K 线（延时报价兜底失效）"""
    d = json.loads(ORIG[VX])
    d["cboe_vix"]["date"] = "2026-09-18"
    d["us_anchor"] = "2026-09-18"
    d["vix_history"] = [x for x in d["vix_history"] if x["date"] < "2026-09-19"]
    wr2(VX, json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def case_vix_anchor():
    """⑤ VIX 锚不自洽"""
    d = json.loads(ORIG[VX])
    d["date"] = "2026-09-19"
    wr2(VX, json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def case_deploy_drift():
    """⑥ deploy 副本漂移（只改 deploy）"""
    wr(VXD, ORIG[VXD].replace('"value": 14.21', '"value": 14.11', 1))


CASES = [
    ("① 块解析退回旧 elif（温度计被静默跳过）", case_blocks, "[1/4]"),
    ("② 温度计落后 5 个交易日", case_thermo_stale, "[2/4]"),
    ("③ 温度计 date ≠ history 末条", case_thermo_mismatch, "[2/4]"),
    ("④ VIX 落后美股 K 线（兜底失效）", case_vix_stale, "[3/4]"),
    ("⑤ VIX 锚不自洽", case_vix_anchor, "[3/4]"),
    ("⑥ deploy 副本漂移", case_deploy_drift, "[4/4]"),
]

bad = 0
try:
    for name, fn, expect_item in CASES:
        for f, s in ORIG.items():
            wr(f, s)
        fn()
        rc, errs = run()
        hit = rc == 1 and any(expect_item in e for e in errs)
        if not hit:
            bad += 1
        print(f"{name:<32} rc={rc} {'✅ 已拦' if hit else '❌ 未按预期拦截'}  {(errs or [''])[:1]}")
finally:
    for f, s in ORIG.items():
        wr(f, s)

rc, errs = run()
print(f"\n还原后 rc={rc} {'✅ PASS 转绿' if rc == 0 else '❌ FAIL ' + str(errs)}")
sys.exit(1 if (bad or rc != 0) else 0)
