#!/usr/bin/env python3
"""
兜金观测 — 板块资金流向采集脚本

查询31个申万一级行业板块的每日资金流向数据，
缓存20个交易日，输出 output/sector_flow.json 供前端展示。

用法: python fetch_sector_flow.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "sector_flow.json")
NODE_BIN = "/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node"
WESTOCK_SCRIPT = "/Users/samt/.workbuddy/plugins/marketplaces/experts/plugins/stock-partner-team/skills/westock-data/scripts/index.js"

# 申万一级行业板块代码 → 名称映射
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

# 板块分类（用于前端分组展示）
SECTOR_CATEGORIES = {
    "大金融": ["银行", "非银金融", "房地产"],
    "大消费": ["食品饮料", "家用电器", "医药生物", "纺织服饰", "商贸零售", "美容护理", "社会服务"],
    "大科技": ["电子", "计算机", "通信", "传媒"],
    "大制造": ["电力设备", "机械设备", "汽车", "国防军工"],
    "资源周期": ["有色金属", "基础化工", "煤炭", "石油石化", "钢铁"],
    "基建公用": ["建筑装饰", "建筑材料", "公用事业", "交通运输", "环保"],
    "农林综合": ["农林牧渔", "综合"],
}


def run_westock(cmd_args: list) -> str:
    """运行 westock-data 命令并返回 stdout"""
    result = subprocess.run(
        [NODE_BIN, WESTOCK_SCRIPT] + cmd_args,
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"  ⚠️ 命令失败: {' '.join(cmd_args)}", file=sys.stderr)
        print(f"  stderr: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def parse_fund_flow(output: str) -> dict | None:
    """解析 fund flow 的 markdown 表格输出，返回字段字典"""
    lines = output.strip().split("\n")
    if len(lines) < 3:
        return None

    header_line = lines[0]
    data_line = lines[2] if len(lines) > 2 else None

    if not data_line:
        return None

    headers = [h.strip() for h in header_line.split("|") if h.strip()]
    values = [v.strip() for v in data_line.split("|") if v.strip()]

    if len(headers) != len(values):
        return None

    result = {}
    for h, v in zip(headers, values):
        try:
            result[h] = float(v)
        except ValueError:
            result[h] = v

    return result


def fetch_sector_flows() -> list:
    """获取所有申万一级行业板块的资金流向数据"""
    sectors = []
    for code, name in SW1_SECTORS.items():
        print(f"  查询 {name} ({code})...")
        flow_output = run_westock(["fund", "flow", code])
        flow_data = parse_fund_flow(flow_output)

        if not flow_data:
            print(f"    ⚠️ 未获取到资金流向数据")
            sectors.append({
                "code": code,
                "name": name,
                "category": get_sector_category(name),
                "main_net_flow": None,
                "jumbo_net_flow": None,
                "has_data": False,
            })
            continue

        main_net_flow = flow_data.get("MainNetFlow", 0)
        jumbo_net_flow = flow_data.get("JumboNetFlow", 0)
        main_in_flow = flow_data.get("MainInFlow", 0)
        main_out_flow = flow_data.get("MainOutFlow", 0)
        block_net_flow = flow_data.get("BlockNetFlow", 0)
        retail_in_flow = flow_data.get("RetailInFlow", 0)
        retail_out_flow = flow_data.get("RetailOutFlow", 0)
        main_inflow_rank = flow_data.get("MainInflowRank", 0)
        main_inflow_ind_rank = flow_data.get("MainInflowIndustryRank", 0)

        sectors.append({
            "code": code,
            "name": name,
            "category": get_sector_category(name),
            "main_net_flow": main_net_flow,
            "jumbo_net_flow": jumbo_net_flow,
            "main_in_flow": main_in_flow,
            "main_out_flow": main_out_flow,
            "block_net_flow": block_net_flow,
            "retail_in_flow": retail_in_flow,
            "retail_out_flow": retail_out_flow,
            "main_inflow_rank": main_inflow_rank,
            "main_inflow_ind_rank": main_inflow_ind_rank,
            "has_data": True,
        })

        sign = "+" if main_net_flow >= 0 else ""
        print(f"    ✅ 主力净流入: {sign}{main_net_flow/1e8:.2f}亿")

    return sectors


def get_sector_category(name: str) -> str:
    """根据板块名称返回分类"""
    for cat, names in SECTOR_CATEGORIES.items():
        if name in names:
            return cat
    return "其他"


def analyze_sector_flows(sectors: list) -> dict:
    """分析板块资金流向，生成汇总统计"""
    total_main_net = sum(s.get("main_net_flow", 0) or 0 for s in sectors)
    total_jumbo_net = sum(s.get("jumbo_net_flow", 0) or 0 for s in sectors)

    # 分类汇总
    category_nets = {}
    for s in sectors:
        cat = s.get("category", "其他")
        net = s.get("main_net_flow", 0) or 0
        category_nets[cat] = category_nets.get(cat, 0) + net

    # 按主力净流入排序
    sectors_sorted = sorted(sectors, key=lambda x: x.get("main_net_flow", 0) or 0, reverse=True)

    # 资金流入/流出板块数
    net_in_count = len([s for s in sectors if (s.get("main_net_flow") or 0) > 0])
    net_out_count = len([s for s in sectors if (s.get("main_net_flow") or 0) < 0])

    # TOP5 流入/流出
    top_in = sectors_sorted[:5]
    top_out = sectors_sorted[-5:][::-1]  # 流出最多的5个

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
    """加载已有历史数据"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": {}, "last_updated": None}


def save_history(data: dict):
    """保存历史数据，保留最多20个交易日"""
    # 按日期排序，只保留最近20个
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

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取板块资金流向 ({date_str})...")

    # 加载历史数据
    data = load_history()

    # 获取资金流向数据
    sectors = fetch_sector_flows()

    # 分析汇总
    summary = analyze_sector_flows(sectors)

    # 写入历史
    data["history"][date_str] = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "sectors": sectors,
    }
    data["last_updated"] = datetime.now().isoformat()

    save_history(data)

    # 打印汇总
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
