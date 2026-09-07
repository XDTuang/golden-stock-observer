#!/usr/bin/env python3
"""投喂推演 → analysis.html 回填内容版式自检（2026-09-02 立 · 5 项）
   跑法：python3 review/check_analysis_style.py
   期望：5 项全过；任何失败=推演版式污染，必须修
   第 5 项专门防御"td 长内容撑破右侧屏幕"重复 bug（9/1 / 9/2 多次踩坑，9/2 治本）"""
import re, io, sys, subprocess
from collections import Counter

path = 'data/daily_review/analysis.html'
try:
    s = io.open(path, encoding='utf-8').read()
except FileNotFoundError:
    print(f'❌ {path} 不存在'); sys.exit(1)

# 1) 锚点唯一
c = re.findall(r'<!-- [0-9][^>]*-->', s)
dup = {k:v for k,v in Counter(c).items() if v>1}
ok1 = not dup
print(f"{'✅' if ok1 else '❌'} [1/4] 锚点注释唯一性: {'通过' if ok1 else '重复: '+str(dup)}")

# 2) 裸 <p> = 0
naked_p = re.findall(r'<p(?![^>]*style)[^>]*>', s)
ok2 = len(naked_p) == 0
print(f"{'✅' if ok2 else '❌'} [2/4] 裸 <p> 标签（无字号）: {len(naked_p)} 个（必须 0）")

# 3) 0.5 段含 2x2 grid
i5 = s.find('<!-- 0.5 深度判读 -->')
j5 = s.find('<!-- 1 ', i5) if i5>0 else -1
g5 = s[i5:j5].count('grid-template-columns:repeat(2,minmax(0,1fr))') if i5>0 and j5>0 else 0
ok3 = g5 >= 1
print(f"{'✅' if ok3 else '❌'} [3/4] 0.5 段含 2x2 grid 四象限: {g5} 处（必须 ≥1）")

# 4) 长文本 td 全覆盖 dr-wrap
bad = []
for m in re.finditer(r'<table.*?</table>', s, re.S):
    for t in re.findall(r'<td([^>]*)>([^<]{25,})', m.group(0)):
        if 'dr-wrap' not in t[0] and 'style' not in t[0]:
            bad.append(t[1][:50])
ok4 = len(bad) == 0
print(f"{'✅' if ok4 else '❌'} [4/4] 长文本 td 全覆盖 dr-wrap: {len(bad)} 个未覆盖")
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

# 5) [5/5] 🔴 CSS 治本防御：三处 index 的 .dr-tbl td 已默认自动换行
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
print(f"{'✅' if ok5 else '❌'} [5/5] .dr-tbl td 默认换行（三处 index CSS 治本防御）：{'通过' if ok5 else '未通过'}")
for f, ok, nb, wb in css_results:
    flag = '✅' if ok else '❌'
    print(f"      {flag} {f}: nowrap_in_drtbl={nb} wordbreak+overflow={wb}")

# 6) [6/6] 🔴 Design token 防御：7.3 段必须用 dk-main/dk-caution/dk-risk 语义色 class
#    用户反馈（9/2 23:38）："7.3 段字号随心所欲、颜色逻辑混乱"——根因是每次推演手写凭印象
#    选颜色字号，无设计 token 约束。治本：定义 dk-main/dk-caution/dk-risk/dk-data/dk-neutral
#    语义颜色 + dr-tag 12.5px 加粗 + dr-card ul/li 12.5px var(--text) 主色统一。
#    此检查强制 7.3 段至少各 1 处 dk-main/caution/risk（避免漏标语义色）；并验证
#    #drAnalysis 范围内至少 5 处 dk-* 用法（说明 design token 体系已落地）。
#    内联 color/font-size 数量仅做参考警告（历史推演已有大量内联，不阻断合入，
#    但 ≥20 处时警告——后续可逐步重构到 dk-*）。
ok6 = True
note6 = []
sec73_start = s.find('<!-- 7.3 开盘指引 -->')
sec73_end = s.find('<!-- 8 数据自检 -->') if sec73_start > 0 else -1
sec73 = s[sec73_start:sec73_end] if sec73_end > 0 else ''
sec73_main = len(re.findall(r'\bdk-main\b', sec73))
sec73_caution = len(re.findall(r'\bdk-caution\b', sec73))
sec73_risk = len(re.findall(r'\bdk-risk\b', sec73))
if sec73_main < 1 or sec73_caution < 1 or sec73_risk < 1:
    note6.append(f'⚠️ 7.3 段语义色不全：dk-main={sec73_main} dk-caution={sec73_caution} dk-risk={sec73_risk}（应各 ≥1）')
    ok6 = False
# 7.3 段外的 dk-* 总数（证明 design token 体系已落地）
total_dk = len(re.findall(r'\bdk-(?:main|caution|risk|data|neutral)\b', s))
print(f"{'✅' if ok6 else '❌'} [6/6] Design token 防御（7.3 段 dk-main/caution/risk ≥1）：{'通过' if ok6 else '未通过'}")
for n in note6: print(f"      {n}")
print(f"      统计：7.3 段 dk-main={sec73_main} dk-caution={sec73_caution} dk-risk={sec73_risk} / 全局 dk-*={total_dk}（应 ≥5）")
if total_dk < 5:
    note6.append(f'⚠️ 全局 dk-* 仅 {total_dk} 处（应 ≥5）')
    ok6 = ok6 and False
# 总结
all_ok = ok1 and ok2 and ok3 and ok4 and ok5 and ok6
print(f"\n{'✅ 全部通过' if all_ok else '❌ 存在版式问题，请修复'}")
sys.exit(0 if all_ok else 1)
