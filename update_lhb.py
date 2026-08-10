#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新机游共振（龙虎榜）日历：只补指定日期（默认今天），merge 进现有 lh_calendar.json。
保留最近 8 个交易日，避免文件无限膨胀。复用 westock_lhb_parser 的解析与分类逻辑，保证格式一致。
用法:
  python3 update_lhb.py                 # 补今天
  python3 update_lhb.py 2026-07-07     # 补指定日期
"""
import sys
import os
import json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import westock_lhb_parser as w

KEEP_DAYS = 30  # 滚动保留最近 N 个交易日（原8天导致每月前半月数据被清）


def main():
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    cal_path = w.OUTPUT_FILE
    cal = {}
    if os.path.exists(cal_path):
        with open(cal_path, encoding='utf-8') as f:
            cal = json.load(f)

    print(f"现有日历: {len(cal)} 天，最新 {max(cal.keys()) if cal else '无'}")
    day = w.generate_calendar(date_str)
    cal[date_str] = day

    # 滚动保留最近 KEEP_DAYS 天
    keys = sorted(cal.keys(), reverse=True)[:KEEP_DAYS]
    cal = {k: cal[k] for k in keys}

    with open(cal_path, 'w', encoding='utf-8') as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)

    print(f"✅ LHB 日历已更新: +{date_str} ({len(day)}只) | 现 {len(cal)} 天: {keys}")


if __name__ == '__main__':
    main()
