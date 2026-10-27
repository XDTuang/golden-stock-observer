# -*- coding: utf-8 -*-
"""2026-10-27 盘前版 · Part B：2 段 / 3 段 / 4 段 / 5 段 / 5.5 段
3 段整段重写时连同 US-MEDICAL 块一并移除（顺序铁律：重写完成后再跑 build_us_medical.py 幂等注入）
"""
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


# ────────────────────────── 2 段 ──────────────────────────
SEC2 = '''<!-- 2 日韩股市与商品 -->
<div class="dr-h" data-version="preopen-0840">2 · 日韩股市与商品利率（JS 自动 · <code>market.json</code> · <b class="dk-up">本版口径 = 日韩 10/27 早盘实时（08:43 复取）</b> · <b class="dk-up">日经 63,345.75（<span class="dk-up">+1.86%</span>）</b> · <b class="dk-up">KOSPI 5,675.49（<span class="dk-up">+3.77%</span>）</b> · <b class="dk-up">韩存储 SK하이닉스 +6.51%（1,358,000）/ 삼성전자 +4.93%（223,500）</b> · <b class="dk-data">港股 10/26 收盘（恒生 <span class="dk-up">+0.51%</span>）</b> · <b class="dk-data">商品汇率 10/26 · 美债 10/23</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag" style="margin-bottom:4px">港股指数（云端自动 · market.json · <b class="dk-data">10/26 收盘</b>）</div>
  <div id="drTblHK"></div>
  <div class="dr-tag" style="margin:12px 0 4px">日韩股指与存储双雄（JS 自动 · <code>market.json.asia</code> · <b class="dk-up">10/27 早盘 08:43 复取（首取 08:31 已被覆盖）</b>）</div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px">
    <thead><tr><th>标的</th><th>最新</th><th>涨跌</th><th>08:31 首取</th><th>读数</th></tr></thead>
    <tbody>
      <tr><td><b>日经225</b></td><td>63,345.75</td><td><b class="dk-up">+1.86%</b></td><td>63,382.56 / +1.92%</td><td class="dr-wrap">开盘强势延续，08:43 小幅回落 0.06pct；<b>日本芯片股大涨、铠侠 +6.8%</b></td></tr>
      <tr><td><b>KOSPI（首尔综合）</b></td><td>5,675.49</td><td><b class="dk-up">+3.77%</b></td><td>5,690.86 / +4.05%</td><td class="dr-wrap"><b>本版最强外部读数</b>：开盘 +3.46% → 08:31 +4.05% → 08:43 +3.77%，<b>自高点回落 0.28pct，属「高开后的正常消化」而非「冲高回落」</b></td></tr>
      <tr><td>SK하이닉스（000660）</td><td>1,358,000</td><td><b class="dk-up">+6.51%</b></td><td>1,361,000 / +6.75%</td><td class="dr-wrap">09:43 KST 口径；<b>HBM 叙事直接受益（韩国央行「受 HBM 带动，明年芯片产量上升」）</b></td></tr>
      <tr><td>삼성전자（005930）</td><td>223,500</td><td><b class="dk-up">+4.93%</b></td><td>224,000 / +5.16%</td><td class="dr-wrap">存储 + 代工双线；<code>traded_at</code> 为空串，故仅列价格与涨跌幅、不列成交时点</td></tr>
    </tbody>
  </table>
  <div class="dr-tag" style="margin:12px 0 4px">商品 / 利率 / 汇率（JS 自动 · <code>market.json.comm</code> · <b class="dk-data">商品〔金 / 油〕/ 汇率 / 碳酸锂 10/26 · <b class="dk-caution">10Y 5.00% / 30Y 5.33% 为 10/23</b></b>）</div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:8px;font-size:12.5px;line-height:1.6">
    <b>口径提示（本版为「日韩 <b class="dk-up">10/27 早盘实时 08:43 复取</b> + 港股 <span class="dk-caution">10/26 收盘</span> + 商品汇率 <span class="dk-data">10/26</span> + 美债 <span class="dk-data">10/23</span>」，各段已逐项标注）：</b><br>
    <b class="dk-up">🟢 日韩 10/27 早盘（本版最重要的「改判证据」，与上一版方向相反）</b>——<b class="dk-up">日经225 63,345.75（<span class="dk-up">+1.86%</span>）、KOSPI 5,675.49（<span class="dk-up">+3.77%</span>）</b>（08:43 复取，韩股开盘约 13 分钟 · 日经开盘约 13 分钟）。<b class="dk-main">判读：上一版（10/26 收盘版）记录的是「日经 -0.80% / KOSPI -1.46%」的收跌，22:15 时的判断是「亚太与美股方向相反、外围给不出方向」；隔夜美股收盘全红 + 今晨韩股 +3.77%，<b class="dk-up">该判断已被完全逆转 —— 亚太不再是拖累项，而是今日 A股 开盘的第一顺位正贡献</b></b>。<b class="dk-caution">但须同时记录：韩股自 08:31 的 +4.05% 高点回落至 +3.77%，说明「高开后已有获利盘」，这与本版「高开回吐压力」的开盘判定同向</b>；<br>
    <b class="dk-up">韩存储双雄（本版存储链定价的直接依据）</b>——SK하이닉스 <b>1,358,000（<span class="dk-up">+6.51%</span>）</b>、삼성전자 <b>223,500（<span class="dk-up">+4.93%</span>）</b>，另有<b>日本铠侠 +6.8%</b>、<b>美光 10/26 收 <span class="dk-up">+2.98%</span>、WDC <span class="dk-up">+3.63%</span>、闪迪 <span class="dk-up">+1.42%</span></b>。<b class="dk-main">判读：存储链的「外部四地共振」（美股 + 韩股 + 日股 + 美光盘后无反转）已成立，<b class="dk-caution">这是本轮唯一具备跨市场一致性的主线，也是今日 A股 存储标的（长鑫科技 / 德明利等）开盘缺口的定价锚</b></b>；<br>
    <b class="dk-caution">港股 10/26 收盘（沿用，非本版刷新）</b>——恒生 <b class="dk-up">23,211.81（+0.51%）</b>（18:31）、恒生科技 <b class="dk-dn">3,857.53（-0.36%）</b>（16:08）。<b class="dk-caution">港股是 10/26 唯一「指数红但科技绿」的市场，与 A股 同日的分裂结构一致；10/27 港股开盘（09:30）是 A股 开盘前最后一块外部拼图，若恒科高开超 1.5% 则 A股 科技高开幅度可上修</b>；<br>
    <b class="dk-data">商品 / 汇率（10/26 口径，本版已刷新一日）</b>—— 现货黄金 <b class="dk-up">4,021.53（+0.59%）</b>、COMEX 黄金 <b class="dk-up">4,038.55（+0.76%）</b>；<b class="dk-risk">WTI 101.69（<span class="dk-dn">-1.53%</span>）、布伦特 110.66（<span class="dk-dn">-0.93%</span>）双双续跌</b>。<b class="dk-caution">🔴 关键背离（连续第三版）：油价三日回落，但 A股 石油石化资金 <span class="dk-up">+6.90 亿</span>（分位 93.3）仍为正 ⇒ 「成本下行利好炼化」的解释仍成立，但「油价上行 → 通胀再加速」这条链已彻底失效，本版据此把石化由「待验证」降级为「只做个股、不做板块」</b>；<b class="dk-data">碳酸锂主连 95,280（10/26，与前值持平）；人民币中间价 6.7162（10/26）</b>；<br>
    <b class="dk-data">利率端：10Y <b>5.00%</b> / 30Y <b>5.33%</b> = <b>10/23</b> 口径（连续第三版未刷新）</b>——<b class="dk-caution">本机脚本不覆盖美债实时报价，属长期缺口；上一版设定的「10Y 是否突破 5.1%」复核项<b class="dk-risk">仍无法验证</b>，本版如实标为「未决项」，不作为任何结论依据</b>。<b class="dk-risk">但须注意：本周 10/29 凌晨 FOMC + 欧央行 + 日央行三央行议息（北京时间 10/29 至 10/30 先后公布），华泰基准情形为「年内 12 月再加息 1 次、明年加息 2 次」⇒ 长端利率是本周最大的未定价变量</b>。</div>
</div>

'''

cut('<!-- 2 日韩股市与商品 -->', '<!-- 3 隔夜美股复盘 -->', SEC2, '2 段')

# ────────────────────────── 3 段（含 US-MEDICAL 块整段移除）──────────────────────────
SEC3 = '''<!-- 3 隔夜美股复盘 -->
<div class="dr-h" data-version="preopen-0840">3 · 隔夜美股复盘（<b class="dk-up">10/26 完整收盘〔结算价〕</b> · <code>us_kline.latest = 2026-10-26</code> / <code>prev = 2026-10-23</code> · 23/23 全量双日 · <b class="dk-up">三大指数全红</b> · <b class="dk-up">存储 + 光通信单点暴动</b> · <b class="dk-caution">上一版（22:15）引用的是 10/26 盘中约 45 分钟〔非收盘价〕，本版已收口</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag" style="margin-bottom:4px">三大指数（10/26 收盘 · 环比 10/23 收盘）</div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>指数</th><th>10/26 收盘</th><th>10/23 收盘</th><th>涨跌</th><th>读数</th></tr></thead>
    <tbody>
      <tr><td><b>道琼斯</b></td><td>52,361.58</td><td>52,215.16</td><td><b class="dk-up">+0.28%</b></td><td class="dr-wrap">涨幅最小，价值 / 防御端跟涨但非主角</td></tr>
      <tr><td><b>标普500</b></td><td>7,676.77</td><td>7,623.68</td><td><b class="dk-up">+0.70%</b></td><td class="dr-wrap">全市场普涨，成长权重贡献主要涨幅</td></tr>
      <tr><td><b>纳斯达克</b></td><td>26,169.38</td><td>25,955.34</td><td><b class="dk-up">+0.82%</b></td><td class="dr-wrap"><b>领涨</b>；<b class="dk-caution">上一版 22:15 时读到的是 +0.29%（10:01 ET 盘中），尾盘 5.5 小时继续上行 0.53pct ⇒ 「盘中读数不足以定方向」再次被验证</b></td></tr>
    </tbody>
  </table>
  <div class="dr-tag" style="margin:12px 0 4px">存储链（<b class="dk-up">四地共振</b>）</div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>标的</th><th>收盘</th><th>涨跌</th><th>读数</th></tr></thead>
    <tbody>
      <tr><td>SKHY（海力士 ADR）</td><td>142.62</td><td><b class="dk-up">+4.09%</b></td><td class="dr-wrap">ADR 领先韩股本体，今晨韩股 SK하이닉스 +6.51% 已跟上</td></tr>
      <tr><td>WDC（西部数据）</td><td>356.13</td><td><b class="dk-up">+3.63%</b></td><td class="dr-wrap"><b>上一版的最大风险项已解除</b>：10/23 曾因「WDC 营收 +55% 但盘后 -7%~-8%」把存储链定性为「估值 + 预期差双腿」，本日收盘 +3.63% 说明预期差已被消化</td></tr>
      <tr><td>MU（美光）</td><td>903.70</td><td><b class="dk-up">+2.98%</b></td><td class="dr-wrap">存储周期主线，HBM 产能指引正面</td></tr>
      <tr><td>SNDK（闪迪）</td><td>1,255.58</td><td><span class="dk-up">+1.42%</span></td><td class="dr-wrap">NAND 端跟涨但幅度最小，说明本轮驱动偏向 DRAM/HBM 而非全存储</td></tr>
    </tbody>
  </table>
  <div class="dr-tag" style="margin:12px 0 4px">光通信 / 算力（<b class="dk-up">幅度最大的一组</b>）</div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>标的</th><th>收盘</th><th>涨跌</th><th>读数</th></tr></thead>
    <tbody>
      <tr><td><b>LITE（朗美通）</b></td><td>818.10</td><td><b class="dk-up">+8.19%</b></td><td class="dr-wrap"><b>全池第一</b>；上一版 10:01 ET 盘中仅 +3.69%，尾盘再涨 4.5pct</td></tr>
      <tr><td>AAOI</td><td>71.94</td><td><b class="dk-up">+6.56%</b></td><td class="dr-wrap">光模块二线弹性更大，<b class="dk-caution">与 A股 剑桥科技 10/26 -7.89% 形成最极端的单日反向</b></td></tr>
      <tr><td>COHR（相干）</td><td>221.50</td><td><b class="dk-up">+5.83%</b></td><td class="dr-wrap">光器件龙头，三只光链标的同步走强 ⇒ 板块级而非个股事件</td></tr>
      <tr><td>MRVL（迈威尔）</td><td>233.78</td><td><span class="dk-up">+2.31%</span></td><td class="dr-wrap">定制 ASIC / 光 DSP，跟随光链</td></tr>
      <tr><td>NVDA</td><td>216.00</td><td><span class="dk-up">+2.39%</span></td><td class="dr-wrap">算力总龙头，涨幅居中；<b>催化 = Anthropic 预计资本开支仍将大幅增长、AI 算力需求维持高位</b></td></tr>
      <tr><td>TSLA</td><td>391.62</td><td><b class="dk-up">+5.21%</b></td><td class="dr-wrap">非 AI 硬件链，属个股事件驱动，<b class="dk-caution">不纳入今日 A股 主线映射</b></td></tr>
    </tbody>
  </table>
  <div style="font-size:12.5px;line-height:1.6;margin-top:6px">
    <b class="dk-main">① 本段结论（与上一版的三处差异，逐条结账）</b><br>
    <b class="dk-up">① 上一版「最大未决项」已结账</b>：22:15 时设定的判据是「<b>若收盘三大指数全绿且纳指跌幅超 1% ⇒ 开盘预判下调为「低开破位风险」，仓位归 0</b>」。实际结果 = <b class="dk-up">三大全红</b>（+0.28% / +0.70% / +0.82%），<b>纳指不仅未跌，反而领涨</b> ⇒ <b class="dk-up">该下调条件未触发，方向改为上调一档</b>。<br>
    <b class="dk-risk">② 上一版「外盘修复对 A股 科技链条的传导已被切断」的判断，被隔夜行情直接否证</b>：22:15 时该结论建立在「费半 +0.90% / NVDA +1.81% / MU +1.42% / LITE +3.69%（10:01 ET 盘中）」与「A股 电子 -146.16 亿」的对比上，属于<b>用盘中读数对抗收盘资金</b>；<b class="dk-caution">本版修正为：不是「传导被切断」，而是「传导被推迟一个交易日」—— 10/26 A股 的杀跌发生在美股暴涨之前，两者不构成矛盾</b>。<br>
    <b class="dk-caution">③ 存储链的风险定性由「双腿」退回「单腿」</b>：上一版把 WDC 盘后 -7%~-8% 视为「估值杀 + 预期差」双腿；本日 WDC 收 +3.63%，<b>预期差腿基本解除，仅剩估值腿（10Y 5.00% 高位）</b>。<b class="dk-risk">但估值腿正是最硬的一条（本周 FOMC）</b>，故本版对存储链的定级是「外部顺风成立、但不可加杠杆」。<br><br>
    <b class="dk-main">② 口径声明（三条）</b>：<b>① 本段全部为 10/26 完整收盘价</b>（<code>us_kline.latest.date = 2026-10-26</code>，<code>quotes.us_*.time = 16:00~17:15 ET</code>），<b class="dk-up">无任何盘中读数混入</b>；<b>② 美股映射 13 只 + 医疗 10 只 + 参考 2 只，均取同一收盘日</b>；<b>③ VIX = 18.39（10-26 结算，前值 19.45，<span class="dk-up">-5.45%</span>）⇒ 波动率同步回落，与「风险偏好修复」方向一致，是本版上调方向的第三条独立证据</b>。
  </div>
</div>

'''

cut('<!-- 3 隔夜美股复盘 -->', '<!-- 4 重点宏观 -->', SEC3, '3 段（含 US-MEDICAL 移除）')

# ────────────────────────── 4 段 ──────────────────────────
SEC4 = '''<!-- 4 重点宏观 -->
<div class="dr-h" data-version="preopen-0840">4 · 重点宏观（<b class="dk-data">日历轨为准</b> · 复盘日 10/26 · 指引日 10/27 · 最新公布值 + 公布日 + 龄期 · <b class="dk-caution">今日（10/27）事件：20:15 美国 ADP 周度就业 / 20:30 美国 9 月数据 · 本周核心 = 10/29 凌晨美联储 + 欧央行 + 日央行三央行议息</b> · 美国 9 月 CPI 3.7% / 核心 2.6%（已 13 天）· 非农 +2.9 万（已 25 天）· 初请 19.4 万（已 5 天））</div>
<div class="dr-card">
  <div style="font-size:12.5px;line-height:1.6">
    <b class="dk-main">① 美国（<b class="dk-data">日历轨</b> · <code>daily_macro.us.calendar</code> · <code>as_of = 2026-10-27 08:31</code> · <code>days_fetched = 26</code> · 龄期 = 今日 − 公布日，<b>现算</b>）</b>
  </div>
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">
    <thead><tr><th>指标</th><th>最新值</th><th>预期</th><th>前值</th><th>公布日</th><th>龄期</th><th>读数含义</th></tr></thead>
    <tbody>
      <tr><td><b>CPI 同比</b>（9 月）</td><td><b class="dk-risk">3.7%</b></td><td>3.6%</td><td>3.4%</td><td>2026-10-14</td><td>13 天</td><td class="dr-wrap">高于预期 0.1pct、高于前值 0.3pct ⇒ <b>通胀重新加速</b>，是本轮「杀估值」的宏观基础；龄期 13 天，边际影响递减但不消失</td></tr>
      <tr><td>核心 CPI 同比（9 月）</td><td><b class="dk-caution">2.6%</b></td><td>2.5%</td><td>2.4%</td><td>2026-10-14</td><td>13 天</td><td class="dr-wrap">亦高于预期 ⇒ <b>非油价单一因素驱动</b>，核心通胀同步抬升</td></tr>
      <tr><td>CPI 月率（9 月）</td><td>0.6%</td><td>0.6%</td><td>0.4%</td><td>2026-10-14</td><td>13 天</td><td class="dr-wrap">符合预期但继续加速（0.4% → 0.6%）</td></tr>
      <tr><td>核心 CPI 月率</td><td>0.3%</td><td>0.2%</td><td>0.3%</td><td>2026-10-14</td><td>13 天</td><td class="dr-wrap">高于预期，核心粘性未解</td></tr>
      <tr><td><b>非农</b>（9 月）</td><td><b class="dk-risk">+2.9 万</b></td><td>9.0 万</td><td>13.3 万</td><td>2026-10-02</td><td>25 天</td><td class="dr-wrap"><b>大幅不及预期（缺口 6.1 万）</b>且低于前值 ⇒ 就业端已明确走弱；<b class="dk-caution">与 CPI 3.7% 组合成「滞胀」形态，是本框架最不利的宏观组合</b></td></tr>
      <tr><td>失业率（9 月）</td><td>4.2%</td><td>4.1%</td><td>4.1%</td><td>2026-10-02</td><td>25 天</td><td class="dr-wrap">高于预期 0.1pct，与非农走弱同向</td></tr>
      <tr><td>初请失业金</td><td>19.4 万</td><td>20.0 万</td><td>19.9 万</td><td>2026-10-22</td><td>5 天</td><td class="dr-wrap">低于预期 ⇒ 裁员端尚未恶化，与非农形成矛盾信号；<b class="dk-caution">两项分歧是本版「滞胀」定性中唯一的反向证据</b></td></tr>
    </tbody>
  </table>
  <div style="font-size:12.5px;line-height:1.6;margin-top:6px">
    <b class="dk-main">② 今日（10/27）事件日历（日历轨 + 新闻轨交叉）</b><br>
    · <b class="dk-data">20:15</b> 美国至 10 月 10 日当周 <b>ADP 就业人数周度变动</b>（上一期 1.85 万，龄 7 天）；<br>
    · <b class="dk-data">20:30</b> 美国 9 月数据（东财日历条目原文在此处截断，<b class="dk-caution">本版不推测具体指标，如实标注为「待公布」</b>）；<br>
    · <b class="dk-risk">本周核心：10/29 凌晨美联储 FOMC + 欧央行 + 日央行三央行议息</b>（北京时间 10/29 至 10/30 先后公布），另加拿大央行、新西兰央行本周亦开会。<b class="dk-caution">华泰基准情形 = 美联储「年内 12 月再加息 1 次、明年加息 2 次」，并预计本次会议维持紧缩倾向以免金融条件再度过度宽松</b> ⇒ <b class="dk-risk">「加息」而非「降息」是本轮的政策主基调，这与市场习惯的宽松叙事相反，是必须显式记录的宏观前提</b>。<br><br>
    <b class="dk-main">③ 本版对宏观的使用方式（三条）</b><br>
    ① <b>宏观不构成今日的做多依据</b>：CPI 3.7% + 非农 2.9 万 = 滞胀，10Y 5.00%，三央行议息在即 ⇒ <b class="dk-risk">外部估值端仍是压制项</b>；今日的做多依据只能来自「隔夜外盘价格 + 存储链景气」这一条，<b>不来自宏观</b>。<br>
    ② <b>龄期用法</b>：CPI（13 天）/ 非农（25 天）均属「已定价」，<b>不因这两个数字再调整方向</b>；真正未定价的是 10/29 三央行。<br>
    ③ <b>数据缺口如实披露</b>：<code>daily_macro.us.stale</code> 标记 <b>核心 PCE / 整体 PCE / CPI / 非农 / 初请 / GDP / 美债收益率</b> 七项为 stale（主因百度日历 10-21 / 10-15 / 10-07 三次 <code>HTTPError</code>，已记 <code>log</code>），<b class="dk-caution">本版 CPI / 非农 / 初请 三项取日历轨最新值（非 stale 兜底的原值），PCE 与 GDP 本版无可用值，故不置评</b>。<br>
    ④ <b>中国侧</b>：<code>daily_macro.china</code> 本日无新增读数（pmi / gdp / cpi / lpr 均为既有值），<b>不虚构</b>；上一交易日已知的央行披露「9 月沪深两市日均成交环比 -18.9%」仍为流动性收缩的佐证。
  </div>
</div>

'''

cut('<!-- 4 重点宏观 -->', '<!-- 5 重点科技 -->', SEC4, '4 段')

# ────────────────────────── 5 段 ──────────────────────────
SEC5 = '''<!-- 5 重点科技 -->
<div class="dr-h" data-version="preopen-0840">5 · 重点科技（对照 <b class="dk-up">最近一个美股收盘日 = 2026-10-26</b> · 六条主线逐条给「外部读数 → A股 映射 → 今日观察点」· <b class="dk-caution">本段全部外部读数均为收盘价，非盘中</b>）</div>
<div class="dr-card" style="margin-top:4px">
  <table class="dr-tbl" style="width:100%;border-collapse:collapse;font-size:12.5px">
    <thead><tr><th>主线</th><th>外部读数（10/26 收盘）</th><th>A股 映射</th><th>今日观察点</th></tr></thead>
    <tbody>
      <tr><td><b class="dk-up">存储 / HBM</b></td><td class="dr-wrap"><b>美光 903.70 <span class="dk-up">+2.98%</span> · WDC 356.13 <span class="dk-up">+3.63%</span> · 闪迪 <span class="dk-up">+1.42%</span> · SKHY(ADR) <span class="dk-up">+4.09%</span></b>；今晨韩股 <b>SK하이닉스 <span class="dk-up">+6.51%</span> / 삼성전자 <span class="dk-up">+4.93%</span></b>、日本 <b>铠侠 <span class="dk-up">+6.8%</span></b></td><td class="dr-wrap">长鑫科技（10/26 <span class="dk-dn">-0.44%</span>，全池最抗跌）· 德明利（观察池）· 兆易创新等存储设计</td><td class="dr-wrap"><b class="dk-caution">四地共振已成立，缺口方向确定向上；观察 09:45 前能否守住开盘价的 80%（即回吐不超过 20%）</b>；催化原文 = 韩国央行「受 HBM 带动，明年芯片产量将上升」</td></tr>
      <tr><td><b class="dk-up">光通信 / CPO</b></td><td class="dr-wrap"><b>LITE 818.10 <span class="dk-up">+8.19%</span> · AAOI <span class="dk-up">+6.56%</span> · COHR <span class="dk-up">+5.83%</span></b>（三只同步 ⇒ 板块级而非个股事件）</td><td class="dr-wrap">剑桥科技（10/26 <b class="dk-dn">-7.89%</b>，全池跌幅第一）· 永鼎股份（<span class="dk-dn">-6.38%</span>）· 华工科技（<span class="dk-dn">-2.98%</span>）</td><td class="dr-wrap"><b class="dk-risk">昨日砸盘资金与今日抢反弹资金非同一批 ⇒ 观察「高开后 30 分钟内的分时是否回补昨日跌幅一半以上」，回补不足 = 出货式高开</b></td></tr>
      <tr><td><b class="dk-caution">算力 / AI 基建</b></td><td class="dr-wrap">NVDA <span class="dk-up">+2.39%</span> · MRVL <span class="dk-up">+2.31%</span>；催化 = <b>Anthropic 预计资本开支仍将大幅增长，AI 算力需求高位</b>；<b class="dk-caution">风险 = 其「资本开支或显著增长」的表态同时被读作成本端压力</b></td><td class="dr-wrap">中科曙光（观察池）· 计算机板块（资金 <span class="dk-dn">-8.42 亿</span>，分位 23.3，背离 B）</td><td class="dr-wrap"><b class="dk-caution">计算机是 31 板块中唯一「站上 EMA20 但资金为负」的科技线（收 4,201.01 &gt; EMA20 4,180.49）；观察资金能否转正 ≥+10 亿，缺此不入</b></td></tr>
      <tr><td><b class="dk-up">创新药 / CXO</b></td><td class="dr-wrap">医疗 10 只 <b class="dk-up">8 涨 2 跌、组内均值 +0.77%</b>，最强 CRL <span class="dk-up">+3.45%</span>、最弱 IQV <span class="dk-dn">-2.06%</span>；<b>催化 = 药明康德进一步上调全年收入指引，创新药产业链持续高景气</b></td><td class="dr-wrap">医药生物（资金 <span class="dk-up">+7.19 亿</span>，分位 96.7，暗线 C）· 三生国健（观察池）· ST万邦</td><td class="dr-wrap"><b class="dk-caution">「钱到话未到」的典型（语料仅 2 条、技术仍低于 EMA20 1.96%）；今日若药明系高开带板块，观察资金能否连续第二日为正</b></td></tr>
      <tr><td><b class="dk-caution">智能驾驶 / 机器人</b></td><td class="dr-wrap">TSLA <span class="dk-up">+5.21%</span>（个股事件）；<b>国内催化密集：小鹏 Robotaxi 获批公开示范运营资质、大众集团（中国）取得 L3 级测试牌照（目标 2027 年 L3 技术就绪）</b></td><td class="dr-wrap">汽车（资金 <span class="dk-up">+11.60 亿</span>，分位 <b>100.0</b> 全市场第一，共振 A）· 汽车零部件 <span class="dk-up">+10.23 亿</span></td><td class="dr-wrap"><b class="dk-up">本版唯一「资金 + 语料 + 催化」三对齐的方向；观察汽车资金能否连续第三日为正（已连续 2 日）</b>；<b class="dk-caution">但技术仍破位（10-23 收 5,954.84 &lt; EMA20 6,078.16）</b></td></tr>
      <tr><td><b class="dk-caution">AI 应用 / 传媒</b></td><td class="dr-wrap">无直接美股对标；国内催化 = <b>广电「十五五」规划出台，明确 AI 渗透率不低于 95%</b>；OpenAI 推出 GPT-6.1 Terra</td><td class="dr-wrap">传媒（资金 <span class="dk-up">+3.69 亿</span>，语料 27 条但<b class="dk-caution">标题多为半导体串味</b>）· 奥飞娱乐（10/26 五福同享 88 分，全市场唯一）</td><td class="dr-wrap"><b class="dk-risk">语料标签可信度低，只按资金侧解读；奥飞娱乐属题材股而非科技主线，本版不因「五福同享」升级为可执行</b></td></tr>
    </tbody>
  </table>
  <div class="dr-note" style="margin-top:6px"><b class="dk-caution">口径提示</b>：外部读数全部为 <b>2026-10-26 完整收盘〔结算价〕</b>，<b>无盘中数据</b>；A股 映射标的的涨跌幅为 <b>10/26 完整收盘</b>，非今日盘前。<b class="dk-risk">本段不含任何买卖建议；个股仅作产业链位置示例</b>。</div>
</div>

'''

cut('<!-- 5 重点科技 -->', '<!-- 5.5 产业链/景气度 -->', SEC5, '5 段')

# ────────────────────────── 5.5 段 ──────────────────────────
SEC55 = '''<!-- 5.5 产业链/景气度 -->
<div class="dr-h" data-version="preopen-0840">5.5 · 产业链 / 景气度评估（六条链 · 每条含 <b class="dk-main">今日观察要点</b> · 数据基准 = A股 10/26 收盘 + 美股 10/26 收盘 + 日韩 10/27 早盘）</div>
<div class="dr-card" style="margin-top:4px">
  <div style="font-size:12.5px;line-height:1.7">
    <b class="dk-up">① 存储链（DRAM / HBM / NAND）—— 景气度：上行（最强）</b><br>
    · 证据链：<b>韩国央行「受 HBM 产品带动，明年芯片产量将上升」</b> + 韩国存储股受「股东回报增长前景 + 资本开支预期」提振 + 日本铠侠 +6.8% + 美光 +2.98% / WDC +3.63% / SKHY +4.09%。<b>四地（美 / 韩 / 日 / 台链）同日同向，是本轮唯一跨市场一致的主线</b>。<br>
    · A股 位置：<b class="dk-risk">背离 B（电子 -146.16 亿，分位 0，语料 65 条全市场第一）</b> —— 外部景气与国内资金完全相反。<br>
    · <b class="dk-main">今日观察要点：09:30–10:00 电子板块资金方向。若开盘 30 分钟净流入 ≥+20 亿 ⇒ 「外强内弱」被打破，存储可恢复观察；若继续净流出 ≥50 亿 ⇒ 高开即出货，科创50 下探 1,300。</b><br><br>
    <b class="dk-up">② 光模块 / 光纤链 —— 景气度：上行（幅度最大）</b><br>
    · 证据链：LITE +8.19% / AAOI +6.56% / COHR +5.83%，<b>三只同步 ⇒ 板块级重定价</b>；MRVL +2.31% 跟随。<br>
    · A股 位置：<b class="dk-risk">双冷 D（通信 -47.54 亿，分位 3.3，偏离 EMA20 -12.01% 为 31 板块最深之一）</b>；个股剑桥 -7.89% / 永鼎 -6.38% 于 10/26 收在日内低点。<br>
    · <b class="dk-main">今日观察要点：缺口幅度 vs 回补幅度。若剑桥科技高开 ≥+5% 但 10:00 前回吐过半 ⇒ 判定为「昨日砸盘方的出货窗口」，本版不参与；若高开且守住 +3% 以上 ⇒ 视为换手成功。</b><br><br>
    <b class="dk-caution">③ 算力 / AI 基建 —— 景气度：高位（但有成本端争议）</b><br>
    · 证据链：NVDA +2.39% / MRVL +2.31%；<b>Anthropic 资本开支仍将大幅增长（需求侧正）</b>，但同一表态亦被读作「成本端压力」（供给侧负）。<br>
    · A股 位置：计算机 <b>-8.42 亿（分位 23.3，背离 B）</b>，但<b class="dk-up">收 4,201.01 仍站上 EMA20 4,180.49（31 板块中仅 2 席之一）</b>。<br>
    · <b class="dk-main">今日观察要点：计算机资金能否转正 ≥+10 亿 且守住 EMA20 4,180.49（双条件，缺一不入）。</b><br><br>
    <b class="dk-caution">④ 创新药 / CXO —— 景气度：上行（政策 + 业绩双击）</b><br>
    · 证据链：<b>药明康德上调全年收入指引</b> + 医疗 10 只 8 涨 2 跌（组内均值 +0.77%，最强 CRL +3.45%）；国内另见「AI 制药交易提速，临床验证成下一关口」「北京 AI 医疗产品临床用量增多」。<br>
    · A股 位置：医药生物资金 <b>+7.19 亿（分位 96.7，暗线 C）</b>，但<b class="dk-caution">语料仅 2 条、技术仍低于 EMA20 7,634.55 达 1.96%</b>。<br>
    · <b class="dk-main">今日观察要点：医药资金能否连续第二日为正（10/26 为单日反转 +24.32 亿）；若转负 ⇒ 「钱先到」退化为「一日脉冲」。</b><br><br>
    <b class="dk-up">⑤ 汽车 / 智能驾驶链 —— 景气度：上行（催化最密）</b><br>
    · 证据链：小鹏 Robotaxi 获批公开示范运营资质 + 大众集团（中国）取得 L3 级测试牌照 + TSLA +5.21%；A股 汽车资金 <b>+11.60 亿（分位 100.0，全市场第一）</b>、汽车零部件 <b>+10.23 亿</b>。<br>
    · A股 位置：<b class="dk-up">共振 A · 唯一「资金 + 语料 + 催化」三对齐</b>；<b class="dk-caution">但技术仍破位（10-23 收 5,954.84 &lt; EMA20 6,078.16，趋势 downtrend）</b>。<br>
    · <b class="dk-main">今日观察要点：汽车资金能否连续第三日为正 + 板块能否收复 6,078.16；两者同时满足才允许提升至 20% 上沿，否则仅做个股。</b><br><br>
    <b class="dk-risk">⑥ 有色金属 / 资源链 —— 景气度：分化（价格与资金背离）</b><br>
    · 证据链：<b>中信证券 Q4 大宗展望「供给约束延续、分化加深」、预计 26Q4 国内铝价 22,500 元/吨</b>；但碳酸锂主连 95,280 持平、WTI -1.53% / 布伦特 -0.93% 续跌。<br>
    · A股 位置：<b class="dk-risk">背离 B（-35.18 亿，语料 24 条）</b>；永杉锂业 -1.96%。<br>
    · <b class="dk-main">今日观察要点：语料热度由 11 条升至 24 条全部来自「中信 Q4 展望」一篇的分拆，属单一来源放大；观察有色金属资金能否止跌，未止跌前不作为方向。</b>
  </div>
</div>

'''

cut('<!-- 5.5 产业链/景气度 -->', '<!-- 6 新闻整合 -->', SEC55, '5.5 段')

io.open(P, 'w', encoding='utf-8-sig').write(s)
print('Part B 写盘完成：%d → %d 字符' % (orig, len(s)))
