#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-11-20 盘前版 feed_review 产物（承接 11-19 数据日 → 指引 11-20）。
落盘：output/feed_review_latest.json + output/feed_review_2026-11-19.json + deploy 双份。"""
import io, json

P = 'output/feed_review_latest.json'
d = json.load(io.open(P, encoding='utf-8'))

win = json.load(io.open('output/window_latest.json', encoding='utf-8'))
ca = json.load(io.open('output/cross_analysis.json', encoding='utf-8'))
v3 = json.load(io.open('output/v3_reasoning_latest.json', encoding='utf-8'))
ai = v3['ai_synthesis']

summ = ca['summary']
quad_str = ' / '.join(str(summ[k]) for k in ['共振', '背离', '暗线', '双冷'])

d['data_date'] = '2026-11-19'
d['for_date'] = '2026-11-20'
d['generated_at'] = '2026-11-20 09:20'
d['source'] = 'local'
d['window'] = {
    'generated_at': win.get('generated_at'),
    'session': win.get('session'),
    'data_date': win.get('data_date'),
    'for_date': win.get('for_date'),
    'data_date_note': win.get('data_date_note', ''),
    'warnings': win.get('warnings', []),
    'span': win.get('span'),
    'span_days': win.get('span_days'),
    'display_days': win.get('display_days'),
    'display_text': win.get('display_text'),
    'span_is_weekend_cross': win.get('span_is_weekend_cross'),
    'span_text': win.get('span_text'),
    'carry': win.get('carry'),
}
d['feeds_days'] = win.get('display_days')
d['feed_count'] = 0
d['feeds'] = []
d['feeds_recent'] = []

d['cross_analysis'] = {
    'quadrant': quad_str,
    'summary': summ,
    'news_window': ca.get('news_window'),
    'flow_date': ca.get('flow_date'),
    'generated_at': '2026-11-20 08:45',
    'data_date': ca.get('data_date'),
}

d['prediction'] = {
    'bias': '偏空',
    'bias_score': -2,
    'reasons': [
        '外生锚由「结构分化」转为「系统性杀跌」：美股三大同跌超 2%（裂口收敛至 0.23pct）、VIX 盘中 28.75、亚太 -4.46% / -4.00%',
        'A股 11/19 跌停 105 家 / 涨跌比 0.13 / 情绪 15 / 成交 10,770.2 亿（-21.4%），三项同处恐慌档',
        '唯一强势方向（科创50 +1.83%）正是今晨外部被杀的方向：AMD 近 -8%、MRVL -4.86%、海力士 -6.51%、铠侠 -10%',
        '通信资金由 +35.37 转 -6.80 亿、计算机 -55.15 亿（最大单席流出）—— 科技链资金已先撤',
    ],
    't1_focus': [
        '跌停能否从 105 回到 60 家以内',
        '成交能否守住 10,000 亿（11/19 为 10,770.2 亿）',
        '科创50 1,220.38（11/19 日内低）是否失守',
        '韩存储双雄跌幅能否由 -6.5% 收窄至 -3% 以内',
        '今夜的美国初请失业金（预期 19.7 万）与 10Y 是否上破 5.20%',
    ],
}

# ai_synthesis：首条改为「投喂窗口」视角，其余沿用同一口径
cf = list(ai['conclusion_first'])
cf[0] = ('<b>本期投喂窗口（11/19 + 11/20）<span class="dk-caution">实到 0 件</span>，'
         '研判依据改为「公开新闻池 285 条 + 行情数据」</b> —— '
         '<b class="dk-caution">须先说明这一点，否则会把「无投喂」误读为「无观点分歧」</b>。'
         '同期结论：<b>偏空 / <span class="dk-data">高置信度</span> / <span class="dk-risk">低开偏弱</span> / '
         '仓位 10%–15% / 风险 <span class="dk-risk">高</span> / 四象限 <b>1 / 6 / 3 / 21</b></b>。'
         '昨夜美股 <span class="dk-risk">道 -2.19% / 标普 -2.02% / 纳 -2.25%</span>（三大同跌、裂口 0.23pct），'
         '今晨亚太 <span class="dk-risk">日经 -4.46% / KOSPI -4.00%</span>、'
         '<span class="dk-risk">SK 海力士 -6.51% / 三星 -4.98% / 铠侠 -10%</span>。'
         '<b class="dk-risk">外部由「结构切换」转为「系统性去杠杆」，且杀的正是 A股 昨日唯一强势的半导体链。</b>')

d['ai_synthesis'] = {
    'conclusion_first': cf,
    'theme_resonance': ai['theme_resonance'],
    'holding_map': ai['holding_map'],
    't1_radar': ai['t1_radar'],
    'risks': ai['risks'],
    'meta': {
        'mode': 'preopen',
        'direction': '偏空',
        'direction_confidence': '高',
        'open_call': '低开偏弱',
        'sh_index_close': 3577.62,
        'sh_open': 3583.12,
        'sh_high': 3584.28,
        'sh_low': 3547.94,
        'turnover_yi': 10770.2,
        'main_net_yi': -309.69,
        'sentiment_score': 15,
        'sentiment_state': '恐慌下跌',
        'position_range': ai['meta']['position_range'],
        'quadrant': {'resonance': 1, 'divergence': 6, 'hidden': 3, 'cold': 21},
        'quadrant_prev': {'resonance': 1, 'divergence': 1, 'hidden': 3, 'cold': 26},
        'risk_level': '高',
        'data_date': '2026-11-19',
        'for_date': '2026-11-20',
        'feed_count': 0,
        'feed_days': ['2026-11-19', '2026-11-20'],
    },
    'disclaimer': ai['disclaimer'],
}

s = json.dumps(d, ensure_ascii=False, indent=2)
for p in ['output/feed_review_latest.json',
          'output/feed_review_2026-11-19.json',
          'deploy/output/feed_review_latest.json',
          'deploy/output/feed_review_2026-11-19.json']:
    io.open(p, 'w', encoding='utf-8').write(s)
    print('written', p, len(s))
print('quad', quad_str)
