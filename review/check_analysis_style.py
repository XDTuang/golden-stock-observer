#!/usr/bin/env python3
"""投喂推演 → analysis.html 回填内容版式自检（2026-09-02 立）
   跑法：python3 review/check_analysis_style.py
   期望：4 项全过；任何失败=推演版式污染，必须修"""
import re, io, sys
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

# 总结
all_ok = ok1 and ok2 and ok3 and ok4
print(f"\n{'✅ 全部通过' if all_ok else '❌ 存在版式问题，请修复'}")
sys.exit(0 if all_ok else 1)
