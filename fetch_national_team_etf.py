#!/usr/bin/env python3
"""
兜金观测 — 国家队ETF资金流向采集脚本 v3

v3 改动（云端化根治）:
  - 数据源从 westock-data（本机 WorkBuddy skill，云端不存在）切换为
    新浪财经资金流 HTTP 接口（全球可达，GitHub Actions runner 可访问）
  - 字段映射: r0_net(主力净流入) → main_net_flow, trade → close_price,
    changeratio*100 → change_pct
  - 5d/10d/20d 通过 num=20 拉最近20个交易日聚合

用法:
  python fetch_national_team_etf.py                    # 增量：采集今日
  python fetch_national_team_etf.py --date YYYY-MM-DD  # 指定日期
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
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "national_team_etf.json")

# 新浪财经资金流接口（个股/ETF，返回最近 N 个交易日的资金流）
SINA_FLOW_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)",
           "Referer": "https://finance.sina.com.cn/"}

# 国家队核心ETF列表（中央汇金投资+中央汇金资管 2025年报公开持仓）
NATIONAL_TEAM_ETFS = [
    # ═══ 沪深300（4只）═══
    {"code": "sh510300", "name": "华泰柏瑞沪深300ETF", "category": "沪深300", "short_name": "沪深300ETF华泰柏瑞"},
    {"code": "sh510310", "name": "易方达沪深300ETF", "category": "沪深300", "short_name": "沪深300ETF易方达"},
    {"code": "sh510330", "name": "华夏沪深300ETF", "category": "沪深300", "short_name": "沪深300ETF华夏"},
    {"code": "sz159919", "name": "嘉实沪深300ETF", "category": "沪深300", "short_name": "沪深300ETF嘉实"},
    # ═══ 上证50（2只）═══
    {"code": "sh510050", "name": "华夏上证50ETF", "category": "上证50", "short_name": "上证50ETF华夏"},
    {"code": "sh510100", "name": "易方达上证50ETF", "category": "上证50", "short_name": "上证50ETF易方达"},
    # ═══ 中证500（3只）═══
    {"code": "sh510500", "name": "南方中证500ETF", "category": "中证500", "short_name": "中证500ETF南方"},
    {"code": "sh512500", "name": "华夏中证500ETF", "category": "中证500", "short_name": "中证500ETF华夏"},
    {"code": "sz159922", "name": "嘉实中证500ETF", "category": "中证500", "short_name": "中证500ETF嘉实"},
    # ═══ 创业板（3只）═══
    {"code": "sz159915", "name": "易方达创业板ETF", "category": "创业板", "short_name": "创业板ETF易方达"},
    {"code": "sz159952", "name": "广发创业板ETF", "category": "创业板", "short_name": "创业板ETF广发"},
    {"code": "sz159977", "name": "天弘创业板ETF", "category": "创业板", "short_name": "创业板ETF天弘"},
    # ═══ 科创50（3只）═══
    {"code": "sh588000", "name": "华夏科创50ETF", "category": "科创50", "short_name": "科创50ETF华夏"},
    {"code": "sh588080", "name": "易方达科创50ETF", "category": "科创50", "short_name": "科创50ETF易方达"},
    {"code": "sh588050", "name": "工银瑞信科创50ETF", "category": "科创50", "short_name": "科创50ETF工银"},
    # ═══ 中证1000（4只）═══
    {"code": "sh512100", "name": "南方中证1000ETF", "category": "中证1000", "short_name": "中证1000ETF南方"},
    {"code": "sz159845", "name": "华夏中证1000ETF", "category": "中证1000", "short_name": "中证1000ETF华夏"},
    {"code": "sh560010", "name": "广发中证1000ETF", "category": "中证1000", "short_name": "中证1000ETF广发"},
    {"code": "sz159629", "name": "富国中证1000ETF", "category": "中证1000", "short_name": "中证1000ETF富国"},
    # ═══ 其他宽基（2只）═══
    {"code": "sh510180", "name": "华安上证180ETF", "category": "上证180", "short_name": "上证180ETF华安"},
    {"code": "sz159901", "name": "易方达深证100ETF", "category": "深证100", "short_name": "深证100ETF易方达"},
]

CODE_TO_ETF = {e["code"]: e for e in NATIONAL_TEAM_ETFS}


def fetch_sina_flow(code: str, num: int = 20) -> list:
    """从新浪接口拉取单只 ETF 最近 num 个交易日的资金流。

    返回按日期倒序（最新在前）的 rows，每项含:
      opendate, trade, changeratio, netamount, r0_net
    """
    if requests is None:
        return []
    params = {"page": 1, "num": num, "sort": "opendate", "asc": 0, "daima": code}
    for attempt in range(3):
        try:
            r = requests.get(SINA_FLOW_URL, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                return []
            return data
        except Exception as e:
            if attempt == 2:
                print(f"    ⚠️ 新浪接口失败: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
                return []
            time.sleep(1 + attempt)
    return []


def build_summary(etfs: list) -> dict:
    """分析 ETF 资金流向，生成汇总统计（与 v2 保持一致）"""
    total_main_net = sum(e.get("main_net_flow", 0) or 0 for e in etfs)
    total_jumbo_net = sum(e.get("jumbo_net_flow", 0) or 0 for e in etfs)
    total_amount = sum(e.get("amount", 0) or 0 for e in etfs)
    total_main_in = sum(e.get("main_in_flow", 0) or 0 for e in etfs)
    total_main_out = sum(e.get("main_out_flow", 0) or 0 for e in etfs)

    category_nets = {}
    for e in etfs:
        cat = e.get("category", "其他")
        category_nets[cat] = category_nets.get(cat, 0) + (e.get("main_net_flow", 0) or 0)

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
    """基于历史每日总主力净流入序列，重算趋势累计（口径与 v2 一致）。"""
    dates = sorted(history.keys())
    if not dates:
        return
    series = [(d, (history[d].get("summary", {}) or {}).get("total_main_net_flow", 0) or 0)
              for d in dates]
    for i, (d, _v) in enumerate(series):
        trend_5d = sum(x[1] for x in series[max(0, i - 4):i + 1])
        trend_10d = sum(x[1] for x in series[max(0, i - 9):i + 1])
        ym = d[:7]
        trend_mtd = sum(x[1] for x in series if x[0][:7] == ym and x[0] <= d)
        if "summary" not in history[d] or not isinstance(history[d]["summary"], dict):
            history[d]["summary"] = {}
        history[d]["summary"]["trend_5d"] = trend_5d
        history[d]["summary"]["trend_10d"] = trend_10d
        history[d]["summary"]["trend_mtd"] = trend_mtd


def load_history():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": {}, "last_updated": None}


def save_history(data: dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def main():
    force_overwrite = False
    date_str = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--date":
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

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取国家队ETF资金流向 ({date_str})...（新浪财经源）")

    data = load_history()

    if date_str in data.get("history", {}) and not force_overwrite:
        print(f"  ℹ️ {date_str} 已有数据，跳过（加 --force-overwrite 可覆盖）")
        print(f"  历史缓存: {len(data['history'])} 个交易日")
        return

    etfs = []
    for etf in NATIONAL_TEAM_ETFS:
        code = etf["code"]
        rows = fetch_sina_flow(code, num=20)
        if not rows:
            print(f"  {etf['short_name']} ({code}) ... ⚠️ 无数据")
            etfs.append({**etf, "main_net_flow": None, "jumbo_net_flow": None,
                         "main_net_flow_5d": None, "main_net_flow_10d": None,
                         "main_net_flow_20d": None, "close_price": None,
                         "change_pct": None, "amount": None, "has_data": False})
            continue

        # 找当日行（rows 倒序，最新在前）
        today_row = None
        for r in rows:
            if str(r.get("opendate")) == date_str:
                today_row = r
                break
        if not today_row:
            # 非交易日或当日数据未出：取最新一条
            today_row = rows[0]

        def _net(row):
            try:
                return float(row.get("r0_net") or 0)
            except (ValueError, TypeError):
                return 0.0

        main_net = _net(today_row)
        # 5d/10d/20d 聚合（rows 倒序，取前 N 条）
        series = [_net(r) for r in rows]
        net_5d = sum(series[:5])
        net_10d = sum(series[:10])
        net_20d = sum(series[:20])

        try:
            close_price = float(today_row.get("trade") or 0)
        except (ValueError, TypeError):
            close_price = 0.0
        try:
            change_pct = float(today_row.get("changeratio") or 0) * 100
        except (ValueError, TypeError):
            change_pct = 0.0

        etf_entry = {
            **etf,
            "main_net_flow": main_net,
            "jumbo_net_flow": 0,
            "main_net_flow_5d": net_5d,
            "main_net_flow_10d": net_10d,
            "main_net_flow_20d": net_20d,
            "main_in_flow": 0,
            "main_out_flow": 0,
            "block_net_flow": 0,
            "retail_in_flow": 0,
            "retail_out_flow": 0,
            "close_price": close_price,
            "change_pct": round(change_pct, 2),
            "amount": 0,
            "has_data": True,
        }
        print(f"  {etf['short_name']} ({code}) ... ✅ 主力净流入 {main_net/1e8:+.2f}亿")
        etfs.append(etf_entry)

    summary = build_summary(etfs)

    data["history"][date_str] = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "etfs": etfs,
    }
    data["last_updated"] = datetime.now().isoformat()

    sorted_keys = sorted(data["history"].keys())
    data["history"] = {k: data["history"][k] for k in sorted_keys}

    recompute_trends(data["history"])
    save_history(data)

    main_net = summary["total_main_net_flow"]
    sign = "+" if main_net >= 0 else ""
    print(f"\n  === 国家队ETF资金流汇总 ({date_str}) ===")
    print(f"  总主力净流入: {sign}{main_net/1e8:.2f}亿")
    print(f"  行为信号: {summary['signal']}")
    print(f"  净流入: {summary['net_in_count']}只 / 净流出: {summary['net_out_count']}只")
    print(f"  历史缓存: {len(data['history'])} 个交易日")
    print(f"  结果已保存至: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
