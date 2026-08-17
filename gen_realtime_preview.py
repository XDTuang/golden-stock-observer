#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜金观测 · 实时盯盘 — 预览页生成器
==================================
读取 fetch_realtime.py 产出的 realtime.json，内联注入 HTML 模板，
生成自包含预览页（双击即可打开，无需服务器）。
同时产出可注入主站 index.html 的 tab 片段（realtime_tab_snippet.html）。

用法:
  python gen_realtime_preview.py [--json realtime/realtime.json] [--out realtime_preview.html]
"""

import argparse
import json
import os

# ═══════════════════════════════════════════════════════════
# HTML 模板（浅色主题，CSS 变量与主站 index.html 一致）
# 数据注入为 window.REALTIME_DATA；注入主站后同一份 JS 可改为 fetch('realtime.json')
# ═══════════════════════════════════════════════════════════
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>兜金观测 · 实时盯盘（预览版）</title>
<style>
  :root{
    --bg-root:#f5f6fa; --bg-surface:#ffffff; --bg-card:#ffffff;
    --bg-card-hover:#f8f9fc; --bg-subtle:#f0f2f5;
    --border:#e8ecf1; --border-light:#f0f2f5; --border-focus:#4f6ef7;
    --text:#1a1d2e; --text-secondary:#5a6178; --text-muted:#9ca3b8; --text-inverse:#fff;
    --accent:#4f6ef7; --accent-light:#6b85fa; --accent-bg:rgba(79,110,247,.06);
    --red:#e53e3e; --red-bg:rgba(229,62,62,.06);
    --green:#22a861; --green-bg:rgba(34,168,97,.06);
    --orange:#ed8936; --orange-bg:rgba(237,137,54,.08);
    --gold:#d69e2e; --gold-bg:rgba(214,158,46,.08);
    --purple:#805ad5; --purple-bg:rgba(128,90,213,.07);
    --blue:#3182ce; --blue-bg:rgba(49,130,206,.07);
    --cyan:#00a3c4; --cyan-bg:rgba(0,163,196,.07);
    --shadow-card:0 1px 3px rgba(0,0,0,.04),0 1px 2px rgba(0,0,0,.03);
    --shadow-hover:0 4px 16px rgba(0,0,0,.06),0 2px 4px rgba(0,0,0,.03);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
    background:var(--bg-root);color:var(--text);line-height:1.65;padding:20px 14px}
  .wrap{max-width:1180px;margin:0 auto}
  h1{font-size:22px;font-weight:700}
  .sub{color:var(--text-secondary);font-size:13px}
  .muted{color:var(--text-muted);font-size:12px}

  /* 状态条 */
  .statusbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;
    background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;
    padding:14px 18px;margin:14px 0 18px;box-shadow:var(--shadow-card)}
  .badge{display:inline-flex;align-items:center;gap:4px;padding:3px 12px;border-radius:20px;
    font-size:12.5px;font-weight:600;white-space:nowrap}
  .b-trading{background:var(--red-bg);color:var(--red);border:1px solid rgba(229,62,62,.25)}
  .b-lunch{background:var(--orange-bg);color:var(--orange);border:1px solid rgba(237,137,54,.25)}
  .b-closed{background:var(--bg-subtle);color:var(--text-secondary);border:1px solid var(--border)}
  .b-holiday{background:var(--bg-subtle);color:var(--text-muted);border:1px solid var(--border)}
  .b-accent{background:var(--accent-bg);color:var(--accent);border:1px solid rgba(79,110,247,.25)}
  .dot{width:7px;height:7px;border-radius:50%;display:inline-block}
  .dot-red{background:var(--red)} .dot-orange{background:var(--orange)}
  .dot-gray{background:var(--text-muted)} .dot-blue{background:var(--accent)}

  /* 卡片 */
  .card{background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;
    padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow-card)}
  .card-title{display:flex;align-items:center;gap:8px;font-size:15.5px;font-weight:700;margin-bottom:12px}
  .lv{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:22px;
    border-radius:6px;font-size:11.5px;font-weight:700;color:#fff;padding:0 6px}
  .lv-l0{background:#5a6178} .lv-l1{background:var(--accent)} .lv-l2{background:var(--purple)}
  .lv-l3{background:var(--cyan)} .lv-l4{background:var(--green)} .lv-l5{background:var(--red)}
  .card-sub{color:var(--text-muted);font-size:12px;margin-left:auto}

  /* L1 情绪 */
  .l1-grid{display:grid;grid-template-columns:200px 1fr;gap:20px;align-items:center}
  .score-wrap{text-align:center;padding:14px;border-radius:12px;background:var(--bg-subtle)}
  .score-num{font-size:52px;font-weight:800;line-height:1}
  .score-lbl{font-size:12.5px;color:var(--text-secondary);margin-top:4px}
  .dims{display:flex;flex-direction:column;gap:9px}
  .dim-row{display:grid;grid-template-columns:86px 1fr 42px;align-items:center;gap:10px;font-size:12.5px}
  .dim-name{color:var(--text-secondary);font-weight:600}
  .bar{height:9px;border-radius:5px;background:var(--bg-subtle);overflow:hidden}
  .bar-fill{height:100%;border-radius:5px;background:var(--accent)}
  .dim-val{text-align:right;font-weight:700;color:var(--text)}
  .state-tag{margin-top:10px;display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:14px}
  .state-note{margin-top:6px;font-size:12.5px;color:var(--text-secondary)}

  /* L2 */
  .pos-range{display:flex;align-items:baseline;gap:6px}
  .pos-num{font-size:40px;font-weight:800;color:var(--purple)}
  .pos-unit{font-size:15px;color:var(--text-secondary);font-weight:600}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
  .chip{background:var(--bg-subtle);border:1px solid var(--border);border-radius:6px;
    padding:3px 9px;font-size:12px;color:var(--text-secondary)}

  /* L3 板块 */
  .sector-row{display:grid;grid-template-columns:110px 1fr 90px 90px;align-items:center;
    gap:10px;padding:6px 0;font-size:13px;border-bottom:1px dashed var(--border-light)}
  .sector-row:last-child{border-bottom:none}
  .s-name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .s-bar{height:14px;border-radius:4px;background:var(--bg-subtle);overflow:hidden}
  .s-fill{height:100%;border-radius:4px}
  .pos{color:var(--red);font-weight:700;text-align:right}
  .neg{color:var(--green);font-weight:700;text-align:right}
  .resonance{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
  .r-chip{background:var(--accent-bg);color:var(--accent);border:1px solid rgba(79,110,247,.2);
    border-radius:6px;padding:3px 9px;font-size:12px}
  .r-chip.warn{background:var(--orange-bg);color:var(--orange);border-color:rgba(237,137,54,.25)}

  /* L4 候选 */
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:var(--bg-subtle);text-align:left;padding:8px 10px;font-weight:600;
    color:var(--text-secondary);font-size:12px;white-space:nowrap}
  td{padding:8px 10px;border-bottom:1px solid var(--border-light);white-space:nowrap}
  tr:hover td{background:var(--bg-card-hover)}
  .t-type{font-size:11.5px;border-radius:4px;padding:1px 7px;font-weight:600}
  .t-dixi{background:var(--green-bg);color:var(--green)}
  .t-zhongji{background:var(--blue-bg);color:var(--blue)}

  /* L5 */
  .alert{border:1px solid;border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:13px;
    display:flex;gap:10px;align-items:flex-start}
  .alert .tag{font-weight:700;white-space:nowrap;flex-shrink:0}
  .a-red{background:var(--red-bg);border-color:rgba(229,62,62,.25);color:var(--red)}
  .a-yellow{background:var(--gold-bg);border-color:rgba(214,158,46,.28);color:#92600a}
  .a-green{background:var(--green-bg);border-color:rgba(34,168,97,.25);color:var(--green)}

  /* ETF */
  .etf-row{display:grid;grid-template-columns:130px 1fr 90px;gap:10px;align-items:center;
    padding:5px 0;font-size:12.5px;border-bottom:1px dashed var(--border-light)}
  .etf-row:last-child{border-bottom:none}

  /* 算法说明 */
  details{background:var(--bg-subtle);border:1px solid var(--border);border-radius:10px;
    padding:12px 16px;margin-top:14px}
  summary{cursor:pointer;font-weight:700;font-size:13.5px;color:var(--text)}
  details[open] summary{margin-bottom:10px}
  details p,details li{font-size:12.5px;color:var(--text-secondary);margin:4px 0}
  details ul{padding-left:20px}

  .empty{color:var(--text-muted);font-size:13px;padding:14px;text-align:center;
    background:var(--bg-subtle);border-radius:10px}
  .foot{color:var(--text-muted);font-size:11.5px;padding:12px 0 24px;text-align:center}
  @media(max-width:720px){
    .l1-grid{grid-template-columns:1fr}
    .sector-row{grid-template-columns:90px 1fr 70px}
    .sector-row .s-extra{display:none}
    .statusbar{gap:8px}
  }
</style>
</head>
<body>
<div class="wrap">

  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <h1>👁 实时盯盘</h1>
    <span class="sub">五层决策架构 · 盘中每 30 分钟自动刷新（GitHub Actions 驱动）</span>
  </div>

  <!-- 数据状态条 -->
  <div class="statusbar">
    <span id="stTime" class="badge b-accent">--</span>
    <span id="stStatus" class="badge b-closed">--</span>
    <span id="stAlgo" class="badge b-closed">算法 v--</span>
    <span class="muted" style="margin-left:auto" id="stNext">--</span>
  </div>

  <!-- L1 市场状态机 -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l1">L1</span>市场状态机<span class="card-sub">情绪分 = 30%涨跌比 + 25%涨停 + 20%指数强度 + 25%资金</span></div>
    <div class="l1-grid">
      <div class="score-wrap">
        <div class="score-num" id="scoreNum">--</div>
        <div class="score-lbl" id="scoreLbl">情绪分 / 100</div>
        <div class="state-tag" id="stateTag">--</div>
      </div>
      <div>
        <div class="dims" id="dims"></div>
        <div class="state-note" id="stateNote"></div>
      </div>
    </div>
  </div>

  <!-- L2 仓位引擎 -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l2">L2</span>仓位引擎<span class="card-sub">状态 → 仓位区间（固定映射）</span></div>
    <div class="pos-range"><span class="pos-num" id="posLo">--</span><span class="pos-unit">% ~</span><span class="pos-num" id="posHi">--</span><span class="pos-unit">%</span></div>
    <div class="sub" id="posNote"></div>
    <div class="chips" id="posChips"></div>
  </div>

  <!-- L3 主线与板块 -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l3">L3</span>主线与板块<span class="card-sub">行业主力净流入 TOP（东财）</span></div>
    <div id="mainline" class="sub" style="margin-bottom:10px"></div>
    <div id="sectors"></div>
    <div class="resonance" id="resonance"></div>
  </div>

  <!-- L4 候选标的 -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l4">L4</span>候选标的 · 观察池<span class="card-sub">四道关：非ST / 涨幅&lt;8% / 主力净流入&gt;1亿 / 成交&gt;5亿</span></div>
    <div style="overflow-x:auto">
    <table id="candTable">
      <thead><tr><th>名称</th><th>代码</th><th>涨跌幅</th><th>主力净流入</th><th>量比</th><th>换手</th><th>成交额</th><th>类型</th></tr></thead>
      <tbody></tbody>
    </table>
    </div>
    <div class="sub muted" id="tradeNote" style="margin-top:8px"></div>
  </div>

  <!-- L5 风险雷达 -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l5">L5</span>风险雷达<span class="card-sub">固定 4 类信号：情绪过热 / 资金背离 / 板块集中 / 普涨过热</span></div>
    <div id="alerts"></div>
  </div>

  <!-- ETF 资金（辅助维度） -->
  <div class="card">
    <div class="card-title"><span class="lv lv-l0">ETF</span>宽基 ETF 资金流<span class="card-sub">新浪 · 当日净流入</span></div>
    <div id="etf"></div>
  </div>

  <!-- 算法规格说明（固定依据） - 线上版隐藏，仅在预览页展开 -->

  <!-- 底部免责声明（线上去掉） -->
</div>

<script>
(function(){
window.REALTIME_DATA = __REALTIME_JSON__;

function fmtYi(v){ if(v==null) return '--'; return (v>0?'+':'')+v.toFixed(2)+'亿'; }
function fmtPct(v){ if(v==null) return '--'; return (v>0?'+':'')+v.toFixed(2)+'%'; }
function cls(v){ return v>0?'pos':'neg'; }
function scoreColor(s){
  if(s>=85) return 'var(--red)';
  if(s>=70) return 'var(--orange)';
  if(s>=55) return 'var(--accent)';
  if(s>=40) return 'var(--gold)';
  return 'var(--green)';
}
function render(){
  const D = window.REALTIME_DATA;
  if(!D || !D.meta){ document.querySelector('.wrap').innerHTML='<div class="empty">暂无数据：请先运行 fetch_realtime.py</div>'; return; }
  const m = D.meta;
  const stMap = {
    trading:{txt:'交易中 · 实时', c:'b-trading', d:'dot-red'},
    lunch:{txt:'午休', c:'b-lunch', d:'dot-orange'},
    closed:{txt:'已收盘', c:'b-closed', d:'dot-gray'},
    holiday:{txt:'非交易日', c:'b-holiday', d:'dot-gray'},
    preopen:{txt:'未开盘', c:'b-closed', d:'dot-gray'},
  };
  const st = stMap[m.market_status]||stMap.closed;
  document.getElementById('stTime').textContent = '更新 '+(m.updated_at||'--');
  const elSt = document.getElementById('stStatus');
  elSt.className = 'badge '+st.c;
  elSt.innerHTML = '<span class="dot '+st.d+'"></span>'+st.txt;
  document.getElementById('stAlgo').textContent = '算法 v'+(m.algorithm||'--');
  document.getElementById('stNext').textContent = m.next_hint||'';

  // L1
  const s = D.L1 && D.L1.sentiment, state = D.L1 && D.L1.state;
  if(s){
    const num = document.getElementById('scoreNum');
    num.textContent = s.score;
    num.style.color = scoreColor(s.score);
    document.getElementById('scoreLbl').textContent = '情绪分 / 100';
    document.getElementById('stateTag').innerHTML = '<span class="badge b-accent">'+(state?state.label:'--')+'</span>';
    const dims = [['涨跌比 S1', s.S1], ['涨停 S2', s.S2], ['指数强度 S3', s.S3], ['资金 S4', s.S4]];
    document.getElementById('dims').innerHTML = dims.map(d=>
      '<div class="dim-row"><span class="dim-name">'+d[0]+'</span>'+
      '<div class="bar"><div class="bar-fill" style="width:'+d[1]+'%;background:'+scoreColor(d[1])+'"></div></div>'+
      '<span class="dim-val">'+d[1]+'</span></div>').join('');
    if(state) document.getElementById('stateNote').textContent = state.note;
  }

  // L2
  const l2 = D.L2;
  if(l2 && l2.range){
    document.getElementById('posLo').textContent = l2.range[0];
    document.getElementById('posHi').textContent = l2.range[1];
    document.getElementById('posNote').textContent = l2.note||'';
    document.getElementById('posChips').innerHTML = (l2.rules||[]).map(r=>'<span class="chip">'+r+'</span>').join('');
  }

  // L3
  const l3 = D.L3;
  if(l3){
    document.getElementById('mainline').textContent = '主线：'+(l3.mainline||'--');
    const sec = l3.sectors||[];
    if(sec.length){
      const mx = Math.max(...sec.map(x=>Math.abs(x.net_yi||0)), 1);
      document.getElementById('sectors').innerHTML = sec.map(x=>{
        const w = Math.round(Math.abs(x.net_yi)/mx*100);
        const col = x.net_yi>=0?'var(--red)':'var(--green)';
        return '<div class="sector-row"><span class="s-name">'+x.name+'</span>'+
          '<div class="s-bar"><div class="s-fill" style="width:'+w+'%;background:'+col+'"></div></div>'+
          '<span class="'+cls(x.net_yi)+'">'+fmtYi(x.net_yi)+'</span>'+
          '<span class="'+cls(x.pct)+' s-extra">'+fmtPct(x.pct)+'</span></div>';
      }).join('');
    }
    document.getElementById('resonance').innerHTML = (l3.resonance||[]).map(r=>
      '<span class="r-chip'+(r.indexOf('⚠')>=0?' warn':'')+'">'+r+'</span>').join('');
  }

  // L4
  const l4 = D.L4;
  const tb = document.querySelector('#candTable tbody');
  const cands = (l4 && l4.candidates)||[];
  if(cands.length){
    tb.innerHTML = cands.map(c=>
      '<tr><td><b>'+c.name+'</b></td><td class="muted">'+c.code+'</td>'+
      '<td class="'+cls(c.zdf)+'">'+fmtPct(c.zdf)+'</td>'+
      '<td class="'+cls(c.zljlr)+'">'+fmtYi(c.zljlr)+'</td>'+
      '<td>'+c.lb+'</td><td>'+c.hsl+'%</td><td>'+c.turnover_yi+'亿</td>'+
      '<td><span class="t-type '+(c.type=='低吸候选'?'t-dixi':'t-zhongji')+'">'+c.type+'</span></td></tr>').join('');
  } else {
    tb.innerHTML = '<tr><td colspan="8" class="empty">今日无候选（可能处于过热/弱势状态或数据未更新）</td></tr>';
  }
  document.getElementById('tradeNote').textContent = (l4 && l4.trade_note)||'';

  // L5
  const l5 = D.L5;
  if(l5 && l5.alerts){
    const lvlMap = {red:['a-red','风险'], yellow:['a-yellow','预警'], green:['a-green','正常']};
    document.getElementById('alerts').innerHTML = l5.alerts.map(a=>{
      const lm = lvlMap[a.level]||lvlMap.yellow;
      return '<div class="alert '+lm[0]+'"><span class="tag">'+lm[1]+' · '+a.type+'</span><span>'+a.msg+'</span></div>';
    }).join('');
  }

  // ETF
  const etf = D.ETF && D.ETF.flows;
  const etfEl = document.getElementById('etf');
  if(etf && etf.length){
    const mx = Math.max(...etf.map(x=>Math.abs(x.net_yi||0)),1);
    etfEl.innerHTML = etf.map(x=>{
      const w = Math.round(Math.abs(x.net_yi)/mx*100);
      return '<div class="etf-row"><span><b>'+x.code+'</b></span>'+
        '<div class="bar"><div class="bar-fill" style="width:'+w+'%;background:'+(x.net_yi>=0?'var(--red)':'var(--green)')+'"></div></div>'+
        '<span class="'+cls(x.net_yi)+'">'+fmtYi(x.net_yi)+'</span></div>';
    }).join('');
  } else etfEl.innerHTML = '<div class="empty">ETF 数据不可用</div>';
}
function initRT(){
  if (window.REALTIME_DATA && window.REALTIME_DATA.meta) { render(); return; }
  fetch('realtime.json').then(r=>r.json()).then(d=>{ window.REALTIME_DATA=d; render(); })
    .catch(e=>{ const w=document.getElementById('tab-realtime')||document.querySelector('.wrap');
      if(w) w.innerHTML='<div class="empty" style="padding:24px;text-align:center;color:var(--text-muted)">实时数据加载失败：'+e.message+'（请确认 realtime.json 已部署）</div>'; });
}
initRT();
})();
</script>
</body>
</html>
"""


def scope_css(css: str, scope: str) -> str:
    """把 CSS 选择器限制在 #tab-realtime 作用域内，避免与主站全局样式冲突。
    跳过 :root/*/body 全局规则（主站已有），@media 行保留但内部选择器同样加前缀。"""
    out = []
    for ln in css.splitlines():
        s = ln.strip()
        if not s or s.startswith("/*") or s.startswith("@media"):
            out.append(ln)
            continue
        if s.startswith(":root") or s.startswith("*") or s.startswith("body") or s.startswith("--"):
            continue
        if "{" in s:
            out.append(scope + " " + ln)
        else:
            out.append(ln)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="realtime/realtime.json")
    ap.add_argument("--out", default="realtime_preview.html")
    ap.add_argument("--snippet", default="realtime_tab_snippet.html")
    args = ap.parse_args()

    if not os.path.exists(args.json):
        print(f"❌ 找不到 {args.json}，请先运行 fetch_realtime.py")
        sys.exit(1)
    data = json.load(open(args.json, encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False)

    html = TEMPLATE.replace("__REALTIME_JSON__", payload)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 预览页已生成: {args.out}（数据内联，可双击打开）")

    # 产出可注入主站的 tab 片段：CSS 限定作用域 + 页面数据用 fetch('realtime.json')
    css = TEMPLATE.split("<style>")[1].split("</style>")[0]
    body_html = '<div class="wrap">' + TEMPLATE.split('<div class="wrap">')[1].split("<script>")[0]
    js = TEMPLATE.split("<script>")[1].split("</script>")[0]
    snippet = "<style>\n" + scope_css(css, "#tab-realtime") + "\n</style>\n" \
              + body_html + "\n<script>\n" + js + "\n</script>"
    with open(args.snippet, "w", encoding="utf-8") as f:
        f.write(snippet)
    print(f"✅ 主站 tab 片段已生成: {args.snippet}（作用域 #tab-realtime + fetch 模式）")


if __name__ == "__main__":
    main()
