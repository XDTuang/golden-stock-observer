# -*- coding: utf-8 -*-
"""东财 HTTP 统一入口（2026-09-29 立 · 反封禁「单点治本」模块）

════════════════════════════════════════════════════════════════════
■ 立此模块的背景（实测，非推断）
  东财 `/api/qt/*` 系列在**生产分片池**被边缘定点覆盖：
    · push2.eastmoney.com          ❌ RemoteDisconnected（RST）
    · push2delay.eastmoney.com     ❌ RST
    · push2his.eastmoney.com       ❌ RST（2026-09-29 10:0x 实测，封禁范围会扩大）
    · push2test.eastmoney.com      ✅ HTTP 200（clist / stock/get 均可用，数据与生产等价）
  拒绝性质是**频率型临时封禁**：短时高频触发、约 1.5 小时自行解除、且**会扩大到同主机其它路径**。

■ 纪律（任何脚本调用本模块即自动遵守）
  1. **主机池顺序 = 健康记忆优先 → 未被覆盖节点 → 其余**；每台**只试 1 次**，失败即换台
     （🔴 禁对同一台重试 —— 高频重试会把「当时还活着的端点」一起打死）
  2. **RST / 连接错误 = 立即换台**；全部失败则抛 `EMUnavailable`（**大声失败**，
     由调用方写 source_status + 非零退出码，**禁静默返回空值冒充当日数据**）
  3. **请求间强制最小间隔**（`REQ_INTERVAL`），防短时高频越过风控阈值
  4. 成功即写 `output/em_host_state.json` → **全脚本共享健康记忆**，下次直接命中可用节点

■ 用法
    from em_http import get_json, probe_all, EMUnavailable
    j, host = get_json("/api/qt/clist/get", {...})          # 自动故障转移
    j, host = get_json("/api/qt/stock/get", {...}, hosts=["push2test.eastmoney.com"])
    print(probe_all("/api/qt/clist/get", {...}))            # 各主机健康（诊断用）
════════════════════════════════════════════════════════════════════
"""
import json
import os
import time
from datetime import datetime

try:
    import requests
except ImportError:  # 极端情况下不阻断 import
    requests = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOST_STATE = os.path.join(SCRIPT_DIR, "output", "em_host_state.json")

# ── 主机池：**未被覆盖节点排第一**（避免每次先打已被封的节点，那本身就是「送频率」）──
EM_HOSTS = [
    "push2test.eastmoney.com",    # ✅ 实测未被覆盖（2026-09-29）—— 默认首选
    "push2.eastmoney.com",        # 生产主域（2026-09-29 起被封）
    "push2delay.eastmoney.com",   # 延时镜像（2026-09-29 起被封）
    "push2his.eastmoney.com",     # 历史域（2026-09-29 10:0x 起被封）
]

# `ut` 取自东财资金流页面现行 JS（data.eastmoney.com/newstatic/js/bkzj/list.js，2026-09-29 抓取）
UT = "8dec03ba335b81bf4ebdf7b29ec27d15"

# 🔴 UA 去机器人标识（原 "GoldenStockObserver/1.0" 等于给风控送特征）
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Referer": "https://data.eastmoney.com/bkzj/hy.html",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
TIMEOUT = 15
REQ_INTERVAL = 1.2          # 请求最小间隔（秒）
MAX_ATTEMPTS_PER_HOST = 1   # 🔴 每台只试 1 次

_last_req_ts = [0.0]        # 模块级节流游标


class EMUnavailable(RuntimeError):
    """主机池全部不可用（调用方据此写 source_status + 非零退出码，禁静默）。"""


# ───────────────────────── 健康记忆 ─────────────────────────
def _load_state() -> dict:
    try:
        with open(HOST_STATE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_state(st: dict) -> None:
    try:
        os.makedirs(os.path.dirname(HOST_STATE), exist_ok=True)
        with open(HOST_STATE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def host_order() -> list:
    """上次成功的 host 优先 → 其余按 EM_HOSTS 顺序（去重）。"""
    pref = (_load_state() or {}).get("preferred")
    order = list(EM_HOSTS)
    if pref and pref in order:
        order.remove(pref)
        order.insert(0, pref)
    elif pref:
        order.insert(0, pref)
    return order


def remember_host(host: str) -> None:
    st = _load_state() or {}
    st["preferred"] = host
    st["updated_at"] = datetime.now().isoformat(timespec="seconds")
    st.setdefault("ok_hosts", {})[host] = {"ok_at": datetime.now().isoformat(timespec="seconds")}
    _save_state(st)


def note_fail(host: str, detail: str) -> None:
    st = _load_state() or {}
    fails = st.setdefault("fail_hosts", {})
    rec = fails.setdefault(host, {"count": 0})
    rec["count"] = int(rec.get("count", 0)) + 1
    rec["last_detail"] = str(detail)[:160]
    rec["last_fail_at"] = datetime.now().isoformat(timespec="seconds")
    _save_state(st)


def _throttle() -> None:
    """模块级最小请求间隔（跨调用累计）。"""
    gap = time.time() - _last_req_ts[0]
    if gap < REQ_INTERVAL:
        time.sleep(REQ_INTERVAL - gap)
    _last_req_ts[0] = time.time()


def session():
    if requests is None:
        raise EMUnavailable("requests 未安装")
    s = requests.Session()
    s.trust_env = False          # 绕开本机代理，直连
    return s


# ───────────────────────── 核心：带故障转移的 GET ─────────────────────────
def get_json(path, params=None, hosts=None, timeout=TIMEOUT, sess=None,
             min_interval=REQ_INTERVAL, allow_empty=False):
    """按主机池顺序取 JSON。返回 (data_dict, host)。

    · 每台**只试 1 次**，失败即换台（禁同台重试）
    · 全部失败 → 抛 EMUnavailable（大声失败）
    · allow_empty=False 时，"200 但 data 为空" 视为该台失败并继续换台
    """
    sess = sess or session()
    last_err = None
    for h in (hosts or host_order()):
        if min_interval:
            _throttle()
        url = f"https://{h}{path}"
        try:
            r = sess.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                note_fail(h, last_err)
                continue
            j = r.json()
            if not allow_empty and not (j or {}).get("data"):
                last_err = "data 为空"
                note_fail(h, last_err)
                continue
            remember_host(h)
            return j, h
        except Exception as e:                       # RST / 超时 / JSON 解析失败 → 换台
            last_err = f"{type(e).__name__}: {str(e)[:80]}"
            note_fail(h, last_err)
            continue
    raise EMUnavailable(f"东财主机池全部不可用（{path}）：{last_err}")


def probe_all(path, params=None, timeout=TIMEOUT, min_interval=REQ_INTERVAL):
    """逐台探测（诊断用）。返回 {host: {ok, detail, ms}}。**每台 1 请求**。"""
    sess = session()
    out = {"probed_at": datetime.now().isoformat(timespec="seconds"), "hosts": {}, "ok": False}
    for h in host_order():
        if min_interval:
            _throttle()
        t0 = time.time()
        try:
            r = sess.get(f"https://{h}{path}", params=params, headers=HEADERS, timeout=timeout)
            n = len((((r.json() or {}).get("data") or {}).get("diff")) or [])
            has = bool((r.json() or {}).get("data"))
            out["hosts"][h] = {"ok": r.status_code == 200 and has,
                               "detail": f"HTTP {r.status_code} diff={n}" if n else f"HTTP {r.status_code}",
                               "ms": int((time.time() - t0) * 1000)}
            if out["hosts"][h]["ok"]:
                out["ok"] = True
        except Exception as e:
            out["hosts"][h] = {"ok": False, "detail": type(e).__name__,
                               "ms": int((time.time() - t0) * 1000)}
    return out


# ───────────────────────── 常用路径常量 ─────────────────────────
CLIST_PATH = "/api/qt/clist/get"
ULIST_PATH = "/api/qt/ulist.np/get"
STOCK_GET_PATH = "/api/qt/stock/get"
FFLOW_DAY_PATH = "/api/qt/stock/fflow/daykline/get"

if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else CLIST_PATH
    prm = {"pn": 1, "pz": 5, "po": 1, "np": 1, "fltt": 2, "invt": 2, "ut": UT,
           "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62"}
    if p == STOCK_GET_PATH:
        prm = {"secid": "1.600000", "fields": "f57,f58,f127"}
    res = probe_all(p, prm)
    print(json.dumps(res, ensure_ascii=False, indent=1))
