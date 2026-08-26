#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把「每日复盘」tab 幂等注入主站 index.html / index_template.html / deploy/index.html。
根治云端 rebuild_html.py 覆盖问题：云端 Actions 每次 rebuild 后实时盯盘 tab 有
inject_realtime_tab.py 重注入，但每日复盘 tab 此前无注入脚本 → 每次被覆盖丢失。
本脚本仿 inject_realtime_tab.py：nav 按钮缺失则插入；tab 容器与 JS 块已存在则用
【最新版本】整体替换（支持后续升级同步）。
用法: python inject_daily_review_tab.py [目标文件]  （默认三文件）
"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ============ 注入素材（与 index.html 中 9ed9961 提交一致 + 后续优化） ============
BTN = '<button class="nav-btn" data-tab="dailyreview">每日复盘</button>'

TAB_BLOCK = '''
<!-- Tab: 每日复盘（盘前简报 + 完整复盘合一；行情=云端08:15自动，分析=本机agent） -->
<div class="tab-content" id="tab-dailyreview">
<style>
.dr-h{font-size:14px;font-weight:600;color:var(--text);margin:12px 0 4px}
.dr-tbl{width:100%;border-collapse:collapse;font-size:12.5px}
.dr-tbl th,.dr-tbl td{padding:5px 9px;border-bottom:1px solid var(--border);text-align:right;white-space:nowrap}
.dr-tbl th:first-child,.dr-tbl td:first-child{text-align:left}
.dr-tbl th{color:var(--text-muted);font-weight:600}
.dr-up{color:var(--red)}.dr-dn{color:var(--green)}
.dr-tag{font-size:11px;color:var(--text-muted)}
.dr-note{font-size:12.5px;color:var(--text-secondary);margin:6px 0}
.dr-card{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:12px 0}
</style>
<div class="dr-card" id="drMarket"><p class="dr-note">行情加载中…</p></div>
<div class="dr-card" id="drAnalysis"><p class="dr-note">分析区加载中…</p></div>
</div>
'''

# JS 块从独立文件读取（若存在），否则用内置版本
JS_BLOCK = ''
_js_src = os.path.join(BASE, 'daily_review_tab_snippet.js')
if os.path.exists(_js_src):
    JS_BLOCK = open(_js_src, encoding='utf-8').read()
else:
    # 内置兜底（与 9ed9961 一致，含 renderDailyReview/drFillTables/drLoadTop10/drLoadDiamond）
    JS_BLOCK = r'''
// ===== 每日复盘 Tab =====
function renderDailyReview() {
  if (window._drInit) return; window._drInit = true;
  const mkt = document.getElementById('drMarket');
  const ana = document.getElementById('drAnalysis');
  const loadAna = (d) => {
    if (!ana) return;
    const q = (d && d.quotes) || {};
    fetch('./data/daily_review/analysis.html', { cache: 'no-store' }).then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    }).then(t => {
      // 保留 analysis.html 的"3·隔夜美股复盘"模块（含 agent 推演结论），
      // 仅用 market.json.us_kline 把双日表数据+说明日期刷新到最新（drRefreshUsDualDayTables）
      ana.innerHTML = t;
      drFillTables(q);
      drFixHeader(d);
      drAIndexSummary(d);
      drAsiaTable(d);
      if (d && d.us_kline) drRefreshUsDualDayTables(d);
      if (d && d.comm) drRefreshCommRates(d);
      drDeriveSections(d);
      drLoadObserveStocks();
      drLoadTop10();
      drLoadDiamond();
    }).catch(err => {
      ana.innerHTML = `<p class="dr-note">分析区加载失败：${err}</p>`;
    });
  };
  if (mkt) {
    fetch('./data/daily_review/market.json', { cache: 'no-store' }).then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(d => {
      const q = d.quotes || {};
      const cnt = Object.values(q).filter(v => !v.error).length;
      mkt.innerHTML = `<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <b>📊 行情数据（${d.date}）</b><span class="dr-tag">${cnt} 标的 · ${d.source}</span>
        <span class="dr-tag">云端 08:15 自动更新</span></div>`;
      // 保留 analysis.html 的"3"模块，仅刷新数据
      loadAna(d);
    }).catch(err => {
      mkt.innerHTML = `<p class="dr-note">行情加载失败：${err}</p>`;
      loadAna();
    });
  } else {
    loadAna();
  }
}

/* ═══════ 隔夜美股复盘（保留 analysis.html 模块，仅刷新双日表数据+说明日期，数据源 market.json.us_kline） ═══════ */
function drRefreshUsDualDayTables(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const k = d.us_kline;
  if (!k || Object.keys(k).length === 0) return;
  const sample = k.us_dji || Object.values(k)[0];
  if (!sample || !sample.latest || !sample.prev) return;
  const latestDate = sample.latest.date, prevDate = sample.prev.date;
  const fmt = (s) => (s || '').slice(5).replace('-', '/');  // 2026-08-24 -> 08/24
  // 1. 定位"3 · 隔夜美股复盘"标题
  const heads = Array.prototype.slice.call(ana.querySelectorAll('.dr-h'));
  const h3 = heads.find(h => /隔夜美股复盘/.test(h.textContent || ''));
  if (!h3) return;
  const card = h3.nextElementSibling;
  if (!card || !card.querySelector) return;
  // 2. 更新说明文字日期（"为什么双日"段）
  Array.prototype.slice.call(card.querySelectorAll('.dr-note')).forEach(n => {
    const t = n.innerHTML || '';
    if (t.indexOf('为什么双日') >= 0) {
      n.innerHTML = t
        .replace(/映射源（[\d/．. ]+）/, '映射源（' + fmt(prevDate) + '）')
        .replace(/隔夜（[\d/．. ]+）/, '隔夜（' + fmt(latestDate) + '）')
        .replace(/<b>说明：[\s\S]*?<\/b>/, '<b>说明：隔夜最新 = ' + latestDate + '（最新已收盘美股交易日），前一交易日 = ' + prevDate + '</b>');
    }
  });
  // 3. 更新双日表（表头含"涨跌（映射源）"）
  const tables = Array.prototype.slice.call(card.querySelectorAll('table.dr-tbl'));
  const dual = tables.find(t => (t.innerHTML || '').indexOf('涨跌（映射源）') >= 0);
  if (!dual) return;
  const thead = dual.querySelector('thead tr');
  if (thead && thead.children.length >= 5) {
    thead.children[1].textContent = fmt(prevDate) + ' 收盘';
    thead.children[2].textContent = fmt(prevDate) + ' 涨跌（映射源）';
    thead.children[3].textContent = fmt(latestDate) + ' 收盘';
    thead.children[4].textContent = fmt(latestDate) + ' 涨跌（隔夜）';
  }
  // 4. 刷新 tbody（us_kline 数据驱动；费城半导体等无 us_kline 的行保留原文）
  const nameMap = {
    '道琼斯':'us_dji', '标普 500':'us_inx', '标普500':'us_inx', '纳斯达克':'us_ixic',
    'MU 美光':'us_mu', 'SNDK 闪迪':'us_sndk', 'MRVL 迈威尔':'us_mrvl', 'LITE 朗美通':'us_lite',
    'AAOI':'us_aaoi', 'WDC 西部数据':'us_wdc', 'COHR':'us_cohr', 'SKHY 海力士':'us_skhy',
  };
  const tbody = dual.querySelector('tbody');
  if (!tbody) return;
  Array.prototype.slice.call(tbody.querySelectorAll('tr')).forEach(tr => {
    const td = tr.children;
    if (!td || td.length < 5) return;
    const nm = (td[0].textContent || '').replace(/\s+/g, ' ').trim();
    const key = nameMap[nm];
    const e = key && k[key];
    if (!e) return;  // 费城半导体等无数据行保留 agent 原文
    const l = e.latest, p = e.prev;
    const cls = (v) => v >= 0 ? 'dr-up' : 'dr-dn';
    const sign = (v) => v >= 0 ? '+' : '';
    td[1].textContent = p.close.toLocaleString();
    td[2].textContent = sign(p.chg_pct) + p.chg_pct.toFixed(2) + '%';
    td[2].className = cls(p.chg_pct);
    td[3].textContent = l.close.toLocaleString();
    const ov = (l.close / p.close - 1) * 100;
    td[4].textContent = sign(ov) + ov.toFixed(2) + '%';
    td[4].className = cls(ov);
  });
  // 5. 隐藏 agent 写的过时"双日结论"推演文字（8/21 口径，无法自动更新），
  //    由数据驱动的最新摘要（客观数据）接管该位置
  const notes = Array.prototype.slice.call(card.querySelectorAll('.dr-note'));
  const concl = notes.find(n => (n.textContent || '').indexOf('双日结论') >= 0);
  if (concl) {
    concl.style.cssText = 'display:none';  // 隐藏过时推演，保留模块结构
    const idxRows = ['us_dji','us_inx','us_ixic'];
    const parts = idxRows.filter(x => k[x]).map(x => {
      const nm = {us_dji:'道指', us_inx:'标普', us_ixic:'纳指'}[x];
      const pct = (k[x].latest.close / k[x].prev.close - 1) * 100;
      return nm + ' ' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
    });
    const div = document.createElement('div');
    div.className = 'dr-note';
    div.style.cssText = 'background:var(--bg-subtle);border-left:3px solid var(--accent);padding:8px 12px;border-radius:6px;margin-top:6px';
    div.innerHTML = '<b>数据刷新（' + latestDate + ' 收盘，自动）：</b>' + parts.join(' · ') + '。推演结论请以本机 agent 重跑后的分析为准。';
    concl.parentNode.insertBefore(div, concl.nextSibling);
  }
}

/* ═══════ 商品·利率·汇率表（保留 analysis.html 表结构，用 market.json.comm 刷新数据+动态标注） ═══════ */
function drRefreshCommRates(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const comm = d.comm;
  if (!comm || Object.keys(comm).length === 0) return;
  const heads = Array.prototype.slice.call(ana.querySelectorAll('.dr-h'));
  const h3 = heads.find(h => /隔夜美股复盘/.test(h.textContent || ''));
  if (!h3) return;
  const card = h3.nextElementSibling;
  if (!card || !card.querySelector) return;
  const tables = Array.prototype.slice.call(card.querySelectorAll('table.dr-tbl'));
  const commTbl = tables.find(t => (t.innerHTML || '').indexOf('商品') >= 0 && (t.innerHTML || '').indexOf('汇率') >= 0);
  if (!commTbl) return;
  // 行名 -> comm key
  const map = {
    '现货黄金':'gold_spot', 'COMEX 黄金':'gold_comex', 'WTI 原油':'wti', '布伦特':'brent',
    '10Y 美债':'us10y', '30Y 美债':'us30y', '人民币中间价':'cny',
  };
  const tbody = commTbl.querySelector('tbody');
  if (!tbody) return;
  Array.prototype.slice.call(tbody.querySelectorAll('tr')).forEach(tr => {
    const td = tr.children;
    if (!td || td.length < 3) return;
    const nm = (td[0].textContent || '').trim();
    const key = nm.indexOf('碳酸锂') >= 0 ? 'lithium' : map[nm];
    const e = key && comm[key];
    if (!e || e.value == null) return;
    td[1].textContent = e.value.toLocaleString() + (nm.indexOf('美债') >= 0 ? '%' : '');
    if (e.chg_pct != null) {
      const cls = e.chg_pct >= 0 ? 'dr-up' : 'dr-dn';
      td[2].textContent = (e.chg_pct >= 0 ? '+' : '') + e.chg_pct.toFixed(2) + '%';
      td[2].className = cls;
    } else if (e.date) {
      td[2].textContent = (td[2].textContent || '') + '（' + e.date.slice(5) + '）';
    }
  });
  // 更新表底标注：来源 → 数据自动刷新日期（美元指数/伦铜无免费实时源，仍待本机补抓）
  const notes = Array.prototype.slice.call(card.querySelectorAll('.dr-note'));
  const src = notes.find(n => (n.textContent || '').indexOf('来源') >= 0);
  if (src) {
    const dates = Object.keys(comm).map(k => comm[k].date).filter(Boolean);
    const latest = dates.sort().pop() || '';
    src.innerHTML = '<span style="color:var(--text-muted)">来源：腾讯hf国际商品 · 乐咕美债 · 中行中间价 · 广期所主连（数据自动刷新至 ' +
      (latest || '—') + '；美元指数/伦铜无免费实时源，仍待本机补抓）</span>';
  }
}
function drFillTables(q) {
  const mk = (items) => {
    if (!items || !items.length) return '<div class="dr-note">【待本机补全】</div>';
    let h = '<table class="dr-tbl"><thead><tr><th>名称</th><th>收盘</th><th>涨跌幅</th><th>最高</th><th>最低</th></tr></thead><tbody>';
    items.forEach(v => {
      const n = parseFloat(v.chg_pct);
      const cls = n > 0 ? 'dr-up' : (n < 0 ? 'dr-dn' : '');
      h += `<tr><td>${v.name}</td><td>${v.close}</td>
        <td class="${cls}">${v.chg_pct}%</td><td>${v.high}</td><td>${v.low}</td></tr>`;
    });
    return h + '</tbody></table>';
  };
  const g = (group) => Object.values(q).filter(v => v.group === group && !v.error);
  const tA = document.getElementById('drTblA'); if (tA) tA.innerHTML = mk(g('A股指数'));
  const tH = document.getElementById('drTblH'); if (tH) tH.innerHTML = mk(g('持仓股'));
  const tU = document.getElementById('drTblUs');
  if (tU) tU.innerHTML = mk([...g('美股指数'), ...g('美股映射'), ...g('美股映射·参考')]);
  const tHK = document.getElementById('drTblHK');
  if (tHK) tHK.innerHTML = mk(g('港股指数'));
}

/* ═══════ 2·日韩股市：标题动态 + 日韩指数表数据驱动（港股 drTblHK 由 drFillTables 渲染） ═══════ */
function drAsiaTable(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const heads = Array.prototype.slice.call(ana.querySelectorAll('.dr-h'));
  const h2 = heads.find(h => /日韩股市/.test(h.textContent || ''));
  if (!h2) return;
  if (d && d.date) {
    h2.textContent = h2.textContent.replace(/（[\d/．. ]+[^）]*）/,
      '（' + d.date.slice(5) + ' · 港股/日韩自动 / 韩股个股本机补）');
  }
  const card = h2.nextElementSibling;
  if (!card || !card.querySelector) return;
  const a = (d && d.asia) || {};
  const tbl = Array.prototype.slice.call(card.querySelectorAll('table.dr-tbl')).find(t =>
    (t.innerHTML || '').indexOf('日经') >= 0 || (t.innerHTML || '').indexOf('KOSPI') >= 0);
  if (!tbl || !tbl.querySelector('tbody')) return;
  const cls = (v) => v >= 0 ? 'dr-up' : 'dr-dn';
  const sign = (v) => v >= 0 ? '+' : '';
  const rows = [];
  if (a.nikkei) rows.push('<tr><td>日本</td><td>日经 225</td><td>' + a.nikkei.close.toLocaleString() +
    '</td><td class="' + cls(a.nikkei.chg_pct) + '">' + sign(a.nikkei.chg_pct) + a.nikkei.chg_pct.toFixed(2) + '%（' + a.nikkei.date.slice(5) + '）</td></tr>');
  if (a.kospi) rows.push('<tr><td>韩国</td><td>KOSPI</td><td>' + a.kospi.close.toLocaleString() +
    '</td><td class="' + cls(a.kospi.chg_pct) + '">' + sign(a.kospi.chg_pct) + a.kospi.chg_pct.toFixed(2) + '%（' + a.kospi.date.slice(5) + '）</td></tr>');
  // 韩股个股（三星/SK 海力士）：market.json asia.kr_stocks（stock.fengle.me NAVER 实时抓取）
  const kr = (a.kr_stocks && a.kr_stocks.stocks) || [];
  const krNames = {'005930': '三星电子', '000660': 'SK 海力士'};
  if (kr.length) {
    kr.forEach(s => {
      if (!s || !s.code) return;
      const pct = s.pct != null ? parseFloat(s.pct) : null;
      rows.push('<tr style="background:rgba(239,68,68,.06)"><td><b>韩国</b></td><td><b>' +
        (krNames[s.code] || s.name || s.code) + '</b> <span style="font-size:11px;color:var(--text-muted)">' + s.code + '.KS</span></td><td>' +
        (s.close != null ? s.close.toLocaleString() : '—') +
        (s.chg != null ? ' <span style="font-size:11px" class="' + cls(s.chg) + '">' + sign(s.chg) + (s.chg / 1000).toFixed(0) + '千</span>' : '') +
        '</td><td class="' + (pct != null ? cls(pct) : '') + '">' + (pct != null ? sign(pct) + pct.toFixed(2) + '%' : '—') + '</td></tr>');
    });
  } else {
    rows.push('<tr style="background:rgba(239,68,68,.06)"><td><b>韩国</b></td><td><b>三星电子/SK 海力士</b></td><td colspan="2" style="color:var(--text-muted)">待抓取（kr_stocks 未生成）</td></tr>');
  }
  tbl.querySelector('tbody').innerHTML = rows.join('');
  // 来源说明更新
  Array.prototype.slice.call(card.querySelectorAll('.dr-note')).forEach(n => {
    if ((n.textContent || '').indexOf('来源') >= 0 && (n.textContent || '').indexOf('znb') < 0) {
      n.innerHTML = '<span style="color:var(--text-muted)">来源：港股 = 云端 market.json（腾讯）；日经/KOSPI = 新浪 znb 接口（自动）｜ 三星/SK = stock.fengle.me NAVER 实时（自动抓取，无 15 分钟延迟）。</span>';
    }
  });
}

/* ═══════ 1·昨日A股走势总结：标题日期动态 + 写死 note 换数据驱动摘要（指数表 drTblA 保留动态） ═══════ */
function drAIndexSummary(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const heads = Array.prototype.slice.call(ana.querySelectorAll('.dr-h'));
  const h1 = heads.find(h => /昨日 A 股走势/.test(h.textContent || ''));
  if (!h1) return;
  // 标题日期动态化（复盘日 = market.date 的 A 股交易日）
  if (d && d.date) {
    h1.textContent = h1.textContent.replace(/（[\d/．. ]+）$/, '（' + d.date.slice(5) + '）');
  }
  const card = h1.nextElementSibling;
  if (!card || !card.querySelector) return;
  const q = (d && d.quotes) || {};
  const idx = ['a_sh', 'a_sz', 'a_cyb', 'a_kcb'].map(k => q[k]).filter(v => v && !v.error);
  if (!idx.length) return;
  const get = (code) => idx.find(v => v.code === code);
  const sh = get('sh000001'), cyb = get('sz399006');
  const style = (sh && cyb)
    ? (parseFloat(cyb.chg_pct) >= parseFloat(sh.chg_pct) ? '成长占优（创业板/科创强于上证）' : '权重/价值占优（上证强于创业板）')
    : '风格分化 —';
  const amtTxt = sh && sh.amt ? '两市成交约 ' + ((parseFloat(sh.amt) + (get('sz399001') ? parseFloat(get('sz399001').amt) : 0)) / 10000).toFixed(0) + ' 亿（腾讯口径）' : '成交额 —';
  // 替换写死的 3 个 dr-note（市场广度/领涨/领跌）为数据驱动摘要
  Array.prototype.slice.call(card.querySelectorAll('.dr-note')).forEach(n => n.remove());
  const div = document.createElement('div');
  div.className = 'dr-note';
  div.style.cssText = 'background:var(--bg-subtle);border-left:3px solid var(--accent);padding:8px 12px;border-radius:6px';
  div.innerHTML = '<b>数据驱动摘要（自动）：</b>' + style + ' ｜ ' + amtTxt +
    '。涨跌家数 / 板块资金流向 / 领涨领跌明细 待本机 agent 补充。';
  card.appendChild(div);
}

/* ═══════ 头部标注动态修正：复盘日保留（分析内容真实日期），指引日→下一交易日，追加行情日期 ═══════ */
function drFixHeader(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  // 复盘日 = 行情数据真实日期（数据驱动，禁止取静态写死文本）
  const reviewDate = (d && d.date) ? d.date : '';
  window._REVIEW_DATE = reviewDate;   // 供 drNextTradeDate 等基于复盘日推算
  let hdr = null;
  Array.prototype.slice.call(ana.querySelectorAll('.dr-tag')).forEach(s => {
    if ((s.textContent || '').indexOf('复盘日') >= 0) hdr = s;
  });
  if (!hdr) return;
  hdr.innerHTML = '复盘日 ' + reviewDate +
    ' ｜ 指引日（自动）' + drNextBizDay(reviewDate) +
    ' ｜ 行情 ' + (reviewDate || '—') + ' 自动刷新';
}

function drNextBizDay(baseDate) {
  // 指引日 = 基准复盘日的下一交易日（8/26 收盘 → 指引 8/27）；baseDate 缺省时退回系统时间
  const dt = baseDate ? new Date(baseDate.replace(/-/g, '/')) : new Date();
  dt.setDate(dt.getDate() + 1);
  while (dt.getDay() === 0 || dt.getDay() === 6) dt.setDate(dt.getDate() + 1);  // 跳过周末
  const wd = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
  const pad = (n) => String(n).padStart(2, '0');
  return dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate()) + '（' + wd + '）';
}

/* ═══════ 推导引擎：0·结论速览卡 + 7·次日开盘指引（数据驱动替代写死） ═══════ */
function drDeriveSections(d) {
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const q = (d && d.quotes) || {};
  const uk = (d && d.us_kline) || {};
  const usDji = uk.us_dji;
  const usChg = usDji ? usDji.prev.chg_pct : null;          // 隔夜道指涨跌（最新美股交易日）
  const usDate = usDji ? usDji.latest.date : '';
  const hstech = q.hk_hstech && q.hk_hstech.chg_pct !== undefined ? parseFloat(q.hk_hstech.chg_pct) : null;
  const vix = (window.VIX_PANEL_DATA && VIX_PANEL_DATA.cboe_vix) ? VIX_PANEL_DATA.cboe_vix.value : null;
  const thermo = (window.THERMO_DATA && THERMO_DATA.snapshot) ? THERMO_DATA.snapshot : null;
  const pePct = thermo ? thermo.pe_pct_10y : null;
  // 打分推导开盘预期（隔夜美股 ±2 / 恒生科技 ±1 / VIX ±1）
  let score = 0;
  const reasons = [];
  if (usChg !== null) {
    if (usChg > 0.5) score += 2; else if (usChg < -0.5) score -= 2;
    reasons.push('隔夜道指 ' + (usChg > 0 ? '+' : '') + usChg.toFixed(2) + '%');
  }
  if (hstech !== null) {
    if (hstech > 0.3) score += 1; else if (hstech < -0.3) score -= 1;
    reasons.push('恒生科技 ' + (hstech > 0 ? '+' : '') + hstech.toFixed(2) + '%');
  }
  if (vix !== null) {
    if (vix < 15) score += 1; else if (vix > 20) score -= 1;
    reasons.push('VIX ' + vix);
  }
  const openExp = score >= 2 ? ['偏强 · 高开概率↑', 'var(--red)']
    : score <= -2 ? ['偏弱 · 低开概率↑', 'var(--green)']
    : ['中性 · 平开震荡', 'var(--orange)'];
  // 风险等级（VIX>20 或 PE分位>80 → 防守；PE分位<30 → 进攻）
  let risk;
  if ((vix !== null && vix > 20) || (pePct !== null && pePct > 80)) risk = ['中高（防守优先）', 'var(--red)'];
  else if (pePct !== null && pePct < 30) risk = ['低（进攻窗口）', 'var(--green)'];
  else risk = ['中（均衡应对）', 'var(--gold)'];
  // 风格倾向（隔夜道指>纳指 → 价值占优；反之成长）
  const usIxic = uk.us_ixic ? uk.us_ixic.prev.chg_pct : null;
  const style = (usChg !== null && usIxic !== null)
    ? (usChg > usIxic ? '价值/资源占优（道指强于纳指）' : '成长/科技占优（纳指强于道指）')
    : '均衡';
  // 事件（明日 + 后日，来自 event_calendar）
  const evUrl = './output/event_calendar_' + new Date().toISOString().slice(0, 7) + '.json';
  const renderAll = (evMap) => {
    const d1 = drNextTradeDate(1), d2 = drNextTradeDate(2);
    const evs = [];
    [d1, d2].forEach(dd => {
      (evMap && evMap[dd] || []).slice(0, 4).forEach(e => {
        if (e.importance !== 'low') evs.push('<span class="dr-tag">' + (e.time || '') + '</span> ' + e.name +
          (e.country ? '（' + e.country + '）' : ''));
      });
    });
    const evHtml = evs.length ? evs.join('<br>') : '明日无重大事件（待知识星球/研报投喂补充）';
    // ── 渲染 0 · 结论速览卡 ──
    const h0 = Array.prototype.slice.call(ana.querySelectorAll('.dr-h')).find(h => /结论先行/.test(h.textContent || ''));
    if (h0 && h0.nextElementSibling && h0.nextElementSibling.querySelector) {
      const card = h0.nextElementSibling;
      card.innerHTML =
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:6px 0">' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">次日开盘预判</div><div style="font-weight:700;color:' + openExp[1] + '">' + openExp[0] + '</div><div style="font-size:11px;color:var(--text-muted);margin-top:4px">' + reasons.join(' · ') + '</div></div>' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">风格倾向</div><div style="font-weight:600">' + style + '</div><div style="font-size:11px;color:var(--text-muted);margin-top:4px">PE分位10y ' + (pePct != null ? pePct + '%' : '—') + ' · 破净率 ' + (thermo && thermo.below_net_ratio != null ? thermo.below_net_ratio + '%' : '—') + '</div></div>' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">风险等级</div><div style="font-weight:700;color:' + risk[1] + '">' + risk[0] + '</div><div style="font-size:11px;color:var(--text-muted);margin-top:4px">' + (vix !== null ? 'VIX ' + vix + ' · ' : '') + '格雷厄姆 ' + (thermo && thermo.graham != null ? thermo.graham : '—') + '</div></div>' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">关键事件</div><div style="font-weight:600;font-size:12px">' + evHtml.replace(/<br>/g, ' · ') + '</div></div>' +
        '</div>' +
        '<div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--blue);padding:8px 12px;border-radius:6px;margin-top:6px"><b>数据驱动速览（自动）：</b>隔夜美股 ' + (usDate || '—') + ' 收盘 · ' + reasons.join(' · ') + '。深度节奏判读/板块推演请以本机 agent 分析为准。</div>';
    }
    // ── 渲染 7 · 次日开盘指引 ──
    const h7 = Array.prototype.slice.call(ana.querySelectorAll('.dr-h')).find(h => /次日开盘指引/.test(h.textContent || ''));
    if (h7) {
      // 标题日期动态化：指引日 = 复盘日下一交易日（8/26 复盘 → 8/27 指引）
      const gd = drNextBizDay(d && d.date ? d.date : '');
      const gdShort = gd.slice(5).replace('-', '/');
      if (h7.textContent.indexOf('（' + gdShort) < 0) h7.textContent = '7 · 次日开盘指引（' + gdShort + '）';
    }
    if (h7 && h7.nextElementSibling && h7.nextElementSibling.querySelector) {
      const card = h7.nextElementSibling;
      card.innerHTML =
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:6px 0">' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">方向判断</div><div style="font-weight:700;color:' + openExp[1] + '">' + openExp[0] + '</div><div style="font-size:12px;color:var(--text-secondary);margin-top:4px">依据：' + reasons.join('；') + '。开盘预期由规则推导（隔夜美股/恒生科技/VIX），非写死。</div></div>' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">风格与操作</div><div style="font-weight:600">' + style + '</div><div style="font-size:12px;color:var(--text-secondary);margin-top:4px">温度计 PE分位10y ' + (pePct != null ? pePct + '%' : '—') + '（' + (pePct != null && pePct > 80 ? '高位·防守' : pePct != null && pePct < 30 ? '低位·进攻' : '中性') + '）；具体持仓操作请以本机 agent 分析为准。</div></div>' +
        '<div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px"><div class="dr-tag">风险与事件雷达</div><div style="font-weight:600">' + d1.slice(5) + ' · ' + d2.slice(5) + '</div><div style="font-size:12px;color:var(--text-secondary);margin-top:4px">' + evHtml + '</div></div>' +
        '</div>' +
        '<div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--orange);padding:8px 12px;border-radius:6px"><b>预案开关（规则生成）：</b>① 若开盘与预期一致（' + openExp[0] + '）→ 按计划执行；② 若反向大幅背离（隔夜美股盘中反转）→ 观望至 10:00 承接确认；③ 风险等级 ' + risk[0] + ' → 对应 ' + (risk[1] === 'var(--red)' ? '减仓防守' : risk[1] === 'var(--green)' ? '进攻但不满仓' : '均衡仓位') + '。证伪线以上证收盘 3860 为基准（可随盘面调整）。</div>';
    }
  };
  fetch(evUrl, { cache: 'no-store' })
    .then(r => r.ok ? r.json() : Promise.reject('HTTP ' + r.status))
    .then(ec => renderAll(ec.events || {}))
    .catch(() => renderAll(null));
}

function drNextTradeDate(n) {
  // 基于复盘日（window._REVIEW_DATE）推算，避免凌晨系统时间导致日期漂移；本地时区格式化
  const base = window._REVIEW_DATE || '';
  const dt = base ? new Date(base.replace(/-/g, '/')) : new Date();
  dt.setDate(dt.getDate() + n);
  const pad = (x) => String(x).padStart(2, '0');
  return dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate());
}

/* ═══════ 1.3 重点观测股（output/obs_deduce_latest.json，本机 agent 最新推演；无则提示待补） ═══════ */
function drLoadObserveStocks() {
  const box = document.getElementById('drTblObs');
  if (!box) return;
  fetch('./output/obs_deduce_latest.json', { cache: 'no-store' }).then(r => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(d => {
    const items = d.items || [];
    if (!items.length) throw new Error('empty');
    const date = d.date || '';
    // 标题日期动态化：obs_deduce 收盘日 + 下一交易日推演（8/26 收盘 → 8/27 推演）
    const ana = document.getElementById('drAnalysis');
    if (ana && date) {
      const h13 = Array.prototype.slice.call(ana.querySelectorAll('.dr-h'))
        .find(h => /重点观测股/.test(h.textContent || ''));
      if (h13) {
        const nd = drNextBizDay(date).slice(5).replace('-', '/');
        h13.textContent = '1.3 · 重点观测股（' + items.length + ' 只 · ' +
          date.slice(5).replace('-', '/') + ' 收盘 + ' + nd + ' 推演）';
      }
    }
    const cls = (v) => v >= 0 ? 'dr-up' : 'dr-dn';
    const sign = (v) => v >= 0 ? '+' : '';
    const trendCls = (t) => (t.indexOf('强') >= 0 || t.indexOf('上') >= 0) ? 'var(--red)' : (t.indexOf('弱') >= 0 || t.indexOf('跌') >= 0 ? 'var(--green)' : 'var(--text-secondary)');
    const rows = items.map(it => {
      const pct = it.chg_last != null ? parseFloat(it.chg_last) : null;
      const dev = it.dev_ma5 != null ? parseFloat(it.dev_ma5) : null;
      return '<tr><td><b>' + it.name + '</b> <span style="font-size:11px;color:var(--text-muted)">' + (it.code || '').toUpperCase() + '</span></td>' +
        '<td>' + (it.close != null ? it.close : '—') + (pct !== null ? ' <span class="' + cls(pct) + '">' + sign(pct) + pct.toFixed(2) + '%</span>' : '') + '</td>' +
        '<td style="font-size:12px">' + (it.sector || '') + '</td>' +
        '<td style="font-size:12px"><span class="dr-tag">' + (it.pattern || '') + '</span> MA5 ' + (it.ma5 != null ? it.ma5 : '—') +
          (dev !== null ? ' <span class="' + cls(dev) + '">' + sign(dev) + dev.toFixed(1) + '%</span>' : '') +
          ' 5日' + (it.chg5 != null ? ' <span class="' + cls(parseFloat(it.chg5)) + '">' + sign(parseFloat(it.chg5)) + parseFloat(it.chg5).toFixed(1) + '%</span>' : '') +
          ' 量比' + (it.vol_ratio != null ? it.vol_ratio : '—') + '</td>' +
        '<td style="color:' + trendCls(it.trend || '') + ';font-weight:600;font-size:13px">' + (it.trend || '') + '</td>' +
        '<td style="font-size:12px">' + (it.open_label || '') + '</td></tr>';
    }).join('');
    box.innerHTML = '<table class="dr-tbl"><thead><tr><th>股票</th><th>' + date + ' 收盘/涨跌</th><th>板块</th><th>技术形态（10日K线）</th><th>推演</th><th>开盘方式</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }).catch(() => {
    box.innerHTML = '<p class="dr-note">重点观测股推演：待本机 agent 补全（obs_deduce 尚未生成）。</p>';
  });
}

// ===== 每日复盘：前一日 TOP10（output/top10_history.json 最新交易日）=====
function drLoadTop10() {
  const el = document.getElementById('drTblTop10');
  if (!el) return;
  fetch('./output/top10_history.json', { cache: 'no-store' }).then(r => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(hist => {
    const dates = Object.keys(hist || {}).filter(d => hist[d] && Array.isArray(hist[d].top10) && hist[d].top10.length);
    if (!dates.length) { el.innerHTML = '<div class="dr-note">暂无 TOP10 历史数据</div>'; return; }
    dates.sort();
    const last = dates[dates.length - 1];
    const stocks = hist[last].top10;
    let h = `<div class="dr-tag" style="margin-bottom:4px">数据日：${last} ｜ 共 ${stocks.length} 只（与总站首页 TOP 表一致）</div>`;
    h += '<table class="dr-tbl"><thead><tr><th>#</th><th>股票</th><th>市场</th><th>信号等级</th><th>EMA</th><th>评分</th><th>涨跌</th><th>收盘</th></tr></thead><tbody>';
    stocks.forEach((r, i) => {
      const chg = Number(r.change_pct) || 0;
      const cls = chg > 0 ? 'dr-up' : (chg < 0 ? 'dr-dn' : '');
      const mkt = r.market || '主板';
      h += `<tr><td>${i + 1}</td><td><b>${r.name}</b> <span style="font-size:11px;color:var(--text-muted)">${r.code}</span></td>
        <td>${mkt}</td><td>${r.grade || '—'}</td><td>${r.ema_score != null ? r.ema_score + '/7' : '—'}</td>
        <td style="font-weight:700">${r.total_score != null ? r.total_score : '—'}</td>
        <td class="${cls}">${chg > 0 ? '+' : ''}${chg.toFixed(2)}%</td><td>¥${(Number(r.close) || 0).toFixed(2)}</td></tr>`;
    });
    h += '</tbody></table>';
    el.innerHTML = h;
  }).catch(err => {
    el.innerHTML = `<div class="dr-note">TOP10 加载失败：${err}</div>`;
  });
}

// ===== 每日复盘：前一日金钻（output/gate_data.json 三个门控分类）=====
function drLoadDiamond() {
  const el = document.getElementById('drTblDiamond');
  if (!el) return;
  fetch('./output/gate_data.json', { cache: 'no-store' }).then(r => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(g => {
    const gates = g.gates || {};
    const GATE_ORDER = ['all_a', 'pool', 'sector_top100_to4'];
    const keys = GATE_ORDER.filter(k => gates[k]);
    if (!keys.length) { el.innerHTML = '<div class="dr-note">暂无金钻门控数据</div>'; return; }
    const date = g.data_date || '';
    let h = `<div class="dr-tag" style="margin-bottom:4px">数据日：${date} ｜ 门控：${keys.map(k => gates[k].label).join(' / ')}</div>`;
    keys.forEach(k => {
      const gk = gates[k];
      const ov = gk.overview || {};
      const stocks = gk.stocks || [];
      h += `<div style="margin:10px 0 4px;font-weight:600">${gk.label}（扫描 ${gk.scope_size} 只）— 命中 ${ov.total || stocks.length} 只</div>`;
      if (ov.analysis) h += `<div class="dr-note" style="font-size:12px;color:var(--text-secondary)">${ov.analysis}</div>`;
      if (!stocks.length) { h += '<div class="dr-note">无命中</div>'; return; }
      h += '<table class="dr-tbl"><thead><tr><th>股票</th><th>分类</th><th>信号日期</th><th>涨跌幅</th><th>阳线</th><th>DY2</th><th>MA5&gt;MA60</th></tr></thead><tbody>';
      stocks.forEach(s => {
        const sig = (s.signals && s.signals[0]) || {};
        const det = sig.detail || {};
        const pct = det.pct != null ? Number(det.pct) : null;
        const pctCls = pct > 0 ? 'dr-up' : (pct < 0 ? 'dr-dn' : '');
        const prim = s.primary || sig.type || '—';
        const primCls = prim.includes('起涨') ? 'color:var(--red);font-weight:700'
          : (prim.includes('买入') ? 'color:var(--blue);font-weight:600'
          : 'color:var(--gold);font-weight:600');
        const dy2 = det.dy2 != null ? Number(det.dy2) : null;
        h += `<tr><td><b>${s.name}</b> <span style="font-size:11px;color:var(--text-muted)">${s.code}</span></td>
          <td style="${primCls}">${prim}</td>
          <td>${sig.date || '—'}</td>
          <td class="${pctCls}">${pct != null ? (pct > 0 ? '+' : '') + pct.toFixed(2) + '%' : '—'}</td>
          <td>${det.yang ? '✓' : (det.yang === false ? '✗' : '—')}</td>
          <td>${dy2 != null ? dy2.toFixed(3) : '—'}</td>
          <td>${det['ma5>ma60'] ? '✓' : (det['ma5>ma60'] === false ? '✗' : '—')}</td></tr>`;
      });
      h += '</tbody></table>';
    });
    el.innerHTML = h;
  }).catch(err => {
    el.innerHTML = `<div class="dr-note">金钻数据加载失败：${err}</div>`;
  });
}

'''

TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html")]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

JS_START = "// ===== 每日复盘 Tab ====="
JS_END = "// ===== 金钻数据加载 =====\n"  # 兜底未命中则用 renderDailyReview 前


def _replace_js(idx, js):
    """幂等：已存在 JS_START 则整体替换到 JS_END；否则在 Tab 切换前插入"""
    if JS_START in idx:
        s = idx.index(JS_START)
        # 找函数块结束：renderDailyReview 之后到 "// ===== Tab 切换" 或文件末尾
        end_marker = "// ===== Tab 切换"
        e = idx.index(end_marker, s) if end_marker in idx[s:] else len(idx)
        return idx[:s] + js + "\n" + idx[e:], True
    return idx, False


for tname in TARGETS:
    path = os.path.join(BASE, tname)
    idx = open(path, encoding="utf-8").read()
    changed = False

    # ① nav 按钮：总览 与 实时盯盘 之间（兼容有/无图标两种格式）
    btn_anchor = ('<button class="nav-btn active" data-tab="overview">总览</button>\n'
                  '<button class="nav-btn" data-tab="realtime">👁 实时盯盘</button>')
    btn_anchor2 = ('<button class="nav-btn active" data-tab="overview">总览</button>\n'
                   '<button class="nav-btn" data-tab="realtime">实时盯盘</button>')
    if 'data-tab="dailyreview"' not in idx:
        anchor = btn_anchor if btn_anchor in idx else (btn_anchor2 if btn_anchor2 in idx else None)
        if anchor:
            idx = idx.replace(anchor,
                '<button class="nav-btn active" data-tab="overview">总览</button>\n'
                + BTN + '\n'
                + anchor.split('\n', 1)[1], 1)
            changed = True
            print(f"✅ {tname}: 已插入 nav 按钮")
        else:
            # 兜底：任意 realtime 按钮前插入
            rt = '<button class="nav-btn" data-tab="realtime">👁 实时盯盘</button>'
            if rt in idx:
                idx = idx.replace(rt, BTN + '\n' + rt, 1)
                changed = True
                print(f"✅ {tname}: 已插入 nav 按钮（兜底锚点）")
            else:
                print(f"⚠️ {tname}: 未找到 nav 锚点，跳过按钮注入")

    # ② tab 内容区
    tab_marker = "<!-- Tab: 每日复盘"
    if 'id="tab-dailyreview"' in idx:
        # 用最新 TAB_BLOCK 替换（整体替换支持升级）
        s = idx.index(tab_marker)
        e = idx.index("<!-- Tab: 实时盯盘 -->", s)
        idx = idx[:s] + TAB_BLOCK + "\n" + idx[e:]
        changed = True
        print(f"✅ {tname}: 已用最新版本更新 tab 内容区")
    else:
        rt_anchor = "<!-- Tab: 实时盯盘 -->"
        if rt_anchor in idx:
            idx = idx.replace(rt_anchor, TAB_BLOCK + "\n" + rt_anchor, 1)
            changed = True
            print(f"✅ {tname}: 已插入 tab 内容区")

    # ③ JS 块
    if JS_START in idx:
        idx, replaced = _replace_js(idx, JS_BLOCK)
        if replaced:
            changed = True
            print(f"✅ {tname}: 已用最新版本更新 JS 块")
    else:
        js_anchor = "// ===== Tab 切换 ====="
        if js_anchor in idx:
            idx = idx.replace(js_anchor, JS_BLOCK + "\n" + js_anchor, 1)
            changed = True
            print(f"✅ {tname}: 已插入 JS 块")

    # ④ tab 切换绑定：renderDailyReview 挂到点击事件
    bind_anchor = "if (btn.dataset.tab === 'diamond') loadDiamondTab();"
    if bind_anchor in idx and "btn.dataset.tab === 'dailyreview'" not in idx:
        idx = idx.replace(bind_anchor,
            "if (btn.dataset.tab === 'dailyreview') renderDailyReview();\n    " + bind_anchor, 1)
        changed = True
        print(f"✅ {tname}: 已插入 tab 切换绑定")
    elif bind_anchor not in idx:
        # 兜底绑定：在 diamond 绑定类似位置
        bind2 = "loadDiamondTab();"
        if bind2 in idx and "renderDailyReview()" not in idx:
            idx = idx.replace(bind2, "renderDailyReview();\n    " + bind2, 1)
            changed = True
            print(f"✅ {tname}: 已插入 tab 切换绑定（兜底）")

    if changed:
        open(path, "w", encoding="utf-8").write(idx)
        print(f"  💾 {tname} 已保存")
    else:
        print(f"  ⏭️ {tname} 无改动（已是最新）")
