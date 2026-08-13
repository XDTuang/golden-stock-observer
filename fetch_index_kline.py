#!/usr/bin/env python3
"""
兜金观测 — 指数日K线采集脚本

数据源: 腾讯官方行情代理 proxy.finance.qq.com（全球可达，GitHub Actions runner 可访问）
用法: python fetch_index_kline.py

输出 output/{sh|sz|cyb|kc50|hs300}_index_kline.json
字段: {date, open, last, high, low, volume}（last=收盘价，与前端展示一致）
"""
import json
import os
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# 腾讯 fqkline 接口（proxy.finance.qq.com 与 web.ifzq.gtimg.cn 同源，均全球可达）
KLINE_URL = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)"}

INDICES = {
    "sh000001": {"file": "sh_index_kline.json", "name": "上证指数"},
    "sz399001": {"file": "sz_index_kline.json", "name": "深证成指"},
    "sz399006": {"file": "cyb_index_kline.json", "name": "创业板指"},
    "sh000688": {"file": "kc50_index_kline.json", "name": "科创50"},
    "sh000300": {"file": "hs300_index_kline.json", "name": "沪深300"},
}

START_DATE = "2026-01-01"
KLINE_COUNT = 260  # 覆盖全年交易日 + 缓冲


def fetch_index_kline(code: str) -> list:
    """获取单只指数的日K线，返回 [{date, open, last, high, low, volume}, ...]"""
    if requests is None:
        print(f"  ⚠️ requests 未安装", file=sys.stderr)
        return []

    params = {"param": f"{code},day,,,{KLINE_COUNT},qfq"}
    for attempt in range(3):
        try:
            r = requests.get(KLINE_URL, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
            node = data.get("data", {}).get(code, {})
            arr = node.get("day") or node.get("qfqday")
            if not arr:
                return []

            bars = []
            for p in arr:
                # 腾讯 day 数组: [date, open, close, high, low, volume(手)]
                if len(p) < 6:
                    continue
                try:
                    bars.append({
                        "date": str(p[0]),
                        "open": float(p[1]),
                        "last": float(p[2]),   # close -> last（与前端字段一致）
                        "high": float(p[3]),
                        "low": float(p[4]),
                        "volume": float(p[5]),
                    })
                except (ValueError, TypeError):
                    continue

            # 过滤出 START_DATE 之后的数据，按日期升序
            bars = [b for b in bars if b["date"] >= START_DATE]
            bars.sort(key=lambda x: x["date"])
            return bars
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️ 拉取失败: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                return []
            time.sleep(1 + attempt)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始采集 5 只指数日K线（腾讯 proxy.finance.qq.com）...")

    ok = 0
    for code, info in INDICES.items():
        print(f"  {info['name']} ({code}) ...", end=" ", flush=True)
        data = fetch_index_kline(code)
        if data:
            path = os.path.join(OUTPUT_DIR, info["file"])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"✅ {len(data)}天 → {info['file']}（末 {data[-1]['date']}）")
            ok += 1
        else:
            print(f"❌ 无数据（保留旧文件）")

    print(f"\n  ✅ 指数K线采集完成: {ok}/5 → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
