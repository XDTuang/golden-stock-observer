#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""观测股推演同步：把最新 obs_deduce_<T>.json 复制为 output/obs_deduce_latest.json（入库，前端可 fetch）

背景：obs_deduce（重点观测股推演）由本机 agent 生成，归档在 data/daily_review_history/<T>/（不入库）。
前端每日复盘 tab 需要读取 → 同步一份到 output/（根 + deploy/output）供页面 fetch。

用法:
  python3 sync_obs_deduce.py            # 找最新 obs_deduce 并同步
  python3 sync_obs_deduce.py --force    # 即使无最新也重写（清空占位）
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
HIST = BASE / "data" / "daily_review_history"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    files = sorted(HIST.glob("*/obs_deduce_*.json"))
    if not files:
        print("未找到 obs_deduce（本机 agent 尚未生成推演）")
        if args.force:
            for p in (BASE / "output" / "obs_deduce_latest.json",
                      BASE / "deploy" / "output" / "obs_deduce_latest.json"):
                p.write_text(json.dumps({"date": None, "items": [], "note": "待本机 agent 补全推演"}, ensure_ascii=False),
                             encoding="utf-8")
            print("已写占位 obs_deduce_latest.json")
        sys.exit(0)

    src = files[-1]          # 字典序 = 日期序
    data = json.loads(src.read_text(encoding="utf-8"))
    date = src.parent.name
    items = data if isinstance(data, list) else data.get("items", [])
    out = {"date": date, "items": items, "count": len(items), "source": f"obs_deduce_{date}.json"}
    for p in (BASE / "output" / "obs_deduce_latest.json",
              BASE / "deploy" / "output" / "obs_deduce_latest.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 已同步 {date} 观测股推演 {len(items)} 只 → output/ + deploy/output/obs_deduce_latest.json")


if __name__ == "__main__":
    main()
