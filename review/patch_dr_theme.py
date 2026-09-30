#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DR-THEME-BRIDGE · 每日复盘 tab 暗色适配补丁（幂等）

背景（2026-09-30 用户报障「夜间模式有超长一大段仍是浅色」）
  · analysis.html 是**自包含**的：自带 <style> 里 `:root{--bg:#fff;--text:#1a1f2e;…}`（浅色）
    + `@media (prefers-color-scheme:dark){:root{…}}`（暗色，跟随**系统**偏好）。
  · 它被注入 index.html 的 `#drAnalysis` 容器时，`drScopeInjectedStyles()` 会把裸选择器
    作用域化 → `:root{…}` 变成 `#drAnalysis{…}`，特异性 (1,0,0)。
  · 主站主题是 `[data-theme="dark"]`（挂在 html 上，特异性 (0,1,0)）→ **容器自带声明在其
    子树内优先**，于是主站切暗色时该 tab 内部变量仍取浅色 ⇒ 整篇推演正文白底深字。
  · 而 `@media (prefers-color-scheme:dark)` 与主站 `data-theme` 无关：系统浅色时永不生效。

修法
  ① `:root` 定义桥接变量 `--dr-*`（light 值 = analysis.html 原值，零观感变化）；
  ② `[data-theme="dark"]` 定义 `--dr-*` 的暗色值（对齐主站暗色板）；
  ③ `html #drAnalysis{ --bg: var(--dr-bg); … }` —— (1,0,1) **高于**注入的 (1,0,0)，
     把重叠变量重声明为桥接值 → 随 `data-theme` 切换；
  ④ 同时免疫 `@media (prefers-color-scheme:dark)` 对浅色站点的反向污染。

落点铁律
  🔴 本块**必须留在 <head> 内**，不得移入「每日复盘」tab 区块 —— 该区块由
     `inject_daily_review_tab.py` 整段替换（TAB_BLOCK/JS_BLOCK），改动会被静默回退。

维护
  analysis.html 的 `:root` 若**新增与主站同名**的变量而下方清单未同步 → 又会静默锁死浅色
  （「有定义无桥接」型静默失效）。守卫 = `review/check_index_render.py [2b]`，
  它断言「桥接清单 ⊇ analysis.html :root 的变量集合」，且 `:root` / `[data-theme="dark"]`
  两侧的 `--dr-*` 集合与桥接需求完全相等。

用法
  python3 review/patch_dr_theme.py            # 落盘（幂等：有则整体替换，无则 </head> 前插入）
  python3 review/patch_dr_theme.py --check    # 只校验，有变化则 exit 1
"""
import hashlib
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['index.html', 'index_template.html', 'deploy/index.html']

MARK_BEGIN = '<!-- DR-THEME-BRIDGE-BEGIN -->'
MARK_END = '<!-- DR-THEME-BRIDGE-END -->'

BLOCK = MARK_BEGIN + '''
<style id="dr-theme-bridge">
/* ═══ DR-THEME-BRIDGE v1 · 2026-09-30 ═══
   问题：analysis.html 自带 <style> 的 :root 被 drScopeInjectedStyles() 作用域化为
   `#drAnalysis{--bg:#fff;--text:#1a1f2e;…}`（浅色值），特异性 (1,0,0) 高于主站
   `[data-theme="dark"]` 对 html 的自定义属性 → 暗色模式下该 tab 内部变量仍为浅色
   （白底/深字），整篇推演正文「超长一大段」保持亮色。
   其暗色分支挂在 `@media (prefers-color-scheme:dark)`（跟随系统偏好），与主站
   `data-theme` 无关 → 主站切暗色时永不生效。
   修法：① :root 定义 `--dr-*` 桥接变量；② 用 `html #drAnalysis`（(1,0,1) > 注入的 (1,0,0)）
        把重叠变量重声明为桥接值。
   → light 下取值与 analysis.html 原值完全一致（零观感变化）；dark 下对齐主站暗色；
     并免疫 `@media (prefers-color-scheme:dark)` 对浅色站点的污染。
   🔴 维护：analysis.html 的 :root 若新增「与主站同名」的变量，须同步加入下方清单。
      补丁：review/patch_dr_theme.py ｜ 守卫：review/check_index_render.py [2b]
   🔴 本块必须留在 <head> 内 —— 不得移入「每日复盘」tab 区块（该区块由
      inject_daily_review_tab.py 整段替换，改动会被静默回退）。 */
:root {
  --dr-bg: #fff;
  --dr-bg-card: #f8f9fb;
  --dr-bg-subtle: #f1f3f6;
  --dr-border: #e2e6ec;
  --dr-text: #1a1f2e;
  --dr-text-secondary: #3c4453;
  --dr-text-muted: #6b7280;
  --dr-accent: #4c8bf5;
  --dr-red: #e74c3c;
  --dr-orange: #f59e0b;
  --dr-green: #16a34a;
  --dr-blue: #4c8bf5;
}
[data-theme="dark"] {
  --dr-bg: #0f1421;
  --dr-bg-card: #151926;
  --dr-bg-subtle: #1a1f2e;
  --dr-border: #252b3b;
  --dr-text: #e8ebf2;
  --dr-text-secondary: #9aa1b8;
  --dr-text-muted: #656c82;
  --dr-accent: #e3b341;
  --dr-red: #ff7b7b;
  --dr-orange: #f6ad55;
  --dr-green: #4ade80;
  --dr-blue: #63b3ed;
}
html #drAnalysis {
  --bg: var(--dr-bg);
  --bg-card: var(--dr-bg-card);
  --bg-subtle: var(--dr-bg-subtle);
  --border: var(--dr-border);
  --text: var(--dr-text);
  --text-secondary: var(--dr-text-secondary);
  --text-muted: var(--dr-text-muted);
  --accent: var(--dr-accent);
  --red: var(--dr-red);
  --orange: var(--dr-orange);
  --green: var(--dr-green);
  --blue: var(--dr-blue);
}
</style>
''' + MARK_END

CHECK = '--check' in sys.argv


def patch(text):
    """返回 (新文本, 动作) —— 动作 ∈ {'replaced','inserted','unchanged'}"""
    if MARK_BEGIN in text:
        i = text.index(MARK_BEGIN)
        j = text.index(MARK_END) + len(MARK_END)
        old = text[i:j]
        if old == BLOCK.strip():
            return text, 'unchanged'
        return text[:i] + BLOCK.strip() + text[j:], 'replaced'
    # 首次插入：</head> 前
    k = text.index('</head>')
    return text[:k] + BLOCK.strip() + '\n\n' + text[k:], 'inserted'


def main():
    results = []
    for f in FILES:
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            results.append((f, 'missing', 0, 0))
            print(f"  {f:24s} missing")
            continue
        raw = open(p, 'rb').read()
        bom = raw.startswith(b'\xef\xbb\xbf')
        s = raw.decode('utf-8-sig')
        new, act = patch(s)
        if act != 'unchanged' and not CHECK:
            open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
        results.append((f, act, len(s.encode()), len(new.encode())))
        print(f"  {f:24s} {act:10s} {len(s.encode()):>8} -> {len(new.encode()):>8} B")

    print()
    md5s = [hashlib.md5(open(os.path.join(BASE, f), 'rb').read()).hexdigest()
            for f in FILES if os.path.exists(os.path.join(BASE, f))]
    same = len(set(md5s)) == 1
    print('  三处 md5:', [m[:10] for m in md5s], '→', '✅ 一致' if same else '⚠️ 不一致')

    if CHECK:
        bad = [f for f, a, *_ in results if a != 'unchanged']
        print('  --check:', '✅ 全部已是最新' if not bad else f'⚠️ 待更新 {bad}')
        sys.exit(0 if not bad and same else 1)


if __name__ == '__main__':
    main()
