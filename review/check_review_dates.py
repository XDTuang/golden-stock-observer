#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按日归档产物的「复盘日 / 指引日」命名守卫（2026-09-16 立）

用户口径（2026-09-16 拍板）：
  · **文件名日期 = 复盘日 = data_date**（该份复盘在复的那一天）
  · **指引日 = for_date = 复盘日的下一交易日**（跳过周末与节假日）

背景：`feed_review_*.json` 与 `v3_reasoning_*.json` 是「按日归档」产物（页面只读各自的
`*_latest.json`，归档件无代码读取 → 命名漂移不影响功能，但会让历史检索与回测对不上号）。
实测已出现三种命名法混用：按 data_date（正确）/ 按 for_date / 按生成日（周日补跑），
且 `for_date` 全仓**没有任何生成脚本**产出（一直靠 agent 手写）→ 必然漂移。

跑法：
  python3 review/check_review_dates.py            # 只读校验（默认）
  python3 review/check_review_dates.py --fix      # 重命名归一（冲突件移入 _backups/）
  python3 review/check_review_dates.py --fix --dry-run   # 只打印将要做的重命名

判据：
  ① 文件名日期 == 该文件的 data_date（复盘日）
  ② for_date 存在且 == data_date 的**下一交易日**（next_trading_day(d + 1)）
  ③ `<prefix>_latest.json` 的 data_date == 同目录归档件中的最新 data_date
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date as _date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from market_calendar import is_trading_day, next_trading_day  # noqa: E402

DIRS = ["output", "deploy/output"]
PREFIXES = ("feed_review", "v3_reasoning")
ARCHIVE_RE = re.compile(r"^(feed_review|v3_reasoning)_(\d{4}-\d{2}-\d{2})\.json$")


def guide_of(data_date: str) -> str:
    """指引日 = 复盘日的下一交易日（严格晚于 data_date）。"""
    d = _date.fromisoformat(data_date) + timedelta(days=1)
    return next_trading_day(d).isoformat()


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"__err__": str(e)}


def scan():
    """返回 (records, problems)。record = dict(path, prefix, fn_date, data_date, for_date, expect_for)"""
    recs = []
    for d in DIRS:
        full = os.path.join(BASE, d)
        if not os.path.isdir(full):
            continue
        for fn in sorted(os.listdir(full)):
            m = ARCHIVE_RE.match(fn)
            if not m:
                continue
            p = os.path.join(full, fn)
            doc = load(p)
            dd = doc.get("data_date")
            err = doc.get("__err__")
            recs.append({
                "path": p,
                "rel": os.path.join(d, fn),
                "prefix": m.group(1),
                "fn_date": m.group(2),
                "data_date": dd,
                "for_date": doc.get("for_date"),
                "expect_for": guide_of(dd) if (dd and re.match(r"^\d{4}-\d{2}-\d{2}$", str(dd))) else None,
                "err": err,
                "size": os.path.getsize(p),
                "mtime": os.path.getmtime(p),
                "mode": doc.get("mode"),
                "generated_at": str(doc.get("generated_at") or doc.get("generated") or ""),
            })

    problems = []
    for r in recs:
        if r["err"]:
            problems.append((r, "JSON 非法", f"{r['err']}")); continue
        if not r["data_date"]:
            problems.append((r, "缺 data_date", "无法判定复盘日")); continue
        if r["fn_date"] != r["data_date"]:
            problems.append((r, "文件名≠复盘日", f"文件名 {r['fn_date']} → 应为 {r['data_date']}"))
        if r["expect_for"] is None:
            problems.append((r, "data_date 非法", str(r["data_date"]))); continue
        if not r["for_date"]:
            problems.append((r, "缺 for_date", f"应为 {r['expect_for']}"))
        elif r["for_date"] != r["expect_for"]:
            problems.append((r, "for_date 错", f"{r['for_date']} → 应为 {r['expect_for']}"))
    return recs, problems


def check_latest(recs):
    """latest 的 data_date 须等于同目录归档件的最新 data_date。"""
    out = []
    for d in DIRS:
        for prefix in PREFIXES:
            latest = os.path.join(BASE, d, f"{prefix}_latest.json")
            if not os.path.exists(latest):
                continue
            dd = load(latest).get("data_date")
            arch = [r["data_date"] for r in recs
                    if r["rel"].startswith(d + os.sep) and r["prefix"] == prefix and r["data_date"]]
            if not arch:
                continue
            newest = max(arch)
            if dd != newest:
                out.append(f"{os.path.join(d, prefix + '_latest.json')} data_date={dd} ≠ 归档最新 {newest}")
    return out


# ── 信息窗口契约守卫（2026-09-16 · 方案 A ⑤）─────────────────────────
WINDOW_LATEST = os.path.join(BASE, "output", "window_latest.json")
WINDOW_ARCH_RE = re.compile(r"^window_(\d{4}-\d{2}-\d{2})\.json$")
# missing 非空时必须能渲染出来的三个页面副本（防「缺口被静默」）
PAGE_FILES = ["index.html", "index_template.html", "deploy/index.html"]


def check_window():
    """校验 output/window_latest.json 的窗口契约是否自洽。

    判据（设计稿 7.4）：
      ① span 连续无洞、端点 = for_date、首日 = data_date + 1 天
      ② display_days == [data_date] + span（展示口径含基准日）
      ③ 含非交易日时 span_is_weekend_cross 必须为真，反之亦然
      ④ data_date / for_date 必须都是交易日（补班周六不得入选）
      ⑤ carry.ref 实际存在
      ⑥ 归档件 window_<for_date>.json 的 for_date == 文件名日期
      ⑦ missing 非空 → 页面副本必须存在缺口渲染（禁静默）
    """
    problems, info = [], []
    if not os.path.exists(WINDOW_LATEST):
        return ["output/window_latest.json 不存在（先跑 python3 review/build_window.py）"], info
    w = load(WINDOW_LATEST)
    if "__err__" in w:
        return [f"window_latest.json JSON 非法：{w['__err__']}"], info

    dd, fd = w.get("data_date"), w.get("for_date")
    span = list(w.get("span") or [])
    disp = list(w.get("display_days") or [])
    info.append(f"session={w.get('session')}｜data_date={dd}→for_date={fd}｜"
                f"span={len(span)}天 display={len(disp)}天｜缺口={len(w.get('missing') or [])}项")

    if not dd or not fd:
        return ["window 缺 data_date / for_date"], info

    # ① span 骨架
    if not span:
        problems.append("window.span 为空（增量层缺失）")
    else:
        want_first = (_date.fromisoformat(dd) + timedelta(days=1)).isoformat()
        if span[0] != want_first:
            problems.append(f"span 首日 {span[0]} ≠ data_date+1（{want_first}）")
        if span[-1] != fd:
            problems.append(f"span 端点 {span[-1]} ≠ for_date（{fd}）")
        for a, b in zip(span, span[1:]):
            gap = (_date.fromisoformat(b) - _date.fromisoformat(a)).days
            if gap != 1:
                problems.append(f"span 有洞：{a} → {b}（相差 {gap} 天）")

    # ② display_days
    if disp != [dd] + span:
        problems.append(f"display_days 与 [data_date]+span 不一致：{disp}")

    # ③ 跨非交易日标记
    has_off = any(not is_trading_day(x) for x in span)
    cross = bool(w.get("span_is_weekend_cross"))
    if has_off and not cross:
        problems.append("span 含非交易日，但 span_is_weekend_cross=false")
    if cross and not has_off:
        problems.append("span_is_weekend_cross=true，但 span 全为交易日")

    # ④ 端点必须是交易日（防「补班周六」再次混入）
    for label, v in (("data_date", dd), ("for_date", fd)):
        try:
            if not is_trading_day(v):
                problems.append(f"{label} {v} 不是交易日（补班周六/周末/节假日不得入选）")
        except Exception as e:
            problems.append(f"{label} {v} 解析失败：{e}")

    # ⑤ 承接层
    ref = (w.get("carry") or {}).get("ref") or ""
    if ref and not os.path.exists(os.path.join(BASE, ref)):
        problems.append(f"carry.ref 不存在：{ref}")

    # ⑥ 归档件命名（window_<for_date>.json）
    for d in DIRS:
        full = os.path.join(BASE, d)
        if not os.path.isdir(full):
            continue
        for fn in sorted(os.listdir(full)):
            m = WINDOW_ARCH_RE.match(fn)
            if not m:
                continue
            doc = load(os.path.join(full, fn))
            got = doc.get("for_date")
            if got != m.group(1):
                problems.append(f"{os.path.join(d, fn)} for_date={got} ≠ 文件名 {m.group(1)}")

    # ⑦ missing 非空 → 页面须渲染（防静默漏读）
    if w.get("missing"):
        for f in PAGE_FILES:
            p = os.path.join(BASE, f)
            if not os.path.exists(p):
                continue
            t = open(p, encoding="utf-8").read()
            if "missing" not in t:
                problems.append(f"{f} 无 window.missing 渲染 → 缺口会被静默（禁）")
    return problems, info


def do_fix(recs, dry=False):
    """① 回填/纠正 for_date（定点文本改写，不重排其余格式）② 按复盘日（data_date）重命名。

    冲突（两份都声称同一复盘日）：保留 `generated_at` 更晚的一份（无该字段则退回 mtime/体积），
    另一份移入 `_backups/date_rename_20260916/`（可回溯，不销毁）。

    ⚠️ 重命名一律走 `occupied` 虚拟文件系统而非直接 `os.path.exists`：
       否则 dry-run 会因「尚未真正移动」而误判冲突，与实际执行结果不一致。
    """
    backup = os.path.join(BASE, "_backups", "date_rename_20260916")
    os.makedirs(backup, exist_ok=True)
    actions, moved, field_fixes = [], [], []

    # ── ① for_date 回填/纠正（定点改写：只动 for_date 这一个键）──
    for r in recs:
        if r["err"] or not r["data_date"] or r["expect_for"] is None:
            continue
        if r["for_date"] == r["expect_for"]:
            continue
        with open(r["path"], encoding="utf-8") as f:
            txt = f.read()
        dd = r["data_date"]
        if re.search(r'"for_date"\s*:', txt):
            new_txt = re.sub(r'("for_date"\s*:\s*)"[^"]*"', rf'\g<1>"{r["expect_for"]}"', txt, count=1)
        else:
            pat = re.compile(r'("data_date"\s*:\s*"%s"\s*)(,?)' % re.escape(dd))
            m = pat.search(txt)
            if not m:
                field_fixes.append((r["rel"], "跳过（未找到可锚定的 data_date 行）"))
                continue
            comma = m.group(2) or ","
            new_txt = txt[:m.start()] + m.group(1) + comma + f'\n  "for_date": "{r["expect_for"]}",' + txt[m.end():]
        if new_txt == txt:
            field_fixes.append((r["rel"], "跳过（改写后无变化）"))
            continue
        if not dry:
            try:
                json.loads(new_txt)
            except Exception as e:
                field_fixes.append((r["rel"], f"❌ 改写后 JSON 非法，已跳过：{e}"))
                continue
            with open(r["path"], "w", encoding="utf-8") as f:
                f.write(new_txt)
        field_fixes.append((r["rel"], f'for_date {r["for_date"] or "(缺)"} → {r["expect_for"]}'))

    # ── ② 按 data_date 重命名（虚拟 FS 跟踪占位）──
    occupied = {os.path.abspath(r["path"]) for r in recs}

    def key(r):
        """保留判定：generated_at 优先，其次 mtime，再次体积。"""
        return (r.get("generated_at") or "", r["mtime"], r["size"])

    for r in sorted(recs, key=lambda x: x["mtime"]):
        dd = r["data_date"]
        if not dd or r["fn_date"] == dd:
            continue
        src = os.path.abspath(r["path"])
        dst = os.path.join(os.path.dirname(src), f"{r['prefix']}_{dd}.json")
        dst_a = os.path.abspath(dst)
        if dst_a in occupied and dst_a != src:
            other = next((x for x in recs if os.path.abspath(x["path"]) == dst_a), None)
            keep_src = other is None or key(r) > key(other)
            loser = (src if not keep_src else dst_a)
            win = r if keep_src else other
            why = (f'保留 {os.path.basename(win["path"])}'
                   f'（generated_at={win.get("generated_at") or "—"}）') if other else "保留本文件"
            rel_b = os.path.join("_backups", "date_rename_20260916",
                                 os.path.basename(os.path.dirname(loser)) + "__" + os.path.basename(loser))
            if not dry:
                shutil.move(loser, os.path.join(BASE, rel_b))
            occupied.discard(loser)
            moved.append((loser, rel_b, why))
            if not keep_src:
                actions.append((src, f'[跳过：保留已有的 {os.path.basename(dst_a)}]'))
                continue
        if not dry:
            shutil.move(src, dst)
        occupied.discard(src); occupied.add(dst_a)
        actions.append((src, dst_a))
    return actions, moved, field_fixes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="回填 for_date + 重命名归一")
    ap.add_argument("--dry-run", action="store_true", help="配合 --fix：只打印不落盘")
    args = ap.parse_args()

    recs, problems = scan()
    print(f"═══ 按日归档命名守卫（复盘日 / 指引日）═══")
    print(f"  扫描目录：{', '.join(DIRS)} | 归档件 {len(recs)} 个")
    print(f"  口径：文件名 = 复盘日（data_date）｜指引日 = for_date = 复盘日的下一交易日\n")

    if args.fix:
        actions, moved, field_fixes = do_fix(recs, dry=args.dry_run)
        tag = "（dry-run）" if args.dry_run else ""
        print(f"{tag}① for_date 回填/纠正 {len(field_fixes)} 项：")
        for rel, detail in field_fixes:
            print(f"   {rel}  {detail}")
        print(f"\n{tag}② 按复盘日重命名 {len(actions)} 项：")
        for a, b in actions:
            print(f"   {os.path.relpath(a, BASE)}")
            print(f"     → {b if not os.path.isabs(b) else os.path.relpath(b, BASE)}")
        if moved:
            print(f"\n{tag}③ 冲突件移入 _backups/（{len(moved)} 项）：")
            for a, b, why in moved:
                print(f"   弃 {os.path.relpath(a, BASE)}   （{why}）")
                print(f"     → {b}")
        if not args.dry_run:
            recs, problems = scan()
            print()
    else:
        print("  明细（仅列有问题的）：")
        if not problems:
            print("   （无）")
        for r, kind, detail in problems:
            print(f"   ❌ {r['rel']}")
            print(f"        {kind}：{detail}")
        print()

    lat = check_latest(recs)
    if lat:
        print("  ⚠️ latest 与归档最新不一致：")
        for x in lat:
            print(f"   {x}")
        print()

    # ── 信息窗口契约（2026-09-16 · 方案 A）──
    wprobs, winfo = check_window()
    print("  【信息窗口契约 output/window_latest.json】")
    for x in winfo:
        print(f"   {x}")
    if wprobs:
        for x in wprobs:
            print(f"   ❌ {x}")
    else:
        print("   ✅ span/display/交易日/承接/归档/missing 渲染 全部自洽")
    print()

    ok = not problems and not lat and not wprobs
    print(f"{'✅' if ok else '❌'} 命名 + 窗口契约守卫："
          + ("通过" if ok else f"未通过（{len(problems)} 项命名/字段，{len(lat)} 项 latest，"
                               f"{len(wprobs)} 项窗口契约）"))
    if not ok and not args.fix:
        print("   → 修法：python3 review/check_review_dates.py --fix  （先看 --dry-run 清单）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
