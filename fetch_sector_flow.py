#!/usr/bin/env python3
"""
兜金观测 — 板块资金流向采集脚本 v2

v2 改动（云端化根治）:
  - 数据源从 westock-data（本机 skill，云端不存在）切换为东方财富
    板块资金流 HTTP 接口（申万一级行业，f62=主力净流入）
  - 失败时优雅降级（保留旧数据 + 警告，不崩溃）

用法: python fetch_sector_flow.py [--date YYYY-MM-DD]
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
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "sector_flow.json")

# 东方财富板块资金流接口（push2delay 域名更稳定，全球可达）
EASTMONEY_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)",
           "Referer": "https://data.eastmoney.com/"}

# 申万一级行业板块代码 → 名称映射（与东财申万一级 f14 名称对应）
SW1_SECTORS = {
    "pt01801780": "银行",
    "pt01801720": "建筑装饰",
    "pt01801950": "煤炭",
    "pt01801790": "非银金融",
    "pt01801230": "综合",
    "pt01801120": "食品饮料",
    "pt01801140": "轻工制造",
    "pt01801030": "基础化工",
    "pt01801080": "电子",
    "pt01801130": "纺织服饰",
    "pt01801960": "石油石化",
    "pt01801110": "家用电器",
    "pt01801180": "房地产",
    "pt01801740": "国防军工",
    "pt01801010": "农林牧渔",
    "pt01801150": "医药生物",
    "pt01801040": "钢铁",
    "pt01801750": "计算机",
    "pt01801880": "汽车",
    "pt01801160": "公用事业",
    "pt01801980": "美容护理",
    "pt01801170": "交通运输",
    "pt01801050": "有色金属",
    "pt01801200": "商贸零售",
    "pt01801730": "电力设备",
    "pt01801760": "传媒",
    "pt01801770": "通信",
    "pt01801210": "社会服务",
    "pt01801710": "建筑材料",
    "pt01801890": "机械设备",
    "pt01801970": "环保",
}

SECTOR_CATEGORIES = {
    "大金融": ["银行", "非银金融", "房地产"],
    "大消费": ["食品饮料", "家用电器", "医药生物", "纺织服饰", "商贸零售", "美容护理", "社会服务"],
    "大科技": ["电子", "计算机", "通信", "传媒"],
    "大制造": ["电力设备", "机械设备", "汽车", "国防军工"],
    "资源周期": ["有色金属", "基础化工", "煤炭", "石油石化", "钢铁"],
    "基建公用": ["建筑装饰", "建筑材料", "公用事业", "交通运输", "环保"],
    "农林综合": ["农林牧渔", "综合"],
}


def get_sector_category(name: str) -> str:
    for cat, names in SECTOR_CATEGORIES.items():
        if name in names:
            return cat
    return "其他"


def fetch_eastmoney_sectors() -> dict:
    """拉取东财行业板块资金流，按名称筛选申万一级，返回 {名称: {main_net, jumbo_net, block_net}}"""
    if requests is None:
        return {}
    result = {}
    for attempt in range(3):
        try:
            # 分页拉取全部行业板块（含申万一/二/三级，按 f14 名称精确筛选申万一级）
            for pn in range(1, 6):
                params = {
                    "pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                    "fid": "f62", "fs": "m:90+t:2",
                    "fields": "f12,f14,f62,f66,f72,f184",
                }
                r = requests.get(EASTMONEY_URL, params=params, headers=HEADERS, timeout=15)
                r.raise_for_status()
                data = r.json().get("data") or {}
                diff = data.get("diff") or []
                for x in diff:
                    name = x.get("f14")
                    if name and name in SW1_SECTORS.values():
                        result[name] = {
                            "main_net": x.get("f62") or 0,
                            "jumbo_net": x.get("f66") or 0,
                            "block_net": x.get("f72") or 0,
                            "ratio": x.get("f184") or 0,
                        }
                total = data.get("total") or 0
                if pn * 100 >= total:
                    break
            if result:
                return result
            return {}
        except Exception as e:
            if attempt == 2:
                print(f"  ⚠️ 东财板块接口失败: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                return {}
            time.sleep(1 + attempt)
    return {}


def fetch_sector_flows() -> list:
    """获取所有申万一级行业板块的资金流向数据"""
    em = fetch_eastmoney_sectors()
    if not em:
        print("  ⚠️ 东财数据源不可达，本次跳过（保留旧数据）")
        return []

    sectors = []
    for code, name in SW1_SECTORS.items():
        flow = em.get(name)
        if flow is None:
            print(f"  {name} ({code}) ... ⚠️ 未匹配到东财板块")
            sectors.append({
                "code": code, "name": name, "category": get_sector_category(name),
                "main_net_flow": None, "jumbo_net_flow": None, "has_data": False,
            })
            continue

        main_net = flow["main_net"]
        sectors.append({
            "code": code,
            "name": name,
            "category": get_sector_category(name),
            "main_net_flow": main_net,
            "jumbo_net_flow": flow["jumbo_net"],
            "main_in_flow": 0,
            "main_out_flow": 0,
            "block_net_flow": flow["block_net"],
            "retail_in_flow": 0,
            "retail_out_flow": 0,
            "main_inflow_rank": 0,
            "main_inflow_ind_rank": 0,
            "has_data": True,
        })
        print(f"  {name} ({code}) ... ✅ 主力净流入 {main_net/1e8:+.2f}亿")

    return sectors


def analyze_sector_flows(sectors: list) -> dict:
    total_main_net = sum(s.get("main_net_flow", 0) or 0 for s in sectors)
    total_jumbo_net = sum(s.get("jumbo_net_flow", 0) or 0 for s in sectors)

    category_nets = {}
    for s in sectors:
        cat = s.get("category", "其他")
        category_nets[cat] = category_nets.get(cat, 0) + (s.get("main_net_flow", 0) or 0)

    sectors_sorted = sorted(sectors, key=lambda x: x.get("main_net_flow", 0) or 0, reverse=True)
    net_in_count = len([s for s in sectors if (s.get("main_net_flow") or 0) > 0])
    net_out_count = len([s for s in sectors if (s.get("main_net_flow") or 0) < 0])
    top_in = sectors_sorted[:5]
    top_out = sectors_sorted[-5:][::-1]

    return {
        "total_main_net_flow": total_main_net,
        "total_jumbo_net_flow": total_jumbo_net,
        "category_nets": category_nets,
        "sector_count": len([s for s in sectors if s.get("has_data")]),
        "net_in_count": net_in_count,
        "net_out_count": net_out_count,
        "top_in": [{"name": s["name"], "main_net_flow": s.get("main_net_flow")} for s in top_in],
        "top_out": [{"name": s["name"], "main_net_flow": s.get("main_net_flow")} for s in top_out],
    }


def load_history():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": {}, "last_updated": None}


def save_history(data: dict):
    dates = sorted(data["history"].keys(), reverse=True)
    if len(dates) > 20:
        for old_date in dates[20:]:
            del data["history"][old_date]
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def main():
    date_str = None
    if len(sys.argv) > 2 and sys.argv[1] == "--date":
        date_str = sys.argv[2]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取板块资金流向 ({date_str})...（东财申万一级）")

    data = load_history()
    sectors = fetch_sector_flows()

    if not sectors:
        print("  ⚠️ 未获取到板块资金流数据，保留旧数据（不更新）")
        return

    summary = analyze_sector_flows(sectors)
    data["history"][date_str] = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "sectors": sectors,
    }
    data["last_updated"] = datetime.now().isoformat()
    save_history(data)

    main_net = summary["total_main_net_flow"]
    sign = "+" if main_net >= 0 else ""
    print(f"\n  === 板块资金流向汇总 ({date_str}) ===")
    print(f"  总主力净流入: {sign}{main_net/1e8:.2f}亿")
    print(f"  流入板块: {summary['net_in_count']}个 / 流出板块: {summary['net_out_count']}个")
    print(f"  TOP5流入: {', '.join(f'{s['name']}({s['main_net_flow']/1e8:+.2f}亿)' for s in summary['top_in'])}")
    print(f"  TOP5流出: {', '.join(f'{s['name']}({s['main_net_flow']/1e8:+.2f}亿)' for s in summary['top_out'])}")
    print(f"  历史缓存: {len(data['history'])}个交易日")
    print(f"  结果已保存至: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
