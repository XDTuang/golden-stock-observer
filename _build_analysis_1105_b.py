#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-05 盘前版 analysis.html · Part B：2 / 3 / 4 / 5 / 5.5 / 6 计数
注：3 段整体重写 ⇒ 之后必须重跑 review/build_us_medical.py 重注 US-MEDICAL 块
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
    assert c == expect, f"[{tag}] 出现 {c} 次，期望 {expect}: {old[:70]}"
    html = html.replace(old, new)


# ═══════════════ 2 亚太与商品利率 ═══════════════
SEC2 = """<!-- 2 日韩股市与商品利率 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">2 · 亚太与商品利率（<b class="dk-risk">日韩 = 11/05 早盘实时（08:47 首取）</b> · 港股 11/04 收盘 · 商品 11/05 早间 · 美债 <b class="dk-caution">11/03（本机长期缺口，滞后 1 日）</b> · <b class="dk-risk">KOSPI -3.32% 与日经 +0.51% 方向相反</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 日韩早盘（<code>market.json.asia</code> · 抓取 2026-11-05 08:47 · 韩国 09:47 KST 实时 / 无延迟）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>最新</th><th>涨跌幅</th><th>时点</th><th>读法（对 A股 11/05 的直接含义）</th></tr></thead><tbody>
    <tr><td><b>日经 225</b></td><td>62,502.89</td><td><b class="dk-up">+0.51%</b></td><td>11/05 早盘</td><td><div class="dr-wrap"><b class="dk-up">逆势收红</b> ⇒ <b class="dk-main">「AI 硬件杀跌」在亚太没有形成全域 risk-off，日本（半导体设备权重高但内需/金融权重更大）承接住了</b>；对 A股 的启示是<b>「指数可守、链条可杀」</b>的同一形态可复制</div></td></tr>
    <tr><td><b>韩国综合（KOSPI）</b></td><td>5,495.14</td><td><b class="dk-risk">-3.32%</b></td><td>11/05 早盘</td><td><div class="dr-wrap"><b class="dk-risk">-3.32% 是本周最大单日跌幅</b>，且<b>发生在美股指数大涨的次日</b> ⇒ <b class="dk-main">韩股定价的是「半导体原产地利空」，不是「全球风险偏好」</b>。A股 电子链与之相关性高于日经</div></td></tr>
    <tr><td><b>SK하이닉스</b>（000660）</td><td>1,297,000</td><td><b class="dk-risk">-7.09%</b></td><td>09:47 KST</td><td><div class="dr-wrap"><b class="dk-risk">HBM 龙头单日 -7.09%，与美股 MU -7.00% / SNDK -7.91% 精确同幅</b> ⇒ <b class="dk-main">全球存储链在同一时点被同一逻辑重定价（数据中心 capex 下修 + 信贷约束），这是本档对 A股 存储 / 半导体最直接的映射证据</b></div></td></tr>
    <tr><td><b>삼성전자</b>（005930）</td><td>206,500</td><td><b class="dk-risk">-5.28%</b></td><td>09:47 KST</td><td><div class="dr-wrap">存储 + 代工双业务，跌幅小于 SK하이닉스（-5.28% vs -7.09%）⇒ <b class="dk-caution">市场区分「纯 HBM 弹性」与「综合半导体」，杀的是<b>弹性最大的一端</b></b>。对应 A股：存储模组 / HBM 概念跌幅将大于半导体设备</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.6;margin-top:6px"><b class="dk-caution">口径：</b>日韩为 11/05 早盘实时（非收盘），不可与 A股 11/04 收盘价做「同日对比」；韩国 09:00 KST 开盘（= 北京 08:00），本档 08:47 抓取时已运行 47 分钟，<b class="dk-main">足以代表「开盘定价」而非「盘中情绪」</b>。</div>

  <div class="dr-tag" style="margin-top:10px">② 港股（11/04 收盘）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>指数</th><th>收盘</th><th>读法</th></tr></thead><tbody>
    <tr><td>恒生指数</td><td><b>23,919.50</b></td><td><div class="dr-wrap">与 A股 同步反弹，<b class="dk-caution">但港股对「关税撤销」的敏感度高于 A股</b>（直接受出口链与外资流影响）⇒ 今日若 A股 低开而港股相对抗跌，可视为「关税逻辑」在起作用</div></td></tr>
    <tr><td>恒生科技</td><td><b>3,936.02</b></td><td><div class="dr-wrap"><b class="dk-risk">恒科是本轮最直接的「AI 硬件 β」载体</b>（含中芯 / 华虹 / 舜宇等），今日开盘大概率同步承压；<b class="dk-main">观察恒科与恒指的背离幅度 = 市场对「硬件 vs 平台」的分歧强度</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">③ 商品与利率（<code>market.json.comm</code> · 商品 11/05 早间 / 美债 11/03）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>品种</th><th>最新</th><th>涨跌幅</th><th>日期</th><th>读法</th></tr></thead><tbody>
    <tr><td>现货黄金</td><td>4,039.86</td><td><b class="dk-up">+2.79%</b></td><td>11/05</td><td><div class="dr-wrap"><b class="dk-up">与美股同涨</b> ⇒ 驱动为「流动性 / 政策不确定性」而非单纯避险；<b class="dk-caution">金与股同涨的行情对流动性边际变化极敏感</b></div></td></tr>
    <tr><td>COMEX 黄金</td><td>4,051.61</td><td><b class="dk-up">+2.82%</b></td><td>11/05</td><td><div class="dr-wrap">期货略高于现货 11.75 美元，<b>期现价差正常，无挤仓特征</b></div></td></tr>
    <tr><td>WTI 原油</td><td>92.02</td><td><b class="dk-risk">-4.23%</b></td><td>11/05</td><td><div class="dr-wrap"><b class="dk-risk">新闻口径「重挫逾 8%」，本机早间为 -4.23%（口径差：本机为亚盘早段连续报价）</b>。<b class="dk-main">对 A股 的结构含义：交运 / 化工 / 电力成本端利好，石油石化 / 煤炭 / 油服利空 —— 与 11/04 的资金列（石油石化 -11.53 亿）方向一致</b></div></td></tr>
    <tr><td>布伦特</td><td>98.87</td><td><b class="dk-risk">-4.56%</b></td><td>11/05</td><td><div class="dr-wrap">跌破 100 关口 ⇒ <b class="dk-caution">「伊朗战争溢价」开始被计价回吐</b>，若中东局势同步降温，油价中枢将系统性下移</div></td></tr>
    <tr><td>10Y 美债</td><td>4.95%</td><td>—</td><td><b class="dk-caution">11/03（滞后）</b></td><td><div class="dr-wrap"><b class="dk-risk">本机长期缺口（数据源自 10/23 起未推进）</b>，<b>不作为今日结论依据</b>，仅列示；<b class="dk-caution">10Y 仍在 4.95% 的高位，折现率约束未解除</b></div></td></tr>
    <tr><td>30Y 美债</td><td>5.32%</td><td>—</td><td><b class="dk-caution">11/03（滞后）</b></td><td><div class="dr-wrap">同口径滞后；<b class="dk-main">长端 5.3% 是「数据中心 capex 融资成本」的直接分母 —— 这也是隔夜 AI 硬件被杀的核心变量之一（信贷市场制约 capex）</b></div></td></tr>
    <tr><td>人民币中间价</td><td>6.718</td><td>—</td><td>11/04</td><td><div class="dr-wrap">汇率稳定，<b>不构成额外扰动</b></div></td></tr>
    <tr><td>碳酸锂（广期所主连）</td><td>86,460</td><td>—</td><td>11/04</td><td><div class="dr-wrap">锂价低位徘徊，<b>新能源链成本端无压力、但价格弹性缺失</b>；与「电力设备为暗线 C」的资金面一致</div></td></tr>
  </tbody></table></div>
</div>

"""

# ═══════════════ 3 隔夜美股复盘 ═══════════════
SEC3 = """<!-- 3 隔夜美股复盘 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">3 · 隔夜美股复盘（<b class="dk-up">最近一个完整收盘 = 11/04〔结算价〕</b> · <b class="dk-risk">指数与产业链方向完全相反：道 +3.03% / 存储 0-4 / 光模块 0-3</b> · 2026 年内最典型的「指数与结构分裂」）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 双日表（<code>market.json.us_kline</code> · latest = 2026-11-04 · prev = 2026-11-03 · 23/23 已滚动到位）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>11/04 收盘</th><th>涨跌幅</th><th>11/03 收盘</th><th>读法</th></tr></thead><tbody>
    <tr><td><b>道琼斯</b></td><td>53,356.12</td><td><b class="dk-up">+3.03%</b></td><td>51,786.72</td><td><div class="dr-wrap"><b class="dk-up">单日 +3.03%（+1,569 点），道指史上罕见量级</b> ⇒ 驱动 = <b>消费 / 金融 / 传统权重</b>（关税撤销 + 消费刺激预期），<b>与科技无关</b></div></td></tr>
    <tr><td><b>标普 500</b></td><td>7,688.62</td><td><b class="dk-up">+1.58%</b></td><td>7,568.92</td><td><div class="dr-wrap">涨幅仅为道指的 52% ⇒ <b class="dk-caution">权重结构差异极大，说明「涨的是价值、跌的是成长」</b></div></td></tr>
    <tr><td><b>纳斯达克</b></td><td>25,736.51</td><td><b class="dk-up">+1.44%</b></td><td>25,372.01</td><td><div class="dr-wrap"><b class="dk-main">纳指仍收红，但成分内部剧烈撕裂</b>：软件 / 平台 / 消费互联网上涨，<b>半导体与 AI 硬件全线重挫</b>（见 ②③）⇒ <b>「纳指涨」不能代表「科技链涨」，这是本档最重要的口径纠偏</b></div></td></tr>
    <tr><td>SK하이닉스 ADR</td><td>143.07</td><td><b class="dk-risk">-5.12%</b></td><td>150.79</td><td><div class="dr-wrap">ADR 跌幅（-5.12%）小于韩股本地（-7.09%，11/05 09:47）⇒ <b class="dk-risk">韩股本地在隔夜后继续补跌，说明「亚洲时段仍在定价」</b>，A股 今日承接的是「第二轮」而非「首轮」</div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">② 存储四线（<b class="dk-risk">0 / 4 全黑</b> · 均值 <span class="dk-dn">-6.70%</span> · 前一日 4/4 均值 +3.01%）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>11/04 收盘</th><th>涨跌幅</th><th>11/03 收盘</th><th>读法</th></tr></thead><tbody>
    <tr><td>SNDK 闪迪</td><td>1,037.40</td><td><b class="dk-risk">-7.91%</b></td><td>1,126.52</td><td><div class="dr-wrap"><b class="dk-risk">四线中最弱</b>，NAND 弹性最大；新闻口径盘中一度跌近 10%</div></td></tr>
    <tr><td>MU 美光</td><td>795.23</td><td><b class="dk-risk">-7.00%</b></td><td>855.10</td><td><div class="dr-wrap">DRAM / HBM 龙头，<b>与 SK하이닉스 -7.09% 精确同幅</b> ⇒ <b class="dk-main">存储链的定价已全球化同步，A股 存储标的今日无「独立行情」空间</b></div></td></tr>
    <tr><td>WDC 西部数据</td><td>323.83</td><td><b class="dk-risk">-6.77%</b></td><td>347.35</td><td><div class="dr-wrap">HDD / NAND，跌幅居中；<b class="dk-caution">10/23 曾因「营收 +55% 但指引不及」盘后 -7%~-8%，本次为第二次预期差叠加</b></div></td></tr>
    <tr><td>SKHY（ADR）</td><td>143.07</td><td><b class="dk-risk">-5.12%</b></td><td>150.79</td><td><div class="dr-wrap">跌幅最小，<b>但韩股本地 11/05 已补跌至 -7.09%</b> ⇒ <b class="dk-risk">ADR 的「抗跌」是时区差造成的假象</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">③ 光模块 / 光互连（<b class="dk-risk">0 / 3 全黑</b> · 均值 <span class="dk-dn">-7.06%</span>）与 AI 算力主链</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>11/04 收盘</th><th>涨跌幅</th><th>关键事实</th></tr></thead><tbody>
    <tr><td>LITE Lumentum</td><td>626.75</td><td><b class="dk-risk">-7.85%</b></td><td><div class="dr-wrap"><b class="dk-risk">光模块三线最弱</b>，新闻口径盘中跌超 11%</div></td></tr>
    <tr><td>AAOI 应用光电</td><td>59.27</td><td><b class="dk-risk">-7.35%</b></td><td><div class="dr-wrap">高 β 小市值，跌幅跟随 LITE</div></td></tr>
    <tr><td>COHR Coherent</td><td>195.09</td><td><b class="dk-risk">-5.98%</b></td><td><div class="dr-wrap"><b class="dk-main">同日盘后发布财报：Q1 营收创纪录、同比 +50%、数据中心业务 +79%、下季指引延续高增、并给出中长期路线图 —— 股价仍收跌 5.98%</b>。⇒ <b class="dk-risk">这是教科书级的「业绩超预期 + 估值下修」组合，证明本轮杀的是折现率与 capex 预期，不是订单</b></div></td></tr>
    <tr><td>MRVL 迈威尔</td><td>159.80</td><td><b class="dk-risk">-7.08%</b></td><td><div class="dr-wrap">定制 ASIC / 数据中心互连，<b>跌幅与存储同幅</b> ⇒ 说明「数据中心资本开支」是全链共同分母</div></td></tr>
    <tr><td>NVDA 英伟达</td><td>200.13</td><td><b class="dk-risk">-3.17%</b></td><td><div class="dr-wrap"><b class="dk-main">龙头跌幅仅为链内一半（-3.17% vs -7%）</b> ⇒ 资金「卖弹性、留龙头」，<b>这是「排序式减仓」而非「清仓式撤退」</b>；对 A股 的映射：算力主设备 / 服务器跌幅应小于存储 / 光模块</div></td></tr>
    <tr><td>TSLA 特斯拉</td><td>385.19</td><td><b class="dk-risk">-3.34%</b></td><td><div class="dr-wrap">非核心链，跌幅与 NVDA 同级，<b>说明抛压不是「AI 主题」，而是「高估值成长」</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">④ 驱动归因（本段结论）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">一次政策事件，两条相反的定价链</b>：<br>
    <b class="dk-up">链条一（利多，已被交易）</b>：民主党中期选举「蓝色浪潮」落槌 ⇒ ① 众议院民主党领袖杰弗里斯表态<b>推动撤销特朗普关税、结束伊朗战争</b> ⇒ <b>WTI -4.23%（新闻口径 -8%）</b>；② 关税撤销利多进口成本 ⇒ <b>苹果 / 亚马逊等消费与平台股飙升</b>；③ 监管预期改善 ⇒ 软件 / 金融 / 传统权重（道指 +3.03%）。<br>
    <b class="dk-risk">链条二（利空，正在被交易）</b>：民主党对数据中心的态度 ⇒ 审批放缓、并网排队延长、水与征地成本上行 ⇒ <b>北美数据中心 capex 预期下修</b>（第三方测算：capex 总额可能上升 10%~20%、接电推迟 12–24 个月、项目 IRR 由 12%~14% 降至 9%~11%）⇒ <b>AI 硬件全链 de-rating</b>。<br>
    <b class="dk-caution">⇒ 两链的交点：<b>「资本开支下降 + 自由现金流改善」的 M7 逻辑（利多巨头）与「订单增速下修」的供应链逻辑（利空硬件）同时成立</b>。这就是为什么「纳指涨 1.44% 而 MRVL 跌 7.08%」可以并存。对 A股 而言，<b class="dk-risk">我们处在链条二的接收端，链条一的受益方（平台 / 消费）在 A股 缺乏对应标的</b>。
    <br><b class="dk-caution">口径声明：</b>以上均为 <b>11/04 完整收盘价〔结算价〕</b>，非盘中快照；盘后事件（COHR 财报）已标注为「盘后」。
  </div>
</div>

"""

# ═══════════════ 4 重点宏观 ═══════════════
SEC4 = """<!-- 4 重点宏观 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">4 · 重点宏观（<b class="dk-data">日历轨为准</b> · <code>output/daily_macro_latest.json</code> · <code>us.calendar.as_of = 2026-11-05 08:47</code> · <b class="dk-risk">今日事件 = 美国中期选举结果消化</b> · 美国 9 月 CPI <b class="dk-risk">3.7%</b> / 核心 2.6% · 中国 10 月 PMI <b class="dk-risk">49.3 / 49.7 双收缩</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 今日事件（2026-11-05）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>事件</th><th>读数 / 内容</th><th>对今日 A股 的传导</th></tr></thead><tbody>
    <tr><td><b>美国中期选举（11/04 投票 · 11/05 结果消化）</b></td><td>民主党「蓝色浪潮」；众议院民主党领袖杰弗里斯称将推动<b>撤销特朗普关税</b>、<b>结束伊朗战争</b></td><td><div class="dr-wrap"><b class="dk-caution">双刃</b>：关税撤销利多出口链 / 消费（但需立法、时间以季度计）；<b class="dk-risk">数据中心监管收紧利空 AI 硬件（当日生效于股价）</b>。<b class="dk-main">市场选择「先把利空交易完、把利多留给未来」</b></div></td></tr>
    <tr><td><b>国际油价</b></td><td>WTI 92.02 <b class="dk-risk">-4.23%</b>（新闻口径 -8%）· 布伦特 98.87 -4.56%（11/05 早间）</td><td><div class="dr-wrap">利多：交运 / 化工 / 电力 / 汽车使用端；利空：石油石化 / 煤炭 / 油服。<b class="dk-caution">注意：昨日资金列石油石化已为 -11.53 亿，属「顺势减配」而非新利空</b></div></td></tr>
    <tr><td><b>央行 SFISF 操作（11/03）</b></td><td>证券 / 基金 / 保险互换便利 <b>1,000 亿元</b>，费率招标 10bp，31 家机构投标 —— <b>自 2024/10 创设以来最大规模</b></td><td><div class="dr-wrap"><b class="dk-up">流动性托底的真实增量</b>，与「头部公募积极发声、千亿互换便利助力逆周期布局」形成闭环。⇒ <b class="dk-main">这是今日 A股 指数层面的主要缓冲，但它的作用对象是「宽基 / 权重」，不是「电子链」</b></div></td></tr>
    <tr><td><b>中国 10 月 PMI（10/31 公布）</b></td><td>制造业 <b class="dk-risk">49.3</b>（前值 49.9 附近）· 非制造业 <b class="dk-risk">49.7</b></td><td><div class="dr-wrap"><b class="dk-risk">双双低于 50 荣枯线</b> ⇒ 基本面侧无增量支撑，<b class="dk-caution">本轮行情只能由「资金 + 政策」驱动，不能由「盈利」驱动；一旦资金撤，缺乏基本面地板</b></div></td></tr>
    <tr><td><b>今日 / 今夜待公布</b></td><td>11/06（周五）美国 10 月非农就业；花旗策略师预期「不足以改变美联储政策方向」</td><td><div class="dr-wrap"><b class="dk-caution">非农是本档之后的第一个宏观检验点</b>，若强于预期 ⇒ 12 月加息压力回升 ⇒ 对高估值成长再压一层</div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">② 美国宏观日历轨（取最新公布值 · 注明公布日与龄期）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新值</th><th>预期 / 前值</th><th>公布日</th><th>龄期</th><th>读法</th></tr></thead><tbody>
    <tr><td>CPI 同比（9 月）</td><td><b class="dk-risk">3.7%</b></td><td>预期 3.6% / 前值 3.4%</td><td>2026-10-14</td><td>22 天</td><td><div class="dr-wrap"><b class="dk-risk">高于预期且较前值上行 0.3pct</b> ⇒ 通胀未继续回落，是「折现率约束」的源头</div></td></tr>
    <tr><td>核心 CPI 同比（9 月）</td><td><b>2.6%</b></td><td>预期 2.5% / 前值 2.4%</td><td>2026-10-14</td><td>22 天</td><td><div class="dr-wrap">同样高于预期与前值 ⇒ <b>核心通胀亦在反弹</b></div></td></tr>
    <tr><td>CPI 月率 / 核心月率</td><td>0.6% / 0.3%</td><td>预期 0.6% / 0.2%</td><td>2026-10-14</td><td>22 天</td><td><div class="dr-wrap">月率 0.6% 折年约 7%，<b class="dk-risk">远高于 2% 目标</b></div></td></tr>
    <tr><td>非农就业（9 月）</td><td><b class="dk-risk">2.9 万</b></td><td>预期 9.0 万 / 前值 13.3 万</td><td>2026-10-02</td><td>34 天</td><td><div class="dr-wrap"><b class="dk-main">大幅低于预期（仅为预期的 32%）</b> ⇒ 就业降温 vs 通胀反弹 = <b class="dk-caution">「滞胀式」组合，央行两难</b></div></td></tr>
    <tr><td>失业率（9 月）</td><td>4.2%</td><td>预期 4.1% / 前值 4.1%</td><td>2026-10-02</td><td>34 天</td><td><div class="dr-wrap">小幅上行，与弱非农一致</div></td></tr>
    <tr><td>ADP 就业（10 月）</td><td><b class="dk-up">8.6 万</b></td><td>预期 6.5 万 / 前值 9.0 万</td><td>2026-11-04</td><td>1 天</td><td><div class="dr-wrap"><b class="dk-caution">大幅高于预期</b> ⇒ 与非农 2.9 万形成矛盾，<b>数据噪音大，不宜作为方向依据</b></div></td></tr>
    <tr><td>核心 PCE 同比（9 月 · 新闻轨）</td><td><b class="dk-risk">3.1%</b></td><td>—</td><td>2026-10-30（财经早餐引述）</td><td>6 天</td><td><div class="dr-wrap"><b class="dk-caution">新闻轨与日历轨口径不同（PCE vs CPI），且被同一则早餐同时提及「美联储 12 月或加息 25bp」</b> ⇒ <b>本档以日历轨 CPI 3.7% 为主口径，PCE 仅作参考</b></div></td></tr>
    <tr><td>政策利率</td><td>维持不变（10/28–10/29 会议）· 有效联邦基金利率 3.88%</td><td>—</td><td>2026-10-29</td><td>7 天</td><td><div class="dr-wrap"><b class="dk-risk">12 月加息预期仍在（新闻口径约 79%~90%）</b>；美联储主席沃什宣布明年起减少议息频次 ⇒ <b>政策不确定性上升</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">③ 中国宏观（日历轨）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新值</th><th>期次</th><th>读法</th></tr></thead><tbody>
    <tr><td>制造业 PMI</td><td><b class="dk-risk">49.3</b></td><td>2026 年 10 月</td><td><div class="dr-wrap"><b class="dk-risk">连续位于收缩区</b>，同比 +0.61% ⇒ 环比改善但绝对水平仍弱</div></td></tr>
    <tr><td>非制造业 PMI</td><td><b class="dk-risk">49.7</b></td><td>2026 年 10 月</td><td><div class="dr-wrap"><b class="dk-risk">跌破 50（同比 -0.80%）</b> ⇒ 服务业亦转弱，<b>「消费刺激预期」缺少国内数据支撑</b></div></td></tr>
    <tr><td>GDP 同比</td><td>4.6%</td><td>2026 年 1–3 季度</td><td><div class="dr-wrap">全年目标压力仍在，<b>政策必须继续宽松</b> ⇒ 与 SFISF 1,000 亿的方向一致</div></td></tr>
    <tr><td>CPI 同比</td><td>0.9%</td><td>2026 年 9 月</td><td><div class="dr-wrap">低通胀 ⇒ <b>货币空间充足，但也说明内需疲弱</b></div></td></tr>
    <tr><td>LPR（1Y / 5Y）</td><td>3.00% / 3.50%</td><td>2026-10-20</td><td><div class="dr-wrap">连续持稳，<b>降息预期尚未兑现</b></div></td></tr>
  </tbody></table></div>
</div>

"""

# ═══════════════ 5 重点科技 ═══════════════
SEC5 = """<!-- 5 重点科技 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">5 · 重点科技（对照 <b class="dk-risk">美股 11/04 完整收盘〔结算价〕</b> · 六条主线 · <b class="dk-risk">全链 de-rating：存储 -6.70% / 光模块 -7.06% / ASIC -7.08%</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>主线</th><th>外部读数（11/04 收盘 · 结算价）</th><th>A股 11/04 对应读数</th><th>今日（11/05）研判</th></tr></thead><tbody>
    <tr><td><b>① 存储 / HBM</b></td><td><b class="dk-risk">0 / 4</b>：MU <span class="dk-dn">-7.00%</span> · SNDK <span class="dk-dn">-7.91%</span> · WDC <span class="dk-dn">-6.77%</span> · SKHY <span class="dk-dn">-5.12%</span>（均值 -6.70%）</td><td>电子 +312.63 亿（半导体 +195.89 / 数字芯片设计 +82.47）· 存储模组为领涨分支</td><td><div class="dr-wrap"><b class="dk-risk">最确定的负向映射</b>：韩股 SK하이닉스 -7.09% 已在亚洲时段二次定价 ⇒ <b>A股 存储 / HBM 概念低开 3%~5% 属合理区间</b>。<b class="dk-caution">但中信证券同日观点「存储供不应求延续、关注长协与股东回报」+ 深圳存储五虎「净赚 397 亿 / 账上流出 212 亿」显示基本面未破</b> ⇒ <b>低开后的关键不是跌幅，而是「是否放量」</b></div></td></tr>
    <tr><td><b>② 光模块 / 光互连</b></td><td><b class="dk-risk">0 / 3</b>：LITE <span class="dk-dn">-7.85%</span> · AAOI <span class="dk-dn">-7.35%</span> · COHR <span class="dk-dn">-5.98%</span>（均值 -7.06%）</td><td>通信 +75.86 亿（通信设备 +76.94 / 网络设备 +57.38）</td><td><div class="dr-wrap"><b class="dk-risk">COHR 财报超预期（+50% / 数据中心 +79%）仍跌 5.98%，是「业绩无法对抗估值」的最强证据</b> ⇒ A股 光模块（中际 / 新易盛 / 天孚）今日<b>不具独立性</b>；<b class="dk-caution">但昨日通信资金刚转正（+75.86 亿），若今日低开后资金不再大幅流出，可视作「筹码未散」的观察点</b></div></td></tr>
    <tr><td><b>③ AI 算力 / ASIC</b></td><td>MRVL <span class="dk-dn">-7.08%</span> · NVDA <span class="dk-dn">-3.17%</span></td><td>计算机 +22.32 亿（共振 A）· 算力租赁 / 服务器分化</td><td><div class="dr-wrap"><b class="dk-main">龙头跌幅（NVDA -3.17%）仅为链内一半 ⇒ 资金「卖弹性、留龙头」</b>，映射到 A股：<b>服务器 / 算力硬件（龙头）跌幅应小于 ASIC 概念 / 小市值弹性标的</b></div></td></tr>
    <tr><td><b>④ 半导体设备 / 国产替代</b></td><td>无直接标的（费半代理缺失）· 间接：MRVL / NVDA 下跌</td><td>半导体 +195.89 亿（+7.40%）；新闻「国产半导体设备产业景气持续、部分公司新增订单」</td><td><div class="dr-wrap"><b class="dk-caution">逻辑对冲最强的一支</b>：海外 capex 下修 <b>利空全球设备</b>，但<b>国产替代是「份额逻辑」</b>，且昨日资金最集中。<b class="dk-main">若今日电子板块内部出现「设备抗跌、存储杀跌」的分化，即验证「国产替代 vs 海外周期」两条腿不同步</b></div></td></tr>
    <tr><td><b>⑤ PCB / 铜连接</b></td><td>间接（MRVL / 服务器链）</td><td>元件 +49.86 亿（+4.56%）；金钻起涨含澳弘电子 / 满坤科技</td><td><div class="dr-wrap"><b class="dk-risk">昨日最强的弹性分支，今日风险最高</b>：PCB 是本轮「AI 服务器 → 铜连接」叙事的直接受益者，<b>数据中心 capex 下修对其杀伤最直接</b></div></td></tr>
    <tr><td><b>⑥ 消费电子 / 苹果链</b></td><td>苹果受益「关税撤销 + 消费刺激」预期（新闻：苹果防御属性凸显）</td><td>电子内部消费电子分支（相对滞后）</td><td><div class="dr-wrap"><b class="dk-up">唯一可能逆势的方向</b>：<b>关税撤销 ⇒ iPhone 成本下行</b>（Vito 观点：成本下行利多 iPhone / 亚马逊）。<b class="dk-caution">但 A股 苹果链同时受「电子板块整体 β」压制，需观察「个股逆板块」的强度</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-main">科技段的一句话总结</b>：<b class="dk-risk">昨夜不是「科技股跌」，而是「AI 硬件的估值分母被政策改写」</b>。分母端的三件事同时发生 —— ① 数据中心审批与并网周期拉长（IRR 由 12%~14% 降至 9%~11%）；② 长端美债 5.32% 抬高融资成本；③ 信贷市场已在制约 capex。<b class="dk-caution">分子端（订单 / 财报）目前没有恶化证据（COHR +50%、中信看多存储），故本轮应定性为「估值杀」而非「景气杀」—— 这决定了它是「可修复的」，但修复需要新的催化，而不是时间</b>。
  </div>
</div>

"""

# ═══════════════ 5.5 产业链 / 景气度 ═══════════════
SEC55 = """<!-- 5.5 产业链 / 景气度 -->
<div class="dr-h" data-version="preopen-0840" data-review-date="2026-11-04" data-for-date="2026-11-05">5.5 · 产业链 / 景气度评估（六条链 · 每条含 <b>11/05 观察要点</b> · 基准 = A股 11/04 完整收盘 + 美股 11/04 完整收盘）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>产业链</th><th>景气读数（本档可得）</th><th>价格 / 资金</th><th>11/05 观察要点</th></tr></thead><tbody>
    <tr><td><b>AI 数据中心（北美链）</b></td><td><b class="dk-risk">预期下修</b>：审批 / 并网 / 征地三重摩擦，IRR 降至 9%~11%；信贷市场已在约束 capex</td><td>MRVL -7.08% · NVDA -3.17% · COHR -5.98%（财报超预期）</td><td><div class="dr-wrap"><b>① 是否出现「财报利好但股价跌」的扩散</b>（COHR 已示范）；<b>② A股 服务器 / 液冷 / 电源 是否跟随 ASIC 概念下跌</b>；③ 关注「高盛与阿波罗洽谈出售 SpaceX 约 400 亿美元芯片融资债务」进展 —— <b class="dk-caution">这是 AI 融资链（债券过剩）风险的直接观测点</b></div></td></tr>
    <tr><td><b>存储（DRAM / NAND / HBM）</b></td><td><b class="dk-caution">基本面仍紧、估值先杀</b>：中信「供不应求延续」；深圳存储五虎净赚 397 亿但经营现金流 -212 亿（利润锁在库存）</td><td>四线均值 -6.70%；韩股 SK -7.09%</td><td><div class="dr-wrap"><b>① A股 存储模组低开幅度是否 &gt; 5%</b>（超跌则存在错杀）；<b>② 长协价格与股东回报公告</b>是否跟进；<b>③ 库存 / 现金流质量</b> —— 「利润锁在仓库」是这一轮的隐性风险，若 Q4 价格转跌，存货减值会反噬</div></td></tr>
    <tr><td><b>光通信 / CPO</b></td><td><b class="dk-caution">需求侧最强（COHR 数据中心 +79%）</b>，估值侧最惨（-7.06%）</td><td>通信资金 +75.86 亿（昨日转正）</td><td><div class="dr-wrap"><b>① 光模块三线今日是否「低开高走」</b>（若走强 = 市场认可业绩）；<b>② 1.6T / CPO 订单口径的新增信息</b>；③ 与存储的分化幅度 —— <b>光通信有真实订单，存储有价格周期，两者不应同幅下跌</b></div></td></tr>
    <tr><td><b>半导体设备 / 国产替代</b></td><td><b class="dk-up">国内景气独立</b>：新闻「国产半导体设备产业景气持续、部分公司新增订单」；昨日细分 +195.89 亿</td><td>电子板块内最集中的资金分支</td><td><div class="dr-wrap"><b>① 设备是否「逆板块抗跌」</b> —— 这是今日电子内部最重要的分化信号；<b>② 新增订单 / 中标公告</b>；③ 与海外设备（应材 / 泛林，本机未覆盖）的方向差</div></td></tr>
    <tr><td><b>新能源（电力设备 / 锂电 / 光伏）</b></td><td><b class="dk-caution">叙事边际改善但基本面弱</b>：叙事侧 = 政策托底 + 兼具沪深300 与创业板权重属性；基本面 = PMI 双收缩、锂价 86,460 低位</td><td>电力设备 +45.56 亿（暗线 C）· 机械设备 +44.86 亿</td><td><div class="dr-wrap"><b>① 是否成为今日「避弹坑」</b>（AI 硬件杀跌时的资金替代方向，且指数权重属性使其具备护盘功能）；<b>② 光伏政策预期</b>（民主党放开光伏对中国企业实质影响有限，但情绪可炒）；③ 与白酒的强弱比较 —— <b class="dk-main">白酒是纯 300 属性（GJD 护盘），新能源是 300 + 创指双属性（弹性更大）</b></div></td></tr>
    <tr><td><b>消费 / 交运（油价与关税受益）</b></td><td><b class="dk-up">今日新增变量</b>：油价 -4.23%~-8%、关税撤销预期、消费刺激预期</td><td>食品饮料 -21.60 亿（双冷）· 交运 -11.67 亿（双冷）· 商贸零售 -2.84 亿</td><td><div class="dr-wrap"><b>① 交运（航空 / 航运 / 物流）对油价 -8% 的反应强度</b> —— 这是今日最「干净」的利多映射；<b>② 食品饮料 / 白酒是否承接护盘资金</b>；<b class="dk-caution">③ 注意两者在象限里都是「双冷」—— 意味着没有资金证据，只能当「避险切换」而非「趋势起点」</b></div></td></tr>
  </tbody></table></div>
</div>

"""

repl("<!-- 2 日韩股市与商品利率 -->", "<!-- 3 隔夜美股复盘 -->", SEC2, tag="sec2")
repl("<!-- 3 隔夜美股复盘 -->", "<!-- US-MEDICAL-BEGIN（由 review/build_us_medical.py 生成 · 勿手改） -->", SEC3, tag="sec3")
repl("<!-- 4 重点宏观 -->", "<!-- 5 重点科技 -->", SEC4, tag="sec4")
repl("<!-- 5 重点科技 -->", "<!-- 5.5 产业链 / 景气度 -->", SEC5, tag="sec5")
repl("<!-- 5.5 产业链 / 景气度 -->", "<!-- 6 新闻整合", SEC55, tag="sec55")

# ═══════════════ 6 段新闻计数刷新 ═══════════════
sub('<b class="dk-up">本版实到：11/04 22:02 抓取 308 条</b>',
    '<b class="dk-up">本版实到：11/05 08:47 抓取 285 条（当日）／ 2 日窗口 587 条</b>', tag="sec6-count")

SRC.write_text(html, encoding="utf-8-sig")
print(f"OK part B: {orig_len} -> {len(html)} chars")
