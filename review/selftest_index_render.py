#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_index_render 守卫的**反向自检**（2026-09-22 立 · 铁律 12「守卫自身须反向测试」）

为什么必须存在
--------------
守卫最容易死在「自以为在守、其实早已失效」上 —— 只验证「正向通过」永远发现不了。
本脚本对 [7]/[8]/[8b]/[9] 各项逐条制造回归（改坏代码 / 删样式 / 去掉 :not 守卫），
断言守卫**必须变红**，最后还原并断言恢复绿灯。

实测战果（2026-09-22 首次运行）：揪出 [9] 的判别模式漏了属性结尾的 `"`，
导致 chips / holding_map.caution 两处「回退到 esc()」根本抓不到 —— 已修。

隔离策略：同一改动同步落到「三份 index + 注入器」，使 [4]/[5] 保持绿，
从而确认红灯确实来自被测项本身（而不是顺带把 md5 弄不一致）。

用法:  python3 review/selftest_index_render.py     # 退出码 1 = 有漏网
"""
import io, os, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
P = sys.executable

P = sys.executable
INDEXES = ['index.html', 'index_template.html', 'deploy/index.html']
INJ = 'inject_feed_review.py'
V3 = ['review_v3/index.html', 'review_v3/index_hide89.html',
      'deploy/review_v3/index.html', 'deploy/review_v3/index_hide89.html']
FILES = INDEXES + [INJ]
ALL = FILES + V3
ORIG = {f: io.open(f, encoding='utf-8').read() for f in ALL}


def run_gate():
    r = subprocess.run([P, 'review/check_index_render.py'], capture_output=True, text=True)
    red = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith('❌')]
    return r.returncode, red


def restore():
    for f, c in ORIG.items():
        io.open(f, 'w', encoding='utf-8').write(c)


def apply(pairs, files):
    """对指定文件做替换；pairs = [(old, new, 期望次数)]。返回所有命中是否达标。"""
    ok = True
    for f in files:
        t = io.open(f, encoding='utf-8').read()
        for old, new, cnt in pairs:
            c = t.count(old)
            if c != cnt:
                ok = False
            t = t.replace(old, new)
        io.open(f, 'w', encoding='utf-8').write(t)
    return ok


_OLD1 = r'''.replace(/&lt;(\/?)(b|i|span)\s+class=(?:"([^"]*)"|'([^']*)')\s*\/?&gt;/g, _rtTag)'''
_OLD2 = r'''.replace(/&lt;span class="(dk-[a-z0-9-]+)"&gt;/g, (m, c) => (DKCLS.test(c) ? '<span class="' + c + '">' : m))'''
_OLD3 = r""".replace(/&amp;(lt|gt|amp|quot|#39);/g, '&$1;');"""


def rp(indent):
    """按缩进生成「退化为初版 rich()」的替换对。"""
    return [(indent + _OLD1, indent + _OLD2, 1), (indent + _OLD3, indent + ";", 1)]


UNESC = lambda i: [(i + r".replace(/&amp;(lt|gt|amp|quot|#39);/g, '&$1;');", i + ";", 1)]

CASES = [
    ("[7] 老站退回初版（双引号 span 专用）", rp("    "), FILES),
    ("[7] 老站去掉「解多余转义」",        UNESC("    "), FILES),
    ("[7] 放宽白名单：任意 class 放行",
     [("if (!cls || !cls.split(/\\s+/).every(c => DKCLS.test(c))) return m;",
       "if (false) return m;", 1)], FILES),
    ("[7] V3 退回初版（只动 V3 四副本）", rp("  "), V3),
    ("[8] 删掉 .dk-up 定义",
     [(".dk-up{color:var(--red);font-weight:600}\n", "", 1)], INDEXES),
    ("[8] .dk-risk 取值漂移（红↔绿颠倒）",
     [(".dk-risk{color:var(--green);font-weight:700}",
       ".dk-risk{color:var(--red);font-weight:700}", 1)], INDEXES),
    ("[8b] 去掉 :not 守卫（容器规则吃掉语义色）",
     [('.dr-note b:not([class*="dk-"]){color:var(--text)}',
       '.dr-note b{color:var(--text)}', 1)], V3),
    ("[8] V3 删掉 .dk-up",
     [(".dk-up{color:var(--red);font-weight:600}\n", "", 1)], V3),
    ("[9] chips 改回 esc()",
     [("""font-size:11px">' + rich(s) + '</span>').join('');""",
       """font-size:11px">' + esc(s) + '</span>').join('');""", 1)], FILES),
    ("[9] holding_map.caution 改回 esc()",
     [("""color:#f0b429;font-size:11px">' + rich(x) + '</span>').join('')""",
       """color:#f0b429;font-size:11px">' + esc(x) + '</span>').join('')""", 1)], FILES),
    ("[9] disclaimer 改回 esc()（含 V3）",
     [("rich(syn.disclaimer)", "esc(syn.disclaimer)", 1)], FILES + V3),
]

print("═══ 反向测试（每例都应变红）═══")
fails, hitwarn = [], []
try:
    for name, pairs, files in CASES:
        restore()
        hit = apply(pairs, files)
        rc, red = run_gate()
        caught = (rc == 1)
        if not caught:
            fails.append(name)
        if not hit:
            hitwarn.append(name)
        print(f"  {name:<32} rc={rc} {'✅ 已拦' if caught else '❌ 漏网'}"
              + ("" if hit else "  ⚠️替换未完全命中")
              + (f"\n        {red[0][:96]}" if caught else ""))
finally:
    restore()

rc, red = run_gate()
print(f"\n还原后 rc={rc} {'✅ PASS（9/9）' if rc == 0 else '❌ FAIL ' + str(red)}")
if hitwarn:
    print(f"⚠️ 有 {len(hitwarn)} 例替换未命中（测试本身失效）：{hitwarn}")
if fails:
    print(f"❌ 有 {len(fails)} 例漏网：{fails}")
    sys.exit(1)
if hitwarn:
    sys.exit(1)
print(f"✅ 反向测试 {len(CASES)}/{len(CASES)} 全部按预期拦截")
