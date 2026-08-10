#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回补7月缺失的机游共振龙虎榜数据。

用法:
  python3 backfill_lhb_july.py                # 回补所有缺失的7月交易日
  python3 backfill_lhb_july.py --date 07-10   # 只回补指定日期
  python3 backfill_lhb_july.py --dry-run      # 仅列出缺失日期，不获取
"""
import sys, os, json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import westock_lhb_parser as w

CAL_PATH = w.OUTPUT_FILE  # lh_calendar.json

# 7月所有交易日（含周末可能有数据的 07-18/25）
JULY_TRADING = [
    '2026-07-01', '2026-07-02', '2026-07-03',
    '2026-07-06', '2026-07-07', '2026-07-08', '2026-07-09', '2026-07-10',
    '2026-07-13', '2026-07-14', '2026-07-15', '2026-07-16', '2026-07-17',
    '2026-07-18',
    '2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23',
    '2026-07-24', '2026-07-25',
]


def main():
    dry_run = '--dry-run' in sys.argv
    single_target = None
    for a in sys.argv[1:]:
        if a.startswith('--date='):
            single_target = a.split('=', 1)[1]
        elif not a.startswith('--'):
            single_target = a

    # 加载现有日历
    cal = {}
    if os.path.exists(CAL_PATH):
        with open(CAL_PATH, encoding='utf-8') as f:
            cal = json.load(f)

    # 确定要获取的日期
    if single_target:
        if single_target.startswith('07-'):
            single_target = f'2026-{single_target}'
        dates_to_fetch = [single_target]
    else:
        dates_to_fetch = [d for d in JULY_TRADING if d not in cal]

    print(f"现有日历: {len(cal)} 天")
    print(f"需要回补: {len(dates_to_fetch)} 天")
    for d in dates_to_fetch:
        exists = '已有' if d in cal else '缺失'
        print(f"  {d} [{exists}]")

    if not dates_to_fetch:
        print("✅ 无需回补，所有7月交易日均已存在")
        return

    if dry_run:
        print("\n⏹️  --dry-run 模式，退出")
        return

    # 逐日获取
    success = 0
    fail = 0
    for date_str in dates_to_fetch:
        try:
            print(f"\n📥 获取 {date_str}...")
            day_stocks = w.generate_calendar(date_str)
            cal[date_str] = day_stocks
            print(f"  ✅ {date_str}: {len(day_stocks)} 只股票")
            success += 1
        except Exception as e:
            print(f"  ❌ {date_str} 获取失败: {e}")
            fail += 1

    # 保存（保留所有数据，不做 KEEP_DAYS 裁剪）
    with open(CAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)

    # 验证
    with open(CAL_PATH, 'r') as f:
        verify = json.load(f)
    print(f"\n{'='*50}")
    print(f"✅ 回补完成: 成功 {success}, 失败 {fail}")
    print(f"文件: {CAL_PATH}")
    print(f"共 {len(verify)} 天, {sum(len(v) for v in verify.values())} 只股票")
    print(f"日期范围: {sorted(verify.keys())}")


if __name__ == '__main__':
    main()
