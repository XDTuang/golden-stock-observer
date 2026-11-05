#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-05 盘前版 analysis.html · Part C：7.1 / 7.4 / 8 / 9 + 2 段港股补涨跌幅
顺序铁律：7.1 整体重写后 → 再跑 build_k3_conclusions.py（上色）→ 再跑 build_sector_tech.py（重注 7.1b）
"""
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
SRC = BASE / "data/daily_review/analysis.html"
html = SRC.read_text(encoding="utf-8-sig")
orig_len = len(html)


def sub(old, new, expect=1, tag=""):
    global html
    c = html.count(old)
    assert c == expect, f"[{tag}] 出现 {c} 次，期望 {expect}: {old[:70]}"
    html = html.replace(old, new)


def repl_block(start_anchor, end_anchor, new, tag=""):
    global html
    c = html.count(start_anchor)
    assert c == 1, f"[{tag}] 起始 count={c}: {start_anchor[:50]}"
    i = html.find(start_anchor)
    j = html.find(end_anchor, i + len(start_anchor))
    assert j > i, f"[{tag}] 结束锚点缺失: {end_anchor[:50]}"
    html = html[:i] + new + html[j:]


# ═══════════ 2 段港股补涨跌幅 ═══════════
sub('<tr><td>恒生指数</td><td><b>23,919.50</b></td>',
    '<tr><td>恒生指数</td><td><b>23,919.50</b>（<span class="dk-up">+1.67%</span>）</td>', tag="hk-hsi")
sub('<tr><td>恒生科技</td><td><b>3,936.02</b></td>',
    '<tr><td>恒生科技</td><td><b>3,936.02</b>（<span class="dk-up">+1.77%</span>）</td>', tag="hk-hstech")

# ═══════════ 7.1 K3 产业信号验证 ═══════════
i71 = html.find(">7.1 · K3 产业信号验证")
assert i71 > 0, "7.1 未找到"
start71 = html.rfind('<div class="dr-h" data-version="close-2215"', 0, i71)
assert start71 > 0, "7.1 段头未找到"
end71 = html.find("<!-- ═══ 7.1b SECTOR-TECH-BEGIN", i71)
assert end71 > start71, "7.1 段尾未找到"

SEC71 = """<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">7.1 · K3 产业信号验证（<b class="dk-up">A股 11/04 完整收盘</b> + <b class="dk-risk">美股 11/04 完整收盘</b> · 8 条 · 结论按「验证结果」分级：<span class="k3c k3c-go">成立</span> / <span class="k3c k3c-cond">有条件</span> / <span class="k3c k3c-risk">风险</span> / <span class="k3c k3c-verify">待验</span>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><div class="k3c-legend">结论色标：<i class="l-go">可执行·相对占优</i><i class="l-cond">有条件·待确认</i><i class="l-risk">风险·回避</i><i class="l-verify">待验证变量·方法论</i></div>
  <table class="dr-tbl"><thead><tr><th>主题</th><th>验证</th><th>内容</th></tr></thead><tbody>
    <tr><td><b>存储 / 半导体链</b></td><td>外部锚是否延续</td><td><div class="dr-wrap">11/03 存储四线 4/4（均值 +3.01%）→ 11/04 四线 <b class="dk-risk">0/4（均值 -6.70%）</b>，SK하이닉스 11/05 早盘再 <b class="dk-risk">-7.09%</b>。<span class="k3c k3c-risk"><b>结论：外部锚由正转负且在同幅量级上反转，昨日「外部映射兑现」的结论作废；今日 A股 存储链不具独立行情条件。</b></span></div></td></tr>
    <tr><td><b>电子板块资金</b></td><td>+312.63 亿是否延续</td><td><div class="dr-wrap">11/04 电子 <b class="dk-up">+312.63 亿</b>占全市场净流入 62%；但外部链条隔夜被重定价，且 <code>flow_date</code> 尚停在 11-04（今日资金未知）。<span class="k3c k3c-cond"><b>结论：资金级反转的事实成立，但其「可持续性」尚未获得任何一日验证 —— 需今日电子不再大幅净流出（&gt; -120 亿）方可保留。</b></span></div></td></tr>
    <tr><td><b>通信 / 光模块</b></td><td>资金转正 vs 外部崩塌</td><td><div class="dr-wrap">通信 11/04 <b class="dk-up">+75.86 亿</b>（前一日 -103.02 亿），<code>news_count 23</code> 已破 16 门槛升<b>共振 A</b>；但 LITE <b class="dk-risk">-7.85%</b> / COHR <span class="dk-dn">-5.98%</span>（财报超预期仍跌）。<span class="k3c k3c-cond"><b>结论：内部资金确认、外部价格否决，属「有条件」—— 今日若光模块低开高走则逻辑修复，低开低走则共振 A 明日降级。</b></span></div></td></tr>
    <tr><td><b>算力 / 数据中心</b></td><td>政策改写折现率</td><td><div class="dr-wrap">民主党的数据中心审批 / 并网 / 征地摩擦 ⇒ 第三方测算 IRR 由 12%~14% 降至 9%~11%、接电推迟 12–24 个月；美股 MRVL <b class="dk-risk">-7.08%</b>、NVDA <span class="dk-dn">-3.17%</span>。<span class="k3c k3c-risk"><b>结论：这是本轮最强的负向信号 —— 杀的是估值分母而非订单，且已由韩股亚洲时段二次确认。</b></span></div></td></tr>
    <tr><td><b class="dk-risk">情绪过热</b></td><td>极值后的均值回归</td><td><div class="dr-wrap">情绪 <b>98</b>（S1 100 / S2 94 / S3 100 / S4 100）、涨停 <b>113</b>、涨跌比 <b>4.99</b>、规则档 <code>overheat [30,50]</code>。<span class="k3c k3c-risk"><b>结论：极值叠加外部断裂，今日「高开」窗口已关闭；追高禁令继续生效，且本档主动下调仓位至 15%–25%。</b></span></div></td></tr>
    <tr><td><b class="dk-risk">技术档位</b></td><td>资金分位 vs 连续性</td><td><div class="dr-wrap"><b>L4 = 0 / L3 = 0 连续第四版</b>，趋势 向上 2 / 反弹 7 / 下跌 22（<code>kline_lag = 0</code>）。<span class="k3c k3c-risk"><b>结论：11/04 的 +507 亿与 +2.16% 未换来任何技术升级 —— 规则要求「连续 ≥2 日」，单日流入不被承认，故今日无技术面承接。</b></span></div></td></tr>
    <tr><td><b>防御 / 红利端</b></td><td>跷跷板能否反向</td><td><div class="dr-wrap">11/04 流出前六全为防御（食品饮料 -21.60 / 银行 -15.33 / 交运 -11.67 / 石油石化 -11.53 / 公用 -10.51 / 煤炭 -6.85）；今日语料端 银行 / 石油石化 / 非银 升<b>背离 B</b>（热而资金负）。<span class="k3c k3c-verify"><b>结论：待验 —— 若今日科技杀跌而防御端放量承接，则「跷跷板反向」成立；若两端同跌，则为「两头空」的真空段。</b></span></div></td></tr>
    <tr><td><b>新能源 / 电力设备</b></td><td>避弹坑属性</td><td><div class="dr-wrap">电力设备 11/04 <b class="dk-up">+45.56 亿</b>（暗线 C）、机械设备 +44.86 亿、<code>news_count 12</code> 未达 16 门槛 ⇒ 资金已入、语料未炒；兼具沪深 300 与创业板权重属性。<span class="k3c k3c-go"><b>结论：本档唯一「资金正 + 未被炒作 + 不受 AI 硬件拖累」的组合，可作为今日唯一的相对占优方向（仍只做回踩、不做追高）。</b></span></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-main">7.1 段的总结</b>：<b class="dk-risk">8 条里 4 条判「风险」、2 条「有条件」、1 条「成立（但仅限相对占优）」、1 条「待验」</b>。核心变化不是「A股 变差」，而是<b>「昨日给出的多头证据，隔夜被原产地作废」</b>：存储 4/4 → 0/4、光模块 2/3 → 0/3、指数层面的利多（道 +3.03%）与链条层面的利空（MRVL -7.08%）同时存在。<b class="dk-caution">⇒ 在这种「指数与结构背离」的环境里，唯一可靠的做法是<b>按链条而非按指数操作</b>：减 AI 硬件、留暗线 C、等回踩。</b>
  </div>
</div>

"""
html = html[:start71] + SEC71 + html[end71:]

# ═══════════ 7.4 操作预案 ═══════════
i74 = html.find("<!-- 7.4 操作预案 -->")
assert i74 > 0
end74 = html.find("<!-- 8 数据自检 -->", i74)
assert end74 > i74
SEC74 = """<!-- 7.4 操作预案 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">7.4 · 操作预案（盘前版 08:40 · agent 详细版 · 面向 <b>11/05（周四）</b> · 依据 A股 11/04 完整收盘 + <b class="dk-risk">美股 11/04 完整收盘</b> + 日韩 11/05 早盘 + <b>本版四象限</b> 7 / 3 / 8 / 13）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>维度</th><th>本档预案（11/05）</th><th>触发条件 / 边界</th></tr></thead><tbody>
    <tr><td><b class="dk-main">大势预判</b></td><td><div class="dr-wrap"><b class="dk-risk">低开、结构分化、指数由权重对冲</b>：上证预计低开 -0.9%~-1.6%（<b>3,627–3,653</b>），日内中枢 <b>3,640–3,670</b>；科创 50 / 创业板跌幅显著大于上证（昨日 +9.92% / +6.40% 的 β 是对称的）。<b class="dk-caution">不预设「低开即反弹」，按「低开 → 二次探底 → 观察承接」三段走</b></div></td><td><div class="dr-wrap">成立前提：<b>电子开盘跌幅 &gt; 2.5%</b>。若上证低开不足 -0.5%（&gt;3,668），说明隔夜映射未充分传导，则改为「平开偏弱 + 内部杀跌」，仓位不变</div></td></tr>
    <tr><td><b class="dk-caution">主线策略</b></td><td><div class="dr-wrap"><b class="dk-caution">只做「暗线 C + 防御承接」两条线，不做 AI 硬件的超跌反弹</b>：<br>① <b>电力设备 / 机械设备</b>（暗线 C · 资金 +45.56 / +44.86 亿 · 语料未炒）—— <b>回踩不破 MA5 才允许轻仓介入</b>；<br>② <b>银行 / 食品饮料</b>（防御承接 · 象限仍为「双冷 / 背离」，即无资金证据）—— <b class="dk-caution">只作为「指数不崩」的观察指标，不作为买入标的</b>；<br>③ <b>交运</b>（油价 -4.23%~-8% 的最干净利多）—— 观察是否出现「低开高走」，若成立可视为避险资金的第一个落点</div></td><td><div class="dr-wrap">仓位：<b class="dk-risk">15%–25%</b>（低于 overheat 档 [30,50] 下限，理由见 0 段）。<b>单日新增不超过 5%</b>；<b class="dk-risk">不接低开第一笔、不做超跌反弹第一根阳线</b></div></td></tr>
    <tr><td><b class="dk-risk">回避清单</b></td><td><div class="dr-wrap"><b class="dk-risk">① 存储 / HBM 概念</b>（美股 0/4、韩股 -7.09% 二次定价）；<b>② 光模块 / CPO</b>（0/3，且 COHR 已示范「财报超预期仍跌」）；<b>③ PCB / 铜连接</b>（数据中心 capex 下修的最直接受体，昨日最热今最危险）；<b>④ 算力租赁 / ASIC 概念小市值</b>（MRVL -7.08%，弹性端先杀）；<b>⑤ 石油石化 / 煤炭 / 油服</b>（油价 -8%，且资金列已为负）；<b>⑥ 任何一字板 / 连板追高</b>（情绪 98 + L2 追高禁令）</div></td><td><div class="dr-wrap">解除条件：<b>电子单日资金转正 &gt;100 亿</b> 或 <b>存储链外部连续两日收红</b>，二者之一出现前不清除</div></td></tr>
    <tr><td><b>盘中哨兵</b></td><td><div class="dr-wrap">09:45 / 10:30 / 11:15 / 14:00 四次检查：<b>① 上证是否守住 3,640</b>；<b>② 跌停家数是否 &gt;25</b>；<b>③ 电子资金是否 &lt; -120 亿</b>；<b>④ 成交是否 &lt; 1.7 万亿</b>（缩量下跌 = 抛压衰减；放量下跌 = 出逃）</div></td><td><div class="dr-wrap"><b class="dk-risk">①②③ 任一触发 ⇒ 仓位降至 10% 以下</b>；④ 缩量 + 指数站稳 ⇒ 可维持 15%–25% 不加不减</div></td></tr>
    <tr><td><b>证伪与升级</b></td><td><div class="dr-wrap"><b class="dk-caution">本档判断（中性偏空）被证伪 = 上证半日内收复 3,686.17 且电子资金转正</b>；<b class="dk-risk">升级为「偏空」= 上证失守 3,608.10（11/03 收盘）或跌停 &gt;40 家</b></div></td><td><div class="dr-wrap">收盘后 22:15 档按实际读数结算本档三条判断（方向 / 开盘 / 仓位），并记录命中与未命中</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-caution">持仓类提示（合规声明）</b>：本页涉及的任何个股均为<b>「其他专家持股参考（非本人）」</b>，只给客观技术读数与板块归属，<b class="dk-risk">不提供任何加减仓建议</b>。今日对电子 / 存储 / 光模块 / PCB 的「回避」表述是<b>板块级风险描述</b>，不是对个股的操作指令。
  </div>
</div>

"""
html = html[:i74] + SEC74 + html[end74:]

# ═══════════ 8 数据自检 ═══════════
i8 = html.find("<!-- 8 数据自检 -->")
end8 = html.find("<!-- 9 来源 -->", i8)
assert i8 > 0 and end8 > i8
SEC8 = """<!-- 8 数据自检 -->
<div class="dr-h" data-version="preopen-0840">8 · 数据自检区（JS 自动扫描 · 各源日期一致性 · <b class="dk-up">本版已核：A股 2026-11-04 完整收盘〔结算价〕· 美股 <span class="dk-up">2026-11-04</span> 完整收盘〔结算价〕/ <code>us_kline.latest = 2026-11-04</code>（23/23）· 日韩 2026-11-05 早盘实时 · 商品 11/05 早间 · 美债 11/03</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div id="drSelfCheck" style="margin-top:8px">
    <div style="font-size:12.5px;color:var(--text-muted)">自检扫描中…</div>
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.6;margin-top:8px">
    <b class="dk-main">一、本版口径声明（源头逐项点名）</b><br>
    · <b>A股</b>：<code>market.json date = 2026-11-04</code>（<code>updated_at = 2026-11-05 08:47:22 CST</code> · <code>preopen_partial = true</code>）· <code>realtime.json</code>（<code>updated_at = 2026-11-04 22:16:02</code> · <code>market_status = closed</code> · 收盘终值）· <code>output/sector_flow.json</code>（<code>last_success = 2026-11-04</code> · <code>stale_days = 0</code> · <code>checked_at = 2026-11-05T08:48:14</code> · 31/31）<br>
    · <b>美股</b>：<code>us_kline</code> <b>23/23</b> 最新日 = <b>2026-11-04</b>（<code>quotes.us_*</code> 同步）—— <b>完整收盘，非盘中快照</b>；<code>COHR</code> 财报为<b>盘后</b>事件，已单独标注；费半 / 苹果 / 微软不在本机抓取范围<br>
    · <b>日韩</b>：<code>market.json.asia</code>（<code>date = 2026-11-05</code> · 日经 62,502.89 <span class="dk-up">+0.51%</span> / KOSPI 5,495.14 <span class="dk-dn">-3.32%</span> · <b>早盘实时 · 非收盘</b>）· <code>kr_stocks</code>（<code>fetched_at = 2026-11-05 08:47</code> · NAVER 无延迟源 · SK하이닉스 <span class="dk-dn">-7.09%</span> / 삼성 <span class="dk-dn">-5.28%</span>）· 港股 11/04 收盘（恒生 23,919.50 <span class="dk-up">+1.67%</span> / 恒生科技 3,936.02 <span class="dk-up">+1.77%</span>）<br>
    · <b>商品 / 美债</b>：<code>market.json.comm</code>（金 4,039.86 / COMEX 4,051.61 / WTI 92.02 / 布伦特 98.87 = <b>2026-11-05</b>；人民币 6.718 / 碳酸锂 86,460 = 2026-11-04；<b>10Y 4.95% / 30Y 5.32% = 2026-11-03</b>，本机长期缺口、滞后 1 日）<br>
    · <b>宏观</b>：<code>output/daily_macro_latest.json</code>（<code>date = 2026-11-05</code> · <code>generated_at = 2026-11-05 08:47</code> · <code>us.calendar.as_of = 2026-11-05 08:47</code>；龄期按今日现算）<br>
    · <b>推演 / 板块</b>：<code>output/cross_analysis.json</code>（<code>date = 2026-11-04</code> · <code>data_date = 2026-11-04</code> · <code>flow_date = 2026-11-04</code> · <code>news_window = 11/04~11/05</code> · 2 日窗 · 语料 <b>587 条</b> · 门槛 16 · <b>08:58 盘前重算</b>）· <code>output/sector_tech.json</code>（<code>data_date = 2026-11-04</code> · <code>kline_last_date = 2026-11-04</code> · <code>kline_lag = 0</code> · 31/31 · <b>08:59 重建</b>）· <code>output/golden_diamond.json</code>（数据日 11-04）<br>
    · <b>三面板</b>：<code>vix_panel.cboe_vix = 16.61 @ 2026-11-04</code>（由 20.83 回落 <span class="dk-up">-20.26%</span>）· <code>valuation_band.date = 2026-11-04</code> · <code>market_thermometer.date = 2026-11-04</code>（本版已由 T-1 推进至 T 日）<br>
    · <b>投喂</b>：<code>feed/archive/2026-11-04/_index.json</code>（<b>0 件</b>）· <code>feed/archive/2026-11-05/_index.json</code>（<b>0 件 · 本档补建、如实为空、无伪造条目</b>）· 上一批次 <code>2026-11-03</code>（5 件 · 内容属 11/02，T-2 语境，本页不引用）；语料侧消费 <code>output/daily_news_2026-11-05.json</code> <b>285 条</b>（08:47）<br>
    <b class="dk-main">二、本版十四道门禁（发布前逐条执行）</b><br>
    ① <code>em_http.py</code>（东财统一入口四台）② <code>check_analysis_style.py</code> ③ <code>check_v3_style.py</code> ④ <code>check_market_json.py</code> ⑤ <code>check_macro_freshness.py</code> ⑥ <code>check_index_render.py</code>（9 项）⑦ <code>check_review_dates.py</code> ⑧ <code>check_sector_tech.py</code> ⑨ <code>build_us_medical.py --check</code> ⑩ <code>patch_news_pool.py --check</code> ⑪ <code>patch_v3_richtext.py --check</code> ⑫ <code>patch_dk_css.py --check</code> ⑬ <code>check_touzid_panel.py</code> ⑭ <code>check_narrative_consistency.py</code><br>
    <b class="dk-main">三、本版已知口径边界（不掩饰）</b><br>
    ① <b>日韩为 11/05 早盘实时、非收盘</b>（08:47，韩国已运行 47 分钟）；② <b>主力净额两口径并存</b>：<code>sector_flow</code> +507.57 亿 vs <code>realtime.L1</code> +375.32 亿，本页以 <code>sector_flow</code> 为准、不相加；③ <b>两市成交两口径并存</b>：指数口径 20,377 亿 / 广度口径 17,231.8 亿，本页以指数口径为准；④ <b>美债 10Y / 30Y 滞后 1 个交易日</b>（11-03），数据源长期缺口；⑤ <b>VIX 为 11-04 结算</b>（CBOE 北京 T+1 04:15 结算，本档已可取到）；⑥ <b>油价口径差</b>：新闻「重挫逾 8%」vs 本机早间 -4.23%；⑦ <b>象限标签时滞</b>：<code>flow_date</code> 为 11-04、<code>news_window</code> 含 11-05 ⇒ 电子「共振 A」是「昨日资金 + 今日利空语料」的错配组合，本档已主动降权；⑧ <b>投喂 0 件</b>（<code>feed_count: 0</code>，如实记录）。
  </div>
</div>

"""
html = html[:i8] + SEC8 + html[end8:]

# ═══════════ 9 来源 ═══════════
i9 = html.find("<!-- 9 来源 -->")
end9 = len(html)
SEC9 = """<!-- 9 来源 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">9 · 来源（<b class="dk-data">盘前版 08:40</b> · 复盘日 <b>2026-11-04（周三）</b> → 指引日 <b>2026-11-05（周四）</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div style="font-size:12.5px;line-height:1.65">
    <b class="dk-main">① 行情与资金</b>：<code>data/daily_review/market.json</code>（11-05 08:47 盘前局部更新 · 37 项报价 / 23 项美股 K 线全滚至 11-04）· <code>realtime.json</code>（11-04 22:16 收盘补抓 · <code>market_status = closed</code>）· <code>output/sector_flow.json</code>（<code>flow_date = 2026-11-04</code> · 31/31 · <code>stale_days = 0</code>）· <code>output/top10_history.json</code>（11-04）· <code>output/golden_diamond.json</code>（11-04）<br>
    <b class="dk-main">② 推演与板块</b>：<code>output/cross_analysis.json</code>（08:58 盘前重算 · 窗口 11/04+11/05 · <b>587 条</b>）· <code>output/sector_tech.json</code>（08:59 重建 · 31/31 · <code>kline_lag = 0</code>）· <code>output/obs_deduce_latest.json</code>（11-04）· <code>output/obs_scenarios.json</code>（11-04 → 11-05）· <code>output/obs_panel.json</code>（折叠卡）· <code>output/vix_panel.json</code>（<b>11-04 · 16.61</b>）· <code>output/market_thermometer.json</code>（<b>11-04</b>）· <code>output/valuation_band.json</code>（<b>11-04</b>）<br>
    <b class="dk-main">③ 宏观与新闻</b>：<code>output/daily_macro_latest.json</code>（08:47 · 日历轨 <code>us.calendar</code> + <code>china.*</code>，12 项指标）· <code>output/daily_news_latest.json</code>（08:47 · <b>285 条</b>：宏观 46 / 政策 41 / 科技 40 / 产业 31 / 美股映射 7 / 持仓 2）· <code>output/daily_news_window.json</code>（滚动池 · 窗口切片 587 条）<br>
    <b class="dk-main">④ 投喂</b>：<code>feed/archive/2026-11-04/_index.json</code>（<b>0 件</b>）· <code>feed/archive/2026-11-05/_index.json</code>（<b>0 件 · 本档补建</b>）· <code>feed/archive/feed_index.json</code>（历史清单，最新批次 11-03 的 5 件）—— <b class="dk-caution">本日无投喂语料，全文不含任何投喂引述；既往投喂内容一律标注「投喂语料 · 非本人持仓」</b><br>
    <b class="dk-main">⑤ 规则与技能</b>：<code>review/REVIEW_SOP.md</code>（盘前模式）· skill <code>daily-reasoning</code>（老站）· skill <code>v3-daily-review</code>（V3）· <code>realtime.L2.rules</code>（仓位与追高禁令）· <code>review_v3/backtest_v3.py</code> 的 <code>OPEN_DIR</code> 白名单（<code>open_call = 低开偏弱</code>）<br>
    <b class="dk-main">⑥ 外部素材</b>：研报流 <code>~/Library/Application Support/goldenstock/feed_mahoro</code>（11-05 · 118 条 · 仅本机判读，<b class="dk-caution">禁原文入仓库</b>）—— 其中「北美数据中心被动反内卷、消费刺激与再平衡的一晚：美股中选后反馈」为本文「两条定价链」框架的参考来源之一（<b>观点归属该札记作者，非本页原创结论</b>）<br>
    <b class="dk-risk">⑦ 免责</b>：本页为量化复盘记录，<b>不构成任何投资建议</b>。文中个股仅作板块代表，<b>持仓类标的为「其他专家持股参考（非本人）」</b>，只列客观技术读数、不给加减仓建议；<b>禁据此交易</b>。
  </div>
</div>
"""
html = html[:i9] + SEC9

SRC.write_text(html, encoding="utf-8-sig")
print(f"OK part C: {orig_len} -> {len(html)} chars")
