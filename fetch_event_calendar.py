#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重要事件日历 —— 按月缓存财经事件数据（含今值/前值/预期）

数据源：华尔街见闻财经日历接口
  GET https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas?start={unix秒}&end={unix秒}
  Header: User-Agent + Referer: https://wallstreetcn.com/calendar
  返回 data.items[]，字段含 actual(今值)/forecast(预期)/previous(前值)/revised(修正值)/
  importance(1-4星)/country/title/period(报告期)/foresight(前瞻解读)/calendar_type(FD=宏观数据,FE=前瞻事件)

缓存机制：每自然月一份 output/event_calendar_{YYYY-MM}.json（与 lh_calendar.json 同模式）。
字段：
  - date: 事件日期（YYYY-MM-DD）
  - time: 具体时间（如 "20:30"，空表示全天）
  - name: 事件名称（title）
  - country/region: 国家/地区
  - category: 类别（宏观数据 / 事件）
  - importance: 重要性（high/medium/low，华尔街见闻 4星/3星 → high）
  - has_data: 是否已公布（actual 非空）
  - published_at: 事件日期（has_data=true 时填）
  - actual_value: 今值
  - previous_value: 前值
  - forecast_value: 预期值
  - description: 报告期/修正值/前瞻解读
"""
import json
import os
import datetime
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, 'output')

WSCN_API = "https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas"
WSCN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://wallstreetcn.com/calendar",
}
# 北京时间（UTC+8）
_TZ = datetime.timezone(datetime.timedelta(hours=8))


def _wscn_fetch(start_ts, end_ts):
    """抓取华尔街见闻财经日历，返回事件列表；失败返回 None。"""
    url = f"{WSCN_API}?start={start_ts}&end={end_ts}"
    req = urllib.request.Request(url, headers=WSCN_HEADERS)
    last_err = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if data.get("code") == 20000:
                return (data.get("data") or {}).get("items") or []
            last_err = f"接口返回 code={data.get('code')} message={data.get('message')}"
        except Exception as e:
            last_err = str(e)
    print(f"  ⚠️  华尔街见闻日历抓取失败: {last_err}")
    return None


def _build_description(x):
    """构建事件说明：报告期 + 修正值 + 前瞻解读（截断）。"""
    parts = []
    period = (x.get("period") or "").strip()
    revised = (x.get("revised") or "").strip()
    if period:
        parts.append(f"报告期:{period}")
    if revised:
        parts.append(f"修正值:{revised}")
    foresight = (x.get("foresight") or "").strip()
    if foresight:
        parts.append(foresight[:150])
    return "；".join(p for p in parts if p)


def fetch_from_api(year, month):
    """从华尔街见闻财经日历接口抓取某月重要事件。返回 {date: [event, ...]}。

    失败或空数据时返回 None（由调用方决定是否回退预置数据）。
    """
    first = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=_TZ)
    if month == 12:
        last = datetime.datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=_TZ)
    else:
        last = datetime.datetime(year, month + 1, 1, 0, 0, 0, tzinfo=_TZ)
    start_ts = int(first.timestamp())
    end_ts = int(last.timestamp())

    items = _wscn_fetch(start_ts, end_ts)
    if not items:
        return None

    events = {}
    total_raw = len(items)
    total_kept = 0
    now = datetime.datetime.now(_TZ)

    for x in items:
        imp = 0
        try:
            imp = int(x.get("importance") or 0)
        except Exception:
            imp = 0
        if imp < 3:
            continue  # 只保留重要（3星）及以上事件

        pub_ts = x.get("public_date")
        try:
            pub = datetime.datetime.fromtimestamp(int(pub_ts), tz=_TZ)
            day = pub.strftime("%Y-%m-%d")
            hhmm = pub.strftime("%H:%M") if (pub.hour or pub.minute) else ""
        except Exception:
            day, hhmm = "", ""

        actual = (x.get("actual") or "").strip()
        calendar_type = x.get("calendar_type") or ""
        is_data = calendar_type == "FD"
        # 宏观数据：今值已公布 → 已发布；事件：日期已过 → 已发生
        if is_data:
            has_data = bool(actual)
        else:
            has_data = pub < now if pub else False
        category = "宏观数据" if is_data else "事件"

        events.setdefault(day, []).append({
            "time": hhmm,
            "name": (x.get("title") or x.get("event") or "").strip(),
            "country": (x.get("country") or "").strip(),
            "region": "",
            "category": category,
            "importance": "high",
            "has_data": has_data,
            "published_at": day if has_data else "",
            "actual_value": actual,
            "previous_value": (x.get("previous") or "").strip(),
            "forecast_value": (x.get("forecast") or "").strip(),
            "description": _build_description(x),
        })
        total_kept += 1

    # 按时间排序
    for day in events:
        events[day].sort(key=lambda e: (e.get("time") or "99:99"))

    print(f"  华尔街见闻: 原始 {total_raw} 条 → 保留重要({total_kept}) 条")
    return events if events else None


# ========== 预置事件清单（2026-08，兜底用，接口失败时启用） ==========
PRESET_EVENTS_2026_08 = {
    "2026-08-01": [],  # 周六
    "2026-08-02": [],  # 周日
    "2026-08-03": [
        {"time": "09:45", "name": "中国:7月财新制造业PMI", "country": "中国", "region": "财新/Markit", "category": "中国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-03T09:45",
         "actual_value": "52.1", "previous_value": "51.7", "forecast_value": "51.9",
         "description": "财新制造业PMI 7月数据"},
        {"time": "22:00", "name": "美国:7月ISM制造业PMI", "country": "美国", "region": "美国供应管理协会", "category": "美国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-03T22:00",
         "actual_value": "52.4", "previous_value": "53.3", "forecast_value": "52.8",
         "description": "美国7月ISM制造业PMI"},
    ],
    "2026-08-04": [
        {"time": "", "name": "新股申购:天承科技", "country": "中国", "region": "深交所", "category": "新股申购", "importance": "low",
         "has_data": False, "description": "天承科技(688787) 网上发行申购日"}
    ],
    "2026-08-05": [
        {"time": "20:15", "name": "美国:7月ADP就业人数变动", "country": "美国", "region": "ADP", "category": "美国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-05T20:15",
         "actual_value": "+7.2万", "previous_value": "+9.8万", "forecast_value": "+8.5万",
         "description": "美国7月ADP私营部门就业(小非农)"},
    ],
    "2026-08-07": [
        {"time": "20:30", "name": "美国:7月非农就业人口变动", "country": "美国", "region": "美国劳工部", "category": "美国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-07T20:30",
         "actual_value": "-2.3万", "previous_value": "+5.7万", "forecast_value": "+8万",
         "description": "美国7月非农就业报告(含失业率/平均时薪)"},
    ],
    "2026-08-09": [
        {"time": "09:30", "name": "中国:7月CPI同比", "country": "中国", "region": "国家统计局", "category": "中国数据", "importance": "high",
         "has_data": False, "previous_value": "+1.0%",
         "description": "中国7月CPI/PPI数据，国家统计局发布"},
    ],
    "2026-08-11": [
        {"time": "12:30", "name": "澳洲联储:利率决议", "country": "澳大利亚", "region": "澳洲联储", "category": "央行", "importance": "high",
         "has_data": True, "published_at": "2026-08-11T12:30",
         "actual_value": "维持利率不变", "previous_value": "4.10%", "forecast_value": "4.10%",
         "description": "澳洲联储8月利率决议"},
    ],
    "2026-08-12": [
        {"time": "20:30", "name": "美国:7月CPI同比", "country": "美国", "region": "美国劳工部", "category": "美国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-12T20:30",
         "actual_value": "+3.4%", "previous_value": "+3.5%", "forecast_value": "+3.4%",
         "description": "美国7月CPI同比"},
        {"time": "20:30", "name": "美国:7月核心CPI同比", "country": "美国", "region": "美国劳工部", "category": "美国数据", "importance": "high",
         "has_data": True, "published_at": "2026-08-12T20:30",
         "actual_value": "+2.5%", "previous_value": "+2.6%", "forecast_value": "+2.5%",
         "description": "美国7月核心CPI同比"},
    ],
    "2026-08-17": [
        {"time": "10:00", "name": "中国:7月规模以上工业增加值", "country": "中国", "region": "国家统计局", "category": "中国数据", "importance": "high",
         "has_data": False, "previous_value": "+5.3%",
         "description": "中国7月规模以上工业增加值同比"},
        {"time": "10:00", "name": "中国:7月社会消费品零售总额", "country": "中国", "region": "国家统计局", "category": "中国数据", "importance": "high",
         "has_data": False, "previous_value": "+1.0%",
         "description": "中国7月社会消费品零售总额同比"},
    ],
    "2026-08-20": [
        {"time": "09:15", "name": "中国:8月LPR报价", "country": "中国", "region": "中国人民银行", "category": "央行/LPR", "importance": "high",
         "has_data": False, "description": "中国8月LPR(贷款市场报价利率)1年期/5年期"},
        {"time": "02:00", "name": "美联储公布货币政策会议纪要", "country": "美国", "region": "美联储", "category": "FOMC", "importance": "high",
         "has_data": False, "description": "美联储7月FOMC会议纪要公布"},
    ],
    "2026-08-27": [
        {"time": "", "name": "杰克逊霍尔全球央行年会", "country": "美国", "region": "堪萨斯联储", "category": "央行", "importance": "high",
         "has_data": False, "description": "杰克逊霍尔全球央行年会(8/27-29)"},
    ],
    "2026-08-31": [
        {"time": "09:30", "name": "中国:8月官方制造业PMI", "country": "中国", "region": "国家统计局", "category": "中国数据", "importance": "high",
         "has_data": False, "description": "中国8月官方制造业PMI/非制造业PMI"},
    ],
}


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

    # 接口失败/空数据 → 回退预置数据（仅 2026-08 有预置）
    source = "wallstreetcn"
    if not events and month_str == "2026-08":
        print("  ⚠️  华尔街见闻接口无数据，回退预置事件清单")
        events = PRESET_EVENTS_2026_08
        source = "preset"
    elif not events:
        events = {}
        source = "empty"

    # 统计已发布/未发布事件
    published_count = sum(1 for day_events in events.values() for e in day_events if e.get('has_data'))
    total_count = sum(len(day_events) for day_events in events.values())
    print(f"  事件总数: {total_count} | 已发布: {published_count} | 数据源: {source}")

    result = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'month': month_str,
        'source': source,
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
