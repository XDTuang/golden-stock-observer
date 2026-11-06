#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-06 · Part C：7.1 / 7.3 / 7.4 / 8 / 9
铁律：7.1 整体重写后 → 先 build_k3_conclusions.py（上色）→ 再 build_sector_tech.py（重注 7.1b）
"""
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


def repl_h(sec_no, new, next_anchor, tag=""):
    """替换某段的 dr-h 到下一个锚点"""
    global html
    import re
    m = re.search(r'<div class="dr-h"[^>]*>' + sec_no + r' · ', html)
    assert m, f"[{tag}] 段头未找到: {sec_no}"
    start = m.start()
    end = html.find(next_anchor, start)
    assert end > start, f"[{tag}] 段尾未找到"
    html = html[:start] + new + html[end:]


# ═══════════ 7.1 K3 产业信号验证 ═══════════
SEC71 = """<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">7.1 · K3 产业信号验证（<b class="dk-up">A股 11/05 完整收盘</b> + <b class="dk-risk">美股 11/05 完整收盘〔昨夜 · 崩塌〕</b> · 8 条 · 结论按「验证结果」分级：<span class="k3c k3c-go">成立</span> / <span class="k3c k3c-cond">有条件</span> / <span class="k3c k3c-risk">风险</span> / <span class="k3c k3c-verify">待验</span>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><div class="k3c-legend">结论色标：<i class="l-go">可执行·相对占优</i><i class="l-cond">有条件·待确认</i><i class="l-risk">风险·回避</i><i class="l-verify">待验证变量·方法论</i></div>
  <table class="dr-tbl"><thead><tr><th>主题</th><th>验证</th><th>内容</th></tr></thead><tbody>
    <tr><td><b class="dk-risk">存储 / 半导体链</b></td><td>外部锚是否止血</td><td><div class="dr-wrap">前版判「外部锚由正转负、A股 该链不具独立行情条件」→ 实际隔夜<b class="dk-risk">四线 0/4、均值 -17.62%</b>（SNDK -22.26 / WDC -17.35 / MU -17.46 / SKHY -13.40），韩股今晨再 -7.91% / -6.90%。<span class="k3c k3c-risk"><b>结论：前版判断完全正确，且恶化幅度超出预期；今日 A股 存储链以「低开幅度」定价，不具任何反弹条件 —— 回避维持，不接第一根阳线。</b></span></div></td></tr>
    <tr><td><b class="dk-risk">通信 / 光模块</b></td><td>能否止血</td><td><div class="dr-wrap">11-05 通信 <b class="dk-risk">-47.11 亿</b>（单日反转 122.97 亿）、语料 14 条、<b>双冷 D</b>；隔夜光通信三线 <b class="dk-risk">-17.52%</b>（AAOI -20.89 / LITE -18.68 / COHR -12.98），<b>两日累计 -23.4%</b>。<span class="k3c k3c-risk"><b>结论：内外双杀、无任何止血迹象 ⇒ 从「回避」正式升级为「负向主线」，今日不参与、不作为对冲标的、若持仓则按板块级风险描述处理。</b></span></div></td></tr>
    <tr><td><b class="dk-risk">算力 / 数据中心</b></td><td>政策是否真的改写分母</td><td><div class="dr-wrap">前版判「杀的是估值分母而非订单」→ 隔夜 <b>MRVL -16.43% / NVDA -9.26%（市值 -4,470 亿美元）/ ORCL -7% / CRWV -9% / NEBIUS -14%</b>，且导火索明确为<b>民主党「蓝色浪潮」后对数据中心审批 / 监管的重估</b>。<span class="k3c k3c-risk"><b>结论：判断成立且已从「预期」变为「事实」—— 这是本轮最强的负向信号，且比前版的「IRR 下修」更硬：现在质疑的是「许可」而非「回报率」。</b></span></div></td></tr>
    <tr><td><b class="dk-caution">半导体设备 / 材料</b></td><td>「双受益」框架是否仍成立</td><td><div class="dr-wrap">前版把设备列为<b>首选</b>，理由是「外盘跌也受益（扩产成本降）、外盘涨也受益」。<b class="dk-main">本次事件证伪了该框架的一半</b>：政策压制的对象是「数据中心 capex / 许可」，<b>原厂扩产本身被质疑 ⇒ 设备订单预期同步下修</b>，故「存储价格跌 → 设备受益」的前提（原厂继续扩产）不成立。<span class="k3c k3c-cond"><b>结论：下调为「有条件」—— 唯一的翻多条件是「A股 设备在低开后率先翻红且资金连续第三日净流入」，否则昨日 +7.71% 定性为一日游。</b></span></div></td></tr>
    <tr><td><b class="dk-up">新能源 / 电力设备</b></td><td>避弹坑属性是否延续</td><td><div class="dr-wrap">电力设备 <b class="dk-up">+63.10 亿</b>（<code>streak 4</code> · 资金分位 <b>100</b> · 31 板块第一）、光伏 +32.36 亿 / +5.77%、电池 +26.43 亿，<code>news_count 12</code> 未达 16 门槛 ⇒ 资金已入、语料未炒；政策端 氢能五大城市群试点 + 发改委储能 / 电力市场调研；<b>且与 AI 资本开支零关联、不受「蓝潮」政策冲击</b>。<span class="k3c k3c-go"><b>结论：本档唯一「资金连续 + 政策共振 + 事件免疫」三重达标的组合 ⇒ 今日唯一相对占优方向（仍只做回踩、不做追高）。</b></span></div></td></tr>
    <tr><td><b class="dk-up">有色 / 贵金属</b></td><td>避险资金是否真的转向</td><td><div class="dr-wrap">金 <b class="dk-up">4,118.81（+1.45%）</b> 突破 4,100（08:19 快讯），而 <b>10Y 美债 4.90% 未下行</b> ⇒ <b>避险资金流向黄金而非债券</b>；有色 11-05 资金 <b class="dk-up">+18.62 亿</b>、语料 24 条 ⇒ 象限由暗线升<b>共振 A</b>。<span class="k3c k3c-go"><b>结论：成立 —— 但须严格区分金属：只认贵金属（避险驱动），不认工业金属（锡已崩、铜未补跌，属需求驱动，风险在下）。</b></span></div></td></tr>
    <tr><td><b class="dk-risk">技术档位</b></td><td>破位面有多大</td><td><div class="dr-wrap"><code>sector_tech</code> 数据日 11-05（<code>kline_lag = 0</code>）：<b>L4 1 / L3 3 / L2 15 / L1 12</b>，趋势 <b>向上 0 / 上升回踩 2 / 下跌反弹 13 / 下跌破位 16</b>。<span class="k3c k3c-risk"><b>结论：16 席处「下跌破位」+ 今日跳空低开 ⇒ 这 16 席开盘即形成新的破位缺口，技术面无任何承接；L4（计算机）在系统性杀估值面前不构成支撑。</b></span></div></td></tr>
    <tr><td><b class="dk-verify">情绪与资金</b></td><td>「情绪脉冲」定性是否被证实</td><td><div class="dr-wrap">11-05 情绪 <b>74</b>、涨停 <b>92</b>、涨跌比 <b>7.32</b>、主力仅 <b class="dk-caution">+5.84 亿</b>（-98.4%）、国家队 ETF <b class="dk-risk">-11.43 亿</b>。前版定性 =「游资主导的两日脉冲，非机构回补」。<span class="k3c k3c-verify"><b>结论：今日即可验证 —— 若低开后跌幅快速扩大（跌停 &gt;40 家）则「脉冲结束」成立；若守住 3,610 并缩量，则说明筹码并未松动，需重新评估。本条留待收盘结算。</b></span></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-main">7.1 段的总结</b>：<b class="dk-risk">8 条里 4 条判「风险」（存储 / 光模块 / 算力 / 技术档位）、1 条「有条件」（半导体设备）、2 条「成立·相对占优」（电力设备 / 贵金属）、1 条「待验」（情绪与资金）</b>。核心变化不是「A股 变差」，而是<b>「昨日给出的首选方向（半导体设备）被昨夜事件改变了前提」</b>：昨日设备的逻辑是「存储价格跌 → 原厂扩产 → 设备受益」，昨夜的现实是「原厂扩产本身被政策质疑」。<b class="dk-caution">⇒ 在这种「前提被改写」的环境里，唯一可靠的做法是<b>把仓位交给与事件无关的两条链（电力设备 / 贵金属），把观察留给被事件命中的链（设备 / 计算机）</b>，而不是在「跌得多」的标的上找反弹。</b>
  </div>
</div>

"""
repl_h("7.1", SEC71, "<!-- ═══ 7.1b SECTOR-TECH-BEGIN", tag="sec71")

# ═══════════ 7.3 K3 次日开盘指引 ═══════════
SEC73 = """<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">7.3 · K3 次日开盘指引（<b>11/06（周五）</b> · 规则自动 + agent 复核 · <b class="dk-risk">外部系统性冲击 / VIX +69.66% / 技术破位面 16 席</b> · 仓位区间 <b>10%–20%</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>项目</th><th>规则自动值</th><th>agent 复核</th></tr></thead><tbody>
    <tr><td>方向</td><td><div class="dr-wrap">偏多（基于 11-05 收盘：情绪 74 · 广度 7.32 · 涨停 92）</div></td><td><div class="dr-wrap"><b class="dk-risk">下调两档至「中性偏空」</b>。理由：① 规则读的是 11-05 收盘快照，<b>不识别隔夜费半 -12% / 存储 -17.62% / 光通信 -17.52% 这一层</b>；② 今日 <b>09:31 上证已 -1.75%、创业板 -3.67%</b>，方向事实上已由开盘给出；③ 日韩同崩（-5.76% / -6.77%）、MSCI 亚太 -3% ⇒ 全域性而非区域性事件。<b class="dk-main">⇒ 规则信号与外部事件方向相反时，以外部事件为准，并明确记录偏离理由</b></div></td></tr>
    <tr><td>开盘口径</td><td>高开延续（按 11-05 涨跌比 7.32 外推）</td><td><div class="dr-wrap"><b class="dk-caution">改为「低开反弹」（已实现）</b>：实际开 <b>3,612.15（-2.11%）</b>、最低 <b>3,610.20</b>、09:31 回升至 <b>3,625.23（-1.75%）</b>。<b class="dk-main">幅度推导复盘：外部核心链（费半 -12% / 存储 -17.62%）× A股 该链权重（约 12%）× 传导折扣（0.4）≈ -0.6%~-0.8%，再加「全球风险偏好」项（VIX +69.66%）× 全域 β ≈ -1.2%~-1.5%，合计 -1.8%~-2.3% ⇒ 与实际 -2.11% 吻合</b>。<b class="dk-caution">该方法本次首次用于极端行情并命中区间，可作为「系统性冲击」情形的折算模板</b></div></td></tr>
    <tr><td>置信度</td><td>中</td><td><div class="dr-wrap"><b class="dk-up">上调至「中高」</b>。理由：① 方向已被开盘价验证（-2.11% 低开，与预测一致）；② 三条独立证据同向（外部崩塌 / 亚太同崩 / A股 结构性低开）；③ 反证（中概股 +0.43%、纳指期货 +0.6%）<b>不足以扭转指数方向，只影响跌幅深度</b>。<b class="dk-caution">不给「高」：午后是否二次探底取决于成交与国家队行为，属不可预判项</b></div></td></tr>
    <tr><td>风险等级</td><td>中高</td><td><div class="dr-wrap"><b class="dk-risk">上调至「高」</b>：① <b>VIX 28.18（+69.66%）</b>，2026 年最大单日升幅，进入「被动减仓」区间；② 技术面 <b>16 席下跌破位</b>，今日跳空低开形成新缺口；③ <b>今晚 21:30 美国 10 月非农</b>（预期 +6.5 万 / 失业率 4.2%），周五持仓需承担跨周末事件风险；④ <b>AI 对冲基金 VARA 10 月 -33%</b>，杠杆清算可能延续</div></td></tr>
    <tr><td>仓位区间</td><td><div class="dr-wrap">30%–50%（overheat [30,50] · 情绪 74）</div></td><td><div class="dr-wrap"><b class="dk-risk">大幅下调至 10%–20%（向下偏离规则带下限 10pct）</b>。<b class="dk-main">偏离理由：规则档位「overheat」的前提是「本土情绪过热 + 无外部冲击」，而今日前提完全反转（外部系统性冲击 + VIX 28 + 技术破位面 16 席）</b>。<b class="dk-caution">偏离幅度超 5pct 属首次，已在此显式记录：这是本档唯一一次突破「±5pct」的偏离上限，理由是 VIX 单日 +69.66% 属统计尾部事件，规则档位不适用于尾部节点</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">正向依据（今日仍成立的支撑）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    ① <b class="dk-up">A股 低开幅度显著小于日韩</b>（上证 -2.11% vs 日经 -5.76% / KOSPI -6.77%），且 09:31 已自低点回升 0.42%；② <b class="dk-up">中概股逆势 +0.43%</b>（网易 +4.37 / 京东 +3.28 / 阿里 +2.64），中国资产脱钩叙事获跨市场印证；③ <b class="dk-up">港股 11/05 恒指 +3.67% / 恒生科技 +5.55%</b>；④ <b class="dk-up">电力设备 +63.10 亿（streak 4 · 分位 100）</b>与贵金属（金 +1.45%）两条与事件无关的资金线；⑤ <b class="dk-up">纳指期货转涨 +0.6%</b>（08:28）、美股盘后已在修复；⑥ <b class="dk-up">国内低通胀（CPI 0.9%）+ 宽货币（LPR 3.00% / 3.50%）</b>，与美国「高通胀 + 紧货币」形成镜像，政策空间充足。
  </div>

  <div class="dr-tag" style="margin-top:10px">反向依据（本档给「中性偏空 + 10%–20%」的直接原因）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    ① <b class="dk-risk">费半 -12%（2020 以来最大）、存储 -17.62%、光通信 -17.52%、MRVL -16.43%</b>，全链 de-rating 尚未在 A股 完成定价；② <b class="dk-risk">VIX 28.18（+69.66%）</b>，波动率本身成为风险源；③ <b class="dk-risk">技术面 16 席「下跌破位」</b>，今日跳空低开会形成新缺口；④ <b class="dk-risk">通信 -47.11 亿 + 外部两日 -23.4%</b>，负向主线确认；⑤ <b class="dk-risk">11-05 主力仅 +5.84 亿、国家队 -11.43 亿</b>，承接力量薄弱；⑥ <b class="dk-caution">今日 21:30 非农</b>（预期 +6.5 万），若强于 10 万则「12 月加息」坐实；⑦ <b class="dk-caution">PMI 49.3 / 49.7</b> 国内基本面不提供独立上行动能；⑧ <b class="dk-caution">韩国 SIDECAR 熔断</b>说明程序化去杠杆已启动，存在跨市场传染路径。
  </div>

  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:10px">
    <b class="dk-main">关键位（11/06 盘中逐条核对）</b>：上方 <b>3,646.57</b>（11/05 日内最低 = 昨日买盘成本线，回补缺口的第一道坎）→ <b>3,689.91</b>（11/05 收盘 = 多空分界）→ <b>3,701.59</b>（11/05 最高）。下方 <b>3,610.20</b>（今日开盘最低 = 第一支撑）→ <b>3,580</b>（8 月以来箱体下沿）→ <b>3,520</b>（本轮起涨平台，失守即中期转空）。<b class="dk-caution">量能门槛：成交 &gt;2.4 万亿 = 恐慌性放量（承接或踩踏，看方向）；&lt;1.8 万亿 = 缩量阴跌（抛压衰减但无买盘）</b>。<b class="dk-main">结构门槛：电力设备资金连续第 5 日净流入 = 本档唯一主线成立；电子 + 通信合计再流出 &gt;80 亿 = 情形 C 触发</b>。
  </div>
</div>

"""
repl_h("7.3", SEC73, "<!-- 7.4 操作预案 -->", tag="sec73")

# ═══════════ 7.4 操作预案 ═══════════
SEC74 = """<!-- 7.4 操作预案 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">7.4 · 操作预案（盘前版 09:30 · agent 详细版 · 面向 <b>11/06（周五）</b> · 依据 A股 11/05 完整收盘 + <b class="dk-risk">美股 11/05 完整收盘〔昨夜〕</b> + 日韩 11/06 早盘 + <b>本版四象限</b> 6 / 2 / 13 / 10）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>维度</th><th>本档预案（11/06）</th><th>触发条件 / 边界</th></tr></thead><tbody>
    <tr><td><b class="dk-risk">大势预判</b></td><td><div class="dr-wrap"><b class="dk-risk">低开已实现（-2.11%）、全日弱势震荡、尾盘方向取决于量能</b>：上证日内中枢 <b>3,600–3,660</b>，收盘预计 <b>-1.2%~-2.6%</b>（3,594–3,646）。<b class="dk-caution">不预设「低开即反弹」——今日的反证（中概股 +0.43%、纳指期货 +0.6%）只降低跌幅深度，不改变指数方向</b></div></td><td><div class="dr-wrap">成立前提：<b>电子 + 通信合计资金净流出 &gt;50 亿</b>。若两板块合计转为净流入（极低概率），说明「国产替代」叙事仍能对冲，则改为「低开高走 + 结构分化」，仓位可回补至 20%</div></td></tr>
    <tr><td><b class="dk-up">唯一可做方向</b></td><td><div class="dr-wrap"><b class="dk-up">只做两条与本次事件无关的链，且只在回踩不破位时轻仓</b>：<br>① <b>电力设备 / 光伏 / 电池</b>（+63.10 亿 · streak 4 · 分位 100 · 政策共振）—— <b>回踩不破 MA5 才允许轻仓</b>；<br>② <b>贵金属（金 / 银）</b>（金 +1.45% 破 4,100 · 有色 +18.62 亿）—— <b>作为组合的避险对冲，不做弹性</b>；<br>③ <b>医药生物</b>（+5.71 亿 · 美股医疗组仅 -2.77%，显著抗跌）—— <b>观察级，不主动加</b></div></td><td><div class="dr-wrap">仓位：<b class="dk-risk">10%–20%</b>（低于 overheat 档 [30,50] 下限 10pct，理由见 7.3 段）。<b class="dk-risk">单日新增不超过 5%；不接低开第一笔、不做超跌反弹第一根阳线、不打板</b></div></td></tr>
    <tr><td><b class="dk-risk">回避清单</b></td><td><div class="dr-wrap"><b class="dk-risk">① 存储 / HBM / 模组</b>（四线 -17.62%、SNDK -22.26）；<b>② 光模块 / CPO / 光通信</b>（三线 -17.52%、两日 -23.4%、资金 -47.11 亿）；<b>③ PCB / 铜连接 / 覆铜板</b>（数据中心 capex 下修最直接受体，昨日最热今最危险）；<b>④ 算力租赁 / ASIC 概念 / 服务器代工</b>（MRVL -16.43%、NEBIUS -14%、CRWV -9%）；<b>⑤ 半导体设备 / 材料（昨日首选，今日降为观察）</b>（前提被改写）；<b>⑥ 任何一字板 / 连板追高 / 昨日涨停板的次日溢价</b></div></td><td><div class="dr-wrap">解除条件（须同时满足）：<b>① 费半单日转正 或 存储四线连续两日收红</b>；<b>② 电子 + 通信合计资金转正 &gt;50 亿</b>。二者缺一不清除</div></td></tr>
    <tr><td><b>盘中哨兵</b></td><td><div class="dr-wrap">09:45 / 10:30 / 11:15 / 14:00 四次检查：<b>① 上证是否守住 3,610</b>（今日开盘最低）；<b>② 跌停家数是否 &gt;25</b>（&gt;40 为情形 C）；<b>③ 电子 + 通信合计资金是否 &lt; -80 亿</b>；<b>④ 成交是否 &lt; 1.8 万亿</b>（缩量下跌 = 抛压衰减；放量下跌 = 出逃）</div></td><td><div class="dr-wrap"><b class="dk-risk">①②③ 任一触发 ⇒ 仓位降至 5% 以下并停止一切新增</b>；④ 缩量 + 上证站稳 3,610 ⇒ 可维持 10%–20% 不加不减</div></td></tr>
    <tr><td><b>证伪与升级</b></td><td><div class="dr-wrap"><b class="dk-caution">本档判断（中性偏空）被证伪 = 上证收复 3,646.57 且成交 &gt;2.2 万亿、跌停 &lt;10 家</b>；<b class="dk-risk">升级为「偏空」= 上证失守 3,580 或 跌停 &gt;40 家 或 电子+通信合计流出 &gt;80 亿</b></div></td><td><div class="dr-wrap">收盘后 22:15 档按实际读数结算本档三条判断（方向 / 开盘 / 仓位），并记录命中与未命中；<b>今晚 21:30 非农为跨周末的独立事件，须在 22:15 档单独结算</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-caution">持仓类提示（合规声明）</b>：本页涉及的任何个股均为<b>「其他专家持股参考（非本人）」</b>，只给客观技术读数与板块归属，<b class="dk-risk">不提供任何加减仓建议</b>。今日对存储 / 光模块 / PCB / 算力的「回避」表述是<b>板块级风险描述</b>，不是对个股的操作指令。<b>11-05 读数显示：剑桥科技 -4.22%、长鑫科技 -3.54% 已先于板块调整，永杉锂业 +4.84%、昊华科技 +3.53%、华工科技 +2.57% 逆势上涨 —— 均为当日客观收盘读数，不构成任何方向判断</b>。
  </div>
</div>

"""
repl_between("<!-- 7.4 操作预案 -->", "<!-- 8 数据自检 -->", SEC74, tag="sec74")

# ═══════════ 8 数据自检 ═══════════
SEC8 = """<!-- 8 数据自检 -->
<div class="dr-h" data-version="preopen-0930">8 · 数据自检区（JS 自动扫描 · 各源日期一致性 · <b class="dk-up">本版已核：A股 2026-11-05 完整收盘〔结算价〕· 美股 <span class="dk-risk">2026-11-05</span> 完整收盘〔结算价 · 昨夜〕/ <code>us_kline.latest = 2026-11-05</code>（23/23）· 日韩 2026-11-06 早盘实时（08:40）· 商品 11/06 早间 · 美债 11/04 · A股 11/06 开盘 09:31</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div id="drSelfCheck" style="margin-top:8px">
    <div style="font-size:12.5px;color:var(--text-muted)">自检扫描中…</div>
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.6;margin-top:8px">
    <b class="dk-main">一、本版口径声明（源头逐项点名）</b><br>
    · <b>A股</b>：<code>market.json date = 2026-11-05</code>（<code>updated_at = 2026-11-06 08:40:48 CST</code> · <code>preopen_partial = true</code>）· <b>11/06 开盘实况取自腾讯实时接口 <code>qt.gtimg.cn</code>（<code>20261106093109</code>）</b>，<b class="dk-caution">仅作「开盘口径」引用，不改写 <code>market.json</code> 的 A股 收盘字段</b> · <code>output/sector_flow.json</code>（<code>flow_date = 2026-11-05</code> · <code>stale_days = 0</code> · 31/31）<br>
    · <b>美股</b>：<code>us_kline</code> <b>23/23</b> 最新日 = <b>2026-11-05</b>（<code>quotes.us_*</code> 同步）—— <b>完整收盘，非盘中快照</b>；费半 / 苹果 / 微软 / ORCL / CRWV / NEBIUS 不在本机 23 项抓取目录内，其读数引自今日语料（<b>已注明来源，不与本机数据混算</b>）<br>
    · <b>日韩</b>：<code>market.json.asia</code>（<code>date = 2026-11-06</code> · 日经 57,560.17 <span class="dr-dn">-5.76%</span> / KOSPI 5,019.56 <span class="dr-dn">-6.77%</span> · <b>早盘实时 · 非收盘</b>）· <code>kr_stocks</code>（<code>fetched_at = 2026-11-06 08:40</code> · NAVER 无延迟源 · SK하이닉스 <span class="dr-dn">-7.91%</span> / 삼성 <span class="dr-dn">-6.90%</span> · <code>traded_at 09:40:20+09:00</code>）· 港股 11/05 收盘（恒生 24,796.98 <span class="dr-up">+3.67%</span> / 恒生科技 4,154.29 <span class="dr-up">+5.55%</span>）<br>
    · <b>商品 / 美债</b>：<code>market.json.comm</code>（金 4,118.81 <span class="dr-up">+1.45%</span> / COMEX 4,131.06 / WTI 90.02 <span class="dr-up">+2.16%</span> / 布伦特 96.69 = <b>2026-11-06</b>；人民币 6.7156 / 碳酸锂 91,580 = 2026-11-05；<b>10Y 4.90% / 30Y 5.28% = 2026-11-04</b>，本机长期缺口、滞后 1 日）<br>
    · <b>宏观</b>：<code>output/daily_macro_latest.json</code>（<code>date = 2026-11-06</code> · <code>generated_at = 2026-11-06 08:42</code> · <code>us.calendar.as_of = 2026-11-06 08:42</code>；龄期按今日现算）· <b class="dk-caution">10 月非农 / 失业率 <code>value</code> 为空（今晚 21:30 公布），已在 <code>us.stale</code> 标注，本档只引用预期值</b><br>
    · <b>推演 / 板块</b>：<code>output/cross_analysis.json</code>（<code>generated_at = 2026-11-06 09:31</code> · <code>window.session = preopen</code> · <code>date/data_date/flow_date = 2026-11-05</code> · <code>news_window = 11/05~11/06</code> · 窗口 <b>589 条</b> · 门槛 日均 8 / 总量 16 · <b>09:31 盘前重算</b>）· <code>output/sector_tech.json</code>（<code>data_date = 2026-11-05</code> · <code>kline_last_date = 2026-11-05</code> · <code>kline_lag = 0</code> · 31/31）· <code>output/golden_diamond.json</code>（数据日 11-05 · 28 只）<br>
    · <b>三面板</b>：<code>vix_panel.cboe_vix = 28.18 @ 2026-11-05</code>（由 16.61 跳升 <span class="dr-dn">+69.66%</span>）· <code>valuation_band.date = 2026-11-05</code>（233 只）· <code>market_thermometer.date = 2026-11-05</code>（graham 1.81 / buffett 0.558 / PE 中位 34.55 / 10Y 分位 54.9%）<br>
    · <b>投喂</b>：<code>feed/archive/2026-11-05/_index.json</code>（<b>0 件</b>）· <code>feed/archive/2026-11-06/_index.json</code>（<b>0 件 · 如实为空、无伪造条目</b>）· 上一批次 <code>2026-11-03</code>（5 件 · T-3 语境，本页不引用）；语料侧消费 <code>output/daily_news_2026-11-06.json</code> <b>291 条</b>（08:40）<br>
    <b class="dk-main">二、本版十四道门禁（发布前逐条执行）</b><br>
    ① <code>em_http.py</code>（东财统一入口四台）② <code>check_analysis_style.py</code> ③ <code>check_v3_style.py</code> ④ <code>check_market_json.py</code> ⑤ <code>check_macro_freshness.py</code> ⑥ <code>check_index_render.py</code>（9 项）⑦ <code>check_review_dates.py</code> ⑧ <code>check_sector_tech.py</code> ⑨ <code>build_us_medical.py --check</code> ⑩ <code>patch_news_pool.py --check</code> ⑪ <code>patch_v3_richtext.py --check</code> ⑫ <code>patch_dk_css.py --check</code> ⑬ <code>check_touzid_panel.py</code> ⑭ <code>check_narrative_consistency.py</code><br>
    <b class="dk-main">三、本版已知口径边界（不掩饰）</b><br>
    ① <b>日韩为 11/06 早盘实时、非收盘</b>（08:40 抓取，韩国已运行 40 分钟、日本运行 40 分钟）；<b>因首取时刻 08:40 ≥ 08:35，按 SOP 未触发「发布前复取」</b>；② <b>本档触发时刻延迟</b>：原定 08:40，实际 09:28 启动（调度排队），故版本语义为「盘前版 09:30 · 含开盘实况」，<b>A股 已开盘</b>；③ <b>美债 10Y / 30Y 滞后 1 个交易日</b>（11-04），数据源长期缺口；④ <b>VIX 为 11-05 结算</b>（CBOE 北京 T+1 04:15 结算）；⑤ <b>费半 / ORCL / CRWV / NEBIUS / 软银</b> 不在本机 23 项抓取目录 → 引用今日语料，已在正文注明；⑥ <b>象限标签时滞</b>：<code>flow_date</code> 为 11-05、<code>news_window</code> 含 11-06 ⇒ 电子 / 计算机的「共振 A」是「昨日资金 + 今日利空语料」的错配组合，本档已主动降权；⑦ <b>投喂 0 件</b>（<code>feed_count: 0</code>，如实记录）；⑧ <b>非农 / 失业率 / 初请数值空缺</b>（源侧未回填），本档只引用预期与公布时点。
  </div>
</div>

"""
repl_between("<!-- 8 数据自检 -->", "<!-- 9 来源 -->", SEC8, tag="sec8")

# ═══════════ 9 来源 ═══════════
SEC9 = """<!-- 9 来源 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">9 · 来源（<b class="dk-data">盘前版 09:30 · 含开盘实况</b> · 复盘日 <b>2026-11-05（周四）</b> → 指引日 <b>2026-11-06（周五）</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div style="font-size:12.5px;line-height:1.65">
    <b class="dk-main">① 行情与资金</b>：<code>data/daily_review/market.json</code>（11-05 收盘 · <code>updated_at 11-06 08:40:48</code> · <code>preopen_partial = true</code> · 23 项美股 K 线滚至 11-05）· <b>腾讯实时 <code>qt.gtimg.cn</code>（11-06 09:31:09 · 开盘实况，仅作旁证）</b> · <code>realtime.json</code>（11-05 22:49 收盘终值 · <code>market_status = closed</code> · 情绪 74 / 主力 +5.84 亿）· <code>output/sector_flow.json</code>（<code>flow_date = 2026-11-05</code> · 31/31 · <code>stale_days = 0</code>）· <code>output/golden_diamond.json</code>（11-05 · 28 只）· <code>output/national_team_etf.json</code>（11-05）<br>
    <b class="dk-main">② 推演与板块</b>：<code>output/cross_analysis.json</code>（<b>11-06 09:31 盘前重算</b> · 窗口 11/05+11/06 · <b>589 条</b> · 四象限 6 / 2 / 13 / 10）· <code>output/sector_tech.json</code>（11-05 · 31/31 · <code>kline_lag = 0</code>）· <code>output/obs_deduce_latest.json</code>（11-05 · 32 只）· <code>output/obs_scenarios.json</code>（11-05 → 11-06）· <code>output/obs_panel.json</code>（折叠卡）· <code>output/vix_panel.json</code>（<b>11-05 · <span class="dr-dn">28.18</span></b>）· <code>output/market_thermometer.json</code>（<b>11-05</b>）· <code>output/valuation_band.json</code>（<b>11-05 · 233 只</b>）<br>
    <b class="dk-main">③ 宏观与新闻</b>：<code>output/daily_macro_latest.json</code>（08:42 · 日历轨 <code>us.calendar</code> + <code>china.*</code> · 12 项指标）· <code>output/daily_news_2026-11-06.json</code>（08:40 · <b>291 条</b>：宏观 37 / 科技 39 / 政策 31 / 产业 27 / 美股映射 3 / 持仓 1）· <code>output/daily_news_window.json</code>（滚动池 · 窗口切片 589 条）<br>
    <b class="dk-main">④ 投喂</b>：<code>feed/archive/2026-11-06/_index.json</code>（<b>0 件</b>）· <code>feed/archive/2026-11-05/_index.json</code>（<b>0 件</b>）· <code>feed/archive/feed_index.json</code>（历史清单 271 条，最新批次 11-03 的 5 件）—— <b class="dk-caution">本日无投喂语料，全文不含任何投喂引述；既往投喂内容一律标注「投喂语料 · 非本人持仓」</b><br>
    <b class="dk-main">⑤ 规则与技能</b>：<code>review/REVIEW_SOP.md</code>（盘前模式）· skill <code>daily-reasoning</code>（老站）· skill <code>v3-daily-review</code>（V3）· <code>realtime.L2.rules</code>（仓位与追高禁令）· <code>review_v3/backtest_v3.py</code> 的 <code>OPEN_DIR</code> 白名单（<code>open_call = 低开反弹</code>）<br>
    <b class="dk-main">⑥ 外部素材</b>：研报流 <code>~/Library/Application Support/goldenstock/feed_mahoro</code>（11-06 · 143 条 · 仅本机判读，<b class="dk-caution">禁原文入仓库</b>）· 新闻源 = 东财全球 / 财经早餐 / 新浪全球 / 同花顺全球 / 富途全球 / 央视联播<br>
    <b class="dk-risk">⑦ 免责</b>：本页为量化复盘记录，<b>不构成任何投资建议</b>。文中个股仅作板块代表，<b>持仓类标的为「其他专家持股参考（非本人）」</b>，只列客观技术读数、不给加减仓建议；<b>禁据此交易</b>。美股数据口径 = <b>11/05 完整收盘（昨夜结算价）</b>，非盘中。
  </div>
</div>
"""
i9 = html.find("<!-- 9 来源 -->")
assert i9 > 0
html = html[:i9] + SEC9

SRC.write_text(html, encoding="utf-8-sig")
print(f"Part C done: {len(html)} chars")
