#!/usr/bin/env python3
"""
兜金观测 — 国家队ETF资金流向采集脚本 v2

v2 改动:
  - 取消 20 天上限，保留全部历史（累计缓存）
  - 新增 --backfill-from YYYY-MM-DD 回填模式：一次性拉取多日数据
  - westock fund flow --start/--end 支持日期范围，每 ETF 一次查询

用法:
  python fetch_national_team_etf.py                           # 增量：采集今日（追加到缓存）
  python fetch_national_team_etf.py --date YYYY-MM-DD         # 指定日期
  python fetch_national_team_etf.py --backfill-from 2026-01-01  # 回填：一次性补全历史
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "national_team_etf.json")
NODE_BIN = "/Users/samt/.workbuddy/binaries/node/versions/22.22.2/bin/node"
WESTOCK_SCRIPT = "/Users/samt/.workbuddy/plugins/marketplaces/experts/plugins/stock-partner-team/skills/westock-data/scripts/index.js"

# 国家队核心ETF列表（中央汇金投资+中央汇金资管 2025年报公开持仓）
NATIONAL_TEAM_ETFS = [
    # ═══ 沪深300（4只）═══
    {"code": "sh510300", "name": "华泰柏瑞沪深300交易型开放式指数证券投资基金", "category": "沪深300", "short_name": "沪深300ETF华泰柏瑞"},
    {"code": "sh510310", "name": "易方达沪深300交易型开放式指数发起式证券投资基金", "category": "沪深300", "short_name": "沪深300ETF易方达"},
    {"code": "sh510330", "name": "华夏沪深300交易型开放式指数证券投资基金", "category": "沪深300", "short_name": "沪深300ETF华夏"},
    {"code": "sz159919", "name": "嘉实沪深300交易型开放式指数证券投资基金", "category": "沪深300", "short_name": "沪深300ETF嘉实"},

    # ═══ 上证50（2只）═══
    {"code": "sh510050", "name": "华夏上证50交易型开放式指数证券投资基金", "category": "上证50", "short_name": "上证50ETF华夏"},
    {"code": "sh510100", "name": "易方达上证50交易型开放式指数证券投资基金", "category": "上证50", "short_name": "上证50ETF易方达"},

    # ═══ 中证500（3只）═══
    {"code": "sh510500", "name": "南方中证500交易型开放式指数证券投资基金", "category": "中证500", "short_name": "中证500ETF南方"},
    {"code": "sh512500", "name": "华夏中证500交易型开放式指数证券投资基金", "category": "中证500", "short_name": "中证500ETF华夏"},
    {"code": "sz159922", "name": "嘉实中证500交易型开放式指数证券投资基金", "category": "中证500", "short_name": "中证500ETF嘉实"},

    # ═══ 创业板（3只）═══
    {"code": "sz159915", "name": "易方达创业板交易型开放式指数证券投资基金", "category": "创业板", "short_name": "创业板ETF易方达"},
    {"code": "sz159952", "name": "广发创业板交易型开放式指数证券投资基金", "category": "创业板", "short_name": "创业板ETF广发"},
    {"code": "sz159977", "name": "天弘创业板交易型开放式指数证券投资基金", "category": "创业板", "short_name": "创业板ETF天弘"},

    # ═══ 科创50（3只）═══
    {"code": "sh588000", "name": "华夏上证科创板50成份交易型开放式指数证券投资基金", "category": "科创50", "short_name": "科创50ETF华夏"},
    {"code": "sh588080", "name": "易方达上证科创板50成份交易型开放式指数证券投资基金", "category": "科创50", "short_name": "科创50ETF易方达"},
    {"code": "sh588050", "name": "工银瑞信上证科创板50成份交易型开放式指数证券投资基金", "category": "科创50", "short_name": "科创50ETF工银"},

    # ═══ 中证1000（4只）═══
    {"code": "sh512100", "name": "南方中证1000交易型开放式指数证券投资基金", "category": "中证1000", "short_name": "中证1000ETF南方"},
    {"code": "sz159845", "name": "华夏中证1000交易型开放式指数证券投资基金", "category": "中证1000", "short_name": "中证1000ETF华夏"},
    {"code": "sh560010", "name": "广发中证1000交易型开放式指数证券投资基金", "category": "中证1000", "short_name": "中证1000ETF广发"},
    {"code": "sz159629", "name": "富国中证1000交易型开放式指数证券投资基金", "category": "中证1000", "short_name": "中证1000ETF富国"},

    # ═══ 其他宽基（2只）═══
    {"code": "sh510180", "name": "华安上证180交易型开放式指数证券投资基金", "category": "上证180", "short_name": "上证180ETF华安"},
    {"code": "sz159901", "name": "易方达深证100交易型开放式指数证券投资基金", "category": "深证100", "short_name": "深证100ETF易方达"},
]

# ETF 代码 → 名称映射（供快速查找）
CODE_TO_ETF = {e["code"]: e for e in NATIONAL_TEAM_ETFS}


def run_westock(cmd_args: list, timeout: int = 60) -> str:
    """运行 westock-data 命令并返回 stdout"""
    result = subprocess.run(
        [NODE_BIN, WESTOCK_SCRIPT] + cmd_args,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        print(f"  ⚠️ 命令失败 ({result.returncode}): {' '.join(cmd_args)}", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr[:200]}", file=sys.stderr)
        return ""
    return result.stdout


def parse_fund_flow_table(output: str) -> list[dict]:
    """解析 westock fund flow markdown 表格（支持多行/多日）"""
    lines = output.strip().split("\n")
    if len(lines) < 3:
        return []

    # 第一行是表头，第二行是分隔符，第三行起是数据
    headers_raw = [h.strip() for h in lines[0].split("|") if h.strip()]
    # 映射标准字段名
    header_map = {}
    for h in headers_raw:
        hl = h.lower().replace("_", "")
        if hl in ("mainnetflow", "main_net_flow"):
            header_map[h] = "main_net_flow"
        elif hl in ("jumbonetflow", "jumbo_net_flow"):
            header_map[h] = "jumbo_net_flow"
        elif hl in ("blocknetflow", "block_net_flow"):
            header_map[h] = "block_net_flow"
        elif hl in ("maininflow", "main_in_flow"):
            header_map[h] = "main_in_flow"
        elif hl in ("mainoutflow", "main_out_flow"):
            header_map[h] = "main_out_flow"
        elif hl in ("retailinflow", "retail_in_flow"):
            header_map[h] = "retail_in_flow"
        elif hl in ("retailoutflow", "retail_out_flow"):
            header_map[h] = "retail_out_flow"
        elif hl in ("closeprice", "close_price"):
            header_map[h] = "close_price"
        elif hl == "date":
            header_map[h] = "date"
        elif hl == "code":
            header_map[h] = "code"
        elif hl in ("midnetflow", "smallnetflow", "secucode", "enddate"):
            header_map[h] = None  # 不需要的字段

    rows = []
    for line in lines[2:]:  # 从第三行开始是数据
        values = [v.strip() for v in line.split("|") if v.strip()]
        if len(values) != len(headers_raw):
            continue
        row = {}
        for h, v in zip(headers_raw, values):
            key = header_map.get(h)
            if key is None:
                continue
            try:
                row[key] = float(v)
            except ValueError:
                row[key] = v
        if row.get("date"):
            rows.append(row)
    return rows


def fetch_single_day_quotes(etfs_date_map: dict) -> dict[str, dict]:
    """为一批 ETF+日期查实时行情（仅单个交易日时用于补 change_pct/amount）"""
    results = {}
    for code in etfs_date_map:
        quote_output = run_westock(["quote", code], timeout=15)
        if quote_output:
            lines = quote_output.strip().split("\n")
            if len(lines) >= 3:
                h_line = lines[0]
                d_line = lines[2]
                h_vals = [x.strip() for x in h_line.split("|") if x.strip()]
                d_vals = [x.strip() for x in d_line.split("|") if x.strip()]
                if len(h_vals) == len(d_vals):
                    qd = dict(zip(h_vals, d_vals))
                    results[code] = qd
    return results


def backfill_history(from_date: str, to_date: str, existing_history: dict):
    """回填模式：遍历全部 ETF，每只一次日期范围查询，写入历史缓存"""
    print(f"\n📊 回填: {from_date} → {to_date}（{len(NATIONAL_TEAM_ETFS)} 只 ETF）\n")

    # 收集所有交易日的每只 ETF 数据
    # 结构: history[date][code] = {flow fields}
    history = {d: {} for d in existing_history}  # 保留已有数据

    for idx, etf in enumerate(NATIONAL_TEAM_ETFS, 1):
        code = etf["code"]
        print(f"  [{idx}/{len(NATIONAL_TEAM_ETFS)}] {etf['short_name']} ({code})...", end=" ", flush=True)

        output = run_westock(["fund", "flow", code, "--start", from_date, "--end", to_date], timeout=120)
        rows = parse_fund_flow_table(output)
        if not rows:
            print("❌ 无数据")
            continue

        row_count = 0
        for row in rows:
            date_str = row.get("date", "")
            if not date_str:
                continue
            if date_str not in history:
                history[date_str] = {}

            entry = {
                **etf,
                "main_net_flow": row.get("main_net_flow", 0) or 0,
                "jumbo_net_flow": row.get("jumbo_net_flow", 0) or 0,
                "main_in_flow": row.get("main_in_flow", 0) or 0,
                "main_out_flow": row.get("main_out_flow", 0) or 0,
                "block_net_flow": row.get("block_net_flow", 0) or 0,
                "retail_in_flow": row.get("retail_in_flow", 0) or 0,
                "retail_out_flow": row.get("retail_out_flow", 0) or 0,
                "close_price": row.get("close_price", 0) or 0,
                "change_pct": 0,  # 回填不补涨跌幅（费时），前端可不展示
                "amount": (row.get("main_in_flow", 0) or 0) + (row.get("main_out_flow", 0) or 0),
                "has_data": True,
                # 5d/10d/20d 不在这里算（由调用方依据日期序列自行聚合）
                "main_net_flow_5d": 0,
                "main_net_flow_10d": 0,
                "main_net_flow_20d": 0,
            }
            history[date_str][code] = entry
            row_count += 1
        print(f"✅ {row_count}天")

    # 按日期排序 + 每日期 build summary
    sorted_dates = sorted(history.keys())
    result = {"history": {}, "last_updated": datetime.now().isoformat()}

    for date_str in sorted_dates:
        day_etfs = history[date_str]
        if not day_etfs:
            continue

        etf_list = list(day_etfs.values())
        summary = build_summary(etf_list)
        result["history"][date_str] = {
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "etfs": etf_list,
        }

    # 重算趋势累计（5日/10日/本月），修正历史 trend 恒为 0 的 bug
    recompute_trends(result["history"])

    # 保存
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 回填完成: {len(result['history'])} 个交易日")
    print(f"📁 保存至: {OUTPUT_FILE}")


def build_summary(etfs: list) -> dict:
    """分析 ETF 资金流向，生成汇总统计（与 v1 保持一致）"""
    total_main_net = sum(e.get("main_net_flow", 0) or 0 for e in etfs)
    total_jumbo_net = sum(e.get("jumbo_net_flow", 0) or 0 for e in etfs)
    total_amount = sum(e.get("amount", 0) or 0 for e in etfs)
    total_main_in = sum(e.get("main_in_flow", 0) or 0 for e in etfs)
    total_main_out = sum(e.get("main_out_flow", 0) or 0 for e in etfs)

    category_nets = {}
    for e in etfs:
        cat = e.get("category", "其他")
        cat_net = e.get("main_net_flow", 0) or 0
        category_nets[cat] = category_nets.get(cat, 0) + cat_net

    # 5d/10d 需要多日数据聚合，backfill 不计算（单日模式由 update_data.sh 调用时算）
    trend_5d = sum(e.get("main_net_flow_5d", 0) or 0 for e in etfs)
    trend_10d = sum(e.get("main_net_flow_10d", 0) or 0 for e in etfs)

    signal = "中性"
    if total_main_net > 2e9:
        signal = "强烈买入"
    elif total_main_net > 5e8:
        signal = "温和买入"
    elif total_main_net < -3e8:
        signal = "减仓"

    return {
        "total_main_net_flow": total_main_net,
        "total_jumbo_net_flow": total_jumbo_net,
        "total_amount": total_amount,
        "total_main_in": total_main_in,
        "total_main_out": total_main_out,
        "category_nets": category_nets,
        "signal": signal,
        "trend_5d": trend_5d,
        "trend_10d": trend_10d,
        "etf_count": len([e for e in etfs if e.get("has_data")]),
        "net_in_count": len([e for e in etfs if (e.get("main_net_flow") or 0) > 0]),
        "net_out_count": len([e for e in etfs if (e.get("main_net_flow") or 0) < 0]),
    }


def recompute_trends(history: dict):
    """基于历史每日总主力净流入序列，重算每个交易日的趋势累计。

    修正此前 trend_5d / trend_10d 恒为 0 的 bug（旧逻辑从每只 ETF 的
    main_net_flow_5d 字段求和，而该字段从未被计算，恒为 0）。

    口径：
      - 5日累计：含当日及往前最多 4 个交易日的 total_main_net_flow 合计
      - 10日累计：含当日及往前最多 9 个交易日的合计
      - 本月累计(trend_mtd)：自然月内（月初→当日）所有交易日的合计
    全量遍历，确保历史存量数据一并修正。
    """
    dates = sorted(history.keys())
    if not dates:
        return
    series = [(d, (history[d].get("summary", {}) or {}).get("total_main_net_flow", 0) or 0)
              for d in dates]
    for i, (d, _v) in enumerate(series):
        window5 = series[max(0, i - 4):i + 1]
        trend_5d = sum(x[1] for x in window5)
        window10 = series[max(0, i - 9):i + 1]
        trend_10d = sum(x[1] for x in window10)
        ym = d[:7]
        trend_mtd = sum(x[1] for x in series if x[0][:7] == ym and x[0] <= d)
        if "summary" not in history[d] or not isinstance(history[d]["summary"], dict):
            history[d]["summary"] = {}
        history[d]["summary"]["trend_5d"] = trend_5d
        history[d]["summary"]["trend_10d"] = trend_10d
        history[d]["summary"]["trend_mtd"] = trend_mtd


def load_history():
    """加载已有历史数据"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    return {"history": {}, "last_updated": None}


def save_history(data: dict):
    """保存历史数据（无上限，无限累计）"""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def main():
    backfill_from = None
    date_str = None
    force_overwrite = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--backfill-from":
            backfill_from = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--date":
            date_str = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] in ("--force-overwrite", "--force"):
            force_overwrite = True
            i += 1
        elif sys.argv[i] == "--recompute-trends":
            data = load_history()
            recompute_trends(data["history"])
            save_history(data)
            print(f"✅ 趋势累计重算完成: {len(data['history'])} 个交易日")
            return
        else:
            i += 1

    if backfill_from:
        to_date = date_str or datetime.now().strftime("%Y-%m-%d")
        existing = load_history()
        backfill_history(backfill_from, to_date, existing["history"])
        return

    # ── 单日增量模式（与 v1 兼容）──
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取国家队ETF资金流向 ({date_str})...")

    data = load_history()

    # 检查是否已有今日数据
    if date_str in data.get("history", {}) and not force_overwrite:
        print(f"  ℹ️ {date_str} 已有数据，跳过（加 --force-overwrite 可覆盖）")
        print(f"  历史缓存: {len(data['history'])} 个交易日")
        return

    # 获取资金流向（单日模式：每只 ETF 单独查询，带日期范围确保命中当日）
    etfs = []
    for etf in NATIONAL_TEAM_ETFS:
        code = etf["code"]
        print(f"  查询 {etf['name']} ({code})...")

        flow_output = run_westock(
            ["fund", "flow", code, "--start", date_str, "--end", date_str],
            timeout=120,
        )
        flow_rows = parse_fund_flow_table(flow_output)

        # 单日模式：取最后一行
        flow_data = None
        if flow_rows:
            for r in flow_rows:
                if r.get("date") == date_str:
                    flow_data = r
                    break
            if not flow_data:
                flow_data = flow_rows[-1]  # fallback: 取最新

        quote_output = run_westock(["quote", code], timeout=15)
        quote_data = None
        if quote_output:
            lines = quote_output.strip().split("\n")
            if len(lines) >= 3:
                h_vals = [x.strip() for x in lines[0].split("|") if x.strip()]
                d_vals = [x.strip() for x in lines[2].split("|") if x.strip()]
                if len(h_vals) == len(d_vals):
                    quote_data = dict(zip(h_vals, d_vals))

        if not flow_data:
            print(f"    ⚠️ 未获取到资金流向数据")
            etfs.append({
                **etf,
                "main_net_flow": None,
                "jumbo_net_flow": None,
                "main_net_flow_5d": None,
                "main_net_flow_10d": None,
                "main_net_flow_20d": None,
                "close_price": float(quote_data.get("price", 0)) if quote_data else None,
                "change_pct": float(quote_data.get("change_percent", 0)) if quote_data else None,
                "amount": float(quote_data.get("amount", 0)) if quote_data else None,
                "has_data": False,
            })
            continue

        close_price = float(quote_data.get("price", 0)) if quote_data else flow_data.get("close_price", 0)
        change_pct = float(quote_data.get("change_percent", 0)) if quote_data else 0
        amount = float(quote_data.get("amount", 0)) if quote_data else (
            (flow_data.get("main_in_flow", 0) or 0) + (flow_data.get("main_out_flow", 0) or 0)
        )

        etf_entry = {
            **etf,
            "main_net_flow": flow_data.get("main_net_flow", 0) or 0,
            "jumbo_net_flow": flow_data.get("jumbo_net_flow", 0) or 0,
            "main_net_flow_5d": flow_data.get("main_net_flow_5d", 0) or 0,
            "main_net_flow_10d": flow_data.get("main_net_flow_10d", 0) or 0,
            "main_net_flow_20d": flow_data.get("main_net_flow_20d", 0) or 0,
            "main_in_flow": flow_data.get("main_in_flow", 0) or 0,
            "main_out_flow": flow_data.get("main_out_flow", 0) or 0,
            "block_net_flow": flow_data.get("block_net_flow", 0) or 0,
            "retail_in_flow": flow_data.get("retail_in_flow", 0) or 0,
            "retail_out_flow": flow_data.get("retail_out_flow", 0) or 0,
            "close_price": close_price,
            "change_pct": change_pct,
            "amount": amount,
            "has_data": True,
        }

        print(f"    ✅ 主力净流入: {etf_entry['main_net_flow']/1e8:.2f}亿")
        etfs.append(etf_entry)

    summary = build_summary(etfs)

    data["history"][date_str] = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "etfs": etfs,
    }
    data["last_updated"] = datetime.now().isoformat()

    # 按日期排序保留 key 顺序
    sorted_keys = sorted(data["history"].keys())
    new_history = {k: data["history"][k] for k in sorted_keys}
    data["history"] = new_history

    # 重算趋势累计（5日/10日/本月），修正历史 trend 恒为 0 的 bug
    recompute_trends(data["history"])

    save_history(data)

    main_net = summary["total_main_net_flow"]
    sign = "+" if main_net >= 0 else ""
    print(f"\n  === 国家队ETF资金流汇总 ({date_str}) ===")
    print(f"  总主力净流入: {sign}{main_net/1e8:.2f}亿")
    print(f"  总成交额: {summary['total_amount']/1e8:.2f}亿")
    print(f"  行为信号: {summary['signal']}")
    print(f"  净流入: {summary['net_in_count']}只 / 净流出: {summary['net_out_count']}只")
    print(f"  历史缓存: {len(data['history'])} 个交易日")
    print(f"  结果已保存至: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
