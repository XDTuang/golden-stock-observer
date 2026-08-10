#!/usr/bin/env python3
# 构建「兜宝金钻」独立版站点
# 策略：从 index_template.html（最新源码）直接生成，物理移除其他 tab 与 navBar，
# 仅保留 #tab-diamond 这一整块内容；隐藏原登录层；金钻 tab 强制可见；ILOVEDB 密码门。
# 不内联 signals.json（金钻仅运行时 fetch ./output/golden_diamond.json），产物更小。
import os, re, shutil, glob

SRC = "index_template.html"
OUTDIR = "diamond_site"
OUT = os.path.join(OUTDIR, "index.html")

os.makedirs(OUTDIR, exist_ok=True)
html = open(SRC, encoding="utf-8").read()

# ── 0. 数据占位符：独立版无需内联主信号数据 ──
html = html.replace(
    "// DATA_PLACEHOLDER",
    "// 独立版：兜宝金钻不内联主信号数据，仅运行时 fetch ./output/golden_diamond.json",
)

# ── 0.5 独立版默认深色主题（仅覆盖独立站默认值，尊重用户已保存的偏好）──
html = html.replace(
    "localStorage.getItem('theme') || 'light'",
    "localStorage.getItem('theme') || 'dark'",
)

# ── 1. CSS：隐藏原登录层 + 强制金钻 tab 可见 + 独立登录门样式 ──
CSS = """
/* ═══ 独立版：兜宝金钻（仅保留此块）═══ */
#loginOverlay{display:none !important;}
#tab-diamond{display:block !important;}
.dalendar-wrap, .nav, #navBar{display:none !important;}
.diamond-gate{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(1200px 700px at 50% -10%, #1a2236 0%, #0a0c12 60%);}
.diamond-gate.hidden{display:none;}
.dg-card{background:linear-gradient(180deg,rgba(26,32,48,.72),rgba(19,23,34,.72));border:1px solid rgba(230,181,60,.28);border-radius:18px;
  padding:32px 36px;width:330px;text-align:center;backdrop-filter:blur(14px);box-shadow:0 20px 60px rgba(0,0,0,.55),0 0 40px rgba(230,181,60,.08);}
.dg-logo{font-size:26px;font-weight:800;color:var(--gold,#e6b53c);letter-spacing:1px;}
.dg-sub{color:#9aa1b8;font-size:13px;margin:6px 0 22px;}
.dg-pw{display:flex;gap:8px;}
.dg-pw input{flex:1;padding:11px 13px;border-radius:10px;border:1px solid rgba(255,255,255,.14);
  background:rgba(10,12,18,.4);color:#e8ebf2;font-size:15px;outline:none;transition:border-color .15s,box-shadow .15s;}
.dg-pw input:focus{border-color:var(--gold,#e6b53c);box-shadow:0 0 0 3px rgba(230,181,60,.16);}
.dg-btn{padding:11px 20px;border:none;border-radius:10px;background:var(--gold,#e6b53c);color:#1a1205;
  font-weight:700;font-size:15px;cursor:pointer;box-shadow:0 4px 14px rgba(230,181,60,.30);transition:filter .15s,transform .15s;}
.dg-btn:hover{filter:brightness(1.06);}
.dg-btn:active{transform:translateY(1px);}
.dg-err{color:#ff7b7b;font-size:12px;min-height:16px;margin-top:10px;}
.dg-hint{color:#656c82;font-size:11px;margin-top:14px;}
"""
assert "</head>" in html, "找不到 </head>"
html = html.replace("</head>", "<style>\n" + CSS + "\n</style>\n</head>", 1)

# ── 2. 物理移除其他 tab-content 与 navBar（仅保留 #tab-diamond）──
def remove_tab(html, tab_id):
    m = re.search(r'<div class="tab-content[^"]*" id="tab-%s">' % re.escape(tab_id), html)
    if not m:
        return html
    start = m.start()
    nxt = html.find('<div class="tab-content', m.end())
    footer = html.find('<div class="footer">', start)
    candidates = [x for x in (nxt, footer) if x != -1]
    end = min(candidates)
    return html[:start] + html[end:]

for tid in ["overview", "short", "long", "emascan", "pool", "signalstock", "calendar"]:
    html = remove_tab(html, tid)

# 移除 navBar
if '<nav' in html:
    ns = html.index('<nav')
    ne = html.index('</nav>', ns) + len('</nav>')
    html = html[:ns] + html[ne:]

# 断言：仅剩金钻 tab
assert 'id="tab-diamond"' in html, "金钻 tab 丢失"
assert 'id="tab-overview"' not in html, "overview tab 未移除"
assert 'id="tab-calendar"' not in html, "calendar tab 未移除"

# ── 2.5 移除机游共振渲染调用（红线：副站不喂机游共振数据，物理移除 initPage 中的 lhb 渲染块）──
_lhb_block = re.search(r'  // ── 机游共振日历 \+ 当月TOP.*?catch\(e\) \{ console\.warn\(\'\[兜金\] 机游共振渲染失败[^\n]*\);\s*\}\n', html, re.S)
if _lhb_block:
    html = html[:_lhb_block.start()] + html[_lhb_block.end():]
assert 'await loadLhbData()' not in html, "机游共振调用块未移除"

# ── 3. HTML：独立登录门（在 <body> 之后注入）──
GATE = """
<!-- ═══════════ 独立版登录门（密码 ILOVEDB）═══════════ -->
<div class="diamond-gate" id="diamondGate">
  <div class="dg-card">
    <div class="dg-logo">\U0001F48E 兜宝金钻</div>
    <div class="dg-sub">独立版 · 请输入访问密码</div>
    <div class="dg-pw">
      <input type="password" id="dgPw" placeholder="访问密码" onkeydown="if(event.key==='Enter')dgGo()">
      <button class="dg-btn" onclick="dgGo()">进入</button>
    </div>
    <div class="dg-err" id="dgErr"></div>
    <div class="dg-hint">密码请联系管理员获取</div>
  </div>
</div>
"""
assert "<body>" in html, "找不到 <body>"
html = html.replace("<body>", "<body>\n" + GATE, 1)

# ── 4. JS：ILOVEDB 鉴权 + 金钻数据仅在授权后加载 ──
JS = """
<script>
(function(){
  var KEY='diamond_auth';
  function dgShow(){var g=document.getElementById('diamondGate');if(g)g.classList.remove('hidden');var p=document.getElementById('dgPw');if(p)p.focus();}
  function dgHide(){var g=document.getElementById('diamondGate');if(g)g.classList.add('hidden');}
  window.dgGo=function(){
    var p=document.getElementById('dgPw'); if(!p)return;
    var v=(p.value||'').trim();
    if(v==='ILOVEDB'||v==='LYY'){
      try{localStorage.setItem(KEY,'1');}catch(e){}
      dgHide();
      if(window.loadDiamondTab) loadDiamondTab();
    }else{
      var e=document.getElementById('dgErr'); if(e)e.textContent='请联系管理员更新密码';
      p.value='';
    }
  };
  document.addEventListener('DOMContentLoaded',function(){
    var auth=null; try{auth=localStorage.getItem(KEY);}catch(e){}
    if(auth){ dgHide(); if(window.loadDiamondTab) loadDiamondTab(); }
    else { dgShow(); }
  });
})();
</script>
"""
assert "</body>" in html, "找不到 </body>"
html = html.replace("</body>", JS + "\n</body>", 1)

# ── 5. 移除原 initPage 调用（避免加载/渲染其他模块），金钻专用初始化已由上方 JS 处理 ──
html = html.replace(
    "document.addEventListener('DOMContentLoaded', initPage);",
    "/* 独立版：不调用 initPage，金钻数据由登录门授权后加载 */",
)
# 主模板末尾为裸调用 initPage();（rebuild_html 路径需要），独立版必须剥离，
# 否则 SIGNALS_DATA 未定义 → initPage 直接把 body 覆盖为“暂无信号数据”错误页。
html = html.replace(
    "initPage();",
    "/* 独立版：不调用 initPage，金钻数据由登录门授权后加载 */",
)

open(OUT, "w", encoding="utf-8").write(html)
print("写入:", OUT, "| 字节:", len(html))

# ── 6. 复制金钻所需数据（运行时 fetch）──
# 独立站钻石 tab 运行时加载 golden_pool 分片（含 K线，点开个股渲染主图/副图/四量图/判定明细）。
# 排除巨量缓存（kline_all.json / gate_data.json 等沙盒数据），避免独立站被撑爆。
NEEDED = ["golden_diamond_history.json", "sector_golden_diamond_history.json"]
for _fn in glob.glob("output/golden_pool_*.json"):
    NEEDED.append(os.path.basename(_fn))
dst = os.path.join(OUTDIR, "output")
os.makedirs(dst, exist_ok=True)
# 注意：不做目录整体删除（shutil.rmtree 在非交互/launchd 环境会触发批量删除安全拦截导致构建失败）。
# 改为仅清理 NEEDED 清单内旧文件 + 覆盖复制：残留的其他文件为历史数据，前端不引用，无害。
for _old in glob.glob(os.path.join(dst, "*")):
    if os.path.basename(_old) in NEEDED:
        try: os.remove(_old)
        except OSError: pass
for fn in NEEDED:
    sp = os.path.join("output", fn)
    if os.path.exists(sp):
        shutil.copy(sp, os.path.join(dst, fn))
        print("复制:", fn, round(os.path.getsize(sp) / 1024, 1), "KB")
# 注意：副站(diaut_site)不承载机游共振模块——按用户要求机游共振数据仅更新主站，
# 不复制 lh_calendar.json 到副站（副站机游共振 tab 代码存在但经 CSS 折叠隐藏，无需数据）。
# 若日后需在副站启用机游共振，再恢复此复制并在此显式同步数据。

open(os.path.join(OUTDIR, ".nojekyll"), "w").close()
print("完成。diamond_site/ 结构:")
for root, dirs, files in os.walk(OUTDIR):
    for f in files:
        fp = os.path.join(root, f)
        print("  ", os.path.relpath(fp, OUTDIR), round(os.path.getsize(fp)/1024, 1), "KB")
