#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 前端注入（每日复盘 tab → 投喂复盘板块）
====================================================
幂等地在 index.html / index_template.html / deploy/index.html 的
每日复盘 tab 中追加「投喂复盘」卡片区块 + 渲染 JS（fetch output/feed_review_latest.json）。

标记（幂等）:
  <!-- Tab: 投喂复盘 -->            内容区锚点
  // ===== 投喂复盘渲染 =====         JS 锚点

用法:
  python inject_feed_review.py                 # 注入全部目标
  python inject_feed_review.py deploy/index.html
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html")]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

TAB_MARK = "<!-- Tab: 投喂复盘 -->"
JS_MARK = "// ===== 投喂复盘渲染 =====\n"

TAB_BLOCK = """
<!-- Tab: 投喂复盘 -->
<div class="dr-card" id="drFeedReview">
  <div class="dr-h" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
    <span>📥 投喂复盘（当日投喂 × 盘面信号）</span>
    <button id="drFeedBtn" style="font-size:12px;padding:4px 12px;border-radius:14px;border:1px solid var(--border);background:var(--bg-card);color:var(--text);cursor:pointer;white-space:nowrap">📥 投喂</button>
  </div>
  <p class="dr-note" id="drFeedReviewBody">投喂复盘加载中…</p>
</div>
"""

# raw 字符串：保留 JS 内的 \n \s 等字面量，避免 Python 转义破坏 JS 语法
JS_BLOCK = r"""
// ===== 投喂复盘渲染 =====
// === feed v4: 内置 AI 综合推演(ai_synthesis) 渲染 —— 修复 rebuild 后本机产物丢失 ===
// 2026-08-31 加固（事故复盘）：ai_synthesis 各字段增加「类型防御」+「子块隔离」。
//   事故：8/31 产物把 theme_resonance / nvda_chain_map / holding_map / risks 降级成纯字符串，
//   本函数按对象数组解析 → theme_resonance.forEach 抛 TypeError → 整个 then() 回调中断
//   → el.innerHTML 永不赋值 → 投喂复盘整块空白（连已拼好的内容一起丢）。
//   现改为：字符串 / 对象 / 数组三种形态都能渲染；每个子块独立 try/catch，单块坏不影响全局。
function drLoadFeedReview() {
  drFeedModalInit();
  const el = document.getElementById('drFeedReviewBody');
  if (!el) return;
  const esc = s => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  /* ═══════════ FEED-RICHTEXT-BEGIN（老站接入 · 2026-09-18）═══════════
     ai_synthesis 各字段由本机 agent 手写，含 <b> 强调与 <span class="dk-*"> 语义色；
     此前统一 esc() → 页面直接显示字面「<b>…</b>」（2026-09-18 用户报障）。
     治本：先整体转义，仅放行白名单标签；<script> 等其余一律保持转义（无 XSS 面）。
     机器数据（日期/价格/代码/枚举/股票名）仍走 esc()，口径不变。 */
  const DKCLS = /^dk-(main|caution|risk|data|up|dn|neutral)$/;
  const rich = (v) => esc(v == null ? '' : v)
    .replace(/&lt;(\/?)(b|i)&gt;/g, '<$1$2>')
    .replace(/&lt;br\s*\/?&gt;/g, '<br>')
    .replace(/&lt;span class="(dk-[a-z0-9-]+)"&gt;/g, (m, c) => (DKCLS.test(c) ? '<span class="' + c + '">' : m))
    .replace(/&lt;\/span&gt;/g, '</span>');
  /* ═══════════ FEED-RICHTEXT-END ═══════════ */
  // 类型归一：数组→原样；对象→[对象]；字符串→[字符串]；空→[]
  const asArr = v => Array.isArray(v) ? v : (v && typeof v === 'object' ? [v] : (v ? [String(v)] : []));
  // 取文本：字符串→原样；对象→desc/text/summary/note 依次取值；其余→JSON
  const asText = v => (typeof v === 'string' ? v
    : (v && typeof v === 'object' ? (v.desc || v.text || v.summary || v.note || v.event || '') : ''));  // 2026-09-10：补 event 字段（V3 t1_radar 产物为 {time,event,impact} 对象，白名单缺 event 曾致 [object Object]）
  // 2026-09-10：任意值→可读文本。对象白名单取不到时拼接其字符串字段值，绝不让对象落入 String() 产生 [object Object]
  const asTxt = v => (typeof v === 'string' ? v
    : (v && typeof v === 'object' ? (asText(v) || Object.values(v).filter(x => typeof x === 'string').join(' '))
    : String(v == null ? '' : v)));
  // 子块隔离：单块出错只在控制台告警 + 占位，不影响其余块
  const safe = (label, fn) => { try { return fn() || ''; }
    catch (e) { console.warn('[投喂复盘] ' + label + ' 渲染失败：', e);
      return '<div class="dr-note dr-tag">⚠️ ' + esc(label) + ' 数据格式异常，已跳过</div>'; } };
  const chips = arr => asArr(arr).map(s =>
    '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('');

  fetch('output/feed_review_latest.json')
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(d => {
      let h = '';
      const pred = d.prediction || {};
      const bias = pred.bias || '—';
      const biasCls = /^偏多/.test(bias) ? 'dr-up' : (/^偏空/.test(bias) ? 'dr-dn' : '');
      h += '<div class="dr-note">数据日期 <b>' + esc(d.data_date || '—') + '</b> · 投喂 ' +
           (d.feed_count || (d.feeds || []).length || 0) + ' 条 · 来源 ' +
           (d.source === 'cloud' ? '云端 08:15' : '本地 19:30') + '</div>';
      h += '<div class="dr-note"><b>后市预判：<span class="' + biasCls + '">' + esc(bias) +
           '</span></b>（score ' + (pred.bias_score == null ? '—' : pred.bias_score) + '）</div>';
      asArr(pred.reasons).forEach(r => h += '<div class="dr-note">· ' + rich(asTxt(r)) + '</div>');  // 2026-09-10：asTxt 防对象→[object Object]

      // ===== 当日投喂 =====
      h += safe('当日投喂', () => {
        const feeds = d.feeds || [];
        if (!feeds.length) return '';
        let s = '<div class="dr-h">当日投喂</div><table class="dr-tbl"><thead><tr><th>类别</th><th>来源</th><th>标题</th><th>关键词</th></tr></thead><tbody>';
        feeds.forEach(f => {
          s += '<tr><td>' + esc(f.category) + '</td><td>' + esc(f.source) + '</td><td>' + esc(f.title) +
               '</td><td style="color:var(--text-muted)">' + asArr(f.keywords).slice(0, 4).map(esc).join(' / ') + '</td></tr>';
        });
        return s + '</tbody></table>';
      });

      // ===== 机制 × 语料交叉验证 =====
      let caEmpty = false;
      h += safe('交叉验证', () => {
        const ca = asArr(d.cross_analysis);
        if (!ca.length) { caEmpty = true; return '<div id="drCrossSlot"></div>'; }
        let s = '<div class="dr-h">机制 × 语料交叉验证</div><table class="dr-tbl"><thead><tr><th>投喂</th><th>匹配信号标的</th><th>判定</th></tr></thead><tbody>';
        ca.forEach(c => {
          if (typeof c === 'string') { s += '<tr><td colspan="3" class="dr-note">' + esc(c) + '</td></tr>'; return; }
          const v = c.verdict || '';
          const cls = v === '共振' ? 'dr-up' : (v === '背离' ? 'dr-dn' : 'dr-tag');
          s += '<tr><td>' + esc(c.feed || c.theme || '') + '</td><td>' + (asArr(c.related_stocks).join('、') || '—') +
               '</td><td class="' + cls + '">' + esc(v) + '</td></tr>';
        });
        return s + '</tbody></table>';
      });

      // ===== T+1 关注 / 风险提示 =====
      h += safe('T+1 关注', () => {
        const t1 = asArr(pred.t1_focus);
        if (!t1.length) return '';
        let s = '<div class="dr-h">T+1 关注</div>';
        t1.forEach(t => s += '<div class="dr-note">· ' + rich(asTxt(t)) + '</div>');  // 2026-09-10：asTxt 防对象→[object Object]
        return s;
      });
      h += safe('风险提示', () => {
        const risks = asArr(pred.risks);
        if (!risks.length) return '';
        let s = '<div class="dr-h">风险提示</div>';
        risks.forEach(r => s += '<div class="dr-note">⚠️ <span class="dr-dn">' + rich(asTxt(r)) + '</span></div>');  // 2026-09-10：asTxt 防对象→[object Object]
        return s;
      });
      if (pred.pending_ai) h += '<div class="dr-note dr-tag">深度预测待本机 agent / 专家对话补全</div>';

      // ===== AI 综合推演 (ai_synthesis) =====
      // 本机 agent 产物：d.ai_synthesis 由 output/feed_review_latest.json 提供。
      // 2026-08-28 审计修复：此块原先由 6f1d2f5 手工补进成品页，模板与注入脚本皆无，
      // 导致每次 rebuild_html.py 重建后必然丢失（且前端 if(syn) 静默不显示）。
      // 现并入注入脚本，随「投喂复盘」一并幂等注入，重建后自动恢复。
      const syn = d.ai_synthesis;
      if (syn) {
        h += safe('AI 综合推演 · 核心结论', () => {
          if (!syn.verdict_headline) return '';
          return '<div style="margin:14px 0 4px;padding:10px 12px;border-left:3px solid #f0b429;background:rgba(240,180,41,.08);border-radius:8px;font-size:13.5px;line-height:1.7"><b style="color:#f0b429">⚑ AI 综合推演 · 核心结论</b><br>' + rich(syn.verdict_headline) + '</div>';
        });
        h += safe('AI 综合推演 · 结论先行', () => {
          const arr = asArr(syn.conclusion_first);
          if (!arr.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · 结论先行</div><ol style="margin:4px 0;padding-left:20px">';
          arr.forEach(c => s += '<li class="dr-note" style="list-style:inherit">' + rich(asTxt(c)) + '</li>');  // 2026-09-10：asTxt 防对象→[object Object]
          return s + '</ol>';
        });
        h += safe('AI 综合推演 · 主题共振', () => {
          const arr = asArr(syn.theme_resonance);
          if (!arr.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · 主题共振</div>';
          arr.forEach(t => {
            if (typeof t === 'string') { s += '<div class="dr-note" style="margin:4px 0">' + rich(t) + '</div>'; return; }
            const w = t.weight || '';
            const wc = w === '最强' ? 'var(--red)' : (w === '强' ? '#f0b429' : (w === '弱' ? '#94a3b8' : 'var(--text-muted)'));
            // 🔴 2026-09-02 治标：weight 为空时整段不渲染方括号（避免显示 `[]` 空牌）
            const wtBadge = w ? (' <span style="color:' + wc + '">[' + esc(w) + ']</span>') : '';
            // 🔴 2026-09-02 治标：related_stocks 空时不渲染空容器
            const rsBadge = (asArr(t.related_stocks).length) ? ('<div style="margin-top:4px">' + chips(t.related_stocks) + '</div>') : '';
            s += '<div style="margin:6px 0;padding:8px 10px;border:1px solid var(--border);border-radius:8px"><b>' + rich(t.theme || '') +
                 '</b>' + wtBadge + '<div class="dr-tag" style="margin-top:4px">' +
                 asArr(t.evidence).map(rich).join('<br>') + '</div>' + rsBadge + '</div>';
          });
          return s;
        });
        h += safe('AI 综合推演 · NVDA 产业链映射', () => {
          const cm = asArr(syn.nvda_chain_map)[0] || {};
          const txt = (typeof cm === 'string') ? cm : (cm.summary || '');
          const a = (typeof cm === 'object') ? asArr(cm.a_shares) : [];
          const u = (typeof cm === 'object') ? asArr(cm.us_mapping) : [];
          if (!txt && !a.length && !u.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · NVDA 产业链映射</div><div class="dr-note">' + rich(txt) + '</div>';
          s += '<div style="display:flex;gap:10px;flex-wrap:wrap"><div style="flex:1;min-width:200px"><b style="color:var(--red)">A股映射</b><div>' + chips(a) +
               '</div></div><div style="flex:1;min-width:200px"><b style="color:var(--green)">美股映射</b><div>' + chips(u) + '</div></div></div>';
          return s;
        });
        h += safe('AI 综合推演 · 持仓映射', () => {
          const hm = asArr(syn.holding_map)[0] || {};
          const note = (typeof hm === 'string') ? hm : (hm.note || '');
          const ta = (typeof hm === 'object') ? asArr(hm.theme_aligned) : [];
          const cau = (typeof hm === 'object') ? asArr(hm.caution) : [];
          const us = (typeof hm === 'object') ? asArr(hm.us) : [];
          if (!note && !ta.length && !cau.length && !us.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · 持仓映射</div><div class="dr-tag">' + rich(note) + '</div>';
          if (ta.length) s += '<div style="margin-top:4px"><b style="color:var(--red)">主题契合</b> ' + chips(ta) + '</div>';
          if (cau.length) s += '<div style="margin-top:4px"><b style="color:#f0b429">需谨慎</b> ' +
            cau.map(x => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:#f0b429;font-size:11px">' + esc(x) + '</span>').join('') + '</div>';
          if (us.length) s += '<div style="margin-top:4px"><b style="color:var(--green)">美股映射</b> ' + chips(us) + '</div>';
          return s;
        });
        h += safe('AI 综合推演 · T+1 事件雷达', () => {
          // 兼容任意日期后缀键名：t1_radar / t1_radar_0901 / t1_radar_0831 ...
          let radar = [];
          Object.keys(syn).forEach(k => { if (/^t1_radar/.test(k)) radar = radar.concat(asArr(syn[k])); });
          if (!radar.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · T+1 事件雷达</div>';
          radar.forEach(t => {
            if (typeof t === 'string') { s += '<div class="dr-note">· ' + rich(t) + '</div>'; return; }
            const o = (t && typeof t === 'object') ? t : {};
            // 2026-09-10：V3 产物元素为 {time,event,impact} 对象，结构化渲染（时间加粗 + 影响上色）；asTxt 兜底杜绝 [object Object]
            const txt = asTxt(o);
            const ic = String(o.impact || '').indexOf('高') >= 0 ? 'var(--red)' : '#f0b429';  // 高/中高 上色，与风险段口径一致
            s += '<div class="dr-note">· ' + (o.time ? '<b>' + esc(String(o.time)) + '</b> ' : '') + rich(txt)
              + (o.impact ? ' <span style="color:' + ic + ';font-weight:600">[' + esc(String(o.impact)) + ']</span>' : '') + '</div>';
          });
          return s;
        });
        h += safe('AI 综合推演 · 风险', () => {
          const arr = asArr(syn.risks);
          if (!arr.length) return '';
          let s = '<div class="dr-h">AI 综合推演 · 风险（概率 × 冲击）</div>';
          arr.forEach(r => {
            if (typeof r === 'string') { s += '<div class="dr-note">· ' + rich(r) + '</div>'; return; }
            const pc = (r.prob || '').indexOf('高') >= 0 ? 'var(--red)' : '#f0b429';  // 2026-09-04：「中高」也含高，与 V3 对齐
            s += '<div class="dr-note">· <span style="color:' + pc + ';font-weight:600">[' + esc(r.prob) + '×' + esc(r.impact || '—') + ']</span> ' + rich(r.desc) + '</div>';  // 2026-09-04：impact 缺失兜底显 —（9/3 曾整列丢失）
          });
          return s;
        });
        if (syn.disclaimer) h += '<div class="dr-tag" style="margin-top:8px">' + esc(syn.disclaimer) + '</div>';
      }
      el.innerHTML = h;
      // cross_analysis 为空时，用公开新闻池 × 板块资金流自动版补位
      if (caEmpty) drLoadCrossAnalysis();
    })
    .catch(err => { el.innerHTML = '<p class="dr-note">投喂复盘加载失败：' + err + '</p>'; });
}

// ===== 投喂弹框（modal）=====
/* ═══════ 投喂直投中转 · GitHub contents API（2026-09-03 新增） ═══════
   背景：页面是静态站（GitHub Pages）无后端，原「生成投喂文件」只下载到本地，
   需人工搬进 feed/inbox/ 才归档，且附件仅记录文件名（真实内容丢失）。
   现改为经 GitHub API 直接提交到 feed/inbox/{类别}/，附件原样上传（base64），
   本机 git pull + feed/feed_archive.py 即可自动归档。
   安全：Token 仅存本机 localStorage，绝不写入任何随仓库公开的文件。 */
var _FEED_REPO = 'XDTuang/golden-stock-observer';
var _FEED_BRANCH = 'main';
var _FEED_TK = 'drFeedGhToken';
function drFeedToken() { try { return localStorage.getItem(_FEED_TK) || ''; } catch (e) { return ''; } }
function drFeedB64Blob(file) {
  return new Promise(function (res, rej) {
    var r = new FileReader();
    r.onload = function () { res(String(r.result).split(',').pop()); };
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}
function drFeedB64Text(s) { return btoa(unescape(encodeURIComponent(s))); }
function drFeedPushFile(path, b64, msg) {
  var url = 'https://api.github.com/repos/' + _FEED_REPO + '/contents/' +
    path.split('/').map(encodeURIComponent).join('/');
  return fetch(url, {
    method: 'PUT',
    headers: {
      'Authorization': 'Bearer ' + drFeedToken(),
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message: msg, content: b64, branch: _FEED_BRANCH })
  }).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      if (!r.ok) throw new Error((j && j.message) ? j.message : ('HTTP ' + r.status));
      return j;
    });
  });
}
function drFeedModalInit() {
  if (document.getElementById('drFeedModal') || !document.getElementById('drFeedBtn')) return;
  const m = document.createElement('div');
  m.id = 'drFeedModal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(6,10,18,.78);z-index:9999;display:none;align-items:center;justify-content:center;padding:16px';
  m.innerHTML =
    '<div style="background:#161d2c;border:1px solid #2b3a5c;border-radius:14px;max-width:560px;width:100%;max-height:88vh;overflow:auto;padding:20px 22px;box-shadow:0 12px 48px rgba(0,0,0,.5)">' +
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
    '<b style="font-size:16px;color:#e8edf7">📥 投喂</b>' +
    '<button id="drFeedModalClose" style="background:none;border:none;color:#9aa7bd;font-size:20px;cursor:pointer;line-height:1">×</button></div>' +
    '<div style="font-size:12px;color:#9aa7bd;margin-bottom:12px"><b style="color:#d4af37">🚀 直投到中转</b>：提交到 feed/inbox/{类别}/（附件原样上传）→ 本机 git pull + feed_archive.py 自动归档。也可「生成投喂文件」下载后手动放入。</div>' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">' +
    '<div><div style="font-size:12px;color:#9aa7bd;margin:6px 0 4px">类别</div>' +
    '<select id="dfCat" style="width:100%;background:#0f1626;border:1px solid #2b3a5c;border-radius:8px;color:#e8edf7;padding:8px 10px;font-size:13px">' +
    '<option value="日常投喂">日常投喂</option><option value="专家投喂">专家投喂</option></select></div>' +
    '<div><div style="font-size:12px;color:#9aa7bd;margin:6px 0 4px">来源</div>' +
    '<select id="dfSrc" style="width:100%;background:#0f1626;border:1px solid #2b3a5c;border-radius:8px;color:#e8edf7;padding:8px 10px;font-size:13px">' +
    '<option>对话</option><option>研报</option><option>观点</option><option>文档</option><option>新闻</option><option>其他</option></select></div></div>' +
    '<div style="font-size:12px;color:#9aa7bd;margin:10px 0 4px">标题（简短描述）</div>' +
    '<input id="dfTitle" style="width:100%;background:#0f1626;border:1px solid #2b3a5c;border-radius:8px;color:#e8edf7;padding:8px 10px;font-size:13px" placeholder="示例：光模块景气 / 大盘异动">' +
    '<div style="font-size:12px;color:#9aa7bd;margin:10px 0 4px">内容</div>' +
    '<textarea id="dfText" style="width:100%;background:#0f1626;border:1px solid #2b3a5c;border-radius:8px;color:#e8edf7;padding:8px 10px;font-size:13px;min-height:72px;resize:vertical" placeholder="示例：8/26 盘中放量，疑似订单传闻…"></textarea>' +
    '<div style="font-size:12px;color:#9aa7bd;margin:10px 0 4px">附件（可选 · 直投时原样上传，不再只记文件名）</div>' +
    '<input id="dfFile" type="file" style="width:100%;color:#9aa7bd;font-size:12px">' +
    '<div style="margin-top:14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
    '<button id="dfPush" style="padding:8px 18px;border-radius:8px;border:1px solid #3b7f5a;background:#234f36;color:#e8edf7;font-size:13px;cursor:pointer">🚀 直投到中转</button>' +
    '<button id="dfGen" style="padding:8px 18px;border-radius:8px;border:1px solid #3b5a8f;background:#23324f;color:#e8edf7;font-size:13px;cursor:pointer">📤 生成投喂文件</button>' +
    '<span id="dfOut" style="font-size:12px;color:#9aa7bd"></span></div>' +
    '<div style="margin-top:10px"><a href="javascript:void(0)" id="dfTkToggle" style="font-size:12px;color:#9aa7bd;text-decoration:none">⚙️ GitHub Token 设置（直投必需）</a>' +
    '<div id="dfTkBox" style="display:none;margin-top:6px">' +
    '<input id="dfTk" type="password" placeholder="github_pat_…（仅存本机浏览器，不写入仓库）" style="width:100%;background:#0f1626;border:1px solid #2b3a5c;border-radius:8px;color:#e8edf7;padding:8px 10px;font-size:12px">' +
    '<div style="font-size:11px;color:#9aa7bd;margin-top:4px;line-height:1.6">需 fine-grained token：仓库选 <b>golden-stock-observer</b>，权限 <b>Contents: Read and write</b>。' +
    '<a href="https://github.com/settings/personal-access-tokens" target="_blank" rel="noopener" style="color:#d4af37">去生成</a></div>' +
    '<div style="margin-top:6px;display:flex;gap:8px;align-items:center">' +
    '<button id="dfTkSave" style="padding:4px 12px;border-radius:6px;border:1px solid #2b3a5c;background:#0f1626;color:#e8edf7;font-size:12px;cursor:pointer">保存</button>' +
    '<button id="dfTkClear" style="padding:4px 12px;border-radius:6px;border:1px solid #2b3a5c;background:#0f1626;color:#e8edf7;font-size:12px;cursor:pointer">清除</button>' +
    '<span id="dfTkState" style="font-size:12px;color:#9aa7bd"></span></div></div></div>' +
    '<div id="dfPreview" style="margin-top:10px;display:none;background:#0f1626;border:1px dashed #2b3a5c;border-radius:8px;padding:10px;font-size:12px">' +
    '<div id="dfPvName" style="font-family:Menlo,monospace;color:#d4af37;word-break:break-all;margin-bottom:6px"></div>' +
    '<pre id="dfPvBody" style="font-family:Menlo,monospace;color:#9aa7bd;white-space:pre-wrap;word-break:break-all;margin:0 0 8px;font-size:11px"></pre>' +
    '<button id="dfCopy" style="padding:4px 12px;border-radius:6px;border:1px solid #2b3a5c;background:#0f1626;color:#e8edf7;font-size:12px;cursor:pointer">📋 复制</button> ' +
    '<button id="dfDl" style="padding:4px 12px;border-radius:6px;border:1px solid #2b3a5c;background:#0f1626;color:#e8edf7;font-size:12px;cursor:pointer">⬇️ 下载 .txt</button>' +
    '<span style="font-size:11px;color:#9aa7bd;margin-left:8px">复制/下载后放入 feed_inbox/{类别}/ 即可自动归档</span></div></div>';
  document.body.appendChild(m);

  const open = () => { m.style.display = 'flex'; document.getElementById('dfTitle').focus(); };
  const close = () => { m.style.display = 'none'; };
  document.getElementById('drFeedBtn').onclick = open;
  document.getElementById('drFeedModalClose').onclick = close;
  m.addEventListener('click', e => { if (e.target === m) close(); });

  // ── Token 设置 ──
  const tkBox = document.getElementById('dfTkBox');
  const tkState = document.getElementById('dfTkState');
  const refreshTk = () => {
    const has = !!drFeedToken();
    tkState.textContent = has ? '✅ 已设置（存本机）' : '⚠️ 未设置';
    if (has) tkBox.style.display = 'block';
  };
  document.getElementById('dfTkToggle').onclick = () => {
    tkBox.style.display = (tkBox.style.display === 'none') ? 'block' : 'none';
  };
  document.getElementById('dfTkSave').onclick = () => {
    const v = (document.getElementById('dfTk').value || '').trim();
    if (!v) { tkState.textContent = '⚠️ 请输入 Token'; return; }
    localStorage.setItem(_FEED_TK, v);
    document.getElementById('dfTk').value = '';
    refreshTk();
  };
  document.getElementById('dfTkClear').onclick = () => {
    try { localStorage.removeItem(_FEED_TK); } catch (e) {}
    refreshTk();
  };
  refreshTk();

  const readForm = () => {
    const cat = document.getElementById('dfCat').value;
    const src = document.getElementById('dfSrc').value;
    const title = (document.getElementById('dfTitle').value || '未命名').replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40).replace(/^_+|_+$/g, '');
    const text = document.getElementById('dfText').value.trim();
    const file = document.getElementById('dfFile').files[0];
    const today = new Date().toISOString().slice(0, 10);
    return { cat, src, title, text, file, today };
  };

  // ── 直投到中转（feed/inbox/{类别}/） ──
  document.getElementById('dfPush').onclick = async function () {
    const out = document.getElementById('dfOut');
    const f = readForm();
    if (!drFeedToken()) {
      out.textContent = '⚠️ 请先设置 Token';
      tkBox.style.display = 'block';
      document.getElementById('dfTk').focus();
      return;
    }
    if (!f.text && !f.file) { out.textContent = '⚠️ 内容或附件至少填一项'; return; }
    const btn = this;
    btn.disabled = true;
    out.style.color = '#9aa7bd';
    out.textContent = '⏳ 提交中…';
    try {
      const tasks = [];
      if (f.file) {
        const ext = '.' + ((f.file.name.split('.').pop() || 'bin').toLowerCase());
        tasks.push({ name: f.today + '_' + f.src + '_' + f.title + ext, b64: await drFeedB64Blob(f.file), size: f.file.size });
      }
      if (f.text) {
        const tname = f.file
          ? (f.today + '_' + f.src + '_' + f.title + '_正文.txt')
          : (f.today + '_' + f.src + '_' + f.title + '.txt');
        tasks.push({ name: tname, b64: drFeedB64Text(f.text), size: f.text.length });
      }
      const done = [];
      for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        await drFeedPushFile('feed/inbox/' + f.cat + '/' + t.name, t.b64, 'feed: ' + t.name);
        done.push(t.name);
      }
      out.style.color = '#4ade80';
      out.innerHTML = '✅ 已投喂 ' + done.length + ' 个文件 → <b>feed/inbox/' + f.cat + '/</b><br>' +
        done.join('<br>') + '<br><span style="color:#9aa7bd">本机执行 git pull + feed_archive.py 即自动归档</span>';
    } catch (e) {
      out.style.color = '#f87171';
      out.textContent = '❌ 失败：' + e.message;
    }
    btn.disabled = false;
  };

  document.getElementById('dfGen').onclick = function () {
    const f = readForm();
    const ext = f.file ? ('.' + ((f.file.name.split('.').pop() || 'txt').toLowerCase())) : '.txt';
    const fname = f.today + '_' + f.src + '_' + f.title + ext;
    let body = '';
    if (f.text) body += f.text + '\n';
    if (f.file) body += '\n[附件] ' + f.file.name + '（' + Math.round(f.file.size / 1024) + ' KB）\n';
    if (!f.text && !f.file) body = '（空投喂）\n';
    document.getElementById('dfPvName').textContent = fname;
    document.getElementById('dfPvBody').textContent = body;
    document.getElementById('dfPreview').style.display = 'block';
    document.getElementById('dfOut').style.color = '#9aa7bd';
    document.getElementById('dfOut').textContent = '✅ 已生成（' + f.cat + '）';
    document.getElementById('dfCopy').dataset.body = fname + '\n' + body;
    document.getElementById('dfDl').dataset.body = fname + '\n' + body;
  };
  document.getElementById('dfCopy').onclick = function () {
    navigator.clipboard.writeText(this.dataset.body).then(() => {
      this.textContent = '✅ 已复制'; setTimeout(() => this.textContent = '📋 复制', 1200);
    });
  };
  document.getElementById('dfDl').onclick = function () {
    const blob = new Blob([this.dataset.body], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = this.dataset.body.split('\n')[0]; a.click();
  };
}














// 2026-09-10：analysis.html 自带 <style> 里的 body / :root / 裸标签规则，经 innerHTML 注入后会【全局生效】
//（曾把整站限宽 980px、并覆盖主站配色变量与字体）。此处把"越界规则"作用域化到 #drAnalysis：
//   body / html / *  → 丢弃；:root → #drAnalysis（变量局部化）；h2 / code / b,strong / br+br → 加 #drAnalysis 前缀；.dr-* 等类规则原样保留
function drScopeInjectedStyles(scopeEl) {
  if (!scopeEl) return;
  const S = '#drAnalysis';
  const fix = (rule) => {
    const sel = rule.selectorText; if (!sel) return false;
    const out = [];
    sel.split(',').map(s => s.trim()).forEach(p => {
      if (!p) return;
      if (p === 'body' || p === 'html' || p === '*') return;
      if (p === ':root') { out.push(S); return; }
      if (/^[a-z][a-z0-9]*(\+[a-z][a-z0-9]*)?$/i.test(p)) { out.push(S + ' ' + p); return; }
      out.push(p);
    });
    if (!out.length) return null;
    try { rule.selectorText = out.join(','); return true; } catch (e) { return false; }
  };
  Array.prototype.slice.call(scopeEl.querySelectorAll('style')).forEach(st => {
    const sheet = st.sheet; if (!sheet || !sheet.cssRules) return;
    try {
      for (let i = sheet.cssRules.length - 1; i >= 0; i--) {
        const r = sheet.cssRules[i];
        if (r.type === 1 && r.selectorText) { if (fix(r) === null) sheet.deleteRule(i); }
        else if (r.type === 4 && r.cssRules) {
          for (let j = r.cssRules.length - 1; j >= 0; j--) {
            const r2 = r.cssRules[j];
            if (r2.type === 1 && r2.selectorText && fix(r2) === null) r.deleteRule(j);
          }
        }
      }
    } catch (e) { /* 只读/跨域等场景忽略，退化为原有行为 */ }
  });
}

"""


def inject(path):
    with open(path, encoding="utf-8") as f:
        idx = f.read()
    changed = False

    # ① 内容区：挂在 drAnalysis 之后；已有卡片则升级标题栏（加投喂按钮）
    if TAB_MARK not in idx:
        anchor = 'id="drAnalysis"'
        if anchor in idx:
            # 找到 drAnalysis 卡片结束（下一个 </div> 之后加）——简单锚定：drAnalysis 卡片闭合
            p = idx.index(anchor)
            close = idx.index("</div>", p) + len("</div>")
            idx = idx[:close] + TAB_BLOCK + idx[close:]
            changed = True
            print(f"✅ {path}: 已插入投喂复盘卡片")
        else:
            print(f"⚠️ {path}: 未找到 drAnalysis 锚点，跳过卡片注入")
    elif 'id="drFeedBtn"' not in idx:
        # 已有卡片但无按钮（v1 → v2 升级）
        old_h = '<div class="dr-h">📥 投喂复盘（当日投喂 × 盘面信号）</div>'
        new_h = ('<div class="dr-h" style="display:flex;justify-content:space-between;align-items:center;gap:8px">\n'
                 '    <span>📥 投喂复盘（当日投喂 × 盘面信号）</span>\n'
                 '    <button id="drFeedBtn" style="font-size:12px;padding:4px 12px;border-radius:14px;border:1px solid var(--border);background:var(--bg-card);color:var(--text);cursor:pointer;white-space:nowrap">📥 投喂</button>\n'
                 '  </div>')
        if old_h in idx:
            idx = idx.replace(old_h, new_h, 1)
            changed = True
            print(f"✅ {path}: 已升级投喂复盘卡片标题栏（加投喂按钮）")
        else:
            print(f"⚠️ {path}: 未找到旧标题栏，请检查卡片结构")
    else:
        print(f"⏭️ {path}: 投喂复盘卡片已存在")

    # ② JS：函数定义挂在每日复盘 JS 块前
    #    🔴 2026-09-18 改为「比对后替换」= 可升级。
    #       原判据 `JS_MARK in idx and "feed v4" not in idx` 一旦文件里已有 v4 标记，
    #       后续对 JS_BLOCK 的任何改进都会被**静默跳过**（实测：改完富文本渲染后跑注入器
    #       输出「投喂复盘 JS 已存在」，页面仍显示字面 <b>，且不报错）。
    #       与 inject_daily_auto_blocks.py 同族，凡注入器一律按此范式。
    JS_END_ANCHOR = "// ===== 每日复盘 Tab ====="
    if JS_MARK in idx and JS_END_ANCHOR in idx:
        s0 = idx.index(JS_MARK)
        e0 = idx.index(JS_END_ANCHOR, s0)
        old_js = idx[s0:e0]
        new_js = JS_BLOCK + "\n"
        if old_js.strip() == new_js.strip():
            print(f"⏭️ {path}: 投喂复盘 JS 已是最新（{len(old_js)} 字符）")
        else:
            idx = idx[:s0] + new_js + idx[e0:]
            changed = True
            print(f"✅ {path}: 投喂复盘 JS 已升级（{len(old_js)} → {len(new_js)} 字符）")
    elif JS_END_ANCHOR in idx:
        idx = idx.replace(JS_END_ANCHOR, JS_BLOCK + JS_END_ANCHOR, 1)
        changed = True
        print(f"✅ {path}: 已插入投喂复盘 JS 函数")
    else:
        print(f"⚠️ {path}: 未找到每日复盘 JS 锚点，跳过 JS 注入")

    # ③ 初始化调用（独立于定义注入，幂等补插）
    call_anchor = "if (btn.dataset.tab === 'dailyreview') renderDailyReview();"
    call_line = "if (btn.dataset.tab === 'dailyreview') drLoadFeedReview();"
    if call_anchor in idx and call_line not in idx:
        idx = idx.replace(call_anchor,
            call_anchor + "\n    " + call_line, 1)
        changed = True
        print(f"✅ {path}: 已插入投喂复盘初始化调用")

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(idx)
        print(f"💾 {path}: 已写入")


if __name__ == "__main__":
    for t in TARGETS:
        p = os.path.join(BASE, t)
        if os.path.exists(p):
            inject(p)
        else:
            print(f"⚠️ 跳过（不存在）: {p}")
