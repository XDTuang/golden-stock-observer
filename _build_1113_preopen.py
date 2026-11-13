# -*- coding: utf-8 -*-
"""11/13 周五 盘前版 analysis.html 段替换（0/0.5/1/1.1/1.2/2/3/4/5/5.5/6/7.1/7.3/7.4/8/9 + 头部注释）"""
import io, re, sys

P = 'data/daily_review/analysis.html'
s = io.open(P, encoding='utf-8-sig').read()
HAD_BOM = io.open(P, 'rb').read(3) == b'\xef\xbb\xbf'

V = 'preopen-0945'
RD = '2026-11-12'
FD = '2026-11-13'
ATTR = 'data-version="%s" data-review-date="%s" data-for-date="%s"' % (V, RD, FD)

def h(text):
    return '<div class="dr-h" %s>%s</div>' % (ATTR, text)

# ══════════════════════ 头部注释 ══════════════════════
HEADER = """
<!--
 版本：11/13 周五 盘前版（08:40 档期任务 · 09:14 补触发 · 盘前逻辑）
 性质：盘前推演。A股 = 11/12 完整收盘〔结算价〕；美股 = **11/12 完整收盘〔昨夜 · 结算价〕**（已含 NVDA 辞职事件的完整定价，不再是盘前报价）；日韩 = 11/13 早盘（09:45 KST，非收盘价）；商品 = 11/13 早盘。本版为 11/13 开盘指引。
 口径：A股 2026-11-12 完整收盘 / 美股 2026-11-12 完整收盘 / 日韩 2026-11-13 早盘 / 港股 11-12 收盘 / 商品 11-13 早盘 / 美债 11-10 结算〔T+2 龄期〕/ VIX 11-12 结算 18.70 / 宏观日历轨 as_of 11-13 08:47。
 当前值（本版，勿与上一版混读）：上证 3,655.83（-0.67%）/ 深成 11,197.98（-1.68%）/ 创业板 2,509.43（-2.44%）/ 科创50 1,309.84（+0.73%）/ 涨 713 跌 3,831（比 0.19）/ 涨停 41 跌停 11 / 主力 -505.98 亿 · 申万一级合计 -525.12 亿 / 情绪 14「恐慌下跌」/ 四象限 0 / 2 / 9 / 20 / 板块技术 L4=0 L3=2 L2=7 L1=22 / 两市 19,320.8 亿（+15.3%）。
 隔夜美股（11/12 完整收盘，本版核心变量）：道 52,297.09（-0.36%）/ 标普 7,592.40（-0.35%）/ 纳 25,366.09（-0.39%）/ VIX 18.70（+6.92%）；NVDA 开 151.01（-13.08%）→ 低 148.80（-14.36%）→ 收 166.19（-4.34%），自最低收窄 10.02pct，市值单日蒸发 1,820 亿美元；博通 / AMD 逆势 +5%、费半盘中转涨；思科 / 应用材料 / Cerebras 业绩超预期。存储四线 -2.39%、光通信三线 -3.35%。
 今早亚太（11/13 · 09:45 KST）：日经 61,771.67（+1.57%）/ KOSPI 5,474.68（+2.47%，盘中曾 +3%）/ SK海力士 1,290,500（+2.91%）/ 三星电子 213,500（+2.64%）。
 上一版（11/12 收盘版 22:15）：四象限 0 / 2 / 9 / 20（更早一版 1 / 1 / 11 / 18）/ L4=0 L3=2 L2=7 L1=22 / 情绪 14 · 主力 -505.98 亿 / 判定 偏空 · 中高 · 低开破位风险 · 仓位 20%–25%。
 判定（本版）：中性（上一版 偏空，上调一档）/ 中高置信度 / 高开回吐压力 / 仓位 25%–35% / 风险 中高（上一版 高，下调一档）。
 门禁：十四道（结果见 8 段与提交信息）
-->
"""

# ══════════════════════ 0 · 结论先行 ══════════════════════
S0 = """<!-- 0 结论先行 -->""" + h(
 '0 · 结论先行（速览卡 · <b>11/13 周五 盘前版</b> · 复盘日 <b>11/12（周四）</b> · A股 <b class="dk-up">11/12 完整收盘〔结算价〕</b> + 美股 <b class="dk-up">11/12 完整收盘〔昨夜 · 结算价〕</b> + 日韩 <b class="dk-caution">11/13 早盘〔09:45 KST · 非收盘〕</b>）'
) + """
<div class="dr-card" data-preopen="1" data-agent="preopen" style="margin-top:4px">
  <div class="dr-tag">① 一句话结论</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">昨夜美股把「盘前 -11%」的恐慌自己吃掉了 —— 三大指数只跌 0.35%，NVDA 从盘中最低 -14.36% 拉回到 -4.34%，今早日韩强反弹（KOSPI +2.47%）。所以今日 A股 的起点不是「低开破位」，而是「高开验证」：高开之后能否站稳 <b>MA20 3,672.71</b>、并向上试 <b>3,700 双顶</b>，才是今天真正的分水岭。</b>
    上证 <b class="dk-dn">3,655.83（-0.67%）</b>、深成 <b class="dk-dn">11,197.98（-1.68%）</b>、创业板 <b class="dk-risk">2,509.43（-2.44%）</b>、科创50 <b class="dk-up">1,309.84（+0.73%）</b>；涨 <b class="dk-risk">713</b> / 跌 <b class="dk-risk">3,831</b>（比 <b class="dk-risk">0.19</b>）、跌停 11 家、主力 <b class="dk-risk">-505.98 亿</b>、情绪 <b class="dk-risk">14「恐慌下跌」</b>。<b class="dk-main">昨日是「放量派发」，今天要问的不是「跌不跌」，而是「外部修复能不能被 A股 采纳」</b>。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-up">② 隔夜发生了什么（只看已收盘的价格）</b>：道 <b>52,297.09（-0.36%）</b> / 标普 <b>7,592.40（-0.35%）</b> / 纳 <b>25,366.09（-0.39%）</b> / <b class="dk-caution">VIX 18.70（+6.92%，11-12 结算）</b>。核心一票：<b class="dk-caution">NVDA 开 151.01（-13.08%）→ 最低 148.80（-14.36%）→ 收 166.19（-4.34%）</b>，<b class="dk-main">自最低收窄 10.02 个百分点、收盘贴近当日高点 167.14，日内振幅 12.19%</b>；市值单日蒸发 <b>1,820 亿美元</b>。同一晚的对手盘：<b class="dk-up">博通 / AMD +5%、费半盘中转涨、思科 / 应用材料 / Cerebras 业绩超预期</b>。<b class="dk-caution">硬件链仍跌但跌幅收窄：存储四线 <b>-2.39%</b>（MU -1.59 / SNDK -4.11 / WDC -0.67 / SKHY -3.19）、光通信三线 <b>-3.35%</b>（AAOI -5.39 / LITE -3.61 / COHR -1.04）</b>。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">③ 上一版（11/12 收盘版）的「低开破位风险」需要修订 —— 这是本档第二次记录同一类错误</b>：上一版只用「NVDA 盘前 -11% + 美联储鹰派」外推指数，<b class="dk-risk">把个股盘前的跌幅当成了指数的跌幅</b>。实际收盘：指数 -0.35%、NVDA -4.34%、且是<b>从 -14.36% 拉回来的</b>。<b class="dk-main">⇒ 方法论修订：<b>个股盘前报价只能用于「个股」，指数层面必须等收盘</b>；两者混用时，开盘价的分布应取下沿之外再留一档缓冲（上一版 11/12 已犯「取中值」错误，本版是同一错误的第二次出现，已写入 0.5 段作为固定条目）</b>。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">④ 本版定调（跨页同值）</b>：方向 <b>中性</b>（上一版「偏空」上调一档）· 开盘 <b class="dk-caution">高开回吐压力</b> · 置信度 <b class="dk-main">中高</b> · 风险 <b class="dk-caution">中高</b>（上一版「高」下调一档）· 仓位 <b>25%–35%</b>（上一版 20%–25%，上调一档）。<br>
    <b class="dk-main">三条理由，均可在数据中复核</b>：<b>①</b> 外部锚由「双杀」变「单杀」—— 旗手端已止血（NVDA 收窄 10pct、半导体设备业绩超预期、博通 / AMD +5%），但<b class="dk-risk">分母端未愈</b>（美元触及 19 个月新高、12 月加息 50bp 概率 15.3%、<b>现货黄金 -2.67% 至 3,881</b>、WTI +1.03% 至 87.42、「金跌油涨」= 实际利率上行的定价未变）；<b>②</b> <b class="dk-up">今早日韩给出同步的正向映射</b>（日经 +1.57%、KOSPI +2.47%、海力士 +2.91%、三星 +2.64%）—— <b class="dk-main">这是自 11/10 以来第一次「母股领先于 A股 反弹」</b>，而 11/12 的失败正是「母股不认、A股 硬跟」；<b>③</b> <b class="dk-risk">但 A股 自身是放量派发形态</b>（19,320.8 亿 / +15.3%、创业板收在最低附近、情绪 14）+ 周五 + 上方 3,672.71 / 3,700 压制 → <b>只上调一档，不给「偏多」</b>。
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">⑤ 今日（11/13）硬线六条</b>：<b class="dk-risk">3,647.44</b>（11/12 低点 · 破位确认线）· <b class="dk-caution">3,653.14</b>（MA10）· <b>3,655.83</b>（11/12 收盘 · 平盘线）· <b>3,662.03</b>（MA5 · 短线修复门槛）· <b class="dk-main">3,672.71</b>（<b>MA20 · 今日第一道真压力</b>）· <b class="dk-risk">3,699.58 / 3,700</b>（11/12 高 · 双顶）。<b class="dk-main">执行口径：<b>①</b> 高开在 <b>+0.3%～+0.8%（3,667–3,685）</b>且在 10:00 前站上 <b>3,672.71</b> → 视为「外部修复被采纳」，仓位可持至 35%，但不追高；<b>②</b> 高开 <b>&gt;+1.0%（&gt;3,692）</b>而 30 分钟内回落至 3,672.71 下方 → 按「高开兑现」处理，仓位压回 25%；<b class="dk-risk">③</b> 高开 <b>&lt;+0.3%（&lt;3,667）</b> → 说明外部反弹未被采纳，按弱势处理、不加仓；<b class="dk-risk">④</b> 跌破 <b>3,647.44</b> 且 30 分钟不收回 → 破位成立，压至 10%–15%</b>。
  </div>
</div>

"""

# ══════════════════════ 0.5 · 深度判读 ══════════════════════
S05 = """<!-- 0.5 深度判读 -->""" + h(
 '0.5 · 深度判读（<b>三件事必须讲清</b>：上一版剧本的「对与错」、隔夜美股的「性质」、四象限的「维持与口径」）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">一、上一版（11/12 收盘版 22:15）剧本核对 —— 含未命中项</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">上一版给出四条判断，逐条对上隔夜实际：</b><br>
    <b class="dk-risk">① 开盘判断「低开破位风险（55%）/ 低开小于 -0.5%（20%）/ 低开超 -1.5%（25%）」→ <span class="dk-risk">未命中</span></b>：隔夜美股三大指数仅 -0.35%、NVDA 从 -14.36% 收窄至 -4.34%、纳指期货早盘 +0.3%、日韩今早高开 2% 以上 —— <b class="dk-risk">今日大概率是高开而非低开</b>。<b class="dk-main">根因 = 把「个股盘前 -11%」当成「指数跌幅」外推。上一版已把「当同一份材料里同时存在利多收盘与利空盘后时，开盘价应取下沿」写进方法论，<b class="dk-risk">但本次连「下沿」都用错了对象 —— 个股跌幅根本不是指数的下沿</b>。</b><br>
    <b class="dk-caution">② 方向「偏空」→ <span class="dk-caution">前提部分失效，本版上调</span></b>：偏空的两条前提中，「旗手失位」已被美股自己消化（NVDA 收盘仅 -4.34%、博通 / AMD +5%），「分母收紧」仍然成立（美元 19 个月新高、黄金 -2.67%）。<b class="dk-main">⇒ 两条前提去一存一 → 方向由「偏空」上调至「中性」，不是「偏多」</b>。<br>
    <b class="dk-up">③ 关键线「3,647.44 为唯一分水岭、3,653.14（MA10）为生死线」→ <span class="dk-up">保留有效</span></b>：外部修复不改变结构位 —— 3,647.44（11/12 低点）与 3,653.14（MA10）仍是今日下方两道硬线，<b>本版新增上方第一道真压力 MA20 3,672.71</b>（上一版未给出，属本版补充）。<br>
    <b class="dk-risk">④ 未预见项（主动记录）</b>：<b>a.</b> 未预见 NVDA 盘中最低 -14.36% 后收窄至 -4.34%（日内反转 10.02pct）；<b>b.</b> 未预见博通 / AMD +5%、费半盘中转涨、思科 / 应用材料 / Cerebras 业绩超预期；<b>c.</b> 未预见韩股 KOSPI 今早 +2.47%（盘中曾 +3%，李在明市场改革表态 + 存储双雄反弹）；<b>d.</b> 未预见黄金继续下跌 -2.67% 至 3,881（实际利率定价进一步强化）。
  </div>
  <div class="dr-tag" style="margin-top:10px">二、隔夜美股的性质：不是「二次杀估值」，而是「单点事件被消化 + 分母未愈」</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">支持「单点事件被消化」的证据</b>：<b>①</b> <b>指数跌幅与个股跌幅严重不匹配</b> —— NVDA -4.34% 而纳指仅 -0.39%，<b>卖压集中在单票，未扩散为板块</b>；<b>②</b> <b>NVDA 日内振幅 12.19%</b>（高 167.14 / 低 148.80），收盘 166.19 贴近高点 → <b class="dk-up">有承接盘</b>（媒体口径：散户逆势抄底 + 机构回补）；<b>③</b> <b class="dk-up">资金在「换标的」而非「离场」</b>：博通 / AMD +5%、费半盘中转涨、思科 / 应用材料 / Cerebras 业绩超预期；<b>④</b> <b class="dk-caution">VIX 仅 18.70（+6.92%）</b>，仍低于 11/09 的 19.92，远低于恐慌阈值 25 → 期权市场没有定价系统性风险。<br>
    <b class="dk-risk">反面证据（不可忽略）</b>：<b>① 分母端继续恶化</b> —— 美元触及 <b>19 个月新高</b>、12 月加息 50bp 概率 <b>15.3%</b>、旧金山联储戴利「可能需要进一步加息」、<b>现货黄金 -2.67% 至 3,881.16、COMEX -2.96%</b>、WTI <b class="dk-up">+1.03% 至 87.42</b>、布伦特 <b class="dk-up">+1.57% 至 94.21</b> —— <b class="dk-main">「金跌油涨」是本轮最稳定的组合，含义是「实际利率上行 + 通胀交易」，而不是「避险」</b>；<b>② 硬件链仍在跌</b>（存储 -2.39%、光通信 -3.35%），只是跌幅小于盘前；<b>③ 治理事件有二次发酵的通道</b>：Truist 下调 NVDA 评级、目标价腰斩，美参议院银行委员会传唤黄仁勋与卢特尼克作证，临时 CEO 克雷斯计划下周三召开公司会议 —— <b class="dk-caution">这三个时点（听证 / 会议 / Q3 财报）都在未来 1–2 周内，构成「利空未出尽」的结构</b>。<br>
    <b class="dk-main">本档判定：<b class="dk-caution">旗手端「止血」、分母端「未愈」</b> → 对应到 A股 的正确读法是：<b>高开可期（外部锚不再单边向下），但成长端的估值修复缺乏持续性（分母未松）</b>。这也是本版「中性 + 高开回吐压力」而非「偏多 / 高开延续」的全部依据。</b>
  </div>
  <div class="dr-tag" style="margin-top:10px">三、四象限（<code>cross_analysis.json</code> · <code>flow_date = 2026-11-12</code> · 新闻窗口 11/12 + 11/13 共 2 日 · 31 席 · 热度门槛 16 条 / 窗口）</div>
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:6px">
    <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);border-radius:6px;padding:8px 10px"><b class="dk-main">共振 A = 0（与上一版同值）</b> —— <b class="dk-risk">连续第二版清零</b>。「资金 + 语料双高」的板块在 11/12 已全部退出，本版<b>无新增</b>。<b class="dk-caution">含义：今日若出现反弹，性质是「超跌修复」，不是「共振驱动」</b></div>
    <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--orange);border-radius:6px;padding:8px 10px"><b class="dk-caution">背离 B = 2（与上一版同值）</b> —— <b class="dk-dn">电子</b>（语料 <b>65 条</b> · 日均 32.5，全场最热；资金 <b class="dk-dn">-79.05 亿</b>）、<b class="dk-dn">计算机</b>（语料 <b>24 条</b> · 日均 12.0；资金 <b class="dk-dn">-31.42 亿</b>）。<b class="dk-caution">两席语料几乎全部来自「英伟达 / 芯片股」单一事件的反复计数，热度含水分 → 今日电子若反弹，属「语料已透支后的技术性修复」</b></div>
    <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--blue);border-radius:6px;padding:8px 10px"><b class="dk-data">暗线 C = 9（与上一版同值）</b> —— 银行 +7.46（12 条）/ 农林牧渔 +4.33（3 条）/ 美容护理 +2.87（0 条）/ 医药生物 +2.52（3 条）/ 交通运输 +1.48（0 条）/ 钢铁 +0.64（3 条）/ 建筑装饰 +0.62（0 条）/ 国防军工 +0.61（8 条）/ 石油石化 +0.16（3 条）。<b class="dk-main">⇒ 9 席全部是「资金正、语料冷」的低估值 / 防守型板块；今日若大盘高开，这一栏反而是「相对收益下降」的一方</b></div>
    <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--green);border-radius:6px;padding:8px 10px"><b class="dk-risk">双冷 D = 20（与上一版同值）</b> —— 含 <b class="dk-dn">通信 -73.03 亿</b>（语料 4 条）、<b class="dk-dn">机械设备 -66.99 亿</b>、<b class="dk-dn">电力设备 -62.39 亿</b>、<b class="dk-dn">有色金属 -59.03 亿</b>、<b class="dk-dn">汽车 -39.15 亿</b>、<b class="dk-dn">传媒 -37.76 亿</b>。<b class="dk-risk">⇒ 20 席双冷 = 三分之二板块既无资金也无语料；今日高开若不能带动「资金」列回正，则仍是「指数反弹、结构不改善」</b></div>
  </div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-main">本版四象限 <b>0 / 2 / 9 / 20</b>，与上一版 <b>完全同值 —— 本版不发生迁移</b></b>。上一版已完成的迁移（<b class="dk-caution">1 / 1 / 11 / 18 → 0 / 2 / 9 / 20</b>：共振 -1、背离 +1、暗线 -2、双冷 +2）成因仍成立且未被推翻：<b>电子语料 40 → 69 条而资金 +177.41 亿 → -79.05 亿（摆幅 256.46 亿）、通信资金 +133.83 亿 → -73.03 亿</b>，属<b class="dk-risk">资金端真实转向</b>，不是语料口径变化。本版不改写该结论，只补充一条对今日有用的推论：<b class="dk-main">共振席连续两版为 0，意味着「今日的上涨若发生，只能由超跌修复或外部映射驱动，缺一环「资金 + 语料同向」的内部支撑 → 反弹的持续性应假定为 1–2 日，而不是趋势反转</b>。<br>
    <b class="dk-caution">必须同时记录的口径限制（本版新增，比上一版更明确）</b>：<code>cross_analysis.json</code> 生成于 <b>11-12 22:01</b>，其 <code>window.covered</code> 显示 <b>11/13 news = 0</b>，即 <b class="dk-risk">今早 08:47 抓取的 287 条（11/13）尚未入池</b>；而 <code>news_per_day</code> 仍按 2 日除权 → <b class="dk-caution">所有板块的「日均热度」被系统性低估约 50%</b>。本档因此<b>不把「双冷」用于否定任何板块的语料侧结论，只用它描述资金侧</b>；若今日收盘档重跑 <code>build_cross_analysis.py</code>，象限分布可能变化，届时以新产物为准并复核本页。
  </div>
</div>

"""

# ══════════════════════ 1 · 复盘日走势 ══════════════════════
S1 = """<!-- 1 昨日 A 股走势总结 -->""" + h(
 '1 · 复盘日（<b>11/12 周四</b>）A 股走势总结（<b class="dk-up">完整收盘〔结算价〕</b> · 涨 <b>713</b> / 跌 <b class="dk-risk">3,831</b>（比 <b class="dk-risk">0.19</b>）、涨停 <b>41</b> / 跌停 <b class="dk-risk">11</b>、情绪 <b class="dk-risk">14「恐慌下跌」</b> · <b class="dk-risk">上证 -0.67% 留 26.5 点长上影</b> · <b class="dk-risk">创业板 -2.44% 收在当日最低附近</b> · 本段即今日（11/13）的「参照基准」）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 指数（<b>A股 与 港股均为 11/12 完整收盘</b>）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>指数</th><th>收盘</th><th>涨跌幅</th><th>开盘</th><th>最高</th><th>最低</th><th>形态读数</th></tr></thead><tbody>
    <tr><td><b>上证指数</b></td><td>3,655.83</td><td><b class="dk-dn">-0.67%</b></td><td>3,673.06</td><td>3,699.58</td><td>3,647.44</td><td><div class="dr-wrap">长上影阴线（上影 26.5 / 实体 17.2）· <b class="dk-caution">收盘仍站 MA10 3,653.14 上方 2.7 点</b>、但已在 <b class="dk-risk">MA20 3,672.71 下方 16.9 点</b></div></td></tr>
    <tr><td><b>深证成指</b></td><td>11,197.98</td><td><b class="dk-dn">-1.68%</b></td><td>11,361.82</td><td>11,515.65</td><td>11,193.26</td><td><div class="dr-wrap">冲高 +1.11% 后收于 -1.68%，<b class="dk-risk">收在当日最低上方 4.7 点</b></div></td></tr>
    <tr><td><b>创业板指</b></td><td>2,509.43</td><td><b class="dk-risk">-2.44%</b></td><td>2,559.16</td><td>2,620.25</td><td>2,508.29</td><td><div class="dr-wrap"><b class="dk-risk">开 -0.50% → 高 +1.87% → 收 -2.44%</b>，自高点回落 <b class="dk-risk">4.31pct</b>，收在当日最低上方 1.1 点</div></td></tr>
    <tr><td><b>科创50</b></td><td>1,309.84</td><td><b class="dk-up">+0.73%</b></td><td>1,302.50</td><td>1,364.88</td><td>1,302.50</td><td><div class="dr-wrap"><b class="dk-caution">唯一红盘</b>，但高点 +4.96% → 收 +0.73%，<b class="dk-risk">回吐 4.23pct</b>；当日最低 = 开盘价</div></td></tr>
    <tr><td><b>北证50</b></td><td>908.07</td><td><b class="dk-dn">-1.65%</b></td><td>920.20</td><td>932.70</td><td>907.74</td><td><div class="dr-wrap">收在当日最低上方 0.33 点，小盘端同步失血</div></td></tr>
    <tr><td><b>恒生指数</b></td><td>24,008.55</td><td><b class="dk-dn">-1.26%</b></td><td>24,121.40</td><td>24,132.20</td><td>23,942.74</td><td><div class="dr-wrap">高开 0.47% 后全天走低，<b class="dk-caution">跌幅小于 A股 成长端</b></div></td></tr>
    <tr><td><b>恒生科技</b></td><td>3,931.93</td><td><b class="dk-risk">-2.36%</b></td><td>3,995.00</td><td>3,998.36</td><td>3,918.42</td><td><div class="dr-wrap">与创业板 -2.44% 基本同幅，<b class="dk-main">两岸科技端同步杀估值</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-tag" style="margin-top:10px">② 广度与资金（<code>realtime.json L0/L1</code> · 收盘口径 · <code>sector_flow.json</code>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">广度</b>：涨 <b>713</b> / 跌 <b class="dk-risk">3,831</b> / 平 62（总 4,606），<b class="dk-risk">涨跌比 0.19</b>（前一日 <b class="dk-up">1.97</b>）—— <b class="dk-risk">单日由「跌家数 : 涨家数 = 1 : 2」翻转为「1 : 5.4」</b>；涨停 <b>41</b>（前一日 87）、<b class="dk-risk">跌停 11</b>（前一日 0）。两市成交 <b>19,320.8 亿</b>（上证 8,795.4 + 深证 10,525.4），<b class="dk-risk">较前一交易日放大约 15%</b>。<br>
    <b class="dk-main">主力资金</b>：全市场 <b class="dk-risk">-505.98 亿</b>；申万一级合计 <b class="dk-risk">-525.12 亿</b>。分大类：<b class="dk-risk">大科技 -221.25 亿</b>（占全部流出 42%）/ <b class="dk-risk">大制造 -167.91 亿</b> / <b class="dk-risk">资源周期 -92.50 亿</b> / 大消费 -23.65 亿 / 基建公用 -14.62 亿 / 大金融 -2.83 亿 / <b class="dk-up">农林综合 +3.24 亿（唯一为正）</b>。<br>
    <b class="dk-main">净流入前八席</b>：银行 <b class="dk-up">+7.46</b> / 农林牧渔 <b class="dk-up">+4.33</b> / 美容护理 <b class="dk-up">+2.87</b> / 医药生物 <b class="dk-up">+2.52</b> / 交通运输 <b class="dk-up">+1.48</b> / 钢铁 <b class="dk-up">+0.64</b> / 建筑装饰 <b class="dk-up">+0.62</b> / 国防军工 <b class="dk-up">+0.61</b>（亿元，共 9 席为正）。<br>
    <b class="dk-main">净流出前八席</b>：电子 <b class="dk-dn">-79.05</b> / 通信 <b class="dk-dn">-73.03</b> / 机械设备 <b class="dk-dn">-66.99</b> / 电力设备 <b class="dk-dn">-62.39</b> / 有色金属 <b class="dk-dn">-59.03</b> / 汽车 <b class="dk-dn">-39.15</b> / 传媒 <b class="dk-dn">-37.76</b> / 计算机 <b class="dk-dn">-31.42</b>（亿元）。<br>
    <b class="dk-main">⇒ 一句话读法</b>：<b class="dk-risk">流入 9 席合计仅 +21.0 亿，流出 22 席合计 -546.1 亿</b> —— <b class="dk-main">这不是「换方向」，量级上就是「净离场」；防守席位（银行 / 农林牧渔 / 医药）承担的是「避风」职能，不是「接力」职能</b>。<br>
    <b class="dk-main">宽基 ETF（<code>realtime.json ETF</code> · 11-12）</b>：沪深300 <b class="dk-up">+0.43 亿</b> / 上证50 <b class="dk-dn">-0.53</b> / 科创50 <b class="dk-risk">-14.20</b> / 创业板 <b class="dk-up">+0.04</b> / 中证500 <b class="dk-risk">-9.58</b> / 中证1000 <b class="dk-dn">-0.13</b>，<b class="dk-risk">六只合计约 -23.97 亿</b>。<b class="dk-risk">⇒ 宽基端仍无护盘迹象，减仓集中于科创50 与中证500，与当日「科创50 冲高回落 4.23pct」方向一致</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 日内节奏（三段式：诱多 → 派发 → 尾盘杀）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b>开盘（09:30）</b>：上证 <b class="dk-caution">+0.21%</b>（3,673.06）、创业板 <b class="dk-dn">-0.50%</b>（2,559.16）、科创50 <b class="dk-up">+0.16%</b>（1,302.50，<b>即当日最低</b>）—— <b>分化开盘，半导体强、成长弱</b>。<br>
    <b>上午（至 11:30）</b>：科创50 攻至 <b class="dk-up">1,364.88（+4.96%）</b>，创业板冲至 <b class="dk-up">2,620.25（+1.87%）</b>，上证触及 <b>3,699.58（+0.51%）</b> —— <b class="dk-caution">三段全部在 3,700 一线受阻</b>（11/05 高 3,701.59 与 11/12 的 3,699.58 构成双顶）。<br>
    <b>午后（13:00–15:00）</b>：<b class="dk-risk">单边回落，无一次有效反抽</b>。创业板由 +1.87% 杀至 -2.44%（<b class="dk-risk">-4.31pct</b>），科创50 由 +4.96% 回落至 +0.73%（<b class="dk-risk">-4.23pct</b>），上证由 +0.51% 至 -0.67%。<br>
    <b class="dk-main">⇒ 节奏判读</b>：<b class="dk-risk">「开盘弱 → 上午强 → 午后弱 → 尾盘杀」是派发形态中最完整的一种</b>，同时满足三点：高点出现在上午（给隔夜利好留足出货时间）、回落无有效反抽（承接盘不足）、收盘贴近最低（尾盘无人愿护）。<b class="dk-main">⇒ 对今日的直接含义：<b class="dk-caution">如果今天高开，昨日的「上午强、午后弱」就是必须验证的模板 —— 高开后能否在 10:30 后维持住，比开盘幅度更重要</b></b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">④ 结构读数（金钻 / TOP10 / 板块技术 三个独立信号）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">① 金钻（<code>golden_diamond.json</code> · 4 只 · 全部「买入」）</b>：<b>中远海能</b>（sh600026）、<b>兖矿能源</b>（sh600188）、<b>中国海油</b>（sh600938）、<b>中国石油</b>（sh601857）。<b class="dk-main">⇒ 连续第二日「金钻池无一只科技股」，4 只全部落在能源 / 油运</b>。<b class="dk-caution">逐字口径：金钻为技术共振信号，须结合大盘环境与个股基本面，勿单一依赖。本页涉及个股均为「其他专家持股参考（非本人）」的客观读数，不构成买卖建议</b>。<br>
    <b class="dk-main">② TOP10（<code>top10_history.json 2026-11-12</code> · 全部「三线共振 EMA 完美」· <b>7 跌 3 涨</b>）</b>：风语筑 <b class="dk-dn">-4.92%</b> / 莱美药业 <b class="dk-dn">-0.42%</b> / 富瀚微 <b class="dk-dn">-3.12%</b> / 移远通信 <b class="dk-dn">-1.58%</b> / 日发精机 <b class="dk-dn">-3.58%</b> / 传智教育 <b class="dk-dn">-5.85%</b> / <b>工商银行 <span class="dk-up">+1.88%</span></b> / 冰山冷热 <b class="dk-dn">-2.93%</b> / 九阳股份 <b class="dk-up">+0.23%</b> / 飞亚达 <b class="dk-up">+5.09%</b>。<b class="dk-main">⇒ 情绪 14 的环境下，「评分高」不构成抗跌依据；唯一逆势的权重是工商银行（防守型）</b>。<br>
    <b class="dk-main">③ 板块技术（<code>sector_tech.json</code> · <code>data_date = 2026-11-12</code> · <b class="dk-caution">K 线源滞后 1 个交易日</b>）</b>：<b>L4 = 0 / L3 = 2 / L2 = 7 / L1 = 22</b>（同上一版）；<b class="dk-caution">L3 两席 = 银行（趋势向上 · 资金分位 100 · 反转首日）、农林牧渔（下跌反弹 · 资金分位 96.7）</b>；趋势分布 <b class="dk-risk">下跌破位 18 席 + 下跌反弹 12 席 = 30 / 31 席处于空头结构</b>，<b>仅 1 席为上升趋势</b>。<b class="dk-risk">⇒ 板块层面几无「趋势向上」的广度 —— 今日若高开，属指数层面的修复，不是结构层面的转好</b>。
  </div>
</div>

"""

# ══════════════════════ 1.1 ══════════════════════
S11 = """<!-- 1.1 当日 TOP10 -->""" + h(
 '1.1 · 当日 TOP10（最新交易日 <b>2026-11-12</b> · 总站首页综合评分，动态）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div id="drTblTop10" style="font-size:12.5px"><span style="color:var(--text-muted)">TOP10 自动加载中…</span></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:6px">
    <b class="dk-caution">本日结构特征（agent 补注，数据由上方表格自动加载）</b>：10 只全部为「三线共振 · EMA 完美」，评分 63 / 60 两档，<b>但 7 跌 3 涨</b> —— 唯一大幅上涨的是<b>飞亚达 +5.09%</b>，唯一逆势的权重股是<b>工商银行 +1.88%</b>。<b class="dk-main">⇒ 「评分」与「当日收益」的背离，是「情绪从 65 掉到 14」在选股结果上的投影</b>。<b class="dk-caution">今日观察口径：这 10 只若在 11/13 高开环境下仍跑不出超额，说明「评分体系」当前捕捉的是「昨日的强势」而非「明日的强度」，须以连续 3 日胜率复核，不因单日否定。TOP10 为当日收盘后按综合评分（信号数 × EMA 分位 × 强度）排序，非预测，不构成推荐</b>。
  </div>
</div>

"""

# ══════════════════════ 1.2 ══════════════════════
S12 = """<!-- 1.2 当日金钻 -->""" + h(
 '1.2 · 当日金钻 · 三重门控合并去重（最新交易日 <b>2026-11-12</b> · 动态）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div id="drTblDiamond" style="font-size:12.5px"><span style="color:var(--text-muted)">金钻自动加载中…</span></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:6px">
    <b class="dk-caution">本日结构特征（agent 补注）</b>：<b>4 只全部为「买入」档，且全部落在能源 / 油运</b>（中远海能 / 兖矿能源 / 中国海油 / 中国石油）。<b class="dk-main">⇒ 与「9 席资金净流入全为低估值防守型」+「银行 L3 趋势向上」构成三处同向读数：<b class="dk-caution">防守是本轮唯一有内部一致性的方向，但它同时说明风险偏好仍在低位</b></b>。<b class="dk-caution">口径：金钻为回调结束、趋势上穿高位后的技术买点信号，须结合大盘与个股基本面，不构成推荐；标的清单不代表任何持仓建议</b>。
  </div>
</div>

"""

# ══════════════════════ 2 · 亚太与商品利率 ══════════════════════
S2 = """<!-- 2 日韩股市与商品利率 -->""" + h(
 '2 · 亚太与商品利率（日韩 = <b class="dk-up">11/13 早盘〔09:45 KST · 非收盘〕</b> · 商品 = <b>11/13 早盘</b> · 美债 <b class="dk-caution">11/10 结算〔T+2 龄期〕</b> · 港股 11/12 收盘）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>品种</th><th>最新</th><th>涨跌幅</th><th>数据日 / 时点</th><th>读数</th></tr></thead><tbody>
    <tr><td><b>日经225</b></td><td>61,771.67</td><td><b class="dk-up">+1.57%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap"><b class="dk-up">高开高走</b>；日经期货早盘曾 +1.3%，指数与其同步</div></td></tr>
    <tr><td><b>韩国综合指数</b></td><td>5,474.68</td><td><b class="dk-up">+2.47%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap"><b class="dk-up">开盘 +2.05%，盘中涨幅一度扩大至 3%</b>；李在明「资本市场正常化 / 改革 KOSDAQ」表态为本土催化</div></td></tr>
    <tr><td><b>SK海力士</b></td><td>1,290,500</td><td><b class="dk-up">+2.91%</b></td><td>2026-11-13 09:45 KST</td><td><div class="dr-wrap"><b class="dk-up">存储母股转正</b>（11/12 收 -2.82% → 今日 +2.91%，两日摆幅 5.73pct）；<b class="dk-main">这是 11 月以来第一次「母股强于 A股 存储端」</b></div></td></tr>
    <tr><td><b>三星电子</b></td><td>213,500</td><td><b class="dk-up">+2.64%</b></td><td>2026-11-13 09:45 KST</td><td><div class="dr-wrap">11/12 收 +0.24% → 今日 +2.64%，<b>本土政策 + 存储反弹双驱动</b></div></td></tr>
    <tr><td><b>恒生指数</b></td><td>24,008.55</td><td><b class="dk-dn">-1.26%</b></td><td>2026-11-12 收盘</td><td><div class="dr-wrap">高开 0.47% 后单边走低，收在当日最低上方 65.8 点</div></td></tr>
    <tr><td><b>恒生科技</b></td><td>3,931.93</td><td><b class="dk-risk">-2.36%</b></td><td>2026-11-12 收盘</td><td><div class="dr-wrap">与创业板 -2.44% 同幅，<b>两岸科技端同步杀估值</b></div></td></tr>
    <tr><td><b>现货黄金</b></td><td>3,881.16</td><td><b class="dk-risk">-2.67%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap"><b class="dk-risk">连续第二日下跌并再破 3,890</b>，与本轮「实际利率上行」定价一致</div></td></tr>
    <tr><td><b>COMEX 黄金</b></td><td>3,881.89</td><td><b class="dk-risk">-2.96%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap">期货跌幅大于现货，<b class="dk-caution">投机盘继续撤离</b></div></td></tr>
    <tr><td><b>WTI 原油</b></td><td>87.42</td><td><b class="dk-up">+1.03%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap">较 11/12 的 86.67 继续上行，<b class="dk-up">风险资产中少数走强的一方</b></div></td></tr>
    <tr><td><b>布伦特原油</b></td><td>94.21</td><td><b class="dk-up">+1.57%</b></td><td>2026-11-13 早盘</td><td><div class="dr-wrap"><b class="dk-up">站上 94</b>，英国制裁「影子船队」的供给端扰动仍在</div></td></tr>
    <tr><td><b>10Y 美债</b></td><td>4.98%</td><td><b class="dk-neutral">—</b></td><td>2026-11-10</td><td><div class="dr-wrap"><b class="dk-caution">T+2 龄期</b>，距 5% 仅 2bp；<b class="dk-risk">不含 11/12 美元新高后的上行，不作为当日读数</b></div></td></tr>
    <tr><td><b>30Y 美债</b></td><td>5.35%</td><td><b class="dk-neutral">—</b></td><td>2026-11-10</td><td><div class="dr-wrap">同上，<b class="dk-caution">龄期 2 日</b></div></td></tr>
    <tr><td><b>人民币中间价</b></td><td>6.7174</td><td><b class="dk-neutral">—</b></td><td>2026-11-12</td><td><div class="dr-wrap">当日中间价，<b class="dk-caution">无前值可比，不做方向判断</b>；美元 19 个月新高下未明显走弱，属偏强信号</div></td></tr>
    <tr><td><b>VIX</b></td><td>18.70</td><td><b class="dk-caution">+6.92%</b></td><td><b>2026-11-12 结算</b></td><td><div class="dr-wrap"><b class="dk-up">已含 11/12 美股全天与 NVDA 事件</b>；<b class="dk-caution">仍低于 11/09 的 19.92，远低于恐慌阈值 25 → 期权市场未定价系统性风险</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-main">本段三条读法</b>：<b>① 今早亚太是「高开且守住」，不是「高开即回吐」</b> —— KOSPI 开盘 +2.05% 后盘中扩大至 +3%、海力士 +2.91%、三星 +2.64%，<b class="dk-up">截至 09:45 KST 未见回吐迹象</b>；<b class="dk-main">这与 11/10、11/12 两版「亚太开盘即见顶」的形态相反，是本版把方向由「偏空」上调为「中性」的直接依据之一</b>。<b>② 存储母股转正</b>：海力士今日 +2.91% 对上 11/12 的 -2.82%，<b class="dk-main">这条链的先行指标（母股）首次给出正向读数 —— 而 11/12 的失败恰是「母股不认、A股 硬跟」</b>；今日若 A股 存储端跟随，属「有母股背书」的跟涨，质量高于昨日。<b>③ 「金跌油涨」继续</b>：黄金 -2.67%、原油 +1.57%、美元 19 个月新高 —— <b class="dk-risk">市场定价的仍是「实际利率上行 + 通胀」，不是「避险消退」</b>。<b class="dk-main">⇒ 对 A股 的含义是双向的：高开可期（风险偏好修复），但高估值成长股缺乏「分母」支撑，反弹更可能发生在低估值 / 资源 / 防守端，而不是创业板</b>。
  </div>
</div>

"""

# ══════════════════════ 3 · 隔夜美股 ══════════════════════
S3 = """<!-- 3 隔夜美股复盘 -->""" + h(
 '3 · 隔夜美股复盘（<b class="dk-up">11/12 完整收盘〔昨夜 · 结算价〕</b> · 道 <b class="dk-dn">-0.36%</b> / 标普 <b class="dk-dn">-0.35%</b> / 纳 <b class="dk-dn">-0.39%</b> · 存储四线 <b class="dk-dn">-2.39%</b> / 光通信三线 <b class="dk-dn">-3.35%</b> · 🔴 <b class="dk-main">NVDA 开 -13.08% → 低 -14.36% → 收 -4.34%，日内反转 10.02pct</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 双日表（<code>market.json us_kline</code> · 前收 11/11 / 收盘 11/12 · 单位 = 美元）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>标的</th><th>前收（11/11）</th><th>收盘（11/12）</th><th>涨跌幅</th><th>读数</th></tr></thead><tbody>
    <tr><td><b>道琼斯</b></td><td>52,486.49</td><td>52,297.09</td><td><b class="dk-dn">-0.36%</b></td><td><div class="dr-wrap">三大指数中最抗跌，<b class="dk-caution">权重结构不含 AI 硬件</b></div></td></tr>
    <tr><td><b>标普500</b></td><td>7,619.38</td><td>7,592.40</td><td><b class="dk-dn">-0.35%</b></td><td><div class="dr-wrap">跌幅最小，<b>成分分散度吸收了单票冲击</b></div></td></tr>
    <tr><td><b>纳斯达克</b></td><td>25,466.19</td><td>25,366.09</td><td><b class="dk-dn">-0.39%</b></td><td><div class="dr-wrap"><b class="dk-main">跌幅结构 = 纳 &gt; 道 ≈ 标普，但三者差距仅 0.04pct → 「事件冲击」而非「风格杀」</b></div></td></tr>
    <tr><td><b class="dk-main">存储四线</b></td><td colspan="2"><b>MU 811.30 / SNDK 977.69 / WDC 313.31 / SKHY 142.25</b></td><td><b class="dk-dn">均值 -2.39%</b></td><td><div class="dr-wrap">MU <b class="dk-dn">-1.59%</b> · SNDK <b class="dk-dn">-4.11%</b> · WDC <b class="dk-dn">-0.67%</b> · SKHY <b class="dk-dn">-3.19%</b>；<b class="dk-caution">11/11 曾 +10.91%，两日净 +8.26% → 属「回吐一半」而非「全部归还」</b></div></td></tr>
    <tr><td><b class="dk-main">光通信三线</b></td><td colspan="2"><b>AAOI 55.86 / LITE 648.06 / COHR 234.51</b></td><td><b class="dk-dn">均值 -3.35%</b></td><td><div class="dr-wrap">AAOI <b class="dk-dn">-5.39%</b> · LITE <b class="dk-dn">-3.61%</b> · COHR <b class="dk-dn">-1.04%</b>；<b class="dk-caution">11/11 曾 +11.84%，两日净 +8.10%</b></div></td></tr>
    <tr><td><b>MRVL 美满</b></td><td>168.80</td><td>164.45</td><td><b class="dk-dn">-2.58%</b></td><td><div class="dr-wrap">定制 ASIC 端跌幅居中，<b>未出现单独的估值杀</b></div></td></tr>
    <tr><td><b class="dk-caution">NVDA 英伟达</b></td><td>173.73</td><td><b>166.19</b></td><td><b class="dk-risk">-4.34%</b></td><td><div class="dr-wrap"><b class="dk-main">开 151.01（-13.08%）→ 低 148.80（-14.36%）→ 高 167.14 → 收 166.19</b>，<b class="dk-up">自最低收窄 10.02pct、收盘贴近当日高点</b>；市值单日蒸发 1,820 亿美元</div></td></tr>
    <tr><td><b>TSLA 特斯拉</b></td><td>390.84</td><td>397.45</td><td><b class="dk-up">+1.69%</b></td><td><div class="dr-wrap"><b class="dk-up">与 AI 硬件无直接关联的大市值唯一红盘</b>，承接部分轮动资金</div></td></tr>
  </tbody></table></div>
  <div class="dr-tag" style="margin-top:10px">② 一夜之间的三段定价：从「-14.36%」到「-4.34%」</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">第一段（开盘，-13.08%）</b>：承接亚洲时段 NVDA 盘前 -11% 的定价，直接以 151.01 开盘，<b>低点 148.80 对应 -14.36%</b> —— <b class="dk-risk">这是「事件未知期」的极值，反映的是董事会遴选期的治理折价</b>。<br>
    <b class="dk-main">第二段（盘中，反抽）</b>：<b class="dk-up">博通 / AMD 逆势 +5%、费城半导体指数盘中转涨约 1%、思科 / 应用材料 / Cerebras 业绩超预期</b>，同时媒体口径出现「散户逆势疯狂抄底英伟达」—— <b class="dk-up">资金没有离开 AI 硬件，而是从「旗手」向「同链的其他标的」再分配</b>。<br>
    <b class="dk-main">第三段（收盘，-4.34%）</b>：收 166.19，<b>较最低点回升 11.7%、贴近当日高点 167.14</b>。<b class="dk-main">⇒ 这个收盘价是本版最重要的单一读数：它说明「CEO 辞职」这件事，市场用一天时间给出了「-4.34%」的定价，而不是「-11%」或「-14%」</b>。<br>
    <b class="dk-caution">同步的机构与制度动作（未来 1–2 周的二次发酵通道）</b>：<b>①</b> Truist 将 NVDA 评级下调、目标价腰斩；<b>②</b> 美参议院银行委员会传唤黄仁勋与卢特尼克就英伟达风波作证；<b>③</b> 临时 CEO 克雷斯计划下周三召开公司会议；<b>④</b> 公司称维持原定时间公布 Q3 财报。<b class="dk-risk">⇒ 三个时点（听证 / 公司会议 / 财报）在未来两周内密集落地，构成「利空未出尽」的结构 —— 这是本版不敢给「偏多」的关键原因之一</b>。<b class="dk-caution">反方证据同样存在：中信证券称「科技龙头管理层变动可能加剧短期波动，但系统性抛售压力或相对有限」；银河证券称「电子行业具备超跌反弹的基本面基础」；多家外资维持对中国半导体设备的买入（Jefferies）</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 关键判读：这是「单点事件被消化」，不是「AI 硬件趋势反转」</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">供给端（旗手）</b>：NVDA 的治理折价已由 -14.36% 收敛至 -4.34%，<b class="dk-caution">「旗手失位」从「未知事件」变成「已定价事件」</b>；<b>估值端（分母）</b>：<b class="dk-risk">未改善</b> —— 美元 19 个月新高、12 月加息 50bp 概率 15.3%、戴利「可能需要进一步加息」、黄金 -2.67% 至 3,881。<b class="dk-main">⇒ 两条作用力的方向不再一致：一条（旗手）已止血，一条（分母）仍在恶化 → <b class="dk-caution">对应 A股 = 情绪修复可期、估值扩张不可期</b>。<b class="dk-main">这也解释了为什么本版「方向中性、仓位上调一档、但明确不给偏多」：修复是「跌多了反弹」的性质，不是「新驱动出现」的性质</b>。
  </div>
</div>

"""

# ══════════════════════ 4 · 重点宏观 ══════════════════════
S4 = """<!-- 4 重点宏观 -->""" + h(
 '4 · 重点宏观（<b>日历轨为准</b> · 最新公布 = <b class="dk-caution">10 月 CPI 月率 0.4%（预期 0.3 · 前值 0.6）· 核心月率 0.3%（预期 0.2）〔11/10 · 龄期 3 日〕</b> + <b class="dk-up">10 月非农 16.5 万 / 失业率 4.1%〔11/06 · 龄期 7 日〕</b> + <b class="dk-caution">初请 20.0 万〔11/12 · 龄期 1 日〕</b> · <b class="dk-risk">CPI 同比 / 核心同比日历轨 value 仍为空，本档不以外推充数</b> · <b class="dk-main">今日事件（11/13）= 15:45 法国 10 月 CPI / 18:00 欧元区 Q3 GDP / 21:30 美国 10 月 PPI</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">① 美国（<code>daily_macro_latest.json us.calendar</code> · 主源 = 百度经济日历 · <code>as_of 2026-11-13 08:47</code>）</div>
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>指标</th><th>最新值</th><th>预期</th><th>前值</th><th>公布日</th><th>龄期</th><th>读数</th></tr></thead><tbody>
    <tr><td><b class="dk-caution">CPI 月率（季调 · 10 月）</b></td><td><b class="dk-caution">0.4%</b></td><td>0.3%</td><td>0.6%</td><td>2026-11-10</td><td><b class="dk-caution">3 日</b></td><td><div class="dr-wrap"><b>超预期 0.1pct</b>，但较 9 月 0.6% 回落 —— <b class="dk-caution">「方向对、节奏慢」</b></div></td></tr>
    <tr><td><b class="dk-caution">核心 CPI 月率（10 月）</b></td><td><b class="dk-caution">0.3%</b></td><td>0.2%</td><td>0.3%</td><td>2026-11-10</td><td><b class="dk-caution">3 日</b></td><td><div class="dr-wrap">超预期 0.1pct，<b class="dk-risk">与前值持平、未见回落</b></div></td></tr>
    <tr><td><b class="dk-risk">CPI 同比 / 核心同比（10 月）</b></td><td><b class="dk-risk">value 为空</b></td><td>—</td><td>3.7% / 2.6%（9 月）</td><td>2026-11-10</td><td class="dk-risk">3 日</td><td><div class="dr-wrap"><b class="dk-risk">日历轨仅回填月率，同比字段 <code>value</code> 仍为空 —— 本档不以「9 月同比」冒充 10 月，也不以新闻轨数字拼接，标为缺口</b></div></td></tr>
    <tr><td><b class="dk-up">非农（10 月）</b></td><td><b class="dk-up">+16.5 万</b></td><td>6.5 万</td><td>6.0 万</td><td>2026-11-06</td><td><b class="dk-up">7 日</b></td><td><div class="dr-wrap"><b class="dk-up">大幅超预期（2.5 倍）</b>，劳动力市场重新转紧</div></td></tr>
    <tr><td><b class="dk-up">失业率（10 月）</b></td><td><b class="dk-up">4.1%</b></td><td>4.2%</td><td>4.2%</td><td>2026-11-06</td><td><b class="dk-up">7 日</b></td><td><div class="dr-wrap">低于预期，<b>与非农同向（就业强）</b></div></td></tr>
    <tr><td><b class="dk-caution">初请失业金（至 11/07 周）</b></td><td><b class="dk-caution">20.0 万</b></td><td>19.5 万</td><td>18.9 万</td><td>2026-11-12</td><td><b class="dk-caution">1 日</b></td><td><div class="dr-wrap"><b class="dk-caution">已回填（上一版为空）</b>，高于预期 0.5 万、高于前值 1.1 万 → <b class="dk-caution">就业边际略转弱，与「非农强」形成小幅背离</b></div></td></tr>
    <tr><td><b>ADP 就业（周度 · 至 10/24 周）</b></td><td>+1.98 万</td><td>—</td><td>+1.68 万</td><td>2026-11-10</td><td>3 日</td><td><div class="dr-wrap">周度口径，<b>与前值同为净增</b></div></td></tr>
    <tr><td><b>核心 PCE（Q3 初值·年化）</b></td><td>2.5%</td><td>2.4%</td><td>3.3%</td><td>2026-10-29</td><td>15 日</td><td><div class="dr-wrap">超预期但<b class="dk-caution">较前值大幅回落（3.3 → 2.5）</b></div></td></tr>
    <tr><td><b>ISM 制造业（10 月）</b></td><td>55.5</td><td>54.6</td><td>54.5</td><td>2026-11-02</td><td>11 日</td><td><div class="dr-wrap">超预期，<b>扩张区间且加速</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:6px">
    <b class="dk-main">口径说明（本版改进）</b>：<b>①</b> 本版已把 10 月 CPI <b>月率</b>（0.4% / 核心 0.3%）从日历轨回填入表，<b class="dk-risk">但同比字段 <code>value</code> 仍为空，故不写同比数值</b> —— 上一版用「9 月 CPI 3.7% / 核心 2.6%〔龄期 29 日〕」作最新值，<b class="dk-caution">在本版会被读成「10 月同比」，属口径误导，已停用</b>；<b>②</b> 初请（11/12 公布）本版已回填 <b>20.0 万</b>，上一版标「待回填」，此处更正。<b class="dk-main">⇒ 结论：<b class="dk-risk">「核心通胀未见回落 + 就业仍强 + 初请边际转弱」的组合，指向「美联储没有降息空间、但也没有加速紧缩的充分理由」—— 这正是「分母端维持压制、但不进一步恶化」的宏观背景</b>，与本版「旗手止血、分母未愈」的判断同源</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">② 利率与汇率的最新读数（本版新增，直接对应分母端）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">美元触及 19 个月新高</b>（11/12 媒体口径，美联储加息预期升温）；<b>12 月加息 50bp 概率 15.3%</b>（CME 口径，11/13 06:17）；<b>旧金山联储戴利：可能需要进一步加息以抑制通胀</b>；<b class="dk-risk">现货黄金 -2.67% 至 3,881.16、COMEX -2.96%</b>；<b class="dk-up">WTI +1.03% 至 87.42 / 布伦特 +1.57% 至 94.21</b>。<b class="dk-main">⇒ 「金跌 + 油涨 + 美元强」三者同向，是本轮最稳定的宏观组合，其经济含义是<b class="dk-risk">实际利率上行</b>：<b>这对高久期成长股（创业板 / 科创）是持续压制，对资源 / 能源是相对受益</b> —— 与本页 5.5 段「能源是唯一正向链」、7.4 段「防守端优先」互为印证。
  </div>
  <div class="dr-tag" style="margin-top:10px">③ 今日（11/13）事件日历（<code>daily_macro_latest</code> 新闻轨 05:52 · 东财全球）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b>15:45 法国 10 月 CPI</b> · <b>18:00 欧元区第三季度 GDP</b> · <b class="dk-main">21:30 美国 10 月 PPI</b> · <b>23:30 美国上周 EIA 天然气库存</b> · <b>次日 02:00 美国石油钻井总数</b>。<b class="dk-main">⇒ 对 A股 而言，<b class="dk-risk">21:30 的美国 10 月 PPI 落在收盘之后，属「无法在盘中定价」的周末隔夜风险</b> —— 这是 7.4 段把周五仓位上限设在 35% 的直接理由；<b class="dk-caution">日内（15:45 / 18:00）的欧洲数据对 A股 影响有限，主要作用于汇率与外资风险偏好</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">④ 中国（<code>daily_macro_latest.json china</code> · 最新可得）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b>10 月 CPI 同比 <span class="dk-up">+0.7%</span></b>（环比 0.0%，累计 100.9）· <b>10 月制造业 PMI <span class="dk-risk">49.3</span> / 非制造业 <span class="dk-risk">49.7</span></b>（<b class="dk-risk">双双低于 50</b>）· <b>前三季度 GDP 同比 <span class="dk-caution">+4.6%</span></b>（绝对值 1,071,071 亿元）· <b>LPR（2026-10-20）1Y <span class="dk-caution">3.0%</span> / 5Y <span class="dk-caution">3.5%</span></b>。<b class="dk-main">⇒ 国内仍是「低通胀 + 弱景气 + 宽货币」，与美国「核心通胀黏性 + 就业强 + 紧货币」相反 —— <b class="dk-caution">外部收紧对 A股 的传导通道主要在「汇率 + 风险偏好」，而非国内利率端；今日人民币中间价 6.7174 未明显走弱，故通道压力可控</b></b>。
  </div>
</div>

"""

# ══════════════════════ 5 · 重点科技 ══════════════════════
S5 = """<!-- 5 重点科技 -->""" + h(
 '5 · 重点科技（对照 <b class="dk-up">美股 11/12 完整收盘〔NVDA 收窄至 -4.34%〕</b> × <b class="dk-dn">A股 11/12 全链杀跌</b> × <b class="dk-up">日韩 11/13 早盘〔海力士 +2.91%〕</b> · 外部锚 = 「旗手止血、分母未愈」）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-caution">① 光模块 / CPO：外盘跌幅收窄，但 A股 资金仍未回头</b>。A股 通信主力 <b class="dk-risk">-73.03 亿</b>（前一日 <b class="dk-up">+133.83 亿</b>），四象限 <b class="dk-risk">双冷 D</b>（语料仅 4 条）；美股 11/12 三线 <b class="dk-dn">-3.35%</b>（AAOI -5.39 / LITE -3.61 / COHR -1.04），<b class="dk-caution">但两日净仍 +8.10%</b>；中际旭创拟 5,000 万元参投产业基金（06:19）为产业级增量。<b class="dk-main">⇒ 判断修正：<b class="dk-caution">由「退潮确认」下调为「退潮未结束、但外盘已止跌」</b> —— 昨日 -73.03 亿的流出并未被今日外盘证明为「趋势性撤离」，更接近「跟随 A股 大盘的被动减仓」。<b>今日判据唯一化：通信主力单日能否收窄至 -30 亿以内</b>；若仍超 -50 亿，则退潮延续</b>。<br>
    <b class="dk-main">② 存储 / 半导体：本版最重要的边际变化 —— 母股转正</b>。A股 电子 <b class="dk-dn">-79.05 亿</b>、四象限 <b class="dk-caution">背离 B</b>（语料 65 条 / 日均 32.5，全场最热）；美股 11/12 四线 <b class="dk-dn">-2.39%</b>（两日净 +8.26%）；<b class="dk-up">韩股海力士今早 1,290,500（+2.91%）、三星 213,500（+2.64%）</b>。<b class="dk-main">⇒ 11/12 的失败模式是「母股不认、A股 硬跟」；今日母股首次给出正向读数 → <b class="dk-up">存储端今日的跟涨属「有母股背书」，质量高于昨日</b>。但注意两点：<b class="dk-caution">① 电子语料 65 条里绝大多数是「英伟达 / 芯片股」单一事件，热度含水分；② 电子是背离 B（语料热、资金撤），反弹初期最容易出现「高开后被昨日套牢盘压制」</b></b>。<br>
    <b class="dk-caution">③ AI 算力 / 服务器：事件已定价，但制度性时点未落地</b>。NVDA 11/12 收 <b>166.19（-4.34%）</b>，自盘中最低 148.80 回升 <b>11.7%</b>；<b class="dk-up">博通 / AMD +5%、费半盘中转涨、思科 / 应用材料 / Cerebras 业绩超预期</b>；<b class="dk-risk">但 Truist 下调评级、参议院传唤听证、临时 CEO 下周三召开公司会议、Q3 财报待发</b>。<b class="dk-main">⇒ 对算力链的正确读法：<b class="dk-caution">「杀估值的第一波」已过，「制度性不确定」仍在 —— 因此可以修复估值，但不能给估值溢价</b>。今日若算力链高开，看能否在 10:30 后维持，而不是看开盘幅度</b>。<br>
    <b class="dk-caution">④ 国产算力 / 信创：外部旗手失位，是本链最直接受益的叙事</b>。今日语料：<b class="dk-up">「A股半导体产业链热度抬升 国产算力链配置价值凸显」（07:21）</b>、<b>Jefferies 维持对中国半导体生产设备的买入（08:46）</b>、<b>路透 / 参议院风波推升地缘风险</b>；产业侧：中科曙光 × 建行（11/12 21:19）、复旦微电回购、联瑞新材 10 亿封装粉体。<b class="dk-main">⇒ 本版把它从「观察」上调为「<b class="dk-caution">相对占优候选</b>」：<b>逻辑是「外部旗手失位 → 国产替代叙事获得催化」，但资金证据仍是负的（计算机 -31.42 亿、背离 B）→ 只给观察仓 ≤5%，需「计算机主力转正 ≥5 亿」才升级</b></b>。<br>
    <b class="dk-risk">⑤ 机器人 / 具身智能：资金端仍是三条里最差的</b>。机械设备 <b class="dk-risk">-66.99 亿</b>、四象限 <b class="dk-risk">双冷 D</b>（语料 4 条）、板块技术 <b>L2</b>（趋势 = 反弹，中期未反转）。<b class="dk-caution">今日语料出现反向声音：「hf大制造：不惧回调，坚定看好物理AI&人形机器人」</b>。<b class="dk-main">⇒ 判断不变：<b class="dk-risk">语料看多、资金撤离、技术未反转 —— 三者仍不匹配，维持回避，不因单条卖方观点改变</b></b>。<br>
    <b class="dk-caution">⑥ 传媒 / AI 应用：连续第四个版本「叙事最密、资金最疏」，但今日出现单一催化剂</b>。传媒 <b class="dk-dn">-37.76 亿</b>（双冷 D）、计算机 <b class="dk-dn">-31.42 亿</b>（背离 B）；<b>今日 08:37「火山引擎发布 Seedance 2.5 flash，AI 影视产业有望进一步降本增效」</b>、<b>08:38「国内首个口服 GLP-1 类减肥药获批上市」</b>。<b class="dk-main">⇒ 处理方式：<b class="dk-risk">仍按「结构性不参与」执行；但把「AI 影视降本」记为「若有色 / 传媒板块出现资金转正，则优先看这条支线」的触发条件</b> —— 事件驱动型催化剂在「资金未转正」时不构成买入理由，只构成观察顺位的上调</b>。
  </div>
</div>

"""

# ══════════════════════ 5.5 · 产业链 ══════════════════════
S55 = """<!-- 5.5 产业链 / 景气度 -->""" + h(
 '5.5 · 产业链 / 景气度评估（六条链 · 每条含 <b>11/13 观察要点</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px"><table class="dr-tbl"><thead><tr><th>产业链</th><th>最新读数（A股 11/12 · 美股 11/12 收盘 · 日韩 11/13 早盘）</th><th>景气度定性</th><th>11/13 观察要点</th></tr></thead><tbody>
    <tr><td><b class="dk-caution">光模块 / CPO</b></td><td><div class="dr-wrap">A股：通信 <span class="dk-risk">-73.03 亿</span>（前一日 <span class="dk-up">+133.83 亿</span>）· 四象限<b class="dk-risk">双冷 D</b>（语料 4 条）｜美股：11/12 三线 <span class="dk-dn">-3.35%</span>（两日净 +8.10%）</div></td><td><div class="dr-wrap"><b class="dk-caution">退潮未结束 · 外盘已止跌</b>：流出更像「被动跟随」而非「趋势撤离」</div></td><td><div class="dr-wrap"><b>看一件事</b>：通信主力能否收窄至 <b>-30 亿以内</b>；<b class="dk-risk">仍超 -50 亿 = 退潮延续</b></div></td></tr>
    <tr><td><b class="dk-caution">存储 / 半导体</b></td><td><div class="dr-wrap">A股 电子 <span class="dk-risk">-79.05 亿</span> · 背离 B（语料 65 条）｜美股 11/12 四线 <span class="dk-dn">-2.39%</span>（两日净 +8.26%）｜<span class="dk-up">韩股海力士 11/13 早盘 +2.91%、三星 +2.64%</span></div></td><td><div class="dr-wrap"><b class="dk-up">母股转正 · 跟涨质量改善</b>：由「母股不认」变为「母股先行」</div></td><td><div class="dr-wrap"><b>看两件事</b>：① 电子主力能否由 -79 亿收窄至 <b>-40 亿以内</b>；② <b class="dk-caution">高开后 10:30 是否回吐</b>（昨日套牢盘压力）</div></td></tr>
    <tr><td><b class="dk-caution">AI 算力 / 服务器</b></td><td><div class="dr-wrap">NVDA 11/12 收 <span class="dk-dn">166.19（-4.34%）</span>，自最低 <span class="dk-up">回升 11.7%</span>；博通 / AMD <span class="dk-up">+5%</span>、费半盘中转涨；A股 计算机 <span class="dk-risk">-31.42 亿</span></div></td><td><div class="dr-wrap"><b class="dk-caution">第一波杀估值已过 · 制度性时点未落地</b></div></td><td><div class="dr-wrap"><b>看开盘缺口与承接</b>：算力链高开 <b>&gt;+2%</b> 且 10:30 前不回落 = 事件已定价；<b class="dk-risk">高开后快速翻绿 = 昨日套牢盘主导</b></div></td></tr>
    <tr><td><b class="dk-caution">国产算力 / 信创</b></td><td><div class="dr-wrap">语料催化：国产算力链配置价值凸显（07:21）· Jefferies 维持中国半导体设备买入（08:46）｜产业：中科曙光 × 建行、复旦微电回购、联瑞新材 10 亿｜<b class="dk-risk">资金：计算机 -31.42 亿、背离 B</b></div></td><td><div class="dr-wrap"><b class="dk-caution">叙事获外部催化 · 资金未跟进</b>（本版由「观察」上调为「相对占优候选」）</div></td><td><div class="dr-wrap"><b>看资金是否转正</b>：计算机主力单日 <b>≥+5 亿</b>才算叙事被采纳；<b class="dk-caution">否则只作抗跌候选，仓位 ≤5%</b></div></td></tr>
    <tr><td><b class="dk-up">能源 / 油运</b></td><td><div class="dr-wrap">石油石化 <span class="dk-up">+0.16 亿</span>（暗线 C，语料 3 条）｜WTI <span class="dk-up">87.42（+1.03%）</span> / 布伦特 <span class="dk-up">94.21（+1.57%）</span>；<b class="dk-up">金钻 4 只全部为能源 / 油运</b></div></td><td><div class="dr-wrap"><b class="dk-up">唯一「三个独立信号同向」的链</b>：板块资金正 + 金钻集群 + 油价上行</div></td><td><div class="dr-wrap"><b>看资金能否过 5 亿</b>：<b class="dk-caution">当前 +0.16 亿的量级不足以支撑「主线」，只能算「避风位」</b>；布伦特站上 95 则上调</div></td></tr>
    <tr><td><b class="dk-caution">医药 / 创新药</b></td><td><div class="dr-wrap">医药生物 <span class="dk-up">+2.52 亿</span>（暗线 C，语料 3 条）｜今日语料：<b>口服 GLP-1 类减肥药获批上市（08:38）</b>｜美股医疗 10 只（11/12）见下段映射块</div></td><td><div class="dr-wrap"><b class="dk-caution">资金底第 2 日 · 事件催化出现</b>：单日 → 连续两日观察中，中期仍「下跌反弹」</div></td><td><div class="dr-wrap"><b>判据</b>：需连续 2 日为正且累计 ≥5 亿；<b class="dk-caution">今日 GLP-1 获批是首个事件级催化，看减肥药链能否带动板块资金转正</b></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-main">本段结论（一句）</b>：六条链中 <b class="dk-caution">2 条边际改善（存储「母股转正」/ 国产算力「叙事获外部催化」）</b>、<b class="dk-caution">2 条维持观察（光模块 / 医药）</b>、<b class="dk-up">1 条唯一正向（能源）</b>、<b class="dk-risk">1 条维持回避（机器人 —— 部分替代传媒的位置）</b>。<b class="dk-main">⇒ 与上一版最大的不同：<b class="dk-caution">上一版是「六条链全线转差、只剩能源」，本版首次出现「两条边际改善」，且改善的原因都来自外部（母股 / 外资观点），不是内部资金</b>。<b class="dk-risk">因此这类改善的正确用法是「降低回避强度」，而不是「提高配置强度」—— 因为六条链中仍有五条同属「成长 / 长久期」，在「实际利率上行」的环境里它们共享同一个风险因子，换股不降低风险，只有降仓降低风险</b>。
  </div>
</div>

"""

# ══════════════════════ 6 · 新闻整合（标题+结构说明） ══════════════════════
S6 = """<!-- 6 新闻整合 + 7.1 -->""" + h(
 '6 · 新闻整合（公开源自动刷新 · 本版实到：<b>11/13 08:47 抓取 287 条</b> · 覆盖 <b class="dk-caution">11/13 单日 00:00–08:47（盘前增量，A股 交易时段尚未开始）</b> · 标签 科技 73 / 宏观 44 / 政策 33 / 产业 26 / 美股映射 3 / 持仓 1）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div id="drNewsPool" style="font-size:12.5px"><span style="color:var(--text-muted)">新闻池自动加载中…</span></div>
  <div class="dr-tag" style="margin-top:10px">本版抓取结构（<code>daily_news_latest.json</code>）</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">① 时点分布（本版为盘前档，覆盖 00:00–08:47）</b>：00 时 <b>13</b> / 01 时 10 / 02 时 16 / 03 时 11 / 04 时 14 / 05 时 21 / 06 时 <b>33</b> / 07 时 <b>76</b> / 08 时 <b>93</b>（合计 287）。<b class="dk-main">⇒ 07–08 时合计 169 条（占 58.9%），说明「盘前 2 小时」是本日信息密度最高的窗口 —— 与昨日「21 时 111 条（盘后）」正好互补</b>。<b class="dk-caution">口径提醒：盘前档的新闻池只覆盖到 08:47，<b>09:15 集合竞价至 09:30 开盘之间的信息不在池内</b>；A股 交易时段（09:30–15:00）的盘中事件须等收盘档补齐</b>。<br>
    <b class="dk-caution">② 源分布</b>：东财全球 <b>200</b> / 富途全球 <b>48</b> / 新浪全球 <b>20</b> / 同花顺全球 <b>13</b> / 财经早餐 <b>6</b>。<b class="dk-caution">单一源（东财）占 69.7%，跨源交叉验证能力仍弱；本档对「黄仁勋辞职后续」类重大事件已用 4 源（东财 / 富途 / 新浪 / 同花顺）× 多时点互证</b>。<br>
    <b class="dk-caution">③ 持仓标签 = 1 条（且为误标）</b>：唯一带「持仓」标签的是 07:09「『超量子』湍流现象首获观测」，<b class="dk-caution">与持仓股无关，属自动打标偏差</b>。<b class="dk-risk">本日 7 只持仓股（剑桥科技 / 永鼎股份 / 华工科技 / 长鑫科技 / 永杉锂业 / 昊华科技 / ST万邦）在盘前新闻池中均无独立事件</b>。<b class="dk-main">⇒ 全部读数为客观技术 / 资金数据，标注「其他专家持股参考（非本人）」，不给加减仓建议</b>。<br>
    <b class="dk-main">④ 本日四条高信息量语料（按对 11/13 的影响排序）</b>：<b>a.</b> 05:01 / 06:23 <b>「纳指收跌 0.4%、英伟达跌超 4%、博通 AMD 涨超 5%」「英伟达单日市值蒸发 1,820 亿美元」</b>（隔夜定价的最终版本，覆盖了昨夜盘前的 -11%）；<b>b.</b> 07:28–08:28 <b>「黄仁勋辞职，临时接任人曝光；特朗普建议库克接替；马斯克：招揽黄仁勋将是我的荣幸」+「美参议院银行委员会要求黄仁勋出席听证会」</b>（治理事件的制度性发酵）；<b>c.</b> 08:01 / 08:13 <b>「日韩股市集体高开，KOSPI 开盘 +2.05%」「韩国综指涨幅扩大至 3%」+ 李在明市场改革表态</b>（今早亚太的正向映射）；<b>d.</b> 08:36 <b>「AI 需求持续爆发！美国半导体设备龙头营收、盈利、业绩指引全面超预期」</b>（硬件链的基本面反证，与「旗手失位」形成对冲）。<br>
    <b class="dk-caution">⑤ 投喂语料状态</b>：<code>feed/archive/2026-11-13/_index.json</code> 为 <b>feed_count = 0</b>；窗口 <code>display_days = ['2026-11-12','2026-11-13']</code>，<b>两日均为 0 件</b>（11-11 批次 <code>F20261111-001</code> 为清单级、正文不可得，且在窗口之外）。<b class="dk-main">⇒ 本页全部内容基于公开新闻池 + 行情 / 资金接口 + 自有信号产物，<b>不含任何投喂正文</b>；研报流仅在本机统计判读（121 条 / 18.36 万字，<b>原文不入仓库、不粘贴正文、不外传</b>）</b>。
  </div>
</div>

"""

# ══════════════════════ 7.1 · K3 产业信号验证 ══════════════════════
S71 = h(
 '7.1 · K3 产业信号验证（<b class="dk-dn">A股 11/12 完整收盘</b> + <b class="dk-up">美股 11/12 完整收盘〔昨夜〕</b> + <b class="dk-up">日韩 11/13 早盘</b> · 8 条主题 · 结论句按语义上色）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-scroll" style="font-size:12.5px">
  <div class="k3c-legend">结论色标：<i class="l-go">可执行·相对占优</i><i class="l-cond">有条件·待确认</i><i class="l-risk">风险·回避</i><i class="l-verify">待验证变量·方法论</i></div>
  <table class="dr-tbl"><thead><tr><th>主题</th><th>验证</th><th>内容</th></tr></thead><tbody>
    <tr><td><b class="dk-caution">存储 / 半导体</b></td><td><div class="dr-wrap"><b class="dk-caution">边际改善</b>：母股由 -2.82% 转 +2.91%</div></td><td><div class="dr-wrap">美股 11/12 四线 <span class="dk-dn">-2.39%</span>（MU -1.59 / SNDK -4.11 / WDC -0.67 / SKHY -3.19；两日净 +8.26%）；<b class="dk-up">韩股海力士 11/13 早盘 1,290,500（+2.91%）、三星 213,500（+2.64%）</b>；A股 电子 <span class="dk-risk">-79.05 亿</span>、背离 B（语料 65 条）。<span class="k3c k3c-cond"><b>母股首次背书 → 跟涨质量改善；但电子资金未转正 + 昨日套牢盘，高开后 10:30 的承接是唯一判据</b></span></div></td></tr>
    <tr><td><b class="dk-caution">光模块 / CPO</b></td><td><div class="dr-wrap"><b class="dk-caution">退潮未结束 · 外盘已止跌</b></div></td><td><div class="dr-wrap">通信主力 <span class="dk-risk">-73.03 亿</span>（前一日 <span class="dk-up">+133.83 亿</span>）· 双冷 D（语料 4 条）· 美股三线 <span class="dk-dn">-3.35%</span>（两日净 +8.10%）· 中际旭创 5,000 万参投产业基金。<span class="k3c k3c-cond"><b>由「退潮确认」下调为「退潮未结束」，判据唯一化：通信主力收窄至 -30 亿以内方可视为止跌</b></span></div></td></tr>
    <tr><td><b class="dk-caution">AI 算力 / 服务器</b></td><td><div class="dr-wrap"><b class="dk-caution">事件已定价 · 制度时点未落地</b></div></td><td><div class="dr-wrap">NVDA 11/12 收 <span class="dk-dn">166.19（-4.34%）</span>，自低 148.80 <span class="dk-up">回升 11.7%</span>；博通 / AMD <span class="dk-up">+5%</span>、费半盘中转涨、思科 / 应材 / Cerebras 超预期；<b class="dk-risk">Truist 下调、参议院听证、下周三公司会议、Q3 财报待发</b>。<span class="k3c k3c-cond"><b>杀估值第一波已过、制度性不确定仍在 → 可修复估值，不可给溢价</b></span></div></td></tr>
    <tr><td><b class="dk-caution">国产算力 / 信创</b></td><td><div class="dr-wrap"><b class="dk-caution">叙事获外部催化 · 资金未跟进</b></div></td><td><div class="dr-wrap">「A股半导体产业链热度抬升 国产算力链配置价值凸显」（07:21）· Jefferies 维持中国半导体设备买入（08:46）· 中科曙光 × 建行 · 复旦微电回购 · 联瑞新材 10 亿；<b class="dk-risk">但计算机主力 -31.42 亿、背离 B</b>。<span class="k3c k3c-cond"><b>本版由「观察」上调为「相对占优候选」，需计算机主力转正 ≥5 亿才升级，仓位 ≤5%</b></span></div></td></tr>
    <tr><td><b class="dk-up">能源 / 油运</b></td><td><div class="dr-wrap"><b class="dk-up">三信号同向</b>：资金正 + 金钻集群 + 油价上行</div></td><td><div class="dr-wrap">石油石化 <span class="dk-up">+0.16 亿</span>（暗线 C，语料 3 条）· WTI <span class="dk-up">87.42（+1.03%）</span> / 布伦特 <span class="dk-up">94.21（+1.57%）</span> · <b class="dk-up">金钻 4 只全为能源 / 油运</b>。<span class="k3c k3c-go"><b>唯一的通胀受益 + 现金流避风位；但量级仅 0.16 亿，只给观察位不给配置位</b></span></div></td></tr>
    <tr><td><b class="dk-up">银行 / 大金融</b></td><td><div class="dr-wrap"><b class="dk-up">逆势资金第一 · 板块技术唯一上行</b></div></td><td><div class="dr-wrap">银行主力 <span class="dk-up">+7.46 亿</span>（全市场第一，分位 100 · 反转首日）· 暗线 C（语料 12 条）· <b class="dk-up">sector_tech L3 且趋势 = 上升（31 席中唯一）</b>；TOP10 中工商银行 <span class="dk-up">+1.88%</span>。<span class="k3c k3c-go"><b>防守资金的第一落点；但今日若大盘高开，其「相对收益」会下降 —— 它是防守票，不是进攻票</b></span></div></td></tr>
    <tr><td><b class="dk-caution">医药 / 创新药</b></td><td><div class="dr-wrap"><b class="dk-caution">资金底第 2 日 · 出现事件催化</b></div></td><td><div class="dr-wrap">医药生物 <span class="dk-up">+2.52 亿</span>（暗线 C，语料 3 条）· 板块技术 L2 / 下跌反弹 · <b>今日 08:38「国内首个口服 GLP-1 类减肥药获批上市」</b>。<span class="k3c k3c-cond"><b>需连续 2 日为正且累计 ≥5 亿；GLP-1 获批是首个事件级催化，看能否带动板块资金转正</b></span></div></td></tr>
    <tr><td><b class="dk-risk">机器人 / 传媒</b></td><td><div class="dr-wrap"><b class="dk-risk">资金撤离 · 双冷 D · 技术未反转</b></div></td><td><div class="dr-wrap">机械设备 <span class="dk-risk">-66.99 亿</span>（双冷 D，语料 4 条）、传媒 <span class="dk-risk">-37.76 亿</span>（双冷 D）；今日语料出现反向声音（hf大制造「坚定看好物理AI&人形机器人」）与事件催化（火山引擎 Seedance 2.5 flash）。<span class="k3c k3c-risk"><b>语料看多、资金撤离、技术未反转 —— 三者不匹配，维持回避；催化剂只上调观察顺位，不构成买入理由</b></span></div></td></tr>
  </tbody></table></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.62;margin-top:8px">
    <b class="dk-main">本段结论</b>：8 条主题中 <b class="dk-up">2 条正向（能源 / 银行，均为防守型）</b>、<b class="dk-caution">5 条待确认（存储 / 光模块 / 算力 / 国产算力 / 医药）</b>、<b class="dk-risk">1 条回避（机器人 · 传媒）</b>。<b class="dk-main">⇒ 与上一版「2 正 + 2 待 + 4 负」相比，本版的实质变化是<b class="dk-caution">「负面席位由 4 条降至 1 条」，其中存储、光模块、算力三条从「负面」上调为「待确认」</b> —— <b class="dk-risk">但必须说清：这三条的上调依据全部来自外部（美股收盘 / 母股 / 卖方观点），A股 内部资金一条都没有转正</b>。<b class="dk-main">⇒ 因此本版的正确姿势是「把回避的力度调低（仓位上修一档），而不是把进攻的力度调高（不给偏多）」</b>。
  </div>
</div>

"""

# ══════════════════════ 7.3 + 7.4 ══════════════════════
S73 = """<!-- 7.3 次日开盘指引 -->""" + h(
 '7.3 · K3 开盘指引（<b>11/13（周五）</b> · 基于 <b class="dk-dn">11/12 完整收盘事实</b> + <b class="dk-up">美股 11/12 完整收盘〔昨夜〕</b> + <b class="dk-up">日韩 11/13 早盘</b> · 情绪 <b class="dk-risk">14 恐慌下跌</b> / 涨跌比 <b class="dk-risk">0.19</b> / 涨停 <b>41</b> / <b>本版四象限 0 / 2 / 9 / 20</b> / 外部锚 <b class="dk-caution">旗手止血（NVDA -4.34%）+ 分母未愈（黄金 -2.67% / 美元 19 个月新高）</b> · 周五特征：<b class="dk-caution">21:30 美国 10 月 PPI 落在收盘后，周末隔夜风险不可对冲</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">① 竞价定档（09:15–09:25）</b>：<b class="dk-caution">基准情形 = 高开 +0.3%～+0.8%（3,667–3,685）</b>，概率 <b>45%</b>；<b class="dk-caution">高开超 +1.0%（&gt;3,692）= 隔夜修复被放大定价，概率 30%</b>，此档最需防「高开兑现」；<b class="dk-risk">平开或高开小于 +0.3%（&lt;3,667）= 外部反弹未被采纳，概率 25%</b>，按弱势处理。依据：美股三大指数 -0.35%～-0.39%、纳指期货早盘 +0.3%、日韩高开 2% 以上、海力士 +2.91%。<br>
    <b class="dk-main">② 09:30–10:30 定性窗口（本版核心判据）</b>：<b>看 <span class="dk-main">3,672.71（MA20）</span> 能否在 10:30 前站住</b>。<b class="dk-caution">站住 = 外部修复被采纳，可持 35%；站不住 = 高开回吐，压回 25%</b>。第二判据：<b class="dk-risk">昨日「上午强、午后弱」的模板是否重演</b> —— 若 10:30 后指数开始单边回落且无有效反抽，即视为派发延续，无论开盘多高都不加仓。<br>
    <b class="dk-main">③ 全天关键时点</b>：<b>10:30</b> 通信 / 电子主力实时估算（<b class="dk-caution">通信收窄至 -30 亿内、电子收窄至 -40 亿内 = 资金确认转向；否则视为「被动跟涨」</b>）；<b>13:30–14:00</b> <b class="dk-caution">周五效应窗口，减仓压力通常集中于此</b>；<b>14:30</b> 看宽基 ETF 是否由负转正（昨日六只合计 -23.97 亿，<b class="dk-caution">若转正 ≥10 亿可视为护盘信号</b>）。<br>
    <b class="dk-main">④ 三条防线与两道压力</b>：<b class="dk-risk">3,647.44</b>（11/12 低点 · 破位线）→ <b class="dk-caution">3,653.14</b>（MA10）→ <b>3,655.83</b>（11/12 收盘 · 平盘线）；<b>上方</b>：<b class="dk-main">3,672.71</b>（MA20 · 第一道真压力）→ <b class="dk-risk">3,699.58 / 3,700</b>（11/12 高 · 双顶，不破不谈反转）。<br>
    <b class="dk-main">⑤ 周五特有约束</b>：<b class="dk-caution">今日 21:30 美国 10 月 PPI 与次日 02:00 石油钻井数据均落在 A股 收盘之后；叠加 NVDA 听证（未来两周）与 Q3 财报，构成「无法在盘中定价」的周末隔夜风险</b>。<b class="dk-main">⇒ 因此即便今日盘中走强，也不建议把仓位推至 35% 以上；周五的正确动作是「留出能过周末的仓位」，而不是「把反弹做满」</b>。
  </div>
</div>

<!-- 7.4 操作预案 -->""" + h(
 '7.4 · 操作预案（盘前版 · agent 详细版 · 面向 <b>11/13（周五）</b> · 依据 <b class="dk-dn">A股 11/12 完整收盘</b> + <b class="dk-up">美股 11/12 完整收盘〔昨夜〕</b> + <b class="dk-up">日韩 11/13 早盘</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-tag">一、大势预判</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">中性 · 中高置信度 · 高开回吐压力 · 仓位 25%–35% · 风险 中高</b>。<b class="dk-caution">核心矛盾已从「外部双杀」变为「外部单杀 + 内部派发」</b>：旗手端（NVDA 治理）已由 -14.36% 收敛至 -4.34%、半导体设备业绩超预期，<b>但分母端（美元 19 个月新高、12 月加息 50bp 概率 15.3%、黄金 -2.67%）未改善</b>；同时 A股 昨日以「放量 19,320.8 亿 + 收在最低 + 情绪 14」完成派发。<b class="dk-main">⇒ 今日的性质是<b class="dk-caution">「超跌修复能否成立」的验证日，而不是「趋势反转」的起点</b>。<b>判据唯一化：<b>3,672.71（MA20）是多空分水岭 —— 站上为修复，站不上为高开回吐</b></b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">二、主线策略</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">① 防守端优先（唯一可加的方向，与上一版一致）</b>：<b class="dk-up">能源 / 油运</b>（石油石化 +0.16 亿、金钻 4 只集群、布伦特 94.21）与 <b class="dk-up">银行</b>（+7.46 亿，全市场第一，L3 唯一上行）。<b class="dk-caution">但两者都只给「观察位 + 小幅配置」—— 量级（0.16 / 7.46 亿）与昨日 525 亿的净流出相比太小，属「避风」而非「进攻」</b>。<br>
    <b class="dk-main">② 存储链：由「回避」改为「有条件参与」</b>：<b class="dk-caution">依据是母股转正（海力士 +2.91%、三星 +2.64%）+ 美股存储四线两日净 +8.26%</b>。<b class="dk-risk">但必须满足两个条件：① 电子主力当日收窄至 -40 亿以内；② 高开后 10:30 不回吐</b>；条件不满足则不参与，<b>不因「外盘涨了」就买</b>。<br>
    <b class="dk-main">③ 国产算力作为「相对占优候选」跟踪</b>：中科曙光 × 建行、复旦微电回购、Jefferies 维持买入、语料「国产算力链配置价值凸显」。<b class="dk-caution">升级条件 = 计算机主力单日 ≥+5 亿；当前为 -31.42 亿，不成立 → 观察仓 ≤5%</b>。<br>
    <b class="dk-main">④ 医药作为「资金底候选」跟踪</b>：医药生物 <b class="dk-up">+2.52 亿</b>（第 2 日为正），<b>今日 GLP-1 口服减肥药获批为首个事件级催化</b>。<b class="dk-caution">需连续 2 日为正且累计 ≥5 亿才升级为可配置</b>。<br>
    <b class="dk-main">⑤ 不加杠杆、不追高开</b>：<b class="dk-risk">情绪 14 的环境下，高开是最容易被用来出货的形态；昨日已完整演示「上午强、午后杀」，今日若重演，追高者即接盘方</b>。
  </div>
  <div class="dr-tag" style="margin-top:10px">三、回避清单</div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-risk">① 机器人 / 具身智能</b>：机械设备 <b>-66.99 亿</b>、双冷 D、技术 L2（反弹），<b>语料看多 / 资金撤离 / 技术未反转三者不匹配，维持回避</b>。<br>
    <b class="dk-risk">② 传媒 / AI 应用</b>：传媒 <b>-37.76 亿</b>（双冷）、计算机 <b>-31.42 亿</b>（背离，连续第四版），<b>结构性不参与；今日「AI 影视降本」只上调观察顺位，不构成买入理由</b>。<br>
    <b class="dk-risk">③ 高偏离的光模块个股</b>：昨日距 MA5 偏离过大且当日下跌者（新易盛 / 长光华芯 / 东山精密一类），<b>兑现区，不参与</b>。<br>
    <b class="dk-risk">④ 空头排列个股</b>：爱美客、东岳集团、果下科技、五一视界等，<b>位置不合格，全部回避</b>。<br>
    <b class="dk-risk">⑤ 追高禁令照常生效</b>：<b>开盘高开 &gt;+1.5% 的标的，当日不建仓、只减持</b>；<b>单板块集中度 ≤30%</b>、<b>单票 ≤10%</b>、<b>总仓位上限 35%</b>。<br>
    <b class="dk-caution">⑥ 特别提示</b>：<b class="dk-caution">今日为周五，21:30 美国 10 月 PPI、NVDA 听证与 Q3 财报均在 A股 收盘后或未来两周落地，<b>任何盘中买入都要承担「无法对冲的周末隔夜风险」</b> —— 这是本档把仓位上限设在 35%（而非 40% 以上）的直接原因</b>。
  </div>
</div>

"""

# ══════════════════════ 8 · 数据自检 ══════════════════════
S8 = """<!-- 8 数据自检 -->""" + h(
 '8 · 数据自检区（JS 自动扫描 · 各源日期一致性 · <b class="dk-up">本版已核：A股 2026-11-12 完整收盘〔结算价〕· 美股 <b>2026-11-12</b> 完整收盘〔昨夜·结算价〕· 日韩 2026-11-13 早盘〔09:45 KST·非收盘〕· 港股 11-12 收盘 · 商品 11-13 早盘 · VIX <b>11-12 结算 18.70</b> · 宏观日历轨 as_of 11-13 08:47</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div id="drSelfCheck" style="font-size:12.5px"><span style="color:var(--text-muted)">自检加载中…</span></div>
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:8px">
    <b class="dk-main">① 数据日一致性</b>：<code>market.json date = 2026-11-12</code>（<code>updated_at 2026-11-13 08:46</code>、<code>preopen_partial = true</code>）✅ · <code>cross_analysis.json date = 2026-11-12</code>（<code>flow_date = 2026-11-12</code>、<code>window.session = close</code>、<code>for_date = 2026-11-13</code>）✅ · <code>sector_tech.json data_date = 2026-11-12</code>（<code>kline_last_date = 2026-11-11</code>，<b class="dk-caution">滞后 1 个交易日，申万源 T+1 未发布</b>）✅ · <code>golden_diamond.json data_date = 2026-11-12</code> ✅ · <code>top10_history 2026-11-12</code> ✅ · <code>realtime.json data_date = 2026-11-12</code>（<code>market_status = closed</code>，<code>22:26:36</code> 收盘补抓）✅。<br>
    <b class="dk-caution">② 已知缺口与口径偏差（逐条列明，不掩盖）</b>：<b>a.</b> <code>sector_tech</code> 的 K 线滞后 1 个交易日（申万宏源 T+1 发布，非本链漏抓），<b>7.1b 段技术面以 11-11 收盘为准</b>；<b>b.</b> <b class="dk-risk">10 月 CPI / 核心 CPI 的<b>同比</b>字段日历轨 <code>value</code> 仍为空</b>，本档只写已回填的月率，<b>不以 9 月同比冒充、不以新闻轨数字拼接</b>；<b>c.</b> <b class="dk-caution">10Y / 30Y 美债为 11-10 结算（T+2 龄期）</b>，未反映美元 19 个月新高后的上行；<b>d.</b> 新闻池仅覆盖 11/13 00:00–08:47，<b>09:15 竞价至 09:30 开盘的信息缺口在案</b>，A股 盘中事件须收盘档补齐；<b>e.</b> <code>cross_analysis</code> 生成于 11-12 22:01，<b>11/13 当日 287 条新闻未入池</b> → <code>news_per_day</code> 被 2 日除权，日均热度低估约 50%；<b>f.</b> 投喂归档 11-12 / 11-13 <b>两日均为 0 件</b>（<code>_index.json</code> 已补，非 404）。<br>
    <b class="dk-main">③ 三处口径同值核验（跨页一致性）</b>：老站本页 / V3 <code>ai_synthesis.meta</code> / <code>feed_review</code> <code>ai_synthesis.meta</code> —— <b>方向「中性」· 置信度「中高」· 开盘判断「高开回吐压力」· 仓位「25%–35%」· 四象限「0 / 2 / 9 / 20」五项必须同值</b>。<b class="dk-caution">本版已在三处写入同值，任一不一致以本页为基准修正</b>。<br>
    <b class="dk-main">④ 渲染与样式</b>：design token（<code>dk-main</code> / <code>dk-caution</code> / <code>dk-risk</code> / <code>dk-data</code> / <code>dk-neutral</code>）· 字号 12.5px 为主 · 三处 index 同步（<code>index.html</code> / <code>index_template.html</code> / <code>deploy/index.html</code>）· <b class="dk-caution">7.1b 板块技术块与 7.2 观测股推演段由脚本注入，本段不重复叙述</b>。<br>
    <b class="dk-main">⑤ 本版相对上一版的三处修正（方法论级）</b>：<b>a.</b> 「个股盘前跌幅不得外推为指数跌幅」（上一版据此判「低开破位风险」，未命中）；<b>b.</b> 宏观段不再用「上一期同比」充当「最新值」，同比缺失即标缺口；<b>c.</b> 四象限若与上一版同值，须显式写「本版维持、不迁移」，不得改写迁移成因（历史引用保持原样）。
  </div>
</div>

"""

# ══════════════════════ 9 · 来源 ══════════════════════
S9 = """<!-- 9 来源 -->""" + h(
 '9 · 来源（<b class="dk-up">盘前版 · 11/13 09:45 落盘</b> · 复盘日 <b>2026-11-12（周四）</b> → 指引日 <b>2026-11-13（周五）</b>）'
) + """
<div class="dr-card" style="margin-top:4px">
  <div class="dr-note" style="font-size:12.5px;line-height:1.65;margin-top:4px">
    <b class="dk-main">① 行情与资金</b>：<code>data/daily_review/market.json</code>（盘前局部更新：腾讯 gtimg 美股 13 只 + akshare 美股双日 + 新浪 znb 日韩 + 腾讯 hf 商品 / 中行中间价，<code>updated_at 2026-11-13 08:46</code>，<code>preopen_partial = true</code>；A股 / 港股沿用 11-12 收盘）· <code>realtime.json</code>（11-12 22:26 收盘补抓，<code>L0.breadth</code> / <code>L1.sentiment</code> / <code>ETF</code>）· <code>output/sector_flow.json</code>（东财 clist，<code>flow_date 2026-11-12</code>，<code>stale_days = 0</code>）· <code>output/vix_panel.json</code>（CBOE 11-12 结算 18.70）· <code>output/market_thermometer.json</code>（11-12）。<br>
    <b class="dk-main">② 信号与推演</b>：<code>output/signals.json</code>（TOP800 扫描）· <code>output/top10_history.json</code>（11-12）· <code>output/golden_diamond.json</code>（11-12 · 4 只）· <code>output/cross_analysis.json</code>（<code>generated_at 2026-11-12 22:01</code>）· <code>output/sector_tech.json</code>（<code>generated_at 11-12 22:24</code>）· <code>output/obs_deduce_latest.json</code>（7.2 段脚本注入）· 上证日 K 均线（MA5 / MA10 / MA20，东财 <code>em_http</code> 单次取数，11-12 收盘）。<br>
    <b class="dk-main">③ 宏观</b>：<code>output/daily_macro_latest.json</code>（日历轨 as_of 11-13 08:47，主源百度经济日历；中国项 = PMI / GDP / CPI / LPR）。<br>
    <b class="dk-main">④ 公开新闻与研报</b>：<code>daily_news_latest.json</code> <b>287 条</b>（东财全球 200 / 富途全球 48 / 新浪全球 20 / 同花顺全球 13 / 财经早餐 6），<b>11-13 08:47 抓取</b>，覆盖 00:00–08:47。研报流：本机 <code>feed_mahoro</code> 当日 <b>121 条 / 18.36 万字</b>（金斧头 102 / 树枝报告 8 / 观澜台 3 / 逻辑与思考 2 / Vito 行研札记 2 / 智堡 2 / 180KResearch 2）——<b class="dk-caution">仅本机统计判读，原文不入仓库、不粘贴正文、不外传</b>。<b class="dk-caution">投喂语料：<code>feed/archive/2026-11-12</code> 与 <code>2026-11-13</code> 均为 0 条（无批次日），本页未引用任何投喂正文</b>。<br>
    <b class="dk-main">⑤ 规则与技能</b>：<code>review/REVIEW_SOP.md</code>（盘前模式）· skill <code>daily-reasoning</code>（老站）· skill <code>v3-daily-review</code>（V3）· <code>realtime.L2.rules</code>（仓位与追高禁令）· <code>review_v3/backtest_v3.py</code> 的 <code>OPEN_DIR</code> 白名单（<code>open_call = 高开回吐压力</code>）。<br>
    <b class="dk-main">⑥ 免责</b>：本页为量化观察与推演记录，<b class="dk-risk">不构成任何投资建议</b>；涉及个股的读数为客观技术 / 资金数据，持仓相关标注为「其他专家持股参考（非本人）」，<b>不给任何加减仓建议</b>。
  </div>
</div>
"""

# ══════════════════════ 替换执行 ══════════════════════
def idx(tag):
    n = s.count(tag)
    assert n == 1, 'anchor %r count=%d' % (tag, n)
    return s.index(tag)

A0, A05, A1, A11, A12 = '<!-- 0 结论先行 -->', '<!-- 0.5 深度判读 -->', '<!-- 1 昨日 A 股走势总结 -->', '<!-- 1.1 当日 TOP10 -->', '<!-- 1.2 当日金钻 -->'
A2, A3, A4, A5, A55, A6 = '<!-- 2 日韩股市与商品利率 -->', '<!-- 3 隔夜美股复盘 -->', '<!-- 4 重点宏观 -->', '<!-- 5 重点科技 -->', '<!-- 5.5 产业链 / 景气度 -->', '<!-- 6 新闻整合 + 7.1 -->'
AMED = '<!-- US-MEDICAL-BEGIN'
A71b = '<!-- ═══ 7.1b SECTOR-TECH-BEGIN'
A73 = '<!-- 7.3 次日开盘指引 -->'
A8, A9 = '<!-- 8 数据自检 -->', '<!-- 9 来源 -->'

seg = {}
seg['0'] = (idx(A0), idx(A05), S0)
seg['05'] = (idx(A05), idx(A1), S05)
seg['1'] = (idx(A1), idx(A11), S1)
seg['11'] = (idx(A11), idx(A12), S11)
seg['12'] = (idx(A12), idx(A2), S12)
seg['2'] = (idx(A2), idx(A3), S2)
seg['3'] = (idx(A3), idx(AMED), S3)
seg['4'] = (idx(A4), idx(A5), S4)
seg['5'] = (idx(A5), idx(A55), S5)
seg['55'] = (idx(A55), idx(A6), S55)
seg['6+71'] = (idx(A6), idx(A71b), S6 + S71)
seg['73+74'] = (idx(A73), idx(A8), S73)
seg['8'] = (idx(A8), idx(A9), S8)
seg['9'] = (idx(A9), len(s), S9)

# 从后往前替换，避免位移
for k in sorted(seg, key=lambda x: -seg[x][0]):
    a, b, txt = seg[k]
    s = s[:a] + txt + s[b:]

# 头部注释块替换
assert s.count(' 版本：11/12 周四 收盘版') == 1
ai = s.index(' 版本：11/12 周四 收盘版')
ai = s.rindex('<!--', 0, ai)
ae = s.index('-->', ai) + 3
s = s[:ai] + HEADER.strip() + s[ae:]

# BOM 保证
if not s.startswith('\ufeff'):
    s = '\ufeff' + s
io.open(P, 'w', encoding='utf-8').write(s)
print('OK sections replaced:', ', '.join(seg.keys()))
print('len', len(s), 'BOM', io.open(P, 'rb').read(3) == b'\xef\xbb\xbf')
