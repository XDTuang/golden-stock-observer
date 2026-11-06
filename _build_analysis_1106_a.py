#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-06 盘前/开盘版 analysis.html · Part A：版本头 + 0 / 0.5 / 2 / 3
铁律：3 段整体重写后 → 再跑 review/build_us_medical.py（否则 US-MEDICAL 块被连带删除）
"""
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
SRC = BASE / "data/daily_review/analysis.html"
html = SRC.read_text(encoding="utf-8-sig")


def sub(old, new, expect=1, tag=""):
    global html
    c = html.count(old)
    assert c == expect, f"[{tag}] 出现 {c} 次，期望 {expect}: {old[:70]}"
    html = html.replace(old, new)


def repl_between(start_anchor, end_anchor, new, tag=""):
    global html
    c = html.count(start_anchor)
    assert c == 1, f"[{tag}] 起始 count={c}: {start_anchor[:60]}"
    i = html.find(start_anchor)
    j = html.find(end_anchor, i + len(start_anchor))
    assert j > i, f"[{tag}] 结束锚点缺失: {end_anchor[:60]}"
    html = html[:i] + new + html[j:]


# ═══════════ 版本注释块 ═══════════
i_vc = html.find("<!--\n版本：")
j_vc = html.find("-->", i_vc)
assert i_vc > 0 and j_vc > i_vc, "版本注释块未找到"
VER = """<!--
版本：盘前版 09:30（含开盘实况 · 原定 08:40 档调度延迟 48 分钟）· 复盘日 2026-11-05（周四 · 交易日）· 指引日 2026-11-06（周五）
结构：0 / 0.5 / 1 / 1.1 / 1.2 / 2 / 3 / 4 / 5 / 5.5 / 6 / 7.1 / 7.1b / 7.2 / 7.3 / 7.4 / 8 / 9（18 段）
口径：A股 11/05 完整收盘〔结算价〕+ 美股 **11/05 完整收盘**〔结算价 · 昨夜〕+ 日韩 **11/06 早盘实时**（08:40）
      + 港股 11/05 收盘 + 商品 11/06 早间 + 美债 11/04（本机长期缺口）+ **A股 11/06 开盘实况（09:31）**
数据链：market.json date=2026-11-05（updated_at 2026-11-06 08:40:48 · preopen_partial=true）
      / cross_analysis data_date=2026-11-05（gen 2026-11-06 09:31 · 盘前重算 · 窗口 11/05+11/06 · 589 条、门槛日均 8）
      / sector_tech data_date=2026-11-05 kline_last_date=2026-11-05（kline_lag=0）
      / sector_flow flow_date=2026-11-05 stale_days=0
      / daily_news_2026-11-06 291 条（08:40）
本版核心事实：**隔夜全球 AI 硬件链崩塌** —— 纳指 **-5.52%** / 纳指100 -6.5% / 道 -3.44% / 标普 -4.36% / **费半 -12%**（2020 以来最大单日）
      · 存储四线 **0/4（均值 -17.62%）**：SNDK -22.26 / WDC -17.35 / MU -17.46 / SKHY(ADR) -13.40
      · 光通信三线 **0/3（均值 -17.52%）**：AAOI -20.89 / LITE -18.68 / COHR -12.98 · MRVL -16.43 · NVDA -9.26 · TSLA -10.77
      · 导火索 = **民主党中期选举大胜（「蓝色浪潮」）→ AI 数据中心政策风险重估**；叠加 9 月 CPI 3.7% / 核心 PCE 3.1%（12 月加息预期）
      · 今晨亚太：日经 **-5.76%**（57,560.17 · 较 6 月高点 -20% 技术性熊市）/ KOSPI **-6.77%**（5,019.56 · 触发 SIDECAR 熔断）/ SK하이닉스 **-7.91%** / 삼성전자 **-6.90%** / MSCI 亚太 -3%
      · 反向证据：**纳指期货转涨 +0.6%**（08:28）/ 中概股金龙 +0.43%（阿里 +2.64 / 京东 +3.28 / 网易 +4.37）/ 港恒指 11/05 **+3.67%**、恒生科技 **+5.55%**
      · VIX **28.18（+69.66%）** · 金 4,118.81 **+1.45%** · WTI 90.02 **+2.16%** · 10Y 4.90% / 30Y 5.28%（11-04）
      · A股 11/06 开盘（09:31）：上证 **3,625.23（-1.75%）**，开 3,612.15（**-2.11%**）· 低 3,610.20 · 创业板 **-3.67%**（开 -4.99%）· 科创50 **-3.92%**（开 -5.05%）· 深成 **-2.63%**
      · 四象限 本版 **共振 6 / 背离 2 / 暗线 13 / 双冷 10**（前版 2 / 0 / 17 / 12，09:31 盘前重算）
      · 判定：方向 **中性偏空** · 开盘 **低开反弹** · 置信度 **中高** · 风险 **高** · 仓位 **10%–20%**
门禁：十四道（详见 8 段与提交信息）
-->"""
html = html[:i_vc] + VER + html[j_vc + 3:]

# ═══════════ 顶部标签行 ═══════════
sub('<span class="dr-tag">分析 = 收盘版 22:15（本机 agent）</span>',
    '<span class="dr-tag">分析 = 盘前版 09:30（含开盘实况 · 本机 agent）</span>', tag="tag-mode")

# ═══════════ 0 结论先行 ═══════════
SEC0 = """<!-- 0 结论先行 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">0 · 结论先行（速览卡 · <b>11/06 周五当日指引</b> · <b class="dk-data">盘前版 09:30（含开盘实况）</b> · 复盘日 <b>11/05（周四）</b> · A股 11/05 完整收盘〔结算价〕+ <b class="dk-risk">美股 11/05 完整收盘〔结算价 · 昨夜 · 全球 AI 硬件崩塌〕</b> + 日韩 11/06 早盘 + 港股 11/05 收盘 + 商品 11/06 早间）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 一句话结论</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">昨夜是全球 AI 硬件链的一次系统性 de-rating，不是普通回调</b>：纳指 <b class="dk-risk">-5.52%</b>（较 10/06 历史高点回落超 10%，进入技术性回调）、纳指100 <b class="dk-risk">-6.5%</b>、道指 <b class="dk-risk">-3.44%</b>、标普 <b class="dk-risk">-4.36%</b>、<b>费城半导体指数 -12%（2020 年以来最大单日跌幅）</b>；<b class="dk-risk">存储四线 0/4（SNDK -22.26 / WDC -17.35 / MU -17.46 / SKHY -13.40，均值 -17.62%）</b>、<b class="dk-risk">光通信三线 0/3（AAOI -20.89 / LITE -18.68 / COHR -12.98，均值 -17.52%）</b>、MRVL <b class="dk-risk">-16.43%</b>、NVDA <b class="dk-risk">-9.26%</b>、TSLA <b class="dk-risk">-10.77%</b>，美股单日市值蒸发约 <b>2.8 万亿美元</b>（刷新单日纪录）。<br>
    <b class="dk-main">导火索是「政治」而非「业绩」：民主党在中期选举中大胜（「蓝色浪潮」），市场开始重新评估 AI 高速扩张面临的数据中心审批 / 并网 / 监管风险</b>；叠加 9 月 CPI <b class="dk-caution">3.7%</b>、核心 PCE <b class="dk-caution">3.1%</b> 与 ADP 强于预期 ⇒ <b class="dk-caution">12 月「加息」而非「降息」的押注重新抬头</b>。<b class="dk-main">即：分母（折现率）与分子（资本开支预期）在同一夜被同时下调，这是最难受的组合</b>。<br>
    <b class="dk-risk">亚太今晨二次确认</b>：日经 <b class="dk-risk">-5.76%</b>（57,560.17，<b>较 6 月高点下跌 20%，进入技术性熊市</b>）、KOSPI <b class="dk-risk">-6.77%</b>（盘中一度 -8.1%，<b>韩国交易所启动 SIDECAR 暂停程序化卖盘</b>）、SK하이닉스 <b class="dk-risk">-7.91%</b>、삼성전자 <b class="dk-risk">-6.90%</b>、MSCI 亚太 <b class="dk-risk">-3%</b>、软银 <b class="dk-risk">-16%</b>（2024/08 以来最大跌幅）。<br>
    <b class="dk-main">A股 已用开盘价给出答案：上证开 3,612.15（<span class="dk-dn">-2.11%</span>）、最低 3,610.20，09:31 回升至 <b>3,625.23（<span class="dk-dn">-1.75%</span>）</b>；创业板开 <span class="dk-dn">-4.99%</span> 现 <span class="dk-dn">-3.67%</span>、科创50 开 <span class="dk-dn">-5.05%</span> 现 <span class="dk-dn">-3.92%</span>、深成现 <span class="dk-dn">-2.63%</span>。<b class="dk-caution">低开幅度已消化了「指数级」的美国冲击，但「结构级」的存储 / 光模块 / 算力硬件冲击尚未在 A股 完成定价</b>。</b><br>
    <b class="dk-main">⇒ 结论：方向 <b class="dk-risk">中性偏空</b>（置信度 <b>中高</b>）、开盘 <b class="dk-caution">低开反弹</b>（已实现）、风险 <b class="dk-risk">高</b>、仓位 <b class="dk-risk">10%–20%</b>。<b class="dk-risk">纪律：今日不做 AI 硬件的任何抄底（存储 / 光模块 / PCB / 铜连接 / 算力租赁），只保留「电力设备 + 有色贵金属」两条与本次冲击无关的资金暗线；不接低开第一笔、不做超跌反弹第一根阳线</b>。</b>
  </div>
  <div class="dr-tag" style="margin-top:10px">② 四象限与门控（现场读取 <code>cross_analysis.json</code>（<b>09:31 盘前重算</b>）/ <code>sector_tech.json</code>（11-05 22:43）/ <code>realtime.L1</code>（11-05 22:49 收盘终值））</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>维度</th><th>本版（11/06 盘前 09:30）</th><th>前版（11/05 收盘 22:15）</th><th>读数</th></tr></thead><tbody>
    <tr><td><b>四象限</b>（共振 A / 背离 B / 暗线 C / 双冷 D）</td><td><b class="dk-up">6 / 2 / 13 / 10</b></td><td>2 / 0 / 17 / 12</td><td><div class="dr-wrap"><b class="dk-main">本版四象限为共振 6 / 背离 2 / 暗线 13 / 双冷 10（09:31 盘前重算，语料窗口 589 条）</b>。<b class="dk-risk">迁移的成因是「语料侧扩容」，不是「资金侧变化」</b>：<code>flow_date</code> 仍为 11-05、31 席 <code>flow_yi</code> 逐板块<b>零变化</b>；变化全部来自今晨新闻池（11-06 新增 291 条，其中 56 条落计算机、58 条落电子）把多个板块的日均热度推过 8 条门槛。<b class="dk-risk">⇒ 共振席由 2 增至 6 是「利空型热度」堆出来的，不得读作资金进场、不得据此加仓</b>。唯一有金额意义的仍是电力设备（<span class="dk-up">+63.10 亿</span>）与通信（<span class="dk-dn">-47.11 亿</span>）两端</div></td></tr>
    <tr><td><b>板块技术分级</b>（<code>sector_tech</code> · 11-05 22:43 · <code>kline_lag = 0</code>）</td><td><div class="dr-wrap"><b class="dk-up">L4 1 / L3 3 / L2 15 / L1 12</b></div></td><td><div class="dr-wrap">L4 1 / L3 3 / L2 15 / L1 12</div></td><td><div class="dr-wrap"><b>与前版一致（未重建，数据日仍为 11-05）</b>：计算机 <b>L4</b>（唯一）、电力设备 / 传媒 / 汽车 <b>L3</b>。<b class="dk-risk">但趋势结构仍弱：向上 0 / 上升回踩 2 / 下跌反弹 13 / 下跌破位 16（<code>downtrend</code> 16 席）</b> ⇒ <b class="dk-main">16 席处「下跌破位」，意味着今日低开恰好落在技术最脆弱的位置上：低开即破位的板块有 16 个</b></div></td></tr>
    <tr><td><b>金钻命中</b>（<code>golden_diamond</code> · 数据日 11-05）</td><td><b>28 只</b>（起涨 6 / 买入 20 / 红区黄柱 2）</td><td>28 只（同）</td><td><div class="dr-wrap">数据日未变，<b>读数沿用</b>。起涨 6 只集中在 10/30–11/02 信号日，<b class="dk-caution">以电子（PCB）与传媒为主，恰是今日外部冲击最重与情绪最松的两端</b> ⇒ 今日这 6 只的「回踩确认」基本作废，须等新的低点确认</div></td></tr>
    <tr><td><b>情绪分</b>（<code>realtime.L1</code> · 11-05 22:49）</td><td><b class="dk-caution">74 · 情绪过热预警</b></td><td>74（同）</td><td><div class="dr-wrap">S1 100 / S2 77 / S3 60 / S4 51，规则档 <code>overheat [30,50]</code>。<b class="dk-risk">今日开盘后该分项必然大幅下修</b>（涨跌比由 7.32 直接翻转、涨停家数将骤降），<b class="dk-main">⇒ 本档不引用「过热」作为仓位依据，改以「外部冲击 + 技术破位面 16 席」为据</b></div></td></tr>
    <tr><td><b>VIX</b>（<code>vix_panel</code> · CBOE 11-05 结算）</td><td><b class="dk-risk">28.18（+69.66%）</b></td><td>16.61（11-04 · -20.26%）</td><td><div class="dr-wrap"><b class="dk-risk">单日由 16.61 跳升至 28.18（+11.57 / +69.66%），是 2026 年最大单日升幅</b> ⇒ <b class="dk-main">这是本档把风险等级打到「高」的第一硬证据：期权市场定价的是「系统性波动」而非「个别板块回调」</b>；<b class="dk-caution">对照昨夜金 +1.45% / 油 +2.16%、美债未见避险买盘（10Y 4.90%）⇒ 仍属「有序卖出」，尚未进入流动性危机</b></div></td></tr>
    <tr><td><b>主力净额</b></td><td><b class="dk-caution">+5.84 亿</b>（11-05 <code>realtime.L1</code>）</td><td>+5.84 亿（同）</td><td><div class="dr-wrap"><b class="dk-risk">11-05 的「指数涨 +5.84 亿」结构在今日开盘即被证伪</b> —— 昨日的普涨由情绪买盘推动、机构未接力，<b class="dk-main">⇒ 今日无人接盘的板块将直接补跌，这与「机构筹码厚」的板块（银行 / 公用）形成对照</b></div></td></tr>
    <tr><td><b>A股 开盘实况</b>（腾讯实时 · 09:31:09）</td><td><div class="dr-wrap"><b class="dk-risk">上证 3,625.23（-1.75%）</b><br>开 3,612.15（-2.11%）· 低 3,610.20</div></td><td>3,689.91（11-05 收）</td><td><div class="dr-wrap"><b class="dk-main">低开 -2.11% 后 1 分钟内未破 3,610，随即回升至 3,625（自低点 +0.42%）</b> ⇒ 定性 <b class="dk-caution">「低开 - 承接 - 未破位」</b>，但幅度上<b class="dk-risk">创业板 -4.99%、科创50 -5.05% 的低开是「成长端全面失守」</b>，反弹幅度（创业板自低 +1.39%、科创50 自低 +1.20%）尚不足以否定弱势</div></td></tr>
  </tbody></table></div>
  <div class="dr-tag" style="margin-top:10px">③ 今日（11/06 周五）三档预案 —— <b>开盘后修订版</b></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-caution">情形 A · 低开反弹后二次探底（概率 50% · 本档基准情形）</b>：上证 10:00–11:00 之间回落至 <b>3,610</b> 下方并测试 <b>3,580</b>，创业板跌破 <b>2,438</b>（今日开盘 = 日内低）；判定 <b class="dk-risk">「隔夜冲击未一次性出清，存量资金继续减仓」</b> ⇒ 仓位 <b>10%</b>，<b class="dk-risk">全日不加仓，只减不加</b>。<br>
    <b class="dk-caution">情形 B · 低开高走、守住 3,610（概率 30%）</b>：上证站稳 <b>3,625</b> 并收复 <b>3,646.57</b>（11-05 日内最低 = 昨日买盘成本线），成交放大至 <b>2.2 万亿</b>以上，<b>电力设备 / 有色资金继续净流入</b> ⇒ 定性 <b class="dk-up">「A股 对外部冲击二次免疫」</b>，仓位 <b>20%</b>（仅限两条暗线 + 防御），<b class="dk-risk">仍不碰 AI 硬件</b>。<br>
    <b class="dk-risk">情形 C · 破位下行（概率 20%）</b>：上证失守 <b>3,580</b>（= 8 月以来箱体下沿）或 <b>跌停 &gt;40 家</b>，或 <b>电子 / 通信合计再流出 &gt;80 亿</b> ⇒ 定性 <b class="dk-risk">「全球 AI 硬件 de-rating 向 A股 产业链传导」</b>，仓位降至 <b>5% 以下</b>，方向下调为「偏空」。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-caution">④ 五条必须同时记录的反向证据（不掩饰多头筹码）</b>：① <b class="dk-up">纳指期货转涨 +0.6%（08:28）</b>，此前一度跌超 1% ⇒ 美股盘后已在修复；② <b class="dk-up">中概股逆势走强，纳斯达克金龙中国指数 +0.43%</b>（网易 +4.37 / 京东 +3.28 / 阿里 +2.64 / 拼多多 +2.20 / B站 +2.67）⇒ <b class="dk-main">「中国资产与美股 AI 泡沫脱钩」的叙事在昨夜被强化，而非削弱</b>；③ <b class="dk-up">港股 11/05 恒指 +3.67% / 恒生科技 +5.55%</b>（南向净卖 213 亿，外资驱动）；④ <b class="dk-caution">金 4,118.81（+1.45%）创新高区、WTI +2.16%、10Y 4.90% 未破位</b> ⇒ <b>Vito 判据：出流动性问题要砸黄金和美债，这两者稳如泰山 ⇒ 属「有序卖出」</b>；⑤ <b class="dk-caution">A股 11-05 已在 KOSPI -5.28% 的环境下走平（+0.10%），昨日的「免疫」先例存在</b> —— <b class="dk-main">但须注意：昨日免疫的是「韩股存储价格叙事」，今日面对的是「费半 -12% + 全链 -17% 的估值重定价」，量级不同</b>。
  </div>
</div>
"""
repl_between("<!-- 0 结论先行 -->", "<!-- 0.5 深度判读 -->", SEC0, tag="sec0")

# ═══════════ 0.5 深度判读 ═══════════
SEC05 = """<!-- 0.5 深度判读 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">0.5 · 深度判读（盘前版 09:30 · <b>A股 11/05 收盘 vs 美股 <span class="dk-risk">11/05 收盘〔昨夜 · 崩塌〕</span> vs 日韩 <span class="dk-risk">11/06 早盘实时</span></b> · <b>本版四象限</b> 共振 6 / 背离 2 / 暗线 13 / 双冷 10 · 前版 2 / 0 / 17 / 12）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 前版（11/05 收盘 22:15）预判 vs 隔夜实际（K3 周卡必填项 · 历史记录，不改写）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>项目</th><th>11/05 收盘版（22:15）预判</th><th>隔夜 / 今晨实际</th><th>判定</th></tr></thead><tbody>
    <tr><td>方向</td><td><div class="dr-wrap">中性偏多（置信度 中）· 仓位 25%–40%</div></td><td>纳指 <b class="dk-risk">-5.52%</b>、费半 <b class="dk-risk">-12%</b>、A股 开盘 <b class="dk-risk">-2.11%</b></td><td><div class="dr-wrap"><b class="dk-risk">❌ 未命中（方向错）</b>。前版已明示反向证据④「11/05 美股早盘纳指 -1.78%、AI 硬件链调整没有结束」，<b>该条实际成为主导变量</b></div></td></tr>
    <tr><td>开盘口径</td><td>高开回吐压力 +0.2%~+0.7%（3,697–3,716）</td><td>开 <b>3,612.15（<span class="dk-dn">-2.11%</span>）</b>，<b>完全反向、且幅度超出区间下沿 2.3pct</b></td><td><b class="dk-risk">❌ 严重未命中（方向 + 幅度双错）</b></td></tr>
    <tr><td>三档剧本归属</td><td><div class="dr-wrap">A 高开回吐 45% / B 补量续攻 35% / <b>C 反向杀跌 20%</b></div></td><td><div class="dr-wrap">实际发生的是<b>概率最低的 C（20%）</b>，且 C 的触发线「通信再流出 &gt;30 亿」尚未有今日数据</div></td><td><b class="dk-risk">❌ 尾档成真（第二版连续尾档命中）</b></td></tr>
    <tr><td>核心判据</td><td><div class="dr-wrap">「外盘只能用于开盘 30 分钟，不能用于全日方向」（11/05 收盘版第三层方法论）</div></td><td>本档正是按该判据推演：<b>用外盘定开盘（低开），用 A股 自身资金结构定全日（不预设反弹）</b></td><td><b class="dk-up">✅ 方法论被本次极端行情验证有效</b></td></tr>
    <tr><td>存储 / 光模块</td><td><div class="dr-wrap">「回避区，明日不参与反弹」</div></td><td><b>SNDK -22.26 / MU -17.46 / WDC -17.35 / AAOI -20.89 / LITE -18.68 / COHR -12.98</b></td><td><b class="dk-up">✅ 命中（回避判断价值极高：隔夜再跌 13%~22%）</b></td></tr>
    <tr><td>设备 / 材料</td><td><div class="dr-wrap">「双受益：外盘跌也受益、外盘涨也受益」本档首选</div></td><td><div class="dr-wrap">外盘设备无对标数据；A股 今日开盘半导体设备随大盘低开。<b>该判断今日将被最严苛检验</b></div></td><td><b class="dk-caution">⏳ 待全日验证（10:30 / 14:00 两次复核）</b></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">该比对的四层方法论产出（本档最重要、必须写入周卡）</b>：<br>
    <b class="dk-risk">第一层：「外盘→全日方向」的判据连续三版失效，正式废止</b> —— 11/04 盘前判偏多（外盘涨）→ 实际涨（对）；11/05 盘前判偏空（外盘跌）→ 实际涨（错）；11/05 收盘判偏多（外盘早盘跌但道指涨）→ 隔夜崩塌（错）。<b class="dk-main">三次里两次错，且错因同构：把「外部价格」当作「A股 全日定价锚」</b>。<b class="dk-caution">⇒ 正式规则：外盘只用于「开盘 30 分钟」的幅度折算，全日方向一律由「本土资金结构 + 板块资金连续性 + 政策面 + 技术破位面」四维决定，外盘权重降为 0</b>。<br>
    <b class="dk-risk">第二层：「贬低尾部情形」是本档反复出错的根源</b> —— 11/05 盘前把「低开被吞」给到 15%（实际发生）、11/05 收盘把「反向杀跌」给到 20%（实际发生）。<b class="dk-main">两次尾档成真的共同点：前版已识别出对应风险（承接不足 / AI 硬件未止跌），但因「主情形胜率更高」而下调了权重</b>。<b class="dk-caution">⇒ 修正：当某一风险已被识别且不可证伪（如隔夜美股盘前大跌、VIX 飙升）时，该情形的最低概率不得低于 30%，且仓位必须按该情形设置</b>。<br>
    <b class="dk-risk">第三层：「同一事件、两套语义」的跨市场框架在本次升级为「语义分层」</b> —— 11/05 A股 把「韩厂存储暴跌」读成「国产替代份额上升」（半导体设备 +7.71%）。<b class="dk-main">但昨夜的事件性质不同：不是「价格见顶」，而是「资本开支被政治力量压制」（数据中心审批 / 监管）</b> ⇒ <b class="dk-caution">前者利好设备（扩产成本降），后者利空设备（扩产本身被质疑）。同一框架在两种事件下结论相反 —— 这是本档今日下调设备链权重的根本原因</b>。<br>
    <b class="dk-risk">第四层：「指数跌幅 ≠ 结构跌幅」在今日的开盘数据里已被量化</b> —— 上证 -2.11%、沪深300 -2.32%，而创业板 -4.99%、科创50 -5.05%。<b class="dk-main">成长端的低开幅度是主板的 2.2 倍，说明市场杀的是「AI 相关的高 β 资产」，不是「中国资产」</b>。<b class="dk-caution">⇒ 本条支持「中国资产与美股 AI 泡沫脱钩」的叙事（中概股 +0.43% 同向印证），但也意味着「指数层面的护盘」与「持仓层面的亏损」会严重背离</b>。
  </div>

  <div class="dr-tag" style="margin-top:10px">② 四象限 2×2（<code>cross_analysis.json</code> · <b>2026-11-06 09:31 盘前重算</b> · <code>flow_date = 2026-11-05</code> · 窗口 11/05–11/06 · 589 条 · 门槛 日均 8 条）</div>
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:6px">
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-up">共振 A · 6 席（前版 2 → 本版 6）</b></div>
      <div style="font-size:12.5px;line-height:1.6">计算机（56 条 / <span class="dk-up">+13.99 亿</span>）· 电子（58 / <span class="dk-up">+12.05 亿</span>）· 有色金属（24 / +18.62）· 机械设备（16 / +18.35）· 传媒（19 / +34.92）· 银行（17 / +8.51）</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-risk">六席里只有传媒（+34.92）、有色（+18.62）、机械（+18.35）是「资金正 + 语料正」的真共振</b>。<b class="dk-caution">电子 58 条 / 计算机 56 条是今晨「美股 AI 崩塌」新闻堆出来的利空型热度，资金列则是 11-05 的旧值（+12.05 / +13.99 亿）</b> ⇒ <b class="dk-risk">这两席必须降权为「高危热度」，不得当作主线</b></div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-caution">背离 B · 2 席（前版 0 → 本版 2）</b></div>
      <div style="font-size:12.5px;line-height:1.6">国防军工（21 条 / <span class="dk-dn">-8.18 亿</span>）· 食品饮料（17 / <span class="dk-dn">-4.40 亿</span>）</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-main">两席均为「语料热而资金撤」</b>：军工的热度来自地缘新闻、食品饮料来自防御叙事，<b class="dk-caution">但资金两席皆负 ⇒ 属「嘴上防御、手上不买」，不宜作为避风港</b></div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-caution">暗线 C · 13 席（前版 17 → 本版 13）</b></div>
      <div style="font-size:12.5px;line-height:1.6">电力设备（12 / <span class="dk-up">+63.10 亿</span>）· 汽车（10 / +11.17）· 商贸零售（0 / +7.69）· 医药生物（6 / +5.71）· 美容护理（0 / +3.12）· 房地产（2 / +2.69）· 社会服务（0 / +2.51）…</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-up">电力设备是本版唯一「大额 + 连续 4 日 + 语料未被炒」的资金暗线（+63.10 亿 / news 12 条未过门槛）</b>，<b class="dk-main">也是唯一与「AI 资本开支」无关的制造业方向</b>。<b class="dk-caution">其余 12 席多为 &lt;12 亿的零轴噪声</b></div>
    </div>
    <div style="border:1px solid var(--border);border-radius:6px;padding:8px">
      <div><b class="dk-risk">双冷 D · 10 席（前版 12 → 本版 10）</b></div>
      <div style="font-size:12.5px;line-height:1.6">通信（14 / <span class="dk-dn">-47.11 亿</span>）· 非银金融（10 / -14.28）· 煤炭（1 / -12.25）· 石油石化（9 / -8.14）· 交通运输（0 / -7.72）· 建筑材料（0 / -4.62）· 公用事业（7 / -4.24）· 家用电器（0 / -1.54）…</div>
      <div style="font-size:12.5px;line-height:1.6;margin-top:4px"><b class="dk-risk">通信仍是全场最大流出（-47.11 亿）且今日外部光通信再跌 13%~21% ⇒ 双冷格局在今日只会加深</b>。石油石化虽双冷，但油价 +2.16% ⇒ <b class="dk-caution">存在「资金未跟」的错配，不作方向</b></div>
    </div>
  </div>

  <div class="dr-tag" style="margin-top:10px">③ 迁移成因的归因判定（<b>必写，不得省略</b>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">迁移主因 = 语料侧扩容，非资金行为变化</b>。<b>量化依据</b>：① <code>flow_date</code> 两版均为 2026-11-05，31 个板块的 <code>flow_yi</code> <b>逐板块零变化</b>（电力设备 +63.10、通信 -47.11、传媒 +34.92 三次核对一致）；② 新闻池由 285 条（11-05 22:25）扩至 589 条（窗口切片），<b>增量 291 条中计算机 56 条、电子 58 条</b>，正好是迁移最剧烈的两个板块；③ 共振席由 2 → 6 的四个新增席（有色 +18.62 / 机械 +18.35 / 传媒 +34.92 / 银行 +8.51）资金<b>全部为 11-05 旧值且未变</b>，仅热度过线。<b class="dk-risk">⇒ 结论：本版四象限的「共振变多」是新闻密度上升的机械结果，<b>不得读作资金行为变化、不得据此上调仓位</b>，更不得把电子 / 计算机的「共振 A」当作买入依据 —— 它们的语料是「利空型热度」</b>。
  </div>

  <div class="dr-tag" style="margin-top:10px">④ 今日必须同时盯的四个变量</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">① 上证 3,610（今日开盘最低）能否守住</b> —— 守住 = 情形 B 成立（低开高走）；跌破且 11:30 前不收回 = 情形 A 转 C。② <b class="dk-caution">电力设备资金能否连续第 5 日净流入</b>（11-05 +63.10 亿 / streak 4）—— <b>这是本档唯一保留的主线，若今日转为流出，则本档的「抗冲击方向」假设全部作废</b>。③ <b class="dk-risk">电子 + 通信合计资金净额</b>（11-05 分别 +12.05 / -47.11 亿）—— 若合计再流出 &gt;80 亿，则从「回避」升级为「负向主线」。④ <b class="dk-caution">今晚 21:30 美国 10 月非农</b>（预期 +6.5 万 / 失业率 4.2%，<b>截至本档数值仍为空</b>）—— 若数据强于预期，「12 月加息」将成主流定价，全球高估值资产面临二次冲击。
  </div>
</div>
"""
repl_between("<!-- 0.5 深度判读 -->", "<!-- 1 昨日 A 股走势总结 -->", SEC05, tag="sec05")

# ═══════════ 2 亚太与商品利率 ═══════════
SEC2 = """<!-- 2 日韩股市与商品利率 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">2 · 亚太与商品利率（日韩 = <b class="dk-risk">11/06 早盘实时〔08:40 抓取 · 非收盘〕</b> · 港股 11/05 收盘 · 商品 11/06 早间 · <b class="dk-caution">美债 11/04（本机长期缺口，滞后 1 日）</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 日韩：<b class="dk-risk">「存储权重市场」被单点击穿，日经跌入技术性熊市</b></div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>11/06 早盘</th><th>涨跌幅</th><th>读法</th></tr></thead><tbody>
    <tr><td>日经225</td><td><b>57,560.17</b></td><td><b class="dk-risk">-5.76%</b></td><td><div class="dr-wrap"><b class="dk-risk">单日 -5.76%，且「较 6 月高点下跌 20%，进入技术性熊市」</b>（08:13 快讯）；08:10 时跌幅为 -4.5%、08:22 扩大至 -6% ⇒ <b class="dk-main">开盘即单边下探、无承接，与 11/05 的 -1.79% 温和回踩完全不是同一量级</b></div></td></tr>
    <tr><td>韩国 KOSPI</td><td><b>5,019.56</b></td><td><b class="dk-risk">-6.77%</b></td><td><div class="dr-wrap"><b class="dk-risk">盘中一度跌 8.1%（接近触发交易暂停），韩国交易所启动 SIDECAR 机制暂停 KOSPI / KOSDAQ 程序化卖盘，恢复交易后跌幅收窄至 6.8%</b> ⇒ <b class="dk-main">这是「程序化交易的强制去杠杆」，属流动性事件的早期形态</b>，而非单纯基本面定价</div></td></tr>
    <tr><td>SK하이닉스 / 삼성전자</td><td>1,164,000 / 187,600</td><td><b class="dk-risk">-7.91% / -6.90%</b></td><td><div class="dr-wrap">两只合计占 KOSPI 权重约 1/3。<b class="dk-caution">注意跌幅结构：个股（-7.91% / -6.90%）与指数（-6.77%）几乎同幅 ⇒ 本轮回撤是「存储双雄主导、其余板块跟随」，而非个别股事件</b>。<code>traded_at = 2026-11-06T09:40:20+09:00</code>（韩国已运行 40 分钟）</div></td></tr>
    <tr><td>MSCI 亚太 / 软银</td><td>—</td><td><b class="dk-risk">-3% / -16%</b></td><td><div class="dr-wrap">MSCI 亚太指数 <b class="dk-risk">-3%</b>（08:31）；<b class="dk-risk">软银集团 -16%，创 2024 年 8 月以来最大跌幅</b>（08:29）⇒ <b class="dk-main">软银是全球 AI / 半导体资产的高 β 代理，其 -16% 说明抛售已从「存储」扩散至「AI 投资平台」</b></div></td></tr>
    <tr><td><b class="dk-up">恒生指数 / 恒生科技</b></td><td>24,796.98 / 4,154.29<br><b class="dk-caution">（11/05 收盘）</b></td><td><b class="dk-up">+3.67% / +5.55%</b></td><td><div class="dr-wrap"><b class="dk-up">11/05 港股是亚太唯一大涨市场，且科技涨得更多</b>。<b class="dk-caution">但南向资金净卖 213 亿港元（外资驱动）</b>，<b class="dk-main">今日港股开盘将同时承受「美股 AI 崩塌」与「中概股逆势 +0.43%」两股相反的力，是 A股 今日最重要的前置观测窗（港股 09:30 开盘，早于 A股 竞价结论）</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">⇒ 亚太今晨的结构性判断（与 11/05 相反的一条）</b>：11/05 的形态是「韩崩、日稳、中涨」，属<b class="dk-caution">区域性分化</b>；今晨的形态是<b class="dk-risk">「日韩同崩（-5.76% / -6.77%）、MSCI 亚太 -3%、软银 -16%」，属全域性风险释放</b>。<b class="dk-main">差别在于事件的来源：11/05 是「存储价格周期」（对韩国单点），今晨是「美国 AI 资本开支的政策风险」（对整个亚太科技链）</b>。<b class="dk-caution">⇒ 判据：区域性事件可以「免疫」，全域性事件难以免疫；A股 今日 -2.11% 的低开幅度，相对日韩 -5.8%/-6.8%，已属「相对抗跌」，但绝对方向仍为负</b>。
  </div>

  <div class="dr-tag" style="margin-top:10px">② 商品 / 利率 / 汇率（<code>market.json.comm</code> · 11/06 早间；美债为 11/04 收盘）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>品种</th><th>最新</th><th>涨跌幅</th><th>日期</th><th>读法</th></tr></thead><tbody>
    <tr><td>现货黄金 / COMEX</td><td><b>4,118.81</b> / 4,131.06</td><td><b class="dk-up">+1.45%</b> / +1.43%</td><td>11/06</td><td><div class="dr-wrap"><b class="dk-up">风险资产崩塌当日，金价再涨 1.45% 至 4,118（08:19 快讯「现货黄金突破 4,100 美元/盎司」）</b> ⇒ <b class="dk-main">避险资金明确流向黄金而非美债 ⇒ 属「股市去杠杆 + 通胀对冲」的组合，不是「衰退避险」</b>（后者会同时买美债）</div></td></tr>
    <tr><td>WTI / 布伦特</td><td><b>90.02</b> / 96.69</td><td><b class="dk-up">+2.16%</b> / <b class="dk-up">+2.19%</b></td><td>11/06</td><td><div class="dr-wrap"><b class="dk-caution">油价连续第二日修复（11/05 +1.51% / +2.38%，11/06 再 +2.16% / +2.19%）</b>，回到 90 上方 ⇒ <b class="dk-main">与「通胀顽固（CPI 3.7%）」互为因果，构成本轮「加息交易」的商品端证据</b>。<b class="dk-caution">对 A股：石油石化 11-05 仍流出 8.14 亿（未受益），成本端压力（化工 / 交运 / 航空）反而重来</b></div></td></tr>
    <tr><td>10Y / 30Y 美债</td><td><b>4.90%</b> / <b>5.28%</b></td><td>—</td><td><b class="dk-caution">11/04</b></td><td><div class="dr-wrap"><b class="dk-risk">长端 5.28% 在「股市崩、VIX +69.66%」的当日未下行</b> ⇒ <b class="dk-main">这是本档最关键的一条反向证据：真正的避险会买美债，本次没有 ⇒ 属「有序卖出 + 通胀担忧」，不是「衰退恐慌」</b>。<b class="dk-caution">本机该源长期滞后 1 日，已在 8 段标注</b></div></td></tr>
    <tr><td>人民币中间价</td><td>6.7156</td><td>—</td><td>11/05</td><td><div class="dr-wrap">汇率稳定，<b>不构成外资流出的加速器</b>；但若今日 A股 大幅下跌而汇率仍稳，则说明是「内部减仓」而非「外资撤离」</div></td></tr>
    <tr><td>碳酸锂（广期所主连）</td><td>91,580</td><td>—</td><td>11/05</td><td><div class="dr-wrap"><b class="dk-main">锂价持稳是「电池 / 电力设备 / 光伏」链条的成本锚</b>；在 AI 硬件崩塌的背景下，<b>新能源链是唯一「与算力资本开支无关」的成长方向</b>，其成本端稳定具有配置意义</div></td></tr>
    <tr><td>VIX</td><td><b class="dk-risk">28.18</b></td><td><b class="dk-risk">+69.66%</b></td><td><b>11/05 结算</b></td><td><div class="dr-wrap"><b class="dk-risk">由 16.61 跳升至 28.18（+11.57 点 / +69.66%），2026 年最大单日升幅</b> ⇒ <b class="dk-main">28 上方属「高波区间」，历史上对应「被动减仓 / 风险预算强制下调」阶段，与「结构性行情」的低波环境（&lt;17）性质相反</b>。<b class="dk-caution">⇒ 本档不给「低开即买」的核心理由：VIX 28 意味着波动率本身已变成风险源</b></div></td></tr>
  </tbody></table></div>
</div>
"""
repl_between("<!-- 2 日韩股市与商品利率 -->", "<!-- 3 隔夜美股复盘 -->", SEC2, tag="sec2")

# ═══════════ 3 隔夜美股复盘 ═══════════
SEC3 = """<!-- 3 隔夜美股复盘 -->
<div class="dr-h" data-version="preopen-0930" data-review-date="2026-11-05" data-for-date="2026-11-06">3 · 隔夜美股复盘（最近一个完整收盘 = <b class="dk-risk">11/05〔结算价 · 昨夜〕</b> · <b class="dk-risk">AI 硬件链系统性崩塌：费半 -12% / 存储 -17.6% / 光通信 -17.5%</b> · 市值单日蒸发约 2.8 万亿美元）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 双日对照表（<code>market.json.us_kline</code> · 23/23 已滚至 11/05 · 完整收盘口径）</div>
  <div class="dr-scroll"><table class="dr-tbl"><thead><tr><th>标的</th><th>11/04 收盘</th><th>11/05 收盘</th><th>变动</th><th>读法</th></tr></thead><tbody>
    <tr><td>道琼斯</td><td>53,356.12</td><td><b>51,523.06</b></td><td><b class="dk-risk">-3.44%</b></td><td><div class="dr-wrap"><b class="dk-risk">单日 -1,833 点</b>，三大股指均创 2025 年 4 月「解放日」关税政策以来最大跌幅 ⇒ <b class="dk-main">跌的不只是科技，是「蓝潮上台 → 政策不确定性」的整体重定价</b></div></td></tr>
    <tr><td>标普500 / 纳斯达克</td><td>7,688.62 / 25,736.51</td><td><b>7,353.73</b> / <b>24,315.00</b></td><td><b class="dk-risk">-4.36%</b> / <b class="dk-risk">-5.52%</b></td><td><div class="dr-wrap"><b class="dk-risk">纳指较 10/06 历史收盘高点回落超 10%，正式进入技术性回调</b>；纳指100 <b class="dk-risk">-6.5%</b>。<b class="dk-main">「科技七巨头」集体下挫，NVDA 单日市值蒸发 4,470 亿美元</b></div></td></tr>
    <tr><td><b>费城半导体指数</b></td><td>—</td><td>—</td><td><b class="dk-risk">-12%</b></td><td><div class="dr-wrap"><b class="dk-risk">2020 年以来最大单日跌幅</b> ⇒ <b class="dk-main">这是本轮最重要的单一读数：费半的跌幅是纳指的 2.2 倍、道指的 3.5 倍，说明杀跌高度集中于半导体</b></div></td></tr>
    <tr><td><b>存储四线</b>（MU / SNDK / WDC / SKHY）</td><td><div class="dr-wrap">795.23 / 1,037.40 / 323.83 / 143.07</div></td><td><b>656.39</b> / <b>806.43</b> / <b>267.63</b> / <b>123.90</b></td><td><b class="dk-risk">-17.46% / -22.26% / -17.35% / -13.40%<br>均值 -17.62%（0/4）</b></td><td><div class="dr-wrap"><b class="dk-risk">四线全黑，且跌幅落在 13%~22% 的极端区间</b> ⇒ <b class="dk-main">这不是回踩，是「存储超级周期」叙事的当日证伪</b>。今日语料已出现〈市场不再相信存储超级周期？〉与〈存储巨头 300 亿工厂停工〉两条，<b class="dk-risk">SNDK -22.26% 是全组最弱</b></div></td></tr>
    <tr><td><b>光通信三线</b>（LITE / AAOI / COHR）</td><td><div class="dr-wrap">626.75 / 59.27 / 195.09</div></td><td><b>509.70</b> / <b>46.89</b> / <b>169.76</b></td><td><b class="dk-risk">-18.68% / -20.89% / -12.98%<br>均值 -17.52%（0/3）</b></td><td><div class="dr-wrap"><b class="dk-risk">11/04 已跌 7.06%，11/05 再跌 17.52%，<b>两日累计约 -23.4%</b></b> ⇒ <b class="dk-main">A股 通信 11-05 已流出 47.11 亿（单日反转 122.97 亿），今日外部再挫 17%+，该链从「回避」升级为「负向主线」</b></div></td></tr>
    <tr><td>MRVL / NVDA / TSLA</td><td>159.80 / 200.13 / 385.19</td><td><b>133.55</b> / <b>181.60</b> / <b>343.69</b></td><td><b class="dk-risk">-16.43% / -9.26% / -10.77%</b></td><td><div class="dr-wrap"><b class="dk-main">ASIC（MRVL -16.43%）跌幅接近 GPU（NVDA -9.26%）的 2 倍</b> ⇒ <b>杀的是「定制化算力 / 自研芯片」的资本开支预期，即「大厂还要不要自建」这个问题本身</b>。<b class="dk-caution">TSLA -10.77% 属高 β 补跌，与 AI 逻辑无关</b></div></td></tr>
    <tr><td><b class="dk-up">中概股（金龙指数）</b></td><td>—</td><td><b class="dk-up">+0.43%</b></td><td><b class="dk-up">逆势收涨</b></td><td><div class="dr-wrap"><b class="dk-up">网易 +4.37 / 京东 +3.28 / B站 +2.67 / 阿里 +2.64 / 拼多多 +2.20，仅小鹏 -2.54</b> ⇒ <b class="dk-main">「中国资产与美股 AI 泡沫脱钩」是昨夜最强的多头证据，与港股 11/05 恒科 +5.55% 形成跨市场印证</b></div></td></tr>
  </tbody></table></div>

  <div class="dr-tag" style="margin-top:10px">② 崩塌的归因链（<b>本档最重要的因果判定</b>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">第一因（导火索 · 政策）：民主党在中期选举中取得重大胜利（「蓝色浪潮」）</b>，投资者开始重新评估 AI 产业高速扩张面临的政策风险；<b>「立马就拿数据中心开刀」</b>（08:32 快讯）、谷歌斥资 170 亿美元布局怀俄明数据中心被质疑（08:38）⇒ <b class="dk-main">市场买的不是「AI 需求下降」，而是「AI 资本开支的许可被收紧」</b>。<br>
    <b class="dk-risk">第二因（放大器 · 利率）：通胀顽固 + 加息预期</b> —— 9 月 CPI <b>3.7%</b>（预期 3.6）、核心 CPI 2.6%（预期 2.5）、9 月核心 PCE <b>3.1%</b>、ADP +8.6 万（预期 6.5 万）、ISM 制造业 55.5 ⇒ <b>「经济不弱 + 通胀不降」的组合把 12 月降息押注打掉，语料已出现「美联储 12 月或加息 25 个基点」</b>。<b class="dk-main">分母端（折现率）与分子端（capex）同时被下调，是本轮跌幅如此之深的结构原因</b>。<br>
    <b class="dk-risk">第三因（传导方式 · 多头踩踏）：Vito 判据「资产跌幅非常平均，没有 pair 迹象 ⇒ 是多头踩踏而非对冲基金发力」</b>；<b>「新云债券跌得比股票还快」</b>，AI 对冲基金 VARA 10 月单月 -33%（07:37 快讯）⇒ <b class="dk-main">杠杆集中在「新云 / 数据中心运营商」，而非传统半导体，因此债券的清算压力会持续外溢</b>。<br>
    <b class="dk-caution">尚未发生的（必须记录 · 决定后续路径）</b>：<b>① 流动性危机未出现</b> —— 黄金 +1.45%、美债 10Y 4.90% 未下行（若真避险应下），<b>说明是「有序卖出」</b>；<b>② 衰退预期未形成</b> —— 万豪创新高、零售销售 0.8% 强于预期、消费端未失速；<b>③ 铜未补跌</b> —— Vito 判据「锡等 AI 后排金属已崩，看铜什么时候补，铜补跌 = 衰退预期从无到有」，<b>铜今日是本档最值得盯的宏观变量</b>。
  </div>

  <div class="dr-tag" style="margin-top:10px">③ 本段结论（对今日 A股 的三条映射）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">① AI 硬件链一律「不接」</b>：存储 -17.62%、光通信 -17.52%、MRVL -16.43%、费半 -12% ⇒ <b class="dk-main">A股 对应环节（存储 / HBM / 光模块 / CPO / PCB / 铜连接 / 算力租赁）今日只有「跌多跌少」的问题，没有「跌不跌」的问题</b>。<b class="dk-caution">昨日 11-05 该链曾逆势 +7.71%（国产替代叙事），今日须观察该叙事是否还能对冲「资本开支被质疑」——本档判断：<b>不能</b>，因为逻辑从「份额上移」变成「蛋糕变小」</b>。<br>
    <b class="dk-up">② 「中国资产脱钩」是本档唯一保留的多头线索</b>：金龙指数 +0.43%、港恒科 11/05 +5.55%、A股 低开幅度（上证 -2.11%）明显小于日韩（-5.76% / -6.77%）⇒ <b class="dk-main">今日若上证能守住 3,610 并收复 3,646.57，则该叙事成立，A股 将走出「独立于美股 AI 的箱体」；若破 3,580，则脱钩叙事当日作废</b>。<br>
    <b class="dk-caution">③ 「成本下降型受益」与「资本开支型受损」必须分开</b>：存储价格下跌对「用存储的终端」（消费电子 / PC / 服务器整机）是成本利好，对「造存储的」（原厂 / 设备 / 材料）是需求利空。<b class="dk-main">⇒ 昨日「设备是双受益」的框架今日失效一半：<b>原厂扩产被质疑 ⇒ 设备订单预期下修</b>，故本档把半导体设备从「首选」下调为「观察」</b>。
  </div>
</div>

"""
repl_between("<!-- 3 隔夜美股复盘 -->", "<!-- US-MEDICAL-BEGIN", SEC3, tag="sec3")

SRC.write_text(html, encoding="utf-8-sig")
print(f"Part A done: {len(html)} chars (was {len(SRC.read_text(encoding='utf-8-sig'))})")
