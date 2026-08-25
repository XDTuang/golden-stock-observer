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
  const loadAna = (q) => {
    if (!ana) return;
    fetch('./data/daily_review/analysis.html', { cache: 'no-store' }).then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    }).then(t => {
      // 抹掉 analysis.html 里的硬编码"3·隔夜美股复盘"模块——由 drRenderUsDualDay 数据驱动渲染
      t = t.replace(/<div class="dr-h">\s*3\s*[·・\.\s]*\s*隔夜美股复盘[\s\S]*?(?=<div class="dr-h">|<\/div>\s*<style|$)/, '');
      ana.innerHTML = t;
      drFillTables(q || {});
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
      // 数据驱动双日表（根治 analysis.html 硬编码滞后）
      drRenderUsDualDay(d);
      loadAna(q);
    }).catch(err => {
      mkt.innerHTML = `<p class="dr-note">行情加载失败：${err}</p>`;
      loadAna();
    });
  } else {
    loadAna();
  }
}

/* ═══════ 隔夜美股复盘（双日表·数据驱动，从 market.json.us_kline 读 prev+latest） ═══════ */
function drRenderUsDualDay(d) {
  if (!d || !d.us_kline || Object.keys(d.us_kline).length === 0) return;
  const k = d.us_kline;
  const usIdxKeys = ['us_dji', 'us_inx', 'us_ixic'];
  const usMapKeys = ['us_mu', 'us_sndk', 'us_lite', 'us_aaoi', 'us_cohr', 'us_wdc', 'us_skhy', 'us_mrvl'];
  const nameMap = {
    us_dji:'道琼斯', us_inx:'标普500', us_ixic:'纳斯达克',
    us_mu:'MU 美光', us_sndk:'SNDK 闪迪', us_lite:'LITE 朗美通', us_aaoi:'AAOI',
    us_cohr:'COHR', us_wdc:'WDC 西部数据', us_skhy:'SKHY 海力士', us_mrvl:'MRVL 迈威尔',
  };
  const sample = k[usIdxKeys[0]] || Object.values(k)[0];
  const latestDate = sample.latest.date, prevDate = sample.prev.date;
  const rows = (keys) => keys.filter(kk => k[kk]).map(kk => {
    const e = k[kk], l = e.latest, p = e.prev;
    const pct = p.chg_pct;
    const cls = pct >= 0 ? 'dr-up' : 'dr-dn';
    const sign = pct >= 0 ? '+' : '';
    return `<tr><td>${nameMap[kk]||kk}</td><td>${l.close.toLocaleString()}</td><td class="${cls}">${sign}${pct.toFixed(2)}%</td><td>${p.close.toLocaleString()}</td><td class="${cls}">${sign}${pct.toFixed(2)}%</td></tr>`;
  }).join('');
  const html = `<div class="dr-h">3 · 隔夜美股复盘（双日表 · V2 数据驱动）</div>
<div class="dr-note"><b>为什么双日？</b>V1 教训：华尔街见闻凌晨快讯实为前一交易日收盘（A 股与美股存在 T-1 映射），若误当"隔夜"则指引方向完全做反。双日表强制呈现<b>映射源</b>与<b>隔夜</b>两日。说明：<b>隔夜最新 = ${latestDate}</b>（最新已收盘美股交易日），<b>前一交易日 = ${prevDate}</b>。</div>
<table class="dr-tbl"><thead><tr><th>标的</th><th>${prevDate} 收盘</th><th>${prevDate} 涨跌</th><th>${latestDate} 收盘</th><th>${latestDate} 涨跌（隔夜）</th></tr></thead>
<tbody>${rows(usIdxKeys)}</tbody></table>
<div class="dr-h" style="margin-top:10px;font-size:13px">美股映射个股</div>
<table class="dr-tbl"><thead><tr><th>标的</th><th>${prevDate} 收盘</th><th>${prevDate} 涨跌</th><th>${latestDate} 收盘</th><th>${latestDate} 涨跌（隔夜）</th></tr></thead>
<tbody>${rows(usMapKeys)}</tbody></table>`;
  const ana = document.getElementById('drAnalysis');
  if (!ana) return;
  const div = document.createElement('div');
  div.id = 'drUsDualDayInjected';
  div.innerHTML = html;
  ana.insertBefore(div, ana.firstChild);
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
