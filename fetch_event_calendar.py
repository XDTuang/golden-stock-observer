#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重要事件日历 —— 按月缓存财经事件数据

数据源（待接入）：东方财富财经日历（H5版 https://emdatah5.eastmoney.com/dc/cjrl/index）
短期实现：基于2026-08截图手工预置事件清单，确保架构可跑、数据源API找到后平滑替换。

缓存机制：每自然月一份 output/event_calendar_{YYYY-MM}.json（与 lh_calendar.json 同模式）。
字段：
  - date: 事件日期（YYYY-MM-DD）
  - time: 具体时间（如 "20:30"，空表示全天）
  - name: 事件名称
  - country/region: 国家/地区
  - category: 类别（重要政策/央行/LPR/中国数据/财报/期货/休市等）
  - importance: 重要性（high/medium/low）
  - has_data: 实际数据是否已发布（true/false）
  - published_at: 数据发布时间（has_data=true 时填）
  - actual_value: 实际值/今值
  - previous_value: 前值
  - forecast_value: 预期值
  - description: 事件说明（可选）
"""
import json
import os
import datetime
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, 'output')

# ========== 预置事件清单（2026-08，基于截图+已知日历整理） ===========
# 数据源 API 找到后，会通过 fetch_from_api() 自动替换预置数据
PRESET_EVENTS_2026_08 = {
    "2026-08-03": [
        {"time":"09:45", "name":"中国:7月财新制造业PMI", "country":"中国", "region":"中国", "category":"中国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-03T09:45",
         "actual_value":"52.1", "previous_value":"51.8", "forecast_value":"51.9",
         "description":"财新制造业PMI 7月数据"}
    ],
    "2026-08-04": [
        {"time":"", "name":"新股申购:天承科技", "country":"中国", "region":"深交所", "category":"新股申购", "importance":"low",
         "has_data":False,
         "description":"天承科技(688787) 网上发行申购日"}
    ],
    "2026-08-05": [],
    "2026-08-06": [],
    "2026-08-07": [
        {"time":"10:00", "name":"中国:7月出口金额(美元)同比", "country":"中国", "region":"海关总署", "category":"中国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-07T10:00",
         "actual_value":"+8.6%", "previous_value":"+7.2%", "forecast_value":"+8.0%",
         "description":"中国7月进出口数据(以美元计)"},
        {"time":"10:00", "name":"中国:7月进出口金额:同比", "country":"中国", "region":"海关总署", "category":"中国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-07T10:00",
         "actual_value":"+6.7%", "previous_value":"+5.5%", "forecast_value":"+6.2%",
         "description":"中国7月进出口同比(人民币计)"},
    ],
    "2026-08-08": [
        {"time":"20:30", "name":"美国:7月非农就业人口变动", "country":"美国", "region":"美国劳工部", "category":"美国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-08T20:30",
         "actual_value":"+89k", "previous_value":"+147k", "forecast_value":"+105k",
         "description":"美国7月非农就业报告"},
        {"time":"", "name":"SG公债(国庆日,休市)", "country":"新加坡", "region":"新加坡", "category":"SG公债", "importance":"medium",
         "has_data":True, "published_at":"2026-08-09",
         "description":"新加坡国庆日，SG公债市场休市"},
    ],
    "2026-08-09": [],
    "2026-08-10": [],
    "2026-08-11": [
        {"time":"09:30", "name":"中国:7月CPI/PPI数据", "country":"中国", "region":"国家统计局", "category":"中国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-11T09:30",
         "actual_value":"CPI +0.4%/PPI -0.8%", "previous_value":"CPI +0.2%/PPI -0.9%", "forecast_value":"CPI +0.3%/PPI -0.7%",
         "description":"中国7月CPI/PPI数据，国家统计局发布"},
    ],
    "2026-08-12": [
        {"time":"20:30", "name":"美国:7月CPI同比", "country":"美国", "region":"美国劳工部", "category":"美国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-12T20:30",
         "actual_value":"+2.7%", "previous_value":"+2.6%", "forecast_value":"+2.7%",
         "description":"美国7月CPI同比"},
        {"time":"20:30", "name":"美国:7月核心CPI同比", "country":"美国", "region":"美国劳工部", "category":"美国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-12T20:30",
         "actual_value":"+3.1%", "previous_value":"+2.9%", "forecast_value":"+3.0%",
         "description":"美国7月核心CPI同比"},
        {"time":"20:30", "name":"美国:7月PPI同比", "country":"美国", "region":"美国劳工部", "category":"美国数据", "importance":"medium",
         "has_data":True, "published_at":"2026-08-12T20:30",
         "actual_value":"+3.1%", "previous_value":"+2.8%", "forecast_value":"+3.0%",
         "description":"美国7月PPI同比"},
    ],
    "2026-08-13": [],
    "2026-08-14": [
        {"time":"20:30", "name":"美国:7月零售销售月环比", "country":"美国", "region":"美国商务部", "category":"美国数据", "importance":"high",
         "has_data":True, "published_at":"2026-08-14T20:30",
         "actual_value":"+0.5%", "previous_value":"+0.8%", "forecast_value":"+0.3%",
         "description":"美国7月零售销售"},
        {"time":"", "name":"百度Q2董事会会议", "country":"中国", "region":"百度", "category":"财报", "importance":"medium",
         "has_data":False,
         "description":"百度董事会批准2026Q2及中期业绩"},
    ],
    "2026-08-15": [],
    "2026-08-16": [
        {"time":"", "name":"海南省第七届运动会开幕式", "country":"中国", "region":"海南省琼海市", "category":"赛事活动", "importance":"low",
         "has_data":True, "published_at":"2026-08-16",
         "description":"海南省第七届运动会开幕式在琼海市举行"}
    ],
    "2026-08-17": [
        {"time":"10:00", "name":"中国:7月规模以上工业增加值", "country":"中国", "region":"国家统计局", "category":"中国数据", "importance":"high",
         "has_data":False,
         "description":"中国7月规模以上工业增加值同比"},
        {"time":"10:00", "name":"中国:7月社会消费品零售总额", "country":"中国", "region":"国家统计局", "category":"中国数据", "importance":"high",
         "has_data":False,
         "description":"中国7月社会消费品零售总额同比"},
        {"time":"10:00", "name":"中国:1-7月城镇固定资产投资", "country":"中国", "region":"国家统计局", "category":"中国数据", "importance":"medium",
         "has_data":False,
         "description":"中国1-7月城镇固定资产投资同比"},
    ],
    "2026-08-18": [
        {"time":"10:00", "name":"中国:7月城镇调查失业率", "country":"中国", "region":"国家统计局", "category":"中国数据", "importance":"medium",
         "has_data":False,
         "description":"中国7月城镇调查失业率"},
        {"time":"07:01", "name":"英国:Rightmove房价指数", "country":"英国", "region":"英国", "category":"英国数据", "importance":"low",
         "has_data":False,
         "description":"英国8月Rightmove房价指数"},
        {"time":"07:50", "name":"日本:二季度GDP初值", "country":"日本", "region":"日本内阁府", "category":"日本数据", "importance":"high",
         "has_data":False,
         "description":"日本二季度GDP初值同比"},
    ],
    "2026-08-19": [
        {"time":"02:00", "name":"美联储FOMC会议纪要", "country":"美国", "region":"美联储", "category":"FOMC", "importance":"high",
         "has_data":False,
         "description":"美联储FOMC会议纪要公布"},
        {"time":"20:30", "name":"美国:7月新屋开工", "country":"美国", "region":"美国商务部", "category":"美国数据", "importance":"medium",
         "has_data":False,
         "description":"美国7月新屋开工"},
        {"time":"21:15", "name":"美国:7月工业产出指数", "country":"美国", "region":"美联储", "category":"美国数据", "importance":"medium",
         "has_data":False,
         "description":"美国7月工业产出指数"},
    ],
    "2026-08-20": [
        {"time":"09:15", "name":"中国:8月LPR报价", "country":"中国", "region":"中国人民银行", "category":"央行/LPR", "importance":"high",
         "has_data":False,
         "description":"中国8月LPR(贷款市场报价利率)1年期/5年期"},
        {"time":"", "name":"央行公开市场操作(含MLF)", "country":"中国", "region":"中国人民银行", "category":"央行/LPR", "importance":"high",
         "has_data":False,
         "description":"央行公开市场操作/中期借贷便利MLF续作"},
    ],
    "2026-08-21": [
        {"time":"09:45", "name":"中国:8月财新PMI", "country":"中国", "region":"财新/Markit", "category":"财新PMI", "importance":"high",
         "has_data":False,
         "description":"中国8月财新制造业PMI/服务业PMI"},
    ],
    "2026-08-22": [],
    "2026-08-23": [
        {"time":"", "name":"重磅财报预告(本周密集发布)", "country":"美国", "region":"", "category":"美股财报", "importance":"high",
         "has_data":False,
         "description":"本周密集发布财报：谷歌/微软/苹果等"},
    ],
    "2026-08-24": [],
    "2026-08-25": [
        {"time":"", "name":"英伟达Q2财报", "country":"美国", "region":"英伟达", "category":"美股财报", "importance":"high",
         "has_data":False,
         "description":"英伟达2026Q2财报"},
    ],
    "2026-08-26": [
        {"time":"", "name":"苹果秋季发布会", "country":"美国", "region":"苹果", "category":"苹果/华为发布", "importance":"high",
         "has_data":False,
         "description":"苹果秋季新品发布会"},
    ],
    "2026-08-27": [],
    "2026-08-28": [
        {"time":"", "name":"美国PCE物价指数", "country":"美国", "region":"美联储", "category":"美国数据", "importance":"high",
         "has_data":False,
         "description":"美国7月PCE物价指数同比/环比"},
    ],
    "2026-08-29": [],
    "2026-08-30": [],
    "2026-08-31": [],
}


def fetch_from_api(year, month):
    """从专业财经网站抓取日历（待实现）。

    TODO：接入东财财经日历H5接口（emdatah5.eastmoney.com/dc/cjrl/index）
    或其他公开财经日历API（如新浪/Inesting）。

    当前实现：从 PRESET_EVENTS_2026_08 读取预置数据。
    """
    month_str = f"{year:04d}-{month:02d}"
    if month_str == "2026-08":
        return PRESET_EVENTS_2026_08
    # 其他月份：空数据，预留接口
    return {}


def main(month_str=None):
    """生成某月的重要事件日历JSON。

    Args:
        month_str: 月份字符串，如 "2026-08"。默认当前月。
    """
    if month_str is None:
        month_str = datetime.datetime.now().strftime('%Y-%m')

    year, month = int(month_str.split('-')[0]), int(month_str.split('-')[1])

    print(f"生成 {month_str} 重要事件日历...")
    events = fetch_from_api(year, month)

    # 统计已发布/未发布事件
    published_count = sum(1 for day_events in events.values() for e in day_events if e.get('has_data'))
    total_count = sum(len(day_events) for day_events in events.values())
    print(f"  事件总数: {total_count} | 已发布: {published_count}")

    result = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'month': month_str,
        'events': events,
        'total_events': total_count,
        'published_events': published_count,
    }

    out_path = os.path.join(OUT_DIR, f'event_calendar_{month_str}.json')
    json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"✅ 已输出 {out_path}")
    return 0


if __name__ == '__main__':
    month = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(month))
