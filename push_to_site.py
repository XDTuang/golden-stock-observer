#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 推送脚本（复盘结果 → 主站每日复盘页）
==================================================
将 output/feed_review_latest.json 同步到主站 deploy/output/，
供前端「每日复盘」tab 的投喂复盘板块动态 fetch。

用法:
  python push_to_site.py            # 同步 feed_review_latest.json 到 deploy/output/
"""
import os, sys, json, shutil, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "output", "feed_review_latest.json")
DST_DIR = os.path.join(BASE, "deploy", "output")


def main():
    if not os.path.exists(SRC):
        print(f"❌ 未找到 {SRC}，请先运行 daily_feed_review.py")
        sys.exit(1)

    d = json.load(open(SRC, encoding="utf-8"))
    os.makedirs(DST_DIR, exist_ok=True)
    dst = os.path.join(DST_DIR, "feed_review_latest.json")
    shutil.copy2(SRC, dst)

    print(f"✅ 已推送: {dst}")
    print(f"   数据日期 {d.get('data_date')} | 投喂 {d.get('feed_count')} 条 | 预测 {d.get('prediction', {}).get('bias')}")
    print(f"   前端入口: 每日复盘 tab → 投喂复盘板块（动态 fetch output/feed_review_latest.json）")


if __name__ == "__main__":
    main()
