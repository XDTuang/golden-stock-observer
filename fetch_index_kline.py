#!/usr/bin/env python3
"""
兜金观测 — 指数日K线采集脚本
用法: python fetch_index_kline.py
"""

import json, os, sys, subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
NODE_BIN = "/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node"
WESTOCK_SCRIPT = "/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/builtin-skills/westock-data/scripts/index.js"

INDICES = {
    "sh000001": {"file": "sh_index_kline.json", "name": "上证指数"},
    "sz399001": {"file": "sz_index_kline.json", "name": "深证成指"},
    "sz399006": {"file": "cyb_index_kline.json", "name": "创业板指"},
    "sh000688": {"file": "kc50_index_kline.json", "name": "科创50"},
    "sh000300": {"file": "hs300_index_kline.json", "name": "沪深300"},
}

START_DATE = "2026-01-01"

def run_westock(cmd_args: list, timeout: int = 60) -> str:
    result = subprocess.run(
        [NODE_BIN, WESTOCK_SCRIPT] + cmd_args,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        print(f"  ⚠️ 命令失败: {' '.join(cmd_args)}", file=sys.stderr)
        return ""
    return result.stdout


def fetch_index_kline(code: str) -> list:
    """获取单只指数的日K线（2026-01-01 至今）"""
    today = datetime.now().strftime("%Y-%m-%d")
    output = run_westock(["kline", code, "--start", START_DATE, "--end", today], timeout=120)

    lines = output.strip().split("\n")
    if len(lines) < 3:
        return []

    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    data = []
    for line in lines[2:]:
        vals = [v.strip() for v in line.split("|") if v.strip()]
        if len(vals) != len(headers):
            continue
        row = {}
        for h, v in zip(headers, vals):
            if h == "date":
                row[h] = v
            else:
                try:
                    row[h] = float(v)
                except ValueError:
                    row[h] = v
        data.append(row)

    data.sort(key=lambda x: x["date"])
    return data


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始采集 5 只指数日K线 ...")

    for code, info in INDICES.items():
        print(f"  {info['name']} ({code}) ...", end=" ", flush=True)
        data = fetch_index_kline(code)
        if data:
            path = os.path.join(OUTPUT_DIR, info["file"])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"✅ {len(data)}天 → {info['file']}")
        else:
            print(f"❌ 无数据")

    print(f"\n  ✅ 指数K线采集完成 → {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
