#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜宝金钻 · 三档选股门控扫描
================================
在「金钻三子形态」策略(analyze)之上建立三档【选股范围门控】，
门控只决定"哪些股票进入扫描范围"，金钻细节规则完全不变。

三档门控：
  1) all_a             —— 全A（无门控，扫描全部 A股）
  2) pool              —— 当前门控：与主站“stock”股票池门控一致，扫描成交额 TOP-800 全量
  3) sector_top100_to4 —— 每个板块按"当日交易总量(成交额)"取前 100，
                          且换手率 >= 4% 的个股，合并为扫描范围

数据管线（一次性取全市场，三档共享）：
  - 全A代码列表        ：akshare（新浪源，本地缓存 7 天）
  - 成交额/换手率快照  ：腾讯 qt.gtimg.cn（field[37]=成交额万元, field[38]=换手率%）
  - 板块→成份股映射     ：新浪行业板块（newSinaHy.php 列表 + getHQNodeData 成份股，稳定可用；
                          失败则板块门控暂不可用，可 --sectors-only 重试）
  - K线(前复权250日)    ：腾讯 web.ifzq.gtimg.cn（主源，与通达信对齐）；新浪备选（并发拉取，可续传，退避重试）
  - 金钻三子形态        ：复用 golden_diamond_viewer/server.py 的 analyze()（唯一真值源）

产出：
  output/gate_data.json         —— 三档合并结果（UI 直接消费）
  output/gate_<gate>.json       —— 各档独立结果

用法：
  python gate_scan.py                      # 全量重建 K线（带续传）后扫描三档
  python gate_scan.py --daily              # 增量日更（只追加最新 K线，温柔抓取，推荐每日自动化）
  python gate_scan.py --full               # 强制全量重建 K线（带续传）
  python gate_scan.py --gates pool         # 只扫指定档（逗号分隔）
  python gate_scan.py --no-kline            # 复用已有 kline_all.json
  python gate_scan.py --sectors-only        # 仅重抓板块映射并重算板块门控
  python gate_scan.py --dry-run             # 仅统计各档范围命中数
"""
import os
import sys
import json
import time
import random
import datetime
import subprocess
import threading
import concurrent.futures as cf
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
KLINE_ALL = os.path.join(OUT, "kline_all.json")
SNAP_FILE = os.path.join(OUT, "gate_snapshot.json")
SECTOR_FILE = os.path.join(OUT, "gate_sectors.json")
GATE_DATA = os.path.join(OUT, "gate_data.json")
POOL = os.path.join(BASE, "candidate_pool.json")
KLINE_RAW = os.path.join(OUT, "kline_raw.json")
# 原始兜宝金钻机制产出（golden_diamond_scan.py + server.analyze + 腾讯 gtimg）：
# 第二档『当前门控』直接照搬此文件，不重算、不漂移。
GOLDEN_DIAMOND = os.path.join(OUT, "golden_diamond.json")

PYTHON_BIN = "/Users/samt/.workbuddy/binaries/python/envs/default/bin/python"
sys.path.insert(0, os.path.join(BASE, "golden_diamond_viewer"))
from server import analyze  # noqa: E402  唯一经实盘校验的真值源
sys.path.insert(0, BASE)
import pandas as pd  # noqa: E402  缠论 DataFrame 构建
from signals import check_chan_buy_signal  # noqa: E402  主站通达信缠论买点（同源，原始买点不做 EMA 门控）

RANK = {"金钻起涨": 3, "买入": 2, "红区黄柱连续": 1}
GATE_LABELS = {
    "all_a": "全A市场",
    "pool": "当前门控（成交额TOP800）",
    "sector_top100_to4": "板块前100·换手≥4%",
}
DEFAULT_GATE = "pool"

HEADERS = ["-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
           "-H", "Referer: https://gu.qq.com/"]
HTTP_TIMEOUT = 30
CONCURRENCY = 5           # K线并发（从3提到5，配合双倍超时提升全A拉取吞吐；单 IP 令牌桶仍可控）
JITTER = (0.2, 0.6)       # 每次请求前的随机抖动延迟区间（秒）
KL_RETRIES = 5
MIN_BARS = 60             # analyze() 要求的最低 K 线数
KLINE_CAP = 250           # 每只股票保留的最大 K 线根数

# ── 反拦截核心：UA 池 + 温柔 Session + 自适应熔断 ──
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]
REFERERS = {
    "qt.gtimg.cn": "https://gu.qq.com/",
    "web.ifzq.gtimg.cn": "https://gu.qq.com/",
    "money.finance.sina.com.cn": "https://finance.sina.com.cn/",
    "vip.stock.finance.sina.com.cn": "https://finance.sina.com.cn/",
}

# 全局自适应熔断：连续失败过多 → 整批冷却，避免硬扛触发长期封禁
_fail_lock = threading.Lock()
_consec_fail = 0
_FAIL_THRESHOLD = 25      # 连续失败达到该值 → 冷却
_COOLDOWN = 90            # 冷却时长（秒）
_NAME = {}                # code -> name 映射（增量/全量复用）


def _gentle_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0,
                  status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


_SESSION = _gentle_session()


def gentle_get(url: str, timeout: int = HTTP_TIMEOUT, enc: str = "utf-8"):
    """带 UA 轮换 + Referer + 指数退避 + 自适应熔断的 GET，返回文本或 None。"""
    global _consec_fail
    host = url.split("/")[2] if "//" in url else ""
    ref = REFERERS.get(host, "https://www.baidu.com/")
    for attempt in range(1, KL_RETRIES + 1):
        # 熔断检查
        with _fail_lock:
            if _consec_fail >= _FAIL_THRESHOLD:
                print(f"  ⏸ 连续失败 {_consec_fail} 次，整批冷却 {_COOLDOWN}s 后继续…")
                time.sleep(_COOLDOWN)
                _consec_fail = 0
        headers = {
            "User-Agent": random.choice(UA_POOL),
            "Referer": ref,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            r = _SESSION.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                with _fail_lock:
                    _consec_fail = 0
                try:
                    return r.text
                except Exception:
                    return r.text
            if r.status_code in (429, 403):
                wait = min(120, 8 * (2 ** attempt)) + random.uniform(0, 4)
                with _fail_lock:
                    _consec_fail += 1
                print(f"  ⏸ 限流 {r.status_code}，退避 {wait:.0f}s")
                time.sleep(wait)
                continue
            # 其他状态码：轻微退避
            with _fail_lock:
                _consec_fail += 1
            time.sleep(0.5 * attempt)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait = min(60, 2 * (2 ** attempt)) + random.uniform(0, 2)
            with _fail_lock:
                _consec_fail += 1
            if attempt == 1:
                print(f"  ⚠ 连接异常（{type(e).__name__}），退避 {wait:.0f}s 重试")
            time.sleep(wait)
        except Exception:
            with _fail_lock:
                _consec_fail += 1
            time.sleep(1.0)
    return None


def _curl(url: str) -> str:
    p = subprocess.run(["curl", "-s", "--max-time", str(HTTP_TIMEOUT), *HEADERS, url],
                       capture_output=True)
    try:
        return p.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return p.stdout.decode("gbk", "ignore")


# ─────────────────── 1. 代码宇宙 ───────────────────
def get_all_a_codes(force=False):
    cache = os.path.join(OUT, "all_a_codes.json")
    if not force and os.path.exists(cache):
        meta = os.path.getmtime(cache)
        if (time.time() - meta) < 7 * 86400:
            d = json.load(open(cache, encoding="utf-8"))
            if d:
                print(f"  ✓ 复用代码缓存 ({len(d)} 只)")
                return d
    import akshare as ak
    print("  🔄 拉取全量 A股代码 (akshare/新浪)...")
    out = []
    try:
        sh = ak.stock_info_sh_name_code()
        for _, r in sh.iterrows():
            c6 = str(r["证券代码"]).zfill(6)
            m = "sh" if c6.startswith(("60", "68", "90")) else None
            if m:
                out.append({"code": f"{m}{c6}", "code6": c6,
                            "name": str(r["证券简称"]).strip(), "market": m})
    except Exception as e:
        print(f"  ⚠️ 沪市列表失败: {e}")
    try:
        sz = ak.stock_info_sz_name_code()
        for _, r in sz.iterrows():
            c6 = str(r["A股代码"]).zfill(6)
            m = "sz" if c6.startswith(("00", "30", "20")) else None
            if m:
                out.append({"code": f"{m}{c6}", "code6": c6,
                            "name": str(r["A股简称"]).strip(), "market": m})
    except Exception as e:
        print(f"  ⚠️ 深市列表失败: {e}")
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ {len(out)} 只 A股")
    return out


# ─────────────────── 2. 成交额/换手率快照 ───────────────────
def fetch_snapshot(codes, force=False):
    if not force and os.path.exists(SNAP_FILE):
        d = json.load(open(SNAP_FILE, encoding="utf-8"))
        if d:
            print(f"  ↺ 复用快照缓存 ({len(d)} 只)")
            return d
    # 云端 / 首次冷启动：SNAP_FILE 不存在 → 尝试从 kline_raw.json 构造成交额/换手率
    # 避免在 GitHub Actions runner 上拉 4600 只 qt.gtimg.cn 快照超时
    if os.path.exists(KLINE_RAW):
        print(f"  🔄 从 kline_raw.json 提取成交额快照({len(codes)} 只, 免网络)...")
        raw = json.load(open(KLINE_RAW, encoding="utf-8"))
        out = {}
        by_code = {r["code"]: r for r in raw}
        for c in codes:
            r = by_code.get(c["code"]) or by_code.get(c.get("code6", ""))
            if r and r.get("kline"):
                last_bar = r["kline"][-1]
                vol = last_bar.get("volume", 0) * 100  # 手 → 股
                close = last_bar.get("last", 0)
                out[c["code"]] = {"amount": close * vol, "turnover": 99}
        if out:
            print(f"  ✓ 从 kline_raw 提取 {len(out)} 只 (无网络)")
            json.dump(out, open(SNAP_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return out
    print(f"  📊 拉取成交额/换手率快照 ({len(codes)} 只)...")
    t0 = time.time()
    out = {}
    by_code = {c["code"]: c for c in codes}
    batches = [codes[i:i + 60] for i in range(0, len(codes), 60)]

    def _one(batch):
        q = ",".join(b["code"] for b in batch)
        try:
            txt = _curl(f"https://qt.gtimg.cn/q={q}")
        except Exception:
            return {}
        import re
        res = {}
        for line in txt.strip().split("\n"):
            if not line.strip():
                continue
            m = re.match(r'v_(\w+)="(.*)";', line)
            if not m:
                continue
            parts = m.group(2).split("~")
            if len(parts) <= 38:
                continue
            try:
                amount = float(parts[37]); turnover = float(parts[38])
            except (ValueError, IndexError):
                continue
            res[m.group(1)] = {"amount": amount, "turnover": turnover}
        return res

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(_one, batches):
            out.update(r)
    json.dump(out, open(SNAP_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  ✓ 快照完成 {len(out)} 只 ({time.time()-t0:.1f}s)")
    return out


# ─────────────────── 3. 板块→成份股映射（push2 直连，带重试）───────────────────
def _push2_boards():
    """板块列表：优先 akshare THS（本机稳定），返回 [(code6, name)]。"""
    import akshare as ak
    boards = [(b["code"], b["name"]) for _, b in ak.stock_board_industry_name_ths().iterrows()]
    return boards


def _push2_cons(code6, attempt=0):
    u = (f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1000"
         f"&fs=b:{code6}&fields=f12,f14")
    try:
        d = json.loads(_curl(u))
        diff = (d.get("data") or {}).get("diff")
        if not diff:
            return []
        return [(x["f12"], x["f14"]) for x in (diff.values() if isinstance(diff, dict) else diff)]
    except Exception:
        return []


def fetch_sectors(max_attempts=8, gap=15):
    """新浪行业板块->成份股映射（新浪源，稳定可用）。"""
    print("  [板块] 拉取行业板块->成份股映射 (新浪源)...")
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    def _get(url, enc="utf-8"):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                                    "Referer": "https://finance.sina.com.cn/"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode(enc, errors="ignore")
    list_url = "https://money.finance.sina.com.cn/q/view/newSinaHy.php"
    for att in range(1, max_attempts + 1):
        try:
            html = _get(list_url, "gbk")
            pairs = re.findall(r'"(new_[a-z0-9]+)":"([^"]*)"', html)
            boards = {k: (v.split(",")[1] if "," in v else k) for k, v in pairs}
            if not boards:
                print(f"  [板块] 列表为空({att}/{max_attempts})，重试..."); time.sleep(gap); continue
        except Exception as e:
            print(f"  [板块] 列表失败({att}/{max_attempts}): {e}"); time.sleep(gap); continue
        sector_map = {}
        ok_boards = 0
        def _cons(node):
            url = ("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                   "Market_Center.getHQNodeData?page=1&num=500&sort=symbol&asc=1&node=" + node)
            try:
                arr = json.loads(_get(url))
                codes = [x["symbol"] for x in arr if x.get("symbol")]
                return node, codes
            except Exception:
                return node, []
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            for node, codes in ex.map(_cons, list(boards.keys())):
                if codes:
                    sector_map[boards[node]] = {"name": boards[node],
                                                "cons": [(c[2:], c) for c in codes]}
                    ok_boards += 1
        if ok_boards == 0:
            print(f"  [板块] 成份全部失败({att}/{max_attempts})，重试..."); time.sleep(gap); continue
        code_sector = {}
        for bk, info in sector_map.items():
            for c6, _ in info["cons"]:
                mp = "sh" if c6.startswith(("60", "68", "90")) else ("sz" if c6.startswith(("00", "30", "20")) else None)
                if mp:
                    code_sector[f"{mp}{c6}"] = info["name"]
        print(f"  [板块] 映射完成：{ok_boards}/{len(boards)} 板块 / {len(code_sector)} 只归属")
        return {"sector_map": sector_map, "code_sector": code_sector}
    print("  [板块] 新浪板块获取失败，板块门控暂不可用。可稍后 `python gate_scan.py --sectors-only` 重试。")
    return {}



# ─────────────────── 4. K线（温柔并发 + 多源兜底 + 可续传 / 增量日更）───────────────────
def _parse_gtimg(node):
    arr = node.get("qfqday") or node.get("day")
    if not arr:
        return None
    return [{"date": p[0], "open": float(p[1]), "last": float(p[2]),
             "high": float(p[3]), "low": float(p[4]), "volume": float(p[5])}
            for p in arr]


def _parse_sina(arr):
    out = []
    for x in arr:
        try:
            out.append({"date": x["day"], "open": float(x["open"]), "last": float(x["close"]),
                        "high": float(x["high"]), "low": float(x["low"]), "volume": float(x["volume"])})
        except (KeyError, ValueError, TypeError):
            continue
    return out or None


def fetch_kline_one(code, code6, count=250):
    """多源兜底抓取单只 K线，全部走腾讯 gtimg 体系（官方代理为主，新浪仅最后兜底）。

    2026-07 起 web.ifzq.gtimg.cn 被腾讯 WAF 拦成 501，故主源切换为官方代理
    proxy.finance.qq.com（同 qfqday 结构、带 CORS，与 fetch_pool.py 对齐，
    这才是“对接腾讯 gtimg”的正确入口）。新浪偶有脏 bar，仅作绝对兜底。
    """
    sources = [
        (f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param={code},day,,,{count},qfq", "tencent"),
        (f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
         f"CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={count}", "sina"),
    ]
    for url, src in sources:
        for _ in range(KL_RETRIES):
            try:
                txt = _curl(url)
            except Exception:
                time.sleep(1); continue
            if not txt or not txt.strip():
                time.sleep(1); continue
            try:
                if src == "tencent":
                    j = json.loads(txt)
                    node = (j.get("data") or {}).get(code) or (j.get("data") or {}).get(code6)
                    bars = _parse_gtimg(node) if node else None
                else:
                    bars = _parse_sina(json.loads(txt))
                if bars and len(bars) >= 2:
                    return bars
            except (json.JSONDecodeError, ValueError):
                break  # 非 JSON（WAF 501 页）→ 此源确定性不可用，跳到下一源
            except Exception:
                pass
            time.sleep(1)
    return None


def _merge_append(old_bars, new_bars):
    """按日期去重合并，保留最近 KLINE_CAP 根。"""
    mp = {b["date"]: b for b in old_bars}
    for b in new_bars:
        mp[b["date"]] = b
    merged = sorted(mp.values(), key=lambda x: x["date"])
    return merged[-KLINE_CAP:]


def _save_klines(results, t0, done, total, label=""):
    json.dump(results, open(KLINE_ALL + ".tmp", "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(KLINE_ALL + ".tmp", KLINE_ALL)
    el = time.time() - t0
    rate = done / el if el > 0 else 0
    print(f"  [{label}{done}/{total}] 累计 {len(results)} 只 | {rate:.1f}只/s")


def _run_pool(tasks):
    """tasks: list of (code, code6, count)。温柔并发（抖动+低并发），定期落盘。"""
    results = {}
    t0 = time.time(); done = 0; ok = 0
    sem = threading.Semaphore(CONCURRENCY)

    def worker(code, code6, count):
        with sem:
            time.sleep(random.uniform(*JITTER))
            return fetch_kline_one(code, code6, count)

    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(worker, c["code"], c.get("code6", c["code"][2:]), n): c["code"]
                for c, n in tasks}
        for fut in cf.as_completed(futs):
            r = fut.result(); done += 1
            if r:
                code = futs[fut]
                # 找到对应 task 的 name/market
                results[code] = {"code": code, "name": _NAME.get(code, code),
                                 "market": code[:2], "kline": r}
                ok += 1
            if done % 150 == 0 or done == len(tasks):
                _save_klines(results, t0, done, len(tasks))
    return results, ok


def fetch_klines_full(codes, resume=True):
    """全量重建（带续传）：只抓缺失或 K 线不足的股票，250 根。"""
    print(f"  📈 全量重建 K线 (并发{CONCURRENCY}, 抖动{JITTER}, 多源兜底, 可续传)...")
    existing = {}
    if resume and os.path.exists(KLINE_ALL):
        try:
            existing = json.load(open(KLINE_ALL, encoding="utf-8"))
            print(f"  ↺ 续传：已存在 {len(existing)} 只")
        except Exception:
            existing = {}
    _NAME.update({c["code"]: c["name"] for c in codes})
    tasks = [(c, 250) for c in codes
             if c["code"] not in existing or len(existing[c["code"]].get("kline", [])) < MIN_BARS]
    print(f"  📦 待抓 {len(tasks)} 只（共 {len(codes)}）")
    new_res, ok = _run_pool(tasks)
    results = dict(existing); results.update(new_res)
    _save_klines(results, time.time(), len(tasks), len(tasks), "全量")
    print(f"  ✓ K线完成：{len(results)} 只（新抓 {ok}）")
    return results


def fetch_klines_daily(existing):
    """增量日更：对缓存内每只股票只追加最新 K 线（count=8），不足则补满 250。"""
    print(f"  📈 增量日更 K线 (并发{CONCURRENCY}, 抖动{JITTER}, 多源兜底)...")
    _NAME.update({c: v.get("name", c) for c, v in existing.items()})
    tasks = []
    for code, stk in existing.items():
        bars = stk.get("kline", [])
        if len(bars) < MIN_BARS:
            tasks.append(({"code": code, "name": stk.get("name", code), "market": code[:2]}, 250))
        else:
            tasks.append(({"code": code, "name": stk.get("name", code), "market": code[:2]}, 8))
    print(f"  📦 待更新 {len(tasks)} 只（缓存 {len(existing)}）")
    new_res, ok = _run_pool(tasks)
    results = dict(existing)
    for code, stk in new_res.items():
        ob = existing.get(code, {}).get("kline", [])
        nb = stk["kline"]
        results[code] = {"code": code, "name": stk["name"], "market": code[:2],
                         "kline": _merge_append(ob, nb) if len(nb) <= 8 else nb}
    _save_klines(results, time.time(), len(tasks), len(tasks), "日更")
    print(f"  ✓ 日更完成：{len(results)} 只（更新 {ok}）")
    return results


# ─────────────────── 5. 金钻扫描（复用 analyze）───────────────────
def _primary(signals):
    best, br = None, -1
    for s in signals:
        t = s.get("type", "")
        r = RANK.get(t, RANK.get("红区黄柱连续") if t.startswith("红区黄柱连续") else 0)
        if r > br:
            br, best = r, t
    return best or ""


def _round(arr, nd=3):
    return [None if x is None else round(float(x), nd) for x in arr]


def scan_universe(klines: dict, codes_scope: set):
    hits = []
    for code, stk in klines.items():
        if code not in codes_scope:
            continue
        rows = [{"date": r["date"], "open": r["open"], "close": r["last"],
                 "high": r["high"], "low": r["low"], "volume": r["volume"]}
                for r in stk.get("kline", [])]
        if len(rows) < 60:
            continue
        try:
            res = analyze(rows)
        except Exception:
            continue
        if not res.get("signals"):
            continue
        hits.append({
            "code": code, "name": stk["name"], "market": stk["market"],
            "primary": _primary(res["signals"]),
            "signals": res["signals"], "kline": rows,
            "golden_bull": _round(res["golden_bull"]),
            "golden_trend": _round(res["golden_trend"]),
            "gt2": _round(res["gt2"]),
            "red_zone": res["red_zone"], "yellow_bar": res["yellow_bar"],
            "count": res["count"],
            "last_date": rows[-1]["date"] if rows else "",
        })
    hits.sort(key=lambda e: (-RANK.get(e["primary"], 1), e["code"]))
    return hits, {"total": len(hits),
                  "buy": sum(1 for e in hits if e["primary"] == "买入"),
                  "up": sum(1 for e in hits if e["primary"] == "金钻起涨"),
                  "hz": sum(1 for e in hits if e["primary"].startswith("红区黄柱连续"))}


def _analysis(total, up, buy, hz, date, scope_label, scope_size, note=""):
    if total == 0:
        return (f"{date} 【{scope_label}】金钻三子形态暂无命中"
                + (f"：{note}" if note else "，市场处震荡筑底阶段，建议观望。")
                + "提示：金钻为技术共振信号，须结合大盘环境与个股基本面，勿单一依赖。")
    p = [f"{date} 【{scope_label}】（扫描范围 {scope_size} 只）金钻策略共命中 {total} 只个股。"]
    if up:
        p.append(f"其中「金钻起涨」{up} 只，为强势启动信号，资金面（DY2）与量价配合达标，可优先跟踪；")
    if buy:
        p.append(f"「买入」{buy} 只，属回调结束、金钻趋势上穿高位后的回补买点；")
    if hz:
        p.append(f"「红区黄柱连续」{hz} 只，处红区（金钻趋势>金牛2）且连续筑底企稳，偏蓄势待发。")
    p.append("提示：金钻为技术共振信号，须结合大盘环境与个股基本面，勿单一依赖。")
    return "".join(p)


# ─────────────────── 门控范围求解 ───────────────────
def load_top800_codes():
    """主门控（当前门控）范围 = 成交额 TOP800，取自 kline_raw.json 键（与 fetch_pool / 主站口径一致）。"""
    if not os.path.exists(KLINE_RAW):
        return set()
    raw = json.load(open(KLINE_RAW, encoding="utf-8"))
    return set(item["code"] for item in raw)


def resolve_scopes(codes, snapshot, sector, klines):
    pool_codes = load_top800_codes()   # 主门控 = TOP800（与主站/金钻口径一致）
    all_codes = set(klines.keys())
    scopes = {}
    scopes["all_a"] = all_codes        # 全A市场 = 所有已缓存 K 线的股票
    scopes["pool"] = all_codes & pool_codes
    se = sector.get("code_sector", {}) if sector else {}
    by_sec = {}
    for code in all_codes:
        sec = se.get(code)
        if not sec:
            continue
        amt = (snapshot.get(code) or {}).get("amount", 0) or 0
        by_sec.setdefault(sec, []).append((code, amt))
    sec_union = set()
    sec_stats = []
    for sec, lst in by_sec.items():
        lst.sort(key=lambda x: x[1], reverse=True)
        top = lst[:100]
        kept = [c for c, _ in top if (snapshot.get(c) or {}).get("turnover", 99) >= 4.0]
        sec_union.update(kept)
        sec_stats.append({"sector": sec, "candidates": len(top), "kept": len(kept)})
    sec_stats.sort(key=lambda x: -x["kept"])
    scopes["sector_top100_to4"] = sec_union
    return scopes, sec_stats


# ─────────────────── 第二档：照搬原始兜宝金钻（不重算） ───────────────────
def load_original_pool_gate():
    """第二档『当前门控（成交额TOP800）』= 直接照搬原始兜宝金钻机制产出（golden_diamond.json）。

    原始机制：fetch_pool.py 拉取成交额 TOP800 候选池 + golden_diamond_scan.py 运行金钻三子形态
    （复用 golden_diamond_viewer/server.py 的 analyze()，腾讯 gtimg 前复权 K 线）。这是经实盘 /
    通达信验证的真值源。沙盒【只读取映射，绝不动其算法、数据源、更新机制】。

    这样『当前门控』与线上持续更新的兜宝金钻逐只一致、不会因沙盒 K线源/候选池漂移而偏离。
    第一档（全A）、第三档（板块前100·换手≥4%）才是沙盒扩展，独立计算。
    """
    if not os.path.exists(GOLDEN_DIAMOND):
        return None
    gd = json.load(open(GOLDEN_DIAMOND, encoding="utf-8"))
    dd = gd.get("data_date", "")
    stocks = []
    for s in gd.get("stocks", []):
        sigs = s.get("signals", []) or []
        sd = sigs[0].get("date") if sigs else None
        stk = {
            "code": s["code"],
            "name": s.get("name", s["code"]),
            "primary": (s.get("primary") or "").replace("天", "日"),
            "signals": sigs,
            "kline": s.get("kline", []),
            "signal_date": sd,
        }
        if sd:
            try:
                d0 = datetime.datetime.strptime(sd, "%Y-%m-%d").date()
                d1 = datetime.datetime.strptime(dd or sd, "%Y-%m-%d").date()
                stk["days_ago"] = (d1 - d0).days
            except Exception:
                stk["days_ago"] = s.get("days_ago")
        else:
            stk["days_ago"] = s.get("days_ago")
        stocks.append(stk)
    stocks.sort(key=lambda e: (-RANK.get(e["primary"], 1), e["code"]))
    ov_in = gd.get("overview", {})
    up = sum(1 for e in stocks if e["primary"] == "金钻起涨")
    buy = sum(1 for e in stocks if e["primary"] == "买入")
    hz = sum(1 for e in stocks if e["primary"].startswith("红区黄柱连续"))
    total = ov_in.get("total", len(stocks))
    ov = {
        "total": total, "up": up, "buy": buy, "hz": hz, "data_date": dd,
        "analysis": ov_in.get("analysis") or _analysis(total, up, buy, hz, dd,
                                                       GATE_LABELS["pool"], total),
    }
    return {"label": GATE_LABELS["pool"], "scope_size": total,
            "overview": ov, "stocks": stocks}


# ─────────────────── 缠论按门控（端口主站 signals.check_chan_buy_signal）───────────────────
def load_chan_klines():
    """缠论逐票计算的 K 线源：合并 kline_all（全A缓存）与 kline_raw（TOP800），
    覆盖主门控 + 板块两档范围，避免重复拉取网络 K 线。"""
    k = {}
    if os.path.exists(KLINE_ALL):
        k.update(json.load(open(KLINE_ALL, encoding="utf-8")))
    if os.path.exists(KLINE_RAW):
        for item in json.load(open(KLINE_RAW, encoding="utf-8")):
            k[item["code"]] = {"code": item["code"], "name": item.get("name", item["code"]),
                               "market": item["code"][:2], "kline": item["kline"]}
    return k


def scan_chan(klines, codes_scope):
    """缠论买点检测（原始买点，不做 EMA 门控），在指定门控范围内逐票计算。
    返回 (hits, total)。hits: [{code,name,buy_date,days_ago,price}]。"""
    hits = []
    for code, stk in klines.items():
        if code not in codes_scope:
            continue
        rows = stk.get("kline", [])
        if len(rows) < 60:
            continue
        try:
            df = pd.DataFrame(rows)
            if "close" not in df.columns and "last" in df.columns:
                df["close"] = df["last"]
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            ok, det = check_chan_buy_signal(df)
        except Exception:
            continue
        if not ok:
            continue
        hits.append({
            "code": code,
            "name": stk.get("name", code),
            "buy_date": det.get("buy_date"),
            "days_ago": det.get("days_ago"),
            "price": det.get("buy_price"),
        })
    hits.sort(key=lambda e: (e["days_ago"] if e["days_ago"] is not None else 999, e["code"]))
    return hits, len(hits)


# ─────────────────── 扫描 + 写档 ───────────────────
def compute_gate(gate, klines, snapshot, sector, scopes, sec_stats,
                 chan_klines=None, top800_codes=None):
    if gate == "pool":
        # 第二档『当前门控』= 照搬原始兜宝金钻真值，不重算、不漂移
        original = load_original_pool_gate()
        if original is not None:
            # 缠论按主门控 TOP800 范围计算（端口主站算法，原始买点不做 EMA 门控）
            if chan_klines and top800_codes:
                ch_hits, ch_total = scan_chan(chan_klines, top800_codes)
                original["chan"] = {"total": ch_total,
                                    "codes": [h["code"] for h in ch_hits],
                                    "stocks": ch_hits}
            return original, sec_stats
        print("  ⚠ 原始 golden_diamond.json 缺失，pool 档退回重算")
    scope = scopes.get(gate, set())
    hits, ov = scan_universe(klines, scope)
    date = hits[0]["last_date"] if hits else ""
    note = ""
    if gate == "sector_top100_to4" and not sector:
        note = "板块数据源暂不可用，门控未生效"
    # 缠论按门控：sector/all_a 档用各自范围；pool 退回重算时用 TOP800 范围
    chan_payload = None
    if chan_klines is not None:
        ch_scope = scope if gate in ("sector_top100_to4", "all_a") else (top800_codes or scope)
        ch_hits, ch_total = scan_chan(chan_klines, ch_scope)
        chan_payload = {"total": ch_total, "codes": [h["code"] for h in ch_hits],
                        "stocks": ch_hits}
        ov["chan_total"] = ch_total
    ov["analysis"] = _analysis(ov["total"], ov["up"], ov["buy"], ov["hz"], date,
                               GATE_LABELS[gate], len(scope), note)
    ov["data_date"] = date
    res = {"label": GATE_LABELS[gate], "scope_size": len(scope),
           "overview": ov, "stocks": hits}
    if chan_payload is not None:
        res["chan"] = chan_payload
    return res, sec_stats


def write_gate_data(gates_dict, sec_stats, data_date):
    gate_data = {
        "data_date": data_date,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "default_gate": DEFAULT_GATE,
        "sector_stats": sec_stats,
        "gates": gates_dict,
    }
    json.dump(gate_data, open(GATE_DATA, "w", encoding="utf-8"), ensure_ascii=False)
    for g, v in gates_dict.items():
        json.dump({"data_date": v["overview"]["data_date"], "updated_at": gate_data["updated_at"],
                   "overview": v["overview"], "stocks": v["stocks"]},
                  open(os.path.join(OUT, f"gate_{g}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return gate_data


# ─────────────────── 主流程 ───────────────────
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", default="all_a,pool,sector_top100_to4")
    ap.add_argument("--no-kline", action="store_true")
    ap.add_argument("--daily", action="store_true", help="增量日更：只追加最新 K线并重算门控（推荐每日自动化）")
    ap.add_argument("--full", action="store_true", help="全量重建 K线（带续传，耗时较长，偶尔跑一次）")
    ap.add_argument("--force", action="store_true", help="强制全量重抓 K线（忽略续传，覆盖已有数据）")
    ap.add_argument("--sectors-only", action="store_true", help="仅重抓板块并重算板块门控")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    gates = [g.strip() for g in args.gates.split(",")]

    print("═══ 兜宝金钻 · 门控扫描（全A市场 + 主门控 TOP800 + 板块前100·换手≥4%）═══")
    t0 = time.time()

    if args.sectors_only:
        # 复用已有 K线 + 快照，仅重抓板块并重算板块门控
        klines = json.load(open(KLINE_ALL, encoding="utf-8")) if os.path.exists(KLINE_ALL) else {}
        snapshot = json.load(open(SNAP_FILE, encoding="utf-8")) if os.path.exists(SNAP_FILE) else {}
        sector = fetch_sectors()
        if sector:
            json.dump(sector, open(SECTOR_FILE, "w", encoding="utf-8"), ensure_ascii=False)
        codes = get_all_a_codes()
        scopes, sec_stats = resolve_scopes(codes, snapshot, sector, klines)
        chan_klines = load_chan_klines()
        top800_codes = load_top800_codes()
        gd = json.load(open(GATE_DATA, encoding="utf-8")) if os.path.exists(GATE_DATA) else {"gates": {}}
        g, sec_stats = compute_gate("sector_top100_to4", klines, snapshot, sector, scopes, sec_stats,
                                    chan_klines, top800_codes)
        gd["gates"]["sector_top100_to4"] = g
        gd["sector_stats"] = sec_stats
        gd["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        json.dump(gd, open(GATE_DATA, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  ✓ 板块门控重算：范围 {g['scope_size']} → 命中 {g['overview']['total']} · 缠论 {g.get('chan', {}).get('total', 0)}")
        print(f"\n✅ 完成 ({time.time()-t0:.0f}s)")
        return

    codes = get_all_a_codes()
    snapshot = fetch_snapshot(codes)
    sector = fetch_sectors()
    if sector:
        json.dump(sector, open(SECTOR_FILE, "w", encoding="utf-8"), ensure_ascii=False)

    if args.daily:
        if os.path.exists(KLINE_ALL):
            existing = json.load(open(KLINE_ALL, encoding="utf-8"))
            print(f"  ↺ 载入缓存 {len(existing)} 只，进入增量日更")
            klines = fetch_klines_daily(existing)
        else:
            print("  ⚠ 无 kline_all.json 缓存，回退全量重建")
            klines = fetch_klines_full(codes, resume=True)
    elif args.no_kline and os.path.exists(KLINE_ALL):
        klines = json.load(open(KLINE_ALL, encoding="utf-8"))
        print(f"  ↺ 复用 kline_all.json ({len(klines)} 只)")
    else:
        klines = fetch_klines_full(codes, resume=not args.force)

    scopes, sec_stats = resolve_scopes(codes, snapshot, sector, klines)
    # 缠论 K 线源（合并 kline_all + kline_raw）与 TOP800 主门控范围
    chan_klines = load_chan_klines()
    top800_codes = load_top800_codes()

    if args.dry_run:
        for g in gates:
            print(f"  [dry] {g}: 范围 {len(scopes.get(g, set()))} 只")
        return

    gates_dict = {}
    for g in gates:
        gates_dict[g], sec_stats = compute_gate(g, klines, snapshot, sector, scopes, sec_stats,
                                                chan_klines, top800_codes)
        ch = gates_dict[g].get("chan", {})
        print(f"  ✓ {g}: 范围 {gates_dict[g]['scope_size']} → 命中 {gates_dict[g]['overview']['total']} "
              f"(起涨{gates_dict[g]['overview']['up']}/买入{gates_dict[g]['overview']['buy']}/红区{gates_dict[g]['overview']['hz']})"
              f" · 缠论 {ch.get('total', 0)}")
    data_date = max((gt["overview"]["data_date"] for gt in gates_dict.values()), default="")
    write_gate_data(gates_dict, sec_stats, data_date)
    print(f"\n✅ 门控扫描完成 ({time.time()-t0:.0f}s) → {GATE_DATA}")


if __name__ == "__main__":
    main()
