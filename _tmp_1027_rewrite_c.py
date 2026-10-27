# -*- coding: utf-8 -*-
"""2026-10-27 盘前版 · Part C：6 段 / 7.1 段 / 7.3 段 / 7.4 段 / 8 段（头部+手工说明）/ 9 段"""
import io

P = 'data/daily_review/analysis.html'
s = io.open(P, encoding='utf-8-sig').read()
orig = len(s)


def cut(a, b, new, label):
    global s
    assert s.count(a) == 1, '[%s] 起点锚点不唯一/缺失: %d' % (label, s.count(a))
    i = s.index(a)
    j = s.index(b, i)
    s = s[:i] + new + s[j:]
    print('  OK %s  (%d → %d)' % (label, j - i, len(new)))


# ────────────────────────── 6 段 ──────────────────────────
SEC6 = '''<!-- 6 新闻整合 -->
<div class="dr-h" data-version="preopen-0840">6 · 新闻整合（公开源自动刷新 · 投喂精选可选 · <b class="dk-data">本版实到：10/27 08:31 抓取 284 条（覆盖 10/27 单日）· 窗口 <code>display_days = 10/26 + 10/27</code>（2 日窗 · 门槛 16 条）· 近 14 日滚动池 4,110 条 · 投喂归档 0 件</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--blue);padding:8px 12px;border-radius:6px;margin-top:6px;font-size:12.5px;line-height:1.6">
    <b>自动化说明：</b>本段主体由<b>公开新闻源自动抓取刷新</b>（东财全球 / 富途全球 / 新浪全球 / 同花顺全球 / 央视联播 / 财经早餐），按标签分类展示当日要闻，每条标注来源并附原文链接；<b>agent 投喂精选</b>为可选补充。<br>
    <b class="dk-main">本版实到</b>：<b class="dk-main">284 条</b>（10/27 08:31 抓取，覆盖 10/27 单日），分源：东财全球 <b>200</b> / 富途全球 <b>50</b> / 新浪全球 <b>20</b> / 同花顺全球 <b>20</b> / 财经早餐 <b>6</b> / 央视联播 <b>0</b>；标签分布：<b>科技 45 / 产业 43 / 宏观 38 / 政策 35 / 美股映射 3 / 持仓 0</b>。<br>
    <b class="dk-risk">🔴 本版语料的结构性特征（必须记录，因为它直接造成四象限迁移）</b>：与 10/26 的 304 条相比，本版 284 条的<b>主轴极度集中</b> ——「AI」出现 29 次、「芯片」12 次、「存储」5 次、「HBM」3 次、「算力」4 次、「创新药」4 次。<b class="dk-caution">即：隔夜外盘的存储 / 光通信行情，在 07:30–08:30 的两小时内被国内媒体全量转载，形成「同一条消息多源复述」的语料放大</b>（例：韩国央行 HBM 表态在 08:28 被 2 条并列收录、日经与 KOSPI 涨幅扩大各有 1 条）。<br>
    <b class="dk-main">当日六条主线（按时效与影响排序）</b><br>
    <b class="dk-up">① 存储 / HBM（最强，外部驱动）</b>：韩国央行官员「受 HBM 产品带动，预计明年芯片产量将上升」；韩国存储芯片股上涨（股东回报增长 + 资本开支预期）；日本芯片股大涨、铠侠 +6.8%；韩国综指涨幅扩大至 4%。<br>
    <b class="dk-up">② 光通信 / AI 算力（外部驱动）</b>：Anthropic 预计资本开支仍将大幅增长、AI 算力需求有望保持高位；OpenAI 推出 GPT-6.1 Terra。<b class="dk-caution">同一主体的表态具有双向解读（需求强 vs 成本高），本版不单边采信</b>。<br>
    <b class="dk-caution">③ 智能驾驶 / 机器人（国内催化最密）</b>：小鹏 Robotaxi 获批公开示范运营资质（智能驾驶迈向规模化落地）；大众集团（中国）取得 L3 级测试牌照（目标 2027 年实现 L3 技术就绪）；<b>反向</b>：投资避雷针提示「福莱新材、宇树科技等机器人概念股密集提示风险」。<br>
    <b class="dk-up">④ 创新药 / CXO（业绩驱动）</b>：药明康德进一步上调全年收入指引、创新药产业链持续高景气；AI 制药交易提速、临床验证成下一关口；中国生物制药两款乙肝创新药纳入突破性治疗程序。<br>
    <b class="dk-caution">⑤ 政策 / 主题</b>：广电「十五五」规划出台（明确 AI 渗透率不低于 95%）；中信证券「物理 AI 爆发，挖掘端侧机遇」；中信证券「四季度供给约束延续，大宗商品分化加深」。<br>
    <b class="dk-data">⑥ 宏观 / 市场制度</b>：三季报披露进入高峰期（10 只个股业绩大增）；债券型 ETF 年内累计流入超 2,400 亿元。<b class="dk-caution">今日 20:15 ADP 周度就业、20:30 美国 9 月数据；10/29 凌晨三央行议息</b>。<br><br>
    <b class="dk-caution">投喂状态：</b>本版<b class="dk-risk">投喂归档 0 件</b>（<code>feed/archive/2026-10-26/</code> 与 <code>feed/archive/2026-10-27/</code> 两目录均无 <code>F*.txt</code>；10/26 目录仅含<b>如实</b>的 <code>_index.json</code> · <code>feed_count: 0</code>；10/27 目录不存在）⇒ <b>如实为空、未伪造条目</b>；<code>window_latest.json</code> 的 <code>covered</code> 字段亦记录 <code>feeds: 0</code>（10/26 与 10/27 两日均 0），与 <code>feed_index.json</code>（266 条、末条 <code>F20261018-001</code>）对账一致。<b class="dk-data">语料侧实消费 = 公开新闻池 284 条（10/27 08:31）+ 近 14 日滚动池 4,110 条 + 本机研报流 60 条</b>（<code>report_analysis</code> 10/26 20:30 更新，目标池 415 只）。<b class="dk-caution">投喂与研报素材性质为「投喂语料 · 非本人持仓」，仅作本机统计判读、未原文入库、未外传</b>。</div>
  <div id="drNewsPool" style="margin-top:8px">
    <div class="dr-note">新闻池自动加载中…（数据源：output/daily_news_window.json · 缺失时回退 output/daily_news_latest.json）</div>
  </div>
</div>

'''

cut('<!-- 6 新闻整合 -->', '<div class="dr-h" data-version="close-2215">7.1 ·', SEC6, '6 段')

# ────────────────────────── 7.1 段 ──────────────────────────
SEC71 = '''<div class="dr-h" data-version="preopen-0840" data-review-date="2026-10-26" data-for-date="2026-10-27">7.1 · K3 产业信号验证（<b class="dk-up">A股 10/26 完整收盘</b> + <b class="dk-up">美股 10/26 完整收盘〔结算价〕</b> + <b class="dk-up">日韩 10/27 早盘（日经 +1.86% / KOSPI +3.77%）</b> · <b class="dk-caution">四象限 本版 5/5/9/12（上一版 0/2/14/15）· 迁移 100% 来自语料侧</b> · <b class="dk-risk">L4 = 0 席 · L3 = 1 席（食品饮料）· 28 板块 downtrend</b> · <b class="dk-up">汽车 → 可执行（唯一）</b> · <b class="dk-caution">医药生物 / 食品饮料 / 石油石化 → 有条件</b> · <b class="dk-risk">电子 / 通信 → 回避（外强内弱，不追高开）</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="k3c-legend">结论色标：<i class="l-go">可执行·相对占优</i><i class="l-cond">有条件·待确认</i><i class="l-risk">风险·回避</i><i class="l-verify">待验证变量·方法论</i></div>
  <table class="dr-tbl">
    <thead><tr><th>主题</th><th>验证</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td><b class="dk-up">汽车（本版唯一「可执行」）</b></td><td><b class="dk-up">✅ 资金分位 100.0（全市场第一）+ 催化连续两日落地 + 语料刚跨门槛</b></td><td class="dr-wrap">资金 <b class="dk-up">+11.60 亿</b>（分位 <b>100.0</b>/31 · 连续 2 日为正 · <code>共振 A</code>）、语料 18 条（刚跨 16 条门槛，此前 12 条未发酵）；催化：<b class="dk-up">10/27 小鹏 Robotaxi 获批公开示范运营资质 + 大众集团（中国）取得 L3 级测试牌照</b>（10/26 为「欧洲季度销量超日本」）；技术：<b class="dk-caution">趋势仍「下跌破位」（K 线 as_of 10-23 收 5,954.84 &lt; EMA20 6,078.16，偏离 -2.03%）</b>。<span class="k3c k3c-go"><b>「可执行·相对占优」：资金第一 + 催化连续落地 + 技术尚未修复 = 「钱先到、话刚起」的标准形态；执行口径 = 只做板块内已在 MA5 上方的个股、单板块 ≤10%、不追涨幅 &gt;5% 的标的；失效条件 = 汽车资金转负 或 板块跌破 5,900</b></span></td></tr>
      <tr><td><b class="dk-risk">电子（含存储 / 半导体设备）</b></td><td><b class="dk-risk">❌ 资金分位 0（全市场最差）+ 语料 65 条（全市场第一）⇒ 背离 B 极值</b></td><td class="dr-wrap">资金 <b class="dk-risk">-146.16 亿</b>（分位 <b>0.0</b>，连续第二日流出）；语料 <b>65 条</b>（日均 32.5，<b>因隔夜 HBM / 存储消息全量转载而单日翻倍</b>）⇒ 背离 B；技术：K 线 as_of 10-23 收 7,089.83 &lt; EMA20 7,692.16（<span class="dk-dn">-7.83%</span>），L1。<b class="dk-up">但外部全面转强：美光 +2.98% / WDC +3.63% / SKHY +4.09% / 今晨 SK하이닉스 +6.51%</b>。<span class="k3c k3c-risk"><b>「回避」：本版明确不做「外强内弱」的追高 —— 上一版已判定电子为背离 B，隔夜外盘反转不等于资金反转；恢复条件加严为「资金连续 2 日为正 + 站回 EMA20 7,692.16」，两者缺一不入。今日本板块只观察、不参与开盘首波</b></span></td></tr>
      <tr><td><b class="dk-risk">光通信 / 通信</b></td><td><b class="dk-risk">❌ 资金 -47.54 亿（分位 3.3）· 偏离 EMA20 -12.01%（31 板块最深）· 而外盘 LITE +8.19%</b></td><td class="dr-wrap">资金 <b class="dk-risk">-47.54 亿</b>（<code>双冷 D</code>）、语料 4 条；技术：K 线 as_of 10-23 收 <b>5,572.57</b> 低于 EMA20 6,333.18 达 <b class="dk-dn">-12.01%</b>；个股 10/26：剑桥科技 <b class="dk-dn">-7.89%</b>、永鼎股份 <b class="dk-dn">-6.38%</b>（均收在日内低点）。<span class="k3c k3c-risk"><b>「回避」：这是本版「内外背离极值」—— 外部三只光链标的同日涨 5.8%~8.2%，而 A股 通信资金昨日流出近 50 亿。判据：今日缺口必大，但「昨日砸盘的资金」与「今日抢反弹的资金」不同源；观察 10:00 前回补昨日跌幅 50% 以上才允许视为换手成功，否则视为出货窗口</b></span></td></tr>
      <tr><td><b class="dk-caution">计算机 / 算力</b></td><td><b class="dk-caution">⚠️ 31 板块中仅 2 席站上 EMA20 之一，但资金为负</b></td><td class="dr-wrap">资金 <b class="dk-risk">-8.42 亿</b>（分位 23.3 · 背离 B）、语料 <b>59 条</b>（日均 29.5，同因 AI 资本开支消息放大）；技术：<b class="dk-up">K 线 as_of 10-23 收 4,201.01 &gt; EMA20 4,180.49（+0.49%）· downtrend_rebound</b>。<span class="k3c k3c-verify"><b>「待验证」：技术是科技线里唯一未破位的一条，但资金未转正；升级条件 = 资金转正 ≥+10 亿 且 守住 EMA20 4,180.49（双条件），缺一不入</b></span></td></tr>
      <tr><td><b class="dk-caution">医药生物</b></td><td><b class="dk-caution">⚠️ 资金分位 96.7 + 药明康德上调全年指引，但语料仅 2 条、技术未修复</b></td><td class="dr-wrap">资金 <b class="dk-up">+7.19 亿</b>（分位 96.7 · <code>暗线 C</code> · 10/26 单日反转 24.32 亿）、语料 <b>仅 2 条</b>；技术：K 线 as_of 10-23 收 7,485.16 &lt; EMA20 7,634.55（<span class="dk-dn">-1.96%</span>）；外部：医疗 10 只 <b class="dk-up">8 涨 2 跌</b>、组内均值 <b class="dk-up">+0.77%</b>（CRL +3.45% 最强 / IQV -2.06% 最弱，10/26 完整收盘）。<span class="k3c k3c-cond"><b>「有条件」：典型「钱到话未到」（语料 2 条 = 全市场倒数第一），但今日有药明康德上调指引这一实质催化；执行口径 = 只做个股不做板块，优先 CRO / 创新药中已收复 MA10 者；升级条件 = 资金连续 2 日 ≥5 亿 + 站上 EMA20 7,634.55</b></span></td></tr>
      <tr><td><b class="dk-caution">食品饮料</b></td><td><b class="dk-caution">⚠️ 唯一 L3 + 唯一「反弹」形态 + 唯一站上 EMA20 的非科技板块</b></td><td class="dr-wrap">资金 <b class="dk-up">+2.92 亿</b>（分位 80.0 · 连续 2 日净流入）、语料 4 条；技术：K 线 as_of 10-23 收 <b class="dk-up">13,885.15 &gt; EMA20 13,750.41（+0.98%）</b> · <code>downtrend_rebound</code> · 31 板块中唯一 L3。<span class="k3c k3c-cond"><b>「有条件」：技术面仍是全市场最好的一个，但资金量级仅 2.92 亿（噪声级上沿）、语料 4 条几乎无关注；升级条件 = 单日资金 ≥5 亿且守住 EMA20 13,750.41</b></span></td></tr>
      <tr><td><b class="dk-caution">石油石化</b></td><td><b class="dk-caution">⚠️ 资金分位 93.3 + 语料 20 条，但商品端连续第三日回落</b></td><td class="dr-wrap">资金 <b class="dk-up">+6.90 亿</b>（分位 93.3 · <code>共振 A</code>）；<b class="dk-risk">但价格端：WTI 101.69 <span class="dk-dn">-1.53%</span>、布伦特 110.66 <span class="dk-dn">-0.93%</span>（10/26 收盘，连续第三日回落）</b>；技术：K 线 as_of 10-23 收 2,673.10 &lt; EMA20 2,710.10。<span class="k3c k3c-verify"><b>「待验证」：本版把解释由「油价上行」改为「成本下行利好炼化」—— 若为后者，油价跌反而是利好；判据 = 今日资金能否连续第三日为正，为正则「炼化价差」逻辑成立</b></span></td></tr>
      <tr><td><b class="dk-caution">银行</b></td><td><b class="dk-caution">⚠️ 唯一 uptrend_pullback 形态，资金微幅为正</b></td><td class="dr-wrap">资金 <b class="dk-up">+0.77 亿</b>（分位 63.3 · <code>共振 A</code>）、语料 19 条（含央行设立新工具公告）；技术：<code>uptrend_pullback</code>（31 板块唯一）。<span class="k3c k3c-verify"><b>「待验证」：昨日是「上证红」的主要贡献者之一，今日若资金转负且指数仍靠它撑 ⇒ 权重护盘逻辑退化为「单腿支撑」，需在 7.4 段兑现降仓</b></span></td></tr>
      <tr><td><b class="dk-risk">有色金属 / 国防军工</b></td><td><b class="dk-risk">❌ 语料跨门槛但资金为负（有色 -35.18 / 军工 -10.00）</b></td><td class="dr-wrap">有色金属 <b class="dk-risk">-35.18 亿</b>（语料 24 条，<b class="dk-caution">全部来自「中信 Q4 大宗展望」一篇的分拆放大</b>）；国防军工 <b class="dk-risk">-10.00 亿</b>（语料 16 条，<b class="dk-caution">样本标题实为「荷航暂停迪拜航线」，与军工无关 ⇒ 语料噪声</b>）。<span class="k3c k3c-risk"><b>「回避」：两席的语料热度均属单一来源 / 误匹配，不构成关注度上升的证据；本版只按资金侧 -35.18 / -10.00 亿判定，不作方向</b></span></td></tr>
    </tbody>
  </table>
</div>

'''

cut('<div class="dr-h" data-version="close-2215">7.1 ·', '<!-- ═══ 7.1b SECTOR-TECH-BEGIN', SEC71, '7.1 段')

# ────────────────────────── 7.3 段 ──────────────────────────
SEC73 = '''<!-- 7.3 次日开盘指引（JS 规则覆盖） -->
<div class="dr-h" data-version="preopen-0840">7.3 · K3 当日开盘指引（<b>10/27（周二）</b> · 规则自动 · <b class="dk-risk">恐慌下跌档 · 仓位区间 0%–20%</b> · <b class="dk-caution">高开回吐压力（预计 +0.6%~+1.2%）</b> · <b class="dk-up">情绪 22 维持、涨停 61 维持、大科技 -198.44 → 资金仍为负</b> · <b class="dk-caution">L4 = 0 / L3 = 1 档位未改善</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.6"><b class="dk-risk">档位说明（10/26 收盘口径，22:17 收盘快照，本版未变）</b>：情绪分 <b class="dk-risk">22「恐慌下跌」</b>（S1 18 / S2 51 / S3 18 / S4 <b class="dk-risk">0</b>）→ 档位 <b class="dk-risk">panic</b>，规则仓位区间 <b>[0%, 20%]</b>，规则附注「空仓或极轻仓等待企稳、不抄底」；<b class="dk-risk">叠加 R22 退潮档（28/31 板块低于 EMA20）上限 40% ⇒ 本版取交集仍为 <b class="dk-main">0%–20%</b></b>。<b class="dk-caution">本卡与 7.4 段、V3 版口径完全一致（方向 中性 · 置信度 中 · 风险等级 中高 · 仓位 0%–20%）；<b class="dk-risk">本版不因「隔夜外盘大涨」上调仓位 —— 档位由 A股 自身情绪与结构决定，不由外部价格决定</b></b>。<br>
  <b class="dk-main">大势预判</b>：<b class="dk-caution">高开回吐压力，预计开在 +0.6%~+1.2%</b>（方向 <b class="dk-caution">中性</b>（由「中性偏空」上调一档）· 置信度 <b>中</b> · 风险等级 <b class="dk-caution">中高</b>）；依据 = ① <b class="dk-up">真正向：美股 10/26 完整收盘三大全红（+0.28% / +0.70% / +0.82%），存储与光通信单点暴动（LITE +8.19% / AAOI +6.56% / COHR +5.83% / MU +2.98% / WDC +3.63%），日韩 10/27 早盘 KOSPI +3.77%、SK하이닉스 +6.51%、日经 +1.86%，VIX 18.39（-5.45%）</b>；② <b class="dk-risk">真负向：情绪 22 且资金分项归零、涨跌比 0.74（1,901 涨 / 2,560 跌）、跌停 37 家、主力 -299.27 亿、L4 = 0 / L3 = 1 / 28 板块 downtrend、站上 EMA20 仅 2 席</b>；③ <b class="dk-risk">资金未验证：电子 -146.16 亿（分位 0）、通信 -47.54 亿，四象限共振 5 席全部由语料跨门槛产生（flow_yi 31/31 零变化）</b>；④ <b class="dk-caution">本周未定价变量：10/29 凌晨 FOMC + 欧央行 + 日央行，10Y 5.00% 高位</b> ⇒ <b class="dk-main">「外强内弱」⇒ 定「高开回吐压力」而不定「高开延续」，定「中性」而不定「中性偏多」</b>。<br>
  <b class="dk-caution">主线策略</b>：<b class="dk-up">可执行 = 汽车（<span class="dk-up">+11.60 亿</span> · 分位 100.0 · Robotaxi + L3 双催化 · 共振 A）</b>；<b class="dk-caution">有条件 = 医药生物（+7.19 亿 · 药明康德上调指引）/ 食品饮料（唯一 L3 + 站上 EMA20 13,750.41）/ 石油石化（+6.90 亿 但油价三连跌）</b>；<b class="dk-risk">回避 = 电子（-146.16 亿 分位 0）/ 通信（-47.54 亿，偏离 EMA20 -12.01%）—— <b>含「不追今日高开的光模块与存储」</b></b>。<br>
  <b class="dk-risk">证伪条件（本卡唯一机械判据）</b>：<b class="dk-risk">若开盘 30 分钟内上证回落至 3,664.82 下方（即高开被全额吞掉）⇒ 今日「外强内弱」定性成立，仓位压至 0%、停止一切新开仓</b>；<b class="dk-caution">若高开 +0.6% 以上但 10:00 前涨幅收窄至 +0.2% 以内 ⇒ 判定「高开兑现」，不加仓、不减仓，等尾盘确认</b>；<b class="dk-up">若高开且电子资金 30 分钟内转正 ≥+20 亿 ⇒ 「外强内弱」被打破，可把仓位用至 20% 上沿（仅限汽车 / 医药两条线）</b>；<b class="dk-caution">若涨停家数 10:00 前低于 40 家（较 10/26 的 61 家萎缩三分之一以上）⇒ 情绪转冰点，按 0%–10% 执行</b>；<b class="dk-risk">若 10/29 FOMC 前 10Y 上破 5.1%（本机无法实时验证，需人工确认）⇒ 成长反弹窗口关闭，直接归 0</b>。<b class="dk-caution">详细预案见 7.4 段。</b></div>
</div>

'''

cut('<!-- 7.3 次日开盘指引（JS 规则覆盖） -->', '<!-- 7.4 操作预案 -->', SEC73, '7.3 段')

# ────────────────────────── 7.4 段 ──────────────────────────
SEC74 = '''<!-- 7.4 操作预案 -->
<div class="dr-h" data-version="preopen-0840">7.4 · 操作预案（<b class="dk-data">盘前版 08:40 · agent 详细版</b> · 面向 <b>10/27（周二）</b> · 依据 <b>A股 10/26 完整收盘</b> + <b class="dk-up">美股 10/26 完整收盘</b> + <b class="dk-up">日韩 10/27 早盘 08:43</b>）</div>
<div class="dr-card" style="font-size:12.5px;line-height:1.6">
  <div style="margin-bottom:6px"><b class="dk-main">大势预判</b>：<b class="dk-caution">中性 · 高开回吐压力</b>（预计 <b class="dk-up">+0.6%~+1.2%</b>）（置信度 <b>中</b>；风险等级 <b class="dk-caution">中高</b>；仓位 <b class="dk-risk">0%–20%</b>）</div>
  <div style="margin-bottom:6px"><b class="dk-main">关键位（10/26 实测）</b>：· <b class="dk-up">上沿 3,700 整数关</b>（10/26 日内高 3,699.01；越过后看 3,720 / 3,750）· <b class="dk-caution">中枢 3,690.48</b>（10/23 收盘 = 10/26 缺口起点，回踩不破即有效）· <b class="dk-risk">生死线 3,664.82</b>（10/26 日内低点，破则高开被全额吞掉）· <b class="dk-caution">创业板 2,601.09 / 科创50 1,305.61</b>（10/26 日内低点，破则科技反弹结束）</div>
  <div style="margin-bottom:6px"><b class="dk-main">节奏</b>：预计「<b class="dk-caution">高开（存储 / 光模块领涨）→ 10:00 前第一波抛压 → 看电子资金是否转正</b>」；<b class="dk-risk">不参与开盘首波抢反弹</b>，等两个条件之一出现：① 上证站稳 3,700 且电子资金转正 ≥+20 亿；② 高开后回踩 3,690.48 不破且 10:00 前重新向上。<b class="dk-caution">若 30 分钟内跌破 3,664.82，则「高开回吐压力」升级为「高开失效」，仓位压至 0%</b></div>
  <div style="margin-bottom:6px"><b class="dk-main">主线策略</b>：<br>
  ① <b class="dk-up">汽车（唯一「可执行」）</b>：资金分位 <b>100.0</b>（<span class="dk-up">+11.60 亿</span>·连续 2 日）+ <b>今日双催化（小鹏 Robotaxi 获批公开示范运营、大众中国 L3 测试牌照）</b> ⇒ <b class="dk-up">只做板块内已在 MA5 上方、涨幅 &lt;5% 的个股，单板块 ≤10%，不追涨停、不参与连板</b>；<b class="dk-caution">失效条件 = 汽车资金转负 或 板块跌破 5,900（10-23 收 5,954.84）</b><br>
  ② <b class="dk-caution">医药生物 / 食品饮料（有条件，只做个股）</b>：医药资金 <span class="dk-up">+7.19 亿</span>（分位 96.7）+ 药明康德上调全年指引，但语料仅 2 条、技术未修复；食品饮料唯一 L3 + 唯一站上 EMA20 ⇒ <b>两板块合计 ≤5%，优先已收复 MA10 者</b><br>
  ③ <b class="dk-risk">电子 / 通信（不追高开，只观察）</b>：<b class="dk-risk">这是本版最容易被误操作的一处 —— 隔夜 LITE +8.19%、SK하이닉스 +6.51%，但 A股 电子昨日 -146.16 亿、通信 -47.54 亿，资金未验证</b>；<b class="dk-risk">明确不做「外强内弱」的追高</b>；恢复条件分别为「资金连续 2 日为正 + 站回 EMA20 7,692.16」与「资金转正 + 收复 EMA20 6,333.18」<br>
  ④ <b class="dk-risk">纪律</b>：单板块 ≤10%、单票 ≤5%；情绪 <b class="dk-risk">22 panic</b> 下禁止一切打板 / 接力 / T+0 博弈；<b class="dk-risk">今日虽为高开日，仍按「防守日」执行，不以「外盘暴涨」为由突破 20% 总仓上限</b></div>
  <div style="margin-bottom:6px"><b class="dk-risk">回避清单</b>：① <b class="dk-risk">光模块 / 存储的「高开追涨」</b>（电子分位 0、通信分位 3.3，昨日砸盘方仍在场）② <b class="dk-risk">有色金属</b>（<span class="dk-dn">-35.18 亿</span>，语料 24 条系单一来源放大）③ <b class="dk-risk">国防军工</b>（<span class="dk-dn">-10.00 亿</span>，语料 16 条系误匹配）④ <b class="dk-risk">电力设备 / 建筑材料 / 公用事业</b>（<span class="dk-dn">-24.96 / -14.20 / -12.13 亿</span>）⑤ <b class="dk-risk">不以「TSLA +5.21%」为由做多 A股 特斯拉链、不以「Anthropic 资本开支」为由追算力、不以「共振由 0 升至 5」为由放大仓位</b></div>
  <div><b class="dk-main">五项复核结果（上一版 7.4 设定的复核项，逐条结账）</b><br>
  ✅ <b class="dk-up">① 「电子 / 计算机资金转负 + 语料维持 ⇒ 直降背离 B」——维持成立</b>：电子 <span class="dk-dn">-146.16 亿</span>（语料 65 条）、计算机 <span class="dk-dn">-8.42 亿</span>（59 条），两席仍在背离 B。<b class="dk-caution">但须记录：本条已被隔夜外盘「部分抵消」—— 资金未变，外部信号反向，构成「外强内弱」而非「双弱」</b>。<br>
  🔴 <b class="dk-risk">② 「通信连续 2 日净流入」——连续两版否决</b>：通信今日仍 <span class="dk-dn">-47.54 亿</span>，计数保持归零。<br>
  🔴 <b class="dk-risk">③ 「情绪不破 40」——已于 10/26 击穿（22）且本版未修复</b> ⇒ 仓位上限 0%–20% 维持，<b class="dk-risk">不因高开上调</b>。<br>
  ⚠️ <b class="dk-caution">④ 「10Y 是否突破 5.1%」——第三版仍无法复核（未决项）</b>：<code>comm.us10y.date</code> 仍为 <b>2026-10-23</b>（值 5.00%），源侧未刷新；<b class="dk-risk">本版保留「一票否决」条款：若 10/27 开盘前见 10Y ≥5.1%，取消全部可执行项、仅留观察（需人工确认，本机脚本不覆盖美债）</b>。<br>
  ✅ <b class="dk-up">⑤ 「美股 10/26 收盘方向」——本档已结账，且结论与上一版预设相反</b>：22:15 时设定的判据是「若收盘三大全绿且纳指跌幅超 1% ⇒ 下调为「低开破位风险」、仓位归 0」。<b>实际 = 三大全红且纳指 +0.82% 领涨 ⇒ 下调条件未触发</b>；<b class="dk-up">本版据此把方向由「中性偏空」上调至「中性」、开盘由「低开偏弱」改为「高开回吐压力」，但仓位不动（仍 0%–20%）</b> —— <b class="dk-caution">理由：上调依据全部来自外部价格，而仓位规则锚定的是 A股 自身情绪与结构，两者不同源，不同步调整</b>。<br>
  <b class="dk-caution">本版新增自设反证条件（供 10/27 收盘结账）</b>：<b class="dk-risk">若 10/27 收盘出现「电子资金继续为负（-50 亿以上）且上证收阴」，则「外强内弱」被双重确认，下一版方向下调为「偏空」、取消汽车可执行资格</b>；<b class="dk-up">反之若出现「电子资金转正 ≥+20 亿 且 通信转正」，则「传导修复」成立，下一版方向上调为「中性偏多」，仓位上限可提至 30%</b>。</div>
</div>

'''

cut('<!-- 7.4 操作预案 -->', '<!-- 8 数据自检 -->', SEC74, '7.4 段')

# ────────────────────────── 8 段（头 + 手工说明，保留 drSelfCheck 容器）──────────────────────────
SEC8 = '''<!-- 8 数据自检 -->
<div class="dr-h" data-version="preopen-0840">8 · 数据自检区（JS 自动扫描 · 各源日期一致性 · <b class="dk-up">本版已核：A股 10/26 完整收盘〔结算价〕· 美股 10/26 完整收盘〔结算价〕/ us_kline latest = 2026-10-26（对照 prev 2026-10-23 · 23/23）· 日韩 10/27 早盘 08:43 复取 · 港股 10/26 收盘 · sector_tech data_date = 2026-10-26 但 kline_last_date = 2026-10-23（源侧未发布 · kline_lag = 1）· cross_analysis.flow_date = 2026-10-26（08:41 盘前重算 · 2 日窗 · 门槛 16 条）· 温度计 2026-10-23（设计内 T-1 锚定）· VIX 2026-10-26（18.39）· 美债 2026-10-23（10Y 5.00%）</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--blue);padding:8px 12px;border-radius:6px;font-size:12.5px;line-height:1.6"><b>本段主体由 JS 自动扫描各 JSON 的 <code>date</code> / <code>data_date</code> 字段生成（下方表格），不再手工维护。</b><br>
  <b class="dk-caution">手工补充说明（七处口径差异，须与数据一致）</b>：① <code>market_thermometer.date = 2026-10-23</code>（<b class="dk-caution">属设计内 T-1 锚定</b>：乐咕当日行约北京 07:30 后才发布，盘前档取前一交易日为正常，非链路滞后；<b class="dk-caution">本档上游证书过期，温度计未能推进，已在本档数据简报中披露</b>）；② <code>vix_panel.cboe_vix</code> = <b>18.39</b>（10-26 结算 · prev 19.45 · <span class="dk-up">-5.45%</span>），<b class="dk-up">本版已推进至 10-26，上一版的 10-23 19.45 口径收口</b>；③ <b class="dk-up">A股 = 10/26 完整收盘〔结算价〕</b>（<code>market.json date = 2026-10-26</code>、<code>preopen_partial = true</code> 仅作用于 us/asia 局部，A股/港股/商品沿用收盘值）；<b class="dk-up">美股 = 10/26 完整收盘</b>（<code>us_kline.latest.date = 2026-10-26</code>，<code>quotes.us_*.time = 2026-10-26 16:00~17:15</code>，<b>非盘中</b>）；④ <b class="dk-caution">10Y 5.00% / 30Y 5.33% 为 10-23 口径（本机脚本不覆盖美债，长期缺口，非本日新增 · 连续第三版）</b>；⑤ <b class="dk-up">广度 / 情绪 / 涨停 / 主力净额 = 10/26 收盘终值</b>（<code>realtime.json meta.updated_at = 2026-10-26 22:17:07</code>、<code>market_status = closed</code>；<b>1,901 涨 / 2,560 跌 / 涨停 61 / 跌停 37 / 涨跌比 0.74 / 主力 -299.27 亿均为收盘口径</b>）；⑥ <b class="dk-caution"><code>sector_tech.kline_last_date = 2026-10-23</code> 而 <code>data_date = 2026-10-26</code>（<code>kline_lag = 1</code>）：源侧申万宏源未发布 10-26 K 线，本地缓存已与源齐平 → 已跳过 31 次逐只抓取（抓取零收益），<b class="dk-risk">故 7.1b 全部技术判定基于 10-23 收盘，若 10-26 出现形态破坏本版未能反映</b></b>；⑦ <b class="dk-caution"><code>market.json.asia.kr_stocks</code> 中 삼성전자 的 <code>traded_at</code> 为空串</b>，故仅列价格与涨跌幅、不列成交时点；<code>asia</code> 为 <b>10/27 早盘 08:43 复取</b>（首取 08:31 已于 08:43 被覆盖，两版读数均留痕于 2 段）。<b class="dk-caution">另：投喂归档 0 件（<code>feed/archive/2026-10-26/_index.json</code> 在位、<code>feed_count = 0</code>；10/27 目录不存在），<code>window_latest.covered</code> 两日 <code>feeds</code> 均为 0，与 <code>feed_index.json</code> 对账一致，如实披露、无伪造。七处均已在对应段落显式标注，无静默。</b></div>
  <div id="drSelfCheck" style="margin-top:8px">
    <div class="dr-note">自检扫描中…</div>
  </div>
</div>

'''

cut('<!-- 8 数据自检 -->', '<div id="drSelfCheck"', SEC8, '8 段（头部+手工说明）')

# ────────────────────────── 9 段 ──────────────────────────
SEC9 = '''<!-- 9 来源 -->
<div class="dr-h" data-version="preopen-0840">9 · 来源（<b class="dk-data">盘前版 08:40</b> · 复盘日 <b>2026-10-26（周一）</b> · 指引日 <b>2026-10-27（周二）</b> · 常规投喂归档 <b>0 件</b> · 语料侧实消费 <b>284 条</b> + 研报池 <b>60 条</b>）</div>
<div class="dr-card" style="font-size:12.5px;line-height:1.65">
  <b class="dk-main">一、本版素材与数据源</b><br>
  ① <b>A股</b>：<code>data/daily_review/market.json</code>（<code>date = 2026-10-26</code> · <code>updated_at = 2026-10-27 08:43:46</code> · <code>preopen_partial = true</code>（仅 us/asia 局部刷新，A股/港股/商品沿用 10/26 收盘）· 腾讯 gtimg）；<br>
  ② <b>A股广度 / 情绪 / 涨停 / 主力</b>：<code>realtime.json</code>（<code>meta.updated_at = 2026-10-26 22:17:07</code> · <code>market_status = closed</code> · 全样本 4,606 只）；<br>
  ③ <b>美股</b>：<code>market.json.us_kline</code>（<code>latest = 2026-10-26</code> / <code>prev = 2026-10-23</code> · 均为<b>完整收盘〔结算价〕</b> · 23 只）+ <code>quotes.us_*</code>（同步 10/26 收盘口径）；<br>
  ④ <b>日韩</b>：<code>market.json.asia</code>（<code>date = 2026-10-27</code> · 08:43 复取 · 新浪 znb 指数 + stock.fengle.me 韩股个股，NAVER 实时无延迟）；<br>
  ⑤ <b>港股 / 商品 / 汇率</b>：<code>market.json</code>（恒生 10/26 18:31 / 恒科 10/26 16:08；金 / 油 / 中间价 / 碳酸锂均为 10/26）；<br>
  ⑥ <b>美债</b>：<code>comm.us10y</code> / <code>comm.us30y</code>（<b>10-23</b> 口径 · 长期缺口）；<br>
  ⑦ <b>技术面</b>：<code>output/sector_tech.json</code>（<code>data_date = 2026-10-26</code> · <code>kline_last_date = 2026-10-23</code> · 31 个申万一级）；<br>
  ⑧ <b>资金 / 交叉验证</b>：<code>output/sector_flow.json</code>（<code>last_success = 2026-10-26</code> · <code>stale_days = 0</code>）+ <code>output/cross_analysis.json</code>（<b>10/27 08:41 盘前重算</b> · 2 日窗 · 583 条语料）；<br>
  ⑨ <b>新闻 / 研报</b>：<code>output/daily_news_latest.json</code>（284 条 · 10/27 08:31）+ <code>daily_news_window.json</code>（4,110 条滚动池）+ <code>report_analysis.json</code>（60 条 · 10/26 20:30）；<br>
  ⑩ <b>宏观</b>：<code>output/daily_macro_latest.json</code>（<code>date = 2026-10-27</code> · <code>as_of 08:31</code> · 百度经济日历 + 新闻兜底）；<br>
  ⑪ <b>信号 / 门控</b>：<code>output/signals.json</code>（<code>data_date = 2026-10-26</code> · 798 只 · 五福同享 1 / 四喜临门 1 / 三线共振 32）+ <code>output/gate_data.json</code> + <code>output/obs_panel.json</code>（32 只 · picks 7）。<br><br>
  <b class="dk-main">二、投喂与研报（只统计、不入库）</b><br>
  ① <b>常规投喂归档 = 0 件</b>（<code>feed/archive/2026-10-26/_index.json</code> 如实 <code>feed_count: 0</code>；<code>2026-10-27</code> 目录不存在）；<br>
  ② <b>研报流（本机统计）</b>：10/27 共 <b>57 条 / 65,252 字</b>，分源 <b>金斧头 42 / 逻辑与思考 14 / Vito行研札记 1</b>；最长篇 = Vito「Anthropic 招股书、Meta 融资风波、训练与推理算力拆解、AI 链多空与 FOMC 及三大云厂」（7,261 字）；<br>
  ③ <b>红线</b>：付费星球与订阅邮件为二手汇总，<b>只在本机统计判读，未原文入仓库、未粘贴正文、未外传</b>；token 未打印、未落盘。<b class="dk-caution">投喂与研报素材性质 = 「投喂语料 · 非本人持仓」</b>。<br><br>
  <b class="dk-main">三、边界声明</b>：本页所有个股读数均为<b>客观技术读数</b>，<b class="dk-risk">不含任何加减仓建议</b>；持仓相关标的一律标注「其他专家持股参考 · 非本人持仓」。<br>
  <b class="dk-caution">四、本版口径约束（三条，供复核）</b>：① <b>美股全部为 10/26 完整收盘价</b>，上一版的「盘中 45 分钟」口径已收口，本版 <b>0 段、3 段、5 段、7.1 段头均已显式标注</b>；② <b>板块技术的价格项统一为 K 线 as_of 2026-10-23</b>（源侧 10/26 未发布，<code>sector_tech.missing</code> 已记录，<b class="dk-up">非抓取失败</b>）；③ <b>四象限与 1 段 / 7.1 段板块资金同为 <code>flow_date = 2026-10-26</code></b>，二者可直接互证；<b class="dk-risk">四象限由 0/2/14/15 迁至 5/5/9/12 属语料侧扩容（flow_yi 31/31 零变化），不得读作资金行为变化</b>。
</div>
'''

i9 = s.index('<!-- 9 来源 -->')
s = s[:i9] + SEC9
print('  OK 9 段（至文末）')

io.open(P, 'w', encoding='utf-8-sig').write(s)
print('Part C 写盘完成：%d → %d 字符' % (orig, len(s)))
