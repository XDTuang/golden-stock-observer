#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前验证：检查主链路产物 freshness 是否已更新到指定交易日。"""
import json, sys, os

def check(path, key="freshness"):
    if not os.path.exists(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    fr = d.get(key, {})
    if key == "freshness":
        return fr.get("latest_data_date"), fr.get("status"), fr.get("expected_date")
    return fr

f = "deploy/signals_full.json"
r = check(f)
if r:
    print(f"✅ signals_full.json latest={r[0]} status={r[1]} expected={r[2]}")
    if r[0] == "2026-08-31":
        print("→ 今日数据已就绪，可以部署")
        sys.exit(0)
    else:
        print("❌ 数据未更新到 8/31，检查 update_data.sh 输出")
        sys.exit(1)
else:
    print(f"❌ {f} 不存在")
    sys.exit(1)
