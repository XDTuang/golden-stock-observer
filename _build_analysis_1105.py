#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-05 盘前版 analysis.html · Part A：顶部注释 / 说明行 / 0 / 0.5
复盘日 2026-11-04（周三收盘）→ 指引日 2026-11-05（周四）
本档核心：A股 11/04「单日暴力反攻 + 情绪 98」→ 隔夜美股「指数涨、AI 硬件崩」的分裂式定价
"""
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
SRC = BASE / "data/daily_review/analysis.html"
html = SRC.read_text(encoding="utf-8-sig")
orig_len = len(html)


def repl(start_anchor, end_anchor, new, tag=""):
    global html
    c = html.count(start_anchor)
    assert c == 1, f"[{tag}] 起始锚点 count={c}: {start_anchor[:50]}"
    i = html.find(start_anchor)
    j = len(html) if end_anchor is None else html.find(end_anchor, i + len(start_anchor))
    assert j > i, f"[{tag}] 结束锚点缺失: {end_anchor[:50]}"
    html = html[:i] + new + html[j:]


def sub(old, new, expect=1, tag=""):
    global html
    c = html.count(old)
    assert c == expect, f"[{tag}] 出现 {c} 次，期望 {expect}: {old[:60]}"
    html = html.replace(old, new)


# ═══════════ 顶部版本注释 ═══════════
i = html.find("<!--\n版本：收盘版 22:15")
j = html.find("-->", i) + 3
OLD_HDR = html[i:j]
NEW_HDR = """<!--
版本：盘前版 08:40 · 复盘日 2026-11-04（周三 · 交易日）· 指引日 2026-11-05（周四）
结构：0 / 0.5 / 1 / 1.1 / 1.2 / 2 / 3 / 4 / 5 / 5.5 / 6 / 7.1 / 7.1b / 7.2 / 7.3 / 7.4 / 8 / 9（18 段）
口径：A股 11/04 完整收盘〔结算价〕 + 美股 **11/04 完整收盘**〔结算价，北京 11/05 05:00 到达，本档已取得〕
      + 日韩 11/05 早盘实时（08:47 首取，见 2 段）+ 港股 11/04 收盘
      + 商品 11/05 早间（金 / 油）+ 美债 11/03（本机长期缺口，滞后 1 日）
数据链：market.json date=2026-11-04（updated_at 2026-11-05 08:47:22 · preopen_partial=true）
      / realtime.json 11-04 22:16:02 market_status=closed（收盘终值，情绪 98）
      / cross_analysis data_date=2026-11-04 flow_date=2026-11-04（2 日窗 11/04–11/05、语料 587 条、门槛 16 = 日均 8 per_day · 08:58 盘前重算）
      / sector_tech data_date=2026-11-04 kline_last_date=2026-11-04（kline_lag=0，08:59 重建）
      / sector_flow flow_date=2026-11-04 stale_days=0
本版核心事实：A股 11/04 上证 3,686.17 +2.16%（开 3,605.39 · 低 3,590.80 · 收＝最高）· 创业板 +6.40% · 科创50 +9.92%
      · 涨 3,731 / 跌 748（比 4.99）· 涨停 113 / 跌停 14 · 主力 +507.57 亿 · 两市 20,377 亿（+19.6%）· 情绪 98「过热」（S1 100/S2 94/S3 100/S4 100）
      · 美股 11/04 完整收盘：道 **+3.03** / 标普 +1.58 / 纳 +1.44，**但 AI 硬件全链崩塌** —— 存储四线 0/4（MU -7.00 / SNDK -7.91 / WDC -6.77 / SKHY -5.12）
        光模块 0/3（LITE -7.85 / AAOI -7.35 / COHR -5.98）· MRVL -7.08 · NVDA -3.17 · TSLA -3.34
      · 今晨亚太 08:47：日经 **+0.51%**（62,502.89）/ KOSPI **-3.32%**（5,495.14）/ SK하이닉스 **-7.09%** / 삼성전자 **-5.28%**
      · 商品 11/05：金 4,039.86 +2.79% · WTI 92.02 -4.23% · 布伦特 98.87 -4.56%；VIX 16.61（11-04，-20.26%）
      · 四象限 本版 7 / 3 / 8 / 13（前版 2 / 0 / 13 / 16）· flow_yi 31/31 逐项零变化、语料 308→587 ⇒ 纯语料侧迁移
      · 判定：方向 中性偏空（由「中性偏多」下调两档）· 开盘 低开（-0.9%~-1.6%，3,627–3,653）· 置信度 中高 · 风险 高 · 仓位 15%–25%
门禁：十四道（详见 8 段与提交信息）
-->"""
html = html.replace(OLD_HDR, NEW_HDR)

# 说明行
sub('<span class="dr-tag">分析 = 收盘版 22:15（本机 agent）</span>',
    '<span class="dr-tag">分析 = 盘前版 08:40（本机 agent）</span>', tag="tagline-ver")

# ═══════════ 0 结论先行 ═══════════
SEC0 = """<!-- 0 结论先行 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">0 · 结论先行（速览卡 · <b>11/05 周四当日指引</b> · <b class="dk-data">盘前版 08:40</b> · 复盘日 <b>11/04（周三）</b> · A股 11/04 完整收盘〔结算价〕+ <b class="dk-up">美股 11/04 完整收盘〔结算价 · 本档新增〕</b> + 日韩 11/05 早盘实时 + 港股 11/04 收盘 + 商品 11/05 早间 + 美债 11/03）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 一句话结论</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">昨夜拿到的是一份「分裂」的外盘：指数在涨，而 11/04 A股 反攻所依赖的那条链，在原产地被打断</b> —— 道指 <b class="dk-up">+3.03%</b>（2026 年内单日最大涨幅之一）、标普 <span class="dk-up">+1.58%</span>、纳指 <span class="dk-up">+1.44%</span>，<b class="dk-risk">但存储四线 <span class="dk-dn">0/4</span>（MU <span class="dk-dn">-7.00%</span> / SNDK <span class="dk-dn">-7.91%</span> / WDC <span class="dk-dn">-6.77%</span> / SKHY <span class="dk-dn">-5.12%</span>）、光模块 <span class="dk-dn">0/3</span>（LITE <span class="dk-dn">-7.85%</span> / AAOI <span class="dk-dn">-7.35%</span> / COHR <span class="dk-dn">-5.98%</span>）、MRVL <span class="dk-dn">-7.08%</span>、NVDA <span class="dk-dn">-3.17%</span></b>。<br>
    <b class="dk-main">成因不是「行情转弱」，而是「分子端换锚」</b>：民主党中期选举「蓝色浪潮」落槌 ⇒ 市场同时交易两件事 —— ① <b class="dk-up">撤销关税 / 结束伊朗战争 ⇒ 油价重挫逾 8%、消费与大型科技飙升</b>；② <b class="dk-risk">数据中心审批与并网放缓 ⇒ AI 资本开支预期下修、算力硬件即刻 de-rating</b>。<b class="dk-caution">11/04 A股 的上涨（科创50 <span class="dk-up">+9.92%</span>、电子 <span class="dk-up">+312.63 亿</span>）恰好全部押在第 ② 条的反面</b>。<br>
    <b class="dk-risk">⇒ 今日（11/05）的定性：昨日「单日暴力反攻」的定价基础被隔夜原产地反向修正，A股 电子 / 存储 / 光模块 / PCB 大概率低开，指数由权重（银行 / 消费 / 交运）承接、结构剧烈分化</b>。今晨韩国已先行验证：<b class="dk-risk">KOSPI <span class="dk-dn">-3.32%</span>、SK하이닉스 <span class="dk-dn">-7.09%</span>、삼성전자 <span class="dk-dn">-5.28%</span></b>（08:47），而日经 <span class="dk-up">+0.51%</span> 逆势收红 ⇒ <b>亚太内部同样是「半导体 vs 非半导体」的分裂，不是全面 risk-off</b>。<br>
    <b class="dk-caution">⇒ 判定：方向 <b class="dk-risk">中性偏空</b>（由「中性偏多」下调两档）· 开盘 <b class="dk-risk">低开（-0.9%~-1.6%，3,627–3,653）</b> · 置信度 <b>中高</b> · 风险 <b class="dk-risk">高</b>（上调一档）· 仓位 <b class="dk-risk">15%–25%</b></b>。核心纪律：<b class="dk-risk">不接低开的第一笔、不做超跌反弹的第一根阳线、情绪 98 的过热档叠加外部核心链断裂 ⇒ 今日只允许「观察 + 减仓」，不允许「加仓」</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 四象限与门控（现场读取 <code>cross_analysis.json</code>（08:58 盘前重算）/ <code>sector_tech.json</code>（08:59 重建）/ <code>realtime.L1</code>（11-04 22:16 收盘终值））</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>维度</th><th>本版（11/05 盘前 08:40）</th><th>前版（11/04 收盘 22:15）</th><th>读数</th></tr></thead><tbody>
    <tr><td><b>四象限</b>（共振 A / 背离 B / 暗线 C / 双冷 D）</td><td><b class="dk-caution">7 / 3 / 8 / 13</b></td><td>2 / 0 / 13 / 16</td><td><div class="dr-wrap"><b class="dk-main">迁移主因 = 纯语料侧扩容，资金列一个数字都没动</b>：<code>flow_yi</code> <b>31/31 逐项零变化</b>（差 &lt; 1e-9，<code>flow_date</code> 仍为 11-04），窗口语料 <b>308 → 587 条</b>（11/05 早间池并入 2 日窗）⇒ 7 个板块跨过「日均 8 条」门槛：<b>国防军工 / 综合 / 汽车</b> 升<b>共振 A</b>，<b>银行 / 石油石化 / 非银金融</b> 升<b>背离 B</b>。<b class="dk-caution">故本版象限迁移 <b>不得读作资金行为改善</b>，更不得据此上调仓位</b></div></td></tr>
    <tr><td><b>象限标签的今日失效提示</b>（本档新增）</td><td><b class="dk-risk">电子仍标「共振 A」，但今日不可按共振读</b></td><td>电子 = 共振 A（当日成立）</td><td><div class="dr-wrap"><b class="dk-risk">机制缺陷显式化：象限 = 「T 日资金」× 「T+1 语料」</b>。电子今日 <code>news_count = 49</code>（全场最高）<b>但其内容主体是「存储 / 光通信下跌」</b>，逢 T 日资金 <span class="dk-up">+312.63 亿</span> ⇒ 机械落进「共振」。<b class="dk-main">当隔夜原产地反向时，「共振 A」会失真为「昨日资金 + 今日利空」的错配组合，本档据此对电子标签<b>主动降权</b></b></div></td></tr>
    <tr><td><b>板块技术分级</b>（<code>sector_tech</code> · 08:59 重建 · <code>kline_lag = 0</code>）</td><td><b class="dk-risk">L4 0 / L3 0 / L2 15 / L1 16</b></td><td>L4 0 / L3 0 / L2 15 / L1 16</td><td><div class="dr-wrap"><b class="dk-risk">连续第四版「L4 = 0 / L3 = 0」</b>，趋势结构 <b>向上 2 / 反弹 7 / 下跌 22</b>。<b class="dk-main">11/04 的 +2.16% 与 +507 亿没有换来任何一个板块的技术升级 —— 因为判据要求「资金分位达标且连续 ≥2 日」，单日暴力流入在规则上不予承认</b>。<b class="dk-caution">⇒ 昨日是「资金到位、技术未认」，今日是「资金待验证、外部先反手」，两者叠加 = 无技术面承接</b></div></td></tr>
    <tr><td><b>情绪分</b>（<code>realtime.L1</code> · 11-04 22:16 收盘终值）</td><td><b class="dk-risk">98 · 情绪过热预警</b>（S1 100 / S2 94 / S3 100 / S4 100）</td><td>98 · 情绪过热预警</td><td><div class="dr-wrap">规则档 <code>overheat [30,50]</code>。<b class="dk-risk">L2 明文：情绪分 ≥ 85 触发追高禁令（只允许回踩低吸）</b>；<b class="dk-main">本档把仓位下调至 15%–25%、主动偏离该档下限 30% 的理由有三：① 情绪 98 是全历史尾部读数，均值回归压力最大；② 外部核心链单日 -7%~-8%，映射确定性高于以往；③ 昨日的资金反攻尚无一日的技术确认（L4/L3 = 0）</b></div></td></tr>
    <tr><td><b>国证美股映射</b>（<code>market.json.us_kline</code> · 23/23 已滚至 11-04）</td><td><b class="dk-risk">存储 0/4 · 光模块 0/3 · AI 硬件全链负</b></td><td>存储 4/4 · 光模块 2/3（11/03）</td><td><div class="dr-wrap"><b class="dk-risk">一夜之间由「4/4 全红」翻为「0/4 全黑」，均值由 +3.01% 变为 <span class="dk-dn">-6.70%</span></b>（MU -7.00 / SNDK -7.91 / WDC -6.77 / SKHY -5.12）；光模块三线均值 <span class="dk-dn">-7.06%</span>。<b class="dk-main">这不是回踩，是链条级重定价 —— 11/04 A股 存储 / 光模块 / PCB 的涨幅已被隔夜抹去，今日开盘价将直接反映</b></div></td></tr>
    <tr><td><b>两市成交 / 主力</b>（11-04 终值）</td><td><b class="dk-up">20,377 亿</b>（+19.6%）· 主力 <b class="dk-up">+507.57 亿</b></td><td>同（11-04）</td><td><div class="dr-wrap">放量 + 主力净流入是<b>昨日的既成事实</b>，但它同时是<b>今日的套牢盘</b>：<b class="dk-main">20,377 亿的成交意味着昨日的平均持仓成本被抬到 3,650 上方，今日若低开至 3,627–3,653，则昨日绝大部分买盘即刻转为浮亏 —— 这是「低开后的二次抛压」来源</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-tag" style="margin-top:10px">③ 今日（11/05 周四）三档剧本</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">情形 A · 低开杀跌扩散（概率 45% · 本档基准情形）</b>：上证低开 -0.9%~-1.6%（<b>3,627–3,653</b>）后 30 分钟内<b>不能收复 3,660</b>，<b>跌停 &gt;25 家或电子板块再流出 &gt;120 亿</b> ⇒ 定性 <b class="dk-risk">「反攻定价被否、进入二次探底」</b>，仓位降至 <b>15%</b> 以下，只保留非电子方向；观察 3,608.10（11/03 收盘 = 前一轮上攻起点）为<b>最后防线</b>。<br>
    <b class="dk-caution">情形 B · 低开承接、内部对冲（概率 40%）</b>：低开后 <b>银行 / 食品饮料 / 交运 / 消费</b> 承接，上证回到 <b>3,660–3,680</b> 区间震荡，而电子 / 科创弱势不改 ⇒ 定性 <b class="dk-caution">「指数稳、结构杀」</b>，仓位 <b>20%–25%</b>，<b class="dk-risk">电子链一律不补、不抢反弹</b>，只允许在非电子方向做回踩。<br>
    <b class="dk-up">情形 C · 低开被吞、外盘误读（概率 15%）</b>：上证低开后<b>半日内收复 3,686.17</b> 且<b>电子资金转正 &gt;100 亿</b>、涨停回升 &gt;110 家 ⇒ 定性 <b class="dk-up">「隔夜杀跌为一次性调仓、A股 独立承接成立」</b>，仓位回升 <b>30%</b>（不破 overheat 档下限），但<b>须等到收盘确认</b>，盘中不加。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-caution">④ 必须同时记录的五条反向证据（不构成买入理由，只用于防止单边解读）</b>：① <b class="dk-up">美股权重与消费端大涨、VIX 反而回落至 16.61（<span class="dk-up">-20.26%</span>）</b> ⇒ 全球风险偏好并未恶化，恶化的是「AI 硬件」这一条产业链；② <b class="dk-up">Coherent 财报超预期（Q1 营收 +50%、数据中心 +79%）而股价 <span class="dk-dn">-5.98%</span></b> ⇒ <b class="dk-main">这是「估值杀 / 预期下修」，不是「业绩杀」—— 真正的景气破坏尚未在财报中出现</b>；③ <b class="dk-up">中信证券同日观点「存储供不应求延续、关注长协与股东回报」</b>；④ <b class="dk-caution">油价 -8% 对 A股 是结构性利多（交运 / 化工 / 电力成本）与利空（石油石化 / 煤炭）并存</b>；⑤ <b class="dk-caution">黄金 <span class="dk-up">+2.79%</span> 至 4,039.86 与美股同涨</b> ⇒ 避险与风险资产同向，说明驱动仍是<b>流动性预期</b>而非盈利。
  </div>
</div>

"""
repl("<!-- 0 结论先行 -->", "<!-- 0.5 深度判读 -->", SEC0, tag="sec0")

# ═══════════ 0.5 深度判读 ═══════════
SEC05 = """<!-- 0.5 深度判读 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">0.5 · 深度判读（盘前版 08:40 · <b>A股 11/04 收盘 vs 美股 <span class="dk-dn">11/04 完整收盘</span> vs 日韩 <span class="dk-risk">11/05 早盘</span></b> · <b>本版四象限</b> 7 / 3 / 8 / 13 · 前版 2 / 0 / 13 / 16）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 前一日推演验证（对 11/04 收盘版 22:15 的五条判断逐条复核 · 含<b class="dk-risk">被推翻项</b>）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>前版判断（11/04 22:15）</th><th>隔夜证据（11/04 美股收盘 / 11/05 早间亚太）</th><th>裁定</th></tr></thead><tbody>
    <tr><td><b>方向 中性偏多</b>（资金级反转成立）</td><td>道 +3.03 / 标普 +1.58 / 纳 +1.44 <b>三项均验证「外部不弱」</b>；但 A股 所依赖的电子 / 存储 / 光模块 <b>全线 -5%~-8%</b></td><td><div class="dr-wrap"><b class="dk-risk">部分推翻</b>：指数层面的「外部不弱」成立，<b>结构层面（A股 相关链条）被完全反向</b>。方向判断的依据选错了维度 —— 用了指数 β，未用产业映射</div></td></tr>
    <tr><td><b>开盘 高开回吐压力（+0.3%~+0.8%，3,697–3,716）</b></td><td>隔夜电子链崩塌 + 今晨 KOSPI -3.32% / SK하이닉스 -7.09%（08:47）</td><td><div class="dr-wrap"><b class="dk-risk">推翻</b>：由「高开」改为「低开」。<b class="dk-main">教训与 10-30 同源：跨市场「同日分化」不可外推为「结构性独立」；盘前必须用「次日亚太开盘」二次确认</b></div></td></tr>
    <tr><td><b>风险 中高 · 仓位 30%–40%</b></td><td>情绪 98 未变，外部核心链单日 -7%；技术档位 L4/L3 连续第四版为 0</td><td><div class="dr-wrap"><b class="dk-caution">上调风险至「高」、下调仓位至 15%–25%</b>：三项叠加（情绪极值 + 外链断裂 + 技术零确认）指向「不给风险预算」</div></td></tr>
    <tr><td><b>证伪线：上证失守 3,608.10 / 电子单日净流出 &gt;100 亿 / 跌停 &gt;40 家</b></td><td>今日尚未开盘，三条均未触发 —— <b>本档沿用并前置为「盘中哨兵」</b></td><td><div class="dr-wrap"><b class="dk-up">保留</b>：证伪线继续有效，且今日被触及的概率显著上升（低开即在 3,627–3,653，距 3,608.10 仅 0.5%~1.3%）</div></td></tr>
    <tr><td><b>「存储 / 光模块的原产地反证」是本轮最强多头证据</b></td><td>11/04 存储 0/4（均值 -6.70%）、光模块 0/3（均值 -7.06%）、MRVL -7.08%</td><td><div class="dr-wrap"><b class="dk-risk">直接推翻</b>：前版把 11/03 的「4/4 全红」当作链条健康证据，<b>隔夜即被 -7% 抹平</b>。<b class="dk-main">⇒ 方法论升级为铁律（第 6 次）：跨市场映射判断的有效期 = 1 个交易日，隔夜必须重新取证，不得沿用</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">② 四象限 2×2（<code>cross_analysis.json</code> · 08:58 盘前重算 · <code>flow_date = 2026-11-04</code> · 窗口 11/04–11/05 · 587 条 · 门槛 16 = 日均 8）</div>
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:6px">
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-up">共振 A · 7 席（前版 2 → 本版 7）</b></div>
      <div style="font-size:12.5px;line-height:1.6">电子（49 条 / +312.63 亿）· 通信（23 / +75.86）· 有色金属（22 / +73.45）· 计算机（56 / +22.32）· 国防军工（20 / +4.21）· 综合（16 / +0.49）· 汽车（23 / +0.48）</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-risk">今日必读：</b>电子 / 通信 两席的「语料热」= 隔夜下跌新闻，<b>不构成今日做多依据</b>；真正有「昨日资金 + 今日顺向语料」双支撑的是<b>有色 / 军工 / 汽车</b></div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-risk">背离 B · 3 席（前版 0 → 本版 3）</b></div>
      <div style="font-size:12.5px;line-height:1.6">银行（23 / <span class="dk-dn">-15.33 亿</span>）· 石油石化（17 / <span class="dk-dn">-11.53</span>）· 非银金融（16 / <span class="dk-dn">-6.82</span>）</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-caution">三席均为「语料热、资金撤」</b>：银行 / 非银是今日最可能的<b>防御承接方向</b>，但资金列仍为负 ⇒ <b>承接力来自「避险切换」而非「增量买入」，不可当作趋势做</b></div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-caution">暗线 C · 8 席（前版 13 → 本版 8）</b></div>
      <div style="font-size:12.5px;line-height:1.6">电力设备（12 / +45.56 亿）· 机械设备（12 / +44.86）· 建筑材料（0 / +12.41）· 传媒（13 / +7.65）· 基础化工（4 / +6.80）· 轻工制造（0 / +4.37）· 建筑装饰（0 / +3.89）· 美容护理（0 / +0.53）</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-main">本档唯一具备「资金已入、语料未炒、且不受 AI 硬件拖累」特征的象限</b> —— 电力设备 / 机械 / 建材 是今日低开后最可能出现「资金续做」的方向</div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-neutral">双冷 D · 13 席（前版 16 → 本版 13）</b></div>
      <div style="font-size:12.5px;line-height:1.6">食品饮料 · 交通运输 · 公用事业 · 煤炭 · 基础化工（部分口径）· 纺织服饰 · 农林牧渔 · 商贸零售 · 社会服务 · 房地产 · 家用电器 · 环保 · 医药生物 · 钢铁</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-caution">注意：食品饮料 / 交运 今日大概率「价格上涨但标签仍是双冷」</b> —— 油价 -8% 与消费刺激是<b>今日新增变量</b>，尚未进入任何一日的资金列。<b>双冷不等于今日不能涨，只等于「无资金证据」</b></div>
    </div>
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.6;margin-top:8px">
    <b class="dk-main">迁移性质的判定（本段最关键的三句）</b>：① <code>flow_yi</code> 31/31 逐项零变化、<code>flow_date</code> 未变 ⇒ <b>资金侧零贡献</b>；② 语料 308 → 587 条（11/05 早间池 08:47 抓取并入）⇒ <b>全部迁移由语料侧完成</b>；③ <b class="dk-caution">因此「共振 A 由 2 升至 7」不得读作「资金共振扩大」，它只说明「昨天流入的板块今天被媒体讨论得更多」—— 而讨论的内容恰是利空</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 三维交叉：为什么今日是「结构性风险」而非「系统性风险」</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>维度</th><th>读数（本档现场取数）</th><th>含义</th></tr></thead><tbody>
    <tr><td><b>触发源</b></td><td>民主党中期选举「蓝色浪潮」→ 关税撤销预期 + 数据中心审批放缓预期</td><td><div class="dr-wrap"><b class="dk-main">两条都是「政策预期」而非「已发生事实」</b>：关税撤销需国会立法（时间以季度计），数据中心限制目前仅体现为「审批变慢」的预期（Vito 引第三方测算：capex 总额可能上升 10%~20%、接电推迟 12–24 个月、项目 IRR 由 12%~14% 降至 9%~11%）。<b class="dk-caution">⇒ 冲击的性质是「折现率与审批周期」，不是「需求消失」</b></div></td></tr>
    <tr><td><b>传导路径</b></td><td>美股：AI 硬件 -5%~-8%，指数 +1.4%~+3.0%；韩股：SK하이닉스 -7.09%、삼성 -5.28%，KOSPI -3.32%；日经 +0.51%</td><td><div class="dr-wrap"><b class="dk-risk">传导是「链内」而非「全市场」</b>：<b>亚太三大市场里只有韩国半导体权重高的市场下跌</b>，日经逆势红盘。A股 的映射顺序应是「电子 / 存储 / 光模块 / PCB 低开 → 科创 50 / 创业板 重挫 → 上证 由权重对冲」</div></td></tr>
    <tr><td><b>内部缓冲</b></td><td>主力 +507.57 亿（昨日）· 宽基 ETF 承接 · 银行 / 消费 / 交运 为防御端 · 政策面 SFISF 1,000 亿（11/03 操作，费率 10bp，31 家机构投标）</td><td><div class="dr-wrap"><b class="dk-up">缓冲真实存在但方向不对</b>：昨日进场的 507 亿主要押在电子（+312.63 亿），<b>今日这部分恰好是被冲击的方向</b>；能起对冲作用的是尚未被资金验证的银行 / 消费 / 交运 —— <b class="dk-caution">即「护盘力量在旧方向，避险资金在新方向」，两者不在同一批标的上</b></div></td></tr>
    <tr><td><b>情绪与位置</b></td><td>情绪 98（S1 100 / S2 94 / S3 100 / S4 100）· 涨跌比 4.99 · 涨停 113 · 上证收于当日最高 3,686.17 · 科创板 +9.92%</td><td><div class="dr-wrap"><b class="dk-risk">位置极端</b>：<b>单日 +9.92% 之后遇外链 -7%，历史上很难在次日完成「平开消化」，多数以「低开 + 二次探底」形式出清</b>；本档据此不设置「低开即买」条款</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-main">④ 本档的取舍（给操作层的明确边界）</b>：<b class="dk-risk">减什么</b> —— 电子 / 半导体 / 存储 / 光模块 / PCB 一律列为「不补、不抢反弹」，若昨日有浮盈则按纪律兑现；<b class="dk-caution">留什么</b> —— 电力设备 / 机械设备（暗线 C 且资金为正）与银行 / 食品饮料（防御承接，但只做低吸不追）；<b class="dk-neutral">等什么</b> —— ① 上证在 3,608.10 上方的第一次「缩量回踩」；② 电子资金转为单日净流入；③ 今晚 11/06 美国 10 月非农（花旗预期不足以改变美联储路径）。<b class="dk-caution">三者未同时出现前，仓位不上 25%</b>。
  </div>
</div>

"""
repl("<!-- 0.5 深度判读 -->", "<!-- 1 昨日", SEC05, tag="sec05")

SRC.write_text(html, encoding="utf-8-sig")
print(f"OK part A: {orig_len} -> {len(html)} chars")
