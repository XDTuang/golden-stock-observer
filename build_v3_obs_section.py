#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V3 独立版第 6 段「重点观测股推演」生成器（分层折叠卡 · 对齐老站 7.2 段）
================================================================
把 review_v3 的第 6 段由「32 行平表 + 6 列」升级为「分层折叠卡」，
展示方式对齐老站 `data/daily_review/analysis.html` 的 7.2 段：

  L2 · 重点票完整三情景  = output/obs_panel.json 的 picks   → 折叠卡展开 = 入选理由 + 关键位条 + 四列情景表
  L1 · 全池关键位总览    = output/obs_panel.json 的 items   → 折叠卡展开 = 板块/形态/开盘姿态 + 关键位条 + 客观触发线

🔴 主源只用 obs_panel.json（由 build_obs_section.py 顺带产出的**配对载荷**）：
   它把「同一次运行实际用的那份观测池快照」与「obs_scenarios.picks」配好对，
   所以 V3 不必再猜该用哪一天的数据，L1 与 L2 的数据日必然一致。
   缺失时回退分别读 obs_deduce_latest.json + obs_scenarios.json，并在页面上显式告警。

🔴 本脚本是 V3 中 `loadObsDeduce` 那一段 JS 的**唯一权威来源**。
   手工编辑该段会被本脚本整块覆盖（实测踩过：先手工加日期标注、再跑脚本 → 被回退）。
   要改展示逻辑，请改本文件的 NEW_JS，然后重跑本脚本。

幂等保证：
  · CSS 块用显式起止标记 `/* OBS-FOLD-CSS v3-1 ·` … `/* /OBS-FOLD-CSS v3-1 */` 整块替换
    （禁用 find('}\\n') 这类模糊收尾锚点 —— 会误抓后方 JS 的括号、吃掉大段代码）
  · JS 块用不随内容变化的前缀锚点整块替换
  · 段标题：已是新版则跳过
  · 连跑两次结果逐字节恒定

红线处理（沿用老站口径）：
  · L1 触发线 = 纯客观技术表述（"失守下看 MA10"），**不含任何动作词**
  · L2 动作列标题固定为「推测专家操作」，主语明确为专家
  · 段首红线声明「其他专家持股参考（非本人）…不构成对读者的任何买卖建议」

用法：
  python3 build_v3_obs_section.py            # 生成并写 review_v3/index.html + 同步其余三副本
  python3 build_v3_obs_section.py --check    # 只校验是否已是最新（漂移则退出码 1，不写盘）
  python3 build_v3_obs_section.py --no-sync  # 只改根 index，不同步副本
"""
import argparse
import hashlib
import io
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE / "review_v3" / "index.html"
COPIES = [
    "review_v3/index_hide89.html",
    "deploy/review_v3/index.html",
    "deploy/review_v3/index_hide89.html",
]

CSS_MARK = '/* OBS-FOLD-CSS v3-1 ·'
CSS_END = '/* /OBS-FOLD-CSS v3-1 */'
JS_START = '/* ── L2：重点观测股推演（'
JS_END = '/* ── L2：新闻 × 资金 交叉验证（'
# 段标题：用**正则整体替换** layer 文案（禁用整串硬编码 —— 文案一变就失配，
#   与 `rebuild_html.py` 的 title bug 同源：old 串必须能吃掉任意旧版本内容）
HDR_RE = re.compile(r'(<div class="dr-h">6 · 重点观测股推演<span class="layer">)[^<]*(</span></div>)')
HDR_LAYER = 'obs_panel.json（配对载荷）· 分层折叠卡 · 引擎自动'

# ---------------------------------------------------------------- CSS

OBS_CSS = r"""/* OBS-FOLD-CSS v3-1 · 6 段「重点观测股推演」分层折叠卡（对齐老站 daily_review 7.2 段 · 纯 CSS 不依赖 JS） */
.obs-sec{font-size:12.5px;font-weight:600;color:var(--text-secondary);margin:14px 0 6px;
  padding-left:8px;border-left:3px solid var(--gold);line-height:1.4}
.obs-list{display:flex;flex-direction:column;gap:5px}
.obs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:5px;align-items:start}
details.obs-fold{background:var(--bg-subtle);border:1px solid var(--border);border-radius:7px;overflow:hidden}
details.obs-fold>summary{cursor:pointer;list-style:none;display:flex;align-items:center;
  gap:6px;flex-wrap:wrap;font-size:12.5px;padding:6px 10px;user-select:none}
details.obs-fold>summary::-webkit-details-marker{display:none}
details.obs-fold>summary:hover{background:var(--bg-card)}
details.obs-fold[open]>summary{border-bottom:1px solid var(--border);background:var(--bg-card)}
.obs-cv,.obs-cd,.obs-sc,.obs-bd,.obs-px,.ob-tag{font-size:11.5px}
.obs-nm{font-weight:700;color:var(--text)}
.obs-cv{margin-left:auto;color:var(--text-muted);line-height:1;transition:transform .15s ease}
details.obs-fold[open] .obs-cv{transform:rotate(90deg)}
.obs-cd{color:var(--text-muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.obs-sc{color:var(--text-muted)}
.obs-bd{border-radius:3px;padding:1px 5px;white-space:nowrap;line-height:1.5}
.obs-bd.b-up{background:rgba(239,68,68,.16);color:var(--red)}
.obs-bd.b-dn{background:rgba(34,197,94,.16);color:var(--green)}
.obs-bd.b-ms{background:rgba(245,158,11,.18);color:var(--orange)}
.obs-px{color:var(--text-secondary);font-variant-numeric:tabular-nums}
.obs-kl,.obs-line{font-size:12.5px}
.obs-body{padding:9px 11px 11px;font-size:12.5px}
.obs-kl{display:flex;flex-wrap:wrap;gap:5px 12px;color:var(--text-secondary);
  padding:7px 9px;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;margin-bottom:8px}
.obs-kl b{font-variant-numeric:tabular-nums}
.obs-kl .kl-s{border-left:3px solid var(--green);padding-left:6px}
.obs-kl .kl-r{border-left:3px solid var(--red);padding-left:6px}
.obs-kl .kl-n{border-left:3px solid var(--blue);padding-left:6px}
.obs-line{color:var(--text-secondary);line-height:1.65;
  background:var(--bg-card);border:1px solid var(--border);border-radius:6px;padding:7px 9px}
.obs-rsn{color:var(--text-muted);margin-bottom:7px;line-height:1.6}
.obs-stwrap{overflow-x:auto;margin:6px 0 0}
table.obs-stbl{margin:0;table-layout:fixed;width:100%;min-width:560px}
table.obs-stbl col.cc1{width:17%}
table.obs-stbl col.cc2{width:7%}
table.obs-stbl col.cc3{width:46%}
table.obs-stbl col.cc4{width:30%}
table.obs-stbl th,table.obs-stbl td{text-align:left;font-size:12.5px}
table.obs-stbl td{vertical-align:top;line-height:1.6}
table.obs-stbl td.ob-p{text-align:center;white-space:nowrap;font-weight:700;font-variant-numeric:tabular-nums}
.ob-tag{display:inline-block;min-width:13px;text-align:center;border-radius:3px;
  font-weight:700;padding:0 4px;margin-right:5px;line-height:1.7}
.ob-tag-a{background:rgba(239,68,68,.18);color:var(--red)}
.ob-tag-b{background:rgba(245,158,11,.2);color:var(--orange)}
.ob-tag-c{background:rgba(34,197,94,.18);color:var(--green)}
.obs-sum{font-size:12.5px;color:var(--text-secondary);line-height:1.6;margin-top:10px;
  background:var(--bg-subtle);border-radius:6px;padding:8px 11px;border-left:3px solid var(--gold)}
@media (max-width:640px){.obs-grid{grid-template-columns:1fr}}
"""

# ---------------------------------------------------------------- JS

NEW_JS = r"""/* ── L2：重点观测股推演（obs_panel.json 配对载荷；回退 obs_deduce_latest + obs_scenarios）──
   2026-09-11 改版：对齐老站 daily_review 7.2 段的「分层折叠卡」展示方式
     L2 · 重点票完整三情景（源 obs_panel.picks，缺失/失败自动降级只出 L1）
     L1 · 全池关键位总览（源 obs_panel.items，关键位全部机械计算、零人工估计）
   🔴 主源只用 obs_panel.json：由 build_obs_section.py 用「同一次运行、同一份观测池快照」配对产出
      → L1 与 L2 的数据日必然一致。原先 V3 自己在运行时分别读 latest 与 scenarios，而
      obs_deduce_latest 会被盘后任务刷成当日、情景还是上一交易日口径 → 卡片上「9/11 的收盘价」
      配「9/10 的情景价位」，不是同一套数。配对责任已上移到生成端。
   交互 = 原生 <details> + 纯 CSS（与老站一致，不依赖 JS 事件绑定）
   生成脚本 = build_v3_obs_section.py（本段 JS 的权威来源，手工改会被覆盖）
   红线 = L1 触发线为纯客观技术表述（无动作词）；L2 动作列口径固定「推测专家操作」 */
const obsF = (v, nd) => (v == null || v === '' || isNaN(Number(v))) ? '—' : Number(v).toFixed(nd == null ? 2 : nd);
const obsPct = (v) => (v == null || v === '' || isNaN(Number(v))) ? '—' : sign(Number(v)) + Number(v).toFixed(2) + '%';
const obsClsPct = (v) => (v == null || v === '' || isNaN(Number(v))) ? '' : (Number(v) > 0 ? 'dr-up' : (Number(v) < 0 ? 'dr-dn' : ''));
const obsBadge = (p) => p === '多头排列' ? 'b-up' : (p === '空头排列' ? 'b-dn' : 'b-ms');
const obsShortBadge = (p) => ({ '多头排列': '多头', '空头排列': '空头' })[p] || '震荡';
// 情景文本含 <b> 富文本（与老站 analysis.html 同源）→ 先整体转义、再放行白名单标签，防注入
const obsRich = (v) => String(v == null ? '' : v)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/&lt;(\/?)(b|br|code|em|strong)&gt;/g, '<$1$2>');

// 关键位机械推导（复刻老站 build_obs_section.py 的 key_levels()，零人工估计）
function obsKey(x) {
  const p = x.pattern || '';
  return {
    close: x.close, ma5: x.ma5, ma10: x.ma10, low10: x.low10, high10: x.high10, dev_ma5: x.dev_ma5,
    break_line: p === '多头排列' ? x.ma10 : x.low10,
    break_note: p === '多头排列' ? '失守 MA10' : (p === '空头排列' ? '跌破近 10 日低' : '跌破区间下沿')
  };
}

// 纯客观技术触发线（不含动作词 · 红线安全表述）—— 复刻老站 trigger_line()
function obsTrigger(x, k) {
  const p = x.pattern || '';
  const ma5 = obsF(k.ma5), ma10 = obsF(k.ma10), lo = obsF(k.low10), hi = obsF(k.high10);
  if (p === '多头排列') return '守 <b>' + ma5 + '</b>(MA5) 则形态延续 ｜ 失守下看 <b>' + ma10 + '</b>(MA10) ｜ 跌破 <b>' + lo + '</b>（近 10 日低）结构转弱';
  if (p === '空头排列') return '站上 <b>' + ma5 + '</b>(MA5) 才算修复启动 ｜ <b>' + ma10 + '</b>(MA10) 为反弹压力 ｜ 跌破 <b>' + lo + '</b> 创近 10 日新低';
  return '区间 <b>' + lo + '</b>~<b>' + hi + '</b> ｜ 上破 <b>' + hi + '</b> 转强 ｜ 下破 <b>' + lo + '</b> 转弱';
}

// 关键位色块（支撑绿 / 压力红 / 偏离蓝）—— 复刻老站 kl_html()
function obsKl(x, k) {
  const dv = (k.dev_ma5 == null || isNaN(Number(k.dev_ma5))) ? null : Number(k.dev_ma5);
  const dc = dv == null ? 'kl-n' : (dv > 3 ? 'kl-r' : (dv < -3 ? 'kl-s' : 'kl-n'));
  const ds = dv == null ? '—' : sign(dv) + dv.toFixed(2) + '%';
  const c5 = (x.chg5 == null || isNaN(Number(x.chg5))) ? '—' : sign(Number(x.chg5)) + Number(x.chg5).toFixed(2) + '%';
  return '<div class="obs-kl">' +
    '<span class="kl-s">支撑 <b>' + obsF(k.ma5) + '</b> MA5 ／ <b>' + obsF(k.ma10) + '</b> MA10</span>' +
    '<span class="kl-r">压力 <b>' + obsF(k.high10) + '</b> 近 10 日高</span>' +
    '<span class="kl-s">结构位 <b>' + obsF(k.low10) + '</b> 近 10 日低</span>' +
    '<span class="' + dc + '">MA5 偏离 <b>' + ds + '</b></span>' +
    '<span class="kl-n">5 日 <b>' + c5 + '</b></span>' +
    '<span class="kl-n">量比 <b>' + obsF(x.vol_ratio) + '</b></span>' +
    '</div>';
}

// L2 · 重点票完整三情景（折叠卡 + 四列情景表）
//   scenDate = obs_scenarios.data_date（情景依据的收盘日）→ 必须显式标注：
//   盘前页面用上一交易日数据，而 obs_deduce_latest 会被盘后任务刷成当日，两者天然可能不同步。
function obsL2(picks, byCode, scenDate) {
  const rows = [];
  picks.forEach(p => {
    const x = byCode[p.code];
    if (!x) return;
    const k = obsKey(x);
    const trs = (p.scenarios || []).map(sc => {
      const tg = String(sc.tag || '').slice(0, 1).toUpperCase();
      return '<tr><td><span class="ob-tag ob-tag-' + tg.toLowerCase() + '">' + esc(tg) + '</span>' + esc(sc.name || '') + '</td>' +
        '<td class="ob-p">' + esc(sc.prob == null ? '' : sc.prob) + '%</td>' +
        '<td class="dr-wrap">' + obsRich(sc.path) + '</td>' +
        '<td class="dr-wrap">' + obsRich(sc.action) + '</td></tr>';
    }).join('');
    rows.push('<details class="obs-fold"><summary>' +
      '<span class="obs-nm">' + esc(x.name) + '</span>' +
      '<span class="obs-cd">' + esc(String(p.code).slice(2)) + '</span>' +
      '<span class="obs-sc">' + esc(x.sector || '') + '</span>' +
      '<span class="obs-bd ' + obsBadge(x.pattern) + '">' + esc(x.pattern || '') + ' · ' + esc(x.trend || '') + '</span>' +
      '<span class="obs-px">收 ' + obsF(x.close) + ' <b class="' + obsClsPct(x.chg_last) + '">' + obsPct(x.chg_last) + '</b></span>' +
      '<span class="obs-cv">▶</span></summary>' +
      '<div class="obs-body">' + (p.reason ? '<div class="obs-rsn">入选理由：' + esc(p.reason) + '</div>' : '') + obsKl(x, k) +
      '<div class="obs-stwrap"><table class="dr-tbl obs-stbl">' +
      '<colgroup><col class="cc1"><col class="cc2"><col class="cc3"><col class="cc4"></colgroup>' +
      '<thead><tr><th>情景</th><th>概率</th><th>路径（机制 + 价位）</th><th>推测专家操作</th></tr></thead>' +
      '<tbody>' + trs + '</tbody></table></div></div></details>');
  });
  if (!rows.length) return '';
  return '<div class="obs-sec">L2 · 重点票完整情景推演（' + rows.length + ' 只' +
    (scenDate ? ' · 情景数据日 ' + esc(scenDate) : '') +
    ' · 点开看三情景 · 概率为主观判断）</div>' +
    '<div class="obs-list">' + rows.join('') + '</div>';
}

// L1 · 全池关键位（grid mini details；排序 = 多头→震荡→空头，同组按 MA5 偏离降序）
function obsL1(items, l2codes, l1date) {
  const order = { '多头排列': 0, '震荡纠缠': 1, '空头排列': 2 };
  const srt = items.slice().sort((a, b) => {
    const oa = order[a.pattern] == null ? 3 : order[a.pattern];
    const ob = order[b.pattern] == null ? 3 : order[b.pattern];
    if (oa !== ob) return oa - ob;
    return (b.dev_ma5 == null ? -99 : Number(b.dev_ma5)) - (a.dev_ma5 == null ? -99 : Number(a.dev_ma5));
  });
  const cards = srt.map(x => {
    const k = obsKey(x);
    const code = String(x.code || '');
    const mark = l2codes[code] ? ' <span class="obs-cd">L2</span>' : '';
    return '<details class="obs-fold"><summary>' +
      '<span class="obs-nm">' + esc(x.name) + '</span>' +
      '<span class="obs-cd">' + esc(code.slice(2)) + '</span>' + mark +
      '<span class="obs-bd ' + obsBadge(x.pattern) + '">' + esc(obsShortBadge(x.pattern)) + '</span>' +
      '<span class="obs-px">' + obsF(x.close) + ' <b class="' + obsClsPct(x.chg_last) + '">' + obsPct(x.chg_last) + '</b></span>' +
      '<span class="obs-cv">▶</span></summary>' +
      '<div class="obs-body"><div class="obs-rsn">' + esc(x.sector || '') + ' · ' + esc(x.trend || '') +
      ' · 开盘姿态「' + esc(x.open_label || '—') + '」</div>' + obsKl(x, k) +
      '<div class="obs-line">' + obsTrigger(x, k) + '</div></div></details>';
  }).join('');
  return '<div class="obs-sec">L1 · 全池关键位总览（' + items.length + ' 只' +
    (l1date ? ' · 数据日 ' + esc(l1date) : '') +
    ' · 点开看关键位与触发线）</div>' +
    '<div class="obs-grid">' + cards + '</div>';
}

// 池内结构小结
function obsSum(items) {
  const n = items.length;
  const nMulti = items.filter(x => x.pattern === '多头排列').length;
  const nEmpty = items.filter(x => x.pattern === '空头排列').length;
  const nHk = items.filter(x => String(x.code || '').indexOf('hk') === 0).length;
  return '<div class="obs-sum"><b>池内结构：</b>' + n + ' 只（' + (n - nHk) + ' 只 A股 + ' + nHk + ' 只港股）｜' +
    '<b class="dk-main">多头排列 ' + nMulti + ' 只</b>｜震荡纠缠 ' + (n - nMulti - nEmpty) + ' 只｜' +
    '<b class="dk-risk">空头排列 ' + nEmpty + ' 只（占比 ' + Math.floor(nEmpty * 100 / Math.max(n, 1)) + '%）</b>。' +
    '形态与关键位为机械读数，未做方向性判断。</div>';
}

// ── 渲染（主源与回退源共用）──────────────────────────────────────────
//   p = {data_date, for_date, scen_data_date, derive_engine, items, picks}
//   paired = true  → 来自 obs_panel.json（生成端已配对，L1/L2 数据日必然一致）
//   paired = false → 来自两个原始源（旧行为，数据日可能不一致 → 页面上显式告警）
function obsRender(p, paired) {
  const items = p.items || [];
  const byCode = {};
  items.forEach(x => { byCode[x.code] = x; });
  const picks = (p.picks || []).filter(x => byCode[x.code]);
  const l2codes = {};
  picks.forEach(x => { l2codes[x.code] = 1; });
  const dataDate = p.data_date || '';
  const scenDate = p.scen_data_date || '';
  let warn = '';
  if (!paired) {
    warn += '<div class="dr-note" style="color:var(--orange)">⚠ <b>配对载荷 obs_panel.json 未取到</b> ｜ 已回退用 ' +
      'obs_deduce_latest.json + obs_scenarios.json 两个原始源，两者数据日可能不一致。修法：<code>python3 build_obs_section.py ' +
      '--data-date &lt;上一交易日&gt; --panel-only</code>。</div>';
  }
  if (scenDate && dataDate && scenDate !== dataDate) {
    // 盘前页面用上一交易日数据，而 obs_deduce_latest 会被盘后任务刷成当日 → 天然可能错位。
    //   不做人工对齐，而是把两个数据日分别标在段标题上、并在页尾显式告警。
    warn += '<div class="dr-note" style="color:var(--orange)">⚠ <b>L2 情景数据日（' + esc(scenDate) +
      '）与 L1 观测池（' + esc(dataDate) + '）不一致</b> ｜ 卡片上的收盘价与情景里的价位不是同一套数据，请按数据日分别解读。</div>';
  }
  const head = '<div class="dr-note" style="font-size:12.5px">' +
    '<b>口径：</b>价格 / 均线 / 技术位来自 <code>obs_deduce</code>（<b>数据日 ' + esc(dataDate) + ' 收盘</b>）；' +
    '<b>关键位全部由 MA5 / MA10 / 近 10 日高低点机械计算，无人工估计</b>。' +
    '<br><b>分层：</b>L2 为重点票完整三情景（含机制路径与概率，<b>概率为主观判断</b>）；L1 为全池关键位与客观触发线。' +
    (picks.length ? '' : '<br><b style="color:var(--orange)">L2 情景本次未生成</b>（无 obs_scenarios 或无匹配标的）→ 仅展示 L1 全池关键位。') +
    '<br><b class="dk-risk">红线声明：本段全部标的均为「其他专家持股参考（非本人）」，内容为客观读数与对该类标的持有者常规操作的推测，仅用于理解其在盘中的可能行为，不构成对读者的任何买卖建议。</b></div>';
  $('v3Obs').innerHTML = '<div class="dr-tag">数据日：' + esc(dataDate) + ' ｜ 池 ' + items.length + ' 只' +
    (picks.length ? ' · L2 重点 ' + picks.length + ' 只' : '') +
    ' ｜ 折叠卡 ' + (items.length + picks.length) + ' 个 ｜ ' +
    esc(p.derive_engine || 'derive_engine') + ' ｜ ' +
    (paired ? '<span style="color:var(--green)">配对载荷 ✓</span>'
            : '<span style="color:var(--orange)">回退源（未配对）</span>') +
    '</div>' + head + obsL2(picks, byCode, scenDate) + obsL1(items, l2codes, dataDate) + obsSum(items) + warn;
}

function obsFail(e) {
  $('v3Obs').innerHTML = '<div class="dr-note">观测股推演未生成：' + esc(e) + '</div>';
}

/* 主源 = obs_panel.json —— 由 build_obs_section.py 用「同一次运行、同一份观测池快照」把 L1 items
   与 L2 picks 配对产出，所以 V3 不必再猜该用哪一天的数据，L1 与 L2 的数据日必然一致。
   回退 = 分别读 obs_deduce_latest.json + obs_scenarios.json（旧行为）→ 页面上会显式告警。 */
function loadObsDeduce() {
  tryJ('../output/obs_panel.json').then(panel => {
    if (panel && (panel.items || []).length) { obsRender(panel, true); return; }
    loadObsDeduceFallback();
  }).catch(obsFail);
}

function loadObsDeduceFallback() {
  Promise.all([tryJ('../output/obs_deduce_latest.json'), tryJ('../output/obs_scenarios.json')])
    .then(res => {
      const d = res[0], scen = res[1];
      const items = (d && d.items) || [];
      if (!items.length) throw new Error('obs_deduce empty');
      obsRender({
        data_date: d.date || '',
        for_date: (scen && scen.for_date) || '',
        scen_data_date: (scen && scen.data_date) || '',
        derive_engine: d.derive_engine || d.source || '',
        items: items,
        picks: (scen && scen.picks) || []
      }, false);
    })
    .catch(obsFail);
}
"""


# ---------------------------------------------------------------- 生成

def build(html):
    """返回 (新 html, css_state)；任何锚点异常抛 RuntimeError，绝不写半成品"""
    css_state = ''
    if CSS_MARK in html:
        a = html.find(CSS_MARK)
        z = html.find(CSS_END, a)
        if z < 0:
            raise RuntimeError(f'CSS 起始标记在、但缺结束标记 {CSS_END!r} → 拒绝替换（防误删）')
        z += len(CSS_END)
        if html[z:z + 1] == '\n':
            z += 1
        html = html[:a] + OBS_CSS.lstrip('\n') + CSS_END + '\n' + html[z:]
        css_state = 'updated'
    else:
        k = html.rfind('</style>')
        if k < 0:
            raise RuntimeError('未找到 </style>')
        html = html[:k] + OBS_CSS + CSS_END + '\n' + html[k:]
        css_state = 'added'

    html, _hn = HDR_RE.subn(lambda m: m.group(1) + HDR_LAYER + m.group(2), html)
    if _hn != 1:
        raise RuntimeError(f'段标题替换命中 {_hn} 处（期望 1）—— 锚点漂移，已中止以免写坏')

    na, nb = html.count(JS_START), html.count(JS_END)
    a, b = html.find(JS_START), html.find(JS_END)
    if na != 1 or nb != 1 or a < 0 or b <= a:
        raise RuntimeError(f'JS 区间锚点异常：START {na} 次 / END {nb} 次 / a={a} b={b}')
    html = html[:a] + NEW_JS + html[b:]
    return html, css_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只校验是否最新，漂移则退出码 1')
    ap.add_argument('--no-sync', action='store_true', help='不同步其余三副本')
    args = ap.parse_args()

    src = ROOT.read_text(encoding='utf-8')
    out, css_state = build(src)

    if args.check:
        drift = []
        if out != src:
            drift.append(f'{ROOT} 与生成器期望输出不一致')
        if not args.no_sync:
            want = hashlib.md5(out.encode('utf-8')).hexdigest()
            for rel in COPIES:
                p = BASE / rel
                if p.exists():
                    got = hashlib.md5(p.read_bytes()).hexdigest()
                    if got != want:
                        drift.append(f'{rel} 与根 index 不一致（{got[:10]} vs {want[:10]}）')
        if drift:
            print('❌ V3 观测股段与生成器不一致（改展示逻辑请改 build_v3_obs_section.py 后重跑）：')
            for d in drift:
                print('   · ' + d)
            sys.exit(1)
        print('✅ V3 观测股段与生成器一致 ✓')
        sys.exit(0)

    if out == src:
        print('· 内容已是最新，无需写盘')
        state = 'unchanged'
    else:
        ROOT.write_text(out, encoding='utf-8')
        state = f'{len(src)} → {len(out)} 字符（CSS {css_state}）'
        print(f'✓ {ROOT.relative_to(BASE)} 已更新：{state}')

    if not args.no_sync:
        want = hashlib.md5(ROOT.read_bytes()).hexdigest()
        for rel in COPIES:
            p = BASE / rel
            if p.exists():
                p.write_bytes(ROOT.read_bytes())
        print(f'✓ 已同步 {len(COPIES)} 份副本')

    # ---- 自检 ----
    t = ROOT.read_text(encoding='utf-8')
    checks = [
        ('OBS-FOLD-CSS 起始标记', t.count(CSS_MARK), 1),
        ('OBS-FOLD-CSS 结束标记', t.count(CSS_END), 1),
        ('obs-fold（CSS+用法）', t.count('obs-fold'), None),
        ('obsTrigger 定义', t.count('function obsTrigger'), 1),
        ('obsKey 定义', t.count('function obsKey'), 1),
        ('obsL1 定义', t.count('function obsL1'), 1),
        ('obsL2 定义', t.count('function obsL2'), 1),
        ('obsSum 定义', t.count('function obsSum'), 1),
        ('obsRich 防注入', t.count('const obsRich'), 1),
        ('主源 obs_panel.json（第 5+6 段）', t.count("tryJ('../output/obs_panel.json')"), 2),
        ('回退源 obs_deduce_latest（仅回退）', t.count("tryJ('../output/obs_deduce_latest.json')"), 2),
        ('回退源 obs_scenarios', t.count("tryJ('../output/obs_scenarios.json')"), 1),
        ('旧直读模式已清零', t.count("const od = await tryJ('../output/obs_deduce_latest.json')"), 0),
        ('硬编码日期 9-8 已清零', t.count("'(9-8 ") + t.count('· 9-8 数据'), 0),
        ('obsRender 定义', t.count('function obsRender('), 1),
        ('obsFail 定义', t.count('function obsFail('), 1),
        ('loadObsDeduceFallback 定义', t.count('function loadObsDeduceFallback('), 1),
        ('旧平表残留 <th>开盘方式</th>', t.count('<th>开盘方式</th>'), 0),
    ]
    bad = []
    print()
    print('=== 自检 ===')
    for name, got, want in checks:
        ok = (got == want) if want is not None else (got > 0)
        print('  %s %-30s %d%s' % ('✓' if ok else '✗', name, got,
                                   '' if want is None else f'（期望 {want}）'))
        if not ok:
            bad.append(name)
    md5 = hashlib.md5(ROOT.read_bytes()).hexdigest()[:10]
    print(f'\n  md5={md5}')
    if bad:
        print('❌ 自检未通过：' + '、'.join(bad))
        sys.exit(1)


if __name__ == '__main__':
    main()
