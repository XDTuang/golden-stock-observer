#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""观测股每日滚动推演（名单保持，推演自动刷新）

名单源: output/obs_deduce_latest.json（本机 agent 更新时刷新名单；否则沿用上次名单）
数据:   腾讯 ifzq 日 K（最近 12 个交易日）
推演:   技术面规则（MA 排列/偏离度/5日动量/量比）+ 大盘环境修正（上证当日涨跌）+ 隔夜美股环境
输出:   覆盖 output/obs_deduce_latest.json（date=今天，items 含最新 trend/open_label）—— 前端 1.3 板块即滚动

用法: python3 derive_obs.py            # 每日盘后运行（已接入 update_data.sh Step 3.9 之后）
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path("/Users/samt/golden_stock_observer")
SRC = BASE / "output" / "obs_deduce_latest.json"

K_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,12"


def fetch_kline(code):
    """返回 [(date, open, close, high, low, vol), ...] 升序（akshare：A股 zh_a_daily / 港股 hk_daily）"""
    import akshare as ak
    import datetime as _dt
    end = _dt.date.today().isoformat()
    start = (_dt.date.today() - _dt.timedelta(days=25)).isoformat()
    try:
        if code.lower().startswith(("sh", "sz", "bj")):
            df = ak.stock_zh_a_daily(symbol=code, start_date=start, end_date=end)
        elif code.lower().startswith("hk"):
            sym = code[2:]                     # 保留前导零：00189/02655/06651
            df = ak.stock_hk_daily(symbol=sym, adjust="")
        else:
            return []
    except Exception:
        return []
    if df is None or len(df) < 6:
        return []
    rows = []
    for _, r in df.iterrows():
        try:
            rows.append((str(r["date"])[:10], float(r["open"]), float(r["close"]),
                         float(r["high"]), float(r["low"]),
                         float(r.get("volume", 0) or 0)))
        except Exception:
            pass
    rows.sort(key=lambda r: r[0])
    return rows


def _sector_chg(sec_name, smap, cache):
    """板块名 → 当日平均涨跌 %（腾讯批量拉成分股行情计算；缓存结果）。

    2026-08-28 v3 新增：东财板块接口被代理屏蔽、同花顺板块命名与
    gate_sectors(东财)不一致，故用腾讯 qt.gtimg.cn 批量拉成分股算均值。
    成分股取前 40 只（够代表板块方向），失败返回 0.0。
    """
    if not sec_name or sec_name in cache:
        return cache.get(sec_name, 0.0)
    info = smap.get(sec_name) or {}
    cons = (info.get("cons") or [])[:40]
    codes = [p for _, p in cons]
    chgs = []
    for i in range(0, len(codes), 50):
        chunk = codes[i:i + 50]
        try:
            url = "http://qt.gtimg.cn/q=" + ",".join(chunk)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=12).read().decode("gbk", "ignore")
            for line in raw.strip().split(";"):
                if '="' not in line:
                    continue
                v = line.split('"')[1].split("~")
                if len(v) > 32:
                    try:
                        chgs.append(float(v[32]))
                    except ValueError:
                        pass
        except Exception:
            continue
        time.sleep(0.1)
    c = round(sum(chgs) / len(chgs), 2) if chgs else 0.0
    cache[sec_name] = c
    return c


def deduce(it, rows, sh_chg, us_chg, sector_chg=0.0):
    """技术面规则推演（v2 简化版：去过度中间态 + 大盘门槛）"""
    if len(rows) < 6:
        it["trend"] = "数据不足"; it["open_label"] = "数据不足"; return it
    closes = [r[2] for r in rows]
    vols = [r[5] for r in rows]
    close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else close
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / min(10, len(closes))
    high10 = max(r[3] for r in rows[-10:])
    low10 = min(r[4] for r in rows[-10:])
    chg_last = (close / prev_close - 1) * 100 if prev_close else 0
    dev_ma5 = (close / ma5 - 1) * 100 if ma5 else 0
    chg5 = (close / closes[-6] - 1) * 100 if len(closes) > 5 and closes[-6] else 0
    vol_ratio = round(vols[-1] / (sum(vols[-6:-1]) / 5), 2) if sum(vols[-6:-1]) else 1.0

    # 形态
    if ma5 > ma10 and close > ma5:
        pattern = "多头排列"
    elif ma5 < ma10 and close < ma5:
        pattern = "空头排列"
    else:
        pattern = "震荡纠缠"

    # 方向推演（技术面基础）
    if pattern == "多头排列":
        trend = "强势上涨" if vol_ratio >= 1.2 else "震荡上行"
    elif pattern == "空头排列":
        if dev_ma5 < -5 and chg5 < -8:
            trend = "弱势下跌"
        else:
            trend = "震荡偏弱"
    else:
        trend = "震荡"

    # ── v3 环境加权修正（2026-08-28 用户调优指令）────────────────────
    # 因子权重: 技术面 70% / 大盘(上证当日) 10% / 板块(东财/同花顺行业当日) 20%
    # 背景: v2 只有"降级"修正(普涨日把弱势降为震荡)，普涨日 69% 股票被判"震荡"，
    #       回测(8-26+8-27)方向准确率仅 23.4%（"震荡"类 11.4%）。
    # 作用: 双向修正 —— 普涨/板块强 → 震荡/偏弱升级；普跌/板块弱 → 强势/上行降级
    def _env_score(c):
        if c is None:
            return 0.0
        if c > 1.0:
            return 1.0
        if c > 0.3:
            return 0.5
        if c < -1.0:
            return -1.0
        if c < -0.3:
            return -0.5
        return 0.0

    _BASE = {"强势上涨": 2, "震荡上行": 1, "震荡": 0, "震荡偏弱": -1, "弱势下跌": -2}
    base = _BASE.get(trend, 0)
    score = 0.7 * base + 0.1 * _env_score(sh_chg) + 0.2 * _env_score(sector_chg)
    if score >= 0.85:
        trend = "强势上涨"
    elif score >= 0.25:
        trend = "震荡上行"
    elif score >= -0.25:
        trend = "震荡"
    elif score >= -0.85:
        trend = "震荡偏弱"
    else:
        trend = "弱势下跌"

    # 开盘方式（基于隔夜美股 + 昨日涨跌）
    if us_chg is not None and abs(us_chg) > 0.8:
        us_bias = "up" if us_chg > 0 else "down"
    else:
        us_bias = None
    if chg_last >= 3:
        open_label = "高开延续"
    elif chg_last >= 1:
        open_label = "高开偏强" if us_bias != "down" else "平开偏强"
    elif chg_last <= -3:
        open_label = "低开破位风险"
    elif chg_last <= -1:
        open_label = "低开偏弱" if us_bias != "up" else "平开偏弱"
    else:
        open_label = "平开震荡"

    it.update({
        "close": round(close, 2), "chg_last": round(chg_last, 2),
        "ma5": round(ma5, 2), "ma10": round(ma10, 2),
        "high10": round(high10, 2), "low10": round(low10, 2),
        "pattern": pattern, "dev_ma5": round(dev_ma5, 2),
        "chg5": round(chg5, 2), "vol_ratio": vol_ratio,
        "trend": trend, "open_label": open_label,
        "derive": "auto" if "derive" not in it else it["derive"],
    })
    return it


def main():
    if not SRC.exists():
        print("无 obs_deduce_latest.json（先跑 sync_obs_deduce.py 建立名单）")
        sys.exit(1)
    data = json.loads(SRC.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        print("名单为空")
        sys.exit(1)

    # 环境：上证当日涨跌（market.json）+ 隔夜美股（us_kline 道指）
    sh_chg = us_chg = None
    try:
        mkt = json.loads((BASE / "data" / "daily_review" / "market.json").read_text(encoding="utf-8"))
        q = mkt.get("quotes", {}).get("a_sh", {})
        if q and "error" not in q:
            sh_chg = float(q["chg_pct"])
        uk = mkt.get("us_kline", {}).get("us_dji", {})
        if uk.get("prev"):
            us_chg = uk["prev"]["chg_pct"]
    except Exception:
        pass

    # ── 板块因子数据（v3 final，2026-08-28）────────────────────
    # 涨跌: 新浪行业 spot（一次请求，49 板块）
    # 映射: 新浪成分缓存 code_sector_sina.json（优先）→ gate_sectors 兜底
    spot_chg = {}
    try:
        import akshare as ak
        _df = ak.stock_sector_spot(indicator="新浪行业")
        spot_chg = {str(r["板块"]): float(r["涨跌幅"]) for _, r in _df.iterrows()}
    except Exception:
        pass
    sina_map = {}
    _p = BASE / "output" / "code_sector_sina.json"
    if _p.exists():
        try:
            sina_map = json.loads(_p.read_text(encoding="utf-8"))
        except Exception:
            pass
    sector_map, smap = {}, {}
    try:
        gs = json.loads((BASE / "output" / "gate_sectors.json").read_text(encoding="utf-8"))
        sector_map = gs.get("code_sector", {})
        smap = gs.get("sector_map", {})
    except Exception:
        pass
    # 反向索引：prefcode(如 sh600176) → 板块名，覆盖 code_sector 未收录的观测股
    code_rev = {}
    for _sec, _info in smap.items():
        for _pair in (_info.get("cons") or []):
            if len(_pair) > 1:
                code_rev[_pair[1]] = _sec
    _scc = {}

    today = __import__("datetime").date.today().isoformat()
    ok = 0
    for it in items:
        code = it.get("code", "")
        if not code:
            continue
        try:
            rows = fetch_kline(code)
            if not rows:
                print(f"  ⚠️ {it.get('name')}: K线获取失败")
                continue
            # 板块因子：板块名（新浪映射优先 → gate 兜底）→ 板块涨跌（spot 优先 → 腾讯聚合兜底）
            code_key = code if code.startswith(("sh", "sz", "hk", "bj")) else ("sh" + code if code[0] == "6" else "sz" + code)
            sec_name = sina_map.get(code_key) or sector_map.get(code_key) or code_rev.get(code_key, "")
            if sec_name in spot_chg:
                sec_chg = spot_chg[sec_name]
            elif sec_name:
                sec_chg = _sector_chg(sec_name, smap, _scc)
            else:
                sec_chg = 0.0
            deduce(it, rows, sh_chg, us_chg, sec_chg)
            ok += 1
            print(f"  ✓ {it['name']}: {it['trend']} (板块 {sec_chg:+.2f}%)")
        except Exception as e:
            print(f"  ⚠️ {it.get('name')}: {type(e).__name__} {str(e)[:60]}")
        time.sleep(0.3)  # 低频

    data["date"] = today
    data["derive_engine"] = "derive_obs.py v3 (技术70% + 大盘10% + 板块20%)"
    data["env"] = {"sh_chg": sh_chg, "us_dji_chg": us_chg}
    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (BASE / "deploy" / "output" / "obs_deduce_latest.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    # 归档到 history（供 backtest_daily_review.py --auto 回测：T 日推演 vs T+1 实际）
    try:
        bk_dir = BASE / "data" / "daily_review_history" / today
        bk_dir.mkdir(parents=True, exist_ok=True)
        (bk_dir / f"obs_deduce_auto_{today}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as _e:
        print(f"  ⚠️ 归档失败（不影响推演）: {_e}")
    print(f"✅ 滚动推演完成：{ok}/{len(items)} 只（date={today}，名单沿用，已归档供回测）")


if __name__ == "__main__":
    main()
