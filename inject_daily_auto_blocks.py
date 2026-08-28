#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 前端注入（每日复盘 tab → 自动宏观日历 + 自动新闻池 只读区块）
=========================================================================
幂等地在 index.html / index_template.html / deploy/index.html 的每日复盘 tab 中
追加两个只读区块（2026-08-28 新增）：

  id="drAutoMacro"   自动宏观日历  ← fetch output/daily_macro_latest.json
  id="drAutoNews"    自动新闻池    ← fetch output/daily_news_latest.json

设计原则：
  1. 只读、独立容器 —— 与 agent 手写区（drAnalysis）并存，互不覆盖；
  2. 幂等：HTML / JS 函数 / 调用行 各自守卫，重复运行不产生重复块；
  3. JS 函数插在「Tab 切换」区之后、「七信号引擎」之前 —— 避开
     inject_daily_review_tab.py 与 inject_feed_review.py 的整体替换区间，
     不会被它们的重跑抹掉；
  4. TARGETS 含 index_template.html —— rebuild_html.py 重建后天然保留。

用法:
  python inject_daily_auto_blocks.py
  python inject_daily_auto_blocks.py index.html
"""
import os, sys, re

BASE = os.path.dirname(os.path.abspath(__file__))
TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html")]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

HTML_MARK = "id=\"drAutoMacro\""
JS_FN_MARK = "function drLoadAutoBlocks"

# ── HTML 区块（插在 drFeedReview 卡片结束之后、容器 </div> 之前）──────
HTML_ANCHOR = '<p class="dr-note" id="drFeedReviewBody">投喂复盘加载中…</p>\n</div>'
HTML_BLOCK = HTML_ANCHOR + """
<!-- Tab: 自动宏观日历 + 自动新闻池 + 推演回测（2026-08-28 新增 · 只读 · 独立于 agent 手写区） -->
<div class="dr-card" id="drAutoBacktest">
  <div class="dr-h">🎯 推演回测（昨日推演 vs 实际）<span class="dr-tag" id="drBacktestDate"></span></div>
  <p class="dr-note" id="drBacktestBody">回测加载中…</p>
</div>
<div class="dr-card" id="drAutoMacro">
  <div class="dr-h">📊 自动宏观日历 <span class="dr-tag" id="drMacroDate"></span></div>
  <p class="dr-note" id="drMacroBody">宏观数据加载中…</p>
</div>
<div class="dr-card" id="drAutoNews">
  <div class="dr-h">📰 自动新闻池 <span class="dr-tag" id="drNewsDate"></span></div>
  <p class="dr-note" id="drNewsBody">新闻池加载中…</p>
</div>
"""

# ── JS 渲染函数（插在「七信号引擎」注释前）──────────────────────────
JS_ANCHOR = "// JavaScript 七信号引擎"
JS_BLOCK = r"""
// ===== 自动宏观 + 新闻池渲染（2026-08-28 新增 · 只读 · 独立于 agent 手写区）=====
function drLoadAutoBlocks() {
  var esc2 = function(s){ return (s == null ? '' : String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  // ① 宏观日历
  fetch('output/daily_macro_latest.json').then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); }).then(function(d){
    var el = document.getElementById('drMacroBody'); if (!el) return;
    document.getElementById('drMacroDate').textContent = '数据日期 ' + (d.date || '—') + ' · ' + (d.generated_at || '');
    var c = d.china || {}; var h = '<div class="dr-note"><b>中国宏观（akshare 主源）</b></div>';
    var row = function(k, o){
      if (!o || !o.latest) return;
      var v = o.latest, s = '—';
      try { s = Object.keys(v).map(function(kk){ return kk + '=' + esc2(v[kk]); }).join(' · '); } catch(e) {}
      h += '<div class="dr-note">' + k + '：' + s + '</div>';
    };
    row('PMI', c.pmi); row('GDP', c.gdp); row('CPI', c.cpi); row('LPR', c.lpr);
    var us = (d.us || {}).indicators || {};
    var usHits = Object.keys(us).filter(function(k){ return us[k] && us[k].length; });
    if (usHits.length) {
      h += '<div class="dr-h">美国宏观（新闻源抽取 · best-effort）</div>';
      usHits.forEach(function(k){
        var items = us[k] || [];
        h += '<div class="dr-note"><b>' + esc2(k) + '</b>：' + items.slice(0,2).map(function(it){
          return esc2(((it.evidence || [])[0] || '')) + ' <span class="dr-tag">[' + esc2(it.source) + ']</span>';
        }).join('；') + '</div>';
      });
    }
    el.innerHTML = h;
  }).catch(function(e){
    var el = document.getElementById('drMacroBody'); if (el) el.innerHTML = '<p class="dr-note">宏观数据加载失败：' + e + '</p>';
  });
  // ② 新闻池（按标签取前 6 条）
  fetch('output/daily_news_latest.json').then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); }).then(function(d){
    var el = document.getElementById('drNewsBody'); if (!el) return;
    document.getElementById('drNewsDate').textContent = '数据日期 ' + (d.date || '—') + ' · 共 ' + (d.total || 0) + ' 条 · ' + (d.generated_at || '');
    var tags = ['宏观', '科技', '政策', '产业'];
    var h = '';
    tags.forEach(function(t){
      var items = (d.news || []).filter(function(x){ return (x.tags || []).indexOf(t) >= 0; }).slice(0, 6);
      if (!items.length) return;
      h += '<div class="dr-h">' + esc2(t) + '（' + items.length + '）</div>';
      items.forEach(function(it){
        var src = it.source ? ' <span class="dr-tag">[' + esc2(it.source) + ' ' + esc2(String(it.time || '').slice(11, 16)) + ']</span>' : '';
        if (it.url) h += '<div class="dr-note">· <a href="' + esc2(it.url) + '" target="_blank" rel="noopener" style="color:var(--blue)">' + esc2(it.title) + '</a>' + src + '</div>';
        else h += '<div class="dr-note">· ' + esc2(it.title) + src + '</div>';
      });
    });
    if (!h) h = '<p class="dr-note">暂无新闻数据</p>';
    el.innerHTML = h;
  }).catch(function(e){
    var el = document.getElementById('drNewsBody'); if (el) el.innerHTML = '<p class="dr-note">新闻池加载失败：' + e + '</p>';
  });
  // ③ 推演回测摘要（2026-08-28 新增 · 数据源 output/backtest_daily.json）
  fetch('output/backtest_daily.json').then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); }).then(function(d){
    var el = document.getElementById('drBacktestBody'); if (!el) return;
    var lt = d.latest || {};
    document.getElementById('drBacktestDate').textContent = lt.date ? '推演日 ' + lt.date + ' · ' + (d.updated_at || '') : '';
    if (!lt.n) {
      el.innerHTML = '<p class="dr-note">暂无回测结果（当日推演需次日收盘后自动比对）</p>';
      return;
    }
    var h = '<div class="dr-note">样本 <b>' + lt.n + '</b> 只 · 方向准确率 <b>' + lt.dir_acc + '%</b> · 开盘准确率 <b>' + lt.open_acc + '%</b></div>';
    var bt = d.by_trend || {};
    var keys = Object.keys(bt);
    if (keys.length) {
      h += '<div class="dr-h">分推演类型（方向准确率）</div>';
      keys.sort(function(a, b){ return (bt[b].n || 0) - (bt[a].n || 0); }).forEach(function(t){
        var v = bt[t] || {};
        var acc = v.n ? Math.round(v.dir_hit / v.n * 100) : 0;
        h += '<div class="dr-note">· ' + esc2(t) + '（' + (v.n || 0) + ' 只）：' + acc + '%</div>';
      });
    }
    el.innerHTML = h;
  }).catch(function(e){
    var el = document.getElementById('drBacktestBody'); if (el) el.innerHTML = '<p class="dr-note">回测数据加载失败：' + e + '</p>';
  });
}

// JavaScript 七信号引擎"""

# ── 调用行（跟在 drLoadFeedReview 调用之后）────────────────────────
CALL_ANCHOR = "if (btn.dataset.tab === 'dailyreview') drLoadFeedReview();"
CALL_LINE = "    if (btn.dataset.tab === 'dailyreview') drLoadAutoBlocks();"


def inject(path):
    p = os.path.join(BASE, path)
    if not os.path.exists(p):
        print(f"⏭️ {path} 不存在，跳过")
        return
    idx = open(p, encoding="utf-8").read()
    changed = False

    # ① HTML 区块（2026-08-28: 升级式——先总是移除旧自动块，再按需插新版）
    _old_re = re.compile(r'<!-- Tab: 自动宏观日历 \+ 自动新闻池（.*?<div class="dr-card" id="drAutoNews">.*?</div>\s*\n', re.S)
    _idx2 = _old_re.sub('', idx)
    if _idx2 != idx:
        changed = True
        print(f"  ♻️ {path}: 已移除旧自动区块")
        idx = _idx2
    if "id=\"drAutoBacktest\"" not in idx:
        if HTML_ANCHOR in idx:
            idx = idx.replace(HTML_ANCHOR, HTML_BLOCK, 1)
            changed = True
            print(f"✅ {path}: 已插入自动区块（回测+宏观+新闻）")
        else:
            print(f"⚠️ {path}: 未找到 drFeedReview 卡片锚点，跳过 HTML 注入")
    else:
        print(f"⏭️ {path}: 自动区块（含回测）已存在")

    # ② JS 渲染函数（2026-08-28: 升级式——含回测段的 drLoadAutoBlocks）
    if "// ③ 推演回测摘要" not in idx:
        if JS_ANCHOR in idx:
            _js_re = re.compile(r'// ===== 自动宏观 \+ 新闻池渲染.*?(?=\n// JavaScript 七信号引擎)', re.S)
            _idx3 = _js_re.sub('', idx)
            _idx3 = _idx3.replace(JS_ANCHOR, JS_BLOCK, 1)
            changed = True
            print(f"✅ {path}: 已插入/升级 drLoadAutoBlocks JS（含回测渲染）")
            idx = _idx3
        else:
            print(f"⚠️ {path}: 未找到七信号引擎锚点，跳过 JS 注入")
    else:
        print(f"⏭️ {path}: drLoadAutoBlocks JS（含回测）已存在")

    # ③ 调用行
    if CALL_ANCHOR in idx and CALL_LINE.strip() not in idx:
        idx = idx.replace(CALL_ANCHOR, CALL_ANCHOR + "\n" + CALL_LINE, 1)
        changed = True
        print(f"✅ {path}: 已插入 drLoadAutoBlocks 调用")
    elif CALL_LINE.strip() in idx:
        print(f"⏭️ {path}: 调用行已存在")

    if changed:
        with open(p, "w", encoding="utf-8") as f:
            f.write(idx)
        print(f"💾 {path}: 已写入")


if __name__ == "__main__":
    for t in TARGETS:
        inject(t)
