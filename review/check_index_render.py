#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老站 index.html 渲染守卫（富文本 + 表格布局 + 注入器同步）
===========================================================================
背景（2026-09-18 立 · 用户报障）:
  ① 老站「AI 综合推演」块显示**字面 `<b>` 标签** —— drLoadFeedReview 对 agent 手写的
     ai_synthesis 内容统一走 esc()，而内容含 102 处 `<b>` 强调（V3 已修，老站漏修）。
  ② 「机制 × 语料交叉验证」表**列宽崩溃** —— `<td class="dr-tag">` 撞上 analysis.html
     注入的 `.dr-tag{display:inline-block}`，td 脱离表格布局
     （实测：判定列被压到 40px、含义列 left 与判定列**重叠**、表头 735px 与实际 66px 脱节）。

守卫内容（任一不通过 → 退出码 1）:
  [1] 三处 index 不得出现 `<td class="dr-tag"`（td 上挂 .dr-tag 会毁掉表格布局）
  [2] 三处 index 必须有 `.dr-tbl td.dr-tag{display:table-cell…}` 防御
  [3] 三处 index 必须有 FEED-RICHTEXT 块且 rich( 调用 ≥ MIN_RICH
  [4] 🔴 **inject_feed_review.py 的 JS_BLOCK 必须与 index.html 现行 JS 区间一致**
      —— 防「注入器滞后」：一旦脚本落后于线上版本，「比对后替换」会用旧版**覆盖新版**
      （2026-09-18 实测踩到：注入器 14429 字符 vs 线上 24707 字符，覆盖后丢了
      类型防御/子块隔离/drCrossSlot 分离等改进）
  [5] 三处 index md5 一致（防漏同步）
  [6] drLoadCrossAnalysis 的表头列宽声明在位（判定 88px / 净流 108px）

用法:
  python review/check_index_render.py        # 校验（红灯退出码 1）
  python review/check_index_render.py -v     # 打印明细
"""
import os, sys, re, hashlib

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEXES = ['index.html', 'index_template.html', 'deploy/index.html']
INJECTOR = 'inject_feed_review.py'
JS_MARK = '// ===== 投喂复盘渲染 =====\n'
JS_END = '// ===== 每日复盘 Tab ====='
MIN_RICH = 10          # rich( 调用点下限（当前 13）


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(65536), b''):
            h.update(b)
    return h.hexdigest()


def main():
    verbose = '-v' in sys.argv
    errs, notes = [], []

    # ── [1] td.dr-tag ──
    bad1 = {}
    for f in INDEXES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            bad1[f] = '缺失'
            continue
        n = open(p, encoding='utf-8').read().count('<td class="dr-tag"')
        if n:
            bad1[f] = n
    ok1 = not bad1
    if bad1:
        errs.append(f"td 上误用 .dr-tag（会毁表格布局）: {bad1}")
    print(f"{'✅' if ok1 else '❌'} [1/6] 三处 index 无 `<td class=\"dr-tag\"`"
          + (f" — 命中 {bad1}" if bad1 else ""))

    # ── [2] 防御 CSS ──
    bad2 = [f for f in INDEXES
            if not os.path.exists(os.path.join(BASE, f))
            or '.dr-tbl td.dr-tag{display:table-cell' not in open(os.path.join(BASE, f), encoding='utf-8').read()]
    ok2 = not bad2
    if bad2:
        errs.append(f"缺 `.dr-tbl td.dr-tag{{display:table-cell}}` 防御: {bad2}")
    print(f"{'✅' if ok2 else '❌'} [2/6] 三处 index 有 td.dr-tag 防御 CSS"
          + (f" — 缺 {bad2}" if bad2 else ""))

    # ── [3] FEED-RICHTEXT 块 ──
    bad3 = []
    for f in INDEXES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            bad3.append(f'{f}(缺失)'); continue
        s = open(p, encoding='utf-8').read()
        if 'FEED-RICHTEXT-BEGIN' not in s:
            bad3.append(f'{f}(无块)'); continue
        n = len(re.findall(r'\brich\(', s))
        if n < MIN_RICH:
            bad3.append(f'{f}(rich {n} < {MIN_RICH})')
    ok3 = not bad3
    if bad3:
        errs.append(f"富文本白名单缺失/不完整: {bad3}")
    print(f"{'✅' if ok3 else '❌'} [3/6] 三处 index 富文本白名单（rich ≥ {MIN_RICH}）"
          + (f" — {bad3}" if bad3 else ""))

    # ── [4] 🔴 注入器 JS_BLOCK 与线上 JS 区间一致 ──
    ok4, d4 = True, ''
    try:
        idx = open(os.path.join(BASE, 'index.html'), encoding='utf-8').read()
        i = idx.index(JS_MARK)
        j = idx.index(JS_END, i)
        cur = idx[i:j]
        t = open(os.path.join(BASE, INJECTOR), encoding='utf-8').read()
        k = t.index('JS_BLOCK = r"""') + len('JS_BLOCK = r"""')
        m = t.index('"""', k)
        block = t[k:m]
        ok4 = block.strip() == cur.strip()
        d4 = f'注入器 {len(block)} vs 线上 {len(cur)} 字符'
        if not ok4:
            errs.append(f"🔴 注入器 JS_BLOCK 与 index.html 现行 JS **不一致**（{d4}）—— "
                        f"跑注入器会用旧版覆盖线上版；请先用 index.html 的现行 JS 更新 JS_BLOCK")
    except Exception as e:
        ok4 = False
        d4 = f'{type(e).__name__}: {str(e)[:60]}'
        errs.append(f'注入器一致性检查异常: {d4}')
    print(f"{'✅' if ok4 else '❌'} [4/6] 注入器 JS_BLOCK ≡ index.html 现行 JS（{d4}）")

    # ── [5] 三处 index md5 一致 ──
    hs = {}
    for f in INDEXES:
        p = os.path.join(BASE, f)
        hs[f] = md5(p) if os.path.exists(p) else None
    uniq = {v for v in hs.values() if v}
    ok5 = len(uniq) == 1 and all(hs.values())
    if not ok5:
        errs.append("三处 index 不一致: " + str({k: (v or 'NA')[:8] for k, v in hs.items()}))
    print(f"{'✅' if ok5 else '❌'} [5/6] 三处 index md5 一致（{list(uniq)[0][:8] if uniq else 'NA'}）")

    # ── [6] 交叉验证表列宽声明 ──
    ok6 = True
    for f in INDEXES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            ok6 = False; break
        s = open(p, encoding='utf-8').read()
        if 'width:88px">判定' not in s or 'width:108px">主力净流' not in s:
            ok6 = False
            errs.append(f'{f}: 交叉验证表列宽声明缺失（判定 88px / 净流 108px）')
            break
    print(f"{'✅' if ok6 else '❌'} [6/6] 交叉验证表列宽声明在位（判定 88 / 净流 108）")

    if verbose:
        print('\n── 明细 ──')
        for f in INDEXES:
            p = os.path.join(BASE, f)
            if os.path.exists(p):
                s = open(p, encoding='utf-8').read()
                print(f'  {f:24s} 大小={os.path.getsize(p)} rich={s.count("rich(")} '
                      f'rich定义={s.count("const rich")} td.dr-tag={s.count(chr(60) + "td class=" + chr(34) + "dr-tag" + chr(34))}')

    print()
    if errs:
        print(f'❌ 老站渲染守卫未通过（{len(errs)} 项）：')
        for e in errs:
            print(f'   · {e}')
        return 1
    print('✅ 老站渲染守卫全部通过（6/6）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
