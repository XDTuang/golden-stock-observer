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
function drLoadFeedReview() {
  drFeedModalInit();
  const el = document.getElementById('drFeedReviewBody');
  if (!el) return;
  fetch('output/feed_review_latest.json')
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(d => {
      const pred = d.prediction || {};
      const biasCls = pred.bias === '偏多' ? 'dr-up' : (pred.bias === '偏空' ? 'dr-dn' : '');
      let h = '<div class="dr-note">数据日期 <b>' + (d.data_date || '—') + '</b> · 投喂 ' +
              (d.feed_count || 0) + ' 条 · 来源 ' + (d.source === 'cloud' ? '云端 08:15' : '本地 19:30') + '</div>';
      h += '<div class="dr-note"><b>后市预判：<span class="' + biasCls + '">' + (pred.bias || '—') +
           '</span></b>（score ' + (pred.bias_score ?? '—') + '）</div>';
      (pred.reasons || []).forEach(r => h += '<div class="dr-note">· ' + r + '</div>');
      const feeds = d.feeds || [];
      if (feeds.length) {
        h += '<div class="dr-h">当日投喂</div><table class="dr-tbl"><thead><tr><th>类别</th><th>来源</th><th>标题</th><th>关键词</th></tr></thead><tbody>';
        feeds.forEach(f => {
          h += '<tr><td>' + f.category + '</td><td>' + f.source + '</td><td>' + f.title + '</td><td class="dr-tag">' +
               (f.keywords || []).slice(0, 4).join(' / ') + '</td></tr>';
        });
        h += '</tbody></table>';
      }
      const ca = d.cross_analysis || [];
      if (ca.length) {
        h += '<div class="dr-h">机制 × 语料交叉验证</div><table class="dr-tbl"><thead><tr><th>投喂</th><th>匹配信号标的</th><th>判定</th></tr></thead><tbody>';
        ca.forEach(c => {
          const cls = c.verdict === '共振' ? 'dr-up' : (c.verdict === '背离' ? 'dr-dn' : 'dr-tag');
          h += '<tr><td>' + c.feed + '</td><td>' + ((c.related_stocks || []).join('、') || '—') +
               '</td><td class="' + cls + '">' + c.verdict + '</td></tr>';
        });
        h += '</tbody></table>';
      }
      const t1 = pred.t1_focus || [];
      if (t1.length) {
        h += '<div class="dr-h">T+1 关注</div>';
        t1.forEach(t => h += '<div class="dr-note">· ' + t + '</div>');
      }
      const risks = pred.risks || [];
      if (risks.length) {
        h += '<div class="dr-h">风险提示</div>';
        risks.forEach(r => h += '<div class="dr-note">⚠️ <span class="dr-dn">' + r.desc + '</span></div>');
      }
      if (pred.pending_ai) h += '<div class="dr-note dr-tag">深度预测待本机 agent / 专家对话补全</div>';
      // ===== AI 综合推演 (ai_synthesis) =====
      // 本机 agent 产物：d.ai_synthesis 由 output/feed_review_latest.json 提供。
      // 2026-08-28 审计修复：此块原先由 6f1d2f5 手工补进成品页，模板与注入脚本皆无，
      // 导致每次 rebuild_html.py 重建后必然丢失（且前端 if(syn) 静默不显示）。
      // 现并入注入脚本，随「投喂复盘」一并幂等注入，重建后自动恢复。
      const syn = d.ai_synthesis;
      if (syn) {
        const esc = s => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        h += '<div style="margin:14px 0 4px;padding:10px 12px;border-left:3px solid #f0b429;background:rgba(240,180,41,.08);border-radius:8px;font-size:13.5px;line-height:1.7"><b style="color:#f0b429">⚑ AI 综合推演 · 核心结论</b><br>' + esc(syn.verdict_headline || '') + '</div>';
        if (syn.conclusion_first && syn.conclusion_first.length) {
          h += '<div class="dr-h">AI 综合推演 · 结论先行</div><ol style="margin:4px 0;padding-left:20px">';
          syn.conclusion_first.forEach(c => h += '<li class="dr-note" style="list-style:inherit">' + esc(c) + '</li>');
          h += '</ol>';
        }
        if (syn.theme_resonance && syn.theme_resonance.length) {
          h += '<div class="dr-h">AI 综合推演 · 主题共振</div>';
          syn.theme_resonance.forEach(t => {
            const w = t.weight || '';
            const wc = w === '最强' ? 'var(--red)' : (w === '强' ? '#f0b429' : 'var(--text-muted)');
            const chips = (t.related_stocks || []).map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('');
            h += '<div style="margin:6px 0;padding:8px 10px;border:1px solid var(--border);border-radius:8px"><b>' + esc(t.theme) + '</b> <span style="color:' + wc + '">[' + esc(w) + ']</span><div class="dr-tag" style="margin-top:4px">' + (t.evidence || []).map(esc).join('<br>') + '</div><div style="margin-top:4px">' + chips + '</div></div>';
          });
        }
        const cm = syn.nvda_chain_map || {};
        if (cm.summary || (cm.a_shares && cm.a_shares.length) || (cm.us_mapping && cm.us_mapping.length)) {
          h += '<div class="dr-h">AI 综合推演 · NVDA 产业链映射</div>';
          h += '<div class="dr-note">' + esc(cm.summary || '') + '</div>';
          h += '<div style="display:flex;gap:10px;flex-wrap:wrap"><div style="flex:1;min-width:200px"><b style="color:var(--red)">A股映射</b><div>' + ((cm.a_shares || []).map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('')) + '</div></div><div style="flex:1;min-width:200px"><b style="color:var(--green)">美股映射</b><div>' + ((cm.us_mapping || []).map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('')) + '</div></div></div>';
        }
        const hm = syn.holding_map || {};
        if (hm.note || (hm.theme_aligned && hm.theme_aligned.length) || (hm.caution && hm.caution.length) || (hm.us && hm.us.length)) {
          h += '<div class="dr-h">AI 综合推演 · 持仓映射</div>';
          h += '<div class="dr-tag">' + esc(hm.note || '') + '</div>';
          if (hm.theme_aligned && hm.theme_aligned.length) h += '<div style="margin-top:4px"><b style="color:var(--red)">主题契合</b> ' + hm.theme_aligned.map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('') + '</div>';
          if (hm.caution && hm.caution.length) h += '<div style="margin-top:4px"><b style="color:#f0b429">需谨慎</b> ' + hm.caution.map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:#f0b429;font-size:11px">' + esc(s) + '</span>').join('') + '</div>';
          if (hm.us && hm.us.length) h += '<div style="margin-top:4px"><b style="color:var(--green)">美股映射</b> ' + hm.us.map(s => '<span style="display:inline-block;margin:2px 4px 2px 0;padding:1px 7px;border:1px solid var(--border);border-radius:6px;color:var(--blue);font-size:11px">' + esc(s) + '</span>').join('') + '</div>';
        }
        // 兼容历史字段名 t1_radar_0827（8/27 产物）与通用名 t1_radar
        const radar = syn.t1_radar_0827 || syn.t1_radar || [];
        if (radar.length) {
          h += '<div class="dr-h">AI 综合推演 · T+1 事件雷达</div>';
          radar.forEach(t => h += '<div class="dr-note">· ' + esc(t) + '</div>');
        }
        if (syn.risks && syn.risks.length) {
          h += '<div class="dr-h">AI 综合推演 · 风险（概率 × 冲击）</div>';
          syn.risks.forEach(r => {
            const pc = r.prob === '高' ? 'var(--red)' : '#f0b429';
            h += '<div class="dr-note">· <span style="color:' + pc + ';font-weight:600">[' + esc(r.prob) + '×' + esc(r.impact) + ']</span> ' + esc(r.desc) + '</div>';
          });
        }
        if (syn.disclaimer) h += '<div class="dr-tag" style="margin-top:8px">' + esc(syn.disclaimer) + '</div>';
      }
      el.innerHTML = h;
    })
    .catch(err => { el.innerHTML = '<p class="dr-note">投喂复盘加载失败：' + err + '</p>'; });
}

// ===== 投喂弹框（modal）=====
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
    '<div style="font-size:12px;color:#9aa7bd;margin-bottom:12px">生成规范投喂文件 → 复制/下载 → 拖入 feed_inbox 自动归档（也可在专家对话直接说「投喂：…」）</div>' +
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
    '<div style="font-size:12px;color:#9aa7bd;margin:10px 0 4px">附件（可选）</div>' +
    '<input id="dfFile" type="file" style="width:100%;color:#9aa7bd;font-size:12px">' +
    '<div style="margin-top:14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
    '<button id="dfGen" style="padding:8px 18px;border-radius:8px;border:1px solid #3b5a8f;background:#23324f;color:#e8edf7;font-size:13px;cursor:pointer">📤 生成投喂文件</button>' +
    '<span id="dfOut" style="font-size:12px;color:#9aa7bd"></span></div>' +
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

  document.getElementById('dfGen').onclick = function () {
    const cat = document.getElementById('dfCat').value;
    const src = document.getElementById('dfSrc').value;
    const title = (document.getElementById('dfTitle').value || '未命名').replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40).replace(/^_+|_+$/g, '');
    const text = document.getElementById('dfText').value.trim();
    const file = document.getElementById('dfFile').files[0];
    const today = new Date().toISOString().slice(0, 10);
    const ext = file ? ('.' + ((file.name.split('.').pop() || 'txt').toLowerCase())) : '.txt';
    const fname = today + '_' + src + '_' + title + ext;
    let body = '';
    if (text) body += text + '\n';
    if (file) body += '\n[附件] ' + file.name + '（' + Math.round(file.size / 1024) + ' KB）\n';
    if (!text && !file) body = '（空投喂）\n';
    document.getElementById('dfPvName').textContent = fname;
    document.getElementById('dfPvBody').textContent = body;
    document.getElementById('dfPreview').style.display = 'block';
    document.getElementById('dfOut').textContent = '✅ 已生成（' + cat + '）';
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

    # ② JS：函数定义挂在每日复盘 JS 块前；v3 标记缺失时整体替换（修复历史坏版）
    if JS_MARK in idx and "feed v4" not in idx:
        s = idx.index(JS_MARK)
        e = idx.index("// ===== 每日复盘 Tab =====", s)
        idx = idx[:s] + JS_BLOCK + "\n" + idx[e:]
        changed = True
        print(f"✅ {path}: 已升级投喂复盘 JS（v4：内置 ai_synthesis 渲染）")
    elif JS_MARK not in idx:
        js_anchor = "// ===== 每日复盘 Tab ====="
        if js_anchor in idx:
            idx = idx.replace(js_anchor, JS_BLOCK + js_anchor, 1)
            changed = True
            print(f"✅ {path}: 已插入投喂复盘 JS 函数")
        else:
            print(f"⚠️ {path}: 未找到每日复盘 JS 锚点，跳过 JS 注入")
    else:
        print(f"⏭️ {path}: 投喂复盘 JS 已存在")

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
