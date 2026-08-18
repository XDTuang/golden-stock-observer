#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜金观测 · 实时盯盘 — 数据采集 + 固定化五层决策算法 v1.0
========================================================
【运行环境】GitHub Actions (ubuntu-latest, python 3.11+, Asia/Shanghai)
【数据源】  全部为无密钥公开接口（与主站现有脚本同源，已验证）：
            1. 指数行情      : qt.gtimg.cn（腾讯实时快照）
            2. 全市场统计    : proxy.finance.qq.com getBoardRankList (aStock 分页 4595只)
            3. 板块资金流    : push2delay.eastmoney.com（东方财富行业板块 f62 主力净流入）
            4. ETF 资金流    : vip.stock.finance.sina.com.cn（新浪，宽基 ETF 净流入，可选）
【输出】    realtime/realtime.json（页面 fetch 用；部署时同步到仓库根目录）
【算法】    五层决策架构（本文件内固化，版本号 algorithm.version，修改需升版本）：
            L0 数据底座    : 口径统一 + 时效分层（trading/午休/收盘/非交易日）
            L1 市场状态机  : 情绪分 = 0.30*涨跌比 + 0.25*涨停 + 0.20*指数强度 + 0.25*资金
            L2 仓位引擎    : 状态 → 仓位区间（固定映射表）
            L3 主线与板块  : 板块主力净流入 TOP + 集中度/共振判断
            L4 标的与执行  : 主力净流入 TOP 过滤（非ST/非高位/净流入>1亿）
            L5 风险闭环    : 4 类固定风险信号（情绪过热/资金背离/集中度/追高风险）

用法: python fetch_realtime.py [--out realtime/realtime.json] [--debug]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

ALGO_VERSION = "1.0.0"

# ───────────────────────── 0. 常量与交易日历 ─────────────────────────
TZ_NAME = "Asia/Shanghai"

# 2026 年 A 股休市日（法定节假日 + 周末补班不涉及；交易所在册休市日）
# 说明：周末由 weekday 判断；以下为工作日休市日（节假日调休）
HOLIDAYS_2026 = {
    # 元旦 2026-01-01(四) ~ 01-02(五)? 以交易所公告为准，此处按常见安排
    "2026-01-01", "2026-01-02",
    # 春节 2026-02-16(一) ~ 02-22(日) 放假，2-23 起
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    # 清明 2026-04-06(一)
    "2026-04-06",
    # 劳动节 2026-05-01(五)
    "2026-05-01",
    # 端午 2026-06-19(五)
    "2026-06-19",
    # 中秋 2026-09-25(五)
    "2026-09-25",
    # 国庆 2026-10-01(四) ~ 10-08(四)
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
}
# 补班交易日（周末上班、正常开市；如需补充可加入；2026 无强制补班则留空）
EXTRA_TRADING_DAYS_2026 = set()


def is_trading_day(d: datetime) -> bool:
    if d.weekday() >= 5:
        return d.weekday() in (0, 1, 2, 3, 4) and False  # 周末不是
    ds = d.strftime("%Y-%m-%d")
    if ds in HOLIDAYS_2026:
        return False
    if d.weekday() >= 5:
        return False
    if ds in EXTRA_TRADING_DAYS_2026:
        return True
    return True


def market_status(now: datetime) -> str:
    """返回数据时效状态：trading / lunch / closed / holiday / preopen"""
    if not is_trading_day(now):
        return "holiday"
    hm = now.hour * 60 + now.minute
    if hm < 9 * 60 + 15:        # < 9:15
        return "preopen"
    if hm < 11 * 60 + 30:       # 9:30-11:30 盘中
        return "trading"
    if hm < 13 * 60:            # 11:30-13:00 午休
        return "lunch"
    if hm < 15 * 60:            # 13:00-15:00 盘中
        return "trading"
    return "closed"             # >= 15:00 收盘


# ───────────────────────── 1. 数据采集 ─────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)",
           "Referer": "https://gu.qq.com/"}
EM_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GoldenStockObserver/1.0)",
              "Referer": "https://data.eastmoney.com/"}

INDEX_CODES = [("sh000001", "上证指数"), ("sz399001", "深证成指"), ("sz399006", "创业板指"),
               ("sh000688", "科创50"), ("sh000300", "沪深300"), ("sh000905", "中证500")]

QT_URL = "https://qt.gtimg.cn/q"
RANK_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList"
EM_SECTOR_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"
SINA_ETF_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs"


def fetch_indexes() -> list:
    """腾讯指数实时快照 → [{code,name,price,chg_pct,turnover(亿),high,low}]"""
    if requests is None:
        return []
    try:
        r = requests.get(QT_URL, params={"q": ",".join(c for c, _ in INDEX_CODES)},
                         headers=HEADERS, timeout=12)
        r.encoding = "gbk"
        out = []
        for line in r.text.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            body = line.split('"')[1]
            f = body.split("~")
            if len(f) < 38:
                continue
            name = f[1]
            price = float(f[3] or 0)
            chg = float(f[32] if len(f) > 32 and f[32] else 0)
            turnover_wan = float(f[37] if len(f) > 37 and f[37] else 0)  # 万元
            high = float(f[33] if len(f) > 33 and f[33] else 0)
            low = float(f[34] if len(f) > 34 and f[34] else 0)
            out.append({"code": f[2], "name": name, "price": round(price, 2),
                        "chg_pct": round(chg, 2), "turnover_yi": round(turnover_wan / 1e4, 1),
                        "high": high, "low": low})
        return out
    except Exception as e:
        print(f"  ⚠️ 指数接口失败: {e}", file=sys.stderr)
        return []


def fetch_market_breadth() -> dict:
    """分页拉取全市场 A 股，统计涨跌家数 / 涨停 / 跌停 / 主力净流入合计。
    涨停规则（按 stock_type 区分）：
      GP-A      主板  10%  → zdf >= 9.9
      GP-A-CYB  创业板 20% → zdf >= 19.9
      GP-A-KCB  科创板 20% → zdf >= 19.9
      GP-A-BJ   北交所 30% → zdf >= 29.5
      名称含 ST         5%  → zdf >= 4.9
    """
    if requests is None:
        return {}
    up = down = flat = 0
    limit_up = limit_down = 0
    main_net_total = 0.0
    turnover_total = 0.0
    stock_rows = []
    try:
        for offset in range(0, 5000, 200):
            params = {"board_code": "aStock", "board_type": "hy", "sort_type": "price",
                      "direct": "down", "offset": offset, "count": 200}
            r = requests.get(RANK_URL, params=params, headers=HEADERS, timeout=15)
            d = r.json()
            lst = (d.get("data") or {}).get("rank_list") or []
            if not lst:
                break
            for x in lst:
                zdf = float(x.get("zdf") or 0)
                stype = x.get("stock_type") or ""
                name = x.get("name") or ""
                is_st = "ST" in name.upper()
                if zdf > 0.001:
                    up += 1
                elif zdf < -0.001:
                    down += 1
                else:
                    flat += 1
                # 涨停判定
                lim = 9.9
                if is_st:
                    lim = 4.9
                elif stype == "GP-A-CYB" or stype == "GP-A-KCB":
                    lim = 19.9
                elif stype == "GP-A-BJ":
                    lim = 29.5
                if zdf >= lim - 0.05:
                    limit_up += 1
                elif zdf <= -(lim - 0.05):
                    limit_down += 1
                main_net_total += float(x.get("zljlr") or 0)  # 万元
                turnover_total += float(x.get("turnover") or 0)  # 万元
                stock_rows.append({
                    "code": x.get("code"), "name": name, "zdf": round(zdf, 2),
                    "zljlr": round(float(x.get("zljlr") or 0) / 1e4, 2),  # 亿
                    "lb": float(x.get("lb") or 0), "hsl": float(x.get("hsl") or 0),
                    "turnover_yi": round(float(x.get("turnover") or 0) / 1e4, 2),
                    "price": float(x.get("zxj") or 0), "stype": stype,
                })
            total = (d.get("data") or {}).get("total") or 0
            if offset + 200 >= total:
                break
        ratio = round(up / down, 2) if down else (99.0 if up else 0.0)
        return {"up": up, "down": down, "flat": flat, "ratio": ratio,
                "limit_up": limit_up, "limit_down": limit_down,
                "main_net_yi": round(main_net_total / 1e4, 2),
                "turnover_yi": round(turnover_total / 1e4, 1),
                "total": up + down + flat, "stocks": stock_rows}
    except Exception as e:
        print(f"  ⚠️ 全市场统计失败: {e}", file=sys.stderr)
        return {}


def fetch_sector_flow() -> list:
    """东财行业板块主力净流入 TOP（f62=主力净流入，单位元）→ [{name, net_yi, pct, main_yi, ...}]"""
    if requests is None:
        return []
    try:
        params = {"pn": 1, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                  "fid": "f62", "fs": "m:90+t:2", "fields": "f12,f14,f62,f66,f72,f184"}
        r = requests.get(EM_SECTOR_URL, params=params, headers=EM_HEADERS, timeout=15)
        d = r.json()
        diff = (d.get("data") or {}).get("diff") or []
        rows = []
        for x in diff:
            rows.append({
                "name": x.get("f14"), "net_yi": round((x.get("f62") or 0) / 1e8, 2),
                "jumbo_yi": round((x.get("f66") or 0) / 1e8, 2),
                "block_yi": round((x.get("f72") or 0) / 1e8, 2),
                "pct": x.get("f184") or 0,
            })
        rows.sort(key=lambda r: r["net_yi"], reverse=True)
        return rows[:20]
    except Exception as e:
        print(f"  ⚠️ 东财板块资金失败: {e}", file=sys.stderr)
        return []


def fetch_etf_flow() -> list:
    """新浪宽基 ETF 净流入（可选维度；失败不阻塞）。仅拉取代表性宽基 ETF。"""
    if requests is None:
        return []
    etfs = ["sh510300", "sh510050", "sh588000", "sz159915", "sh510500", "sz159949"]
    out = []
    try:
        for code in etfs:
            r = requests.get(SINA_ETF_URL, params={"page": 1, "num": 1, "sort": "netamount",
                                                   "asc": 0, "daima": code},
                             headers={"Referer": "https://finance.sina.com.cn/"}, timeout=10)
            arr = r.json()
            if arr:
                it = arr[0]
                out.append({"code": code, "opendate": it.get("opendate"),
                            "net_yi": round(float(it.get("netamount") or 0) / 1e8, 2),
                            "chg_pct": round(float(it.get("changeratio") or 0) * 100, 2)})
            time.sleep(0.3)
        return out
    except Exception as e:
        print(f"  ⚠️ 新浪ETF资金失败: {e}", file=sys.stderr)
        return []


# ───────────────────────── 2. 固定化五层算法 ─────────────────────────
def _norm(v, lo, hi, v_lo, v_hi):
    """把 v 从 [lo,hi] 线性映射到 [v_lo,v_hi]，越界截断"""
    if hi == lo:
        return v_lo
    t = max(0.0, min(1.0, (v - lo) / (hi - lo)))
    return v_lo + t * (v_hi - v_lo)


def calc_l1_sentiment(idx: list, breadth: dict) -> dict:
    """情绪分 = 0.30*S1(涨跌比) + 0.25*S2(涨停) + 0.20*S3(指数强度) + 0.25*S4(资金)"""
    ratio = breadth.get("ratio") or 0
    lu = breadth.get("limit_up") or 0
    avg_idx = 0.0
    if idx:
        avg_idx = sum(i["chg_pct"] for i in idx) / len(idx)
    main_net = breadth.get("main_net_yi") or 0
    s1 = round(_norm(ratio, 0, 4, 0, 100))        # 涨跌比 0→0, 4→100
    s2 = round(_norm(lu, 0, 120, 0, 100))         # 涨停 0→0, 120→100
    s3 = round(_norm(avg_idx, -2, 3, 0, 100))     # 指数均值 -2%→0, +3%→100
    s4 = round(_norm(main_net, -300, 300, 0, 100))  # 主力净流入 -300亿→0, +300亿→100
    score = round(0.30 * s1 + 0.25 * s2 + 0.20 * s3 + 0.25 * s4)
    return {"score": score, "S1": s1, "S2": s2, "S3": s3, "S4": s4,
            "inputs": {"ratio": ratio, "limit_up": lu, "avg_idx_pct": round(avg_idx, 2),
                       "main_net_yi": main_net}}


def calc_l1_state(sent: dict, breadth: dict) -> dict:
    """状态机（固定阈值）→ {state, label, note}"""
    score = sent["score"]
    ratio = breadth.get("ratio") or 0
    lu = breadth.get("limit_up") or 0
    if score >= 85 or lu >= 120 or ratio >= 4.0:
        state, label, note = "overheat", "情绪过热预警", "情绪分极高/涨停过多，禁止追高，仓位收敛至上限以内"
    elif score >= 70 and ratio >= 2.0:
        state, label, note = "strong_bull", "强势普涨", "量价配合，可持股，允许主线板块操作"
    elif score >= 55:
        state, label, note = "structural", "结构强势", "指数分化，只做主线板块，回避弱势方向"
    elif score >= 40:
        state, label, note = "oscillation", "震荡分化", "降低频率，控制单票仓位，等待主线明朗"
    elif score >= 25:
        state, label, note = "weak", "弱势回调", "防守为主，仅小仓低吸，严格止损"
    else:
        state, label, note = "panic", "恐慌下跌", "空仓或极轻仓观望，不抄底，等企稳信号"
    return {"state": state, "label": label, "note": note, "score": score}


def calc_l2_position(state: str) -> dict:
    """仓位引擎：状态 → 仓位区间 + 风控规则（固定映射表）"""
    MAP = {
        "overheat":   {"range": [30, 50], "note": "过热收敛，上限 50%，禁止新增追板仓位"},
        "strong_bull": {"range": [70, 90], "note": "强势普涨，可保持较高仓位，但需留回调子弹"},
        "structural": {"range": [60, 75], "note": "结构强势，聚焦主线板块内操作"},
        "oscillation": {"range": [40, 60], "note": "震荡分化，控制总仓与单票上限"},
        "weak":       {"range": [25, 40], "note": "弱势回调，防守为主，严格止损"},
        "panic":      {"range": [0, 20], "note": "恐慌下跌，空仓或极轻仓等待企稳"},
    }
    m = MAP.get(state, MAP["oscillation"])
    return {"range": m["range"], "note": m["note"],
            "rules": ["单票仓位 ≤ 10%", "单一板块集中度 ≤ 30%", "账户回撤 > 5% 强制降半仓",
                      "情绪分 ≥ 85 触发追高禁令（只允许回踩低吸）"]}


def calc_l3_mainline(sectors: list, breadth: dict) -> dict:
    """主线与板块：主力净流入 TOP3 + 集中度信号"""
    if not sectors:
        return {"sectors": [], "mainline": "数据不可用", "resonance": []}
    top = sectors[:3]
    mainline = " → ".join(f"{s['name']}(+{s['net_yi']}亿)" for s in top)
    # 集中度：第一名净流入 vs 第二名的比值 > 1.5 视为高度集中（风险提示）
    conc = None
    if len(sectors) >= 2 and sectors[1]["net_yi"] > 0:
        ratio_c = sectors[0]["net_yi"] / max(sectors[1]["net_yi"], 0.01)
        conc = {"lead": sectors[0]["name"], "ratio": round(ratio_c, 2),
                "alert": ratio_c > 1.5}
    resonance = []
    if breadth.get("limit_up"):
        resonance.append("全市场涨停 %d 只，情绪有温度" % breadth["limit_up"])
    if breadth.get("main_net_yi", 0) > 0:
        resonance.append("全市场主力净流入 %+.1f 亿，资金面偏多" % breadth["main_net_yi"])
    if conc and conc["alert"]:
        resonance.append(f"⚠ 资金高度集中于 {conc['lead']}，追高风险上升")
    return {"sectors": sectors, "mainline": mainline, "resonance": resonance, "conc": conc}


def calc_l4_candidates(breadth: dict) -> dict:
    """标的执行：主力净流入 TOP 过滤四道关：①非ST ②非高位(zdf<8) ③净流入>1亿 ④成交额>5亿"""
    stocks = breadth.get("stocks") or []
    cands = []
    for s in sorted(stocks, key=lambda x: x["zljlr"], reverse=True):
        if len(cands) >= 10:
            break
        name = s["name"]
        if "ST" in name.upper():
            continue
        if s["zdf"] >= 8.0:          # 已大幅上涨，追高风险
            continue
        if s["zljlr"] < 1.0:         # 主力净流入 < 1 亿
            continue
        if s["turnover_yi"] < 5.0:   # 成交额 < 5 亿，流动性不足
            continue
        cands.append({**s, "type": "低吸候选" if s["zdf"] <= 3 else "中继观察"})
    return {"candidates": cands,
            "filters": "四道关：①非ST ②当日涨幅<8%(不追高) ③主力净流入>1亿 ④成交额>5亿",
            "trade_note": "入选仅作观察池：回踩MA5企稳分批(2批)，破入场-5%或MA20止损，事件利空即止"}


def calc_l5_risk(idx: list, breadth: dict, sent: dict, l3: dict) -> list:
    """风险雷达（固定 4 信号）→ [{level, type, msg}]"""
    alerts = []
    score = sent["score"]
    ratio = breadth.get("ratio") or 0
    lu = breadth.get("limit_up") or 0
    main_net = breadth.get("main_net_yi") or 0
    avg_idx = 0.0
    if idx:
        avg_idx = sum(i["chg_pct"] for i in idx) / len(idx)
    # R1 情绪过热
    if score >= 85 or lu >= 120 or ratio >= 4.0:
        alerts.append({"level": "red", "type": "情绪过热",
                       "msg": f"情绪分 {score} / 涨停 {lu} 只 / 涨跌比 {ratio}，短线过热，禁止追高"})
    # R2 资金背离：指数涨但全市场主力净流出
    if avg_idx > 0.5 and main_net < 0:
        alerts.append({"level": "red", "type": "资金背离",
                       "msg": f"指数均值 +{avg_idx:.1f}% 但全市场主力净流出 {main_net:.0f} 亿，反弹持续性存疑"})
    # R3 板块集中度
    conc = (l3 or {}).get("conc") or {}
    if conc and conc.get("alert"):
        alerts.append({"level": "yellow", "type": "板块集中",
                       "msg": f"资金高度集中于 {conc['lead']}（第一/第二板块净流入比 {conc['ratio']}），拥挤度风险"})
    # R4 涨跌比极端
    if ratio >= 3.5:
        alerts.append({"level": "yellow", "type": "普涨过热",
                       "msg": f"涨跌比 {ratio} 接近极端，次日分歧概率上升，留意兑现"})
    if not alerts:
        alerts.append({"level": "green", "type": "正常",
                       "msg": "未触发预警信号，按状态机规则执行即可"})
    return alerts


# ───────────────────────── 3. 主流程 ─────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="realtime/realtime.json")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="强制抓取并计算（用于测试/盘后预览，跳过盘中时段判断）")
    args = ap.parse_args()

    now = datetime.now()
    status = market_status(now)

    print(f"⏱ {now.strftime('%Y-%m-%d %H:%M:%S')} 状态={status}")
    if not args.force and status != "trading":
        # 非盘中时段（未开盘/午休/收盘/非交易日）：不刷新、不写文件，
        # 保留上一次盘中数据（页面显示"最后更新"时间），避免无效提交。
        print(f"  当前为 {status}，不执行盘中刷新（保留上次数据）。")
        return

    print("  [1/4] 拉取指数行情 ...")
    idx = fetch_indexes()
    print(f"        {len(idx)} 只指数")
    print("  [2/4] 拉取全市场统计（分页 4595 只）...")
    breadth = fetch_market_breadth()
    print(f"        涨{breadth.get('up')}/跌{breadth.get('down')}/平{breadth.get('flat')} "
          f"涨停{breadth.get('limit_up')} 主力{breadth.get('main_net_yi')}亿")
    print("  [3/4] 拉取板块资金流 ...")
    sectors = fetch_sector_flow()
    print(f"        {len(sectors)} 个行业板块")
    print("  [4/4] 拉取 ETF 资金流 ...")
    etf = fetch_etf_flow()
    print(f"        {len(etf)} 只宽基 ETF")

    sent = calc_l1_sentiment(idx, breadth)
    l1 = calc_l1_state(sent, breadth)
    l2 = calc_l2_position(l1["state"])
    l3 = calc_l3_mainline(sectors, breadth)
    l4 = calc_l4_candidates(breadth)
    l5 = calc_l5_risk(idx, breadth, sent, l3)

    payload = {
        "meta": {"updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                 "data_date": now.strftime("%Y-%m-%d"),
                 "market_status": status, "algorithm": ALGO_VERSION,
                 "next_hint": "每 30 分钟自动刷新（交易日 9:30-15:00，GitHub Actions 驱动）"},
        "L0": {"indexes": idx, "breadth": {k: v for k, v in breadth.items() if k != "stocks"}},
        "L1": {"sentiment": sent, "state": l1},
        "L2": l2,
        "L3": l3,
        "L4": l4,
        "L5": {"alerts": l5},
        "ETF": {"flows": etf},
    }
    if args.debug:
        payload["_raw_count"] = len(breadth.get("stocks") or [])

    # --out 可能为根目录文件名（如 realtime.json，dirname 为 ''），需容错；
    # 此前 os.makedirs('') 抛 FileNotFoundError，导致盘中 workflow run 必然失败
    # （realtime.json 自 08-17 23:10 起从未被更新过）。
    _out_dir = os.path.dirname(args.out)
    if _out_dir:
        os.makedirs(_out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n✅ 已写入 {args.out}（情绪分 {sent['score']} / 状态 {l1['label']} / 仓位 {l2['range']}）")


if __name__ == "__main__":
    main()
