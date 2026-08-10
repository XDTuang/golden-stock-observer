#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 gd_tracker_preview.html —— 兜宝金钻「金钻池跟踪」框架预览（不部署）。
把 output/golden_diamond_history.json + output/golden_diamond.json 嵌入到
独立 HTML 中，含：日期选择器（看某交易日明细）、总览汇总、金钻变动跟踪卡片。
"""
import os
import json

BASE = os.path.dirname(os.path.abspath(__file__))
history = json.load(open(os.path.join(BASE, "output", "golden_diamond_history.json"), encoding="utf-8"))
today = json.load(open(os.path.join(BASE, "output", "golden_diamond.json"), encoding="utf-8"))

APP = {
    "history": history,
    "today_overview": today.get("overview", {}),
    "today_data_date": today.get("data_date", ""),
}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>兜宝金钻 · 金钻池跟踪（预览）</title>
<style>
  :root{
    --bg:#0b0e14; --panel:#151a23; --panel2:#1b2230; --border:#232b38;
    --text:#e6edf3; --muted:#8b949e; --gold:#f5c518; --green:#3fb950;
    --orange:#f0883e; --added:#3fb950; --removed:#f85149; --kept:#58a6ff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    font-size:14px;line-height:1.5}
  .wrap{max-width:1080px;margin:0 auto;padding:24px 18px 60px}
  .topbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
    border-bottom:1px solid var(--border);padding-bottom:14px;margin-bottom:20px}
  .title{font-size:20px;font-weight:700;letter-spacing:.5px}
  .title .gem{color:var(--gold)}
  .badge-prev{font-size:11px;color:#0b0e14;background:var(--gold);padding:2px 8px;border-radius:10px;font-weight:700}
  .ctrl{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  select{background:var(--panel2);color:var(--text);border:1px solid var(--border);
    border-radius:8px;padding:7px 10px;font-size:13px}
  .hint{color:var(--muted);font-size:12px}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 22px}
  .stat{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
  .stat .k{color:var(--muted);font-size:12px}
  .stat .v{font-size:26px;font-weight:700;margin-top:4px}
  .stat.up .v{color:var(--gold)} .stat.buy .v{color:var(--green)} .stat.hz .v{color:var(--orange)}
  .stat .note{font-size:12px;margin-top:7px;font-weight:600;letter-spacing:.3px}
  .note.pos{color:var(--added)} .note.neg{color:var(--removed)} .note.flat{color:var(--muted)}
  .sec-title{font-size:15px;font-weight:700;margin:26px 0 12px;display:flex;align-items:center;gap:8px}
  .sec-title .bar{width:4px;height:16px;background:var(--gold);border-radius:2px}
  table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--border);
    border-radius:12px;overflow:hidden}
  th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--border);font-size:13px}
  th{color:var(--muted);font-weight:600;background:var(--panel2)}
  tr:last-child td{border-bottom:none}
  .pill{display:inline-block;padding:2px 9px;border-radius:10px;font-size:12px;font-weight:600}
  .p-up{background:rgba(245,197,24,.15);color:var(--gold)}
  .p-buy{background:rgba(63,185,80,.15);color:var(--green)}
  .p-hz{background:rgba(240,136,62,.15);color:var(--orange)}
  .ago{color:var(--muted);font-size:12px}
  .track{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .tcard{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
  .tcard h4{margin:0 0 4px;font-size:14px}
  .tcard .sub{color:var(--muted);font-size:12px;margin-bottom:10px}
  .grp{margin-top:10px}
  .grp .gh{font-size:12px;font-weight:700;margin-bottom:6px;display:flex;justify-content:space-between}
  .gh.add{color:var(--added)} .gh.rem{color:var(--removed)} .gh.keep{color:var(--kept)}
  .item{display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:8px;background:var(--panel2);
    margin-bottom:5px;font-size:13px}
  .mk{font-size:11px;font-weight:700;border-radius:6px;padding:1px 6px;flex:none}
  .mk.add{background:rgba(63,185,80,.18);color:var(--added)}
  .mk.rem{background:rgba(248,81,73,.18);color:var(--removed)}
  .mk.keep{background:rgba(88,166,255,.16);color:var(--kept)}
  .nm{font-weight:600}
  .cd{color:var(--muted);font-size:12px}
  .arrow{color:var(--kept);font-size:11px;margin-left:4px}
  .empty{color:var(--muted);font-size:12px;padding:6px 2px}
  @media(max-width:760px){.cards{grid-template-columns:repeat(2,1fr)}.track{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div class="title"><span class="gem">💎 兜宝金钻</span> · 金钻池跟踪 <span class="badge-prev">PREVIEW</span></div>
    <div class="ctrl">
      <span class="hint">选择交易日查看明细：</span>
      <select id="daySel"></select>
    </div>
  </div>

  <div id="overview"></div>

  <div class="sec-title"><span class="bar"></span>金钻变动跟踪（最新交易日 → 前1日 / 前2日）</div>
  <div id="tracking" class="track"></div>
</div>

<script>
const APP = /*__DATA__*/;
const H = APP.history;
const days = H.trading_days;
const snaps = H.snapshots;
const latest = days[days.length-1];

function pclass(p){
  if(p==="金钻起涨") return "p-up";
  if(p==="买入") return "p-buy";
  if(p.startsWith("红区黄柱连续")) return "p-hz";
  return "";
}
function pill(p){ return `<span class="pill ${pclass(p)}">${p}</span>`; }

function countByPrimary(snap){
  let c={up:0,buy:0,hz:0,total:0};
  for(const code in snap){
    const p=snap[code].primary; c.total++;
    if(p==="金钻起涨")c.up++;
    else if(p==="买入")c.buy++;
    else if(p.startsWith("红区黄柱连续"))c.hz++;
  }
  return c;
}

function renderOverview(date){
  const snap=snaps[date]||{};
  const c=countByPrimary(snap);
  const idx=days.indexOf(date);
  const prevDate = idx>0 ? days[idx-1] : null;
  const prevC = prevDate ? countByPrimary(snaps[prevDate]||{}) : null;
  function note(curr,prev,label){
    if(prev===null) return `<div class="note flat">无前一交易日</div>`;
    const d=curr-prev;
    if(d>0) return `<div class="note pos">较前一交易日 ▲ +${d} ${label}</div>`;
    if(d<0) return `<div class="note neg">较前一交易日 ▼ ${d} ${label}</div>`;
    return `<div class="note flat">较前一交易日 持平</div>`;
  }
  const codes=Object.keys(snap).sort((a,b)=>{
    const ra=rankOf(snap[a].primary), rb=rankOf(snap[b].primary);
    return rb-ra || a.localeCompare(b);
  });
  let rows = codes.length ? codes.map(code=>{
    const s=snap[code];
    return `<tr><td><b>${code}</b></td><td>${s.name}</td><td>${pill(s.primary)}</td>
      <td class="cd">${s.signal_date||"-"}</td><td class="ago">${s.days_ago==null?"":s.days_ago+"天前"}</td></tr>`;
  }).join("") : `<tr><td colspan="5" class="empty">当日无金钻信号命中</td></tr>`;

  document.getElementById("overview").innerHTML = `
    <div class="cards">
      <div class="stat"><div class="k">金钻池总数</div><div class="v">${c.total}</div>${note(c.total,prevC?prevC.total:null,"只")}</div>
      <div class="stat up"><div class="k">金钻起涨</div><div class="v">${c.up}</div>${note(c.up,prevC?prevC.up:null,"只")}</div>
      <div class="stat buy"><div class="k">买入</div><div class="v">${c.buy}</div>${note(c.buy,prevC?prevC.buy:null,"只")}</div>
      <div class="stat hz"><div class="k">红区黄柱连续</div><div class="v">${c.hz}</div>${note(c.hz,prevC?prevC.hz:null,"只")}</div>
    </div>
    <div class="sec-title"><span class="bar"></span>${date} · 金钻池明细（${c.total} 只）</div>
    <table><thead><tr><th>代码</th><th>名称</th><th>主信号</th><th>触发日</th><th>距今天数</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function rankOf(p){ return p==="金钻起涨"?3 : p==="买入"?2 : p.startsWith("红区黄柱连续")?1 : 0; }

function diffSets(a,b){
  const sa=new Set(Object.keys(a)), sb=new Set(Object.keys(b));
  const added=[...sa].filter(x=>!sb.has(x));
  const removed=[...sb].filter(x=>!sa.has(x));
  const retained=[...sa].filter(x=>sb.has(x));
  const changed=retained.filter(x=>a[x].primary!==b[x].primary);
  return {added,removed,retained,changed};
}

function itemHtml(snap,code,mk){
  const s=snap[code];
  return `<div class="item"><span class="mk ${mk}">${mk==="add"?"新增":mk==="rem"?"消除":"留存"}</span>
    <span class="nm">${s.name}</span><span class="cd">${code}</span>${pill(s.primary)}</div>`;
}
function changedHtml(a,b,code){
  const s=a[code];
  return `<div class="item"><span class="mk keep">留存</span>
    <span class="nm">${s.name}</span><span class="cd">${code}</span>
    ${pill(b[code].primary)}<span class="arrow">→</span>${pill(s.primary)}</div>`;
}

function renderCompare(d0,d1){
  if(!d1) return `<div class="tcard"><h4>前1交易日对比</h4><div class="empty">历史数据不足</div></div>`;
  const cmp=diffSets(snaps[d0],snaps[d1]);
  const c0=countByPrimary(snaps[d0]).total, c1=countByPrimary(snaps[d1]).total;
  return `<div class="tcard">
    <h4>${d0} ↔ ${d1}</h4>
    <div class="sub">最新池 ${c0} 只 · 前1日池 ${c1} 只 · 净增 ${c0-c1>=0?"+":""}${c0-c1}</div>
    <div class="grp"><div class="gh add"><span>＋ 新增（${cmp.added.length}）</span></div>
      ${cmp.added.length?cmp.added.map(c=>itemHtml(snaps[d0],c,"add")).join(""):'<div class="empty">无</div>'}</div>
    <div class="grp"><div class="gh rem"><span>－ 消除（${cmp.removed.length}）</span></div>
      ${cmp.removed.length?cmp.removed.map(c=>itemHtml(snaps[d1],c,"rem")).join(""):'<div class="empty">无</div>'}</div>
    <div class="grp"><div class="gh keep"><span>● 留存（${cmp.retained.length}）｜其中信号变更 ${cmp.changed.length}</span></div>
      ${cmp.retained.length?cmp.retained.map(c=>cmp.changed.includes(c)?changedHtml(snaps[d0],snaps[d1],c):itemHtml(snaps[d0],c,"keep")).join(""):'<div class="empty">无</div>'}</div>
  </div>`;
}

function renderTracking(){
  const d0=latest, d1=days[days.length-2], d2=days[days.length-3];
  document.getElementById("tracking").innerHTML = renderCompare(d0,d1)+renderCompare(d0,d2);
}

// 初始化
const sel=document.getElementById("daySel");
days.slice().reverse().forEach(d=>{
  const o=document.createElement("option"); o.value=d; o.textContent=d+(d===latest?"（最新）":""); sel.appendChild(o);
});
sel.value=latest;
sel.addEventListener("change",e=>renderOverview(e.target.value));
renderOverview(latest);
renderTracking();
</script>
</body>
</html>
"""

html = TEMPLATE.replace("/*__DATA__*/", json.dumps(APP, ensure_ascii=False))
out = os.path.join(BASE, "gd_tracker_preview.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✓ 预览已生成: {out} ({os.path.getsize(out)} 字节)")
