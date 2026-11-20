#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-20 盘前版 analysis.html 组装。
重写 0/0.5/2/3/4/5/5.5/6+7.1/7.3/7.4/8/9，保留数据驱动的 1/1.1/1.2/7.1b/7.2 与 US-MEDICAL 块。
数据日 2026-11-19（A股完整收盘 + 美股 11-19 完整收盘）；指引日 2026-11-20（周五）。"""
import io, re

P = 'data/daily_review/analysis.html'
s = io.open(P, encoding='utf-8-sig').read()

e = s.index('</style>') + len('</style>')
prefix = s[:e]

def block(a, b):
    i = s.index(a); j = s.index(b, i)
    return s[i:j]

sec1      = block('<!-- 1 昨日 A 股走势总结 -->', '<!-- 2 日韩股市与商品利率 -->')
med_start = s.rindex('<!--', 0, s.index('US-MEDICAL-BEGIN'))
med_end   = s.index('US-MEDICAL-END') + len('US-MEDICAL-END -->')
medical   = s[med_start:med_end]
st_start  = s.rindex('<!--', 0, s.index('SECTOR-TECH-BEGIN'))
st_end    = s.index('SECTOR-TECH-END') + len('SECTOR-TECH-END ═══ -->')
sector71b = s[st_start:st_end]
sec72     = block('<!-- 7.2 重点观测股 -->', '<!-- 7.3 次日开盘指引 -->')

V = 'data-version="preopen-0840" data-review-date="2026-11-19" data-for-date="2026-11-20"'

HEADER = '''<!--
  ═══════════════════════════════════════════════════════════════════
  每日复盘 · 2026-11-20（周五）盘前版 · 数据日 2026-11-19 · 指引日 2026-11-20（周五）
  ═══════════════════════════════════════════════════════════════════
  本版数据口径（逐项可核）：
    · A股    = 2026-11-19 完整收盘（结算价 · 上证 3,577.62 / 深成 10,583.20 / 创业板 2,293.34 / 科创50 1,270.78 / 北证50 798.64）
    · 美股   = 2026-11-19 完整收盘（北京 11/20 05:00 落定 · 道 49,097.06 / 标普 7,175.83 / 纳 23,879.20）
    · 亚太   = 2026-11-20 早盘实时（08:40 抓取 · 日经 56,795.51 / KOSPI 4,932.47）
    · 商品   = 2026-11-20 最新（金 3,688.07 / COMEX 3,688.82 / WTI 83.44 / 布伦特 92.97 / 碳酸锂 91,500〔11-19〕）
    · 美债   = 2026-11-18 结算（10Y 5.07% / 30Y 5.41%）
    · VIX    = 2026-11-18 CBOE 结算 24.56；11-19 盘中最高 28.75（新闻轨，结算值待发布）
    · 广度/情绪 = realtime.json 2026-11-19 22:18 收盘重算版（涨 538 / 跌 4,020 / 涨停 31 / 跌停 105 / 成交 10,770.2 亿 / 情绪 15）
  四象限以 output/cross_analysis.json（2026-11-20 08:45 盘前重算）现场现算为准：
    · 本版 共振 A = 1 / 背离 B = 6 / 暗线 C = 3 / 双冷 D = 21（斜杠简写 1/6/3/21）
    · 上一版（2026-11-20 00:15）为 1 / 1 / 3 / 26（斜杠简写 1/1/3/26）
    · 迁移主因 = 纯语料侧：31 席 flow_yi 逐席零变化（flow_date 同为 11-19），5 席「双冷→背离」
      全部来自 11-20 早间新闻池入库后 news_count 跨过 16 条/2 日门槛（有色 10→29 / 传媒 13→29 / 银行 3→17 / 非银 10→22 / 食品饮料 13→26），五席资金全为负。
  凡引用上一版的方向 / 开盘档 / 仓位 / 象限数字，一律标注「上一版」，不作为当前值。
  运维纪律（推送范围 / 授权 / 协作约定）不入本文件。
-->'''

NEW0 = '''<!-- 0 结论先行 --><div class="dr-h" ''' + V + '''>0 · 结论先行（速览卡 · <b>11/20 周五 盘前版</b> · 复盘日 <b>11/19（周四）</b> · A股 <b class="dk-up">11/19 完整收盘〔结算价〕</b> · 美股 <b class="dk-risk">11/19 完整收盘〔三大全跌超 2%〕</b> · 亚太 <b class="dk-risk">11/20 早盘实时</b> · 指引 <b>11/20（周五）</b>）</div>
<div class="dr-card" style="margin-top:4px" data-preopen="1" data-agent="preopen">
  <div class="dr-tag">① 一句话结论</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b class="dk-main">外生锚由「结构分化」全面转为「系统性杀跌」，且杀的正是 A股 昨日唯一强势的方向 —— 这是本档唯一需要记住的结论</b>：昨夜美股 <b class="dk-risk">道 49,097.06（-2.19%）/ 标普 7,175.83（-2.02%）/ 纳 23,879.20（-2.25%）</b>，<b>三大同跌超 2%、裂口收敛至 0.23pct，上一版的「1 红 2 绿、结构切换」解释已被彻底否定</b>；今晨亚太 <b class="dk-risk">日经 56,795.51（-4.46%）、KOSPI 4,932.47（-4.00%）</b>，<b class="dk-risk">SK 海力士 -6.51%、三星电子 -4.98%</b>。
    <br><b class="dk-risk">A股 自身的处境比昨日更差</b>：11/19 上证 <b class="dk-risk">3,577.62（-0.28%）</b>、深成 -0.71%、创业板 -0.79%，<b class="dk-risk">跌停 105 家（+43）、涨跌比 0.13、主力 -309.69 亿、成交 10,770.2 亿（-21.4%，11/14 以来最低）、情绪 15「恐慌下跌」</b>；<b>唯一亮点是科创50 <b class="dk-up">+1.83%</b>（日内反转 4.57%）</b>。
    <br><b class="dk-main">⇒ 逻辑闭环在此处断掉</b>：<b>昨夜被杀的正是半导体 / AI 硬件</b> —— <b class="dk-risk">AMD 遭做空重挫近 8%、NVDA -3.30%（连跌第五日）、MRVL -4.86%、美光 -2.10%、海力士 -6.51%</b>；<b class="dk-main">而 A股 昨日的强势恰恰只集中在这条线上（科创50 +1.83%、电子 +17.50 亿为 4 席净流入之首）</b>。<b class="dk-risk">⇒ 这不是「外部补跌、A股 抗跌」，而是「A股 唯一有支撑的柱子被外部抽走」</b>。
    <br><b class="dk-caution">唯一的对冲项是托底资金，但它只买宽基</b>：<b class="dk-up">国家队 ETF 11/19 净流入 +132.48 亿（本月最大单日）</b>、科创50 ETF +29.33 亿、深市月内回购超 200 亿元。<b class="dk-caution">⇒ 托底资金能守沪深300 / 科创50 的指数点位，但守不住个股的跌停家数（11/19 已有 105 家）</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 本版时间轴（只看已发生的）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b>11/19 09:30–15:00 A股</b>：上证开 <b class="dk-risk">3,583.12（-0.13%）</b> → 高 3,584.28 → 低 <b class="dk-risk">3,547.94（-1.11%）</b> → 收 <b class="dk-risk">3,577.62（-0.28%）</b>；科创50 由 <b class="dk-risk">-2.21%（1,220.38）</b>拉至 <b class="dk-up">+1.83%（1,270.78）</b>，振幅 4.57%；<b class="dk-risk">北证50 -3.99%（单边下行）</b>。<br>
    <b>11/19 全天</b>：涨 <b class="dk-risk">538</b> / 跌 <b class="dk-risk">4,020</b> / 平 47 · 涨跌比 <b class="dk-risk">0.13</b> · 涨停 31 / <b class="dk-risk">跌停 105</b> · 主力 <b class="dk-risk">-309.69 亿</b> · 两市成交 <b class="dk-risk">10,770.2 亿（-21.4%）</b> · 申万 31 席 <b class="dk-risk">-313.15 亿</b>（4 进 27 出）；结构 —— <b class="dk-up">电子 +17.50 亿（连 3 日为正但已缩 82.7%）</b>、<b class="dk-risk">计算机 -55.15 亿（最大单席流出）</b>、有色 -25.45、传媒 -23.71、银行 -19.29。<br>
    <b>11/19 美东（昨夜落定）</b>：道 <b class="dk-risk">49,097.06（-2.19%）</b> · 标普 <b class="dk-risk">7,175.83（-2.02%）</b> · 纳 <b class="dk-risk">23,879.20（-2.25%）</b> · <b class="dk-risk">VIX 盘中最高 28.75（3 月底以来最高）</b>；<b class="dk-risk">存储四线均值 -1.13%</b>（MU -2.10 / SNDK -2.71 / WDC +2.98 / SKHY -2.67）、<b class="dk-risk">光通信三线均值 -1.72%</b>（LITE -2.89 / COHR +0.99 / AAOI -3.26）、<b class="dk-risk">MRVL -4.86%、NVDA -3.30%、AMD 近 -8%</b>。<br>
    <b>11/20 早盘（08:40 抓取）</b>：日经 <b class="dk-risk">56,795.51（-4.46%）</b> · KOSPI <b class="dk-risk">4,932.47（-4.00%）</b> · <b class="dk-risk">海力士 1,106,000（-6.51%）、三星 187,100（-4.98%）</b>；<b class="dk-risk">软银 -14%、铠侠 -10%、爱德万 -8%（08:17）</b>。<br>
    <b>11/20 盘前事件</b>：<b class="dk-risk">美联储 12 月加息 25bp 概率升至 96.4%（06:05）；法巴上调至「连续三次加息」（07:29）；保尔森「不应在通胀问题上玩火」「10 月暂停只是调整节奏」（07:54–08:27）</b>；<b class="dk-risk">加州司法部询问英伟达是否误导投资者（06:33）</b>；<b class="dk-up">美光总裁：2027 年存储供需将比今年更紧张（08:25）</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 上一版（11/19 收盘版 22:15）给 11/20 的指引：可核项与已否证项</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b class="dk-risk">已否证（1 条，且是主判据）</b>：上一版写「<b>托底资金创本月最大单日（+132.48 亿）+ 科创50 完成日内反转 ⇒ 明日若跌停回落至 60 家以下、成交回到 13,000 亿以上，可把仓位恢复到 20%–25%</b>」，<b class="dk-risk">其隐含前提是「外部不再恶化」——今晨被否定</b>：<b>美股三大同跌超 2%、亚太 -4%、韩存储 -6.5%</b>，<b class="dk-risk">外生条件从「结构切换」变为「系统性杀跌」，故本版把仓位条件整体下移、不设「恢复到 20%」的路径</b>。<br>
    <b class="dk-up">已获前置确认（1 条）</b>：上一版写「<b>若成交再跌破 10,000 亿，任何集中赎回都会被放大，指数跌幅会从 -0.28% 跳到 -1.5% 量级</b>」，<b class="dk-up">✅ 判据有效</b>：11/19 成交已降至 10,770.2 亿（距 10,000 亿仅 7.7%），<b>本版把它从「风险假设」升级为「基准情形的一半」</b>。<br>
    <b class="dk-caution">待验证（3 条，今日盘中结算）</b>：<b>①</b> 方向「偏空」（本版维持）；<b>②</b> 开盘档「低开反弹」（<b class="dk-risk">本版下调为「低开偏弱」，见下</b>）；<b>③</b> 「Anthropic 首日破发 → 科创50 低开覆盖 +1.83%」（<b class="dk-caution">结果：Anthropic 上市未能缓解市场回调（08:26），KOSPI 仍跌 4.1%，<b class="dk-risk">该风险已兑现</b></b>）。<br>
    <b class="dk-main">⇒ 方法判据延续</b>：<b>开盘档只描述「开盘 30 分钟内的形态」，方向只描述「收盘位置」，两者不互相推导</b>（上一版已立，本版继续）。
  </div>
  <div class="dr-tag" style="margin-top:10px">④ 本版定调（跨页同值：老站 / V3 / feed_review 三处一致）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b class="dk-main">方向</b> <b class="dk-risk">偏空</b>（与上一版持平）· <b class="dk-main">置信度</b> <b class="dk-data">高</b>（上一版「中高」，<b>上调一档</b>）· <b class="dk-main">开盘</b> <b class="dk-risk">低开偏弱</b>（上一版「低开反弹」，<b>下调一档</b>）· <b class="dk-main">仓位</b> <b>10%–15%</b>（持平）· <b class="dk-main">风险</b> <b class="dk-risk">高</b>（持平）· <b class="dk-main">四象限</b> <b>1 / 6 / 3 / 21</b>（共振 1 / 背离 6 / 暗线 3 / 双冷 21；上一版 1 / 1 / 3 / 26）。<br>
    <b class="dk-main">四条理由</b>：<b>①</b> <b class="dk-risk">外部由「分化」转为「共振下跌」</b> —— 三大指数裂口由 1.53pct 收敛至 <b>0.23pct</b>，<b>「结构切换」解释失效，只剩「系统性风险偏好下修」一条解释</b>；<b>②</b> <b class="dk-risk">A股 昨日唯一强势（半导体 / 科创50）正是今夜被杀的方向</b> —— 判据 M11，<b>「唯一柱子被抽走」的结构比「普跌」更脆弱</b>；<b>③</b> <b class="dk-risk">量能已到 10,770 亿、跌停 105 家、情绪 15</b> —— 三项同时处于「恐慌档」，<b>开盘缺乏承接盘，低开后不易快速回补</b>；<b>④</b> <b class="dk-up">但托底资金 +132.48 亿（本月最大）与产业资本回购仍在</b> —— <b>这决定的是「跌幅上限」而非「方向」</b>，故仓位不给 0，维持 10%–15%。<br>
    <b class="dk-main">⇒ 一句话执行口径</b>：<b class="dk-caution">11/20 不看「能否收红」，只看两个数 —— 跌停能否从 105 回到 60 家以内、成交能否守住 10,000 亿；跌停回落且成交守住 → 仓位维持 10%–15% 做结构；跌停继续放大或成交跌破 10,000 亿 → 仓位压到 5%–10%，只留科创50 宽基</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">⑤ 11/20（周五）硬线</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b class="dk-main">上证 · 下方</b>：<b class="dk-risk">3,547.94</b>（11/19 日内低 · 第一支撑，破位即确认低开无法回补）→ <b class="dk-risk">3,505</b>（-2.0% 折算位）→ <b class="dk-risk">3,480</b>（11/14 低点区）。<br>
    <b class="dk-main">上证 · 上方</b>：<b class="dk-caution">3,584.28</b>（11/19 日内高 = 回补线，低开幅度 &gt;1.5% 时当日难以触及）→ <b>3,600</b>（整数关）→ <b>3,623.12</b>（11/16 日内高 · 真压力）。<br>
    <b class="dk-main">创业板</b>：下方 <b class="dk-risk">2,271.99</b>（11/19 低）→ 2,250；上方 <b class="dk-caution">2,315.78</b>（11/19 高）。<b class="dk-main">科创50</b>：下方 <b class="dk-risk">1,220.38</b>（11/19 最低，<b>今日若失守 = 昨日 +1.83% 反转完全作废</b>）· 上方 1,276.78。<br>
    <b class="dk-main">执行口径（if-then，四条）</b>：<b>①</b> <b>低开 -1.0%~-1.8%（3,513–3,542）且 10:00 前跌停 ≤80 家</b> → 属「外部一次性冲击」消化，<b class="dk-up">维持 10%–15%，只在科创50 宽基上加 2%–3%</b>；<b>②</b> <b class="dk-risk">跌停回升至 150 家以上或上证失守 3,547.94</b> → 恐慌二次扩散，<b class="dk-risk">仓位压至 5%，只留沪深300 / 科创50 宽基，个股清零</b>；<b>③</b> <b>科创50 失守 1,220.38</b> → 昨日反转作废，<b class="dk-risk">半导体链（含 PCB / 元件）一律减半，不做补仓</b>；<b>④</b> <b class="dk-caution">上证低开后 10:30 前回补至 3,570 以上且成交同比放大 ≥10%</b> → <b class="dk-up">「低开偏弱」改判「低开反弹」，仓位可回 15%</b>。<br>
    <b class="dk-main">跨市场确认（先看这个再看指数）</b>：<b>①</b> <b class="dk-risk">09:00 后日经 / KOSPI 若继续扩大跌幅至 -5% 以下，则 A股 低开幅度下沿（-1.8%）会被击穿</b>；<b>②</b> <b class="dk-up">若韩存储双雄盘中由 -6.5% 收窄至 -3% 以内，则半导体链的外部杀跌属「一次性定价」，A股 科创50 有反抽条件</b>；<b>③</b> <b>今夜 21:30 美国初请失业金（预期 19.7 / 前值 20.0）</b> —— <b>高于 20.0 万才是加息预期松动的第一根稻草，低于 19.7 万则分母端继续收紧</b>。
  </div>
</div>
'''

NEW05 = '''<!-- 0.5 深度判读 --><div class="dr-h" ''' + V + '''>0.5 · 深度判读（<b>三件事必须讲清</b>：上一版指引的「对与错」、今日「变了什么」、四象限的「迁移与成因」）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 剧本对账：11/19 收盘版 → 11/20 盘前（可核 / 待验证分开列）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>上一版给的判据</th><th>截至本档已知事实</th><th>判定</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">「托底资金 +132.48 亿 + 科创50 反转 ⇒ 跌停回落 + 成交回 13,000 亿则可恢复 20%–25% 仓位」</div></td><td><div class="dr-wrap">今晨美股三大同跌超 2%、亚太 <b class="dk-risk">-4.46% / -4.00%</b>、韩存储 <b class="dk-risk">-6.51%</b></div></td><td><div class="dr-wrap"><b class="dk-risk">❌ 前提被否证</b>（外生条件未满足，恢复路径取消）</div></td></tr>
    <tr><td><div class="dr-wrap">「成交跌破 10,000 亿则跌幅跳到 -1.5% 量级」</div></td><td><div class="dr-wrap">11/19 成交 <b>10,770.2 亿</b>（距 10,000 亿仅 7.7%）</div></td><td><div class="dr-wrap"><b class="dk-up">✅ 判据有效</b>（升级为基准情形的一半）</div></td></tr>
    <tr><td><div class="dr-wrap">「Anthropic 破发 → 科创50 低开覆盖 +1.83%」</div></td><td><div class="dr-wrap"><b>上市未能缓解市场回调（08:26）</b>，KOSPI 仍 -4.1%</div></td><td><div class="dr-wrap"><b class="dk-risk">⚠ 风险已兑现</b></div></td></tr>
    <tr><td><div class="dr-wrap">方向「偏空」</div></td><td><div class="dr-wrap">11/20 尚未开盘</div></td><td><div class="dr-wrap"><b class="dk-caution">待验证 · 本版维持</b></div></td></tr>
    <tr><td><div class="dr-wrap">开盘档「低开反弹」</div></td><td><div class="dr-wrap">本版据外部锚改为「<b class="dk-risk">低开偏弱</b>」</div></td><td><div class="dr-wrap"><b class="dk-risk">待验证 · 本版下调一档</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 1 条被否证、1 条判据有效、1 条风险兑现、2 条待验证</b>。<b class="dk-caution">必须说清的是：上一版的逻辑本身没有错，错在它的前提是「外部不再恶化」</b> —— <b>收盘版在 22:15 落盘时，美股 11/19 的美东时段才刚开始（21:30 开盘），纳指盘中一度 +2% 后转跌、费半回吐近 5% 涨幅（23:37–23:40）</b>，<b class="dk-main">这正是「盘前版与收盘版分工」的价值所在：收盘版只能给条件式，盘前版才拿到外生变量的完整答案</b>。<br>
    <b class="dk-risk">口径风险提醒</b>：<b>上一版「低开反弹」与本版「低开偏弱」差一档，属方向内的幅度修正，非方向反转</b> —— <b>两版方向均为「偏空」</b>；<b>差别只在「低开之后能不能回补」，本版认为回补概率低于 35%（上一版隐含约 55%）</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 今日到底变了什么（三件事，按对定价的权重排序）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:4px">
    <b class="dk-risk">① 外部锚从「结构分化」变成「系统性共振下跌」（权重最高）</b>：<b class="dk-risk">三大指数裂口由 1.53pct（纳 +0.42 / 道 -1.11）收敛至 0.23pct（纳 -2.25 / 道 -2.19）</b>，<b class="dk-main">⇒ 判据 M7（指数裂口 = 结构切换）本日失效，<b class="dk-risk">因为「裂口」这个前提不存在了</b>；同时 <b class="dk-risk">VIX 盘中冲至 28.75（3 月底以来最高）</b>，<b>与 11/18 的 24.56 相比单日跳升 4 点以上</b>，<b class="dk-risk">这是「全面避险」而非「结构切换」的直接读数</b></b>。<br>
    <b class="dk-risk">② A股 唯一强势方向被外部精准击穿（第二权重）</b>：<b>11/19 A股 的结构是「科创50 +1.83% vs 其余全绿」，资金也只在电子 +17.50 亿为正</b>；<b class="dk-risk">而今晨被杀的全部是这条链</b> —— <b class="dk-risk">AMD 近 -8%、NVDA -3.30%、MRVL -4.86%、美光 -2.10%、海力士 -6.51%、三星 -4.98%、软银 -14%、铠侠 -10%、爱德万 -8%</b>。<b class="dk-main">⇒ 判据 M11：<b class="dk-risk">「唯一柱子被抽走」的结构性脆弱，跌幅一定大于「普跌 + 普涨」的均衡结构</b>；<b>因为此时没有第二个方向可以对冲指数</b></b>。<br>
    <b class="dk-caution">③ 加息预期从「共识」升级为「定价」（第三权重）</b>：<b class="dk-risk">12 月加息 25bp 概率 96.4%（06:05，此前 95%）</b>、<b class="dk-risk">法巴上调至「连续三次加息、每次 25bp」（07:29）</b>、<b class="dk-risk">保尔森「不应在通胀问题上玩火」「10 月暂停只是调整节奏」（07:54–08:27）</b>、<b class="dk-caution">沃什「AI 可能带来繁荣但也需警惕风险」（08:35）</b>。<b class="dk-main">⇒ 这解释了「为什么跌的是高估值科技而不是全部」 —— 但本日连道指也跌 2.19%，<b class="dk-risk">说明已从「杀估值」扩散到「杀盈利预期」</b></b>。<br>
    <b class="dk-caution">口径披露（必须写）</b>：<code>daily_news_latest.json</code> 本档实到 <b>285 条</b>，<code>generated_at 08:42</code>，覆盖 <b>11/20 早间 06:00–08:42</b>；<b>四象限窗口 = 11/19 + 11/20</b>。<b class="dk-main">⇒ 与上一版（00:15）相比，<b>唯一新增的输入是 11/20 早间新闻池</b>，<b>资金侧零变化</b>（<code>flow_date</code> 同为 11-19）。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 四象限迁移（现场读 <code>cross_analysis.json</code> 08:45 版 · 四卡）</div>
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:6px">
    <div class="dr-note" style="font-size:12.5px;line-height:1.6;background:var(--bg-subtle);border-radius:8px;padding:9px 11px;margin:0">
      <b class="dk-up">共振 A = 1</b>（上一版 1，<b>席位不变</b>）<br><b>电子</b>：资金 <span class="dk-up">+17.50 亿</span> · 热度 <b>41.5 条/日</b>（上一版同席）· <b class="dk-risk">技术 L2 破位（电子板块 downtrend）</b><br><b class="dk-caution">⇒ 名称未变但质量下降：资金由 +99.84 亿（11/18）降至 +17.50 亿，<b>已连 3 日为正但量级缩 82.7%</b></b>
    </div>
    <div class="dr-note" style="font-size:12.5px;line-height:1.6;background:var(--bg-subtle);border-radius:8px;padding:9px 11px;margin:0">
      <b class="dk-caution">背离 B = 6</b>（上一版 1 → 本版 6，<b>+5 席全部由双冷升入</b>）<br><b>计算机</b>（77 条 / <span class="dk-risk">-55.15 亿</span>，<b>唯一存量席</b>）· 有色金属（29 / -25.45）· 传媒（29 / -23.71）· 银行（17 / -19.29）· 非银金融（22 / -9.21）· 食品饮料（26 / -4.96）—— <b class="dk-risk">6 席资金全部为负</b>
    </div>
    <div class="dr-note" style="font-size:12.5px;line-height:1.6;background:var(--bg-subtle);border-radius:8px;padding:9px 11px;margin:0">
      <b class="dk-data">暗线 C = 3</b>（上一版 3，<b>席位不变</b>）<br><b>美容护理</b>（<span class="dk-up">+1.92 亿</span> · 热度 0 · <b>连 20 日净流入</b>）· <b>综合</b>（+0.70 亿 · 热度 3.0）· <b>轻工制造</b>（+0.42 亿 · 热度 0）—— <b>三席均为小额流入，不构成主线</b>
    </div>
    <div class="dr-note" style="font-size:12.5px;line-height:1.6;background:var(--bg-subtle);border-radius:8px;padding:9px 11px;margin:0">
      <b class="dk-neutral">双冷 D = 21</b>（上一版 26，<b>减 5 席</b>）<br>机械设备 -31.98 · 医药生物 -28.64 · 电力设备 -27.89 · 基础化工 -19.17 · 国防军工 -15.26 · 通信 -6.80 · 汽车 -8.80 …（<b>21 席全部为资金净流出</b>）
    </div>
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:8px">
    <b class="dk-main">迁移主因（必须与上一版区分，不得照抄）：<b class="dk-risk">本版迁移 100% 来自语料侧，资金侧零变化</b></b> —— <b>31 席 <code>flow_yi</code> 逐席比对，变化数 = 0</b>（<code>flow_date</code> 两版同为 11-19），<b>唯一变化的是 <code>news_count</code></b>：有色 10→29、传媒 13→29、银行 3→17、非银 10→22、食品饮料 13→26。<b class="dk-main">⇒ 5 席「双冷 → 背离」全部是「11/20 早间新闻池入库后跨过 16 条/2 日门槛」的结果，不是因为有钱进来</b>。<br>
    <b class="dk-caution">性质必须写清</b>：<b>背离 B = 「有热度无资金」</b>，<b>6 席资金全为负，属「讨论度上升但资金在撤」的分歧加剧组合，不是机会增加</b>；<b class="dk-main">且本日它们的讨论升温题材多为「下跌归因」（有色大跌 / 银行息差 / 食品饮料防御讨论），<b class="dk-risk">在系统性下跌日，这类讨论升温本身就是风险信号而非资金信号</b></b>。<br>
    <b class="dk-data">成因链（可核）</b>：<b>①</b> 上一版 00:15 重算时，11/20 早间新闻尚未入库，<b>五席 news_count 停在 3–13 条</b>；<b>②</b> 本档 08:45 重算时，11/20 早间 285 条已入库，<b>五席 news_count 升至 17–29 条，全部跨过 16 条门槛</b>；<b>③</b> 电子 83 条（41.5/日）本身远超门槛，<b>故席位不变</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">④ 本版新增的方法论判据（写入 7.4，供次日验证）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:4px">
    <b class="dk-data">判据 M10</b>：<b>外部跌幅 → A股 开盘的非线性折算</b> —— 当美股三大同跌 ≥2% <b>且</b> 亚太同步跌 ≥4% 时，A股 开盘幅度约为外部跌幅的 <b>0.55–0.75 倍</b>（常规系数 0.4）；<b>放大原因 = A股 前一日已处恐慌档（情绪 ≤20）+ 量能萎缩</b>。<b>本日折算：外部均值 -2.15%、亚太 -4.23% ⇒ 上证低开 -1.0%~-1.8%（3,513–3,542）</b>。<br>
    <b class="dk-data">判据 M11</b>：<b>「唯一强势方向被击穿」= 指数级补跌</b> —— 当 A股 前一日的强势只集中于单一板块（本例：科创50 +1.83%，其余主要指数全绿），<b>而该板块恰是外部隔夜被杀的方向</b>，则<b>当日该板块跌幅中位数大于指数，且指数无法靠「结构性对冲」收红</b>。<b>操作含义 = 不因「昨日该板块强」而在今日补仓</b>。<br>
    <b class="dk-data">判据 M12</b>：<b>托底资金只守宽基、不守个股</b> —— 国家队 ETF 单日净流入 &gt;100 亿（本例 +132.48 亿）时，<b>次日若外生冲击 ≥2%，托底资金通常只承接沪深300 / 科创50 等宽基，个股跌停家数易破 100</b>；<b>故「托底资金大额流入」只能用于判断跌幅上限，不能用于判断方向或个股安全</b>。
  </div>
</div>
'''

NEW2 = '''<!-- 2 日韩股市与商品利率 --><div class="dr-h" ''' + V + '''>2 · 亚太与商品利率（日韩 = <b class="dk-risk">11/20 早盘实时 08:40</b> · 商品 = <b class="dk-data">11/20 最新</b> · 美债 = <b class="dk-caution">11/18 结算</b> · 港股 = 11/19 收盘）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 亚太早盘（11/20 · 由连涨转为暴跌，单日反转）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>市场 / 标的</th><th>11/20 早盘</th><th>涨跌</th><th>11/19 收盘（对照）</th><th>对 A 股的意义</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">日经 225</div></td><td>56,795.51</td><td><b class="dk-risk">-4.46%</b></td><td>59,443.99（+0.71%）</td><td><div class="dr-wrap"><b class="dk-risk">单日反转 5.17pct</b>；期货盘前已 -3.63%（07:46），现货跌幅持续扩大（-2% → -3% → -4%）</div></td></tr>
    <tr><td><div class="dr-wrap">韩国 KOSPI</div></td><td>4,932.47</td><td><b class="dk-risk">-4.00%</b></td><td>5,114.20（+0.92%）</td><td><div class="dr-wrap"><b class="dk-risk">开盘即 -4.08%</b>（08:01）· <b>单日反转 4.92pct</b> —— 昨日「存储双雄主导的新高」全部回吐</div></td></tr>
    <tr><td><div class="dr-wrap">SK 海力士</div></td><td>1,106,000</td><td><b class="dk-risk">-6.51%</b></td><td>1,190,000（+4.02%）</td><td><div class="dr-wrap"><b class="dk-risk">两日累计由 +10.3% 转为 +3.1%</b>；<code>traded_at 09:39:21+09:00</code>（本次读数有效）</div></td></tr>
    <tr><td><div class="dr-wrap">三星电子</div></td><td>187,100</td><td><b class="dk-risk">-4.98%</b></td><td>197,400（+1.39%）</td><td><div class="dr-wrap"><b class="dk-risk">跌破 19 万整数关</b>；同日宣布存储 / 移动业务新负责人（08:20）</div></td></tr>
    <tr><td><div class="dr-wrap">恒生指数（11/19 收盘）</div></td><td>22,841.62</td><td><b class="dk-risk">-1.95%</b></td><td>—</td><td><div class="dr-wrap">延续弱势，<b>与亚太今晨方向一致</b></div></td></tr>
    <tr><td><div class="dr-wrap">恒生科技（11/19 收盘）</div></td><td>3,649.14</td><td><b class="dk-risk">-2.33%</b></td><td>—</td><td><div class="dr-wrap"><b class="dk-risk">阿里业绩超预期（18:09）未能带动</b> → 港股「叙事外溢」证伪</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 本段要点：昨日的「亚太领涨」在 12 小时内变为「亚太领跌」，且跌幅集中在半导体</b>。<b class="dk-risk">软银 -14%、铠侠 -10%、爱德万 -8%（08:17）</b> —— <b class="dk-risk">铠侠作为 NAND 原厂跌 10%，直接对应 A股 存储链（德明利 / 香农芯创 / 长鑫映射）与半导体设备（北方华创 / 中微）</b>。<br>
    <b class="dk-main">⇒ 判读：<b class="dk-risk">这不是「亚太风险偏好下降」，而是「全球半导体链集中出清」</b></b> —— <b>如果是前者，日经与 KOSPI 的跌幅应与恒指（-2% 级别）接近；实际是 -4.46% / -4.00%，即 2 倍于恒指</b>，<b class="dk-main">⇒ 说明杀跌有明确的行业指向（存储 / 半导体设备 / AI 硬件），而非全域风险偏好</b>。<b class="dk-caution">对 A股 的含义：半导体链今日补跌是「确定性事件」，需防的是它拖累指数而非自身</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 商品 / 利率 / 汇率（口径：11-20 最新或 11-18 结算）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>品种</th><th>数值</th><th>涨跌</th><th>数据日</th><th>读数</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">现货黄金</div></td><td>3,688.07</td><td><b class="dk-risk">-0.98%</b></td><td>11-20</td><td><div class="dr-wrap"><b class="dk-risk">连续第四日下跌</b>；较 11/12 的 3,890 上方累计 -5.2%</div></td></tr>
    <tr><td><div class="dr-wrap">COMEX 黄金</div></td><td>3,688.82</td><td><b class="dk-risk">-1.42%</b></td><td>11-20</td><td><div class="dr-wrap">跌幅大于现货，<b>期货端定价更悲观</b></div></td></tr>
    <tr><td><div class="dr-wrap">WTI 原油</div></td><td>83.44</td><td><b class="dk-up">+1.37%</b></td><td>11-20</td><td><div class="dr-wrap"><b class="dk-up">连续第三日反弹</b>（81.5 → 83.4），<b>与贵金属反向</b></div></td></tr>
    <tr><td><div class="dr-wrap">布伦特原油</div></td><td>92.97</td><td><b class="dk-up">+1.10%</b></td><td>11-20</td><td><div class="dr-wrap">同向反弹，<b>能源与贵金属的分叉已持续 3 日</b></div></td></tr>
    <tr><td><div class="dr-wrap">10Y 美债</div></td><td><b class="dk-risk">5.07%</b></td><td><b class="dk-neutral">—</b></td><td>11-18</td><td><div class="dr-wrap"><b class="dk-caution">龄期 2 日未更新</b>；<b>在「三次加息」预期下仍未上破 5.20%</b></div></td></tr>
    <tr><td><div class="dr-wrap">30Y 美债</div></td><td><b class="dk-risk">5.41%</b></td><td><b class="dk-neutral">—</b></td><td>11-18</td><td><div class="dr-wrap">曲线陡峭（30Y-10Y = 34bp），长端定价「财政 + 通胀」</div></td></tr>
    <tr><td><div class="dr-wrap">碳酸锂（广期所主连）</div></td><td>91,500</td><td><b class="dk-neutral">—</b></td><td>11-19</td><td><div class="dr-wrap"><b>连续第四日持平</b>，锂链无新驱动</div></td></tr>
    <tr><td><div class="dr-wrap">VIX</div></td><td><b class="dk-risk">24.56</b> / 盘中 28.75</td><td><b class="dk-caution">11-18 结算</b></td><td>11-18 / 11-19</td><td><div class="dr-wrap"><b class="dk-risk">11/19 盘中冲至 28.75（3 月底以来最高）</b>，结算值待 CBOE 发布</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 三个读数</b>：<b>①</b> <b class="dk-risk">贵金属连跌四日（金 -0.98% / COMEX -1.42%）而原油连涨三日（+1.37%）</b> —— <b class="dk-main">这是本轮最重要的一处结构变化：<b class="dk-caution">「金跌油涨」= 实际利率上行 + 供给端扰动，而非「通缩」</b>；<b class="dk-risk">与 11/19 的「金铜油同跌」不同，判据 M6 的三线同跌已解除，改为「贵金属独跌」</b></b>。<b>②</b> <b class="dk-caution">10Y 5.07% 在 96.4% 的加息概率下仍未破 5.20%</b> —— <b>这是当前唯一「没有恶化」的宏观读数</b>，<b>说明债市并未定价「连续三次加息」，与法巴 / 保尔森的口径存在分歧</b>；<b class="dk-main">⇒ 若今晚上破 5.20%，则成长股分母端二次承压，科创50 的独立性终结</b>。<b>③</b> <b class="dk-risk">VIX 盘中 28.75 已进入「高波动」区间</b> —— <b>与 A股 情绪 15「恐慌下跌」形成「内外同紧」</b>，<b class="dk-main">⇒ 这消除了上一版「外松内紧」的错配解释，<b class="dk-risk">本日 A股 的问题与外盘同步，无法用「内部筹码」单独解释</b></b>。<br>
    <b class="dk-data">口径说明</b>：<code>comm</code> 商品为 <b>11-20 早间最新报价</b>，<b>不代表 11-20 收盘</b>；美债为 <b>11-18</b> 结算（龄期 2 日，源侧未推进，<b>已显式标注、未用新闻轨替代</b>）；VIX 11-18 结算 24.56 值可信，<b>11/19 结算值 CBOE 尚未发布（T+1 04:15），本档只引用新闻轨盘中高点 28.75 并标明口径</b>。
  </div>
</div>
'''

NEW3 = '''<!-- 3 隔夜美股复盘 --><div class="dr-h" ''' + V + '''>3 · 隔夜美股复盘（<b class="dk-risk">11/19（周四）完整收盘</b> · 北京 11/20 05:00 落定 · <b class="dk-data">本档为盘前，可含量价</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 指数双日表（11/19 vs 11/18）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>指数</th><th>11/19 收盘</th><th>涨跌</th><th>11/18 收盘</th><th>两日累计</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">道琼斯</div></td><td>49,097.06</td><td><b class="dk-risk">-2.19%</b></td><td>50,198.17</td><td><b class="dk-risk">-3.28%</b></td></tr>
    <tr><td><div class="dr-wrap">标普 500</div></td><td>7,175.83</td><td><b class="dk-risk">-2.02%</b></td><td>7,323.63</td><td><b class="dk-risk">-2.25%</b></td></tr>
    <tr><td><div class="dr-wrap">纳斯达克</div></td><td>23,879.20</td><td><b class="dk-risk">-2.25%</b></td><td>24,429.88</td><td><b class="dk-risk">-1.84%</b></td></tr>
    <tr><td><div class="dr-wrap">VIX（盘中）</div></td><td><b class="dk-risk">最高 28.75</b></td><td><b class="dk-risk">+4.19 点</b></td><td>24.56（11-18 结算）</td><td><b class="dk-risk">进入高波动区</b></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 核心形态 = 「高开低走 + 三大同跌 + 裂口收敛」</b>：<b class="dk-risk">纳指盘中一度 +2%（23:37 转跌前）、费半一度涨近 5%（23:40 回吐全部涨幅）</b>，<b>最终三大指数收在 -2% 至 -2.25% 的极窄区间</b>，<b class="dk-risk">裂口 0.23pct 为近期最窄 —— 上一版「1 红 2 绿、裂口 1.53pct」的结构在一夜之间消失</b>。<b class="dk-main">⇒ 含义：<b class="dk-risk">这不是「科技被抛弃、传统被买入」的轮动，而是「全部资产一起减仓」</b>；<b>VIX 单日跳升 4 点以上是最直接的证据</b>，<b>判据 M7（裂口 = 结构切换）本日不适用，改用「VIX 跳升 = 系统性去杠杆」解释</b></b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 映射链：存储 / 光通信 / AI 硬件（11/19）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>标的</th><th>收盘</th><th>涨跌</th><th>A 股 同环节（11/19 收盘）</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">美光 MU</div></td><td>690.44</td><td><b class="dk-risk">-2.10%</b></td><td><div class="dr-wrap">德明利 <b class="dk-up">+5.78%</b> / 香农芯创 -2.43% / 协创数据 <b class="dk-risk">-5.64%</b>（<b class="dk-caution">内部分化 11pct 未收敛</b>）</div></td></tr>
    <tr><td><div class="dr-wrap">闪迪 SNDK</div></td><td>755.16</td><td><b class="dk-risk">-2.71%</b></td><td><div class="dr-wrap">存储模组 / 主控（长鑫映射 <b class="dk-up">+1.99%</b>）</div></td></tr>
    <tr><td><div class="dr-wrap">西部数据 WDC</div></td><td>296.78</td><td><b class="dk-up">+2.98%</b></td><td><div class="dr-wrap"><b class="dk-up">存储四线唯一红盘（连 3 日）</b> —— HDD 的 AI 冷数据叙事独立于 DRAM/NAND</div></td></tr>
    <tr><td><div class="dr-wrap">SK 海力士 ADR</div></td><td>119.20</td><td><b class="dk-risk">-2.67%</b></td><td><div class="dr-wrap"><b>今晨韩股现货 -6.51%</b>（1,106,000）—— <b class="dk-risk">ADR 跌幅小于现货，说明亚洲时段仍在补跌</b></div></td></tr>
    <tr><td><div class="dr-wrap">LITE 朗美通</div></td><td>535.15</td><td><b class="dk-risk">-2.89%</b></td><td><div class="dr-wrap">光迅 <b class="dk-up">+3.68%</b> / 联特 +2.10% / 长飞 +2.22%（11/19 收盘）</div></td></tr>
    <tr><td><div class="dr-wrap">AAOI</div></td><td>39.46</td><td><b class="dk-risk">-3.26%</b></td><td><div class="dr-wrap"><b class="dk-risk">连续两日重挫（前日 -9.80%）</b> ⇒ A股 光模块二线补跌压力累计</div></td></tr>
    <tr><td><div class="dr-wrap">COHR</div></td><td>214.94</td><td><b class="dk-up">+0.99%</b></td><td><div class="dr-wrap">剑桥科技 <b class="dk-risk">-3.78%</b> / 华工科技 <b class="dk-risk">-5.70%</b>（11/19 收盘，<b>已先行回吐</b>）</div></td></tr>
    <tr><td><div class="dr-wrap">MRVL 迈威尔</div></td><td>138.47</td><td><b class="dk-risk">-4.86%</b></td><td><div class="dr-wrap">光 DSP / 定制芯片（<b class="dk-risk">两日累计 -6.90%</b>）</div></td></tr>
    <tr><td><div class="dr-wrap">NVDA</div></td><td>145.98</td><td><b class="dk-risk">-3.30%</b></td><td><div class="dr-wrap">算力链（中科曙光 <b class="dk-up">+2.09%</b> / 工业富联 金钻）；<b class="dk-risk">NVDA 连跌第五日</b></div></td></tr>
    <tr><td><div class="dr-wrap">TSLA</div></td><td>374.41</td><td><b class="dk-risk">-2.43%</b></td><td><div class="dr-wrap">新能源车链（汽车 -8.80 亿）</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 三重背离（本段要点）</b>：<b>① 指数与硬件同向下跌，但幅度不对等</b> —— <b>存储四线均值 -1.13%</b>（MU -2.10 / SNDK -2.71 / WDC +2.98 / SKHY -2.67）、<b class="dk-risk">光通信三线均值 -1.72%</b>（LITE -2.89 / COHR +0.99 / AAOI -3.26），<b>而 MRVL -4.86%、AMD 近 -8%</b>。<b class="dk-main">⇒ <b class="dk-risk">跌幅梯度 = 「定制芯片 / GPU 二线 &gt; 光通信 &gt; 存储」</b>，<b>说明杀跌核心是「AI 算力订单预期」，不是「存储周期」</b>；<b>这对 A股 的指向很明确：算力链（工业富联 / 中科曙光 / 浪潮）风险大于存储链</b></b>。<b>② COHR +0.99% 与 A股 光模块 11/19 已跌 3.78%–5.70%，方向相反</b> —— <b class="dk-caution">A股 先行回吐、美股后补跌，<b>今日 A股 光模块的补跌压力小于「同步下跌」情形</b></b>。<b>③ WDC +2.98% 连 3 日红盘</b> —— <b class="dk-up">HDD 的 AI 冷数据叙事与 DRAM/NAND 周期脱钩，是本轮唯一独立的多头结构</b>，<b>对应 A股 无直接标的，不构成操作依据</b>。<br>
    <b class="dk-main">⇒ 一句话：外部锚的真实状态是「算力预期被杀、存储周期未破」</b>，<b>本档因此把风险权重从「存储」移到「算力 / 光模块二线」，并把科创50 的失守位定在 1,220.38</b>。<br>
    <b class="dk-data">口径说明</b>：本段全部为 <b>11/19 完整收盘</b>（<code>us_kline.latest.date = 2026-11-19</code>），与 A股 11/19 收盘构成「同日对照」；<b>VIX 为新闻轨盘中高点 28.75，11/19 结算值待 CBOE 次日 04:15 发布</b>。
  </div>
</div>
'''

NEW4 = '''<!-- 4 重点宏观 --><div class="dr-h" ''' + V + '''>4 · 重点宏观（<b>日历轨为准</b> · <b class="dk-risk">12 月加息概率 96.4%</b> · CPI 月率 0.4%（11/10，龄 9 日）· 非农 16.5 万（11/06，龄 13 日）· <b>今晨保尔森 / 法巴双双强化加息</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 美国关键指标（日历轨 · 逐项带公布日与龄期）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新值</th><th>预期 / 前值</th><th>公布日</th><th>龄期</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">CPI 同比（9 月）</div></td><td><b class="dk-risk">3.7%</b></td><td>3.6 / 3.4</td><td>2026-10-14</td><td><b class="dk-caution">37 日</b></td></tr>
    <tr><td><div class="dr-wrap">核心 CPI 同比（9 月）</div></td><td><b class="dk-risk">2.6%</b></td><td>2.5 / 2.4</td><td>2026-10-14</td><td><b class="dk-caution">37 日</b></td></tr>
    <tr><td><div class="dr-wrap">CPI 月率（10 月 · 已回填）</div></td><td><b class="dk-risk">0.4%</b></td><td>0.3 / 0.6</td><td>2026-11-10</td><td><b>9 日</b></td></tr>
    <tr><td><div class="dr-wrap">核心 CPI 月率（10 月）</div></td><td><b class="dk-risk">0.3%</b></td><td>0.2 / 0.3</td><td>2026-11-10</td><td><b>9 日</b></td></tr>
    <tr><td><div class="dr-wrap">非农（10 月）</div></td><td><b class="dk-up">16.5 万</b></td><td>6.5 / 6.0</td><td>2026-11-06</td><td><b>13 日</b></td></tr>
    <tr><td><div class="dr-wrap">失业率（10 月）</div></td><td><b>4.1%</b></td><td>4.2 / 4.2</td><td>2026-11-06</td><td><b>13 日</b></td></tr>
    <tr><td><div class="dr-wrap">ADP 周度就业（截至 10/31）</div></td><td><b class="dk-up">2.38 万</b></td><td>— / 1.98</td><td>2026-11-17</td><td><b>2 日</b></td></tr>
    <tr><td><div class="dr-wrap">初请失业金（截至 11/14 周）</div></td><td><b class="dk-caution">今夜 21:30</b></td><td>19.7 / 20.0</td><td>2026-11-19</td><td><b class="dk-caution">值未回填</b></td></tr>
    <tr><td><div class="dr-wrap">零售销售（10 月）</div></td><td><b>0.2%</b></td><td>0.2 / 0.8</td><td>2026-11-17</td><td><b>2 日</b></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 宏观三判（本版有实质更新）</b>：<b>①</b> <b class="dk-risk">通胀的「月度动能」连续两月高于预期</b>（10 月 CPI 月率 0.4% &gt; 预期 0.3%；核心月率 0.3% &gt; 预期 0.2%）—— <b>这是 12 月加息概率升至 96.4% 的数据基础</b>；<b class="dk-caution">CPI 同比 / 核心同比日历轨值仍为空（源侧未返回），本档沿用 9 月 3.7% / 2.6% 并标龄 37 日，<b>不以新闻轨二手转述充数</b></b>。<b>②</b> <b class="dk-up">就业端持续强于预期</b> —— 非农 16.5 万（预期 6.5）、失业率 4.1%（预期 4.2）、ADP 周度 2.38 万（前值 1.98）。<b class="dk-main">⇒ 「强就业 + 通胀月率 0.4%」= 「不着陆」，<b class="dk-risk">此时美联储没有降息空间，法巴「连续三次加息」与保尔森「不应玩火」在数据上自洽</b></b>。<b>③</b> <b class="dk-caution">今晨三位官员口径一致偏鹰</b>：<b>保尔森「以审慎的加息步伐推进」（08:04）·「10 月加息暂停只是调整节奏」（07:54）·「不应在通胀问题上玩火」（08:27）</b>；<b>沃什「AI 可能带来繁荣，但也需警惕风险」（08:35）</b>。<b class="dk-main">⇒ <b class="dk-risk">这是本档「高置信度」判定的宏观依据：不是单一官员表态，而是「数据 + 三官员 + 市场定价（96.4%）」三重一致</b></b>。<br>
    <b class="dk-main">⇒ 组合读法（与上一版一致，未变）</b>：<b>通胀月度动能 0.4% + 就业 16.5 万 = 「不着陆」而非「滞胀」</b>，<b class="dk-risk">分母端（利率）仍是主导变量，高估值方向只能给「结构仓」不给「主仓」</b>；<b class="dk-caution">本版新增一条：<b>当加息概率 &gt;95% 时，「加息」本身已被定价，边际影响转为「加息次数」而非「是否加息」—— 这解释了为何 11/19 美股先涨后跌（先定价「已确定」，后定价「还要加两次」）</b></b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 中国（同一日历轨体系）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新值</th><th>期间</th><th>读数</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">CPI 同比</div></td><td><b>+0.7%</b></td><td>2026 年 10 月</td><td><div class="dr-wrap">环比 0.0%，仍在低位，内需价格弹性弱</div></td></tr>
    <tr><td><div class="dr-wrap">制造业 PMI</div></td><td><b class="dk-caution">49.3</b></td><td>2026 年 10 月</td><td><div class="dr-wrap"><b class="dk-risk">连续处于收缩区间</b>，同比 +0.61%</div></td></tr>
    <tr><td><div class="dr-wrap">非制造业 PMI</div></td><td><b class="dk-caution">49.7</b></td><td>2026 年 10 月</td><td><div class="dr-wrap"><b class="dk-risk">跌破荣枯线</b>，同比 -0.80%</div></td></tr>
    <tr><td><div class="dr-wrap">GDP 同比</div></td><td><b>+4.6%</b></td><td>2026 Q1–Q3</td><td><div class="dr-wrap">累计 107.11 万亿；第三产业 +5.2% 为主要贡献</div></td></tr>
    <tr><td><div class="dr-wrap">LPR（1Y / 5Y）</div></td><td><b>3.0% / 3.5%</b></td><td>2026-10-20</td><td><div class="dr-wrap">连续持平，货币端未进一步宽松</div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 中外剪刀差在本档「不再作为资源股依据」（口径延续）</b>：<b class="dk-risk">美国「CPI 月率 0.4% + 非农 16.5 万 + 加息概率 96.4%」vs 中国「CPI +0.7% + 双 PMI 收缩 + LPR 持平」</b>。<b class="dk-caution">本档商品读数已给出新证据：<b>金 -0.98%（连跌四日）而油 +1.37%（连涨三日）</b>，<b>说明资源内部已分叉 —— 贵金属被实际利率压制，能源被供给端支撑，<b class="dk-risk">故「资源整体受益于剪刀差」的推论彻底失效，须逐品种判断</b></b>。
  </div>
</div>
'''

NEW5 = '''<!-- 5 重点科技 --><div class="dr-h" ''' + V + '''>5 · 重点科技（对照 <b class="dk-risk">美股 11/19 算力硬件被杀</b> vs <b class="dk-up">A 股 11/19 半导体单极反转</b> · 映射精确到细分环节）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>环节</th><th>美股 11/19</th><th>A 股 11/19</th><th>判读</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap">光模块 / 光通信</div></td><td><b class="dk-risk">LITE -2.89 / COHR +0.99 / AAOI -3.26</b>（三线均值 -1.72%）</td><td><div class="dr-wrap">光迅 <b class="dk-up">+3.68%</b> / 长飞 +2.22% / 联特 +2.10%；<b class="dk-risk">华工 -5.70% / 剑桥 -3.78%</b>（其他专家持股参考·非本人）</div></td><td><div class="dr-wrap"><b class="dk-caution">A股 已提前一日分化</b>：一线（光迅 / 长飞）抗跌、二线（华工 / 剑桥）已杀 → <b class="dk-risk">今日二线补跌压力小于「同步下跌」情形</b></div></td></tr>
    <tr><td><div class="dr-wrap">PCB / 覆铜板</div></td><td>—（无直接对标）</td><td><div class="dr-wrap"><b class="dk-up">印制电路板 +45.17 亿</b> · 元件 <b class="dk-up">+46.38 亿</b>；金钻 3 只（沪电 / 深南 / 兴森）</div></td><td><div class="dr-wrap"><b class="dk-up">仍是质量最高的链</b>：<b>无外部锚 = 不被算力杀跌传导</b>；但<b class="dk-caution">已连涨多日，今日若科创50 失守 1,220.38 须同步减半</b></div></td></tr>
    <tr><td><div class="dr-wrap">存储（DRAM / NAND）</div></td><td><b class="dk-risk">MU -2.10 / SNDK -2.71 / WDC +2.98 / SKHY -2.67</b>（均值 -1.13%）</td><td><div class="dr-wrap">德明利 <b class="dk-up">+5.78%</b> / 长鑫 <b class="dk-up">+1.99%</b> / 香农芯创 -2.43% / <b class="dk-risk">协创数据 -5.64%</b></div></td><td><div class="dr-wrap"><b class="dk-caution">跌幅梯度最小的一环</b>（-1.13% &lt; 光通信 -1.72% &lt; MRVL -4.86%）；<b class="dk-up">但今晨韩存储 -6.51% / 铠侠 -10% 才是真正的定价 → 今日补跌压力大</b></div></td></tr>
    <tr><td><div class="dr-wrap">半导体设备 / 材料</div></td><td><b class="dk-risk">爱德万 -8% / 铠侠 -10%（亚洲时段）</b></td><td><div class="dr-wrap">兴福电子 -0.65% / 东微半导 +0.20% / 天岳先进 <b class="dk-up">+2.01%</b> / 长光华芯 +0.78%</div></td><td><div class="dr-wrap"><b class="dk-risk">本日风险最高的细分</b>：<b>设备（爱德万 -8%）与 NAND 原厂（铠侠 -10%）同步杀</b> → 国产设备今日补跌压力最大</div></td></tr>
    <tr><td><div class="dr-wrap">算力 / 服务器</div></td><td><b class="dk-risk">NVDA -3.30（连跌五日）/ MRVL -4.86 / AMD 近 -8</b></td><td><div class="dr-wrap">中科曙光 <b class="dk-up">+2.09%</b>（唯一多头排列）/ 工业富联（金钻）/ 罗博特科 +1.73%</div></td><td><div class="dr-wrap"><b class="dk-risk">内外背离最大且方向最明确向下</b>：外部两日累计 -6% 以上，A股 仍强 → <b class="dk-risk">判据 M11：今日收敛方向向下，且幅度大于指数</b></div></td></tr>
    <tr><td><div class="dr-wrap">AI 应用 / 数据要素</div></td><td><b class="dk-caution">Anthropic 上市未能缓解回调（08:26）</b></td><td><div class="dr-wrap">计算机 <b class="dk-risk">-55.15 亿</b>（最大单席流出，升背离 B）· 国家数据局第二批可信数据空间试点</div></td><td><div class="dr-wrap"><b class="dk-risk">叙事与资金反向</b>：IPO 融资 813 亿对上游是订单，但对二级是抽水；<b class="dk-risk">A股 计算机 -55.15 亿已先行确认抽水效应</b></div></td></tr>
    <tr><td><div class="dr-wrap">面板 / 消费电子</div></td><td>—</td><td><div class="dr-wrap">京东方Ａ（金钻）/ 惠科股份 -0.84% / 利通电子（金钻）；OpenAI AI 硬件年底出货、立讯参与（08:25）</div></td><td><div class="dr-wrap"><b class="dk-up">唯一「不依赖美股价格」的事件链</b>：<b>但今日属系统性下跌日，事件驱动的胜率下降 → 只观察不建仓</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72;margin-top:6px">
    <b class="dk-main">⇒ 本段一句话结论：<b class="dk-risk">「叙事仍在、价格已破、资金已撤」三者同时出现，是本档科技板块的核心矛盾</b>。三组证据：<b>①</b> <b class="dk-up">叙事侧仍在改善</b> —— 美光总裁「2027 年存储供需更紧张」（08:25）、英伟达收购 Inception（06:46）、OpenAI AI 硬件年底出货（08:25）；<b>②</b> <b class="dk-risk">价格侧全线转跌</b> —— 存储 -1.13%、光通信 -1.72%、MRVL -4.86%、AMD 近 -8%、韩存储 -6.51%、铠侠 -10%；<b>③</b> <b class="dk-risk">A股 资金侧已撤</b> —— 电子 +17.50 亿（较 11/18 的 +99.84 亿缩 82.7%）、计算机 <b class="dk-risk">-55.15 亿</b>、通信 -6.80 亿。<b class="dk-main">⇒ 三者合起来只能得出一个操作结论：<b class="dk-risk">今日科技不建仓、只减不加；唯一保留的是「无外部价格锚」的 PCB / 元件，且须以科创50 1,220.38 为止损线</b></b>。<br>
    <b class="dk-risk">反向证据必须并列</b>：<b>①</b> <b class="dk-up">国家队科创50 ETF 11/19 净流入 +29.33 亿（7.8 倍）</b> —— <b>托底资金在半导体方向有明确动作</b>；<b>②</b> <b class="dk-up">深市月内回购超 200 亿元、单日 8 起以上公告</b>（紫金 20–30 亿 / 长鑫 25–50 亿 / 海光 2.35 亿）—— <b>产业资本在买自己</b>；<b>③</b> <b class="dk-up">美光「2027 年供需更紧张」与 A股 存储链库存周期位置一致</b> —— <b>基本面未反转，反转的是分母端</b>。<b class="dk-main">⇒ 三条共同指向：<b class="dk-caution">科技的问题在「估值 / 流动性」而非「景气」，故跌幅有底（托底 + 回购）但反弹无力（加息 + 杀估值）—— 这正是「10%–15% 仓位、只做宽基」的依据</b>
  </div>
</div>
'''

NEW55 = '''<!-- 5.5 产业链 / 景气度 --><div class="dr-h" ''' + V + '''>5.5 · 产业链 / 景气度评估（六条链 · 每条含 <b>价格 / 资金 / 事件</b> 三要素与一句判据）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>链</th><th>价格</th><th>资金 / 技术</th><th>判据</th></tr></thead><tbody>
    <tr><td><div class="dr-wrap"><b>① 光模块 / 光通信</b></div></td><td><div class="dr-wrap"><b class="dk-risk">LITE -2.89% / AAOI -3.26%（连两日重挫）</b>；COHR <b class="dk-up">+0.99%</b></div></td><td><div class="dr-wrap">通信 <b class="dk-risk">-6.80 亿</b>（由 +35.37 转负）；热度 6.0 条/日未达门槛 → 暗线降为双冷；<b class="dk-risk">板块 downtrend</b></div></td><td><div class="dr-wrap"><b class="dk-risk">降为「0 仓位」</b>：<b>资金由正转负 + 外部连两日杀 + A股 二线已跌 3.8%–5.7%</b> → <b class="dk-risk">今日不接任何光模块，含一线</b></div></td></tr>
    <tr><td><div class="dr-wrap"><b>② PCB / 覆铜板 / 元件</b></div></td><td><div class="dr-wrap">—（无直接外部锚，纯内部定价）</div></td><td><div class="dr-wrap">印制电路板 +45.17 亿 · 元件 <b class="dk-up">+46.38 亿（+6.49%）</b>；金钻 3 只；<b class="dk-caution">但电子本身已是 downtrend（L2）</b></div></td><td><div class="dr-wrap"><b class="dk-caution">降级为「只减不加」</b>：<b>无外部锚仍是优势，但今日是系统性杀跌日，「无锚」不等于「上涨」</b>；<b class="dk-risk">止损 = 科创50 失守 1,220.38</b></div></td></tr>
    <tr><td><div class="dr-wrap"><b>③ AI 硬件代工 / 消费电子</b></div></td><td><div class="dr-wrap"><b class="dk-up">OpenAI 首款 AI 硬件年底出货，立讯精密等参与（08:25）</b>；三星新任存储 / 移动负责人（08:20）</div></td><td><div class="dr-wrap">电子 +17.50 亿（含全链）；<b class="dk-risk">板块 downtrend</b></div></td><td><div class="dr-wrap"><b class="dk-caution">只观察不建仓</b>：<b>事件驱动在系统性下跌日胜率显著下降</b>；<b>等跌停收敛至 60 家以内再评估</b></div></td></tr>
    <tr><td><div class="dr-wrap"><b>④ 存储</b></div></td><td><div class="dr-wrap">MU -2.10% / SNDK -2.71% / WDC <b class="dk-up">+2.98%</b> / SKHY -2.67%（均值 -1.13%）；<b class="dk-risk">今晨海力士 -6.51%、三星 -4.98%、铠侠 -10%</b></div></td><td><div class="dr-wrap">德明利 +5.78% vs 协创数据 <b class="dk-risk">-5.64%</b>（内部分化 11pct）；<b class="dk-up">美光：2027 供需更紧张（08:25）</b></div></td><td><div class="dr-wrap"><b class="dk-risk">风险·回避</b>：<b>美股端只是小跌，亚洲时段才是真杀（韩存储 -6.5%、铠侠 -10%）→ 今日 A股 存储补跌压力最直接</b></div></td></tr>
    <tr><td><div class="dr-wrap"><b>⑤ 有色 / 黄金 / 能源（实物资产）</b></div></td><td><div class="dr-wrap"><b class="dk-risk">金 -0.98%（连四日）· COMEX -1.42%</b>；<b class="dk-up">WTI +1.37% · 布伦特 +1.10%（连三日）</b>；碳酸锂 91,500 持平</div></td><td><div class="dr-wrap">有色金属 <b class="dk-risk">-25.45 亿</b>（升背离 B）；石油石化 / 煤炭无新数据</div></td><td><div class="dr-wrap"><b class="dk-risk">贵金属回避、能源转中性</b>：<b>判据 M6 修订 —— 「金跌油涨」= 实际利率上行 + 供给扰动，<b class="dk-risk">故贵金属仍 0 仓位，能源从「回避」上调为「不参与」</b></b></div></td></tr>
    <tr><td><div class="dr-wrap"><b>⑥ 银行 / 红利</b></div></td><td><div class="dr-wrap">—（无当日价格数据）</div></td><td><div class="dr-wrap">银行 <b class="dk-risk">-19.29 亿</b>；<b class="dk-up">仍是唯一 uptrend 板块（4,511.98 &gt; EMA20 4,376.46）</b>；语料 17 条（升背离 B）</div></td><td><div class="dr-wrap"><b class="dk-caution">只守不加（连续第四日）</b>：<b>系统性下跌日，红利是相对防守而非绝对收益</b>；<b>跌破 EMA20 4,376.46 则底仓再减半</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:6px">
    <b class="dk-main">⇒ 六条链的排序（本档口径，<b class="dk-risk">与上一版相比两处降级、零处升级</b>）</b>：<b class="dk-caution">银行（只守不加，相对最优）&gt; PCB / 元件（只减不加）&gt; AI 硬件代工（只观察）&gt; 能源（不参与）&gt; 存储（回避）&gt; 光模块（0 仓位）&gt; 贵金属（回避）</b>。<b class="dk-risk">两处降级：① 光模块由「只做一线」降为「0 仓位」（通信资金由 +35.37 转 -6.80）；② PCB 由「第一优先」降为「只减不加」（电子板块 downtrend + 系统性杀跌日）</b>。<b class="dk-main">⇒ 本档没有任何一条链获得「加仓」授权 —— 这是与上一版最本质的差别</b>。
  </div>
</div>
'''

NEW671 = '''<!-- 6 新闻整合 + 7.1 --><div class="dr-h" ''' + V + '''>6 · 新闻整合（公开源自动刷新 · 本档实到：<b>285 条</b> · 覆盖 <b class="dk-data">11/20 早间 06:00–08:42</b> · 源分布 东财为主 + 富途 / 新浪 / 同花顺 / 央视 / 财经早餐）</div>
<div class="dr-card" style="margin-top:4px">
  <div id="drNewsPool" style="font-size:12.5px"><span style="color:var(--text-muted)">新闻池自动加载中…</span></div>
  <div class="dr-tag" style="margin-top:10px">① 抓取结构（<b>必须先看这一项，它决定了「热度」维度的可信度</b>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.66;margin-top:4px">
    <b class="dk-main">本档口径（<code>daily_news_latest.json</code> · <code>date 2026-11-20</code> · <code>generated_at 08:42</code>）</b>：实到 <b>285 条</b>，覆盖 <b>11/20 早间 06:00–08:42</b>；<b>四象限窗口 = 11/19 + 11/20（2 日，门槛 16 条）</b>。<br>
    <b class="dk-data">与上一版的差别（关键）</b>：上一版 00:15 重算时，<b>11/20 早间新闻尚未入池</b>，五席（有色 / 传媒 / 银行 / 非银 / 食品饮料）的 <code>news_count</code> 停在 3–13 条；<b>本档入库后升至 17–29 条，全部跨过 16 条门槛</b>。<b class="dk-main">⇒ 这正是四象限「背离 B 由 1 增至 6」的唯一成因（已逐席核过：<code>flow_yi</code> 变化数 = 0）</b>。<br>
    <b class="dk-caution">口径提醒</b>：<b class="dk-risk">本日五席的讨论升温题材多为「下跌归因」（有色大跌、银行息差、食品饮料防御），在系统性下跌日，<b>这类升温本身是风险信号而非资金信号</b></b> —— <b>本档不把任何一席背离 B 列入观察池</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 今日五条主线（按对 11/20 的定价权重排序）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7;margin-top:4px">
    <b class="dk-risk">① 亚太与美股同步杀跌，半导体是唯一靶心（权重最高）</b>：<b class="dk-risk">日经 -4.46%（期货盘前 -3.63%）· KOSPI -4.00%（开盘 -4.08%）· 海力士 -6.51% · 三星 -4.98% · 软银 -14% · 铠侠 -10% · 爱德万 -8%</b>；<b class="dk-risk">美股三大同跌超 2%、AMD 遭做空重挫近 8%、VIX 盘中 28.75</b>。<b class="dk-main">⇒ 这决定了本档「低开偏弱」的判定，<b class="dk-risk">且跌幅的行业指向非常明确：存储 / 设备 / 算力</b></b>。<br>
    <b class="dk-risk">② 加息预期升至 96.4%，且三家机构同日强化（第二权重）</b>：<b class="dk-risk">12 月加息 25bp 概率 96.4%（06:05）· 法巴「连续三次加息」（07:29）· 保尔森「不应玩火」「10 月暂停只是调整节奏」（07:54–08:27）</b>；<b>沃什「AI 繁荣但需警惕风险」（08:35）</b>。<b class="dk-main">⇒ <b class="dk-risk">这是「杀估值」的宏观底因，且属「已定价但仍在升级」的状态 —— 从「一次」升级为「三次」才是新增变量</b></b>。<br>
    <b class="dk-caution">③ Anthropic 上市未能提振市场（第三权重，已证伪）</b>：<b class="dk-risk">KOSPI 下跌 4.1%，Anthropic 上市未能缓解市场普遍回调（08:26）</b>；对应上一版「判据 M9：IPO 双面性，等首日裁决」。<b class="dk-main">⇒ <b class="dk-risk">裁决结果 = 叙事未成立（至少首日未成立）</b>，<b>上一版「Anthropic 破发 → 科创50 低开覆盖 +1.83%」的风险假设已兑现</b></b>。<br>
    <b class="dk-up">④ 存储供需的中期逻辑仍在（第四权重，唯一利多）</b>：<b class="dk-up">美光总裁：2027 年供需形势将比今年更紧张（08:25）</b>；<b>三星任命存储与移动业务独立负责人（08:20）</b>；<b>LG Display 取消 3 万亿韩元 OLED 投资（08:13，电视需求放缓）</b>。<b class="dk-main">⇒ <b>中期供需 vs 短期杀估值</b>，<b class="dk-caution">本档只把它作为「跌幅有底」的依据，不作为「今日买入」的理由</b></b>。<br>
    <b class="dk-caution">⑤ 国内对冲项（第五权重）</b>：<b class="dk-up">北京商报「加快回购节奏利于提振市场信心」（08:33）</b> · <b>半导体材料设备板块「触底回升」（07:36，行业标准落地 + 国产化向多工序拓展）</b> · <b>流感用药销量翻倍（08:38，医药主题性机会）</b>。<b class="dk-main">⇒ 两条都与「托底 / 超跌」相关，<b class="dk-caution">属防守型信息，不构成进攻理由</b></b>。
  </div>
</div>
<div class="dr-h" ''' + V + '''>7.1 · K3 产业信号验证（<b class="dk-risk">A股 11/19 完整收盘</b> + <b class="dk-risk">美股 11/19 完整收盘</b> + <b class="dk-risk">亚太 11/20 早盘</b> · 7 条主题 · 结论句按语义上色 · <b>周五</b>盘中需复核前四条）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px">
  <div class="k3c-legend">结论色标：<i class="l-go">可执行·相对占优</i><i class="l-cond">有条件·待确认</i><i class="l-risk">风险·回避</i><i class="l-verify">待验证变量·方法论</i></div>
  <table class="dr-tbl"><thead><tr><th>主题</th><th>验证</th><th>内容</th></tr></thead><tbody>
    <tr><td><b class="dk-caution">PCB / 元件</b></td><td><div class="dr-wrap"><b class="dk-caution">无外部锚，但已被算力杀跌包围</b></div></td><td><div class="dr-wrap">印制电路板细分 <span class="dk-up">+45.17 亿</span> · 元件 <span class="dk-up">+46.38 亿（+6.49%）</span> · 金钻 3 只（沪电股份 / 深南电路 / 兴森科技）；<b class="dk-risk">但电子板块整体 downtrend（L2），且外部算力链被杀（AMD 近 -8%、MRVL -4.86%）</b>。<span class="k3c k3c-cond"><b>判据：由「第一优先」降为「只减不加」——「无外部锚」在系统性下跌日只是「不被直接传导」，不等于「逆势上涨」；止损线 = 科创50 失守 1,220.38</b></span></div></td></tr>
    <tr><td><b class="dk-risk">光模块 / 光通信</b></td><td><div class="dr-wrap"><b class="dk-risk">资金由 +35.37 转 -6.80，外部连两日杀</b></div></td><td><div class="dr-wrap">通信主力 <span class="dk-risk">-6.80 亿</span>（11/19 由正转负）；外部 LITE <span class="dk-risk">-2.89%</span> / AAOI <span class="dk-risk">-3.26%</span>（连两日重挫，累计 -12.7%）/ COHR <span class="dk-up">+0.99%</span>；A股 华工 <span class="dk-risk">-5.70%</span> / 剑桥 <span class="dk-risk">-3.78%</span> 已先行回吐。<span class="k3c k3c-risk"><b>判据：资金维转负 + 外部连两日杀 + A股 二线已跌 → 三重否定，光模块 0 仓位（含一线）；AAOI 两日 -12.7% 是二线补跌的先行指标，今日不接任何二线</b></span></div></td></tr>
    <tr><td><b class="dk-risk">算力 / 服务器</b></td><td><div class="dr-wrap"><b class="dk-risk">内外背离最大，今日收敛且方向向下</b></div></td><td><div class="dr-wrap">计算机主力 <span class="dk-risk">-55.15 亿</span>（31 席最大流出，升背离 B）· 中科曙光 <span class="dk-up">+2.09%</span>（唯一多头排列）/ 工业富联（金钻）；外部 <b class="dk-risk">NVDA -3.30%（连跌五日）</b> / <b class="dk-risk">MRVL -4.86%</b> / <b class="dk-risk">AMD 近 -8%</b>。<span class="k3c k3c-risk"><b>判据：判据 M11 直接适用 —— 唯一强势方向被击穿 → 当日跌幅中位数大于指数；算力链 0 仓位，中科曙光若跌破 MA5 全撤，不做板块</b></span></div></td></tr>
    <tr><td><b class="dk-risk">存储</b></td><td><div class="dr-wrap"><b class="dk-risk">美股小跌、亚洲真杀，今日补跌压力最直接</b></div></td><td><div class="dr-wrap">MU <span class="dk-risk">-2.10%</span> / SNDK <span class="dk-risk">-2.71%</span> / WDC <span class="dk-up">+2.98%</span> / SKHY <span class="dk-risk">-2.67%</span>（四线均值 -1.13%）；<b class="dk-risk">但今晨海力士 -6.51%、三星 -4.98%、铠侠 -10%</b>；A股 德明利 <span class="dk-up">+5.78%</span> vs 协创数据 <span class="dk-risk">-5.64%</span>。<span class="k3c k3c-risk"><b>判据：亚洲时段跌幅（-6.5% / -10%）才是今日的真实定价，美股 -1.13% 是滞后读数 → 存储 0 仓位；德明利昨日的 +5.78% 在今日低开环境下须按「补跌」处理，不接</b></span></div></td></tr>
    <tr><td><b class="dk-risk">有色金属 / 贵金属</b></td><td><div class="dr-wrap"><b class="dk-risk">贵金属连跌四日，能源反向</b></div></td><td><div class="dr-wrap">今晨现货金 <span class="dk-risk">-0.98%（3,688.07）</span>、COMEX <span class="dk-risk">-1.42%</span>；<b class="dk-up">WTI +1.37%（83.44）、布伦特 +1.10%</b>；A股 有色金属主力 <span class="dk-risk">-25.45 亿</span>（升背离 B）、语料 29 条。<span class="k3c k3c-risk"><b>判据：判据 M6 修订 —— 「金跌油涨」= 实际利率上行 + 供给扰动，非通缩；贵金属 0 仓位（连四日跌、累计 -5.2%），能源由「回避」上调为「不参与」，资源整体不加</b></span></div></td></tr>
    <tr><td><b class="dk-caution">银行 / 红利</b></td><td><div class="dr-wrap"><b class="dk-caution">技术强 / 资金弱（第四日）</b></div></td><td><div class="dr-wrap"><b>唯一 uptrend 板块</b>（4,511.98 &gt; EMA20 4,376.46），但主力 <span class="dk-risk">-19.29 亿</span>、语料 17 条（升入背离 B）；TOP10 中银行占 3 席（中国银行 75 / 杭州银行 75 / 工商银行 60）。<span class="k3c k3c-verify"><b>判据：技术面与资金面连续两日反向、今日语料升温 → 只守不加；系统性下跌日红利的价值在「跌幅小于指数」而非「绝对收益」；跌破 EMA20 4,376.46 则底仓再减半</b></span></div></td></tr>
    <tr><td><b class="dk-neutral">AI 硬件代工 / 消费电子</b></td><td><div class="dr-wrap"><b class="dk-neutral">事件仍在，但今日胜率下降</b></div></td><td><div class="dr-wrap">OpenAI 首款 AI 硬件年底启动出货、<b>立讯精密等中国供应商参与</b>（08:25）· 三星新任存储 / 移动负责人（08:20）· 特斯拉 Optimus 两月内演示；电子资金 <span class="dk-up">+17.50 亿</span>（较 11/18 缩 82.7%）。<span class="k3c k3c-verify"><b>判据：事件驱动型机会在「跌停 105 家 + 情绪 15」的环境下胜率显著下降 → 只观察不建仓；等跌停收敛至 60 家以内、情绪回到 20 以上再评估，届时单票 ≤4%</b></span></div></td></tr>
  </tbody></table></div>
</div>
'''

NEW73 = '''<!-- 7.3 次日开盘指引 --><div class="dr-h" ''' + V + '''>7.3 · 当日开盘指引（<b>11/20 周五</b> · 结论 1 条 + 依据 3 条 + 反向风险 3 条 · 本卡由规则引擎二次覆盖，agent 版详见 7.4）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">结论（跨页同值）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72">
    <b class="dk-main">方向</b> <b class="dk-risk">偏空</b> · <b class="dk-main">置信度</b> <b class="dk-data">高</b> · <b class="dk-main">开盘档</b> <b class="dk-risk">低开偏弱</b> · <b class="dk-main">仓位</b> <b>10%–15%</b> · <b class="dk-main">风险</b> <b class="dk-risk">高</b> · <b class="dk-main">四象限</b> <b>1 / 6 / 3 / 21</b>。<br>
    <b class="dk-main">一句话</b>：<b class="dk-caution">11/20 不看「能否收红」，只看两个数 —— 跌停能否从 105 回到 60 家以内、成交能否守住 10,000 亿；跌停回落且成交守住 → 维持 10%–15% 只做宽基，跌停继续放大或成交跌破 10,000 亿 → 仓位压到 5%–10% 且个股清零</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">正向依据（3 条）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7">
    <b class="dk-up">① 托底资金创本月最大单日</b>：国家队 ETF <b>+132.48 亿</b>（昨 +36.86，<b>3.6 倍</b>）、trend_5d +269.73 亿；<b>科创50 ETF +29.33 亿（7.8 倍）</b>、中证1000 由 +0.19 亿放量至 <b>+16.98 亿</b> —— <b>托底目标已从「守指数」扩到「止血小盘」</b>。<br>
    <b class="dk-up">② 产业资本密集回购</b>：<b>深市月内回购超 200 亿元</b>；单日 8 起以上回购公告（<b>紫金 20–30 亿 / 长鑫 25–50 亿 / 海光 2.35 亿 / 赣锋 2–4 亿 / 鹏鼎 3.4 亿</b>）—— <b>与二级市场情绪严重背离，是典型的底部区域特征</b>。<br>
    <b class="dk-up">③ 债市未跟随加息预期定价</b>：<b>10Y 5.07% 在 96.4% 的加息概率下仍未上破 5.20%</b> —— <b>说明债市对「连续三次加息」持保留态度（法巴 / 保尔森是鹰派少数），这是当前唯一没有恶化的宏观读数</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">反向风险（3 条，按概率 × 冲击排序）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7">
    <b class="dk-risk">① 系统性杀跌二次扩散（概率 高 / 冲击 高）</b>：<b>亚太 -4.46% / -4.00%、韩存储 -6.51%、铠侠 -10%、软银 -14%</b> —— <b>跌幅的行业指向明确（存储 / 设备 / 算力），而 A股 昨日强势恰在此处</b>；<b class="dk-risk">判据 M11：唯一柱子被抽走 → 指数跌幅大于「普跌」情形，且科创50 跌幅最大</b>。<br>
    <b class="dk-risk">② 量能断崖 + 跌停扩散（概率 高 / 冲击 高）</b>：<b>成交 10,770.2 亿（-21.4%）为 11/14 以来最低、跌停 105 家</b>；<b class="dk-risk">若今日成交跌破 10,000 亿，个股无承接（托底资金只买宽基），跌停家数可能冲 150 家以上</b>。<br>
    <b class="dk-caution">③ 10Y 上破 5.20%（概率 中 / 冲击 中高）</b>：<b>法巴「连续三次加息」+ 保尔森「不玩火」尚未在债市定价（10Y 5.07%）</b>；<b>若今晚上破 5.20%，成长股分母端二次承压，科创50 的「独立性」终结，下周一的低开幅度会更大</b>。
  </div>
</div>
'''

NEW74 = '''<!-- 7.4 操作预案 --><div class="dr-h" ''' + V + '''>7.4 · 操作预案（<b>盘前版 · agent 详细版 · 面向 11/20 周五</b> · 含「大势预判 / 主线策略 / 回避清单」三要素）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 大势预判（if-then，四条，可直接执行）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72">
    <b class="dk-risk">基准情形（概率 45%）：低开 -1.0%~-1.8%（3,513–3,542），日内低位震荡</b> —— 跌停 80–130 家、成交 9,500–10,800 亿。<b class="dk-caution">应对：总仓位维持 10%–15%，<b>只持有沪深300 / 科创50 宽基，个股不加</b>；不抄底、不做题材</b>。<br>
    <b class="dk-up">改善情形（概率 20%）：低开 &lt;1.0% 且 10:30 前回补至 3,570 以上、成交同比放大 ≥10%</b> —— 外部冲击被一次性消化。<b class="dk-main">应对：仓位可回 15%（不加个股），<b>只在科创50 宽基上加 2%–3%</b>；「低开偏弱」改判「低开反弹」</b>。<br>
    <b class="dk-risk">恶化情形（概率 30%）：低开 &gt;1.8%，或跌停回升至 150 家以上 / 上证失守 3,547.94</b> —— 恐慌二次扩散。<b class="dk-risk">应对：仓位压至 5%，<b>个股全部清零，只留沪深300 / 科创50 宽基底仓</b>，等 VIX 回落至 25 以下再评估</b>。<br>
    <b class="dk-caution">尾部情形（概率 5%）：日经盘中跌破 -6% 且韩存储扩大至 -8% 以上，或 10Y 上破 5.20%</b> —— 外部定价失控。<b class="dk-caution">应对：宽基亦减半，全仓降至 2%–3%，等次日再评估；不做任何左侧</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 主线策略（<b class="dk-risk">本档零条「加仓」主线，只有三条「守」与「看」</b>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72">
    <b class="dk-caution">第一优先 · 宽基 ETF（唯一允许持有的方向）</b>：<b>沪深300（510300）/ 科创50（588000）</b> —— <b>国家队 11/19 净流入 +132.48 亿、科创50 ETF +29.33 亿，托底资金的承接位就是这两个品种</b>。<b class="dk-main">做法：<b class="dk-caution">只在低开 -1.5% 以下分批承接，单日不超过总仓位 5%；止损 = 上证失守 3,547.94 则减半</b></b>。<br>
    <b class="dk-caution">第二优先 · 银行 / 红利（只守不加）</b>：<b>唯一 uptrend 板块</b>（4,511.98 &gt; EMA20 4,376.46），<b>但资金 -19.29 亿、语料升温至 17 条</b>。<b class="dk-main">做法：<b>已有底仓持有，不新增</b>；<b>跌破 EMA20 4,376.46 则底仓再减半</b>（本档唯一设技术止损位的防守方向）</b>。<br>
    <b class="dk-caution">第三优先 · PCB / 元件（只减不加）</b>：<b>无外部锚仍是最优结构（印制电路板 +45.17 亿 / 元件 +46.38 亿）</b>，<b class="dk-risk">但电子板块 downtrend、外部算力链被杀</b>。<b class="dk-main">做法：<b>只减不加</b>；<b>止损 = 科创50 失守 1,220.38 → 电子链持仓减半</b>；不加仓、不摊薄</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 回避清单（四条，硬性）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.72">
    <b class="dk-risk">① 光模块 / 光通信（含一线）</b>：<b>通信资金由 +35.37 转 -6.80、AAOI 连两日 -12.7%、华工 -5.70% / 剑桥 -3.78% 已先行回吐</b> —— <b class="dk-risk">资金 / 价格 / 外部锚三重否定，0 仓位</b>。<br>
    <b class="dk-risk">② 算力 / 服务器</b>：<b>计算机 -55.15 亿（最大单席流出）、NVDA 连跌五日、MRVL -4.86%、AMD 近 -8%</b> —— <b class="dk-risk">判据 M11 直接适用，0 仓位；中科曙光昨日 +2.09% 是「最后一个强势点」，破 MA5 即全撤</b>。<br>
    <b class="dk-risk">③ 存储（含德明利 / 协创 / 香农 / 长鑫映射）</b>：<b class="dk-risk">今晨海力士 -6.51%、三星 -4.98%、铠侠 -10%</b> —— <b>亚洲时段才是真实定价，美股 -1.13% 是滞后读数</b>；<b class="dk-risk">存储 0 仓位，德明利昨日 +5.78% 按补跌处理</b>。<br>
    <b class="dk-risk">④ 有色金属 / 贵金属</b>：<b>金 -0.98% 连四日（累计 -5.2%）、COMEX -1.42%、板块 -25.45 亿、语料 29 条</b> —— <b class="dk-risk">价格 / 资金 / 叙事三重否定，0 仓位</b>；<b class="dk-caution">能源（WTI +1.37%）上调为「不参与」，不因油价反弹而买石化 / 煤炭</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">④ 规则与技能</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7">
    <b class="dk-main">规则</b>：<code>review/REVIEW_SOP.md</code>（盘前模式）· skill <code>daily-reasoning</code>（老站）· skill <code>v3-daily-review</code>（V3）· <code>realtime.L2.rules</code>（情绪 15 → 仓位区间 [0,20]）· <code>review_v3/backtest_v3.py</code> 的 <code>OPEN_DIR</code> 白名单（<code>open_call = 低开偏弱</code>）· 十四道门禁（<code>review/check_*.py</code>）· 本档新增判据 M10（外部跌幅→A股开盘非线性折算）/ M11（唯一强势方向被击穿 = 指数级补跌）/ M12（托底资金只守宽基不守个股）。<br>
    <b class="dk-data">口径</b>：本页所有个股为「其他专家持股参考（非本人）」的客观读数，<b>不构成买卖建议</b>；AI 仅做分析，不执行任何交易。
  </div>
</div>
'''

NEW8 = '''<!-- 8 数据自检 --><div class="dr-h" ''' + V + '''>8 · 数据自检区（JS 自动扫描 · 各源日期一致性 · <b class="dk-up">本档已核：A股 2026-11-19 完整收盘〔结算价〕· 美股 2026-11-19 完整收盘〔北京 11/20 05:00 落定〕· 亚太 2026-11-20 早盘 08:40 · 商品 11-20 最新 · 美债 11-18 结算 · VIX 11-18 结算 24.56〔11/19 结算待发〕· 宏观日历轨 as_of 01:31</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div id="drSelfCheck" style="font-size:12.5px"><span style="color:var(--text-muted)">自检加载中…</span></div>
  <div class="dr-tag" style="margin-top:10px">① 各源日期与新鲜度（逐项核对）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>数据源</th><th>内部日期字段</th><th>是否 == 数据日</th><th>备注</th></tr></thead><tbody>
    <tr><td><code>data/daily_review/market.json</code></td><td><code>date 2026-11-19</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap">A股 11-19 收盘；<code>us_kline</code> 全部为 <b>11-19</b>（昨夜已落定）；<code>asia</code> = 11-20 早盘 08:40；<code>comm</code> = 11-20 最新</div></td></tr>
    <tr><td><code>output/cross_analysis.json</code></td><td><code>data_date 2026-11-19</code> / <code>news_window ['11-19','11-20']</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap"><code>news_window_days 2</code> / <code>flow_date 2026-11-19</code>（<code>flow_is_weekend_copy = false</code>）· <b>本档四象限 1/6/3/21 现场现算</b></div></td></tr>
    <tr><td><code>output/sector_tech.json</code></td><td><code>data_date 2026-11-19</code> / <code>kline_last_date 2026-11-18</code></td><td><b class="dk-caution">⚠️ 滞后 1 日</b></td><td><div class="dr-wrap"><b><code>kline_lag.trading_days = 1</code></b>（申万宏源官网 T+1 发布，非本链漏抓）· 31 席全覆盖 · <b>L4 0 / L3 0 / L2 4 / L1 27</b>（向上 1 / 下跌反弹 4 / 下跌破位 26）</div></td></tr>
    <tr><td><code>output/sector_flow.json</code></td><td><code>source_status.last_success 2026-11-19</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap"><code>ok = true</code> · <code>stale_days 0</code> · <b>资金维无滞后（<code>flow_date</code> = 数据日）</b></div></td></tr>
    <tr><td><code>realtime.json</code></td><td><code>meta.updated_at 2026-11-19 22:18:16</code> / <code>closed</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap">涨 538 / 跌 4,020 / 平 47 · 涨停 31 / <b class="dk-risk">跌停 105</b> · 主力 -309.69 亿 · <b>成交 10,770.2 亿</b> · 情绪 15 · <b>收盘重算版</b></div></td></tr>
    <tr><td><code>output/daily_news_latest.json</code></td><td><code>date 2026-11-20</code> / <code>generated_at 08:42</code> · <b>285 条</b></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap">覆盖 11/20 早间 06:00–08:42；<b>四象限窗口 = 11/19 + 11/20</b>（<code>news_window_days 2</code>）</div></td></tr>
    <tr><td><code>output/daily_macro_latest.json</code></td><td><code>date 2026-11-20</code> / 日历轨 <code>as_of 01:31</code></td><td><b class="dk-caution">⚠️ 美国轨空</b></td><td><div class="dr-wrap"><b class="dk-caution">11-20 版 <code>us.indicators</code> 为空（<code>stale</code> 列出 9 类）</b> → <b>本档宏观改取 11-19 版日历轨（<code>as_of 22:01</code>，10 类指标完整）</b>，龄期按公布日计算</div></td></tr>
    <tr><td><code>output/vix_panel.json</code></td><td><code>cboe_vix.date 2026-11-18</code></td><td><b class="dk-caution">⚠️ T+1</b></td><td><div class="dr-wrap">CBOE <b>24.56</b>（11-18 结算）；<b class="dk-caution">11/19 结算值待发布（04:15），本档另引新闻轨盘中高点 28.75 并标明口径</b></div></td></tr>
    <tr><td><code>output/market_thermometer.json</code></td><td><code>date 2026-11-18</code></td><td><b class="dk-caution">⚠️ 前一交易日</b></td><td><div class="dr-wrap">主页三面板之一，<b>恒为前一交易日锚定（属设计内，非失败）</b>；<code>graham 1.97 / pe_pct_10y 28.6%</code></div></td></tr>
    <tr><td><code>output/signals.json</code></td><td><code>data_date 2026-11-19</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap">TOP 800 扫描 · 最高分 75（中国银行）</div></td></tr>
    <tr><td><code>feed/archive/2026-11-20/</code></td><td><code>_index.json</code> <code>feed_count 0</code></td><td><b class="dk-up">✅</b></td><td><div class="dr-wrap"><b>无批次日，如实记 0 件</b>（禁伪造条目）；<code>feed/archive/2026-11-19/</code> 同为 0 件</div></td></tr>
  </tbody></table></div>
  <div class="dr-tag" style="margin-top:10px">② 本档瑕疵与口径声明（不掩盖）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.7">
    <b class="dk-caution">① 板块技术 K 线滞后 1 日（11-18）</b>：<code>kline_lag.trading_days = 1</code>，<b>源侧申万宏源官网 T+1 发布，非本链漏抓</b>；<b>7.1b 已标注「K 线源实际末条 11-18」</b>，<b>不作为当日交易依据的唯一定量来源</b>。<br>
    <b class="dk-caution">② 美债龄期 2 日（11-18）</b>：<b>10Y 5.07% / 30Y 5.41%</b>，源侧未推进；<b>已显式标注日期，未用新闻轨转述替代</b>。<br>
    <b class="dk-caution">③ 11/19 VIX 结算值未发布</b>：<b>CBOE T+1（04:15）</b>；本档引用<b>新闻轨盘中高点 28.75 并标明「盘中」</b>，<b>未以 24.56 冒充 11/19 值</b>。<br>
    <b class="dk-caution">④ 美国宏观日历轨 11-20 版为空</b>：<b>改取 11-19 版（10 类指标）</b>，<b>CPI 同比 / 核心同比值仍为空 → 沿用 9 月 3.7% / 2.6%（龄 37 日）并标注</b>。<br>
    <b class="dk-caution">⑤ 四象限迁移为纯语料侧</b>：31 席 <code>flow_yi</code> 变化数 = 0，<b>背离 B 由 1 增至 6 全部因 <code>news_count</code> 跨 16 条门槛</b>，<b>已在 §0.5 / §6 两处披露「不得读作资金改善」</b>。<br>
    <b class="dk-data">⑥ 口径一致</b>：方向「偏空」/ 置信度「高」/ 开盘档「低开偏弱」/ 仓位「10%–15%」/ 风险「高」/ 四象限「1 / 6 / 3 / 21」<b>在老站 0 段 · 7.3 段 · V3 meta · V3 conclusion_first · feed_review meta + conclusion_first 五处同值</b>。
  </div>
</div>
'''

NEW9 = '''<!-- 9 来源 --><div class="dr-h" ''' + V + '''>9 · 来源（<b class="dk-up">盘前版 · 11/20 08:40 档落盘</b> · 数据日 2026-11-19 · 指引日 2026-11-20）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.7">
    <b class="dk-main">行情</b>：腾讯 gtimg（A股 指数 / 其他专家持股参考 / 港股 / 美股 13 只 / 商品汇率）· akshare 美股双日 · stock.fengle.me（韩存储双雄，<b class="dk-up">本次读数有效：海力士 -6.51% / 三星 -4.98%</b>）· 东财 push2test（申万 31 席资金流 / 宽基 ETF）· CBOE（VIX 结算）。<br>
    <b class="dk-main">信号与结构</b>：<code>signals.json</code>（成交额 TOP 800 扫描）· <code>golden_diamond.json</code>（金钻三重门控）· <code>cross_analysis.json</code>（资金 × 热度四象限，08:45 盘前重算）· <code>sector_tech.json</code>（申万一级 EMA / 趋势分级，K 线 11-18）· <code>obs_deduce_latest.json</code>（观测池 32 只）。<br>
    <b class="dk-main">语料</b>：<code>daily_news_latest.json</code> <b>285 条</b>（覆盖 11/20 早间 06:00–08:42）· <code>daily_macro_latest.json</code>（11-19 版日历轨 + 中国 PMI/CPI/GDP/LPR）· 当日投喂归档 <code>feed/archive/2026-11-20/</code> <b>0 件</b>、<code>feed/archive/2026-11-19/</code> <b>0 件</b>（<code>_index.json</code> 已如实记 <code>feed_count 0</code>）· 研报池仅取聚合读数，原文不入仓（<b>投喂语料 · 非本人持仓</b>）。<br>
    <b class="dk-main">口径</b>：A股 为 <b>11-19 收盘</b>；美股为 <b>11-19 完整收盘</b>；亚太为 <b>11-20 早盘 08:40</b>；商品为 <b>11-20 最新</b>；美债为 <b>11-18 结算</b>；VIX 为 <b>11-18 结算 24.56 + 11/19 盘中 28.75（新闻轨）</b>；广度 / 情绪为 <b>22:18:16 收盘重算版</b>。本页涉及个股均为「其他专家持股参考（非本人）」的客观读数，<b>不构成买卖建议</b>；运维纪律不入公开页面。
  </div>
</div>
'''

out = (prefix + '\n\n' + HEADER + '\n' + NEW0 + NEW05 + sec1 + NEW2 + NEW3
       + medical + '\n\n' + NEW4 + NEW5 + NEW55 + NEW671 + sector71b + '\n\n'
       + sec72 + NEW73 + NEW74 + NEW8 + NEW9)

io.open(P, 'w', encoding='utf-8-sig').write(out)
print('written', len(out), 'chars')

for m in re.finditer(r'<div class="dr-h"[^>]*>([\s\S]{0,70}?)</div>', out):
    t = re.sub(r'<[^>]+>', '', m.group(1)).strip().replace('\n', ' ')
    print(' -', t[:64])
