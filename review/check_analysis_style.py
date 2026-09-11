#!/usr/bin/env python3
"""投喂推演 → analysis.html 回填内容版式自检（2026-09-02 立 · 11 项）
   跑法：python3 review/check_analysis_style.py
   期望：全部通过；任何失败=推演版式污染，必须修
   第 5 项专门防御"td 长内容撑破右侧屏幕"重复 bug（9/1 / 9/2 多次踩坑，9/2 治本）
   第 7 项（2026-09-10 增）防御"analysis.html 自包含 style 越界规则经注入污染整站"（整站曾被限宽 980px）
   第 8 项（2026-09-11 增）防御 7.1 结论句退回"只有加粗无色"
   第 9 项（2026-09-11 增）防御"class 有标记无定义"静默失效（曾实测 dk-dn/dr-caution/dr-wrap 三例）
   第 10 项（2026-09-11 增）防御"JS 引用无容器"空转静默失效（曾实测 drTblA/drTblH/drTblUs/drTblObs/drCmdBtn/allGrid
       六例；见 Obsidian 30-PRINCIPLES/改版自检与静默失效防御）
   第 11 项（2026-09-11 增）防御"7.x 段落顺序错 + 裸段号硬编码"复发 bug（用户报「7 段排在 7.4 后、7.3 未见」；
       顺序自 e545530 起 7 个版本一直是 7.2→7.4→7.3；段号硬编码曾在 229a20a 修过又被 0070ddd 静默回退）"""
import re, io, sys, subprocess, glob
from collections import Counter

path = 'data/daily_review/analysis.html'
try:
    s = io.open(path, encoding='utf-8').read()
except FileNotFoundError:
    print(f'❌ {path} 不存在'); sys.exit(1)

# 0) UTF-8 BOM 守卫（2026-09-09 治本：fragment 无 <head>/<meta charset>，file:// 直开必须靠 BOM 声明编码，
#    否则浏览器按系统 locale（中文=GBK/GB18030）探测 → 全中文乱码。任何重写丢 BOM 必须在此红灯）
raw = io.open(path, 'rb').read()
ok0 = raw.startswith(b'\xef\xbb\xbf')
print(f"{chr(10004) if ok0 else chr(10060)} [0] UTF-8 BOM 守卫(file://直开编码自声明): {'通过' if ok0 else 'FAIL: analysis.html 必须以 UTF-8 BOM(efbbbf)开头，重写时勿丢'}")

# 1) 锚点唯一
c = re.findall(r'<!-- [0-9][^>]*-->', s)
dup = {k:v for k,v in Counter(c).items() if v>1}
ok1 = not dup
print(f"{'✅' if ok1 else '❌'} [1/11] 锚点注释唯一性: {'通过' if ok1 else '重复: '+str(dup)}")

# 2) 裸 <p> = 0
naked_p = re.findall(r'<p(?![^>]*style)[^>]*>', s)
ok2 = len(naked_p) == 0
print(f"{'✅' if ok2 else '❌'} [2/11] 裸 <p> 标签（无字号）: {len(naked_p)} 个（必须 0）")

# 3) 0.5 段含 2x2 grid
i5 = s.find('<!-- 0.5 深度判读 -->')
j5 = s.find('<!-- 1 ', i5) if i5>0 else -1
g5 = s[i5:j5].count('grid-template-columns:repeat(2,minmax(0,1fr))') if i5>0 and j5>0 else 0
ok3 = g5 >= 1
print(f"{'✅' if ok3 else '❌'} [3/11] 0.5 段含 2x2 grid 四象限: {g5} 处（必须 ≥1）")

# 4) 长文本 td 全覆盖 dr-wrap
bad = []
for m in re.finditer(r'<table.*?</table>', s, re.S):
    for t in re.findall(r'<td([^>]*)>([^<]{25,})', m.group(0)):
        if 'dr-wrap' not in t[0] and 'style' not in t[0]:
            bad.append(t[1][:50])
ok4 = len(bad) == 0
print(f"{'✅' if ok4 else '❌'} [4/11] 长文本 td 全覆盖 dr-wrap: {len(bad)} 个未覆盖")
if bad:
    for b in bad[:3]: print(f"      → {b}")

# 字号分布
fs = re.findall(r'font-size:([0-9.]+px)', s)
fs_dist = Counter(fs)
print(f"\n字号分布: {dict(fs_dist.most_common())}")
fs_125 = fs_dist.get('12.5px', 0)
fs_total = sum(fs_dist.values())
fs_pct = fs_125/fs_total*100 if fs_total else 0
print(f"12.5px 占比: {fs_pct:.1f}%（应 >80%；0 段卡片值 13.5px 允许少量）")

# 5) [5/11] 🔴 CSS 治本防御：三处 index 的 .dr-tbl td 已默认自动换行
#    原 root cause：.dr-tbl td 默认 white-space:nowrap → 长内容撑破右侧屏幕
#    治本（9/2 23:30）：删 nowrap + 加 word-break:break-word + overflow-wrap:anywhere + min-width:0
#    此检查确保三处 index CSS 都已治本；如未改、有回归 → ❌
ok5 = True
css_results = []
for f in ['index.html', 'index_template.html', 'deploy/index.html']:
    try:
        css_text = io.open(f, encoding='utf-8').read()
        has_nowrap_in_drtbl = re.search(r'\.dr-tbl\s+th\s*,\s*\.dr-tbl\s+td\s*\{[^}]*white-space\s*:\s*nowrap', css_text)
        has_wordbreak = 'word-break:break-word' in css_text and 'overflow-wrap:anywhere' in css_text
        ok_this = (not has_nowrap_in_drtbl) and has_wordbreak
        css_results.append((f, ok_this, bool(has_nowrap_in_drtbl), has_wordbreak))
        if not ok_this: ok5 = False
    except FileNotFoundError:
        css_results.append((f, False, 'NO FILE', False))
        ok5 = False
print(f"{'✅' if ok5 else '❌'} [5/11] .dr-tbl td 默认换行（三处 index CSS 治本防御）：{'通过' if ok5 else '未通过'}")
for f, ok, nb, wb in css_results:
    flag = '✅' if ok else '❌'
    print(f"      {flag} {f}: nowrap_in_drtbl={nb} wordbreak+overflow={wb}")

# 6) [6/11] 🔴 Design token 防御：7.3 段必须用 dk-main/dk-caution/dk-risk 语义色 class
#    用户反馈（9/2 23:38）："7.3 段字号随心所欲、颜色逻辑混乱"——根因是每次推演手写凭印象
#    选颜色字号，无设计 token 约束。治本：定义 dk-main/dk-caution/dk-risk/dk-data/dk-neutral
#    语义颜色 + dr-tag 12.5px 加粗 + dr-card ul/li 12.5px var(--text) 主色统一。
#    此检查强制 7.3 段至少各 1 处 dk-main/caution/risk（避免漏标语义色）；并验证
#    #drAnalysis 范围内至少 5 处 dk-* 用法（说明 design token 体系已落地）。
#    内联 color/font-size 数量仅做参考警告（历史推演已有大量内联，不阻断合入，
#    但 ≥20 处时警告——后续可逐步重构到 dk-*）。
ok6 = True
note6 = []
sec73_m = re.search(r'<!-- 7\.[34] ', s)   # 兼容老版 7.3 agent 卡 与 新版 7.4 agent 预案（7.3 让位 JS 规则版）
sec73_start = sec73_m.start() if sec73_m else -1
sec73_end = s.find('<!-- 8 数据自检 -->') if sec73_start > 0 else -1
sec73 = s[sec73_start:sec73_end] if sec73_end > 0 else ''
sec73_main = len(re.findall(r'\bdk-main\b', sec73))
sec73_caution = len(re.findall(r'\bdk-caution\b', sec73))
sec73_risk = len(re.findall(r'\bdk-risk\b', sec73))
if sec73_main < 1 or sec73_caution < 1 or sec73_risk < 1:
    note6.append(f'⚠️ 7.3/7.4 操作预案段语义色不全：dk-main={sec73_main} dk-caution={sec73_caution} dk-risk={sec73_risk}（应各 ≥1）')
    ok6 = False
# 7.3 段外的 dk-* 总数（证明 design token 体系已落地）
total_dk = len(re.findall(r'\bdk-(?:main|caution|risk|data|neutral)\b', s))
print(f"{'✅' if ok6 else '❌'} [6/11] Design token 防御（7.3/7.4 操作预案段 dk-main/caution/risk ≥1）：{'通过' if ok6 else '未通过'}")
for n in note6: print(f"      {n}")
print(f"      统计：7.3/7.4 段 dk-main={sec73_main} dk-caution={sec73_caution} dk-risk={sec73_risk} / 全局 dk-*={total_dk}（应 ≥5）")
if total_dk < 5:
    note6.append(f'⚠️ 全局 dk-* 仅 {total_dk} 处（应 ≥5）')
    ok6 = ok6 and False
# 7) [7/11] 🔴 注入样式作用域化守卫（2026-09-10）
#    analysis.html 自带 <style> 里有 body{padding:20px;max-width:980px;margin:0 auto} 与 :root{...} 等
#    "越界规则"（为 file:// 独立阅读而写），经 index.html 的 ana.innerHTML 注入后会【全局生效】：
#    曾把整站限宽 980px（.main 的 max-width:1480px 沦为死代码）、并覆盖主站配色变量与字体。
#    治本：index.html 的 drScopeInjectedStyles(ana) 在注入后把越界规则作用域化到 #drAnalysis
#    （body/html 丢弃、:root→#drAnalysis、裸标签加前缀、.dr-* 类规则保留）。
#    此检查确保三份 index 均保留该调用——缺失即整站会再次变窄。
ok7 = True
note7 = []
for f in ['index.html', 'index_template.html', 'deploy/index.html']:
    try:
        t = io.open(f, encoding='utf-8').read()
    except FileNotFoundError:
        note7.append(f'⚠️ 缺少 {f}'); ok7 = False; continue
    has_fn = 'function drScopeInjectedStyles' in t
    has_call = 'drScopeInjectedStyles(ana);' in t
    if not (has_fn and has_call):
        note7.append(f'⚠️ {f}: 定义={has_fn} 调用={has_call}（应均 True；缺失会导致 analysis.html 注入样式污染整站宽度/配色）')
        ok7 = False
print(f"{'✅' if ok7 else '❌'} [7/11] 注入样式作用域化守卫（analysis.html 越界规则不污染整站）：{'通过' if ok7 else '未通过'}")
for n in note7: print(f"      {n}")

# 8) [8/11] 🔴 7.1 段结论句语义色守卫（2026-09-11）
#    用户反馈：7.1「内容」格每段最后一句是结论句，原先只用 <b> 加粗 → 不够醒目，
#    且无法区分「可执行 / 有条件 / 风险回避 / 待验证」四种性质。
#    治本：build_k3_conclusions.py 生成四类语义色（与第二列 dr-up/up-caution/dn 色系呼应）
#      k3c-go(红) / k3c-cond(橙) / k3c-risk(绿) / k3c-verify(蓝) + .k3c-legend 图例。
#    此检查确保 7.1 段【每一数据行】的结论句都带 k3c-* 类，且 CSS 与图例各仅 1 份
#    —— 漏标会让该行结论退回「只有加粗」的旧观感（用户明确反馈过的问题）。
ok8 = True
note8 = []
try:
    _i71 = s.find('7.1 · K3')
    _j71 = s.find('<!-- 7.2 重点观测股')
    _s71 = s[_i71:_j71] if (_i71 >= 0 and _j71 > _i71) else ''
    if not _s71:
        note8.append('⚠️ 未定位到 7.1 段（锚点 `7.1 · K3` / `<!-- 7.2 重点观测股` 缺失）')
        ok8 = False
    else:
        _rows = [r for r in re.findall(r'<tr>(.*?)</tr>', _s71, re.S)
                 if len(re.findall(r'<td', r)) >= 3]
        _miss = []
        for _r in _rows:
            _tds = re.findall(r'<td[^>]*>(.*?)</td>', _r, re.S)
            if len(_tds) < 3:
                continue
            if 'class="k3c k3c-' not in _tds[2]:
                _theme = re.sub(r'<[^>]+>', '', _tds[0]).strip()
                _miss.append(_theme)
        _n_cls = s.count('class="k3c k3c-')
        _n_css = s.count('/* K3C-CONCLUSION-CSS v1')
        _n_lgd = s.count('class="k3c-legend"')
        print(f"      7.1 数据行={len(_rows)} 已上色={len(_rows) - len(_miss)}"
              f" | K3C CSS 块={_n_css}(须=1) 图例={_n_lgd}(须=1) 结论条={_n_cls}")
        if _miss:
            note8.append(f'⚠️ 未上色 {len(_miss)} 行：{_miss}（跑 python3 build_k3_conclusions.py）')
            ok8 = False
        if _n_css != 1:
            note8.append(f'⚠️ K3C CSS 块数={_n_css}（须=1；重复插入会导致样式叠加）')
            ok8 = False
        if _n_lgd != 1:
            note8.append(f'⚠️ k3c 图例数={_n_lgd}（须=1）')
            ok8 = False
except Exception as _e:
    note8.append(f'⚠️ 检查异常：{_e}')
    ok8 = False
print(f"{'✅' if ok8 else '❌'} [8/11] 7.1 结论句语义色（k3c-* 全行覆盖 + CSS/图例唯一）：{'通过' if ok8 else '未通过'}")
for n in note8: print(f"      {n}")

# 9) [9/11] 🔴 未定义类守卫（2026-09-11 自检新增）
#    实测：dk-dn(13 处) / dr-caution(4 处) / dr-wrap(54 处) 在 analysis.html 中使用，
#    但全站 CSS（analysis.html 自包含 style + 三处 index）均无定义
#    → 这些类静默退化为「无色 / 无效果」，用户看到的只是普通文字。
#    这与用户反馈的「结论句不够醒目」是同一类问题（有标记、无样式），故立守卫永久防御。
ok9 = True
note9 = []
try:
    _defined = set(re.findall(r'\.([A-Za-z][\w-]*)',
                              "\n".join(re.findall(r'<style[^>]*>(.*?)</style>', s, re.S))))
    for _f9 in ['index.html', 'index_template.html', 'deploy/index.html']:
        try:
            _defined |= set(re.findall(r'\.([A-Za-z][\w-]*)', io.open(_f9, encoding='utf-8').read()))
        except FileNotFoundError:
            note9.append(f'⚠️ 缺少 {_f9}（定义集合可能不全）')
    _used = Counter()
    for _m9 in re.finditer(r'class="([^"]+)"', s):
        for _cl in _m9.group(1).split():
            _used[_cl] += 1
    _miss = [(k, v) for k, v in _used.most_common() if k not in _defined]
    if _miss:
        note9.append('⚠️ 使用但无 CSS 定义（会静默无色/无样式）：' +
                     '、'.join(f'{k}×{v}' for k, v in _miss))
        note9.append('   → 修法：在 analysis.html 自包含 <style> 内补类定义，或改用已定义的语义色类')
        ok9 = False
    # 关键语义类必须存在（即使在当前版本暂时未被使用）——防被误删后同类问题复发
    _KEY9 = ['dk-dn', 'dr-caution', 'dr-wrap', 'dk-main', 'dk-caution', 'dk-risk',
             'dk-data', 'dk-neutral', 'dr-up', 'dr-dn']
    _lack9 = [k for k in _KEY9 if k not in _defined]
    if _lack9:
        note9.append(f'⚠️ 关键语义类定义缺失：{_lack9}')
        ok9 = False
    if ok9:
        print(f"      扫描 {len(_used)} 个在用 class，全部有定义 ✓；10 个关键语义类齐备 ✓")
except Exception as _e:
    note9.append(f'⚠️ 检查异常：{_e}')
    ok9 = False
print(f"{'✅' if ok9 else '❌'} [9/11] 未定义类守卫（在用 class 必须有 CSS 定义）：{'通过' if ok9 else '未通过'}")
for n in note9: print(f"      {n}")

# 10) [10/11] 🔴 空转引用守卫（2026-09-11 新增 · 铁律 15 五维自检法第 2 维「容器·引用反查」）
#     实测：drTblA / drTblH / drTblUs / drTblObs / drCmdBtn / allGrid 六处 getElementById
#     的目标在全部活文件中都不存在 → 原代码靠 `if (el)` 或无守卫静默空转、永不生效。
#     判据：孤儿 id **允许存在**（可能由注入器 HTML 片段或 JS 动态创建提供），
#           但每个引用点必须有**空值守卫** —— 无守卫 = 一旦容器出现/消失即 TypeError。
ok10 = True
note10 = []
try:
    # ① 收集所有合法 id 来源
    _src = set()
    for _f10 in ['index.html', 'index_template.html', 'deploy/index.html']:
        try:
            _src |= set(re.findall(r'id="([^"]+)"', io.open(_f10, encoding='utf-8').read()))
        except FileNotFoundError:
            note10.append(f'⚠️ 缺少 {_f10}（id 来源集合可能不全）')
    _src |= set(re.findall(r'id="([^"]+)"', s))                     # analysis.html 注入内容
    for _f10 in glob.glob('inject_*.py') + glob.glob('*_snippet*.js'):   # 注入器 HTML 片段
        try:
            _t = io.open(_f10, encoding='utf-8').read()
            _src |= set(re.findall(r'id=\\?"([^"\\]+)\\?"', _t))
        except Exception:
            pass
    _idx = io.open('index.html', encoding='utf-8').read()
    _src |= set(re.findall(r"\.id\s*=\s*['\"]([^'\"\s]+)['\"]", _idx))          # JS 动态创建
    _src |= set(re.findall(r"setAttribute\(\s*['\"]id['\"]\s*,\s*['\"]([^'\"\s]+)['\"]", _idx))

    # ② 找孤儿引用，并检查引用点 ±2 行内是否有守卫
    _G = (r'if\s*\(\s*!\s*\w+\s*\)\s*return', r'if\s*\(\s*\w+\s*\)', r'\?\.', r'\|\|\s*\{\}')
    _lines = _idx.split('\n')
    _refs10 = list(re.finditer(r"getElementById\(\s*'([^']+)'\s*\)", _idx))
    _orph10 = {}
    for _m10 in _refs10:
        _id10 = _m10.group(1)
        if _id10 in _src:
            continue
        _orph10.setdefault(_id10, []).append(_idx[:_m10.start()].count('\n'))
    _bad10 = []
    for _id10, _lns10 in _orph10.items():
        _ung = [L for L in _lns10
                if not any(re.search(g, '\n'.join(_lines[max(0, L - 1):L + 3])) for g in _G)]
        if _ung:
            _bad10.append((_id10, _ung))
    if _bad10:
        note10.append('⚠️ 孤儿 id 且**无空值守卫**（一旦走到即 TypeError）：' +
                      '、'.join(f'{k}(行 {",".join(map(str, v))})' for k, v in _bad10))
        note10.append('   → 修法：删除该引用，或改为 '
                      '`const el = document.getElementById(..); if (!el) return;`')
        ok10 = False
    else:
        print(f"      扫描 {len(_refs10)} 个 getElementById 引用；"
              f"孤儿 {len(_orph10)} 个（均有空值守卫）✓")
except Exception as _e:
    note10.append(f'⚠️ 检查异常：{_e}')
    ok10 = False
print(f"{'✅' if ok10 else '❌'} [10/11] 空转引用守卫（JS 引用的 id 须有来源或空值守卫）："
      f"{'通过' if ok10 else '未通过'}")
for n in note10: print(f"      {n}")

# 11) [11/11] 🔴 段落顺序 + 段号硬编码守卫（2026-09-11 新增 · 用户报「7 段排在 7.4 后、7.3 未见」）
#     两个**复发**bug（都有前科，必须机器化）：
#     a. analysis.html 的 7.x **段落顺序错**：历史一直是 7.1→7.2→7.4→7.3（从 e545530 起 7 个版本全部如此），
#        而 build_obs_section.py 的 END_ANCHOR 还写着 "<!-- 7.4 操作预案" —— **迁就了错误顺序**，把它固化。
#     b. index.html 的 h7 段**硬编码裸段号 '7 · '** 覆盖标题 → 页面上 7.3 显示成「7 ·」。
#        该行曾在 229a20a 修为 '7.3 · '，但 0070ddd 重构 drDeriveSections 时基于旧副本编辑 → **静默回退**
#        （与铁律 9 注入器快照回退同源）。治本 = 改为从原标题提取 7.x 前缀，不再写死。
ok11 = True
note11 = []
try:
    # a) 7.x 段落顺序
    _order11 = []
    for _m11 in re.finditer(r'<div class="dr-h"[^>]*>(.*?)</div>', s, re.S):
        _t11 = re.sub(r'<[^>]+>', '', _m11.group(1)).strip()
        _k11 = re.match(r'^(7\.\d)', _t11)
        if _k11:
            _order11.append(_k11.group(1))
    if _order11 != sorted(_order11):
        note11.append(f'⚠️ 7.x 段落顺序错：{" → ".join(_order11)}（应为 7.1 → 7.2 → 7.3 → 7.4）')
        note11.append('   → 修法：把 7.4 块整体移到 7.3 块之后；'
                      '同步把 build_obs_section.py 的 END_ANCHOR 改为 "<!-- 7.3 次日开盘指引"（两者必须同时改）')
        ok11 = False
    elif _order11 != ['7.1', '7.2', '7.3', '7.4']:
        note11.append(f'⚠️ 7.x 段落不齐：{" → ".join(_order11)}（应 7.1/7.2/7.3/7.4 各一段）')
        ok11 = False

    # b) 裸段号硬编码（须为 'x.y · ' 形式，纯数字 = 会吃掉小数段号）
    _BAD11 = re.compile(r"textContent\s*=\s*'(\d+)\s·\s")
    for _f11 in ['index.html', 'index_template.html', 'deploy/index.html',
                 'daily_review_tab_snippet.js', 'inject_daily_review_tab.py']:
        try:
            _x11 = io.open(_f11, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        for _ln11 in _x11.split('\n'):
            _st11 = _ln11.strip()
            if _st11.startswith('//') or _st11.startswith('#') or _st11.startswith('*'):
                continue
            if _BAD11.search(_ln11):
                note11.append(f'⚠️ {_f11} 存在**裸段号硬编码**（会覆盖小数段号）：{_st11[:88]}')
                ok11 = False

    if ok11:
        print(f"      7.x 段落顺序 = {' → '.join(_order11)} ✓；5 个文件无裸段号硬编码 ✓")
except Exception as _e:
    note11.append(f'⚠️ 检查异常：{_e}')
    ok11 = False
print(f"{'✅' if ok11 else '❌'} [11/11] 段落顺序 + 段号守卫：{'通过' if ok11 else '未通过'}")
for n in note11: print(f"      {n}")

# 总结
all_ok = (ok0 and ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8 and ok9 and ok10 and ok11)
print(f"\n{'✅ 全部通过' if all_ok else '❌ 存在版式问题，请修复'}")
sys.exit(0 if all_ok else 1)
