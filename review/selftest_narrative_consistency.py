#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_narrative_consistency.py 的反向自检（10 场景）

与 `selftest_index_render.py` / `selftest_touzid_panel.py` 的区别：
  那两个会**临时改坏正式文件再还原**（故不得在自动链路中途运行）；
  本脚本**在 /tmp 沙箱内构造副本**，**完全不触碰仓库内任何文件**
  → 可在任意时刻（含自动链路中）安全运行。

它验证的是「守卫本身有没有失效」——
只验正向通过（绿灯）发现不了守卫早就坏了，必须**先能红、且红得准**。

用法：python3 review/selftest_narrative_consistency.py
退出码：全过 0 / 有失败 1
"""

import os
import re
import json
import shutil
import subprocess
import sys
import tempfile
import importlib.util

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(REVIEW_DIR)

GUARD = "check_narrative_consistency.py"
ANALYSIS_REL = os.path.join("data", "daily_review", "analysis.html")
CROSS_REL = os.path.join("output", "cross_analysis.json")

FULL_RX = re.compile(r"共振\s*(\d+)\s*/\s*背离\s*(\d+)\s*/\s*暗线\s*(\d+)\s*/\s*双冷\s*(\d+)")
HIT_RX = re.compile(r"命中\s*(\d+)\s*处.*?当前值\s*(\d+)\s*·\s*历史\s*(\d+)")

results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    mark = "\033[32m✅\033[0m" if cond else "\033[31m❌\033[0m"
    print(f"  {mark} {name}" + (f"   {detail}" if detail else ""))
    return bool(cond)


def setup(tmp):
    """沙箱：复制守卫 + 真实产物（root 与 deploy 各一份）"""
    os.makedirs(os.path.join(tmp, "review"), exist_ok=True)
    for rel in (ANALYSIS_REL, CROSS_REL):
        os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
        os.makedirs(os.path.join(tmp, "deploy", os.path.dirname(rel)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, rel))
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, "deploy", rel))
    shutil.copyfile(os.path.join(REVIEW_DIR, GUARD), os.path.join(tmp, "review", GUARD))


def run(tmp, *args):
    p = subprocess.run([sys.executable, os.path.join("review", GUARD), *args],
                       cwd=tmp, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read(tmp, rel):
    with open(os.path.join(tmp, rel), encoding="utf-8") as f:
        return f.read()


def write(tmp, rel, s):
    with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
        f.write(s)


def q_true(tmp):
    d = json.load(open(os.path.join(tmp, CROSS_REL), encoding="utf-8"))
    q = {"共振": 0, "背离": 0, "暗线": 0, "双冷": 0}
    for it in d.get("items") or []:
        if it.get("verdict") in q:
            q[it["verdict"]] += 1
    return q


def q_full(tmp):
    h = read(tmp, ANALYSIS_REL)
    m = FULL_RX.search(h)
    return tuple(int(x) for x in m.groups()) if m else None


def n_hits(out):
    m = HIT_RX.search(out)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (None, None, None)


def main():
    if not os.path.exists(os.path.join(ROOT, ANALYSIS_REL)):
        print("❌ 缺少 analysis.html，无法自检")
        return 1

    tmp = tempfile.mkdtemp(prefix="nc_selftest_")
    print("═" * 74)
    print("  check_narrative_consistency.py · 反向自检（10 场景 · 沙箱式）")
    print(f"  沙箱 = {tmp}")
    print("═" * 74)
    try:
        setup(tmp)
        # 载入守卫模块（用于单元级验证；顶层无副作用）
        spec = importlib.util.spec_from_file_location("nc_guard", os.path.join(REVIEW_DIR, GUARD))
        nc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nc)
        q = q_true(tmp)
        want_full = "共振 %d / 背离 %d / 暗线 %d / 双冷 %d" % (q["共振"], q["背离"], q["暗线"], q["双冷"])
        want_slash = "%d/%d/%d/%d" % (q["共振"], q["背离"], q["暗线"], q["双冷"])
        orig = read(tmp, ANALYSIS_REL)

        # 基线：原始副本当前的命中结构（历史引用处数须在修复后保持不变）
        rc0, out0 = run(tmp, "-v")
        n0, c0, h0 = n_hits(out0)
        print(f"  基线：命中 {n0} 处（当前值 {c0} · 历史 {h0}）｜数据侧 {want_full}")
        print("─" * 74)

        # ── S1 构造分叉（把当前值全改成 9/9/9/9）→ 应红灯 ──
        h = orig
        h = h.replace(want_full, "共振 9 / 背离 9 / 暗线 9 / 双冷 9")
        h = h.replace(want_slash, "9/9/9/9")
        write(tmp, ANALYSIS_REL, h)
        rc, out = run(tmp)
        n1, c1, _ = n_hits(out)
        ok("S1  构造分叉 → 红灯", rc == 1 and "未通过" in out, f"退出码 {rc}")
        ok("S1b 命中「当前值」处数 > 0 且被逐处列出",
           c1 is not None and c1 > 0 and out.count("❌ L") >= c1,
           f"当前值 {c1} 处，列出 {out.count('❌ L')} 处")

        # ── S2 --fix ──
        rc, out = run(tmp, "--fix")
        m = re.search(r"--fix 已替换 (\d+) 处（全式 (\d+) / 简写 (\d+)）", out)
        ok("S2  --fix 执行且报告替换处数", rc == 0 and m is not None,
           f"替换 {m.group(1) if m else '?'} 处（全式 {m.group(2) if m else '?'} / 简写 {m.group(3) if m else '?'}）")
        ok("S2b --fix 复检自报通过", "复检通过" in out)

        # ── S3 修后复跑 → 绿灯 ──
        rc, out = run(tmp)
        ok("S3  修后复跑 → 绿灯", rc == 0 and "✅ 通过" in out, f"退出码 {rc}")

        # ── S4 精确断言：脏值清零 + 历史引用未伤 ──
        fixed = read(tmp, ANALYSIS_REL)
        ok("S4a 全式脏值 9/9/9/9 已清零", "共振 9 / 背离 9 / 暗线 9 / 双冷 9" not in fixed)
        ok("S4b 简写脏值 9/9/9/9 已清零", "9/9/9/9" not in fixed)
        ok("S4c 当前值已全部等于数据侧",
           len(re.findall(re.escape(want_full), fixed)) >= 1 and want_slash in fixed)
        hist_before = orig.count("4/6/5/16")
        hist_after = fixed.count("4/6/5/16")
        ok("S4d 历史引用未被误伤（示例 4/6/5/16）", hist_after == hist_before,
           f"修前 {hist_before} → 修后 {hist_after}")

        # ── S5 root↔deploy 同步 ──
        same = read(tmp, ANALYSIS_REL) == read(tmp, os.path.join("deploy", ANALYSIS_REL))
        ok("S5  --fix 后 root↔deploy 同步写入", same)

        # ── S6 数据侧变更（模拟云端抢跑重算）→ 应红灯 ──
        d = json.load(open(os.path.join(tmp, CROSS_REL), encoding="utf-8"))
        for it in d["items"]:
            if it.get("verdict") == "共振":
                it["verdict"] = "背离"
                break
        json.dump(d, open(os.path.join(tmp, CROSS_REL), "w", encoding="utf-8"), ensure_ascii=False)
        rc, out = run(tmp)
        ok("S6  数据变更而页面未动 → 红灯", rc == 1 and "未通过" in out, f"退出码 {rc}")

        # 复原数据
        shutil.copyfile(os.path.join(tmp, "deploy", CROSS_REL), os.path.join(tmp, CROSS_REL))

        # ── S7 页面出现两种「当前值」→ 应报「不同源」──
        rc, out = run(tmp, "--fix")            # 先确保一致
        fixed = read(tmp, ANALYSIS_REL)
        i = fixed.rfind(want_full)
        if i > 0:
            tmp_h = fixed[:i] + "共振 3 / 背离 9 / 暗线 5 / 双冷 14" + fixed[i + len(want_full):]
            write(tmp, ANALYSIS_REL, tmp_h)
            rc, out = run(tmp)
            ok("S7  页面出现两种当前值 → 报「不同源」", "不同源" in out, f"退出码 {rc}")
            write(tmp, ANALYSIS_REL, fixed)
        else:
            ok("S7  页面出现两种当前值 → 报「不同源」", False, "未找到可改位置")

        # ── S8 无标记词的象限简写 → 应判「待判(unknown)」 ──
        # 用单元级验证（避免依赖页面里恰好存在/不存在某个标记词）：
        fake_u = "象限分布 7/7/7/7 示例"                     # 含「象限」→ 准入；无 cur/hist 标记 → unknown
        hits_u = nc.scan(fake_u)
        sl_u = [x for x in hits_u if x["form"] == "slash"]
        ok("S8a classify：无标记词 → unknown",
           len(sl_u) == 1 and sl_u[0]["kind"] == "unknown",
           f"命中 {len(sl_u)} 处，kind={[x['kind'] for x in sl_u]}")
        ok("S8b classify：'变为' 前判历史 / 后判当前（实测句式）",
           nc.classify("象限分布由 ") == "hist" and nc.classify("象限分布变为 ") == "cur",
           f"由→{nc.classify('象限分布由 ')} / 变为→{nc.classify('象限分布变为 ')}")
        # 端到端：把页面里「当前值」全式替换为无标记简写 → 应报无法判定并红灯
        hh = read(tmp, ANALYSIS_REL)
        hh = hh.replace(want_full, "象限分布 7/7/7/7", 1)
        write(tmp, ANALYSIS_REL, hh)
        rc, out = run(tmp)
        ok("S8c 页面出现无标记简写 → 红灯且提示「无法判定」",
           rc == 1 and "无法判定" in out, f"退出码 {rc}")
        shutil.copyfile(os.path.join(tmp, "deploy", ANALYSIS_REL),
                        os.path.join(tmp, ANALYSIS_REL))   # 复原页面

        # ── S9 非象限语境的 A/B/C/D 不得被纳入 ──
        fake_n = "成交量比 1/2/3/4 与日期 09/28 无关。"
        sl_n = [x for x in nc.scan(fake_n) if x["form"] == "slash"]
        ok("S9a 非象限简写未被纳入（单元）", len(sl_n) == 0, f"命中 {len(sl_n)} 处")
        rc, out = run(tmp)
        n9, _, _ = n_hits(out)
        ok("S9b 复原后命中数回到基线", n9 == n0, f"基线 {n0} → 现在 {n9}")

        # ── S10 BOM 缺失 → 红灯 ──
        hh = read(tmp, ANALYSIS_REL)
        if hh.startswith("\ufeff"):
            hh = hh[1:]
        write(tmp, ANALYSIS_REL, hh)
        rc, out = run(tmp)
        ok("S10 缺 UTF-8 BOM → 红灯且明确提示",
           rc == 1 and "BOM" in out, f"退出码 {rc}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    npass = sum(1 for _, okc, _ in results if okc)
    ntot = len(results)
    print("═" * 74)
    if npass == ntot:
        print(f"\033[32m  ✅ 反向自检全部通过（{npass}/{ntot}）—— 守卫具备「能红、红得准、可自愈」三项能力\033[0m")
        return 0
    print(f"\033[31m  ❌ 反向自检未全过（{npass}/{ntot}）—— 守卫可能已失效\033[0m")
    for name, okc, det in results:
        if not okc:
            print(f"     · {name}  {det}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
