#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机游共振日历 —— 使用 westock-data skill 获取龙虎榜数据
数据源: westock-data lhb --type institution,hotmoney --date YYYY-MM-DD
逻辑: 交叉比对机构榜和游资榜，找出"游资+机构"股票
"""
import subprocess
import json
import os
import re

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'lh_calendar.json')
WESTOCK_CLI = '/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node'
WESTOCK_SCRIPT = '/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/builtin-skills/westock-data/scripts/index.js'

def run_westock(date_str):
    """运行 westock-data lhb 命令获取机构＋游资数据"""
    cmd = [WESTOCK_CLI, WESTOCK_SCRIPT, 'lhb', '--type', 'institution,hotmoney', '--date', date_str]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout

def parse_amount(text):
    """解析金额：'3.63亿' -> 363000000, '9651.33万' -> 96513300"""
    text = text.strip()
    try:
        if '亿' in text:
            return float(text.replace('亿', '')) * 100000000
        elif '万' in text:
            return float(text.replace('万', '')) * 10000
        else:
            return float(text)
    except:
        return 0.0

def parse_institution_table(output):
    """解析机构榜表格"""
    institutions = []
    # 找到机构榜区域
    inst_start = output.find('**机构榜**')
    if inst_start == -1:
        return institutions
    
    # 找到表格头部后的数据行
    section = output[inst_start:]
    lines = section.split('\n')
    in_table = False
    for line in lines:
        line = line.strip()
        if '代码' in line and '名称' in line and '机构买入额' in line:
            in_table = True
            continue
        if in_table:
            if not line.startswith('|') or '---' in line:
                continue
            # 解析表格行: | 1 | sz002080 | 中材科技 | 3 | 5 | 3.63亿 | ...
            parts = [p.strip() for p in line.split('|')]
            parts = [p for p in parts if p and p != '']
            if len(parts) < 8:
                continue
            
            # 去重: 按股票名称去重（同一个股票可能因为不同原因上榜多次）
            code = parts[1]  # 代码 (index 1 after filtering empty parts)
            name = parts[2]  # 名称
            inst_buy = parse_amount(parts[5])  # 机构买入额 (index 5)
            total_net = parse_amount(parts[8])  # 净买入额 (index 8)
            
            institutions.append({
                'code': code.replace('sz', '').replace('sh', ''),
                'full_code': code,
                'name': name,
                'inst_buy': inst_buy,
                'total_net': total_net,
            })
    
    return institutions

def parse_hotmoney_stocks(output):
    """解析游资榜中涉及的股票代码"""
    inst_start = output.find('**游资榜**')
    if inst_start == -1:
        return set()
    
    section = output[inst_start:]
    stocks = set()
    
    # 匹配股票格式: sz002080 / sh600519 (格式: sh/sz + 6位数字)
    pattern = re.compile(r'[sz][hz]\d{6}')
    matches = pattern.findall(section)
    
    return set(matches)

def classify_six(inst_net, retail_net):
    """六维分类（金额单位: 亿元）"""
    if inst_net < -1.0:
        return '机构大卖'
    if inst_net >= 4.0:
        return '机构独买'
    if inst_net > 0.8 and retail_net > 0.8:
        return '纯共振'
    if inst_net > 0.8 and 0.5 <= retail_net <= 0.8:
        return '准共振'
    if inst_net < 4.0 and retail_net > 0:
        return '标X'
    return '其他'

def generate_calendar(date_str='2026-06-26'):
    """获取单日数据并生成日历"""
    print(f"获取 {date_str} 龙虎榜数据...")
    
    output = run_westock(date_str)
    
    # 解析机构榜
    institutions = parse_institution_table(output)
    print(f"机构榜: {len(institutions)} 条记录")
    
    # 解析游资榜中的股票
    hotmoney_stocks = parse_hotmoney_stocks(output)
    print(f"游资涉及的股票: {len(hotmoney_stocks)} 只")
    print(f"游资股票代码: {sorted(hotmoney_stocks)}")
    
    # 按股票代码去重机构数据（取最大的机构买入额记录）
    inst_map = {}
    for inst in institutions:
        code = inst['code']  # 6位代码
        full_code = inst['full_code']
        if code not in inst_map:
            inst_map[code] = inst
        # 如果已存在，取机构买入额更大的记录
        elif inst['inst_buy'] > inst_map[code]['inst_buy']:
            inst_map[code] = inst
    
    # 生成所有股票（包含机构参与的 + 游资参与的）
    day_stocks = []
    for code, inst in inst_map.items():
        full_code = inst['full_code']
        is_hotmoney = full_code in hotmoney_stocks
        
        inst_net = inst['inst_buy'] / 100000000  # 机构净买额 -> 亿
        total_net = inst['total_net'] / 100000000
        retail_net = total_net - inst_net  # 近似游资净买额
        
        category = classify_six(inst_net, retail_net)
        
        # reason 标明是否有游资参与
        reason = '游资+机构' if is_hotmoney else '仅机构'
        
        day_stocks.append({
            'code': code,
            'name': inst['name'],
            'inst_net': round(inst_net, 2),
            'retail_net': round(retail_net, 2),
            'total_net': round(total_net, 2),
            'category': category,
            'reason': reason,
            'has_hotmoney': is_hotmoney  # 标记是否有游资参与
        })
    
    print(f"\n游资+机构股票: {len(day_stocks)} 只")
    
    # 分类统计
    from collections import Counter
    cat_count = Counter(s['category'] for s in day_stocks)
    for cat, cnt in sorted(cat_count.items()):
        print(f"  {cat}: {cnt}只")
    
    return day_stocks

def main():
    """获取最近N天的龙虎榜数据"""
    import datetime
    
    # 获取最近7天的数据（排除周末）
    calendar = {}
    today = datetime.datetime.now()
    
    # 获取最近7天的日期（只获取工作日）
    dates = []
    for i in range(7):
        date = today - datetime.timedelta(days=i)
        # 跳过周末（0=周一, 1=周二, ..., 5=周六, 6=周日）
        if date.weekday() < 5:  # 只获取工作日
            dates.append(date.strftime('%Y-%m-%d'))
    
    print(f"将获取以下日期的数据: {dates}")
    
    # 串行获取每一天的数据
    for date_str in dates:
        try:
            day_stocks = generate_calendar(date_str)
            calendar[date_str] = day_stocks
            print(f"✅ {date_str}: {len(day_stocks)} 只股票")
        except Exception as e:
            print(f"❌ {date_str} 获取失败: {e}")
    
    # 保存数据
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存到: {OUTPUT_FILE}")
    
    # 验证
    with open(OUTPUT_FILE, 'r') as f:
        verify = json.load(f)
    print(f"验证通过: {len(verify)} 天, {sum(len(v) for v in verify.values())} 只股票")
    print(f"日期范围: {sorted(verify.keys())}")

if __name__ == '__main__':
    main()
