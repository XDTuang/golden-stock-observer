#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机游共振日历 —— 使用东方财富龙虎榜接口获取数据（云端化根治）

v2 改动:
  - 数据源从 westock-data（本机 WorkBuddy skill，云端不存在）切换为
    东方财富 datacenter 龙虎榜接口（全球可达）
  - 机构/游资分类规则: 席位名称含「机构/通专用」→机构，含「营业部/分公司/总部」→游资
  - 输出格式与原版完全一致（code/name/inst_net/retail_net/total_net/category/reason/has_hotmoney）

数据源:
  - RPT_DAILYBILLBOARD_DETAILS  龙虎榜每日详情（个股汇总: 代码/名称/净买入额）
  - RPT_BILLBOARD_DAILYDETAILSBUY 龙虎榜买入席位明细（席位: 名称/买入/卖出/净额）
"""
import json
import os
import time
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'lh_calendar.json')

# 东财龙虎榜 datacenter 接口
EM_DC_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)",
           "Referer": "https://data.eastmoney.com/"}


def _dc_get(report_name: str, flt: str, page: int = 1, size: int = 500, sort_col: str = "", sort_dir: int = -1) -> list:
    """调用东财 datacenter 通用接口，返回 data 列表（自动分页）"""
    if requests is None:
        return []
    all_data = []
    for attempt in range(3):
        try:
            params = {
                "reportName": report_name,
                "columns": "ALL",
                "filter": flt,
                "pageNumber": page,
                "pageSize": size,
            }
            if sort_col:
                params["sortColumns"] = sort_col
                params["sortTypes"] = sort_dir
            r = requests.get(EM_DC_URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            j = r.json()
            result = j.get("result") or {}
            data = result.get("data") or []
            count = result.get("count") or len(data)
            all_data = data
            # 分页拉取
            pages = result.get("pages") or 1
            if pages > 1:
                for p in range(2, pages + 1):
                    params["pageNumber"] = p
                    r2 = requests.get(EM_DC_URL, params=params, headers=HEADERS, timeout=20)
                    r2.raise_for_status()
                    j2 = r2.json()
                    all_data.extend((j2.get("result") or {}).get("data") or [])
            return all_data
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️ 东财龙虎榜接口失败: {type(e).__name__}: {str(e)[:100]}", file=__import__('sys').stderr)
                return []
            time.sleep(1 + attempt)
    return []


def _is_institution(seat_name: str) -> bool:
    """判断席位是否为机构（机构专用 / 深沪股通专用 / 机构投资者）"""
    if not seat_name:
        return False
    return ("机构" in seat_name) or ("通专用" in seat_name)


def _is_hotmoney(seat_name: str) -> bool:
    """判断席位是否为游资（营业部 / 分公司 / 总部等非机构非自然人的交易席位）"""
    if not seat_name:
        return False
    if _is_institution(seat_name):
        return False
    if ("自然人" in seat_name) or ("中小投资者" in seat_name):
        return False
    return ("营业部" in seat_name) or ("分公司" in seat_name) or ("总部" in seat_name) or ("证券" in seat_name)


def classify_six(inst_net, retail_net):
    """六维分类（金额单位: 亿元）—— 与原版保持一致"""
    if inst_net < -1.0:
        return '机构大卖'
    if inst_net >= 4.0:
        return '机构独买'
    if inst_net > 0.8 and retail_net > 0.8:
        return '纯共振'
    if inst_net > 0.8 and 0.5 <= retail_net <= 0.8:
        return '准共振'
    if inst_net < 4.0 and retail_net > 0:
        return '标X'
    return '其他'


def generate_calendar(date_str):
    """获取单日龙虎榜数据并生成机游共振日历"""
    print(f"获取 {date_str} 龙虎榜数据（东财）...")

    flt = f"(TRADE_DATE='{date_str}')"

    # 1. 个股汇总（代码→名称 + 净买入额）
    details = _dc_get("RPT_DAILYBILLBOARD_DETAILS", flt, sort_col="BILLBOARD_NET_AMT")
    name_map = {}
    net_map = {}
    for x in details:
        code = str(x.get("SECURITY_CODE") or "")
        if not code:
            continue
        name_map[code] = x.get("SECURITY_NAME_ABBR") or code
        try:
            net_map[code] = float(x.get("BILLBOARD_NET_AMT") or 0)
        except (ValueError, TypeError):
            net_map[code] = 0.0

    # 2. 席位明细（按股票聚合机构买入额 + 游资买入额）
    seats = _dc_get("RPT_BILLBOARD_DAILYDETAILSBUY", flt, sort_col="BUY")
    inst_buy_map = {}
    hotmoney_buy_map = {}
    for x in seats:
        code = str(x.get("SECURITY_CODE") or "")
        seat_name = str(x.get("OPERATEDEPT_NAME") or "")
        try:
            buy = float(x.get("BUY") or 0)
        except (ValueError, TypeError):
            buy = 0.0
        if not code:
            continue
        if _is_institution(seat_name):
            inst_buy_map[code] = inst_buy_map.get(code, 0.0) + buy
        elif _is_hotmoney(seat_name):
            hotmoney_buy_map[code] = hotmoney_buy_map.get(code, 0.0) + buy

    # 3. 合并生成 day_stocks
    all_codes = set(list(name_map.keys()) + list(inst_buy_map.keys()) + list(hotmoney_buy_map.keys()))
    day_stocks = []
    for code in all_codes:
        name = name_map.get(code, code)
        inst_buy = inst_buy_map.get(code, 0.0)
        hotmoney_buy = hotmoney_buy_map.get(code, 0.0)
        total_net = net_map.get(code, 0.0)

        inst_net = inst_buy / 1e8      # 机构买入额 -> 亿
        total_net_e = total_net / 1e8  # 净买入额 -> 亿
        retail_net = total_net_e - inst_net  # 近似游资净买额（与原版口径一致）

        category = classify_six(inst_net, retail_net)
        has_hotmoney = hotmoney_buy > 0
        reason = '游资+机构' if has_hotmoney else '仅机构'

        day_stocks.append({
            'code': code,
            'name': name,
            'inst_net': round(inst_net, 2),
            'retail_net': round(retail_net, 2),
            'total_net': round(total_net_e, 2),
            'category': category,
            'reason': reason,
            'has_hotmoney': has_hotmoney,
        })

    print(f"机构参与: {len(inst_buy_map)} 只 | 游资参与: {len(hotmoney_buy_map)} 只 | 总计: {len(day_stocks)} 只")

    from collections import Counter
    cat_count = Counter(s['category'] for s in day_stocks)
    for cat, cnt in sorted(cat_count.items()):
        print(f"  {cat}: {cnt}只")

    return day_stocks


def main():
    """获取最近N天的龙虎榜数据"""
    import datetime

    calendar = {}
    today = datetime.datetime.now()

    dates = []
    for i in range(7):
        date = today - datetime.timedelta(days=i)
        if date.weekday() < 5:
            dates.append(date.strftime('%Y-%m-%d'))

    print(f"将获取以下日期的数据: {dates}")

    for date_str in dates:
        try:
            day_stocks = generate_calendar(date_str)
            calendar[date_str] = day_stocks
            print(f"✅ {date_str}: {len(day_stocks)} 只股票")
        except Exception as e:
            print(f"❌ {date_str} 获取失败: {e}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 数据已保存到: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'r') as f:
        verify = json.load(f)
    print(f"验证通过: {len(verify)} 天, {sum(len(v) for v in verify.values())} 只股票")
    print(f"日期范围: {sorted(verify.keys())}")


if __name__ == '__main__':
    main()
