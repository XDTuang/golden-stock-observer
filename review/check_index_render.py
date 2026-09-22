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

守卫内容（任一不通过 → 退出码 1）: 9 项
  [1] 三处 index 不得出现 `<td class="dr-tag"`（td 上挂 .dr-tag 会毁掉表格布局）
  [2] 三处 index 必须有 `.dr-tbl td.dr-tag{display:table-cell…}` 防御
  [3] 三处 index 必须有 FEED-RICHTEXT 块且 rich( 调用 ≥ MIN_RICH
  [4] 🔴 **inject_feed_review.py 的 JS_BLOCK 必须与 index.html 现行 JS 区间一致**
      —— 防「注入器滞后」：一旦脚本落后于线上版本，「比对后替换」会用旧版**覆盖新版**
      （2026-09-18 实测踩到：注入器 14429 字符 vs 线上 24707 字符，覆盖后丢了
      类型防御/子块隔离/drCrossSlot 分离等改进）
  [5] 三处 index md5 一致（防漏同步）
  [6] drLoadCrossAnalysis 的表头列宽声明在位（判定 88px / 净流 108px）
  [7] 🔴 **rich() 行为级测试**（2026-09-22 新增）—— 把页面里的 esc+rich 抽出来在 Node 里
      **真跑测试向量**，覆盖 2026-09-22 报障的三类缺口（带 class 的 <b>、单引号 class、
      多余 HTML 实体）+ 4 个注入向量必须保持转义。文本匹配测不出「正则漏一种写法」，
      只有跑代码才测得出来。
  [8] 🔴 **.dk-* 语义色 7 类齐备且取值同源**（2026-09-22 新增）—— `#drFeedReview`
      是 `#drAnalysis` 的**兄弟节点**，analysis.html 被作用域化的样式管不到它；
      缺定义 → 放行了标签也没有颜色。老站 3 份 + V3 4 份都要有，且取值同源。
  [9] 🔴 **agent 字段不得走裸 esc()**（2026-09-22 新增）—— chips() /
      holding_map.caution / ai_synthesis.disclaimer 三处曾漏改，导致这些字段内的
      `<b>`、`<span class='dk-*'>` 全部以字面文字显示。

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
V3_INDEXES = ['review_v3/index.html', 'review_v3/index_hide89.html',
              'deploy/review_v3/index.html', 'deploy/review_v3/index_hide89.html']

# ── [7] rich() 行为级测试向量：[输入, rich() 应产出的 HTML 源码串] ──
#    （页面最终由浏览器解一次实体；这里校验的是 rich 的输出串本身）
RICH_CASES = [
    # ① 三类缺口（2026-09-22 报障）
    ['<b class="dk-main">核心</b>',        '<b class="dk-main">核心</b>'],
    ['<b class="dk-risk">转弱</b>',         '<b class="dk-risk">转弱</b>'],
    ["<span class='dk-dn'>-2.80%</span>",   '<span class="dk-dn">-2.80%</span>'],
    ["<span class='dk-up'>+0.87%</span>",   '<span class="dk-up">+0.87%</span>'],
    ['高开 &gt;0.5%',                       '高开 &gt;0.5%'],
    ['S&amp;P100',                          'S&amp;P100'],
    ['涨跌比 &lt;0.6',                      '涨跌比 &lt;0.6'],
    # ② 既有能力不得回退
    ['<b>裸粗体</b>',                       '<b>裸粗体</b>'],
    ['<i>斜</i>',                           '<i>斜</i>'],
    ['<br>',                                '<br>'],
    ['A & B',                               'A &amp; B'],
    ['&lt;b&gt;（刻意显示字面标签）',        '&lt;b&gt;（刻意显示字面标签）'],
    # ③ 安全：非白名单 class / 注入向量必须保持转义（XSS 面为零）
    ['<b class="evil">x</b>',               '&lt;b class="evil"&gt;x</b>'],
    ['<span class="dk-main evil">x</span>', '&lt;span class="dk-main evil"&gt;x</span>'],
    ['<script>alert(1)</script>',           '&lt;script&gt;alert(1)&lt;/script&gt;'],
    ['<img src=x onerror=alert(1)>',        '&lt;img src=x onerror=alert(1)&gt;'],
    ['<a href="javascript:1">x</a>',        '&lt;a href="javascript:1"&gt;x&lt;/a&gt;'],
]

# ── [9] 渲染路径：agent 手写字段若走 esc() → 该字段内的标签变字面文字 ──
#    用**精确子串**而非正则：这些是代码片段本身，子串匹配不会因一个引号写错而静默失效
#    （2026-09-22 反向测试实测：初版正则漏了属性结尾的 `"` → chips/caution 回退抓不到）
BAD_ESC = [
    ('chips() 对 agent 字段用 esc()（holding_map.theme_aligned/us 含 <b> 与 <span>）',
     "font-size:11px\">' + esc(s) + '</span>').join('');"),
    ('holding_map.caution 徽章用 esc()（含 <span class=…dk-*…> 富文本）',
     "color:#f0b429;font-size:11px\">' + esc(x) + '</span>').join('')"),
    ('ai_synthesis.disclaimer 用 esc()（实测含 <b class="dk-caution">）',
     "esc(syn.disclaimer)"),
]

NODE_CANDIDATES = [
    '/Users/samt/.workbuddy/binaries/node/versions/22.22.2-2/bin/node',
    '/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node',
    '/usr/local/bin/node',
]

_RUNNER = r'''
const fs = require('fs');
const code = fs.readFileSync(process.argv[2], 'utf8');
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
let f;
try { f = new Function(code + '\n;return rich;')(); }
catch (e) { console.log(JSON.stringify({error: String(e.message)})); process.exit(0); }
const bad = [];
for (const [inp, want] of cases) {
  let got;
  try { got = f(inp); } catch (e) { got = 'THROW:' + e.message; }
  if (got !== want) bad.push({inp: inp, want: want, got: String(got)});
}
console.log(JSON.stringify({bad: bad}));
'''


def _node():
    for p in NODE_CANDIDATES:
        if os.path.exists(p):
            return p
    import shutil as _sh
    return _sh.which('node')


def _extract_rich(path, begin_mark, end_mark):
    """抽出从 `const esc = ` 起、到 end_mark 止的代码块（esc + DKCLS + _rtTag + rich）。"""
    s = open(path, encoding='utf-8').read()
    j = s.index(begin_mark)
    k = s.rindex('const esc = ', 0, j)
    e = s.index(end_mark, j) + len(end_mark)
    return s[k:e]


def rich_behavior():
    """真跑真代码：Node 里对老站与 V3 两套 rich() 求值。返回 (ok|None, fails)。"""
    node = _node()
    if not node:
        return None, ['未找到 node 可执行文件，行为级测试跳过']
    import tempfile, subprocess, json as _json
    targets = [
        ('老站 index.html', 'index.html',
         '/* ═══════════ FEED-RICHTEXT-BEGIN',
         '/* ═══════════ FEED-RICHTEXT-END ═══════════ */'),
        ('V3 review_v3/index.html', 'review_v3/index.html',
         '/* ═══════════ V3-RICHTEXT-BEGIN ═══════════ */',
         '/* ═══════════ V3-RICHTEXT-END ═══════════ */'),
    ]
    bad = []
    with tempfile.TemporaryDirectory() as d:
        rp = os.path.join(d, 'runner.js')
        open(rp, 'w', encoding='utf-8').write(_RUNNER)
        cp = os.path.join(d, 'cases.json')
        open(cp, 'w', encoding='utf-8').write(_json.dumps(RICH_CASES, ensure_ascii=False))
        for label, rel, bm, em in targets:
            p = os.path.join(BASE, rel)
            if not os.path.exists(p):
                bad.append(f'{label}: 文件不存在')
                continue
            try:
                src = _extract_rich(p, bm, em)
            except Exception as e:
                bad.append(f'{label}: 抽取 rich 块失败（{type(e).__name__}）')
                continue
            sp = os.path.join(d, 'rich_src.js')
            open(sp, 'w', encoding='utf-8').write(src)
            try:
                r = subprocess.run([node, rp, sp, cp], capture_output=True, text=True, timeout=60)
            except Exception as e:
                bad.append(f'{label}: node 执行失败（{type(e).__name__}）')
                continue
            out = [x for x in (r.stdout or '').strip().splitlines() if x.strip()]
            if not out:
                bad.append(f'{label}: node 无输出（{(r.stderr or "")[:70]}）')
                continue
            try:
                res = _json.loads(out[-1])
            except Exception:
                bad.append(f'{label}: node 输出非 JSON')
                continue
            if res.get('error'):
                bad.append(f'{label}: rich 块语法错误 — {res["error"][:70]}')
                continue
            for b in res.get('bad', []):
                bad.append(f'{label}: rich({b["inp"][:30]!r}) → {b["got"][:52]!r}，期望 {b["want"][:52]!r}')
    return (not bad), bad


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
    print(f"{'✅' if ok1 else '❌'} [1/9] 三处 index 无 `<td class=\"dr-tag\"`"
          + (f" — 命中 {bad1}" if bad1 else ""))

    # ── [2] 防御 CSS ──
    bad2 = [f for f in INDEXES
            if not os.path.exists(os.path.join(BASE, f))
            or '.dr-tbl td.dr-tag{display:table-cell' not in open(os.path.join(BASE, f), encoding='utf-8').read()]
    ok2 = not bad2
    if bad2:
        errs.append(f"缺 `.dr-tbl td.dr-tag{{display:table-cell}}` 防御: {bad2}")
    print(f"{'✅' if ok2 else '❌'} [2/9] 三处 index 有 td.dr-tag 防御 CSS"
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
    print(f"{'✅' if ok3 else '❌'} [3/9] 三处 index 富文本白名单（rich ≥ {MIN_RICH}）"
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
    print(f"{'✅' if ok4 else '❌'} [4/9] 注入器 JS_BLOCK ≡ index.html 现行 JS（{d4}）")

    # ── [5] 三处 index md5 一致 ──
    hs = {}
    for f in INDEXES:
        p = os.path.join(BASE, f)
        hs[f] = md5(p) if os.path.exists(p) else None
    uniq = {v for v in hs.values() if v}
    ok5 = len(uniq) == 1 and all(hs.values())
    if not ok5:
        errs.append("三处 index 不一致: " + str({k: (v or 'NA')[:8] for k, v in hs.items()}))
    print(f"{'✅' if ok5 else '❌'} [5/9] 三处 index md5 一致（{list(uniq)[0][:8] if uniq else 'NA'}）")

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
    print(f"{'✅' if ok6 else '❌'} [6/9] 交叉验证表列宽声明在位（判定 88 / 净流 108）")

    # ── [7] rich() 行为级测试（真跑真代码）──
    ok7, d7 = rich_behavior()
    if ok7 is None:
        notes.append(d7[0])
        print(f'⚠️ [7/9] rich() 行为级测试跳过 — {d7[0]}')
    else:
        if not ok7:
            errs.append(f'rich() 行为级测试未通过（{len(d7)} 项）：')
            errs.extend('     ' + x for x in d7[:8])
        print(f"{'✅' if ok7 else '❌'} [7/9] rich() 行为级测试"
              f"（{len(RICH_CASES)} 向量 × 老站/V3 双实现）"
              + ('' if ok7 else f" — {len(d7)} 项不符"))

    # ── [8] .dk-* 语义色 7 类齐备且取值同源 ──
    want = {}
    try:
        sys.path.insert(0, os.path.join(BASE, 'review'))
        import patch_dk_css as _dk
        want = dict(_dk.RULES)
    except Exception as e:
        errs.append(f'无法载入 review/patch_dk_css.py 权威取值：{type(e).__name__} {e}')
    bad8 = []
    if want:
        for f in INDEXES + V3_INDEXES:
            p = os.path.join(BASE, f)
            if not os.path.exists(p):
                bad8.append(f'{f}(缺失)')
                continue
            s = open(p, encoding='utf-8').read()
            for name, decl in want.items():
                m = re.search(r'\.' + re.escape(name) + r'\s*\{([^}]*)\}', s)
                if not m:
                    bad8.append(f'{f}: 缺 .{name}')
                elif m.group(1).replace(' ', '') != decl.replace(' ', ''):
                    bad8.append(f'{f}: .{name} = {m.group(1)!r} ≠ 权威 {decl!r}')
    ok8 = bool(want) and not bad8
    if bad8:
        errs.append(f'.dk-* 语义色缺失/取值漂移（{len(bad8)} 项）：' + '；'.join(bad8[:6]))
    print(f"{'✅' if ok8 else '❌'} [8/9] .dk-* 语义色 7 类齐备且取值同源（老站 3 + V3 4）"
          + ('' if ok8 else f' — {len(bad8)} 项'))

    # ── [8b] 容器规则不得压掉语义色 ──
    #  `.dr-note b{color:…}`（0,1,1）会盖过 `.dk-main{…}`（0,1,0）→ <b class="dk-main"> 变正文色，
    #  而 SPAN.dk-caution 不受命中却是好的（2026-09-22 实测「同类不同色」）。
    #  正解 = 该规则加 `:not([class*="dk-"])` 守卫；此处断言不存在「未加守卫」的形态。
    GUARD_RE = re.compile(r"\.(dr-note|dr-tag|dr-h|dr-wrap|rc-block)[^{,]*\b(b|span|i)\s*\{[^}]*color")
    bad8b = []
    for f in INDEXES + V3_INDEXES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8').read()
        for m in GUARD_RE.finditer(s):
            if ':not(' not in m.group(0):
                bad8b.append(f'{f}: {m.group(0)[:58]}')
    ok8b = not bad8b
    if bad8b:
        errs.append('容器规则未加 :not 守卫（会压掉语义色）：' + '；'.join(bad8b[:4]))
    print(f"{'✅' if ok8b else '❌'} [8b] 无「未加 :not 守卫」的容器 color 规则"
          + ('' if ok8b else f' — {len(bad8b)} 处'))

    # ── [9] agent 字段不得走裸 esc() ──
    bad9 = []
    for f in INDEXES + V3_INDEXES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8').read()
        for desc, pat in BAD_ESC:
            if pat in s:
                bad9.append(f'{f}: {desc}')
    ok9 = not bad9
    if bad9:
        errs.append('agent 字段仍走 esc()（标签会以字面文字显示）：' + '；'.join(bad9[:5]))
    print(f"{'✅' if ok9 else '❌'} [9/9] agent 字段均已走 rich()（chips / caution / disclaimer）"
          + ('' if ok9 else f' — {len(bad9)} 处'))

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
    print('✅ 老站渲染守卫全部通过（9/9）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
