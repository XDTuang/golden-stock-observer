#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-06 · Part B：4 重点宏观 / 5 重点科技 / 5.5 产业链 / 6 新闻整合"""
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
SRC = BASE / "data/daily_review/analysis.html"
html = SRC.read_text(encoding="utf-8-sig")


def repl_between(start_anchor, end_anchor, new, tag=""):
    global html
    c = html.count(start_anchor)
    assert c == 1, f"[{tag}] 起始 count={c}: {start_anchor[:60]}"
    i = html.find(start_anchor)
    j = html.find(end_anchor, i + len(start_anchor))
    assert j > i, f"[{tag}] 结束锚点缺失: {end_anchor[:60]}"
    html = html[:i] + new + html[j:]


# ═══════════ 4 重点宏观 ═══════════
SEC4 = """<!-- 4 重点宏观 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">4 · 重点宏观（<b>日历轨为准</b> · <code>output/daily_macro_latest.json</code> · <code>us.calendar.as_of = 2026-11-06 08:42</code> · <b class="dk-risk">通胀顽固 + 增长减速 = 滞胀特征；今晚 21:30 公布 10 月非农</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 美国关键指标（<b>日历轨公布值</b> · 龄期按 2026-11-06 现算，<b>不用文件内 days_ago</b>）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新公布值</th><th>公布日</th><th>龄期</th><th>预期 / 前值</th><th>读法</th></tr></thead><tbody>
    <tr><td><b>CPI 同比</b>（9 月）</td><td><b class="dk-caution">3.7%</b></td><td>2026-10-14</td><td>23 天</td><td>预期 3.6 / 前值 3.4</td><td><div class="dr-wrap"><b class="dk-caution">高于预期 0.1pct、高于前值 0.3pct，通胀在 3.7% 重新抬头</b>。<b class="dk-main">这是「全球央行转鹰 + 昨夜美股杀估值」的数据基础 —— 不是预期驱动，是已公布事实驱动</b></div></td></tr>
    <tr><td><b>核心 CPI</b>（同比 / 月率）</td><td><b class="dk-caution">2.6% / 0.3%</b></td><td>2026-10-14</td><td>23 天</td><td>预期 2.5 / 0.2</td><td><div class="dr-wrap">同比与月率<b>双双高于预期</b> ⇒ <b class="dk-caution">核心通胀的回落斜率被打断</b>，这是长端利率难下（30Y 5.28%）的直接原因</div></td></tr>
    <tr><td><b>核心 PCE</b>（9 月同比）</td><td><b class="dk-caution">3.1%</b></td><td>2026-10-29</td><td><b>8 天</b></td><td>预期 3.1 / Q3 年化 2.5</td><td><div class="dr-wrap"><b class="dk-caution">与预期持平但绝对水平仍在 3.1%，距 2% 目标尚有 1.1pct</b>；Q3 年化 2.5%（预期 2.4）⇒ <b class="dk-main">季度维度在改善、同比维度仍顽固，「通胀已解决」的叙事被否</b></div></td></tr>
    <tr><td><b>GDP 价格指数</b>（Q3 初值）</td><td>2.1% / 2.3%</td><td>2026-10-29</td><td>8 天</td><td>预期 3.5</td><td><div class="dr-wrap">隐性平减指数 2.1%、价格指数 2.3%，<b>双双大幅低于预期 3.5%</b> ⇒ 与 CPI 3.7% 方向相反 ⇒ <b class="dk-caution">统计口径间的分歧，压低了「滞胀」判断的确定性</b></div></td></tr>
    <tr><td><b class="dk-risk">非农</b>（10 月新增）</td><td><b class="dk-risk">今晚 21:30 公布 · 值未出</b></td><td><b>2026-11-06</b></td><td><b>0 天</b></td><td>预期 +6.5 万 / 失业率 4.2%</td><td><div class="dr-wrap"><b class="dk-risk">今日最重要的单点事件</b>。<b class="dk-caution">日历轨该条 <code>value</code> 为空（源侧未回填），<code>us.stale</code> 已列「非农」，本档<b>只引用预期值与公布时点，不引用数值</b></b>。<b class="dk-main">情景：&gt;10 万 ⇒ 加息预期坐实、全球高估值二次杀；&lt;4 万 ⇒ 就业失速、降息交易回归、美股可能 V 型修复</b></div></td></tr>
    <tr><td><b>失业率</b>（10 月）</td><td><b class="dk-risk">今晚 21:30 公布 · 值未出</b></td><td><b>2026-11-06</b></td><td><b>0 天</b></td><td>预期 4.2%</td><td><div class="dr-wrap">与非农同刻公布；<b>4.2% 是市场共识</b>，若升至 4.4%+ 则「衰退」叙事启动，对 A股 反而是流动性利好（政策空间打开）</div></td></tr>
    <tr><td><b>ADP 就业</b>（10 月）</td><td><b class="dk-up">+8.6 万</b></td><td><b>2026-11-04</b></td><td><b>2 天</b></td><td>预期 6.5</td><td><div class="dr-wrap"><b class="dk-up">强于预期 2.1 万</b> ⇒ <b class="dk-main">与非农预期的 +6.5 万形成分歧（ADP 强 / 非农预期弱），这正是「今晚非农」的不确定性来源</b></div></td></tr>
    <tr><td><b>ISM 制造业</b></td><td><b class="dk-up">55.5</b></td><td>2026-11-02</td><td>4 天</td><td>预期 54.6</td><td><div class="dr-wrap"><b class="dk-up">连续扩张且高于预期</b> ⇒ <b class="dk-caution">制造业景气不支持「衰退」定价，进一步压缩降息空间</b></div></td></tr>
    <tr><td>零售销售（9 月）</td><td><b class="dk-up">0.8%</b></td><td>2026-10-15</td><td>22 天</td><td>预期 0.3 / 核心 0.9%</td><td><div class="dr-wrap">消费端未失速，<b class="dk-main">与 Vito「万豪创新高、客单价非常猛 ⇒ 离衰退预期还比较远」的判断一致</b></div></td></tr>
    <tr><td>初请失业金</td><td><b class="dk-caution">空缺</b></td><td>2026-11-05</td><td>1 天</td><td>预期 19.5 万</td><td><div class="dr-wrap"><b class="dk-caution">条目已生成但数值为空（源侧未回填）→ 已在 <code>us.stale</code> 列表标注，本档不引用其值</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">② 昨夜「政策 × 利率」双杀的结构（<b>本段最重要的宏观判断</b>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">① 政治端：民主党中期选举大胜（「蓝色浪潮」）⇒ AI 数据中心成为首个被点名对象</b>。今日语料〈立马就拿数据中心「开刀」？「蓝潮」席卷美国 民主党高层接连发声〉（08:32）、〈顶住「蓝色浪潮」潜在阻力？谷歌官宣斥资 170 亿美元布局怀俄明数据中心〉（08:38）、〈微软曾帮助催生「新云」热潮…与新兴数据中心运营商签署数百亿合同〉（07:5x）⇒ <b class="dk-main">这条链是「政策不确定性」而非「需求证伪」，前者可以用时间化解，后者不能</b>。<br>
    <b class="dk-risk">② 利率端：CPI 3.7% + 核心 PCE 3.1% + ADP 8.6 万 + ISM 55.5 ⇒ 12 月「加息」成为可交易情景</b>。<b class="dk-caution">语料已出现「美国 9 月核心 PCE 同比上涨 3.1%，美联储 12 月或加息 25 个基点」（10-30 财经早餐）</b> ⇒ <b class="dk-main">这是 2026 年首次出现「加息」而非「推迟降息」的表述，属货币政策框架的实质性转向</b>。<br>
    <b class="dk-caution">③ 反向：Q3 GDP 平减指数 2.1%（预期 3.5%）+ 核心 PCE 年化 2.5%</b> ⇒ <b>季度口径的通胀压力明显低于月度口径</b>，这为「加息论」留下了反驳空间，也是昨夜美股盘中一度收窄跌幅的原因。<br>
    <b class="dk-main">⇒ 本段结论：这是「政策不确定性 + 利率方向不确定」的叠加，而非「基本面恶化」</b>。<b class="dk-caution">因此本档对 A股 的判断是「杀估值、不杀盈利」：跌的是高 β / 高估值（创业板 -4.99% 开盘、科创50 -5.05% 开盘），而不是全部（上证 -2.11%、沪深300 -2.32%）</b>。
  </div>

  <div class="dr-tag" style="margin-top:10px">③ 中国侧（国内政策与数据，择要记录）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b>数据</b>：10 月制造业 PMI <b class="dk-risk">49.3</b>（连续处收缩区）、非制造业 <b class="dk-risk">49.7</b>（跌破荣枯线）；前三季度 GDP <b>+4.6%</b>；9 月 CPI <b class="dk-up">+0.9%</b>（环比 +0.2%）；LPR 1Y <b>3.00%</b> / 5Y <b>3.50%</b>（10-20 报价，连续持稳）⇒ <b class="dk-main">国内是「低通胀 + 弱增长 + 宽货币」的组合，与美国「高通胀 + 强就业 + 紧货币」正好相反 ⇒ 这是「中国资产脱钩」的宏观基础</b>。<br>
    <b>政策</b>：今日语料中华泰证券张继强〈千亿元增量资金蓄势 稳市工具迈向长期制度安排〉（08:12）、中信证券〈利率拐点叠加资金回流，看好港股互联网修复行情〉（08:12）、〈在美上市中概股逆势走强 中国科技政策稳定预期形成支撑〉（08:19）、〈华泰证券：供给优化与全球补库共振，大宗化工品景气有望逐步回升〉（08:15）⇒ <b class="dk-main">卖方在今日一致转向「稳市 + 港股 + 化工」，这是「外部冲击 → 内部对冲」的标准叙事路径</b>。<br>
    <b class="dk-caution">须警惕</b>：PMI 49.3 / 49.7 双双低于荣枯线，<b>国内基本面并未提供「独立上行」的支撑</b>，A股 今日的「抗跌」只能来自「估值已低 + 政策预期」，不能来自盈利。
  </div>
</div>

"""
repl_between("<!-- 4 重点宏观 -->", "<!-- 5 重点科技 -->", SEC4, tag="sec4")

# ═══════════ 5 重点科技 ═══════════
SEC5 = """<!-- 5 重点科技 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">5 · 重点科技（对照 <b class="dk-risk">美股 11/05 完整收盘〔结算价 · 昨夜〕</b> · 六条主线 · <b class="dk-risk">全链 de-rating：存储 -17.62% / 光通信 -17.52% / ASIC -16.43%</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>主线</th><th>美股 11/05 收盘读数</th><th>A股 11/05 对应环节</th><th>读法 / 今日含义</th></tr></thead><tbody>
    <tr><td><b>存储</b></td><td><div class="dr-wrap">SNDK <b class="dk-risk">-22.26%</b>（806.43）· MU <b class="dk-risk">-17.46%</b>（656.39）· WDC <b class="dk-risk">-17.35%</b>（267.63）· SKHY <b class="dk-risk">-13.40%</b>（123.90）<br><b>四线均值 -17.62%（0/4）</b>；韩股 SK하이닉스 <b class="dk-risk">-7.91%</b> / 삼성전자 <b class="dk-risk">-6.90%</b>（今晨）</div></td><td><div class="dr-wrap">半导体 <b class="dk-up">+2.05%</b>（+61.04 亿）· 半导体材料 <b class="dk-up">+6.01%</b>（+20.38 亿）· 半导体设备 <b class="dk-up">+7.71%</b>（+54.32 亿）<br><b class="dk-caution">（均为 11-05 数据，今日必大幅回吐）</b></div></td><td><div class="dr-wrap"><b class="dk-risk">昨日「首尔读价格见顶、A股 读份额上移」的语义反转框架，今日失效</b>：本次事件的语义是<b>「资本开支被政策压制」</b>（数据中心审批 / 监管），而不是「存储价格见顶」。<b class="dk-main">⇒ 前者同时利空「原厂」与「设备」（扩产本身被质疑），后者的结论（设备受益）不再适用</b>。<b class="dk-risk">今日 A股 存储 / 设备链从「首选」降为「观察」，不接反弹</b></div></td></tr>
    <tr><td><b>光模块 / 光通信</b></td><td><div class="dr-wrap">AAOI <b class="dk-risk">-20.89%</b>（46.89）· LITE <b class="dk-risk">-18.68%</b>（509.70）· COHR <b class="dk-risk">-12.98%</b>（169.76）<br><b>三线均值 -17.52%（0/3）· 两日累计约 -23.4%</b></div></td><td><div class="dr-wrap"><b class="dk-risk">通信 -47.11 亿（前日 +75.86 亿，单日反转 122.97 亿）</b>，<code>news_count</code> 14 条 · <b>双冷 D（全场最大流出）</b></div></td><td><div class="dr-wrap"><b class="dk-risk">本档最明确、最无争议的「负向主线」</b>：外部两日 -23.4%、内部资金单日反转 123 亿、象限双冷，三重同向。<b class="dk-main">⇒ 今日任何反弹都不参与；若再流出 &gt;30 亿，则升级为「回避 + 反手不做」</b>。<b class="dk-caution">注意：COHR 财报超预期（数据中心 +79%）仍跌 12.98% ⇒ 估值杀远未结束</b></div></td></tr>
    <tr><td><b>ASIC / 算力芯片</b></td><td><div class="dr-wrap">MRVL <b class="dk-risk">-16.43%</b>（133.55）· NVDA <b class="dk-risk">-9.26%</b>（181.60，市值蒸发 4,470 亿美元）· TSLA <b class="dk-risk">-10.77%</b></div></td><td><div class="dr-wrap">计算机 <b class="dk-up">+13.99 亿</b>（<b>唯一 L4</b> · 56 条语料）· 电子 +12.05 亿（58 条）</div></td><td><div class="dr-wrap"><b class="dk-risk">ASIC 跌幅是 GPU 的 1.77 倍</b> ⇒ 市场杀的是「大厂自研 / 定制化算力」的资本开支，<b>即「还要不要自建」这个根本问题</b>。<b class="dk-caution">计算机 56 条语料是利空型热度、资金是 11-05 旧值 ⇒ 共振 A 必须降权；L4 技术档位在「系统性杀估值」面前不构成支撑</b></div></td></tr>
    <tr><td><b>PCB / 铜连接</b></td><td><div class="dr-wrap">— （本档无直接对标；费半 -12% 覆盖其下游）</div></td><td><div class="dr-wrap">电子 +12.05 亿，但 <b>金钻起涨 6 只中 3 只为 PCB（澳弘电子 / 满坤科技 等）</b></div></td><td><div class="dr-wrap"><b class="dk-risk">这是本档认为「最危险」的一组</b>：昨日是「最热」（半导体设备 +7.71%、PCB 金钻命中），今日对应外部是「数据中心 capex 被质疑」。<b class="dk-main">⇒ 昨日最热 + 今日最危险，是本轮最典型的「错位」；持仓类标的须按板块级风险描述处理</b></div></td></tr>
    <tr><td><b>新能源 / 电力设备</b></td><td><div class="dr-wrap">— （与 AI 资本开支无关，昨夜未被抛售）</div></td><td><div class="dr-wrap"><b class="dk-up">电力设备 +3.02%（+63.10 亿 · streak 4 · 资金分位 100 · 31 板块第一）</b> · 光伏设备 +5.77%（+32.36 亿）· 电池 +3.10%（+26.43 亿）· 碳酸锂 91,580 持稳</div></td><td><div class="dr-wrap"><b class="dk-up">本档唯一保留的「抗冲击方向」</b>：① 资金连续 4 日净流入、分位 100；② 与 AI 资本开支零关联，不受「蓝潮」政策冲击；③ 政策共振（氢能五大城市群试点、发改委储能 / 电力市场调研）；④ 锂价稳 ⇒ 成本端无压力。<b class="dk-caution">风险：news 仅 12 条未过门槛（仍是暗线），且今日大盘系统性下跌时难有超额</b></div></td></tr>
    <tr><td><b>医药 / CXO（映射参考）</b></td><td><div class="dr-wrap">RGEN <b class="dk-risk">-5.45%</b>（最弱）· TMO <b class="dk-risk">-4.14%</b> · CRL <b class="dk-risk">-4.07%</b> · WST -3.99% · LLY -3.76% · DHR -3.66% · MEDP -3.32% · LH -1.22% · ICLR <span class="dk-dn">-0.72%</span> · <b class="dk-up">IQV +0.41%</b>（唯一上涨）<br><b>核心 8 只均值 -2.77% · 上涨 1/8</b></div></td><td><div class="dr-wrap">医药生物 <b class="dk-up">+5.71 亿</b>（暗线 · news 6 条）</div></td><td><div class="dr-wrap"><b class="dk-caution">医疗是昨夜跌幅最小的板块组（核心 8 只 -2.77%，显著优于纳指 -5.52%）</b> ⇒ <b class="dk-main">「非 AI 资产」的相对抗跌在美股已经验证，这为 A股 今日的「防御 + 非 AI」方向提供了外部参照</b>。<b>详见 3 段末的 10 只映射表</b></div></td></tr>
  </tbody></table></div>
</div>

"""
repl_between("<!-- 5 重点科技 -->", "<!-- 5.5 产业链 / 景气度 -->", SEC5, tag="sec5")

# ═══════════ 5.5 产业链 ═══════════
SEC55 = """<!-- 5.5 产业链 / 景气度 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">5.5 · 产业链 / 景气度评估（六条链 · 每条含 <b>今日（11/06）观察要点</b> · 基准 = A股 11/05 完整收盘 + 美股 <span class="dk-risk">11/05 完整收盘〔昨夜〕</span>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>链</th><th>景气度判定</th><th>证据（价格 / 订单 / 资金）</th><th>今日（11/06）观察要点</th></tr></thead><tbody>
    <tr><td><b>存储</b></td><td><b class="dk-risk">叙事被否（当日证伪）</b></td><td><div class="dr-wrap">美股四线 <b>-17.62%</b>（SNDK -22.26 最弱）、韩股 -7.91% / -6.90%；语料〈市场不再相信存储超级周期？〉〈存储巨头 300 亿工厂停工〉；A股 11-05 半导体 +61.04 亿为旧值</div></td><td><div class="dr-wrap"><b class="dk-risk">看 A股 存储（设计 / 模组 / 设备）低开后能否收回一半跌幅</b>：<b>不能收回 ⇒ 「国产替代」叙事正式作废</b>；能收回 ⇒ 说明 A股 定价的是「份额」而非「周期」，但<b>仍不构成买入理由</b></div></td></tr>
    <tr><td><b>光模块 / 光通信</b></td><td><b class="dk-risk">下行确认（六条链中最差）</b></td><td><div class="dr-wrap">美股三线 <b>-17.52%</b>（两日 -23.4%）；A股 通信 <b>-47.11 亿</b>（单日反转 122.97 亿）、语料 14 条、<b>双冷 D</b></div></td><td><div class="dr-wrap"><b class="dk-risk">看通信资金是否再流出 &gt;30 亿</b>：成立 ⇒ 该链从「回避」升级为「负向主线」，并拖累电子；<b>止血 ⇒ 说明 A股 已提前定价，但外部仍跌 17%，不构成反转</b></div></td></tr>
    <tr><td><b>算力 / 数据中心</b></td><td><b class="dk-risk">政策风险显性化（由「分歧」转为「负向」）</b></td><td><div class="dr-wrap">MRVL -16.43%、NVDA -9.26%、ORCL -7%、CRWV -9%、NEBIUS -14%；A股 计算机 +13.99 亿（旧值）、56 条语料（利空型）</div></td><td><div class="dr-wrap"><b>看计算机 L4 能否守住</b>（唯一 L4）：<b>若今日资金转负，则「软件 / 信创承接硬件」的叙事作废</b>；<b class="dk-caution">注：信创 / 国产软件本身不受美国政策影响，是这条链里唯一可能「反向受益」的分支</b></div></td></tr>
    <tr><td><b>半导体设备 / 材料</b></td><td><b class="dk-caution">由「上行」下调为「观察」</b></td><td><div class="dr-wrap">A股 11-05 设备 +7.71% / +54.32 亿（streak 2）、材料 +6.01% / +20.38 亿；<b>但外部逻辑已由「扩产受益」变为「扩产被质疑」</b></div></td><td><div class="dr-wrap"><b class="dk-caution">看设备能否在低开后率先翻红</b>：<b>能 ⇒ 说明「政策只影响美国 capex、不影响中国扩产」的逻辑成立，可恢复首选；不能 ⇒ 昨日 +7.71% 定性为「一日游」</b>。<b class="dk-main">这是本档今日最重要的单点验证</b></div></td></tr>
    <tr><td><b>新能源 / 电力设备</b></td><td><b class="dk-up">上行（资金证据最硬 · 且与 AI 无关）</b></td><td><div class="dr-wrap">电力设备 +63.10 亿 / streak 4 / 分位 100；光伏 +32.36 亿 / +5.77%；电池 +26.43 亿；锂价 91,580 稳；政策：氢能试点 + 储能调研</div></td><td><div class="dr-wrap"><b class="dk-up">看 streak 能否到 5</b>（连续 5 日净流入）：<b>成立 ⇒ 从暗线升级为「全场唯一有连续性的方向」</b>；<b class="dk-caution">同时看是否出现「低开高走 + 放量」，这是避险资金落点的确认信号</b></div></td></tr>
    <tr><td><b>有色 / 贵金属</b></td><td><b class="dk-up">上行（金价新高驱动）</b></td><td><div class="dr-wrap">金 4,118.81 <b class="dk-up">+1.45%</b>（突破 4,100）、有色资金 <b>+18.62 亿</b>（暗线→<b>共振 A</b> · 24 条语料）；<b class="dk-caution">但 Vito 判据：「锡等 AI 后排金属已崩，看铜什么时候补跌」</b></div></td><td><div class="dr-wrap"><b class="dk-caution">这是本档新增的防御方向，但须严格区分金属</b>：<b>贵金属（金 / 银）跟避险，AI 后排金属（锡 / 铜 / 铝）跟需求</b>。<b class="dk-main">今日若铜补跌，则「衰退预期」启动，有色内部将剧烈分化 —— 此时只认黄金，不认工业金属</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">六条链的排序（本档结论）：电力设备 / 新能源 &gt; 有色（仅贵金属）&gt; 医药（防御）&gt; 半导体设备（观察）&gt; 存储（回避）&gt; 光模块 / 算力硬件（负向）</b>。<b class="dk-risk">与 11/05 收盘版相比，最大变化是「半导体设备」由第 1 位降至第 4 位、「有色贵金属」新增入榜</b>。<b class="dk-caution">排序依据仍是三项加权（资金连续性 + 政策共振 + 与外盘方向的相关性），但本次新增第四项：<b>「是否受美国 AI 政策变量影响」</b> —— 这是昨夜事件带来的框架升级</b>。
  </div>
</div>

"""
repl_between("<!-- 5.5 产业链 / 景气度 -->", "<!-- 6 新闻整合 + 7.1 -->", SEC55, tag="sec55")

# ═══════════ 6 新闻整合 ═══════════
SEC6 = """<!-- 6 新闻整合 + 7.1 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">6 · 新闻整合（公开源自动刷新 · <b class="dk-up">本版实到：11/06 08:40 抓取 <b>291</b> 条</b> · 宏观 37 / 科技 39 / 政策 31 / 产业 27 / 美股映射 3 / 持仓 1 · 窗口 = 11/05 + 11/06）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.62">
    <b class="dk-caution">① 口径（必读）</b>：本段由 <code>output/daily_news_2026-11-06.json</code> 驱动（<code>generated_at = 2026-11-06 08:40</code>，<b>291 条</b>，六源：东财全球 / 财经早餐 / 新浪全球 / 同花顺全球 / 富途全球 / 央视联播）；滚动池 <code>daily_news_window.json</code> 窗口切片 <b>589 条</b>（11/05 + 11/06）。<b class="dk-main">标签结构已由昨日的「政策 + 利率主导」转为「科技 39 + 宏观 37」双高</b> ⇒ <b>语料本身就说明今日是「外部事件驱动」的一天</b>；<b>投喂精选 0 件</b>（<code>feed/archive/2026-11-06/_index.json</code> 如实记录 <code>feed_count: 0</code>，无独立批次，<b>未伪造条目</b>）。<br>
    <b class="dk-main">② 今日语料的三条主线（按信息量排序）</b>：<b class="dk-risk">A. AI 崩塌的完整因果链</b>——〈11月6日投资避雷针：纳斯达克100指数收跌6.5% AI产业链遭重挫 英伟达跌超9%〉（08:35）、〈AI监管担忧引爆历史性抛售！纳指狂泻5.5% 中概股表现坚挺〉（07:27）、〈立马就拿数据中心「开刀」？「蓝潮」席卷美国 民主党高层接连发声〉（08:32）、〈谷歌官宣斥资170亿美元布局怀俄明数据中心〉（08:38）；<b class="dk-risk">B. 亚太连锁反应</b>——〈日经225指数跌超5% 较6月高点下跌20% 进入技术性熊市〉（08:13）、〈韩国交易所启动SIDECAR机制 暂停KOSPI程序性卖盘〉（08:36）、〈软银集团股价下跌幅度高达16%〉（08:29）、〈MSCI亚太指数下跌3%〉（08:31）；<b class="dk-up">C. 中国资产的反向证据</b>——〈在美上市中概股逆势走强 中国科技政策稳定预期形成支撑〉（08:19）、〈中信证券：利率拐点叠加资金回流，看好港股互联网修复行情〉（08:12）、〈华泰证券张继强：千亿元增量资金蓄势 稳市工具迈向长期制度安排〉（08:12）。<br>
    <b class="dk-caution">③ 需留意的负面 / 风险类信息（非投资建议，仅记录）</b>：〈对冲基金 VARA 在人工智能股票惨淡的 10 月暴跌 33%〉（07:37，说明杠杆资金已受重创、后续或有被动赎回）；〈辉瑞：血友病创新疗法在华获批新适应症〉（08:25，属个股级利好）；〈韩国 KOSPI 指数恢复交易 跌幅收窄至 6.8%〉（08:34，SIDECAR 解除但跌幅未修复）。<br>
    <b class="dk-main">④ 语料与资金的交叉验证</b>：科技 39 条 + 宏观 37 条合计占 26%，<b>而「产业」类仅 27 条</b> ⇒ <b class="dk-caution">今日是「宏观叙事日」而非「产业景气日」，这类日子的特征是：指数波动大、板块轮动快、个股 alpha 弱</b> ⇒ <b class="dk-main">本档据此不下「结构主线」的重注，只保留两条与事件无关的暗线（电力设备 / 贵金属）</b>。
  </div>
</div>

"""
repl_between("<!-- 6 新闻整合 + 7.1 -->",
             '<div class="dr-h" data-version="close-2215" data-review-date="2026-11-05" data-for-date="2026-11-06">7.1 · K3 产业信号验证',
             SEC6, tag="sec6")

SRC.write_text(html, encoding="utf-8-sig")
print(f"Part B done: {len(html)} chars")
