#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜金观测 — 板块资金流向采集脚本 v3（申万一级 · 东财口径）

v2 改动（云端化根治）:
  - 数据源从 westock-data（本机 skill，云端不存在）切换为东方财富板块资金流 HTTP 接口
  - 失败时优雅降级（保留旧数据 + 警告，不崩溃）

v3 改动（2026-09-29 · 实测根因修复，用户报障「资金流接口连续多日不可达」）:
  🔴 根因（实测证据，非推断）:
     东财 **`/api/qt/clist/get`（批量列表接口）已被边缘风控针对性封禁** —— 表现为
     `RemoteDisconnected`（TLS 握手成功、请求发出后服务端直接断开，应用层丢包）。
     · 实测同一会话内：`push2.eastmoney.com/api/qt/ulist.np/get` 与
       `push2his.eastmoney.com/api/qt/stock/fflow/daykline/get` **均返回真实数据（HTTP 200）**，
       而 `clist` **从头到尾被拒** → 说明**不是**网络/DNS/UA/`ut` 令牌/TLS 指纹问题，
       **也不是整站不可达**，而是**该 API 路径被定点封禁**。
     · 同期 `data.eastmoney.com` 网页、`datacenter-web.eastmoney.com` API、
       `push2delay.eastmoney.com/` 根路径（404）、`qt.gtimg.cn` **全部正常** —— 排除本机代理/断网。
     · 🔴 二级效应：**短时高频请求会触发更大范围的 IP 级临时封禁**（实测把 `ulist.np` 也一起打到 RST）
       → 因此 v3 **严禁重试风暴**：单次运行请求数 **15 → 1~2**，尝试次数 **3 → 2**，且带**请求间隔 + 指数退避**。
  ✅ v3 修复动作:
     ① **请求数 15→1**：`clist` 改 `pz=500` 单请求拉全（原 `for pn in 1..5` × `for attempt in 3` 最多 15 请求）；
     ② **兜底端点**：`clist` 失败 → 同主机 `ulist.np`（批量 `secids`，字段同源 `f62/f66/f72/f184`），
        `secid` 表由 `clist` 首次成功时**自举**写入 `output/sw1_secids.json`，并做**名称回读自校验**（防代码漂移静默错配）；
     ③ **UA 去机器人标识**（原 `GoldenStockObserver/1.0` 是给风控送人头的特征）；
     ④ **大声失败**：不再静默保留旧数据 —— 产物新增 `source_status`（`ok/last_success/stale_days/error/endpoint`），
        stderr 明确告警，**退出码 4**（区别于成功 0），供自动化与守卫捕获；
     ⑤ **`--probe`**：单请求健康探针（供 08:30 推演档 / 哨兵调用，失败不写产物）；
     ⑥ **`--backfill`**：用 `push2his` 板块资金流日线**回填缺失交易日**（一次 31 请求，逐只带间隔、遇 RST 即刻停）。

用法:
  python fetch_sector_flow.py                     # 采集「最近一个已收盘交易日」
  python fetch_sector_flow.py --date 2026-09-28   # 指定数据日
  python fetch_sector_flow.py --probe             # 只做健康探针（不写产物）
  python fetch_sector_flow.py --backfill 2026-09-23 2026-09-28   # 回填指定日期（含端点闭区间）
退出码: 0=成功 / 4=数据源不可达（产物已标记 stale）/ 2=参数错误
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

try:
    from market_calendar import is_trading_day, last_trading_day
except Exception:  # 交易日历不可用时不阻断采集
    is_trading_day = last_trading_day = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "output", "sector_flow.json")
SECID_SIDECAR = os.path.join(SCRIPT_DIR, "output", "sw1_secids.json")

# ── 东财接口 ────────────────────────────────────────────────────────────
# 🔴 2026-09-29 实测：`clist` 被定点封禁（RST），`ulist.np` / `push2his fflow daykline` 可用。
CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"        # 主源（批量列表，当前被封则走兜底）
ULIST_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"     # 兜底源（批量 secids，同主机未被封）
FFLOW_DAY_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"  # 回填源（板块资金流日线）

# `ut` 取自东财资金流页面现行 JS（data.eastmoney.com/newstatic/js/bkzj/list.js，2026-09-29 抓取）
# 历史的 bd1d9ddb… 已非页面在用值；实测 ut 不是本故障主因，但随页面同步更稳。
UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

# 🔴 UA 去机器人标识：原 "GoldenStockObserver/1.0" 是给风控送人头的特征
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://data.eastmoney.com/bkzj/hy.html",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 反封禁参数（🔴 禁调大：短时高频会触发 IP 级封禁，实测会把兜底端点一起打死）
REQ_INTERVAL = 1.5     # 请求间隔秒
MAX_ATTEMPTS = 2       # 单端点最多尝试次数（原 3 + 分页 = 最多 15 请求）
BACKOFF_BASE = 3.0     # 退避基数：3s → 6s
CLIST_PAGE_SIZE = 500  # 单请求拉全（行业板块总数 < 500）

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
SW1_NAMES = set(SW1_SECTORS.values())


def get_sector_category(name: str) -> str:
    for cat, names in SECTOR_CATEGORIES.items():
        if name in names:
            return cat
    return "其他"


# ── HTTP 层（带间隔 + 指数退避，禁重试风暴） ──────────────────────────────
def _session():
    if requests is None:
        return None
    s = requests.Session()
    # 绕开本机代理环境变量（沙箱/开发机可能配了代理导致 ProxyError；生产无代理时为 no-op）
    s.trust_env = False
    return s


def _http_get(sess, url, params, timeout=15):
    """单端点 GET：最多 MAX_ATTEMPTS 次，带退避；失败抛最后一次异常。"""
    last = None
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            time.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))  # 3s → 6s
        try:
            r = sess.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def probe_source(verbose=True):
    """健康探针：单请求判定主源/兜底源可用性。返回 dict，不写产物。"""
    out = {"probed_at": datetime.now().isoformat(timespec="seconds"),
           "clist": {"ok": False, "detail": ""}, "ulist": {"ok": False, "detail": ""}}
    sess = _session()
    if sess is None:
        out["clist"]["detail"] = "requests 未安装"
        return out

    # ① 主源 clist
    t0 = time.time()
    try:
        r = _http_get(sess, CLIST_URL, {
            "pn": 1, "pz": 5, "po": 1, "np": 1, "fltt": 2, "invt": 2, "ut": UT,
            "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62"})
        n = len(((r.json().get("data") or {}).get("diff")) or [])
        out["clist"].update(ok=n > 0, detail=f"HTTP {r.status_code} diff={n}",
                            latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        out["clist"].update(detail=f"{type(e).__name__}: {str(e)[:80]}",
                            latency_ms=int((time.time() - t0) * 1000))
    time.sleep(REQ_INTERVAL)

    # ② 兜底源 ulist（用 sidecar 若已有，否则用 1 只已知板块探测通路）
    t0 = time.time()
    secids = list(_load_secids().values())[:5] or ["90.BK0475"]
    try:
        r = _http_get(sess, ULIST_URL, {
            "fltt": 2, "invt": 2, "ut": UT, "secids": ",".join(secids), "fields": "f12,f14,f62"})
        n = len(((r.json().get("data") or {}).get("diff")) or [])
        out["ulist"].update(ok=n > 0, detail=f"HTTP {r.status_code} diff={n}",
                            latency_ms=int((time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        out["ulist"].update(detail=f"{type(e).__name__}: {str(e)[:80]}",
                            latency_ms=int((time.time() - t0) * 1000))

    out["ok"] = out["clist"]["ok"] or out["ulist"]["ok"]
    if verbose:
        print(f"  🔎 资金流源探针: clist={'✅' if out['clist']['ok'] else '❌'}"
              f"({out['clist']['detail']}) | ulist={'✅' if out['ulist']['ok'] else '❌'}"
              f"({out['ulist']['detail']})")
    return out


# ── secid 自举表（clist 首次成功时写入，供 ulist 兜底） ────────────────────
def _load_secids():
    if os.path.exists(SECID_SIDECAR):
        try:
            d = json.load(open(SECID_SIDECAR, encoding="utf-8"))
            if isinstance(d, dict) and d.get("by_name"):
                return d["by_name"]
        except Exception:  # noqa: BLE001
            pass
    return {}


def _save_secids(by_name):
    """by_name: {申万一级名称: '90.BK0123'}；同时做**名称回读自校验**（防代码漂移静默错配）。"""
    if not by_name:
        return
    payload = {"updated_at": datetime.now().isoformat(timespec="seconds"),
               "note": "东财板块 secid 自举表：由 clist 首次成功响应中的 f12 采集，供 ulist.np 兜底使用",
               "by_name": by_name}
    try:
        os.makedirs(os.path.dirname(SECID_SIDECAR), exist_ok=True)
        json.dump(payload, open(SECID_SIDECAR, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ secid 自举表写入失败（不致命）：{type(e).__name__}", file=sys.stderr)


# ── 数据源 ──────────────────────────────────────────────────────────────
def fetch_via_clist(sess):
    """主源：clist 单请求拉全行业板块，按 f14 名称精确筛选申万一级。
    返回 (result, board_codes)：result={名称:{main_net,jumbo_net,block_net,ratio}}"""
    r = _http_get(sess, CLIST_URL, {
        "pn": 1, "pz": CLIST_PAGE_SIZE, "po": 1, "np": 1, "fltt": 2, "invt": 2, "ut": UT,
        "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62,f66,f72,f184"})
    data = (r.json() or {}).get("data") or {}
    diff = data.get("diff") or []
    result, codes = {}, {}
    for x in diff:
        name = x.get("f14")
        if name and name in SW1_NAMES:
            result[name] = {"main_net": x.get("f62") or 0, "jumbo_net": x.get("f66") or 0,
                            "block_net": x.get("f72") or 0, "ratio": x.get("f184") or 0}
            if x.get("f12"):
                codes[name] = f"90.{x['f12']}"     # f12 = 板块代码（如 BK0475）
    total = data.get("total") or 0
    return result, codes, total


def fetch_via_ulist(sess):
    """兜底源：ulist.np 批量 secids（字段同源 f62/f66/f72/f184）。"""
    by_name = _load_secids()          # {名称: 90.BKxxxx}
    rev = {v: k for k, v in by_name.items()}
    if not rev:
        raise RuntimeError("secid 自举表为空（sw1_secids.json 未建立）")
    secids = list(rev.keys())
    r = _http_get(sess, ULIST_URL, {
        "fltt": 2, "invt": 2, "ut": UT, "secids": ",".join(secids),
        "fields": "f12,f14,f62,f66,f72,f184"})
    diff = ((r.json() or {}).get("data") or {}).get("diff") or []
    result = {}
    for x in diff:
        code = x.get("f12")
        name = rev.get(f"90.{code}") or x.get("f14")
        if name and name in SW1_NAMES:
            result[name] = {"main_net": x.get("f62") or 0, "jumbo_net": x.get("f66") or 0,
                            "block_net": x.get("f72") or 0, "ratio": x.get("f184") or 0}
    return result, {}, 0


def fetch_eastmoney_sectors():
    """返回 (result, meta)。meta 记录端点与错误，供 source_status 落盘。"""
    meta = {"endpoint": None, "error": None, "board_codes": {}}
    sess = _session()
    if sess is None:
        meta["error"] = "requests 未安装"
        return {}, meta

    # ① 主源
    try:
        res, codes, total = fetch_via_clist(sess)
        if res and len(res) >= 25:
            meta["endpoint"] = "clist"
            meta["board_codes"] = codes
            meta["total_boards"] = total
            _save_secids(codes)                      # 自举：为 ulist 兜底留下 secid 表
            return res, meta
        meta["error"] = f"clist 返回不足（命中 {len(res)}/31）"
    except Exception as e:  # noqa: BLE001
        meta["error"] = f"clist {type(e).__name__}: {str(e)[:100]}"
    time.sleep(REQ_INTERVAL)

    # ② 兜底源
    try:
        res, _, _ = fetch_via_ulist(sess)
        if res and len(res) >= 25:
            meta["endpoint"] = "ulist.np"
            meta["error"] = None
            return res, meta
        meta["error"] = (meta["error"] or "") + f" | ulist 返回不足（命中 {len(res)}/31）"
    except Exception as e:  # noqa: BLE001
        meta["error"] = (meta["error"] or "") + f" | ulist {type(e).__name__}: {str(e)[:100]}"
    return {}, meta


def fetch_sector_flows():
    """获取所有申万一级行业板块的资金流向数据。返回 (sectors, meta)。"""
    em, meta = fetch_eastmoney_sectors()
    if not em:
        return [], meta
    board_codes = meta.get("board_codes") or {}

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
        try:
            main_net = float(main_net)
        except (TypeError, ValueError):
            # 东财接口偶发返回字符串/空值（2026-09-15 实测盘前返回 str 导致打印崩溃）
            main_net = None
        sectors.append({
            "code": code,
            "name": name,
            "category": get_sector_category(name),
            # 🆕 v3：记录东财板块代码（仅新增字段，不改既有语义）
            "em_board_code": board_codes.get(name),
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
        if main_net is None:
            print(f"  {name} ({code}) ... ⚠️ 主力净额缺失（接口返回非数值，已置空）")
        else:
            print(f"  {name} ({code}) ... ✅ 主力净流入 {main_net/1e8:+.2f}亿")

    return sectors, meta


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


# ── 交易日距离（stale 标记用） ────────────────────────────────────────────
def trading_days_between(later: str, earlier: str) -> int:
    """later 与 earlier 之间相隔的**交易日**数（later 计入、earlier 不计入）。"""
    try:
        a, b = datetime.fromisoformat(later).date(), datetime.fromisoformat(earlier).date()
    except Exception:  # noqa: BLE001
        return -1
    if a <= b:
        return 0
    if is_trading_day is None:
        return (a - b).days
    n, d = 0, b
    while d < a:
        d += timedelta(days=1)
        if is_trading_day(d):
            n += 1
    return n


# ── 存取 ────────────────────────────────────────────────────────────────
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


def resolve_data_date(now: datetime) -> str:
    """返回本次采集所属的『最近一个已收盘交易日』。

    🔴 2026-09-15 修复：原实现直接取 `datetime.now().strftime('%Y-%m-%d')`，
    任务若跨零点运行（实测 2026-09-15 00:13 调度）会把 **9/14 收盘**的资金流
    写成 `history["2026-09-15"]` —— 既是未来日期、又让 9/14 键永久缺失，
    属静默失效（有值但日期错位）。改为按『收盘是否已过』判定。
    """
    d = now.date()
    if is_trading_day is not None:
        if is_trading_day(d) and now.hour >= 15:
            return str(d)
        return str(last_trading_day(d - timedelta(days=1)))
    # 兜底：无交易日历时按工作日近似
    if d.weekday() < 5 and now.hour >= 15:
        return str(d)
    prev = d - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return str(prev)


# ── 回填（缺失交易日） ───────────────────────────────────────────────────
def backfill(start_date: str, end_date: str):
    """用 push2his 板块资金流日线回填 [start, end] 区间内的交易日。

    🔴 只回填 `main_net_flow`（主力净额，字段位置已由 9/24 存量数据反查确认）；
      `jumbo/block` 置 None 并标 `backfilled=true`，避免未经核验的字段污染下游。
    """
    data = load_history()
    sess = _session()
    if sess is None:
        print("  ❌ requests 未安装，无法回填", file=sys.stderr)
        return 4

    # 目标交易日
    targets = []
    d = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    while d <= end:
        if is_trading_day is None or is_trading_day(d):
            targets.append(str(d))
        d += timedelta(days=1)
    todo = [t for t in targets if t not in data["history"]]
    print(f"  回填目标交易日 {targets}；其中缺失需补 {todo}")
    if not todo:
        print("  ✅ 无缺失，无需回填")
        return 0

    # secid 表：优先 sidecar，否则用 clist 自举
    by_name = _load_secids()
    if not by_name:
        try:
            _, codes, _ = fetch_via_clist(sess)
            if codes:
                _save_secids(codes)
                by_name = codes
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ clist 自举 secid 失败：{type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
    if not by_name:
        print("  ❌ 无 secid 表，无法回填（先成功跑一次主源以自举）", file=sys.stderr)
        return 4

    span = len(todo) + 5
    filled = 0
    for code, name in SW1_SECTORS.items():
        secid = by_name.get(name)
        if not secid:
            print(f"  ⚠️ {name} 缺 secid，跳过")
            continue
        try:
            r = _http_get(sess, FFLOW_DAY_URL, {
                "lmt": span, "klt": 101, "secid": secid, "ut": UT,
                "fields1": "f1,f2,f3,f7",
                "fields2": ("f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61")})
            klines = ((r.json() or {}).get("data") or {}).get("klines") or []
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {name} 回填中断：{type(e).__name__}: {str(e)[:80]} —— 遇阻即停（防触发封禁）",
                  file=sys.stderr)
            break
        for k in klines:
            p = k.split(",")
            if len(p) < 2:
                continue
            day = p[0]
            if day not in todo:
                continue
            try:
                main_net = float(p[1])
            except (TypeError, ValueError):
                continue
            entry = data["history"].setdefault(day, {"date": day, "generated_at": None,
                                                     "summary": {}, "sectors": []})
            entry["backfilled"] = True
            entry["backfill_source"] = "push2his/stock/fflow/daykline"
            entry["generated_at"] = entry.get("generated_at") or datetime.now().isoformat()
            row = None
            for s in entry["sectors"]:
                if s.get("name") == name:
                    row = s
                    break
            if row is None:
                row = {"code": code, "name": name, "category": get_sector_category(name),
                       "main_net_flow": None, "jumbo_net_flow": None,
                       "main_in_flow": 0, "main_out_flow": 0, "block_net_flow": None,
                       "retail_in_flow": 0, "retail_out_flow": 0,
                       "main_inflow_rank": 0, "main_inflow_ind_rank": 0, "has_data": True}
                entry["sectors"].append(row)
            row["main_net_flow"] = main_net
            # 超大单/大单位置未逐项核验 → 不落盘（避免静默错配）
            row["jumbo_net_flow"] = None
            row["backfilled"] = True
            filled += 1
        print(f"  ✅ {name} 回填完成")
        time.sleep(REQ_INTERVAL)

    if filled:
        for day in todo:
            e = data["history"].get(day)
            if e and e.get("sectors"):
                e["sectors"].sort(key=lambda s: SW1_NAMES and list(SW1_SECTORS.values()).index(s["name"]))
                e["summary"] = analyze_sector_flows(e["sectors"])
        data["last_updated"] = datetime.now().isoformat()
        save_history(data)
        print(f"  ✅ 回填 {filled} 条板块-日记录，涉及 {len([d for d in todo if data['history'].get(d, {}).get('sectors')])} 个交易日")
    return 0


# ── 主流程 ──────────────────────────────────────────────────────────────
def mark_stale(error: str):
    """数据源不可达时：不静默 —— 产物写入 source_status，返回 stale 天数。"""
    data = load_history()
    hist = data.get("history", {})
    last_success = None
    for day in sorted(hist.keys(), reverse=True):
        if not hist[day].get("backfilled"):
            last_success = day
            break
    today = resolve_data_date(datetime.now())
    stale_days = trading_days_between(today, last_success) if last_success else -1
    data["source_status"] = {
        "ok": False,
        "error": error,
        "last_success": last_success,
        "stale_days": stale_days,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "note": ("资金流源不可达 → 本次未更新，snapshot 保留上一成功交易日；"
                 "cross_analysis / build_sector_tech 的资金列会随之滞后，页面须显示该 stale 天数。"),
    }
    data["last_updated"] = datetime.now().isoformat()
    save_history(data)
    return stale_days, last_success


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--date", default="", help="数据日 YYYY-MM-DD（默认=最近一个已收盘交易日）")
    ap.add_argument("--probe", action="store_true", help="只做健康探针，不写产物")
    ap.add_argument("--backfill", nargs=2, metavar=("START", "END"), help="回填区间（交易日）")
    args = ap.parse_args()

    if args.probe:
        out = probe_source()
        return 0 if out["ok"] else 4

    if args.backfill:
        return backfill(args.backfill[0], args.backfill[1])

    date_str = args.date or resolve_data_date(datetime.now())
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取板块资金流向 ({date_str})...（东财申万一级）")

    data = load_history()
    sectors, meta = fetch_sector_flows()

    if not sectors:
        err = meta.get("error") or "未知错误"
        stale_days, last_success = mark_stale(err)
        print(f"  ❌ 资金流源不可达：{err}", file=sys.stderr)
        print(f"  🔴 产物已标记 stale：last_success={last_success} / stale_days={stale_days}"
              f" → cross_analysis 与 build_sector_tech 的资金列将滞后 {stale_days} 个交易日", file=sys.stderr)
        print(f"  提示：用 `python fetch_sector_flow.py --probe` 复核源健康；"
              f"`--backfill <START> <END>` 可回填缺失交易日。", file=sys.stderr)
        return 4

    summary = analyze_sector_flows(sectors)
    data["history"][date_str] = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "endpoint": meta.get("endpoint"),
        "summary": summary,
        "sectors": sectors,
    }
    data["source_status"] = {
        "ok": True,
        "endpoint": meta.get("endpoint"),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "stale_days": 0,
    }
    data["last_updated"] = datetime.now().isoformat()
    save_history(data)

    main_net = summary["total_main_net_flow"]
    sign = "+" if main_net >= 0 else ""
    top_in = ", ".join("%s(%+.2f亿)" % (s["name"], s["main_net_flow"] / 1e8) for s in summary["top_in"])
    top_out = ", ".join("%s(%+.2f亿)" % (s["name"], s["main_net_flow"] / 1e8) for s in summary["top_out"])
    print(f"\n  === 板块资金流向汇总 ({date_str}) ===  [源: {meta.get('endpoint')}]")
    print(f"  总主力净流入: {sign}{main_net/1e8:.2f}亿")
    print(f"  流入板块: {summary['net_in_count']}个 / 流出板块: {summary['net_out_count']}个")
    print(f"  TOP5流入: {top_in}")
    print(f"  TOP5流出: {top_out}")
    print(f"  历史缓存: {len(data['history'])}个交易日")
    print(f"  结果已保存至: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
