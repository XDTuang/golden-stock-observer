# -*- coding: utf-8 -*-
"""11/13 盘前版 V3 ai_synthesis 落盘（v3_reasoning_latest + 按日归档 + deploy 双写）"""
import json, io, shutil, os

DATA_DATE = '2026-11-12'
FOR_DATE = '2026-11-13'
GEN = '2026-11-13 09:30'

conclusion_first = (
 '<b>一句话：中性 / 中高置信度 / 高开回吐压力 / 仓位 25%–35% / 风险 中高 —— 外部「旗手止血」，但「分母未愈」，今日是「高开验证」而非「低开破位」</b>。'
 '隔夜（11/12 完整收盘）道 <span class="dk-dn">52,297.09（-0.36%）</span>、标普 <span class="dk-dn">7,592.40（-0.35%）</span>、纳 <span class="dk-dn">25,366.09（-0.39%）</span>、'
 '<b>VIX 18.70</b>；<b class="dk-main">NVDA 开 151.01（-13.08%）→ 最低 148.80（-14.36%）→ 收 166.19（-4.34%），自最低收窄 10.02pct</b>，市值单日蒸发 1,820 亿美元，'
 '同晚博通 / AMD <span class="dk-up">+5%</span>、费半盘中转涨、思科 / 应用材料 / Cerebras 业绩超预期；存储四线 <span class="dk-dn">-2.39%</span>、光通信三线 <span class="dk-dn">-3.35%</span>（跌幅小于盘前）。'
 '今早日韩 <span class="dk-up">日经 61,868.94（+1.73%）/ KOSPI 5,478.55（+2.54%）/ 海力士 +2.91% / 三星 +2.64%</span>。'
 'A股 昨日（11/12）以 <span class="dk-risk">放量 19,320.8 亿（+15.3%）+ 创业板 -2.44% 收在最低 + 情绪 14「恐慌下跌」+ 主力 -505.98 亿</span>完成派发。'
 '<b>三条理由</b>：① 外部锚由「双杀」变「单杀」—— 旗手止血、分母未愈（美元 19 个月新高、12 月加息 50bp 概率 15.3%、黄金 <span class="dk-risk">-2.67%</span> 至 3,881）；'
 '② 今早日韩首次「母股领先于 A股 反弹」（海力士 +2.91% vs 11/12 的 -2.82%）；③ 但 A股 自身是放量派发 + 周五 + 上方 MA20 压制，故只上调一档、不给偏多。'
 '<b class="dk-main">判据唯一化：3,672.71（MA20）为多空分水岭 —— 站上为修复（可持 35%），站不上为高开回吐（压回 25%）；跌破 3,647.44 且 30 分钟不收回则破位成立（10%–15%）</b>。'
)

theme_resonance = [
 {"theme": "维度 A · 母股转正（新的正向变量）", "name": "存储 / 半导体", "weight": "高",
  "related_stocks": ["长鑫科技", "兆易创新", "北京君正", "江波龙", "佰维存储", "澜起科技"],
  "desc": "A股 电子 11/12 主力 <span class=\"dk-risk\">-79.05 亿</span>、四象限 <span class=\"dk-caution\">背离 B</span>（语料 65 条 / 日均 32.5，全场最热）；"
           "美股存储四线 11/12 <span class=\"dk-dn\">-2.39%</span>（两日净 <span class=\"dk-up\">+8.26%</span>）；"
           "<b class=\"dk-up\">韩股海力士 11/13 早盘 1,290,500（+2.91%）、三星 213,500（+2.64%）</b>。"
           "<b>11/12 的失败模式是「母股不认、A股 硬跟」，今日母股首次转正 → 跟涨质量高于昨日</b>；"
           "<span class=\"dk-caution\">但电子资金未转正 + 昨日套牢盘，高开后 10:30 的承接才是判据</span>。",
  "evidence": "sector_flow 11-12 电子 -79.05 亿；cross_analysis 电子 verdict=背离 news=65；us_kline 11-12 存储四线 -2.39%；fengle_kr 11-13 09:45 海力士 +2.91% / 三星 +2.64%"},
 {"theme": "维度 B · 叙事获外部催化", "name": "国产算力 / 信创", "weight": "中高",
  "related_stocks": ["中科曙光", "海光信息", "寒武纪", "复旦微电", "北方华创", "联瑞新材"],
  "desc": "今日语料「A股 半导体产业链热度抬升 国产算力链配置价值凸显」（07:21）、<b>Jefferies 维持对中国半导体生产设备的买入（08:46）</b>；"
           "产业侧中科曙光 × 建行（11/12 21:19）、复旦微电提议回购 A+H、联瑞新材 10 亿元封装粉体项目。"
           "<b class=\"dk-caution\">逻辑 = 外部旗手失位 → 国产替代叙事获催化；但资金证据仍为负（计算机 -31.42 亿、背离 B）</b>。"
           "<b>升级条件：计算机主力单日 ≥+5 亿；当前不成立 → 观察仓 ≤5%</b>。",
  "evidence": "daily_news 07:21 / 08:46；sector_flow 11-12 计算机 -31.42 亿；cross_analysis 计算机 verdict=背离 news=24"},
 {"theme": "维度 C · 退潮未结束（由「确认」下调）", "name": "光模块 / CPO", "weight": "中",
  "related_stocks": ["中际旭创", "新易盛", "光迅科技", "天孚通信", "华工科技", "永鼎股份"],
  "desc": "A股 通信 11/12 <span class=\"dk-risk\">-73.03 亿</span>（11/11 <span class=\"dk-up\">+133.83 亿</span>）、四象限 <span class=\"dk-risk\">双冷 D</span>（语料 4 条）；"
           "美股三线 11/12 <span class=\"dk-dn\">-3.35%</span>（两日净 <span class=\"dk-up\">+8.10%</span>）；中际旭创拟 5,000 万元参投产业基金。"
           "<b class=\"dk-caution\">昨日 -73.03 亿更像「跟随大盘的被动减仓」，而非「趋势性撤离」</b>。"
           "<b>判据唯一化：通信主力单日能否收窄至 -30 亿以内；仍超 -50 亿则退潮延续</b>。",
  "evidence": "sector_flow 11-12 通信 -73.03 亿 / 11-11 +133.83 亿；cross_analysis 通信 verdict=双冷 news=4；us_kline 11-12 三线 -3.35%"},
 {"theme": "维度 D · 唯一三信号同向（防守）", "name": "能源 / 油运", "weight": "中",
  "related_stocks": ["中国海油", "中国石油", "中远海能", "兖矿能源", "广汇能源", "招商轮船"],
  "desc": "石油石化 <span class=\"dk-up\">+0.16 亿</span>（暗线 C，语料 3 条）；WTI <span class=\"dk-up\">87.42（+1.03%）</span> / 布伦特 <span class=\"dk-up\">94.21（+1.57%）</span>；"
           "<b class=\"dk-up\">11/12 金钻 4 只全部为能源 / 油运（中远海能 / 兖矿能源 / 中国海油 / 中国石油）</b>。"
           "<b>「资金为正 + 金钻集群 + 油价上行」是本轮唯一三个独立信号同向的链</b>；"
           "<span class=\"dk-caution\">但资金量级仅 0.16 亿，属「避风位」而非「主线」，只给观察位不给配置位</span>。",
  "evidence": "sector_flow 11-12 石油石化 +0.16 亿；market.comm WTI 87.42 / 布伦特 94.21（11-13 早盘）；golden_diamond 11-12 4 只"},
 {"theme": "维度 E · 三者不匹配（回避）", "name": "机器人 / 传媒", "weight": "中",
  "related_stocks": ["绿的谐波", "三花智控", "拓普集团", "光线传媒", "芒果超媒", "昆仑万维"],
  "desc": "机械设备 <span class=\"dk-risk\">-66.99 亿</span>（双冷 D，语料 4 条）、传媒 <span class=\"dk-risk\">-37.76 亿</span>（双冷 D）；板块技术机械设备 L2（趋势 = 反弹，中期未反转）。"
           "今日出现反向语料（「hf大制造：坚定看好物理AI&人形机器人」）与事件催化（火山引擎 Seedance 2.5 flash、国内首个口服 GLP-1 获批）。"
           "<b class=\"dk-risk\">语料看多、资金撤离、技术未反转 —— 三者不匹配，维持回避</b>；"
           "<span class=\"dk-caution\">催化剂只上调观察顺位，不构成买入理由</span>。",
  "evidence": "sector_flow 11-12 机械设备 -66.99 亿 / 传媒 -37.76 亿；sector_tech 机械设备 L2；daily_news 07:2x / 08:37 / 08:38"},
]

holding_map = {
 "note": "以下个股读数均为<b>客观技术 / 资金数据</b>，标注「其他专家持股参考（非本人）」，<b class=\"dk-risk\">不构成任何加减仓建议</b>。数据日 = 2026-11-12 收盘（11/13 盘前尚未开盘，量价未更新）。",
 "theme_aligned": [
   "剑桥科技（光模块 · 通信主线，11/12 <b class=\"dk-up\">122.85（+5.04%）</b>，为组内唯一上涨；<b class=\"dk-caution\">通信板块净流出 73.03 亿、板块双冷的同日逆势上涨且无新闻解释，属纯资金行为，退潮期回撤最快</b>）",
   "永鼎股份（光通信线缆，11/12 <b class=\"dk-dn\">23.76（-2.66%）</b>；外部锚 = 光通信三线 11/12 <b class=\"dk-dn\">-3.35%</b>，10:30 前看通信主力能否收窄至 -30 亿内）",
   "华工科技（光模块 / 激光，11/12 <b class=\"dk-dn\">68.26（-1.43%）</b>；<b class=\"dk-caution\">链内温度计 —— 其 MA5 得失可作光模块主线是否终结的客观判据</b>）",
   "长鑫科技（存储，11/12 <b class=\"dk-dn\">40.97（-2.61%）</b>；<b class=\"dk-main\">外部锚由负转正：海力士 11/13 早盘 +2.91%、三星 +2.64%，是本组唯一获得母股背书的标的</b>）",
 ],
 "caution": [
   "永杉锂业（锂电材料，11/12 <b class=\"dk-dn\">10.59（-2.22%）</b>；碳酸锂主连 90,900 无日涨跌字段，<b class=\"dk-caution\">方向不可判，仅记录水平值</b>）",
   "昊华科技（氟化工 / 电子特气，11/12 <b class=\"dk-dn\">33.36（-0.80%）</b>；基础化工板块 11/12 <b class=\"dk-dn\">-30.67 亿</b>、双冷 D）",
   "ST万邦（11/12 <b class=\"dk-dn\">10.12（-2.69%）</b>；<b class=\"dk-risk\">ST 标的流动性风险与退市规则风险独立于大盘，任何外部修复都不改变该项</b>）",
 ],
 "us": [
   "存储映射：MU 11/12 <b class=\"dk-dn\">798.44（-1.59%）</b> / SNDK <b class=\"dk-dn\">937.46（-4.11%）</b> / WDC <b class=\"dk-dn\">311.21（-0.67%）</b> / SKHY <b class=\"dk-dn\">137.71（-3.19%）</b> —— 四线均值 <b class=\"dk-dn\">-2.39%</b>，两日净仍 <b class=\"dk-up\">+8.26%</b>",
   "光通信映射：LITE 11/12 <b class=\"dk-dn\">624.65（-3.61%）</b> / AAOI <b class=\"dk-dn\">52.85（-5.39%）</b> / COHR <b class=\"dk-dn\">232.08（-1.04%）</b> —— 三线均值 <b class=\"dk-dn\">-3.35%</b>",
   "算力旗手：NVDA 11/12 <b class=\"dk-dn\">166.19（-4.34%）</b>，自盘中最低 148.80 回升 <b class=\"dk-up\">11.7%</b>；<b class=\"dk-caution\">治理事件的制度性时点（参议院听证 / 下周三公司会议 / Q3 财报）在未来两周内</b>",
 ],
}

t1_radar = [
 {"time": "09:15–09:25", "impact": "高",
  "event": "<b>竞价定档</b>：<b class=\"dk-caution\">基准 = 高开 +0.3%～+0.8%（3,667–3,685），概率 45%</b>；<b class=\"dk-caution\">高开 &gt;+1.0%（&gt;3,692）概率 30%</b>（最需防高开兑现）；<b class=\"dk-risk\">平开或 &lt;+0.3%（&lt;3,667）概率 25%</b>（外部反弹未被采纳）。依据 = 美股三大指数 -0.35%～-0.39%、纳指期货早盘 +0.3%、日韩高开 2% 以上、海力士 +2.91%。"},
 {"time": "09:30–10:30", "impact": "高",
  "event": "<b>本版核心定性窗口</b>：看 <b>3,672.71（MA20）</b>能否在 10:30 前站住。<b class=\"dk-caution\">站住 = 修复成立，可持 35%；站不住 = 高开回吐，压回 25%</b>。第二判据 = 昨日「上午强、午后弱」模板是否重演 —— 若 10:30 后单边回落且无有效反抽，即视为派发延续。"},
 {"time": "10:30", "impact": "高",
  "event": "<b>资金验证（唯一硬指标）</b>：<b>通信主力能否收窄至 -30 亿内、电子能否收窄至 -40 亿内</b>。<b class=\"dk-caution\">两者均达标 = 资金确认转向，存储 / 光模块可由「观察」升为「有条件参与」；任一不达标 = 今日上涨属「被动跟涨」，不加仓</b>。"},
 {"time": "13:30–14:00", "impact": "中高",
  "event": "<b>周五效应窗口</b>：<b class=\"dk-caution\">周末隔夜风险不可对冲，减仓行为通常前置到周五午后</b>；若此时段出现「指数不跌、个股普跌」，属典型的「指数护盘 + 个股出货」组合，须以持仓个股的实际承接为准。"},
 {"time": "14:30 / 21:30", "impact": "中高",
  "event": "<b>14:30 宽基 ETF</b>：昨日六只合计 -23.97 亿，<b class=\"dk-caution\">若今日转正 ≥10 亿可视为护盘信号</b>；<b>21:30 美国 10 月 PPI</b>（A股 收盘后）—— <b class=\"dk-risk\">无法在盘中定价，是本周最大的周末隔夜风险来源</b>。"},
]

risks = [
 {"name": "把「高开」直接当成「修复成立」的抄底理由", "prob": "高", "impact": "高",
  "desc": "昨日已完整演示「上午诱多、午后杀跌」（创业板自高点回落 <b>4.31pct</b>、科创50 回落 <b>4.23pct</b>），<b class=\"dk-risk\">高开在当前环境里首先是被用来出货的形态</b>。"
          "<b class=\"dk-main\">本档因此把买入条件写成价格条件（10:30 前站上 3,672.71）与资金条件（通信 -30 亿内 / 电子 -40 亿内），而不是情绪条件</b>。"},
 {"name": "分母端继续收紧（利率 / 美元）", "prob": "中高", "impact": "高",
  "desc": "美元触及 <b>19 个月新高</b>、12 月加息 50bp 概率 <b>15.3%</b>、戴利「可能需要进一步加息」、黄金 <b class=\"dk-risk\">-2.67%</b> 至 3,881、WTI <b class=\"dk-up\">+1.03%</b>。"
          "<b class=\"dk-risk\">「金跌油涨 + 美元强」= 实际利率上行，对高久期成长股（创业板 / 科创）是持续性压制</b>；即使今日高开，估值扩张也缺乏支撑。"},
 {"name": "NVDA 治理事件的「制度性二次发酵」", "prob": "中", "impact": "中高",
  "desc": "Truist 下调评级、目标价腰斩；美参议院银行委员会传唤黄仁勋与卢特尼克作证；临时 CEO 克雷斯计划下周三召开公司会议；Q3 财报待发。"
          "<b class=\"dk-risk\">三个时点在未来两周内密集落地 —— 「利空未出尽」是结构性的，不因单日 -4.34% 的收敛而结束</b>。"},
 {"name": "昨日套牢盘在背离板块的压制（电子 / 计算机）", "prob": "中高", "impact": "中",
  "desc": "电子 <b class=\"dk-risk\">-79.05 亿</b>、计算机 <b class=\"dk-risk\">-31.42 亿</b>，四象限分别为背离 B / 背离 B，<b>且电子语料 65 条中绝大多数是「英伟达 / 芯片股」单一事件的反复计数，热度含水分</b>。"
          "<b class=\"dk-caution\">反弹初期最容易出现「高开后被昨日套牢盘压制」，需以 10:30 的承接而非开盘幅度判断</b>。"},
 {"name": "把「母股背书」误读为「趋势反转」", "prob": "中", "impact": "中",
  "desc": "海力士 11/13 早盘 <b class=\"dk-up\">+2.91%</b> 是本轮首次「母股领先」，<b class=\"dk-caution\">但它出现在存储四线两日净 +8.26% 后的回吐过程中，属「跌深反弹」性质</b>。"
          "<b class=\"dk-main\">判据须叠加两条：① 母股能否连续 2 日为正；② A股 电子主力能否由 -79 亿转为 -40 亿以内。单日母股反弹不构成趋势结论</b>。"},
]

meta = {
 "mode": "preopen",
 "direction": "中性",
 "direction_confidence": "中高",
 "open_call": "高开回吐压力",
 "sh_index_close": 3655.83,
 "sh_open": 3673.06,
 "sh_high": 3699.58,
 "sh_low": 3647.44,
 "turnover_yi": 19320.8,
 "main_net_yi": -505.98,
 "sentiment_score": 14,
 "sentiment_state": "恐慌下跌",
 "position_range": "25%–35%（情绪档 [0,20) 机械值为 0%–20%，本档上修：① 外部锚由「双杀」变「单杀」—— NVDA 收窄至 -4.34%、博通/AMD +5%、半导体设备业绩超预期；② 今早日韩首次「母股领先于 A股 反弹」（日经 +1.73% / KOSPI +2.54% / 海力士 +2.91%）；③ 但 A股 自身放量派发（19,320.8 亿 / 情绪 14）+ 周五 + 上方 MA20 3,672.71 压制，故不给 40% 以上）",
 "quadrant": "0 / 2 / 9 / 20",
 "quadrant_prev": "0 / 2 / 9 / 20",
 "quadrant_note": "共振 A 0（连续第二版清零）/ 背离 B 2（电子 65 条 vs -79.05 亿、计算机 24 条 vs -31.42 亿）/ 暗线 C 9（银行 +7.46 / 农林牧渔 +4.33 / 美容护理 +2.87 / 医药生物 +2.52 / 交通运输 +1.48 / 钢铁 +0.64 / 建筑装饰 +0.62 / 国防军工 +0.61 / 石油石化 +0.16，全部资金为正）/ 双冷 D 20（通信 -73.03 / 机械设备 -66.99 / 电力设备 -62.39 / 有色金属 -59.03 居前），共 31 席。本版与上一版完全同值、不发生迁移；上一版已完成的迁移（1 / 1 / 11 / 18 → 0 / 2 / 9 / 20）成因未变，本版不改写。口径限制：cross_analysis 生成于 11-12 22:01，11/13 当日 287 条新闻未入池，news_per_day 被 2 日除权，日均热度低估约 50%。",
 "us_close_date": "2026-11-12",
 "asia_date": "2026-11-13",
 "vix": 18.7,
 "data_date": DATA_DATE,
 "for_date": FOR_DATE,
 "agent": "WorkBuddy（08:40 盘前推演档 · v3 preopen · 09:14 补触发）",
}

payload = {
 "data_date": DATA_DATE,
 "for_date": FOR_DATE,
 "generated": GEN,
 "mode": "preopen",
 "data_window": ("A股 11/12 完整收盘（上证 3,655.83 -0.67% / 创业板 2,509.43 -2.44% / 科创50 +0.73% 冲高 +4.96% 回落 / 两市 19,320.8 亿 · 放量 15.3%）"
                 " × 美股 11/12 完整收盘〔昨夜：道 -0.36% / 标普 -0.35% / 纳 -0.39% / VIX 18.70 / NVDA -4.34%（自低 -14.36% 收窄 10.02pct）/ 存储四线 -2.39% / 光通信三线 -3.35%〕"
                 " × 日韩 11/13 早盘〔日经 61,868.94 +1.73% · KOSPI 5,478.55 +2.54% · 海力士 +2.91% · 三星 +2.64%〕"
                 " × 商品 11-13 早盘〔黄金 -2.67% / WTI +1.03% / 布伦特 +1.57%〕"),
 "ai_synthesis": {
   "conclusion_first": conclusion_first,
   "theme_resonance": theme_resonance,
   "holding_map": holding_map,
   "t1_radar": t1_radar,
   "risks": risks,
   "meta": meta,
   "disclaimer": "本页为量化观察与推演记录，<b class=\"dk-risk\">不构成任何投资建议</b>。涉及个股的读数均为客观技术 / 资金数据；持仓相关标注为「其他专家持股参考（非本人）」，不含任何加减仓建议。",
 },
}

targets = [
 'output/v3_reasoning_latest.json',
 'output/v3_reasoning_%s.json' % DATA_DATE,
 'deploy/output/v3_reasoning_latest.json',
 'deploy/output/v3_reasoning_%s.json' % DATA_DATE,
]
for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    json.dump(payload, io.open(t, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('written', t)

# 自检
import re
bad = []
for f in ('conclusion_first',):
    if '<code>' in payload['ai_synthesis'][f]: bad.append(f)
for it in theme_resonance:
    for k in ('name','desc'):
        if '<code>' in it[k]: bad.append(it['name']+k)
    if any('<code>' in x for x in it['related_stocks']): bad.append(it['name']+'stocks')
for x in t1_radar:
    if '<code>' in x['event']: bad.append(x['time'])
for x in risks:
    if '<code>' in x['desc']: bad.append(x['name'])
    assert x['prob'] in ('高','中高','中','低中','低'), x['prob']
    assert x['impact'] in ('极高','高','中高','中','低中','低'), x['impact']
print('code-tag violations:', bad)
print('OK, keys:', list(payload['ai_synthesis'].keys()))
