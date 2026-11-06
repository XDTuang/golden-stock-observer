#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-06 盘前版 V3 推演产物（output/ + deploy/ 双写 · mode=preopen）"""
import json
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
OUT = BASE / "output"
DEP = BASE / "deploy/output"

src = json.load(open(OUT / "v3_reasoning_latest.json", encoding="utf-8"))

CF = [
    "<b>【方向判定】中性偏空（由「中性偏多」下调两档）· 置信度 中高 · 开盘 低开反弹（已实现：开 3,612.15 / -2.11%）· 仓位 10%–20% · 风险 高（上调一档）。</b><br><b class=\"dk-main\">昨夜是全球 AI 硬件链的系统性 de-rating，不是普通回调</b>：纳指 <b class=\"dk-risk\">-5.52%</b>（较 10/06 高点回落超 10%，进入技术性回调）、纳指100 <b class=\"dk-risk\">-6.5%</b>、道指 <b class=\"dk-risk\">-3.44%</b>、标普 <b class=\"dk-risk\">-4.36%</b>、<b class=\"dk-risk\">费城半导体 -12%（2020 年以来最大单日跌幅）</b>；<b class=\"dk-risk\">存储四线 0/4（SNDK -22.26 / MU -17.46 / WDC -17.35 / SKHY -13.40，均值 -17.62%）</b>、<b class=\"dk-risk\">光通信三线 0/3（AAOI -20.89 / LITE -18.68 / COHR -12.98，均值 -17.52%）</b>、MRVL <b class=\"dk-risk\">-16.43%</b>、NVDA <b class=\"dk-risk\">-9.26%</b>、TSLA <b class=\"dk-risk\">-10.77%</b>，美股单日市值蒸发约 2.8 万亿美元（刷新单日纪录）。",
    "<b>【核心矛盾】分母与分子在同一夜被同时下调 —— 这是最难受的组合。</b><br><b class=\"dk-risk\">分子端</b>：民主党中期选举大胜（「蓝色浪潮」）⇒ 市场重估 AI 高速扩张面临的数据中心审批 / 并网 / 监管风险，<b class=\"dk-main\">被质疑的不是「AI 需求」，而是「AI 资本开支的许可」</b>。 <b class=\"dk-risk\">分母端</b>：9 月 CPI <b>3.7%</b>（预期 3.6）、核心 CPI 2.6%、<b>核心 PCE 3.1%</b>、ADP +8.6 万（预期 6.5）、ISM 55.5 ⇒ <b>「12 月加息 25bp」重新成为可交易情景</b>。<b class=\"dk-caution\">两者叠加 ⇒ 杀的是估值，不是盈利；因此跌幅集中在高 β / 高估值（创业板开 -4.99%、科创50 开 -5.05%），而非全面（上证开 -2.11%、沪深300 开 -2.32%）</b>。",
    "<b>【亚太二次确认】今晨不是分化，是全域释放。</b><br>与 11/05 的「韩崩、日稳、中涨」不同，今晨 <b class=\"dk-risk\">日经 57,560.17（-5.76%，较 6 月高点 -20%，进入技术性熊市）</b>、<b class=\"dk-risk\">KOSPI 5,019.56（-6.77%，盘中一度 -8.1%，韩国交易所启动 SIDECAR 暂停程序化卖盘）</b>、SK하이닉스 <b class=\"dk-risk\">-7.91%</b>、삼성전자 <b class=\"dk-risk\">-6.90%</b>、MSCI 亚太 <b class=\"dk-risk\">-3%</b>、<b class=\"dk-risk\">软银 -16%（2024/08 以来最大跌幅）</b>。<b class=\"dk-main\">⇒ 判据升级：区域性事件（存储价格）可以免疫，全域性事件（资本开支政策 + 折现率）难以免疫</b>。",
    "<b>【A股 开盘实况】低开 -2.11% 后未破位，但成长端全面失守。</b><br>09:31:09 读数：上证 <b class=\"dk-risk\">3,625.23（-1.75%）</b>，开 3,612.15（-2.11%）、最低 3,610.20；<b class=\"dk-risk\">创业板 2,472.67（-3.67%），开 2,438.72（-4.99%）</b>；<b class=\"dk-risk\">科创50 1,236.30（-3.92%），开 1,221.67（-5.05%）</b>；深成 <b class=\"dk-risk\">-2.63%</b>、沪深300 <b class=\"dk-risk\">-1.93%</b>、中证500 <b class=\"dk-risk\">-2.44%</b>。<b class=\"dk-main\">成长端低开幅度是主板的 2.2 倍 ⇒ 市场杀的是「AI 相关高 β」，不是「中国资产」</b>，与中概股金龙 <span class=\"dk-up\">+0.43%</span>、港恒科 11/05 <span class=\"dk-up\">+5.55%</span> 互为印证。",
    "<b>【四象限】本版 共振 6 / 背离 2 / 暗线 13 / 双冷 10（前版 2 / 0 / 17 / 12）· 迁移全部来自语料侧。</b><br><code>flow_yi</code> <b>31/31 逐板块零变化</b>（<code>flow_date</code> 仍为 2026-11-05），窗口语料 285 → <b>589 条</b>（11-06 早间池入库 291 条）⇒ 有色 / 机械 / 传媒 / 银行 升<b>共振 A</b>，国防军工 / 食品饮料 升<b>背离 B</b>。<b class=\"dk-caution\">⇒ 共振 A 由 2 升至 6 不得读作「资金共振扩大」，只说明「昨天流入的板块今天被讨论得更多」—— 而电子（58 条）/ 计算机（56 条）讨论的内容恰是利空</b>。",
    "<b>【象限标签的今日失真】电子仍标「共振 A」，本档主动降权两次。</b><br>象限 = 「T 日资金」×「T+1 语料」的机械交叉。电子 <code>news_count 58</code>（全场第二高）+ 11-05 <span class=\"dk-up\">+12.05 亿</span> ⇒ 机械落进「共振」。<b class=\"dk-risk\">当隔夜原产地反向时，共振 A 会失真为「昨日资金 + 今日利空」的错配组合</b>；<b class=\"dk-main\">叠加「半导体设备昨日 +7.71% 的叙事前提（原厂扩产）已被政策质疑」，该席今日的风险收益比是全场最差的</b>。",
    "<b>【今日三档剧本 · 开盘后修订】</b><b class=\"dk-caution\">A. 低开反弹后二次探底（50% · 基准）</b>：10:00–11:00 回落至 3,610 下方并测试 3,580，创业板跌破 2,438 ⇒ 仓位 10%，<b class=\"dk-risk\">全日只减不加</b>；<b class=\"dk-caution\">B. 低开高走、守住 3,610（30%）</b>：站稳 3,625 并收复 3,646.57（11-05 日内最低 = 昨日买盘成本线），成交 &gt;2.2 万亿、电力设备资金续入 ⇒ 仓位 20%，<b class=\"dk-risk\">仍不碰 AI 硬件</b>；<b class=\"dk-risk\">C. 破位下行（20%）</b>：失守 3,580 或跌停 &gt;40 家，或电子+通信合计再流出 &gt;80 亿 ⇒ 仓位降至 5% 以下，方向改「偏空」。",
]

THEMES = [
    {
        "theme": "相对占优：电力设备 / 新能源（资金连续 4 日 + 与 AI 资本开支零关联）",
        "name": "相对占优：电力设备 / 新能源",
        "weight": "高",
        "desc": "电力设备 <b class=\"dk-up\">+63.10 亿</b>（<code>streak 4</code> · 资金分位 <b>100</b> · 31 板块第一）、光伏设备 <b class=\"dk-up\">+32.36 亿</b>（<span class=\"dk-up\">+5.77%</span>）、电池 <b class=\"dk-up\">+26.43 亿</b>、碳酸锂 91,580 持稳；<code>news_count 12</code> 未达 16 门槛 ⇒ <b class=\"dk-main\">「资金已入 + 语料未炒」的教科书形态</b>。政策共振：氢能五大城市群试点、发改委储能 / 电力市场调研。<b class=\"dk-caution\">定位为「相对占优」而非「趋势起点」—— 板块技术档位为 L3 且 trend 为 downtrend_rebound，今日大盘系统性下跌时亦难有正超额</b>。",
        "related_stocks": ["电力设备（申万一级 · L3 · +63.10 亿）", "光伏设备（+32.36 亿）", "电池（+26.43 亿）", "汽车（L3 · +11.17 亿）"],
        "evidence": "cross_analysis.json（2026-11-06 09:31 盘前重算）：电力设备 12 条 / +63.10 亿 → 暗线；sector_tech.json（11-05 · kline_lag=0）：电力设备 L3 / downtrend_rebound；sector_flow flow_date=2026-11-05 ｜ stale_days=0。",
    },
    {
        "theme": "防御对冲：有色 / 贵金属（金价破 4,100，避险资金转向黄金而非美债）",
        "name": "防御对冲：有色 / 贵金属",
        "weight": "中高",
        "desc": "金 <b class=\"dk-up\">4,118.81（+1.45%）</b> 突破 4,100（08:19 快讯）、COMEX 4,131.06（+1.43%）；<b class=\"dk-main\">而 10Y 美债 4.90% 未下行 ⇒ 避险资金流向黄金而非债券</b>，说明是「股市去杠杆 + 通胀对冲」，不是「衰退避险」。有色 11-05 资金 <b class=\"dk-up\">+18.62 亿</b>、语料 24 条 ⇒ 象限由暗线升<b>共振 A</b>。<b class=\"dk-caution\">硬约束：只认贵金属，不认工业金属 —— 锡等 AI 后排金属已崩，铜若补跌则「衰退预期」启动，届时工业金属将二次杀</b>。",
        "related_stocks": ["有色（申万一级 · 共振 A · +18.62 亿）", "黄金（避险）", "白银（避险）", "工业金属（观察，不参与）"],
        "evidence": "market.json.comm（gold_spot 4,118.81 +1.45% / gold_comex 4,131.06 +1.43% / us10y 4.90%，2026-11-06 与 2026-11-04）；cross_analysis 有色 24 条 / +18.62 亿 → 共振 A。",
    },
    {
        "theme": "负向主线：AI 硬件全链 de-rating（存储 / 光模块 / PCB / 算力）",
        "name": "负向主线：AI 硬件全链 de-rating",
        "weight": "极高",
        "desc": "美股 11/05 完整收盘：<b class=\"dk-risk\">SNDK -22.26% / MU -17.46% / WDC -17.35% / SKHY -13.40%</b>、<b class=\"dk-risk\">AAOI -20.89% / LITE -18.68% / COHR -12.98%</b>、<b class=\"dk-risk\">MRVL -16.43% / NVDA -9.26%</b>、费半 -12%；今晨韩股 SK하이닉스 <b class=\"dk-risk\">-7.91%</b> / 삼성전자 <b class=\"dk-risk\">-6.90%</b> 完成亚洲时段二次定价。<b class=\"dk-main\">性质是「估值 + 许可」双杀而非「业绩杀」—— COHR 财报数据中心 +79% 仍跌 12.98%</b>。A股 侧：通信 11-05 <b class=\"dk-risk\">-47.11 亿</b>（单日反转 122.97 亿）且象限双冷 D。",
        "related_stocks": ["半导体（存储 / 模组）", "通信设备（光模块 / CPO）", "元件（PCB / 覆铜板）", "算力租赁 / 服务器代工"],
        "evidence": "market.json.us_kline 23/23 最新日 2026-11-05；market.json.asia.kr_stocks fetched_at 2026-11-06 08:40；cross_analysis 通信 14 条 / -47.11 亿 → 双冷 D。",
    },
    {
        "theme": "前提被改写：半导体设备 / 材料（昨日首选 → 今日观察）",
        "name": "前提被改写：半导体设备 / 材料",
        "weight": "中高",
        "desc": "11-05 设备 <b class=\"dk-up\">+7.71%</b> / <b class=\"dk-up\">+54.32 亿</b>（streak 2）、材料 <span class=\"dk-up\">+6.01%</span> / +20.38 亿，昨日被列为<b>首选</b>，理由是「外盘跌也受益（扩产成本降）」。<b class=\"dk-risk\">但昨夜事件的性质是「原厂扩产本身被政策质疑」⇒ 该前提不成立</b>，故「存储价格跌 → 设备受益」的链条断开。<b class=\"dk-main\">翻多的唯一条件是「今日低开后设备率先翻红且资金连续第三日净流入」——这是本档今日最重要的单点验证</b>。",
        "related_stocks": ["半导体设备（L2 · +54.32 亿 streak 2）", "半导体材料（+20.38 亿）", "半导体（+61.04 亿）"],
        "evidence": "cross_analysis 电子 58 条 / +12.05 亿 → 共振 A（利空型热度，本档降权）；sector_tech 电子 L2；sector_flow 11-05 分项（半导体 +61.04 / 设备 +54.32 / 材料 +20.38）。",
    },
    {
        "theme": "防御参照：医药 / CXO（美股医疗组仅 -2.77%，显著抗跌）",
        "name": "防御参照：医药 / CXO",
        "weight": "中",
        "desc": "美股医疗 10 只组：核心 8 只均值 <b class=\"dk-risk\">-2.77%</b>、上涨 <b>1/8</b>（仅 IQV <span class=\"dk-up\">+0.41%</span>），最弱 RGEN <span class=\"dk-dn\">-5.45%</span>。<b class=\"dk-main\">显著优于纳指 -5.52% ⇒ 「非 AI 资产」的相对抗跌在美股已验证</b>，为 A股 「防御 + 非 AI」方向提供外部参照。A股 医药生物 11-05 <b class=\"dk-up\">+5.71 亿</b>（暗线 · news 6 条）。<b class=\"dk-caution\">但美股医疗内部极差 5.86pct（RGEN -5.45 vs IQV +0.41）⇒ 是「结构分化」不是「板块上行」，只作观察、不主动加</b>。",
        "related_stocks": ["医药生物（申万一级 · 暗线 · +5.71 亿）", "CRO（对标 CRL / IQV / ICLR / MEDP）", "CDMO（对标 TMO）", "诊断（对标 LH）"],
        "evidence": "output/daily_review/analysis.html 3 段末 US-MEDICAL 块（由 review/build_us_medical.py 生成 · 11-05 数据）；cross_analysis 医药生物 6 条 / +5.71 亿 → 暗线。",
    },
]

HOLDING = {
    "note": "持仓与个股段落一律为「其他专家持股参考（非本人）」，只列客观技术读数，不给加减仓建议。观测池读数由 obs_panel.json（32 只 · 数据日 2026-11-05）派生，L2 情景 7 只（obs_scenarios.json · 11-05 → 11-06）。今日 A股 已开盘，下列读数为 11-05 收盘值，仅作「昨日结构」参照。",
    "theme_aligned": [
        "电力设备 / 光伏：晶盛机电（11-05 收盘读数 · 5 日 +17.06%）；罗博特科 -1.94%（299.07 · 5 日 -9.38%，回踩中）",
        "有色：兴业银锡 +7.86%（25.93 · 量比 2.05 · 偏离 MA5 +10.15%）—— 与金价新高同向，但属工业金属，须按 7.4 段「只认贵金属」的约束读",
        "计算机 / 算力整机：中科曙光 -0.08%（78.88 · 站上 MA5 +4.75% · 5 日 +4.67%）—— 板块 L4 但个股滞涨；今日外部为利空型热度，降权",
    ],
    "caution": [
        "光模块（回避）：新易盛 -5.54%（185.61 · 5 日 -18.73% · 空头排列）、光迅科技 -0.96%（97.29 · 5 日 -13.40% · 空头排列）、联特科技 +0.02%（153.47 · 5 日 -12.40%）",
        "半导体设备（观察）：天岳先进 +4.19%（78.79 · 偏离 MA5 +8.60%）、东微半导 +1.91%（56.15）、长光华芯 +3.94%（139.28）—— 昨日强势、今日面临「叙事前提被改写」的检验",
        "PCB / 存储（回避）：11-05 金钻起涨 6 只中 3 只为 PCB（澳弘电子 / 满坤科技 等），恰是今日外部冲击最重的环节",
    ],
    "us": "美股 11/05 完整收盘（昨夜）：医疗 10 只核心 8 只均值 -2.77%（上涨 1/8）· 存储四线 -17.62%（0/4）· 光通信三线 -17.52%（0/3）· 道 -3.44% / 标普 -4.36% / 纳 -5.52% / 费半 -12% · VIX 28.18（+69.66%）。",
}

T1 = [
    {"time": "09:15–09:30", "impact": "极高", "event": "竞价落点：<b class=\"dk-risk\">实际大幅低开（上证开 3,612.15 / -2.11%，创业板开 -4.99%）⇒ 本档「低开」判断成立</b>；<b class=\"dk-caution\">关注 09:25 集合竞价成交额是否放大 —— 放量低开 = 恐慌盘出清，缩量低开 = 抛压未释放</b>。"},
    {"time": "09:30–10:00", "impact": "极高", "event": "<b>第一小时定方向</b>：<b class=\"dk-up\">上证若站上 3,625 并向 3,646.57（11-05 日内最低）靠拢 ⇒ 情形 B（低开高走）成立</b>；<b class=\"dk-risk\">若跌破 3,610.20（今日开盘最低）⇒ 情形 A（二次探底）启动，下一支撑 3,580</b>。<b class=\"dk-caution\">同时看跌停家数：&gt;25 家为警戒，&gt;40 家为情形 C</b>。"},
    {"time": "10:00–11:30", "impact": "高", "event": "<b>结构验证窗口</b>：<b class=\"dk-main\">① 半导体设备能否在低开后率先翻红（昨日 +7.71% 的叙事是否仍成立）② 电力设备资金能否连续第 5 日净流入 ③ 通信 / 光模块是否再放量下杀</b>。三项中前两项有一项成立 ⇒ 结构性抵抗存在；全不成立 ⇒ 普跌确认。"},
    {"time": "13:00–14:00", "impact": "中高", "event": "<b>午后方向 = 承接力检验</b>：<b class=\"dk-caution\">若上午缩量下跌、午后成交不放大 ⇒ 抛压衰减，收盘可能在 -1.2%~-1.8%；若午后放量破 3,580 ⇒ 尾盘踩踏，收盘 -2.5% 以上</b>。<b class=\"dk-main\">国家队 ETF 的日内净额是本时段最关键的单一变量</b>（11-05 为 -11.43 亿，若今日转为大额净买入，则护盘启动）。"},
    {"time": "14:30–15:00", "impact": "高", "event": "<b>尾盘决断</b>：<b class=\"dk-risk\">周五尾盘若出现「放量下杀至 3,600 下方」⇒ 说明资金不愿持仓过周末（今晚非农 + 地缘）；若尾盘拉升 ⇒ 政策预期主导</b>。<b class=\"dk-caution\">同时记录：今日跌停家数、两市成交、电力设备与电子 / 通信的资金净额，作为 22:15 档结算依据</b>。"},
    {"time": "21:30", "impact": "极高", "event": "<b>美国 10 月非农就业 + 失业率（预期 +6.5 万 / 4.2%，值未公布）</b>。<b class=\"dk-risk\">情景一：&gt;10 万 ⇒ 「12 月加息」坐实，下周一全球高估值资产二次杀；情景二：4–10 万 ⇒ 符合预期，冲击钝化；情景三：&lt;4 万 ⇒ 就业失速、降息交易回归，风险资产可能 V 型修复</b>。<b class=\"dk-main\">这是本周最重要的单一事件，直接决定下周一 A股 的开盘方向</b>。"},
]

RISKS = [
    {"name": "AI 硬件链 de-rating 向 A股 产业链传导（存储 / 光模块 / PCB / 算力）", "prob": "高", "impact": "高", "desc": "费半 <b class=\"dk-risk\">-12%</b>、存储四线 <b class=\"dk-risk\">-17.62%</b>、光通信 <b class=\"dk-risk\">-17.52%</b>、MRVL <b class=\"dk-risk\">-16.43%</b>，且韩国 SK하이닉스今晨再 <b class=\"dk-risk\">-7.91%</b>。<b class=\"dk-main\">A股 相关环节 11-05 仍是上涨的（半导体设备 +7.71%），今日须完成定价</b>。<b class=\"dk-caution\">判据：电子 + 通信合计再流出 &gt;80 亿即确认传导</b>。"},
    {"name": "VIX 单日 +69.66% 触发风险预算强制下调 / 被动减仓", "prob": "高", "impact": "中高", "desc": "VIX <b class=\"dk-risk\">16.61 → 28.18（+69.66%）</b>，为 2026 年最大单日升幅。28 上方属高波区间，<b>历史对应「波动率目标基金 / 风险平价基金被动降杠杆」阶段</b>，减仓往往持续 2–5 个交易日而非一日完成。<b class=\"dk-main\">这是「低开反弹」不能演变为「V 型反转」的结构性原因</b>。"},
    {"name": "今晚 21:30 非农强于预期，坐实 12 月加息", "prob": "中", "impact": "高", "desc": "预期 +6.5 万 / 失业率 4.2%，ADP 已 +8.6 万（超预期 2.1 万）、ISM 55.5（超预期）。<b class=\"dk-risk\">若实际 &gt;10 万，则「加息」从尾部情景变为主流定价，全球高估值资产面临二次冲击</b>。<b class=\"dk-caution\">A股 因低通胀（CPI 0.9%）+ 宽货币（LPR 3.00%）而相对抗跌，但成长端仍将承压</b>。"},
    {"name": "韩国 SIDECAR 熔断后的程序化去杠杆跨市场传染", "prob": "中", "impact": "中高", "desc": "KOSPI 盘中一度 <b class=\"dk-risk\">-8.1%</b>，韩国交易所启动 <b>SIDECAR</b> 暂停 KOSPI / KOSDAQ 程序化卖盘（08:09 / 08:36）。<b class=\"dk-main\">SIDECAR 是「强制停止卖出」而非「流动性注入」，解除后卖压往往二次释放</b>；<b class=\"dk-caution\">软银 -16%、AI 对冲基金 VARA 10 月 -33% 说明杠杆端已在强制平仓</b>。"},
    {"name": "昨日「情绪脉冲」结构无机构承接，今日无人接盘", "prob": "中高", "impact": "中", "desc": "11-05 主力净额仅 <b class=\"dk-caution\">+5.84 亿</b>（前日 +375.32 亿，<b class=\"dk-risk\">-98.4%</b>）、国家队 ETF <b class=\"dk-risk\">-11.43 亿</b>（宽基全线转卖）、涨跌比 7.32 处统计尾部。<b class=\"dk-main\">普涨由情绪买盘推动，一旦低开，承接盘会迅速消失</b> —— 这与「机构筹码厚」的银行 / 公用形成对照。"},
    {"name": "技术面 16 席「下跌破位」，跳空低开形成新缺口", "prob": "高", "impact": "中", "desc": "<code>sector_tech</code>（11-05 · <code>kline_lag=0</code>）：趋势 <b>向上 0 / 上升回踩 2 / 下跌反弹 13 / 下跌破位 16</b>。<b class=\"dk-risk\">16 席处 downtrend，今日跳空低开将在这 16 席上形成新的向下缺口</b>，技术面无任何承接；<b class=\"dk-caution\">L4（传媒 / 计算机）在系统性杀估值面前不构成支撑</b>。"},
    {"name": "周五跨周末的事件风险溢价（非农 + 地缘 + AI 政策）", "prob": "高", "impact": "中", "desc": "今晚非农、民主党「蓝潮」后的数据中心政策细则、以及中东局势（WTI <b class=\"dk-up\">+2.16%</b> 至 90.02 反映供给担忧）三项均在周末发酵。<b class=\"dk-main\">周五尾盘的资金选择将显著偏向「降仓过周末」</b>，这是本档把仓位上限压到 20% 的时点性理由。"},
]

META = {
    "mode": "preopen",
    "direction": "中性偏空",
    "direction_confidence": "中高",
    "open_call": "低开反弹",
    "sh_index_close": 3689.91,
    "sh_open": 3646.57,
    "sh_high": 3701.59,
    "sh_low": 3646.57,
    "turnover_yi": 21179.5,
    "main_net_yi": 5.84,
    "sentiment_score": 74,
    "sentiment_state": "情绪过热预警",
    "position_range": "10%–20%（规则档 overheat [30,50]，本档向下偏离 10pct —— 超 ±5pct 偏离上限，已在 7.3 段显式记录理由：外部系统性冲击 + VIX 单日 +69.66% + 技术破位面 16 席，规则档位不适用于尾部节点）",
    "limit_up": 92,
    "limit_down": 2,
    "up_down_ratio": 7.32,
    "up_count": 3983,
    "down_count": 544,
    "flat_count": 79,
    "breadth_snapshot": "2026-11-05 22:49:33 · market_status=closed（收盘补抓终值；11-06 开盘实况另取腾讯实时 09:31:09）",
    "quadrant": {"A": 6, "B": 2, "C": 13, "D": 10},
    "quadrants": "共振 6 / 背离 2 / 暗线 13 / 双冷 10",
    "risk_level": "高",
    "news_window_days": 2,
    "hot_threshold": 16,
    "news_count": 589,
    "flow_date": "2026-11-05",
    "flow_stale_days": 0,
    "us_close_date": "2026-11-05",
    "us_cpi_yoy": 3.7,
    "us_core_cpi_yoy": 2.6,
    "us_gdp_qoq": 2.1,
    "us_core_pce_yoy": 3.1,
    "us_nonfarm_wan": None,
    "us_unemployment": None,
    "us_adp_wan": 8.6,
    "us_ism_mfg": 55.5,
    "vix": 28.18,
    "vix_date": "2026-11-05",
    "sector_tech_l4": 2,
    "sector_tech_l3": 2,
    "kline_last_date": "2026-11-05",
    "golden_diamond_count": 28,
    "national_team_etf_yi": -11.43,
    "open_actual_pct": -2.11,
    "open_actual_note": "上证 11-06 09:31:09 实时：3,625.23（-1.75%）· 开 3,612.15（-2.11%）· 低 3,610.20",
}

a = src["ai_synthesis"]
a["conclusion_first"] = CF
a["theme_resonance"] = THEMES
a["holding_map"] = HOLDING
a["t1_radar"] = T1
a["risks"] = RISKS
a["meta"] = META
a["disclaimer"] = ("个人学习用途，不构成投资建议；持仓段为其他专家持股参考（非本人），仅客观技术读数，不给加减仓建议。"
                   "投喂语料中的持仓表述一律为「投喂语料 · 非本人持仓」。美股数据口径 = 11/05 完整收盘（昨夜结算价），非盘中。")

src["data_date"] = "2026-11-05"
src["for_date"] = "2026-11-06"
src["generated"] = "2026-11-06 09:35"
src["mode"] = "preopen"
src["data_window"] = ("A股 11/05 完整收盘〔结算价〕 + 美股 11/05 完整收盘〔结算价 · 昨夜〕 + 日韩 11/06 早盘实时（08:40）"
                      " + 港股 11/05 收盘 + 商品 11/06 早间 + 美债 11/04（本机长期缺口） + A股 11/06 开盘实况（09:31）")

targets = [OUT / "v3_reasoning_latest.json", OUT / "v3_reasoning_2026-11-05.json",
           DEP / "v3_reasoning_latest.json", DEP / "v3_reasoning_2026-11-05.json"]
for t in targets:
    t.parent.mkdir(parents=True, exist_ok=True)
    with open(t, "w", encoding="utf-8") as f:
        json.dump(src, f, ensure_ascii=False, indent=2)
    print("  ✓", t)
print("cf", len(CF), "theme", len(THEMES), "t1", len(T1), "risks", len(RISKS))
