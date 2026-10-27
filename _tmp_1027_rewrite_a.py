# -*- coding: utf-8 -*-
"""2026-10-27 盘前版（preopen-0840）analysis.html 段落重写 · Part A
顶部注释 / 顶部标签 / 0 段 / 0.5 段 / 1 段
数据日 2026-10-26 → 指引日 2026-10-27
所有替换均带唯一性断言；任一处不匹配即中止不写盘。
"""
import io

P = 'data/daily_review/analysis.html'
s = io.open(P, encoding='utf-8-sig').read()
orig = len(s)


def cut(a, b, new, label):
    global s
    assert s.count(a) == 1, '[%s] 起点锚点不唯一/缺失: %d' % (label, s.count(a))
    assert s.count(b) >= 1, '[%s] 终点锚点缺失: %d' % (label, s.count(b))
    i = s.index(a)
    j = s.index(b, i)
    s = s[:i] + new + s[j:]
    print('  OK %s  (%d → %d 字符)' % (label, j - i, len(new)))


def rep(old, new, label):
    global s
    assert s.count(old) == 1, '[%s] 目标串不唯一/缺失: %d' % (label, s.count(old))
    s = s.replace(old, new)
    print('  OK %s  (串替换)' % label)


# ────────────────────────── A. 顶部注释块 ──────────────────────────
COMMENT = '''<!--
  每日复盘 · 分析区（V2 完整结构）
  ── 行情表（drTblA/drTblH/drTblUs）= 主页面 renderDailyReview 注入 market.json 自动填充
  ── 分析内容 = 本机 agent 成品（数据可溯）
  本版: 2026-10-27 盘前版 08:40（A股 10/26 完整收盘〔结算价〕+ 美股 10/26 完整收盘〔结算价〕+ 日韩 10/27 早盘实时〔08:43 复取〕+ 港股 10/26 收盘 + 商品汇率 10/26 · 美债 10/23）→ 指引 10/27 周二当日
  上一版（10/26 收盘版 22:15 · 留痕）: A股 10/26 完整收盘 + 美股 10/26 盘中约 45 分钟〔非收盘价〕+ 日韩 10/26 收盘 → 指引 10/27；该版方向「中性偏空」、开盘「低开偏弱」、风险「中高」、仓位「0%–20%」、四象限上一版 0 / 2 / 14 / 15
  口径变更（本版核心动作）：① 美股由「10/26 盘中约 45 分钟〔非收盘价〕」推进为「10/26 完整收盘〔结算价〕」（us_kline latest = 2026-10-26，23/23 全量双日）；② 日韩由「10/26 收盘」推进为「10/27 早盘实时 08:43 复取」（日经 63,345.75 +1.86% / KOSPI 5,675.49 +3.77% / SK하이닉스 1,358,000 +6.51% / 삼성전자 223,500 +4.93%）；③ cross_analysis 于 10/27 08:41 盘前重算并补入 10/27 新闻池（窗口内语料 304 → 583 条）；④ sector_tech 同步重建（data_date 2026-10-26，kline 仍 2026-10-23，kline_lag = 1）；⑤ 新闻池 10/27 共 284 条（东财全球 200 / 富途 46 / 新浪 20 / 同花顺 12 / 财经早餐 6）；⑥ 宏观龄期整体 +1 天（CPI 12→13 天、非农 24→25 天、初请 4→5 天）；⑦ VIX 由 10-23 结算 19.45 推进至 10-26 结算 18.39（-5.45%）
  结论变更: 方向「中性偏空」→「中性」（上调一档）｜ 置信度「中高」→「中」（下调一档）｜ 开盘「低开偏弱」→「高开回吐压力」｜ 风险「中高」→「中高」（维持）｜ 仓位「0%–20%」→「0%–20%」（维持，规则锁死）；★唯一实质升级 = 隔夜外盘全面翻红且存储/光通信单点暴涨（LITE +8.19% / AAOI +6.56% / COHR +5.83% / MU +2.98% / WDC +3.63% / SKHY +4.09%）+ 韩股早盘 KOSPI +3.77%、SK하이닉스 +6.51%，上一版「外盘修复对 A股 科技链条的传导已被切断」被隔夜行情直接否证；核心矛盾由「内弱外弱」转为「外强内弱」
  口径缺口（本版显式披露）：① 10Y / 30Y 美债为 10-23 口径（5.00% / 5.33%，本机脚本不覆盖美债）；② 广度 / 情绪 / 涨停 / 主力为 10/26 收盘终值（realtime.json 22:17，非盘中读数）；③ sector_tech 的价格项统一为 K 线 as_of 2026-10-23（源侧 T+1 未发布，kline_lag = 1）；④ 投喂归档本版 0 件（2026-10-26 与 2026-10-27 两目录均无 F*.txt，feed_index feeds = 0，如实披露、未伪造）；⑤ 亚太为 08:43 复取（韩股开盘约 13 分钟 · 日经开盘约 13 分钟）；⑥ 温度计为 2026-10-23（设计内 T-1 锚定）
-->'''

a = '<!--\n  每日复盘 · 分析区（V2 完整结构）'
i = s.index(a)
j = s.index('\n-->', i) + len('\n-->')
s = s[:i] + COMMENT + s[j:]
print('  OK A. 顶部注释块')

# ────────────────────────── B. 顶部标签 ──────────────────────────
rep('''  <span class="dr-tag">分析 = 10/26 收盘版 22:15（本机 agent）</span>
  <span class="dr-tag">复盘日 2026-10-26（周一）｜ 指引日 2026-10-27（周二 · 收盘推演）</span>''',
    '''  <span class="dr-tag">分析 = 10/27 盘前版 08:40（本机 agent）</span>
  <span class="dr-tag">复盘日 2026-10-26（周一）｜ 指引日 2026-10-27（周二 · 盘前推演）</span>''',
    'B. 顶部标签')

# ────────────────────────── C. 0 段 ──────────────────────────
SEC0 = '''<!-- 0 结论先行 -->
<div class="dr-h" data-preopen="1" data-version="preopen-0840" data-review-date="2026-10-26" data-for-date="2026-10-27">0 · 结论先行（速览卡 · <b>10/27 周二当日指引</b> · <b class="dk-data">盘前版 08:40</b> · 复盘日 <b class="dk-main">10/26（周一）</b> · A股 10/26 完整收盘〔结算价〕+ <b class="dk-up">美股 10/26 完整收盘〔结算价〕</b> + <b class="dk-up">日韩 10/27 早盘实时（08:43 复取）</b> · 港股 10/26 收盘 · 商品汇率 10/26 · 美债 10/23）</div>
<div class="dr-card" style="margin-top:4px">
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:6px 0">
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">10/27 开盘预判</div><div style="font-weight:700;font-size:12.5px"><b class="dk-caution">高开回吐压力</b></div><div style="font-size:12.5px;color:var(--text-muted)">预计开在 <b class="dk-up">+0.6%~+1.2%</b>（3,720–3,742）· 方向判定 <b class="dk-caution">中性</b>（由「中性偏空」上调一档）· 置信度 <b>中</b></div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">核心矛盾</div><div style="font-weight:700;font-size:12.5px"><b class="dk-caution">外强 / 内弱</b></div><div style="font-size:12.5px;color:var(--text-muted)">隔夜美股三大全红 + 韩股 <b class="dk-up">+3.77%</b>，而 A股 内部情绪 <b class="dk-risk">22</b>、L4 <b class="dk-risk">= 0</b>、<b class="dk-risk">28/31</b> 板块仍处下行结构</div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">风险 / 仓位</div><div style="font-weight:700;font-size:12.5px"><b class="dk-risk">中高 · 0%–20%</b></div><div style="font-size:12.5px;color:var(--text-muted)">L2「恐慌下跌」规则区间 <b>[0%, 20%]</b> 锁死上限，<b class="dk-risk">不因高开上调</b></div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">四象限（本版现算）</div><div style="font-weight:700;font-size:12.5px"><b class="dk-up">5 / 5 / 9 / 12</b></div><div style="font-size:12.5px;color:var(--text-muted)">共振 <b>5</b>（上一版 0）· 但 <code>flow_yi</code> <b class="dk-up">31/31 逐项零变化</b> ⇒ 纯语料侧扩容，<b class="dk-risk">不构成加仓依据</b></div></div>
  </div>
  <div style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">① 一句话结论</b>：今日定性 = <b class="dk-caution">「外部单点强修复 + 内部结构未修复」</b>。<b class="dk-up">开盘方向确定性高</b>（存储 / 光通信 / CPO 高开已成定局），<b class="dk-risk">但持续性存疑</b>（内部无一个板块处上升趋势、情绪处最低档）。<b class="dk-caution">执行口径 = 只做回踩不追高开首波</b>。<br>
    <b class="dk-main">② 隔夜外部证据（本版最重要的改判来源）</b>：美股 10/26 <b>完整收盘</b>三大指数全红 —— 道指 52,361.58 <span class="dk-up">+0.28%</span> / 标普 7,676.77 <span class="dk-up">+0.70%</span> / 纳指 26,169.38 <span class="dk-up">+0.82%</span>；<b class="dk-up">存储与光通信是单点暴动</b>：LITE <span class="dk-up">+8.19%</span>、AAOI <span class="dk-up">+6.56%</span>、COHR <span class="dk-up">+5.83%</span>、SKHY <span class="dk-up">+4.09%</span>、WDC <span class="dk-up">+3.63%</span>、MU <span class="dk-up">+2.98%</span>；日韩 10/27 早盘延续 —— <b class="dk-up">KOSPI 5,675.49 <span class="dk-up">+3.77%</span>（开盘 +3.46%）</b>、日经 63,345.75 <span class="dk-up">+1.86%</span>、<b class="dk-up">SK하이닉스 +6.51%（1,358,000）</b>、삼성전자 <span class="dk-up">+4.93%</span>、<b>日本铠侠 +6.8%</b>；催化 = <b>韩国央行「受 HBM 产品带动，明年芯片产量将上升」+ 韩国存储股受股东回报与资本开支预期提振</b>。<br>
    <b class="dk-risk">③ 内外错位（本版核心结构事实）</b>：<b>A股 10/26 恰恰是存储 / 光通信的杀跌日</b> —— 剑桥科技 <span class="dk-dn">-7.89%</span>、永鼎股份 <span class="dk-dn">-6.38%</span>、华工科技 <span class="dk-dn">-2.98%</span>，电子板块主力 <span class="dk-dn">-146.16 亿</span>（分位 <b>0</b>，全市场流出第一）。⇒ <b class="dk-caution">今日缺口性质 = 「修复性缺口」（补隔夜外盘）而非「趋势性缺口」（新资金进场）</b>；<b class="dk-risk">两者的区别在于「有没有承接」——修复性缺口回补概率高，追进去等于给昨日出逃资金接盘</b>。<br>
    <b class="dk-risk">④ 反面约束（不得因高开解除）</b>：情绪分 <b class="dk-risk">22「恐慌下跌」</b>（S1 18 / S2 51 / S3 18 / S4 <b>0</b>，资金分项已归零）、涨跌比 <b class="dk-risk">0.74</b>（1,901 涨 / 2,560 跌）、跌停 <b class="dk-risk">37</b> 家、全市场主力 <span class="dk-dn">-299.27 亿</span>、两市成交 <b>13,513.3 亿</b>、<b class="dk-risk">L4 = 0 席 / L3 = 1 席（仅食品饮料）/ 28 个板块 downtrend / 站上 EMA20 仅 2 席</b>、美债 10Y <b class="dk-risk">5.00%</b>（10-23 口径）、本周 <b class="dk-caution">10/29 凌晨 FOMC + 欧央行 + 日央行三央行议息</b>。<br>
    <b class="dk-main">⑤ 关键位（10/26 实测）</b>：· <b class="dk-up">上沿 3,700 整数关</b>（10/26 日内高 3,699.01，高开越过后看 3,720 / 3,750）· <b class="dk-caution">中枢 3,690.48</b>（10/23 收盘 = 10/26 缺口起点，回踩不破即有效）· <b class="dk-risk">生死线 3,664.82</b>（10/26 日内低点，破则今日高开被全额吞掉）。<b class="dk-caution">创业板 / 科创50 是今日主战场（昨日 -1.71% / -2.23%），若科技高开后 30 分钟不能站稳昨收上方，则整体判为「一日游」</b>。
  </div>
</div>

'''

cut('<!-- 0 结论先行 -->', '<!-- 0.5 深度判读 -->', SEC0, 'C. 0 段')

# ────────────────────────── D. 0.5 段 ──────────────────────────
SEC05 = '''<!-- 0.5 深度判读 -->
<div class="dr-h" data-version="preopen-0840">0.5 · 深度判读（<b class="dk-data">四象限现场现算</b> · <code>output/cross_analysis.json</code> 生成于 <b>2026-10-27 08:41</b> · <code>flow_date = 2026-10-26</code> · 2 日新闻窗口 · 门槛 16 条 · <b class="dk-up">本版 5 / 5 / 9 / 12</b>（上一版 0 / 2 / 14 / 15）· <b class="dk-risk">迁移 100% 来自语料侧</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:6px 0">
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-left:3px solid var(--red);border-radius:8px;padding:8px 10px">
      <div style="font-weight:700;font-size:12.5px"><b class="dk-up">共振 A = 5</b>（资金流入 + 语料热）</div>
      <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.6">汽车 <span class="dk-up">+11.60 亿</span>（语料 18 条）· 石油石化 <span class="dk-up">+6.90 亿</span>（20 条）· 传媒 <span class="dk-up">+3.69 亿</span>（27 条）· 机械设备 <span class="dk-up">+1.85 亿</span>（20 条）· 银行 <span class="dk-up">+0.77 亿</span>（19 条）。<b class="dk-caution">上一版为 0 席，本版 5 席全部由「暗线 C 跨过 16 条语料门槛」升格，无一是资金新增</b></div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-left:3px solid var(--green);border-radius:8px;padding:8px 10px">
      <div style="font-weight:700;font-size:12.5px"><b class="dk-risk">背离 B = 5</b>（语料热 + 资金撤）</div>
      <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.6">电子 <span class="dk-dn">-146.16 亿</span>（语料 65 条 · 全市场第一）· 有色金属 <span class="dk-dn">-35.18 亿</span>（24 条）· 国防军工 <span class="dk-dn">-10.00 亿</span>（16 条）· 计算机 <span class="dk-dn">-8.42 亿</span>（59 条）· 非银金融 <span class="dk-dn">-6.60 亿</span>（24 条）。<b class="dk-risk">电子 / 计算机 = 「外强内弱」最危险组合：隔夜外盘暴涨而资金昨日刚撤</b></div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-left:3px solid var(--blue);border-radius:8px;padding:8px 10px">
      <div style="font-weight:700;font-size:12.5px"><b class="dk-data">暗线 C = 9</b>（资金流入 + 语料冷）</div>
      <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.6">医药生物 <span class="dk-up">+7.19 亿</span> · 美容护理 <span class="dk-up">+4.44 亿</span> · 房地产 <span class="dk-up">+4.38 亿</span> · 食品饮料 <span class="dk-up">+2.92 亿</span> · 商贸零售 +1.50 亿 · 综合 +0.86 亿 · 纺织服饰 +0.84 亿 · 轻工制造 +0.65 亿 · 社会服务 +0.64 亿。<b class="dk-caution">「钱先到、话未到」的组合池，是当前唯一可低吸方向（但量级均为个位数亿）</b></div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-left:3px solid var(--text-muted);border-radius:8px;padding:8px 10px">
      <div style="font-weight:700;font-size:12.5px"><b class="dk-neutral">双冷 D = 12</b>（资金撤 + 语料冷）</div>
      <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.6">通信 <span class="dk-dn">-47.54 亿</span> · 电力设备 <span class="dk-dn">-24.96 亿</span> · 建筑材料 · 公用事业 · 家用电器 · 基础化工 · 建筑装饰 · 交通运输 · 煤炭 · 钢铁 · 农林牧渔 · 环保。<b class="dk-risk">通信最刺眼：隔夜 LITE +8.19% 而 A股 通信资金昨日 -47.54 亿、偏离 EMA20 -12.01%</b></div></div>
  </div>
  <div style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">迁移主因（本版必须显式定性）</b>：四象限由上一版 <b>0 / 2 / 14 / 15</b> 变为本版 <b>5 / 5 / 9 / 12</b>，八个板块发生迁移 —— <b class="dk-up">暗线→共振 5 席</b>（汽车 / 石油石化 / 传媒 / 机械设备 / 银行）、<b class="dk-risk">双冷/暗线→背离 3 席</b>（有色金属 11→24 条、国防军工 11→16 条、非银金融 9→24 条）。<b class="dk-risk">判据：<code>flow_yi</code> 31/31 逐板块逐项零变化（已全量比对上一版与重算版）</b>，唯一变量是 <b>新闻窗口由 304 条扩至 583 条（+91.8%）</b>，各板块语料同步翻倍并跨过 16 条门槛。<br>
    <b class="dk-up">⇒ 定性 = 纯语料侧扩容（口径变化），不是资金行为变化</b>。<b class="dk-risk">因此：① 不得读作「资金开始回流」；② 不得据此上调仓位；③ 本版仓位维持 0%–20%，不因共振由 0 升至 5 而放宽</b>。真正可用的信号仍是 <b class="dk-main">资金分位</b>：汽车 100.0（全市场第一）/ 医药生物 96.7 / 石油石化 93.3 / 美容护理 90.0，而电子 0.0 / 通信 3.3 为末位。<br>
    <b class="dk-caution">另须披露一处语料噪声</b>：本轮 10/27 新闻池以半导体 / 存储 / AI 算力为绝对主轴（「AI」29 条、「芯片」12 条、「存储」5 条、「HBM」3 条），按标题关键词匹配时出现<b>跨板块串味</b> —— 例：传媒 27 条样本标题实为「韩国存储芯片股上涨」「Anthropic 资本开支」，非银金融 24 条同源。<b class="dk-risk">故传媒 / 非银 / 机械设备三席的「共振 / 背离」标签语料侧可信度低，本版只按资金侧（传媒 +3.69 亿 / 机械设备 +1.85 亿 / 非银 -6.60 亿）解读，不按标签解读</b>。<br>
    <b class="dk-data">口径恒等式（供复核）</b>：<code>cross_analysis.flow_date = 2026-10-26</code> = <code>sector_flow.last_success</code> = <code>sector_tech.flow_date</code>；<code>sector_flow.source_status.stale_days = 0</code>（资金维无滞后，<b class="dk-up">无需以价格侧替代</b>）。
  </div>
</div>

'''

cut('<!-- 0.5 深度判读 -->', '<!-- 1 昨日 A 股走势总结 -->', SEC05, 'D. 0.5 段')

# ────────────────────────── E. 1 段 ──────────────────────────
SEC1 = '''<!-- 1 昨日 A 股走势总结 -->
<div class="dr-h" data-version="preopen-0840">1 · 上一交易日（<b class="dk-main">10/26 周一</b>）A 股走势总结（<b class="dk-data">完整收盘〔结算价〕</b> · <code>market.json date = 2026-10-26</code> · 广度/情绪为收盘后补抓终值〔<code>realtime.json</code> 22:17〕· <b class="dk-risk">分裂日：指数维稳、个股普跌、成长破位</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag" style="margin-bottom:4px">主要指数（10/26 收盘 · 腾讯 gtimg）</div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>指数</th><th>收盘</th><th>涨跌</th><th>日内高 / 低</th><th>成交（亿）</th><th>读数</th></tr></thead>
    <tbody>
      <tr><td><b>上证指数</b></td><td>3,697.52</td><td><b class="dk-up">+0.19%</b></td><td>3,699.01 / 3,664.82</td><td>7,465.3</td><td class="dr-wrap"><b>距日内高仅 1.49 点收出</b>，权重（银行 / 石油石化 / 汽车）托举的「维稳红」</td></tr>
      <tr><td>沪深300</td><td>4,103.54</td><td><span class="dk-dn">-0.04%</span></td><td>4,107.79 / 4,057.56</td><td>4,562.5</td><td class="dr-wrap">几乎收平，说明「上证红」并非全市场共识，仅少数权重贡献</td></tr>
      <tr><td><b>深证成指</b></td><td>11,534.38</td><td><b class="dk-dn">-1.19%</b></td><td>11,638.79 / 11,432.29</td><td>8,622.7</td><td class="dr-wrap">全天单边下行，无有效反抽</td></tr>
      <tr><td><b>创业板指</b></td><td>2,638.23</td><td><b class="dk-dn">-1.71%</b></td><td>2,671.81 / 2,601.09</td><td>4,281.4</td><td class="dr-wrap">日内低 2,601.09，<b class="dk-risk">2,600 整数关一度告急</b></td></tr>
      <tr><td><b>科创50</b></td><td>1,315.50</td><td><b class="dk-dn">-2.23%</b></td><td>1,335.92 / 1,305.61</td><td>817.0</td><td class="dr-wrap"><b>跌幅最深</b>，半导体权重直接承受「电子 -146.16 亿」</td></tr>
      <tr><td>中证500</td><td>6,712.73</td><td><span class="dk-dn">-1.49%</span></td><td>6,787.32 / 6,674.40</td><td>2,785.0</td><td class="dr-wrap">中小盘同步走弱，与「国家队只护沪深300」的结构一致</td></tr>
      <tr><td>北证50</td><td>963.95</td><td><span class="dk-dn">-2.13%</span></td><td>983.83 / 962.26</td><td>144.3</td><td class="dr-wrap">成交仅 144.3 亿，流动性继续萎缩</td></tr>
    </tbody>
  </table>
  <div style="font-size:12.5px;line-height:1.6;margin-top:6px">
    <b class="dk-main">① 广度与情绪（10/26 收盘终值 · <code>realtime.json</code> · <code>market_status = closed</code>）</b><br>
    全样本 <b>4,606</b> 只：上涨 <b class="dk-dn">1,901</b> / 下跌 <b class="dk-risk">2,560</b> / 平盘 145，<b class="dk-risk">涨跌比 0.74</b>（10/23 为 4.74 ⇒ 一日由普涨转普跌）；涨停 <b>61</b> / 跌停 <b class="dk-risk">37</b>（10/23 为 12，<b class="dk-risk">跌停家数三倍化</b>）；全市场主力净额 <b class="dk-risk">-299.27 亿</b>；两市成交额 <b>13,513.3 亿</b>。<br>
    情绪分 <b class="dk-risk">22「恐慌下跌」</b>（S1 涨跌比 18 / S2 涨停 51 / S3 指数强度 18 / S4 资金 <b class="dk-risk">0</b>）⇒ L2 规则仓位区间 <b class="dk-risk">[0%, 20%]</b>，附注「空仓或极轻仓观望，不抄底，等企稳信号」。<b class="dk-caution">四个分项中「资金」已归零，是 9 月以来首次</b>。<br><br>
    <b class="dk-main">② 结构判断（本段结论）</b>：这是<b class="dk-risk">「指数维稳 + 个股普跌 + 成长破位」的三重分裂</b>。三个证据同向：<b>① 上证 +0.19% 靠银行 / 石油石化 / 汽车三条腿，而深成 / 创业板 / 科创50 / 北证全线跌超 1.19%</b>；<b>② 涨跌比 0.74 但涨停仍有 61 家</b> ⇒ 题材资金尚未退场，只是拒绝扩散；<b>③ 跌停 37 家集中在高位科技股</b>（剑桥科技 -7.89%、永鼎股份 -6.38% 为光模块 / 光通信代表）。<br>
    <b class="dk-caution">⇒ 本版对该结构的用法</b>：<b>它不构成「今日必跌」的理由，也不构成「超跌必反弹」的理由</b> —— 隔夜外盘已给出强修复信号（见 3 段），但内部结构（L4 = 0 / 28 下行 / 情绪 22）说明<b>承接力仍未恢复</b>；两者的合力 = <b class="dk-caution">高开、但高开后的第一波抛压必须被吃掉</b>。<br><br>
    <b class="dk-main">③ 个股读数（其他专家持股参考 · 非本人持仓 · 仅客观读数，不含任何加减仓建议）</b>
  </div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>标的</th><th>收盘</th><th>涨跌</th><th>板块归属</th><th>板块主力</th><th>客观读数</th></tr></thead>
    <tbody>
      <tr><td>长鑫科技</td><td>42.66</td><td><span class="dk-dn">-0.44%</span></td><td>存储 / 半导体</td><td><span class="dk-dn">电子 -146.16 亿</span></td><td class="dr-wrap"><b>全池最抗跌</b>：板块资金分位 0 而个股仅微跌 0.44% ⇒ 主力撤出但有承接；<b class="dk-caution">隔夜美光 +2.98% / SKHY +4.09%，本标的今日开盘缺口方向由外部定价</b></td></tr>
      <tr><td>华工科技</td><td>72.36</td><td><span class="dk-dn">-2.98%</span></td><td>激光 + 光模块</td><td><span class="dk-dn">电子 -146.16 亿</span></td><td class="dr-wrap">自 74.58 继续下挫，日内低 71.46；<b>与隔夜 LITE +8.19% / COHR +5.83% 方向完全相反</b> ⇒ 今日为「外盘定价缺口」的典型标的</td></tr>
      <tr><td>永杉锂业</td><td>11.00</td><td><span class="dk-dn">-1.96%</span></td><td>锂电 / 有色</td><td><span class="dk-dn">有色金属 -35.18 亿</span></td><td class="dr-wrap">碳酸锂主连 95,280（10/26 广期所）持平上一版读数；板块资金流出第二 ⇒ <b class="dk-dn">价格与资金双弱</b>，无外部对冲项</td></tr>
      <tr><td>剑桥科技</td><td>145.89</td><td><b class="dk-dn">-7.89%</b></td><td>光模块</td><td><span class="dk-dn">电子 -146.16 亿</span></td><td class="dr-wrap"><b>全池跌幅第一</b>：日内高 156.00 → 低 145.00 收在最低，<b class="dk-risk">跌停附近收盘，形态破坏</b>；隔夜外盘光模块暴涨 ⇒ <b class="dk-caution">今日高开幅度可能最大，但「昨日砸盘的资金」与「今日抢反弹的资金」不是同一批</b></td></tr>
      <tr><td>永鼎股份</td><td>26.14</td><td><b class="dk-dn">-6.38%</b></td><td>光通信 / 光纤</td><td><span class="dk-dn">通信 -47.54 亿</span></td><td class="dr-wrap">跌幅第二，与剑桥同属光链；<b>通信板块双冷 D（资金 -47.54 亿 + 语料 4 条）</b>，是本轮「外强内弱」最极端的板块</td></tr>
      <tr><td>昊华科技</td><td>34.67</td><td><span class="dk-dn">-2.12%</span></td><td>化工 / 氟材料</td><td><span class="dk-dn">基础化工 -5.85 亿</span></td><td class="dr-wrap">板块双冷 D、语料 1 条；无外部催化，跟随大盘 beta</td></tr>
      <tr><td>ST万邦</td><td>11.28</td><td><b class="dk-up">+2.55%</b></td><td>医药 / ST</td><td><span class="dk-up">医药生物 +7.19 亿</span></td><td class="dr-wrap"><b>全池唯一上涨</b>：医药生物资金分位 96.7（流入第二）⇒ 与板块资金同向，属「钱先到」的受益标的</td></tr>
    </tbody>
  </table>
  <div class="dr-note"><b class="dk-caution">口径提示</b>：本节全部为 10/26 <b>完整收盘〔结算价〕</b>读数；<b>不含 10/27 早盘任何数据</b>（A股 09:30 才开盘）。个股为「其他专家持股参考 · 非本人持仓」，只给客观技术读数，<b class="dk-risk">不含任何加减仓建议</b>。</div>
</div>

'''

cut('<!-- 1 昨日 A 股走势总结 -->', '<!-- 1.1 当日 TOP10 -->', SEC1, 'E. 1 段')

io.open(P, 'w', encoding='utf-8-sig').write(s)
print('Part A 写盘完成：%d → %d 字符' % (orig, len(s)))
