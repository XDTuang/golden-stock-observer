#!/usr/bin/env python3
"""
兜金观测 — 候选池数据获取脚本（跨平台版 · 腾讯 gtimg 接口）

数据源说明（2026-07 起生效）：
  东方财富 push2 接口在本机网络环境下已被屏蔽（curl rc=52 空回复），故切换为
  腾讯财经 gtimg 接口，全部走直连，Mac / Linux / Windows 常驻机器均可稳定取数。

  - 股票宇宙：akshare（新浪源）全量 A股代码列表，本地缓存 7 天
  - 成交额排行：腾讯 qt.gtimg.cn 实时快照（字段[37]=成交额/万元）
  - K线：web.ifzq.gtimg.cn 前复权日线（qfqday）

输出 output/kline_raw.json（结构不变）供 data_pipeline.py 消费：
  [{code, name, market, kline:[{date, open, last, high, low, volume}]}, ...]

HTTP 客户端统一走系统 curl（subprocess），在无代理的常驻机器
（launchd / 任务计划程序）上直连更稳定。

用法: python fetch_pool.py [--limit N] [--no-pipeline] [--dry-run]
"""

import json
import os
import re
import sys
import time
import argparse
import datetime
import subprocess
import concurrent.futures as cf
from urllib.parse import urlencode


# ── 路径配置 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_BIN = "/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "kline_raw.json")
CODES_CACHE = os.path.join(SCRIPT_DIR, "output", "all_a_codes.json")
CODES_CACHE_DAYS = 7

# ── 参数 ──
KLINE_DAYS = 250          # 需要获取的 K 线天数（前复权）
RETRY_LIMIT = 3           # 单只股票 / 单次请求最大重试次数
CONCURRENCY = 4           # K线并发拉取的工作线程数（温柔：避免单 IP 令牌桶被耗尽触发限流）
HTTP_TIMEOUT = 12         # 单次请求总超时（秒，curl --max-time）
CONNECT_TIMEOUT = 5       # 连接阶段超时（秒，curl --connect-timeout）
SUBPROC_TIMEOUT = 18      # subprocess 兜底硬超时（秒）：curl 卡死不返回时由 Python 强杀回收
MAX_BACKOFF = 8           # 指数退避上限（秒）
TURNOVER_BATCH = 60       # qt.gtimg.cn 每次查询的股票数
TURNOVER_CONCURRENCY = 6

HEADERS = [
    "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "-H", "Referer: https://gu.qq.com/",
]

# 腾讯接口
QT_URL = "https://qt.gtimg.cn/q"                       # 实时快照（成交额排行）
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"  # 前复权日线


def _curl_text(url: str) -> str:
    """用系统 curl 发起 GET，返回原始文本。失败抛异常（由调用方重试）。

    三重超时防护：
      - --connect-timeout：连接阶段（含 DNS）挂起时快速失败
      - --max-time：单次请求总耗时上限
      - subprocess.run(timeout=)：curl 进程本身卡死不返回时的硬兜底（强杀）
    """
    try:
        proc = subprocess.run(
            ["curl", "-s",
             "--connect-timeout", str(CONNECT_TIMEOUT),
             "--max-time", str(HTTP_TIMEOUT),
             *HEADERS, url],
            capture_output=True,
            timeout=SUBPROC_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"curl 进程超时(> {SUBPROC_TIMEOUT}s 未返回，疑似网络层卡死): {url[:60]}")
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "ignore").strip().replace("\n", " ")[:160]
        raise RuntimeError(f"curl rc={proc.returncode} {err}")
    # qt.gtimg.cn 返回 GBK，web.ifzq.gtimg.cn 返回 UTF-8，需容错解码
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return proc.stdout.decode("gbk", "ignore")


def _backoff(attempt: int):
    """指数退避：attempt 0→1s, 1→2s, 2→4s, 3→8s（封顶 MAX_BACKOFF）。
    避免对故障接口连续狂打，给对端/链路恢复时间。"""
    time.sleep(min(2 ** attempt, MAX_BACKOFF))


def _http_get_json(url: str, params: dict) -> dict:
    """用系统 curl 发起 GET 请求并返回解析后的 JSON。失败重试。"""
    full = f"{url}?{urlencode(params)}"
    last_err = None
    for _ in range(RETRY_LIMIT):
        try:
            out = _curl_text(full)
            if not out.strip():
                last_err = "empty body"
                _backoff(_)
                continue
            data = json.loads(out)
            if "data" not in data and data.get("code") not in (0, None):
                last_err = f"api code={data.get('code')}"
                _backoff(_)
                continue
            return data
        except Exception as e:
            last_err = str(e)[:80]
            _backoff(_)
    raise RuntimeError(f"请求失败 {url[:50]}: {last_err}")


def market_prefix(code6: str):
    """返回 (market短码, 是否纳入候选)。覆盖沪/深主板+科创/创业板。"""
    if code6.startswith(("60", "68", "90")):
        return "sh"
    if code6.startswith(("00", "30", "20")):
        return "sz"
    return None


def get_all_a_codes(force=False) -> list:
    """
    通过 akshare（新浪源，本机可达）获取全量 A股代码+名称。
    本地缓存 output/all_a_codes.json，7 天内复用，避免每日重复拉取。

    Returns: [{code:"sh600519", code6:"600519", name, market}, ...]
    """
    now = time.time()
    if not force and os.path.exists(CODES_CACHE):
        try:
            meta = os.path.getmtime(CODES_CACHE)
            if (now - meta) < CODES_CACHE_DAYS * 86400:
                with open(CODES_CACHE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if isinstance(cached, list) and cached:
                    print(f"  ✓ 复用缓存代码列表 ({len(cached)} 只, {(now-meta)/3600:.0f}h 前)")
                    return cached
        except Exception:
            pass

    import akshare as ak
    print("  🔄 拉取全量 A股代码列表 (akshare/新浪, 沪+深)...")
    t0 = time.time()
    out = []
    # 分市场拉取，规避北交所(bse.cn)在本机网络被屏蔽的问题
    # 北交所代码(8xxxxx)本就不在候选范围内，无需获取
    try:
        sh = ak.stock_info_sh_name_code()
        for _, row in sh.iterrows():
            code6 = str(row["证券代码"]).zfill(6)
            m = market_prefix(code6)
            if not m:
                continue
            out.append({"code": f"{m}{code6}", "code6": code6,
                        "name": str(row["证券简称"]).strip(), "market": m})
    except Exception as e:
        print(f"  ⚠️  沪市列表获取失败: {e}")
    try:
        sz = ak.stock_info_sz_name_code()
        for _, row in sz.iterrows():
            code6 = str(row["A股代码"]).zfill(6)
            m = market_prefix(code6)
            if not m:
                continue
            out.append({"code": f"{m}{code6}", "code6": code6,
                        "name": str(row["A股简称"]).strip(), "market": m})
    except Exception as e:
        print(f"  ⚠️  深市列表获取失败: {e}")
    print(f"  ✓ 获取到 {len(out)} 只 A股 ({time.time()-t0:.1f}s)")
    with open(CODES_CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def _parse_qt_turnover(text: str) -> dict:
    """解析 qt.gtimg.cn 快照文本，返回 {code: 成交额(万元)}。"""
    result = {}
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        m = re.match(r'v_(\w+)="(.*)";', line)
        if not m:
            continue
        code = m.group(1)            # 如 sh600519
        parts = m.group(2).split("~")
        if len(parts) <= 37:
            continue
        try:
            to = float(parts[37])     # 成交额(万元)
        except (ValueError, IndexError):
            to = 0.0
        result[code] = to
    return result


def fetch_turnover_ranking(codes: list, limit: int) -> list:
    """
    通过 qt.gtimg.cn 快照获取每只股票当日成交额，按降序取 TOP limit。

    Returns: [{code, code6, name, market, turnover}, ...] 已排序
    """
    print(f"📊 Step 1: 获取 A股成交额 TOP{limit} (腾讯 qt 快照)...")
    # 接口探活：先确认 qt.gtimg.cn 可达，避免批量拉取时整体卡死（launchd 不再挂 15 分钟）
    try:
        _curl_text(f"{QT_URL}=sh000001")
    except Exception as e:
        print(f"  ❌ qt.gtimg.cn 探活失败，网络可能不可达: {e}")
        sys.exit(2)
    t0 = time.time()

    # 切分为每批 TURNOVER_BATCH 只
    batches = [codes[i:i + TURNOVER_BATCH]
               for i in range(0, len(codes), TURNOVER_BATCH)]

    turnover_map = {}

    def _one(batch):
        q = ",".join(c["code"] for c in batch)
        for attempt in range(RETRY_LIMIT):
            try:
                text = _curl_text(f"{QT_URL}={q}")
                return _parse_qt_turnover(text)
            except Exception:
                _backoff(attempt)
        return {}

    with cf.ThreadPoolExecutor(max_workers=TURNOVER_CONCURRENCY) as ex:
        for res in ex.map(_one, batches):
            turnover_map.update(res)

    # 合并成交额到代码对象并排序
    ranked = []
    for c in codes:
        to = turnover_map.get(c["code"], 0.0)
        if to <= 0:
            continue
        item = dict(c)
        item["turnover"] = to
        ranked.append(item)
    ranked.sort(key=lambda x: x["turnover"], reverse=True)
    ranked = ranked[:limit]

    print(f"  ✓ 排序完成: {len(ranked)} 只有效 (top={ranked[0]['name'] if ranked else '-'} "
          f"{ranked[0]['turnover']/1e4:.1f}亿)" if ranked else "  ⚠️ 未获取到成交额")
    print(f"  ⏱  用时 {time.time()-t0:.1f}s")
    return ranked


def _fetch_kline_sina(stock: dict) -> dict | None:
    """新浪 K线兜底：稳、不被限流。返回与 fetch_kline 同构的字典或 None。"""
    code = stock["code"]
    url = (f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           f"CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={KLINE_DAYS}")
    for _ in range(RETRY_LIMIT):
        try:
            out = _curl_text(url)
            if not out.strip():
                _backoff(_); continue
            arr = json.loads(out)
            if not arr or len(arr) < 60:
                return None
            bars = [{
                "date": x["day"], "open": float(x["open"]), "last": float(x["close"]),
                "high": float(x["high"]), "low": float(x["low"]), "volume": float(x["volume"]),
            } for x in arr]
            return {"code": code, "name": stock["name"], "market": stock["market"], "kline": bars}
        except Exception:
            _backoff(_)
    return None


def fetch_kline(stock: dict) -> dict | None:
    """
    拉取单只股票 250 日 K线（前复权）。
    数据源：腾讯 gtimg(主) → 新浪(兜底，稳且不被限流)。

    Returns:
        {code, name, market, kline:[{date, open, last, high, low, volume}]} or None
        volume 单位：手（data_pipeline 会 ×100 转回股，与原 thsdk 口径一致）
    """
    code = stock["code"]
    params = {"param": f"{code},day,,,{KLINE_DAYS},qfq"}
    kline_url = f"{KLINE_URL}?{urlencode(params)}"

    # 1) 腾讯 gtimg（主）
    #    仅当返回有效 JSON 时使用；接口返回非 JSON（如 501 维护页）视为确定性不可用，
    #    立即降级新浪兜底，避免对故障接口空耗重试时间（否则 800 只会被拖到数小时）。
    for _ in range(RETRY_LIMIT):
        try:
            out = _curl_text(kline_url)
            if not out.strip():
                _backoff(_); continue
            j = json.loads(out)
        except json.JSONDecodeError:
            break  # 非 JSON（501/网关页），确定性失败，直接转新浪兜底
        except Exception as e:
            if _ == RETRY_LIMIT - 1:
                print(f"  ⚠️  {stock['name']} ({code}) gtimg K线失败: {e}")
            _backoff(_); continue
        node = (j.get("data") or {}).get(code) or \
               (j.get("data") or {}).get(stock.get("code6", ""))
        if not node:
            break
        arr = node.get("qfqday") or node.get("day")
        if not arr or len(arr) < 60:
            break
        bars = []
        for p in arr:
            # [date, open, close, high, low, volume(手)]
            bars.append({
                "date": p[0],
                "open": float(p[1]),
                "last": float(p[2]),
                "high": float(p[3]),
                "low": float(p[4]),
                "volume": float(p[5]),
            })
        return {
            "code": code,
            "name": stock["name"],
            "market": stock["market"],
            "kline": bars,
        }

    # 2) 新浪兜底（稳，不被限流）
    try:
        sina = _fetch_kline_sina(stock)
        if sina:
            return sina
    except Exception as e:
        print(f"  ⚠️  {stock['name']} ({code}) 新浪兜底也失败: {e}")
    return None


def fetch_all_klines(stocks: list, concurrency: int = CONCURRENCY) -> tuple:
    """
    并发拉取全部候选股的 K 线，含自适应降级。

    逻辑：
      1. 先用小批量(min(4, N))以 `concurrency` 并发探测网络；
      2. 若探测成功率 < 50%，自动降级为串行 (workers=1)；
      3. 否则全程并发。

    Returns:
        (results, failed_codes)
    """
    def _run(batch, workers):
        out, fails = [], []
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            fmap = {ex.submit(fetch_kline, s): s for s in batch}
            done = 0
            for fut in cf.as_completed(fmap):
                done += 1
                s = fmap[fut]
                try:
                    r = fut.result()
                except Exception as e:
                    r = None
                    print(f"  ⚠️  {s['name']} ({s['code']}) 异常: {e}")
                if r:
                    out.append(r)
                else:
                    fails.append(s["code"])
                if done % 50 == 0 or done == len(batch):
                    el = time.time() - t0
                    rate = done / el if el > 0 else 0
                    print(f"  [{done}/{len(batch)}] ✓{len(out)} ✗{len(fails)} | {rate:.1f}只/s")
        return out, fails

    total = len(stocks)
    if total == 0:
        return [], []

    probe_n = min(4, total)
    print(f"\n📈 Step 2: K线拉取 (每只{KLINE_DAYS}日)...")
    print(f"  🔍 探测网络并发能力 (前 {probe_n} 只, 并发 {concurrency})...")
    probe_res, probe_fail = _run(stocks[:probe_n], concurrency)

    if len(probe_res) == 0:
        print(f"  ❌ 网络探测 0/{probe_n} 成功，疑似数据源整体不可达，终止 K线拉取（避免空跑 {total} 只）")
        sys.exit(2)

    if len(probe_res) < max(1, probe_n // 2):
        print(f"  ⚠️  并发探测成功率过低 ({len(probe_res)}/{probe_n})，降级为串行模式")
        rest_res, rest_fail = _run(stocks[probe_n:], 1)
        results = probe_res + rest_res
        failed_codes = probe_fail + rest_fail
    else:
        rest_res, rest_fail = _run(stocks[probe_n:], concurrency)
        results = probe_res + rest_res
        failed_codes = probe_fail + rest_fail

    return results, failed_codes


def main():
    parser = argparse.ArgumentParser(description="兜金观测候选池数据获取（跨平台·腾讯 gtimg）")
    parser.add_argument("--limit", type=int, default=800, help="最多获取 N 只股票 (默认800)")
    parser.add_argument("--no-pipeline", action="store_true", help="仅获取 K线数据，不运行信号管线")
    parser.add_argument("--dry-run", action="store_true", help="仅获取股票列表，不拉取 K线")
    parser.add_argument("--force-codes", action="store_true", help="强制刷新代码列表缓存")
    args = parser.parse_args()

    limit = args.limit
    print("═══ 兜金观测 · 候选池数据更新（跨平台·腾讯 gtimg）═══")
    print(f"  目标: A股成交额 TOP{limit}")
    print(f"  K线: {KLINE_DAYS}日前复权 | 并发: {CONCURRENCY} 线程")
    print()

    # Step 0: 全量代码宇宙
    codes = get_all_a_codes(force=args.force_codes)
    if not codes:
        print("  ❌ 未获取到代码列表，退出")
        sys.exit(1)

    # Step 1: 成交额排行 → TOP N
    stocks = fetch_turnover_ranking(codes, limit)
    if not stocks:
        print("  ❌ 未获取到任何股票，退出")
        sys.exit(1)

    # Step 1.5: 打印前 5 名确认
    print("\n  📋 TOP5 确认:")
    for i, s in enumerate(stocks[:5], 1):
        print(f"    {i}. {s['name']} ({s['code']}) 成交额:{s['turnover']/1e4:.1f}亿")

    if args.dry_run:
        print("\n  ⏭️  --dry-run 模式，仅获取列表")
        return

    # Step 2: 并发拉取 K线（含自适应降级，见 fetch_all_klines）
    t0_global = time.time()
    total = len(stocks)
    results, failed_codes = fetch_all_klines(stocks, CONCURRENCY)

    elapsed = time.time() - t0_global
    print(f"  ✅ K线拉取完成: {len(results)}只有效数据 ({elapsed:.0f}s)")
    if total:
        print(f"     成功率: {len(results)/total*100:.1f}%")

    # Step 3: 写入 kline_raw.json（原子替换，防中断损坏）
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT_FILE)
    print(f"  ✓ 已写入 {OUTPUT_FILE} ({len(results)}只)")

    # Step 4: 信号计算 + 生成页面（调用 data_pipeline.py）
    if not args.no_pipeline:
        print()
        print("🧮  Step 3: 信号计算 + 生成页面...")
        pipeline_script = os.path.join(SCRIPT_DIR, "data_pipeline.py")
        ret = os.system(f'cd "{SCRIPT_DIR}" && "{PYTHON_BIN}" "{pipeline_script}"')
        if ret != 0:
            print("  ⚠️  data_pipeline.py 返回非零退出码")
    else:
        print()
        print("  ⏭️  跳过管线步骤 (--no-pipeline)")

    print()
    print("=" * 40)
    print("✅ 全部完成！")
    print("=" * 40)


if __name__ == "__main__":
    main()
