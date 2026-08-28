#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 个股代码 → 新浪行业板块 映射缓存（供 derive_obs.py v3 板块因子使用）
=====================================================================
背景：东财板块接口被代理屏蔽；同花顺/东财板块命名体系与观测股映射不全。
方案：新浪行业板块（49 个）——stock_sector_spot 拿板块清单 + 涨跌幅，
      stock_sector_detail(sector=label) 拿成分股 → 建立 symbol→板块 映射。

输出: output/code_sector_sina.json  { "sh600176": "玻璃行业", ... }
用法: python build_sector_map_sina.py     # 全量构建（约 2-3 分钟）
      python build_sector_map_sina.py --spot-only  # 只更新板块涨跌（不重建映射）
"""
import json, sys, time
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
OUT = BASE / "output" / "code_sector_sina.json"


def main():
    import akshare as ak
    spot = ak.stock_sector_spot(indicator="新浪行业")
    if spot is None or spot.empty:
        print("❌ 新浪行业板块列表获取失败")
        sys.exit(1)
    print(f"新浪行业板块: {len(spot)} 个")

    # 已存在则增量（只补缺失板块）
    mapping = {}
    if OUT.exists():
        try:
            mapping = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            mapping = {}

    done, fail = 0, 0
    for _, r in spot.iterrows():
        label, name = str(r["label"]), str(r["板块"])
        # 板块名已在缓存且映射非空 → 跳过（重建时可用 --rebuild）
        if any(v == name for v in mapping.values()) and "--rebuild" not in sys.argv:
            continue
        try:
            df = ak.stock_sector_detail(sector=label)
            if df is not None and not df.empty:
                for _, s in df.iterrows():
                    mapping[str(s["symbol"])] = name
                done += 1
            time.sleep(0.2)
        except Exception as e:
            fail += 1
            print(f"  ⚠️ {name}: {type(e).__name__} {str(e)[:50]}")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ 完成: 板块 {done} 个（失败 {fail}）| 映射 {len(mapping)} 只 → {OUT}")


if __name__ == "__main__":
    main()
