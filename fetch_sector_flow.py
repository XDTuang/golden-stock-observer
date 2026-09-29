#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜金观测 — 板块资金流向采集脚本 v4（申万一级 · 东财口径 · 主机池故障转移）

版本沿革
  v2  数据源从 westock-data 切为东方财富 HTTP 接口；失败保留旧数据（**静默**）。
  v3（2026-09-29 上午）根因修复：东财 `/api/qt/clist/get` 被边缘定点封禁 →
      换 `ulist.np` 兜底 + 降频 + UA 去机器人标识 + **大声失败**（`source_status` + 退出码 4）+ `--probe/--backfill`。
  v4（2026-09-29 · 落实版）补齐「可执行性」，四件事：

    ① **主机池故障转移 + 健康记忆**
       实测：东财**生产分片池**（`push2` / `1.push2` / `17.push2` / `48.push2` / `push2delay` / `push2his`）
       被同一条风控规则覆盖（全部 RST），而 **`push2test.eastmoney.com` 未被覆盖** ——
       `clist` 返回 200、`total=496`、**31/31 申万一级命中**，且数据与生产**等价**（见 ④ 三方对账）。
       → 脚本按「上次成功的 host 优先」顺序**逐台试、每台只试 1 次**
       （🔴 禁对同一 host 重试：高频重试会把可用端点一起打死），成功即记
       `preferred` 到 `output/em_host_state.json`。

    ② **日期标签权威源 daykline**（`push2his/stock/fflow/daykline`）
       每行自带日期 ⇒ **免疫「生成日 ≠ 数据日」**，且**可回填任意历史交易日**。
       作为「指定日取值」的权威路径 + 回填路径。

    ③ **安全窗口守卫**（修一处**存量静默错位**）
       `clist` 返回的是**最新快照**（无日期标签）。实测：竞价开始前 = 上一交易日收盘；15:00 后 = 当日收盘；
       **09:15–15:00 竞价中/盘中 = 当日未收盘值** —— 而旧版 `resolve_data_date` 在 `hour < 15` 时一律返回
       **上一交易日** ⇒ 盘中运行会把「今日盘中值」写成「上一交易日收盘值」（与 2026-09-15 跨零点 bug 同族）。
       v4 用 `snapshot_date()` 统一判定：快照数据日 ≠ 目标日 ⇒ **不用快照**，改走 ②。

    ④ **已核验的字段映射**（三方对账通过，非推断）
       日线字段序：`[日期, 主力净额, 小单, 中单, 大单, 超大单, …]`
       对账：**电子 -228.76 亿 / 国防军工 +8.84 亿 / 医药生物 -69.00 亿**（9/24）
         ≡ 存量 `sector_flow.json` 的 clist 值 ≡ K3 周报的 iFinD 核验值
       ⇒ **大单 = index4 → `block_net_flow`；超大单 = index5 → `jumbo_net_flow`**
         ⇒ 回填可**安全填全 main / jumbo / block 三项**（v3 曾因未核验而置 None）。

用法:
  python fetch_sector_flow.py                                   # 采集「最近一个已收盘交易日」
  python fetch_sector_flow.py --date 2026-09-28                 # 指定数据日
  python fetch_sector_flow.py --probe                           # 主机池健康探针（不写产物）
  python fetch_sector_flow.py --backfill 2026-09-23 2026-09-28  # 回填区间（交易日）
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
HOST_STATE = os.path.join(SCRIPT_DIR, "output", "em_host_state.json")

# ── 东财主机池（2026-09-29 实测：生产分片池被封；push2test 可用且数据等价）────────
EM_HOSTS = [
    "push2.eastmoney.com",        # 生产主域（可能被风控覆盖）
    "push2test.eastmoney.com",    # 测试节点（实测未被覆盖，数据与生产等价）
    "push2delay.eastmoney.com",   # 延时镜像
    "push2his.eastmoney.com",     # 历史域
]
CLIST_PATH = "/api/qt/clist/get"
ULIST_PATH = "/api/qt/ulist.np/get"
FFLOW_DAY_PATH = "/api/qt/stock/fflow/daykline/get"

# `ut` 取自东财资金流页面现行 JS（data.eastmoney.com/newstatic/js/bkzj/list.js，2026-09-29 抓取）
UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

# 🔴 UA 去机器人标识（原 "GoldenStockObserver/1.0" 是给风控送特征）
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://data.eastmoney.com/bkzj/hy.html",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
TIMEOUT = 15
REQ_INTERVAL = 1.2          # 请求间隔秒
MAX_ATTEMPTS_PER_HOST = 1   # 🔴 每台只试 1 次（禁重试风暴）

# 申万一级行业板块（旧代码保留作产物 `code` 字段：`pt01` + 申万一级指数代码）
SW1_SECTORS = {
    "pt01801780": "银行", "pt01801720": "建筑装饰", "pt01801950": "煤炭", "pt01801790": "非银金融",
    "pt01801230": "综合", "pt01801120": "食品饮料", "pt01801140": "轻工制造", "pt01801030": "基础化工",
    "pt01801080": "电子", "pt01801130": "纺织服饰", "pt01801960": "石油石化", "pt01801110": "家用电器",
    "pt01801180": "房地产", "pt01801740": "国防军工", "pt01801010": "农林牧渔", "pt01801150": "医药生物",
    "pt01801040": "钢铁", "pt01801750": "计算机", "pt01801880": "汽车", "pt01801160": "公用事业",
    "pt01801980": "美容护理", "pt01801170": "交通运输", "pt01801050": "有色金属", "pt01801200": "商贸零售",
    "pt01801730": "电力设备", "pt01801760": "传媒", "pt01801770": "通信", "pt01801210": "社会服务",
    "pt01801710": "建筑材料", "pt01801890": "机械设备", "pt01801970": "环保",
}
SW1_NAMES = set(SW1_SECTORS.values())

# 🆕 v4 · 东财板块 secid **实测种子**（2026-09-29 取自 clist 的 f12，31/31 命中）
#    每次 clist 成功后自动刷新 → 不是「猜的代码」，也不怕东财改码。
SECID_SEED = {
    "银行": "90.BK1283", "建筑装饰": "90.BK1209", "煤炭": "90.BK0437", "非银金融": "90.BK1203",
    "综合": "90.BK1217", "食品饮料": "90.BK0438", "轻工制造": "90.BK1212", "基础化工": "90.BK1206",
    "电子": "90.BK1201", "纺织服饰": "90.BK0436", "石油石化": "90.BK0464", "家用电器": "90.BK0456",
    "房地产": "90.BK1202", "国防军工": "90.BK1204", "农林牧渔": "90.BK0433", "医药生物": "90.BK1216",
    "钢铁": "90.BK0479", "计算机": "90.BK1207", "汽车": "90.BK1211", "公用事业": "90.BK0427",
    "美容护理": "90.BK1035", "交通运输": "90.BK1210", "有色金属": "90.BK0478", "商贸零售": "90.BK1213",
    "电力设备": "90.BK1200", "传媒": "90.BK0486", "通信": "90.BK1215", "社会服务": "90.BK1214",
    "建筑材料": "90.BK1208", "机械设备": "90.BK1205", "环保": "90.BK0728",
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


def get_sector_category(name):
    for cat, names in SECTOR_CATEGORIES.items():
        if name in names:
            return cat
    return "其他"


# ── 基础 IO ────────────────────────────────────────────────────────────
def _load_json(path, default):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return default


def _save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 🔴 保持与既有产物一致的**无 BOM** 写法（本仓 JSON 产物约定；用 utf-8-sig 会引入 BOM 触雷）
    json.dump(payload, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _session():
    if requests is None:
        return None
    s = requests.Session()
    s.trust_env = False   # 绕开本机代理环境变量（生产无代理时为 no-op；沙箱/开发机可避免 ProxyError）
    return s


# ── 主机池（故障转移 + 健康记忆） ─────────────────────────────────────────
def _host_order():
    pref = (_load_json(HOST_STATE, {}) or {}).get("preferred")
    order = list(EM_HOSTS)
    if pref in order:
        order.remove(pref)
        order.insert(0, pref)
    return order


def _remember_host(host):
    st = _load_json(HOST_STATE, {}) or {}
    st["preferred"] = host
    st.setdefault("ok_hosts", {})[host] = {"ok_at": datetime.now().isoformat(timespec="seconds")}
    st["updated_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        _save_json(HOST_STATE, st)
    except Exception:  # noqa: BLE001
        pass


def _get_json(sess, path, params, hosts=None, timeout=TIMEOUT):
    """主机池依次尝试：**每台只 1 次**（禁重试风暴）。成功返回 (json, host)。"""
    tried = []
    for h in (hosts or _host_order()):
        try:
            r = sess.get(f"https://{h}{path}", params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            j = r.json()
            if not isinstance(j, dict):
                raise ValueError("响应非 JSON 对象")
            _remember_host(h)
            return j, h
        except Exception as e:  # noqa: BLE001
            tried.append(f"{h}:{type(e).__name__}")
        time.sleep(REQ_INTERVAL)
    raise RuntimeError("主机池全部不可用 → " + "; ".join(tried))


# ── secid 表（实测种子 + clist 自举刷新） ─────────────────────────────────
def _load_secids():
    by = (_load_json(SECID_SIDECAR, {}) or {}).get("by_name") if isinstance(_load_json(SECID_SIDECAR, {}), dict) else None
    return by if by else dict(SECID_SEED)


def _save_secids(by_name):
    if by_name:
        _save_json(SECID_SIDECAR, {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "note": "东财板块 secid 表：种子为 2026-09-29 实测值；每次 clist 成功后按 f12 自动刷新",
            "by_name": by_name})


# ── 快照安全窗口（修存量静默错位） ─────────────────────────────────────────
def snapshot_date(now):
    """`clist` 快照所代表的『数据日』。None ⇒ 不可用（竞价中/盘中，语义不确定）。"""
    d, hm = now.date(), now.hour * 60 + now.minute
    if is_trading_day is None:            # 无交易日历：按工作日近似
        if d.weekday() < 5 and hm >= 15 * 60:
            return str(d)
        p = d - timedelta(days=1)
        while p.weekday() >= 5:
            p -= timedelta(days=1)
        return str(p)
    if is_trading_day(d):
        if hm >= 15 * 60:
            return str(d)                                  # 已收盘 → 今日收盘
        if hm < 9 * 60 + 15:
            return str(last_trading_day(d - timedelta(days=1)))   # 竞价前 → 上一交易日收盘
        return None                                        # 🔴 竞价中 / 盘中 → 禁写历史
    return str(last_trading_day(d))                        # 非交易日 → 上一交易日收盘


def resolve_data_date(now):
    """本次采集所属的『最近一个已收盘交易日』（与快照安全窗口同源，避免两套口径打架）。"""
    sd = snapshot_date(now)
    if sd:
        return sd
    d = now.date()
    if is_trading_day is not None and is_trading_day(d):
        return str(last_trading_day(d - timedelta(days=1)))
    return str(d)


# ── 取数①：快照（1 请求，仅安全窗口） ──────────────────────────────────────
def fetch_snapshot(sess):
    """clist 单请求拉全行业板块（pz=500），按 f14 名称精确筛申万一级。
    返回 (result, board_codes, host)。"""
    j, host = _get_json(sess, CLIST_PATH, {
        "pn": 1, "pz": 500, "po": 1, "np": 1, "fltt": 2, "invt": 2, "ut": UT,
        "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62,f66,f72,f184"})
    data = j.get("data") or {}
    result, codes = {}, {}
    for x in data.get("diff") or []:
        name = x.get("f14")
        if name and name in SW1_NAMES:
            result[name] = {"main_net": x.get("f62"), "jumbo_net": x.get("f66"),
                            "block_net": x.get("f72"), "ratio": x.get("f184")}
            if x.get("f12"):
                codes[name] = f"90.{x['f12']}"
    if len(codes) >= 25:
        _save_secids(codes)      # 自举刷新（按 f14 名称匹配，天然含名称回读自校验）
    return result, codes, host


def fetch_via_ulist(sess):
    """兜底快照路径：ulist.np 批量 secids（字段同源 f62/f66/f72/f184）。"""
    by_name = _load_secids()
    rev = {v: k for k, v in by_name.items()}
    if not rev:
        raise RuntimeError("secid 表为空")
    j, host = _get_json(sess, ULIST_PATH, {
        "fltt": 2, "invt": 2, "ut": UT, "secids": ",".join(rev.keys()),
        "fields": "f12,f14,f62,f66,f72,f184"})
    result = {}
    for x in ((j.get("data") or {}).get("diff") or []):
        name = rev.get(f"90.{x.get('f12')}") or x.get("f14")
        if name in SW1_NAMES:
            result[name] = {"main_net": x.get("f62"), "jumbo_net": x.get("f66"),
                            "block_net": x.get("f72"), "ratio": x.get("f184")}
    return result, {}, host


# ── 取数②：日期标签权威源（daykline，可回填） ────────────────────────────────
DAY_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
# 已核验字段序（三方对账）：[0]日期 [1]主力净额 [2]小单 [3]中单 [4]大单 [5]超大单 …
DAY_IDX = {"date": 0, "main": 1, "small": 2, "mid": 3, "block": 4, "jumbo": 5}


def fetch_daykline(sess, target_dates, lmt=None):
    """逐板块取资金流日线 → {日期: {名称: {main, jumbo, block}}}。
    逐只带间隔；**任一只失败即停**（防封禁），返回 (got, host, 成功板块数, 中途错误)。"""
    by_name = _load_secids()
    rev = {v: k for k, v in by_name.items()}
    if not rev:
        raise RuntimeError("secid 表为空")
    lmt = lmt or max(len(target_dates) + 5, 10)
    out, host, done, err = {}, None, 0, None
    for secid, name in rev.items():
        try:
            j, h = _get_json(sess, FFLOW_DAY_PATH, {
                "lmt": lmt, "klt": 101, "secid": secid, "ut": UT,
                "fields1": "f1,f2,f3,f7", "fields2": DAY_FIELDS2})
        except Exception as e:  # noqa: BLE001
            err = f"{name}:{type(e).__name__}:{str(e)[:70]}"
            break
        host = h
        done += 1
        for k in ((j.get("data") or {}).get("klines") or []):
            p = k.split(",")
            if len(p) <= DAY_IDX["jumbo"]:
                continue
            day = p[DAY_IDX["date"]]
            if day not in target_dates:
                continue
            try:
                out.setdefault(day, {})[name] = {
                    "main_net": float(p[DAY_IDX["main"]]),
                    "jumbo_net": float(p[DAY_IDX["jumbo"]]),
                    "block_net": float(p[DAY_IDX["block"]]),
                }
            except (TypeError, ValueError):
                continue
        time.sleep(REQ_INTERVAL)
    return out, host, done, err


# ── 组装与分析 ──────────────────────────────────────────────────────────
def build_rows(per_name, board_codes=None):
    board_codes = board_codes or {}
    seed = _load_secids()
    rows = []
    for code, name in SW1_SECTORS.items():
        f = per_name.get(name)

        def _f(key):
            if not f:
                return None
            v = f.get(key)
            if v is None or v == "-":
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        main = _f("main_net")
        rows.append({
            "code": code, "name": name, "category": get_sector_category(name),
            "em_board_code": board_codes.get(name) or seed.get(name),
            "main_net_flow": main,
            "jumbo_net_flow": _f("jumbo_net"),
            "block_net_flow": _f("block_net"),
            "main_in_flow": 0, "main_out_flow": 0,
            "retail_in_flow": 0, "retail_out_flow": 0,
            "main_inflow_rank": 0, "main_inflow_ind_rank": 0,
            "has_data": main is not None,
        })
    return rows


def analyze_sector_flows(sectors):
    cat = {}
    for s in sectors:
        cat[s.get("category", "其他")] = cat.get(s.get("category", "其他"), 0) + (s.get("main_net_flow") or 0)
    ss = sorted(sectors, key=lambda x: x.get("main_net_flow", 0) or 0, reverse=True)
    return {
        "total_main_net_flow": sum(s.get("main_net_flow", 0) or 0 for s in sectors),
        "total_jumbo_net_flow": sum(s.get("jumbo_net_flow", 0) or 0 for s in sectors),
        "category_nets": cat,
        "sector_count": len([s for s in sectors if s.get("has_data")]),
        "net_in_count": len([s for s in sectors if (s.get("main_net_flow") or 0) > 0]),
        "net_out_count": len([s for s in sectors if (s.get("main_net_flow") or 0) < 0]),
        "top_in": [{"name": s["name"], "main_net_flow": s.get("main_net_flow")} for s in ss[:5]],
        "top_out": [{"name": s["name"], "main_net_flow": s.get("main_net_flow")} for s in ss[-5:][::-1]],
    }


# ── 健康探针 ────────────────────────────────────────────────────────────
def probe_source(verbose=True):
    sess = _session()
    out = {"probed_at": datetime.now().isoformat(timespec="seconds"), "hosts": {}, "ok": False}
    if sess is None:
        out["error"] = "requests 未安装"
        return out
    for h in _host_order():
        t0 = time.time()
        try:
            r = sess.get(f"https://{h}{CLIST_PATH}", params={
                "pn": 1, "pz": 5, "po": 1, "np": 1, "fltt": 2, "invt": 2, "ut": UT,
                "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62"},
                headers=HEADERS, timeout=10)
            n = len((((r.json() or {}).get("data") or {}).get("diff")) or [])
            out["hosts"][h] = {"ok": n > 0, "detail": f"HTTP {r.status_code} diff={n}",
                               "ms": int((time.time() - t0) * 1000)}
            out["ok"] = out["ok"] or n > 0
        except Exception as e:  # noqa: BLE001
            out["hosts"][h] = {"ok": False, "detail": type(e).__name__, "ms": int((time.time() - t0) * 1000)}
        time.sleep(REQ_INTERVAL)
    if verbose:
        for h, v in out["hosts"].items():
            print(f"  {'✅' if v['ok'] else '❌'} {h:30s} {v['detail']:22s} {v['ms']}ms")
    return out


# ── 存取 ────────────────────────────────────────────────────────────────
def load_history():
    d = _load_json(OUTPUT_FILE, None)
    return d if isinstance(d, dict) and "history" in d else {"history": {}, "last_updated": None}


def save_history(data):
    for old in sorted(data["history"].keys(), reverse=True)[20:]:
        del data["history"][old]
    _save_json(OUTPUT_FILE, data)


def trading_days_between(later, earlier):
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


def write_day(data, date_str, per_name, board_codes, endpoint, extra=None):
    rows = build_rows(per_name, board_codes)
    entry = {"date": date_str, "generated_at": datetime.now().isoformat(),
             "endpoint": endpoint, "summary": analyze_sector_flows(rows), "sectors": rows}
    if extra:
        entry.update(extra)
    data["history"][date_str] = entry
    return entry


def mark_stale(error):
    data = load_history()
    last_success = None
    for day in sorted(data.get("history", {}).keys(), reverse=True):
        if (data["history"][day].get("summary") or {}).get("sector_count"):
            last_success = day
            break
    today = resolve_data_date(datetime.now())
    stale = trading_days_between(today, last_success) if last_success else -1
    data["source_status"] = {
        "ok": False, "error": error, "last_success": last_success, "stale_days": stale,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "note": ("资金流源不可达 → 本次未更新，snapshot 保留上一成功交易日；"
                 "cross_analysis / build_sector_tech 的资金列会随之滞后，页面须显示该 stale 天数。"),
    }
    data["last_updated"] = datetime.now().isoformat()
    save_history(data)
    return stale, last_success


# ── 主流程 ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--backfill", nargs=2, metavar=("START", "END"))
    args = ap.parse_args()

    if args.probe:
        return 0 if probe_source()["ok"] else 4

    sess = _session()
    if sess is None:
        print("  ❌ requests 未安装", file=sys.stderr)
        return 2
    now = datetime.now()

    # ── 回填 ──
    if args.backfill:
        data = load_history()
        d0 = datetime.fromisoformat(args.backfill[0]).date()
        d1 = datetime.fromisoformat(args.backfill[1]).date()
        targets, d = [], d0
        while d <= d1:
            if is_trading_day is None or is_trading_day(d):
                targets.append(str(d))
            d += timedelta(days=1)
        todo = [t for t in targets if not (data["history"].get(t, {}).get("summary") or {}).get("sector_count")]
        print(f"  回填 {args.backfill[0]}~{args.backfill[1]}｜目标交易日 {targets}｜需补 {todo}")
        if not todo:
            # 幂等：即使无缺口，也把 source_status 按现状刷新一次（防「已补齐但状态仍显示 stale」）
            target = resolve_data_date(datetime.now())
            last_success = max(data["history"].keys()) if data["history"] else None
            if last_success:
                data["source_status"] = {
                    "ok": True,
                    "endpoint": "status-refresh(no-op)",
                    "last_success": last_success,
                    "stale_days": trading_days_between(target, last_success),
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                    "note": "无缺口；source_status 已按现状重算。",
                }
                data["last_updated"] = datetime.now().isoformat()
                save_history(data)
                print(f"  ✅ 无缺失，无需回填；source_status 已刷新 "
                      f"(last_success={last_success} / stale_days={data['source_status']['stale_days']})")
            else:
                print("  ✅ 无缺失，无需回填")
            return 0
        try:
            got, host, n, err = fetch_daykline(sess, set(todo), lmt=len(todo) + 10)
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ 回填失败：{type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
            return 4
        print(f"  日线取数：host={host}｜成功板块 {n}/{len(SW1_SECTORS)}" + (f"｜中途错: {err}" if err else ""))
        filled = 0
        for day in todo:
            per = got.get(day) or {}
            if len(per) < 25:
                print(f"  ⚠️ {day} 仅取到 {len(per)}/31 → **跳过**（不写不完整日）")
                continue
            write_day(data, day, per, None, f"daykline@{host}",
                      extra={"backfilled": True, "backfill_source": f"{host}{FFLOW_DAY_PATH}"})
            filled += 1
            s = data["history"][day]["summary"]
            print(f"  ✅ {day} 已回填（{len(per)}/31 · main/jumbo/block 全填）"
                  f" 总主力 {s['total_main_net_flow']/1e8:+.2f}亿")
        if filled:
            # 🔴 回填成功后必须刷新 source_status，否则状态仍停在「不可达/stale」→ 误导下游与简报
            target = resolve_data_date(datetime.now())
            last_success = max(data["history"].keys())
            data["source_status"] = {
                "ok": True,
                "endpoint": f"daykline@{host}",
                "backfilled_to": last_success,
                "last_success": last_success,
                "stale_days": trading_days_between(target, last_success),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
                "note": "本次以 daykline 回填补齐缺口；stale_days 已按回填后的最新数据日重算（=0 即不再滞后）。",
            }
            data["last_updated"] = datetime.now().isoformat()
            save_history(data)
            print(f"  🩹 source_status 已刷新：ok=True / last_success={last_success} / "
                  f"stale_days={data['source_status']['stale_days']}")
        return 0 if filled else 4

    # ── 常规采集 ──
    date_str = args.date or resolve_data_date(now)
    sd = snapshot_date(now)
    print(f"[{now.strftime('%H:%M:%S')}] 采集板块资金流（目标数据日 {date_str}）…（东财申万一级）")
    data = load_history()

    per_name, board_codes, endpoint, err = {}, None, None, None
    # ① 快照快路径（1 请求）—— 仅当快照数据日 == 目标数据日
    if sd == date_str:
        try:
            snap, codes, host = fetch_snapshot(sess)
            if len([1 for v in snap.values() if v.get("main_net") not in (None, "-")]) >= 25:
                per_name, board_codes, endpoint = snap, codes, f"clist@{host}"
            else:
                err = f"快照字段未就绪（{len(snap)}/31）"
        except Exception as e:  # noqa: BLE001
            err = f"clist {type(e).__name__}: {str(e)[:90]}"
    else:
        err = (f"快照不可用（竞价中/盘中，语义不确定）" if sd is None
               else f"快照日 {sd} ≠ 目标日 {date_str}")

    # ①b 兜底快照（ulist）
    if not per_name:
        try:
            snap, _, host = fetch_via_ulist(sess)
            if len([1 for v in snap.values() if v.get("main_net") not in (None, "-")]) >= 25:
                per_name, endpoint, err = snap, f"ulist@{host}", None
        except Exception as e:  # noqa: BLE001
            err = f"{err} | ulist {type(e).__name__}: {str(e)[:80]}"

    # ② 日期标签权威路径（daykline，可回填/可盘中取证）
    if not per_name:
        print(f"  ↪ 快照路径不可用（{err}）→ 走日期标签权威源 daykline")
        try:
            got, host, n, derr = fetch_daykline(sess, {date_str}, lmt=10)
            per = got.get(date_str) or {}
            if len(per) >= 25:
                per_name, endpoint, err = per, f"daykline@{host}", None
            else:
                err = f"{err} | daykline 仅 {len(per)}/31" + (f"（{derr}）" if derr else "")
        except Exception as e:  # noqa: BLE001
            err = f"{err} | daykline {type(e).__name__}: {str(e)[:90]}"

    if not per_name:
        stale, last_ok = mark_stale(err or "未知错误")
        print(f"  ❌ 资金流源不可达：{err}", file=sys.stderr)
        print(f"  🔴 产物已标记 stale：last_success={last_ok} / stale_days={stale} "
              f"→ cross_analysis 与 build_sector_tech 的资金列将滞后 {stale} 个交易日", file=sys.stderr)
        print("  提示：`--probe` 看主机池健康；`--backfill START END` 回填缺失交易日。", file=sys.stderr)
        return 4

    entry = write_day(data, date_str, per_name, board_codes, endpoint)
    # 🔴 成功分支与失败/回填分支的 source_status **须同 schema**（下游/简报按字段读，缺字段会 KeyError）
    data["source_status"] = {"ok": True, "endpoint": endpoint, "last_success": date_str,
                             "checked_at": now.isoformat(timespec="seconds"), "stale_days": 0}
    data["last_updated"] = now.isoformat()
    save_history(data)

    s = entry["summary"]
    print(f"\n  === 板块资金流向汇总 ({date_str}) ===  [源: {endpoint}]")
    print(f"  总主力净流入: {s['total_main_net_flow']/1e8:+.2f}亿")
    print(f"  流入板块: {s['net_in_count']}个 / 流出板块: {s['net_out_count']}个")
    print("  TOP5流入: " + ", ".join("%s(%+.2f亿)" % (x["name"], x["main_net_flow"] / 1e8) for x in s["top_in"]))
    print("  TOP5流出: " + ", ".join("%s(%+.2f亿)" % (x["name"], x["main_net_flow"] / 1e8) for x in s["top_out"]))
    print(f"  历史缓存: {len(data['history'])}个交易日 → {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
