#!/usr/bin/env python3
"""
兜金观测 — A股一级板块资金流向采集脚本

获取申万一级行业的当日资金流入流出情况，
输出 output/sector_fund_flow_YYYY-MM-DD.json 供前端展示。

用法: python fetch_sector_fund_flow.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "sector_cache")  # 板块资金流向缓存目录
CACHE_DAYS = 20  # 缓存20个交易日

NODE_BIN = "/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node"
WESTOCK_SCRIPT = "/Users/samt/.workbuddy/plugins/marketplaces/experts/plugins/stock-partner-team/skills/westock-data/scripts/index.js"


def get_sector_list():
    """获取申万一级行业清单"""
    try:
        result = subprocess.run(
            [NODE_BIN, WESTOCK_SCRIPT, "sector", "list", "industry_list_sw1"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            print(f"获取板块清单失败: {result.stderr}")
            return []
        
        # 解析表格输出
        lines = result.stdout.strip().split("\n")
        sectors = []
        
        for line in lines:
            if not line.strip() or "─" in line or "|" not in line:
                continue
            
            parts = [p.strip() for p in line.split("|")]
            # 格式: | code | name |
            if len(parts) >= 3:
                code = parts[1].strip()
                name = parts[2].strip()
                if code.startswith("pt") and name:
                    sectors.append({"code": code, "name": name})
        
        return sectors
    except Exception as e:
        print(f"获取板块清单异常: {e}")
        return []


def get_sector_fund_flow(sector_code: str, sector_name: str) -> dict:
    """获取单个板块的资金流向数据"""
    try:
        # sector_code 已经包含 pt 前缀
        result = subprocess.run(
            [NODE_BIN, WESTOCK_SCRIPT, "fund", "flow", sector_code],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        # 解析表格输出
        lines = result.stdout.strip().split("\n")
        if len(lines) < 3:
            return None
        
        # 第三行是数据
        data_line = lines[2]
        parts = [p.strip() for p in data_line.split("|")]
        
        if len(parts) >= 19:
            return {
                "code": sector_code,
                "name": sector_name,
                "main_net": float(parts[9]) if parts[9] else 0,  # MainNetFlow
                "main_in": float(parts[6]) if parts[6] else 0,   # MainInFlow
                "main_out": float(parts[13]) if parts[13] else 0, # MainOutFlow
            }
        
        return None
    except Exception as e:
        print(f"获取{sector_name}资金流向失败: {e}")
        return None


def clean_old_cache():
    """清理超过20个交易日的缓存"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        return
    
    # 获取所有缓存文件
    cache_files = sorted(Path(OUTPUT_DIR).glob("sector_fund_flow_*.json"))
    
    # 保留最近20个交易日
    if len(cache_files) > CACHE_DAYS:
        for old_file in cache_files[:-CACHE_DAYS]:
            try:
                os.remove(old_file)
                print(f"已删除过期缓存: {old_file.name}")
            except Exception as e:
                print(f"删除缓存失败: {e}")


def main(date_str=None):
    """主函数"""
    # 确定日期
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"sector_fund_flow_{date_str}.json")
    
    # 如果当天数据已存在，直接返回
    if os.path.exists(output_file):
        print(f"当日数据已存在: {output_file}")
        return output_file
    
    print(f"开始采集 {date_str} 板块资金流向数据...")
    
    # 1. 获取板块清单
    sectors = get_sector_list()
    if not sectors:
        print("获取板块清单失败")
        return None
    
    print(f"获取到 {len(sectors)} 个板块")
    
    # 2. 获取每个板块的资金流向
    sector_data = []
    for i, sector in enumerate(sectors):
        print(f"[{i+1}/{len(sectors)}] 获取 {sector['name']} 资金流向...")
        flow_data = get_sector_fund_flow(sector["code"], sector["name"])
        
        if flow_data:
            sector_data.append(flow_data)
    
    if not sector_data:
        print("未能获取任何板块数据")
        return None
    
    # 3. 汇总统计
    total_main_net = sum(s["main_net"] for s in sector_data)
    total_main_in = sum(s["main_in"] for s in sector_data)
    total_main_out = sum(s["main_out"] for s in sector_data)
    
    net_in_sectors = [s for s in sector_data if s["main_net"] > 0]
    net_out_sectors = [s for s in sector_data if s["main_net"] < 0]
    
    # 按净流入排序
    sector_data.sort(key=lambda x: x["main_net"], reverse=True)
    
    # 4. 构建输出数据
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "date": date_str,
        "summary": {
            "total_main_net": total_main_net,
            "total_main_in": total_main_in,
            "total_main_out": total_main_out,
            "net_in_count": len(net_in_sectors),
            "net_out_count": len(net_out_sectors),
            "sector_count": len(sector_data)
        },
        "top5_in": sector_data[:5],  # 净流入TOP5
        "top5_out": sector_data[-5:][::-1],  # 净流出TOP5
        "sectors": sector_data  # 所有板块数据
    }
    
    # 5. 保存数据
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存: {output_file}")
    print(f"汇总: 净流入 {len(net_in_sectors)} 个板块, 净流出 {len(net_out_sectors)} 个板块")
    print(f"合计净流入: {total_main_net/1e8:.2f} 亿元")
    
    # 6. 清理过期缓存
    clean_old_cache()
    
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="A股一级板块资金流向采集")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)", default=None)
    
    args = parser.parse_args()
    main(args.date)
