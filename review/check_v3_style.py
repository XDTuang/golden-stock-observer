#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V3 独立版（review_v3/）守卫自检（2026-09-11 立 · 8 项）

跑法：python3 review/check_v3_style.py
期望：全部通过；任何失败 = V3 存在副本漂移或渲染缺陷，必须修。

立此脚本的原因（2026-09-11 全站自检实测）：
  1. `deploy/review_v3/index_hide89.html` 落后线上 1 个版本（86801 vs 88533 字节），
     其内容停留在 2026-09-08 —— 含两处已知 bug 的旧实现：
       · `num()` 缺兜底、`toLocaleString()` 直调 → us_sox.close=null 时抛 TypeError
         → main() reject → 全页永久卡「加载中…」
       · 缠论买点仍从 obs_deduce 读（该源无 chan 字段）→ 该列全为「—待补」
     而 `review/REVIEW_SOP.md` 的推送清单里仍列着 index_hide89.html
     → 一旦推送即把线上正确版**回退成旧 bug 版**。属防回退红线范畴。
  2. V3 的结论卡此前仅「金色标题 + 无色正文」，且 chips 仍用旧模式
     `esc(asText(x) || x)`（白名单缺 event，对象会渲染成 [object Object]）。
  3. V3 是四副本结构（根 index / 根 hide89 / deploy index / deploy hide89），
     无生成脚本、纯手工同步 → 必然漂移，需要机器守卫。
  4. （2026-09-11 增 · [8/8]）V3 第 6 段「重点观测股推演」原为「32 行平表 + 6 列」，
     窄视口折行、重点票与全池票无区分。已按老站 daily_review 7.2 段改造为
     **分层折叠卡**（L2 重点票三情景 + L1 全池关键位），交互走原生 <details> + 纯 CSS。
     折叠卡共有 27 个 obs-*/b-*/kl-* 类，任一缺 CSS 定义即「有标记无样式」静默退化
     （与老站 dk-dn 同类）→ 必须机器守卫。
"""
import re
import sys
import hashlib
import os

ROOT = 'review_v3/index.html'
COPIES = [
    'review_v3/index.html',
    'review_v3/index_hide89.html',
    'deploy/review_v3/index.html',
    'deploy/review_v3/index_hide89.html',
]

fails = []


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


# ── [1/8] 四副本必须逐字节一致 ────────────────────────────────────────────
# index_hide89.html 经核实与 index.html 无任何差异（"hide89" 关键词 0 次，
# 不含隐藏 8/9 段逻辑），且无脚本生成、无页面引用 → 它就是 index 的同内容副本。
# 既然同内容，就必须保持一致，否则会出现「推送旧副本覆盖线上新版」的回退事故。
ok1 = True
note1 = []
existing = [p for p in COPIES if os.path.exists(p)]
missing = [p for p in COPIES if not os.path.exists(p)]
if missing:
    note1.append(f'⚠️ 缺失副本：{missing}')
    ok1 = False
if len(existing) >= 2:
    hashes = {p: md5(p) for p in existing}
    uniq = set(hashes.values())
    if len(uniq) != 1:
        ok1 = False
        note1.append('⚠️ 副本内容不一致（会导致推送后线上版本回退）：')
        for p, h in hashes.items():
            note1.append(f'      {h[:10]}  {len(open(p, "rb").read()):>7} B  {p}')
        note1.append('   → 修法：cp review_v3/index.html 到其余三份（V3 为同内容多副本结构）')
    else:
        note1.append(f'{len(existing)} 份副本逐字节一致 ✓ md5={list(uniq)[0][:10]}')
print(f"{'✅' if ok1 else '❌'} [1/8] 四副本一致性（防推送旧副本回退线上）：{'通过' if ok1 else '未通过'}")
for n in note1:
    print(f'      {n}')

if not os.path.exists(ROOT):
    print(f'❌ {ROOT} 不存在，后续检查中止')
    sys.exit(1)
s = open(ROOT, encoding='utf-8').read()

# ── [2/8] dk-* 语义色定义齐备且唯一 ─────────────────────────────────────
# 结论卡按性质着色依赖这套类；缺失即静默无色（与老站 dk-dn 同类问题）。
ok2 = True
note2 = []
DK = ['dk-main', 'dk-caution', 'dk-risk', 'dk-data', 'dk-neutral', 'dk-dn']
for k in DK:
    n = len(re.findall(r'\.' + re.escape(k) + r'\s*\{', s))
    if n != 1:
        note2.append(f'⚠️ .{k} 定义 {n} 次（须=1）')
        ok2 = False
if s.count('/* DK-SEMANTIC-CSS v1') != 1:
    note2.append(f"⚠️ DK-SEMANTIC-CSS 块数={s.count('/* DK-SEMANTIC-CSS v1')}（须=1）")
    ok2 = False
if ok2:
    note2.append(f"{len(DK)} 个 dk-* 类定义各 1 次 ✓；CSS 块唯一 ✓")
print(f"{'✅' if ok2 else '❌'} [2/8] dk-* 语义色定义（结论卡着色依赖）：{'通过' if ok2 else '未通过'}")
for n in note2:
    print(f'      {n}')

# ── [3/8] 结论卡分类渲染逻辑在位 ────────────────────────────────────────
ok3 = True
note3 = []
i_rc = s.find('function renderConclusion')
if i_rc < 0:
    note3.append('⚠️ 未找到 renderConclusion 函数')
    ok3 = False
else:
    seg = s[i_rc:i_rc + 4000]
    for kw, why in [('rc-block', '结论块分类 class 未生成'),
                    ('dk-risk', 'risk 分类规则缺失'),
                    ('dk-caution', 'caution 分类规则缺失'),
                    ('dk-data', 'data 分类规则缺失'),
                    ('dk-main', 'main 分类规则缺失'),
                    ('border-left:3px solid', '块左侧色条未生成')]:
        if kw not in seg:
            note3.append(f'⚠️ renderConclusion 缺 {kw}（{why}）')
            ok3 = False
    # 首句加粗阈值须存在
    if not re.search(r'cut\s*<=\s*\d+', seg):
        note3.append('⚠️ 首句加粗阈值判断缺失')
        ok3 = False
if ok3:
    note3.append('renderConclusion 含 rc-block 分类 + 5 色规则 + 左侧色条 + 首句阈值 ✓')
print(f"{'✅' if ok3 else '❌'} [3/8] 结论卡分类渲染逻辑：{'通过' if ok3 else '未通过'}")
for n in note3:
    print(f'      {n}')

# ── [4/8] 旧模式 esc(asText(x) || x) 必须清零 ───────────────────────────
# 老站 2026-09-10 已治本为 esc(asTxt(x))；V3 曾残留旧模式。
# 判据必须精确到「esc( 包住整个 asText(x) || x 表达式」——
#   否则会误判 asTxt 自身实现里的 `asText(v) || Object.values(...)`（那是兜底逻辑，正确写法）。
# 同时跳过注释行，避免说明文字被当成代码。
ok4 = True
note4 = []
bad = []
for ln, line in enumerate(s.splitlines(), 1):
    if line.strip().startswith('//'):
        continue
    if re.search(r'esc\(\s*asText\([^)]*\)\s*\|\|\s*\w+\s*\)', line):
        bad.append(ln)
if bad:
    note4.append(f'⚠️ 旧模式 esc(asText(x) || x) 残留于行 {bad}（对象会渲染成 [object Object]）')
    note4.append('   → 修法：改用 esc(asTxt(x))，asTxt 已含对象字段兜底拼接')
    ok4 = False
else:
    note4.append('无旧模式残留 ✓（asTxt 内部的 asText(v) || … 为正确兜底，不计入）')
print(f"{'✅' if ok4 else '❌'} [4/8] 旧模式 esc(asText(x) || x) 清零：{'通过' if ok4 else '未通过'}")
for n in note4:
    print(f'      {n}')

# ── [5/8] asArr/asText/asTxt 三件套与老站对齐（asText 白名单须含 event）───
ok5 = True
note5 = []
if 'const asTxt' not in s:
    note5.append('⚠️ 缺 asTxt 定义')
    ok5 = False
m_at = re.search(r'const asText\s*=[^\n]*\n[^\n]*', s)
if not m_at:
    note5.append('⚠️ 未找到 asText 定义')
    ok5 = False
elif 'event' not in m_at.group(0):
    note5.append('⚠️ asText 白名单缺 event（V3 的 t1_radar 产物为 {time,event,impact}）')
    ok5 = False
if 'chips' in s and 'esc(asTxt(x))' not in s:
    note5.append('⚠️ chips 未使用 esc(asTxt(x))')
    ok5 = False
if ok5:
    note5.append('asArr/asText（含 event）/asTxt 齐备，chips 用 esc(asTxt(x)) ✓')
print(f"{'✅' if ok5 else '❌'} [5/8] 文本归一化三件套（对齐老站）：{'通过' if ok5 else '未通过'}")
for n in note5:
    print(f'      {n}')

# ── [6/8] 空值兜底 + 逐段隔离在位（防「全页永久加载中」复发）────────────
ok6 = True
note6 = []
for kw, why in [('const num =', '数值格式化兜底 num() 缺失'),
                ('safe(', '单段渲染隔离 safe() 缺失'),
                ('unhandledrejection', '未捕获 promise 兜底缺失')]:
    if kw not in s:
        note6.append(f'⚠️ {kw}（{why}）')
        ok6 = False
# 禁止在**无空值守卫**的情况下直调 toLocaleString（us_sox.close=null 曾致整页卡死）。
# 判据按行：命中 `X.close.toLocaleString()` 的行若不含 `!= null` / `num(` 守卫则红灯
#   —— 例：`(s.close != null ? s.close.toLocaleString() : '—')` 是合法写法，不得误判。
_bad_ts = []
for ln, line in enumerate(s.splitlines(), 1):
    if line.strip().startswith('//'):
        continue
    if re.search(r'\b\w+(?:\.\w+)?\.close\.toLocaleString\(\)', line):
        if '!= null' not in line and '!=null' not in line and 'num(' not in line:
            _bad_ts.append(ln)
if _bad_ts:
    note6.append(f'⚠️ 无空值守卫的 close.toLocaleString() 直调，行 {_bad_ts}')
    ok6 = False
if ok6:
    note6.append('num() 兜底 + safe() 逐段隔离 + unhandledrejection 兜底齐备；close 直调均有 null 守卫 ✓')
print(f"{'✅' if ok6 else '❌'} [6/8] 空值兜底与逐段隔离：{'通过' if ok6 else '未通过'}")
for n in note6:
    print(f'      {n}')

# ── [7/8] 缠论买点数据源须为 gate_data.chan（obs_deduce 无该字段）────────
ok7 = True
note7 = []
if 'gate_data' not in s:
    note7.append('⚠️ 未从 gate_data 读取（缠论买点唯一有效源）')
    ok7 = False
elif 'chan' not in s:
    note7.append('⚠️ 未见 chan 字段读取')
    ok7 = False
else:
    i_chan = s.find('chanMap')
    if i_chan < 0:
        note7.append('⚠️ 未见 chanMap 构建（缠论列可能退回读 obs_deduce → 全为「—待补」）')
        ok7 = False
    else:
        seg = s[max(0, i_chan - 600):i_chan + 600]
        if 'obs_deduce' in seg and 'chanMap' not in seg[:seg.find('chanMap') + 10]:
            note7.append('⚠️ chanMap 附近仍引用 obs_deduce，请确认缠论源未被回退')
            ok7 = False
if ok7:
    note7.append('缠论买点源 = gate_data.chan（chanMap 构建在位）✓')
print(f"{'✅' if ok7 else '❌'} [7/8] 缠论买点数据源（gate_data.chan）：{'通过' if ok7 else '未通过'}")
for n in note7:
    print(f'      {n}')

# ── [8/8] 6 段「重点观测股推演」分层折叠卡（对齐老站 7.2 段 · 2026-09-11 增）──
# 背景：V3 原为「32 行平表 + 6 列」，窄视口折行、重点票与全池票无区分。
#   2026-09-11 按老站 daily_review 7.2 段改造为分层折叠卡：
#     L2 · 重点票完整三情景（源 obs_scenarios.json，可选）
#     L1 · 全池关键位总览（源 obs_deduce_latest.json，关键位全部机械计算）
#   守卫点 ① CSS 起止标记各 1 次（防重复插入 / 幂等替换误删后方代码）
#          ② 27 个折叠卡类必须有 CSS 定义（否则「有标记无样式」静默退化成普通文字）
#          ③ 关键函数在位 ④ L2 必须优雅降级（obs_scenarios 缺失不得破页）
#          ⑤ 旧平表已移除 ⑥ L1 触发线不得含动作词（红线：仅客观技术表述）
ok8 = True
note8 = []
CSS_S, CSS_E = '/* OBS-FOLD-CSS v3-1 ·', '/* /OBS-FOLD-CSS v3-1 */'
if s.count(CSS_S) != 1:
    note8.append(f'⚠️ CSS 起始标记出现 {s.count(CSS_S)} 次（须=1）')
    ok8 = False
if s.count(CSS_E) != 1:
    note8.append(f'⚠️ CSS 结束标记出现 {s.count(CSS_E)} 次（须=1）→ 幂等替换会误删后方代码')
    ok8 = False
_style = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', s, re.S))
OBS_CLS = ['obs-sec', 'obs-list', 'obs-grid', 'obs-fold', 'obs-nm', 'obs-cd', 'obs-sc', 'obs-bd',
           'obs-cv', 'obs-px', 'obs-kl', 'obs-line', 'obs-body', 'obs-rsn', 'obs-stbl', 'obs-sum',
           'obs-stwrap', 'ob-tag', 'ob-tag-a', 'ob-tag-b', 'ob-tag-c',
           'b-up', 'b-dn', 'b-ms', 'kl-s', 'kl-r', 'kl-n']
_lack = [c for c in OBS_CLS if not re.search(r'\.' + re.escape(c) + r'\s*[,{]', _style)]
if _lack:
    note8.append(f'⚠️ 折叠卡类无 CSS 定义（会静默退化成普通文字）：{_lack}')
    note8.append('   → 修法：在 OBS-FOLD-CSS 块内补定义（勿动 index 其他部分）')
    ok8 = False
for _fn in ['obsKey', 'obsTrigger', 'obsKl', 'obsL2', 'obsL1', 'obsSum', 'loadObsDeduce']:
    if not re.search(r'function\s+' + _fn + r'\s*\(', s):
        note8.append(f'⚠️ 缺函数 {_fn}()')
        ok8 = False
# 数据源纪律（2026-09-11 增）：主源必须是**配对载荷 obs_panel.json**（第 5 段映射分析 + 第 6 段观测股 = 2 处），
#   回退才是 obs_deduce_latest + obs_scenarios。旧「直读 latest 当唯一源」必须清零 ——
#   否则盘后 latest 被刷成当日、而页面口径还是上一交易日 → 卡片上的收盘价与情景里的价位不是同一套数据。
_n_panel = s.count("tryJ('../output/obs_panel.json')")
if _n_panel < 2:
    note8.append(f'⚠️ 主源 obs_panel.json 仅引用 {_n_panel} 处（期望 2：第 5 段映射分析 + 第 6 段观测股）')
    note8.append('   → 修法：python3 build_obs_section.py --data-date <上一交易日> --panel-only 产出载荷后重跑生成器')
    ok8 = False
if s.count("const od = await tryJ('../output/obs_deduce_latest.json')"):
    note8.append('⚠️ 第 5 段映射分析仍直读 obs_deduce_latest.json（未走配对载荷）→ 数据日会与页面口径错位')
    ok8 = False
for _k, _w in [("tryJ('../output/obs_scenarios.json')", 'obs_scenarios.json'),
               ("tryJ('../output/obs_deduce_latest.json')", 'obs_deduce_latest.json')]:
    if _k not in s:
        note8.append(f'⚠️ 未保留 {_w} 回退（载荷缺失时会破页，须优雅降级）')
        ok8 = False
if "'(9-8 " in s or '· 9-8 数据' in s:
    note8.append('⚠️ 残留硬编码数据日「9-8」（日期一律取实际 data_date，禁写死）')
    ok8 = False
if '<th>开盘方式</th>' in s:
    note8.append('⚠️ 旧平表残留（<th>开盘方式</th>）')
    ok8 = False
_i_tr = s.find('function obsTrigger')
_seg_tr = s[_i_tr:s.find('function obsKl', _i_tr)] if _i_tr >= 0 else ''
_bad_w = [w for w in ['买入', '卖出', '减仓', '加仓', '清仓', '止损', '止盈'] if w in _seg_tr]
if _bad_w:
    note8.append(f'⚠️ L1 触发线含动作词 {_bad_w}')
    note8.append('   → 红线：动作词只允许出现在 L2 的「推测专家操作」列，L1 须纯客观技术表述')
    ok8 = False
if '推测专家操作' not in s:
    note8.append('⚠️ 缺「推测专家操作」列标题（红线委婉口径）')
    ok8 = False
# 生成链反查（铁律 15 第四维）：该段 JS 由 build_v3_obs_section.py 拥有，手工改过就会被抓
_GEN = 'build_v3_obs_section.py'
if not os.path.exists(_GEN):
    note8.append(f'⚠️ 缺生成脚本 {_GEN}（本段 JS 由它拥有，手工改会被覆盖）')
    ok8 = False
else:
    import subprocess
    _r = subprocess.run([sys.executable, _GEN, '--check'], capture_output=True, text=True)
    if _r.returncode != 0:
        note8.append(f'⚠️ {_GEN} --check 未通过（段内容与生成器不一致）：')
        for _l in ((_r.stdout or '') + (_r.stderr or '')).strip().splitlines()[:4]:
            note8.append('      ' + _l)
        note8.append('   → 修法：改 build_v3_obs_section.py 的 NEW_JS 后重跑，勿直接手改 index')
        ok8 = False
if ok8:
    note8.append(f'CSS 起止标记各 1 次 ✓；{len(OBS_CLS)} 个折叠卡类定义齐备 ✓；7 个函数在位 ✓')
    note8.append('主源 obs_panel.json（配对载荷）✓；回退链齐备 ✓；无硬编码数据日 ✓')
    note8.append('旧平表已移除 ✓；触发线无动作词 ✓；「推测专家操作」口径在位 ✓')
print(f"{'✅' if ok8 else '❌'} [8/8] 6 段分层折叠卡（对齐老站 7.2）：{'通过' if ok8 else '未通过'}")
for n in note8:
    print(f'      {n}')

# ── 总结 ────────────────────────────────────────────────────────────────
all_ok = (ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8)
print(f"\n{'✅ 全部通过' if all_ok else '❌ V3 存在守卫项未通过，修复后重跑'}")
sys.exit(0 if all_ok else 1)
