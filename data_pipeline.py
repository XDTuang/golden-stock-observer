#!/usr/bin/env python3
"""
金股观测 — 数据处理管线
从 westock-data 获取的 K 线数据 JSON，通过 signals.py 计算信号，
输出前端可用的 signals.json。
"""

import json
import sys
import os
import tempfile
import pandas as pd
import requests
import time

# 导入信号引擎
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals import analyze_stock, batch_analyze, compute_four_volume

# 交易日历 / 数据新鲜度校验
from market_calendar import eval_freshness, last_trading_day


def atomic_write_json(path: str, obj) -> None:
    """
    原子写入 JSON：先写临时文件再 os.replace，避免进程中断（Ctrl-C /
    接口断开）产生半个文件导致 signals.json 损坏、前端加载失败。

    同时保留一份「full」副本到同目录 signals_full.json 供调试/回溯，
    供线上服务使用的精简版由 slim_signals.py 负责生成。
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", prefix=".sig_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, path)  # 原子替换
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def fetch_industry_info(code: str) -> dict:
    """
    从东方财富获取行业分类（一级/二级/三级）。

    Args:
        code: 6位数字代码（如 '600519'）

    Returns:
        {level1: str, level2: str, level3: str} 或空dict
    """
    try:
        # 确定市场前缀
        prefix = '1.' if code.startswith(('6', '68')) else '0.'
        # 股票详情API获取申万二级 (f127) 和概念 (f129)
        url_detail = f"https://push2.eastmoney.com/api/qt/stock/get?secid={prefix}{code}&fields=f57,f58,f100,f127,f128,f129"
        resp = requests.get(url_detail, timeout=8)
        data = resp.json().get("data", {}) if resp.status_code == 200 else {}

        # F10公司概况获取一级行业
        market_prefix = 'SH' if code.startswith('6') else 'SZ'
        url_f10 = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code={market_prefix}{code}"
        resp_f10 = requests.get(url_f10, timeout=8)
        f10_data = resp_f10.json() if resp_f10.status_code == 200 else {}

        level1 = f10_data.get("jbzl", {}).get("sshy", data.get("f100", ""))
        level2 = data.get("f127", "")
        # 三级行业: 优先取F10中证监会行业(sszjhhy), 其格式为"门类-大类"
        # 或使用地域板块(f128)作为补充
        sszjhhy = f10_data.get("jbzl", {}).get("sszjhhy", "")
        level3 = sszjhhy if sszjhhy else data.get("f128", "")

        return {
            "level1": level1 or "",
            "level2": level2 or "",
            "level3": level3 or "",
        }
    except Exception as e:
        return {"level1": "", "level2": "", "level3": ""}


def load_kline_data(input_file: str) -> dict:
    """加载原始K线JSON，转换为signals.py需要的格式"""
    with open(input_file, "r") as f:
        raw_data = json.load(f)

    stocks_data = {}
    for stock in raw_data:
        code = stock["code"]
        name = stock["name"]
        market_code = stock["market"]

        # 确定市场类型
        if market_code == "sh":
            if code.startswith("sh688"):
                market = "科创板"
            else:
                market = "主板"
        elif market_code == "sz":
            if code.startswith("sz300") or code.startswith("sz301"):
                market = "创业板"
            else:
                market = "主板"
        else:
            market = market_code

        # 转换K线数据为DataFrame
        kline = stock["kline"]
        if not kline:
            continue

        records = []
        for bar in kline:
            # westock-data kline 字段: date, open, last(收盘), high, low, volume(手), amount(元)
            records.append({
                "date": bar["date"],
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": float(bar["low"]),
                "close": float(bar["last"]),   # westock 用 'last' 表示收盘价
                "volume": float(bar["volume"]) * 100,  # 手 → 股
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")

        stocks_data[code] = {
            "df": df,
            "name": name,
            "market": market,
        }

    # 批量获取行业分类（并行，最多8路并发）
    print("Fetching industry data...")
    industry_map = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    codes_list = list(stocks_data.keys())
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for code in codes_list:
            raw_code = code.replace("sh", "").replace("sz", "")
            futures[executor.submit(fetch_industry_info, raw_code)] = code
        for future in as_completed(futures):
            code = futures[future]
            try:
                industry_map[code] = future.result(timeout=15)
            except Exception:
                industry_map[code] = {"level1": "", "level2": "", "level3": ""}
    industry_count = sum(1 for v in industry_map.values() if v.get("level1"))
    print(f"Industry data fetched: {industry_count}/{len(industry_map)} stocks")

    return stocks_data, industry_map


def generate_stats(results: list) -> dict:
    """生成统计摘要（五策略体系）"""
    total = len([r for r in results if r.get("has_data")])
    stats = {
        "total_stocks": total,
        "六六大顺": 0,
        "五福同享": 0,
        "四喜临门": 0,
        "三线共振": 0,
        "双线": 0,
        "单信号": 0,
        "ema_7_7": 0,
        "ema_5_6": 0,
        "ema_3_4": 0,
        "ema_0_2": 0,
        "ema_distribution": {},  # 新增：EMA分数详细分布
        "highest_score": 0,
        "highest_score_stock": "",
        "top_signals": [],
    }
    
    # EMA分布统计
    ema_dist = {}


    for r in results:
        if not r.get("has_data"):
            continue
        # 根据 signal_count 和 ema_strong 判断等级
        # 注意：只有ema_strong=true时，才计入高等级统计（和前端卡片逻辑一致）
        score = r.get("score", {})
        signal_count = score.get("signal_count", 0)
        ema_strong = score.get("ema_strong", False)
        
        # 只有ema_strong=true时，才计入统计
        if ema_strong:
            if signal_count >= 6:
                stats["六六大顺"] += 1
            elif signal_count >= 5:
                stats["五福同享"] += 1
            elif signal_count >= 4:
                stats["四喜临门"] += 1
            elif signal_count >= 3:
                stats["三线共振"] += 1
            elif signal_count >= 2:
                stats["双线"] += 1
            elif signal_count >= 1:
                stats["单信号"] += 1

        ema = r.get("ema_score", 0)
        ema_str = str(ema)
        ema_dist[ema_str] = ema_dist.get(ema_str, 0) + 1
        
        if ema >= 7:
            stats["ema_7_7"] += 1
        elif ema >= 5:
            stats["ema_5_6"] += 1
        elif ema >= 3:
            stats["ema_3_4"] += 1
        else:
            stats["ema_0_2"] += 1

        total_score = r.get("score", {}).get("total_score", 0)
        if total_score > stats["highest_score"]:
            stats["highest_score"] = total_score
            stats["highest_score_stock"] = f"{r.get('name','')}({r.get('code','')})"

    stats["ema_distribution"] = ema_dist

    # 短线（缠论触发）和中长线（趋势+机构）分组
    short_term = [r for r in results if r.get("has_data") and r.get("score", {}).get("signal_count", 0) >= 2
                  and r.get("chan_buy")]
    long_term = [r for r in results if r.get("has_data") and r.get("uptrend") and r.get("inst_red")]

    short_term.sort(key=lambda x: x.get("score", {}).get("total_score", 0), reverse=True)
    long_term.sort(key=lambda x: x.get("score", {}).get("total_score", 0), reverse=True)

    stats["short_term_count"] = len(short_term)
    stats["long_term_count"] = len(long_term)

    return stats


def update_top10_history(results, max_days=20):
    """更新每日TOP10历史缓存，保留最多20个交易日"""
    top10_path = os.path.join(os.path.dirname(__file__), "output", "top10_history.json")
    
    # 加载已有历史
    if os.path.exists(top10_path):
        with open(top10_path, "r") as f:
            history = json.load(f)
    else:
        history = {}
    
    # 获取当前日期
    current_date = None
    for r in results:
        if r.get("date"):
            current_date = r["date"]
            break
    if not current_date:
        current_date = str(pd.Timestamp.now())[:10]
    
    # 提取TOP10
    top10 = [r for r in results if r.get("has_data")][:10]
    top10_entries = []
    for r in top10:
        s = r.get("score", {})
        ind = r.get("industry", {})
        top10_entries.append({
            "code": r.get("code", ""),
            "name": r.get("name", ""),
            "market": r.get("market", ""),
            "ema_score": r.get("ema_score", 0),
            "close": r.get("close", 0),
            "change_pct": r.get("change_pct", 0),
            "total_score": s.get("total_score", 0),
            "grade": s.get("grade", ""),
            "signals": s.get("signals", []),
            "signal_count": s.get("signal_count", 0),
            "industry": ind,
        })
    
    history[current_date] = {
        "date": current_date,
        "generated_at": str(pd.Timestamp.now()),
        "top10": top10_entries,
    }
    
    # 保留最近 max_days 天
    dates = sorted(history.keys(), reverse=True)
    if len(dates) > max_days:
        for old_date in dates[max_days:]:
            del history[old_date]
    
    # 保存（原子写入）
    os.makedirs(os.path.dirname(top10_path), exist_ok=True)
    atomic_write_json(top10_path, history)

    return history


def build_observation_pool(results):
    """
    构建观测池：从全量候选股中筛选
      - EMA 强趋势（ema_strong = True）且
      - 信号数 >= 3
    的股票。候选股本身即由 fetch_pool 按成交额 TOP N 取得，已具备流动性，
    无需再按成交量二次筛选（旧逻辑中「TOP800 内」实为冗余，且当 N<800 时会
    误杀合格股）。

    按日期存储，仅保留最近 20 个交易日（动态窗口，不再写死起始日期）。
    写入采用原子替换，避免中断损坏 21MB 的池文件。
    """
    # 合格条件：EMA 强趋势 + 信号数 >= 3
    qualified = [r for r in results
                 if r.get("has_data")
                 and r.get("score", {}).get("ema_strong", False)
                 and r.get("score", {}).get("signal_count", 0) >= 3]

    # 读取已有观测池（保留历史，便于前端展示近期入选轨迹）
    output_file = os.path.join(os.path.dirname(__file__), "output", "observation_pool.json")
    pool = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, "r") as f:
                pool = json.load(f)
        except Exception:
            pool = {}

    if not qualified:
        print("  ⚠️  观测池：没有符合条件的股票（需 EMA强 + 信号数>=3），保留历史")
        all_stocks = []
        for date_stocks in pool.values():
            all_stocks.extend(date_stocks)
        return all_stocks

    # 按信号数降序排序
    qualified.sort(key=lambda x: x.get("score", {}).get("signal_count", 0), reverse=True)

    # 当前日期（取第一条有数据股票的日期）
    current_date = next((r["date"] for r in results if r.get("date")), None)
    if not current_date:
        current_date = str(pd.Timestamp.now())[:10]

    # 存入当日数据（动态窗口，无写死起始日）
    for stock in qualified:
        stock["pool_date"] = current_date
    pool[current_date] = qualified
    print(f"  ✅ 观测池更新：{current_date}，{len(qualified)} 只股票（EMA强+信号>=3）")

    # 仅保留最近 20 个交易日
    dates = sorted(pool.keys(), reverse=True)
    for old_date in dates[20:]:
        del pool[old_date]

    # 原子写入（防中断损坏）
    atomic_write_json(output_file, pool)

    # 返回扁平化数组（供 signals.json 使用，slim_signals 会进一步裁剪字段）
    all_stocks = []
    for date_stocks in pool.values():
        all_stocks.extend(date_stocks)
    return all_stocks


def main():
    input_file = os.path.join(os.path.dirname(__file__), "output", "kline_raw.json")
    output_file = os.path.join(os.path.dirname(__file__), "output", "signals.json")

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run fetch_data.sh first.")
        sys.exit(1)

    print("Loading K-line data...")
    stocks_data, industry_map = load_kline_data(input_file)
    print(f"Loaded {len(stocks_data)} stocks")

    print("Computing signals (fast path: 缠论/金钻按EMA门控, 四量图懒加载)...")
    results = []
    for code, info in stocks_data.items():
        r = analyze_stock(info["df"], code, info["name"], info["market"], industry_map.get(code), compute_fv=False)
        results.append(r)
    results.sort(key=lambda x: x.get("score", {}).get("total_score", 0) if x.get("has_data") else 0, reverse=True)

    # ── 四量图懒加载：仅对展示价值高的股票计算 ──
    # 不参与评分，仅前端四量图展示。对"评分前100 或 信号数>=2"的股计算，
    # 既保留绝大多数被查看卡片的图表，又避免对全部 800 只做无用 O(n) 计算。
    top_codes = {r["code"] for r in results[:100] if r.get("has_data")}
    sig_codes = {r["code"] for r in results if r.get("has_data") and r.get("score", {}).get("signal_count", 0) >= 2}
    fv_codes = top_codes | sig_codes
    fv_count = 0
    for r in results:
        if r.get("code") in fv_codes and r.get("has_data"):
            info = stocks_data.get(r["code"])
            if info:
                r["four_volume"] = compute_four_volume(info["df"])
                fv_count += 1
    has_data_total = len([r for r in results if r.get("has_data")])
    print(f"  四量图懒加载：{fv_count}/{has_data_total} 只计算（其余展示'暂无'）")

    # 统计
    stats = generate_stats(results)

    # 观测池
    observation_pool = build_observation_pool(results)

    # TOP10 历史缓存
    top10_history = update_top10_history(results)

    # ── 数据新鲜度校验（数据更新策略精准度的核心闸门）──
    latest_data_date = None
    for r in results:
        if r.get("has_data") and r.get("date"):
            if latest_data_date is None or r["date"] > latest_data_date:
                latest_data_date = r["date"]

    freshness = eval_freshness(latest_data_date) if latest_data_date else {
        "latest_data_date": None,
        "expected_date": None,
        "is_fresh": False,
        "gap_days": -1,
        "checked_at": str(pd.Timestamp.now()),
        "status": "unknown",
    }

    # 输出（full 版写入 output/signals.json，作为唯一全量来源；原子写入防中断损坏）
    output = {
        "generated_at": str(pd.Timestamp.now()),
        "data_date": latest_data_date,
        "freshness": freshness,
        "stats": stats,
        "observation_pool": observation_pool,
        "top10_history": top10_history,
        "stocks": results,
    }

    atomic_write_json(output_file, output)
    print(f"signals.json（全量）已写入: {output_file}")

    # 同时输出一份到项目根目录，供本地 index.html fetch 使用
    root_output = os.path.join(os.path.dirname(__file__), "signals.json")
    atomic_write_json(root_output, output)
    print(f"signals.json 已同步到项目根目录（线上精简版由 slim_signals.py 生成）")

    print(f"\n=== 信号统计 ===")
    print(f"总计: {stats['total_stocks']}只")
    for grade in ["五福同享", "四喜临门", "三线共振", "双线", "单信号"]:
        if stats.get(grade, 0) > 0:
            print(f"  {grade}: {stats[grade]}只")
    print(f"\nEMA趋势分布:")
    print(f"  7/7最强: {stats['ema_7_7']}只")
    print(f"  5-6/7: {stats['ema_5_6']}只")
    print(f"  3-4/7: {stats['ema_3_4']}只")
    print(f"  0-2/7: {stats['ema_0_2']}只")
    print(f"\n短线信号: {stats['short_term_count']}只")
    print(f"中长线确认: {stats['long_term_count']}只")
    print(f"\n结果已保存至: {output_file}")

    # 生成前端页面（fetch 动态加载版）——
    # 注意：index.html 不再在此内嵌数据。页面采用 fetch 加载外部 JSON，
    # 由 slim_signals.py（生产/部署）或 rebuild_html.py（本地）基于
    # index_template.html 生成。单一构建路径，避免「内嵌版」与「fetch 版」
    # 数据不一致、以及把 36MB 全量数据塞进 HTML。
    print("ℹ️  index.html 由 slim_signals.py / rebuild_html.py 生成，此处跳过内嵌。")

    # 打印前5名
    print(f"\n=== TOP 股票 ===")
    for i, r in enumerate(results[:5]):
        if r.get("has_data"):
            s = r["score"]
            print(f"  {i+1}. {r['name']}({r['code']}) | {s['grade']} | "
                  f"评分:{s['total_score']} | EMA:{r['ema_score']}/7 | "
                  f"信号:{','.join(s['signals'])}")


if __name__ == "__main__":
    main()
