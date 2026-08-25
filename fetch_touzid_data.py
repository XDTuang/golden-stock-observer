#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""touzid 三合一数据抓取：市场温度计 + 估值分位 + 机构/股东户数

数据源（全部免费公开，无 key）：
  块① 市场温度计:
    - 乐咕乐股 stock_a_all_pb     : 全A PB 中位 + 近10年分位（含历史序列）
    - 乐咕乐股 stock_market_pe_lg : 上证/深证/创业板 全市场 PE（含历史序列）
    - 乐咕乐股 stock_a_ttm_lyr    : 全A 等权 PE TTM（格雷厄姆指数分子）
    - 新浪   stock_zh_a_spot      : 全市场快照（破净率 / 总市值 / 中位PB）— 失败则跳过
    - 中美国债 bond_zh_us_rate    : 10Y 国债收益率（格雷厄姆指数分母 / 股债收益差）
    - 国家统计局 macro_china_gdp  : 季度 GDP（巴菲特指数分母 = 最近12个月 TTM）
  块② 估值分位:
    - 百度股市通 stock_zh_valuation_baidu : 个股历史 PE/PB（近五年）→ 分位 + PE-Band
  块③ 机构/股东户数:
    - 东财股东户数 stock_zh_a_gdhs : 全市场股东户数（报告期对比 → 增减比例）

输出（原子写，根目录 output/ + deploy/output/ 双写，与现有产物一致）:
  output/market_thermometer.json  市场温度计（快照 + 近5年历史序列）
  output/valuation_band.json      命中股估值分位 + PE-Band 通道
  output/institutional_flow.json  命中股/池内 股东户数趋势

用法:
  python fetch_touzid_data.py              # 全量
  python fetch_touzid_data.py --no-spot    # 跳过新浪全市场快照（破净率/总市值，较慢）
"""
import json
import os
import sys
import time
import tempfile
import warnings
import datetime as _dt

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
DEPLOY_OUT = os.path.join(BASE, "deploy", "output")
os.makedirs(OUT, exist_ok=True)
os.makedirs(DEPLOY_OUT, exist_ok=True)

SKIP_SPOT = "--no-spot" in sys.argv
THERMO_ONLY = "--thermo-only" in sys.argv
VIX_ONLY = "--vix-only" in sys.argv
INST_ONLY = "--inst-only" in sys.argv
NO_INST = "--no-inst" in sys.argv

def _atomic(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=".tz_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, ensure_ascii=False, default=str, indent=1)
    os.replace(tmp, path)

def _clean(o):
    """递归把 float('nan')/inf 转 None，保证合法 JSON"""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    return o

def _write_both(name, obj):
    for d in (OUT, DEPLOY_OUT):
        p = os.path.join(d, name)
        _atomic(p, obj)
    print(f"  ✅ {name} ({os.path.getsize(os.path.join(OUT, name))/1024:.1f} KB)")

def _safe(fn, default=None, retries=2):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            if i == retries - 1:
                print(f"  ⚠️  {getattr(fn, '__name__', '') or fn} 失败: {type(e).__name__} {str(e)[:100]}")
                return default
            time.sleep(1.5)

# ═══════════════════════════════ 块① 市场温度计 ═══════════════════════════════
def build_thermometer():
    print("\n📊 块① 市场温度计")
    import akshare as ak

    # 1. 全A PB 分布（乐咕，含近10年分位历史）
    pb_df = _safe(ak.stock_a_all_pb)
    # 2. 全A 等权/中位 PE TTM（乐咕，含近10年分位历史）— 温度计 PE 主源
    ttm_df = _safe(ak.stock_a_ttm_lyr)
    # 3. 10Y 国债（格雷厄姆分母 / ERP）
    bond_df = _safe(ak.bond_zh_us_rate)
    # 4. GDP TTM
    gdp_df = _safe(ak.macro_china_gdp)
    # 6. 破净率（乐咕手动接口，2005 至今历史；akshare 包装已过时）
    import requests as _req
    below_df = None
    try:
        _r = _req.get("https://legulegu.com/stockdata/below-net-asset-statistics-data",
                      params={"marketId": "1", "token": "325843825a2745a2a8f9b9e3355cb864"},
                      headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        _j = _r.json()
        below_df = [{"date": x["date"], "below": x["belowNetAsset"], "total": x["totalCompany"],
                     "close": x.get("close")} for x in _j]
    except Exception as e:
        print(f"  ⚠️  乐咕破净接口失败: {e}")
    # 7. 全A 总市值 / 中位PE·PB（腾讯 gtimg 批量，4595只 ≈ 77 批）
    mv_spot = None if SKIP_SPOT else _spot_from_gtimg()

    today = _dt.date.today().isoformat()

    # ── 当前快照 ──
    snap = {"date": today, "graham": None, "buffett": None, "below_net_ratio": None,
            "pe_median": None, "pb_median": None, "pe_pct_10y": None, "pb_pct_10y": None,
            "erp": None, "bond_10y": None, "total_mv_yi": None, "gdp_ttm_yi": None}

    # PE 中位 + 近10年分位（乐咕全A中位PE TTM）
    if ttm_df is not None and len(ttm_df):
        r = ttm_df.iloc[-1]
        try:
            snap["pe_median"] = round(float(r.get("middlePETTM", 0)), 2)
        except Exception:
            pass
        v = r.get("quantileInRecent10YearsMiddlePeTtm")
        if v is not None and v == v:
            try:
                snap["pe_pct_10y"] = round(float(v) * 100, 1)
            except Exception:
                pass

    # PB 中位 + 近10年分位（乐咕 stock_a_all_pb 直接给）
    if pb_df is not None and len(pb_df):
        r = pb_df.iloc[-1]
        snap["pb_median"] = round(float(r.get("middlePB", 0)), 2)
        for k in ("quantileInRecent10YearsMiddlePB", "quantileInAllHistoryMiddlePB"):
            v = r.get(k)
            if v is not None and v == v:
                try:
                    snap["pb_pct_10y"] = round(float(v) * 100, 1)
                    break
                except Exception:
                    pass

    # 10Y 国债
    if bond_df is not None and len(bond_df):
        row = bond_df.dropna(subset=["中国国债收益率10年"]).iloc[-1]
        snap["bond_10y"] = round(float(row["中国国债收益率10年"]), 2)

    # 格雷厄姆指数 = (1/全A PE) / 10Y国债
    if snap["pe_median"] and snap["bond_10y"] and snap["pe_median"] > 0 and snap["bond_10y"] > 0:
        snap["graham"] = round((1 / snap["pe_median"] * 100) / snap["bond_10y"], 2)

    # 股债收益差 ERP = 1/PE - 10Y国债
    if snap["pe_median"] and snap["bond_10y"] and snap["pe_median"] > 0:
        snap["erp"] = round(1 / snap["pe_median"] * 100 - snap["bond_10y"], 2)

    # GDP TTM（最新累计 + 上年Q4；接口从新到旧排列）
    if gdp_df is not None and len(gdp_df):
        col = "国内生产总值-绝对值"
        latest = gdp_df.dropna(subset=[col]).iloc[0]
        y = int(str(latest["季度"])[:4])
        try:
            y_full = float(gdp_df[gdp_df["季度"] == f"{y-1}年第1-4季度"][col].iloc[0])
            y_3q = float(gdp_df[gdp_df["季度"] == f"{y-1}年第1-3季度"][col].iloc[0])
            prev_q4 = y_full - y_3q
            snap["gdp_ttm_yi"] = round(float(latest[col]) + prev_q4, 0)
        except Exception as e:
            print(f"  ⚠️  GDP TTM 计算失败(退化用最新累计): {e}")
            snap["gdp_ttm_yi"] = round(float(latest[col]), 0)

    # 破净率（乐咕：当天 + 历史）
    if below_df:
        snap["below_net_ratio"] = round(below_df[-1]["below"] / below_df[-1]["total"] * 100, 2)

    # 全A 总市值（gtimg，亿元）；PE/PB 中位以乐咕为准，不覆盖
    if mv_spot:
        snap["total_mv_yi"] = round(mv_spot.get("total_mv_yi"), 0) if mv_spot.get("total_mv_yi") else None

    if snap["total_mv_yi"] and snap["gdp_ttm_yi"] and snap["gdp_ttm_yi"] > 0:
        snap["buffett"] = round(snap["total_mv_yi"] / snap["gdp_ttm_yi"], 3)

    # ── 历史序列（近5年，日频；乐咕 PE/PB/国债/破净率 有历史，巴菲特指数待积累）──
    hist = []
    if ttm_df is not None and len(ttm_df) and pb_df is not None and len(pb_df):
        pb_dates = {str(d): r for d, r in zip(pb_df["date"], pb_df.to_dict("records"))}
        below_map = {}
        if below_df:
            for x in below_df:
                below_map[x["date"]] = round(x["below"] / x["total"] * 100, 2) if x["total"] else None
        seen = set()
        for _, row in ttm_df.iterrows():
            d = str(row["date"])[:10]
            if d in seen or d < "2021-08-01":
                continue
            seen.add(d)
            e = {"date": d, "pe": None, "pb": None, "pe_pct": None, "pb_pct": None,
                 "bond": None, "graham": None, "below_net_ratio": below_map.get(d)}
            try:
                v = float(row.get("middlePETTM"))
                e["pe"] = round(v, 2) if v == v else None
            except Exception:
                pass
            v = row.get("quantileInRecent10YearsMiddlePeTtm")
            if v is not None and v == v:
                try:
                    e["pe_pct"] = round(float(v) * 100, 1)
                except Exception:
                    pass
            pbrow = pb_dates.get(d)
            if pbrow:
                try:
                    v = float(pbrow.get("middlePB", 0))
                    e["pb"] = round(v, 2) if v == v else None
                except Exception:
                    pass
                v = pbrow.get("quantileInRecent10YearsMiddlePB")
                if v is not None and v == v:
                    try:
                        e["pb_pct"] = round(float(v) * 100, 1)
                    except Exception:
                        pass
            if bond_df is not None and len(bond_df):
                bd = bond_df[bond_df["日期"].astype(str).str[:10] == d]
                if len(bd):
                    try:
                        e["bond"] = round(float(bd.iloc[-1]["中国国债收益率10年"]), 2)
                    except Exception:
                        pass
            if e["pe"] and e["bond"] and e["bond"] > 0:
                e["graham"] = round((1 / e["pe"] * 100) / e["bond"], 2)
            hist.append(e)
        # 补充分位曲线：乐咕 quantile 列仅最新行有值，改用近5年序列自算分位填充全部点
        # （快照仍用乐咕精确10年分位；曲线用5年滚动近似，前端已标注"近5年"）
        try:
            import numpy as _np
            pe_vals = [x["pe"] for x in hist if x["pe"] is not None]
            pb_vals = [x["pb"] for x in hist if x["pb"] is not None]
            if pe_vals:
                pe_arr = _np.array(sorted(pe_vals), dtype=float)
                for x in hist:
                    if x["pe"] is not None:
                        x["pe_pct"] = round(float(_np.searchsorted(pe_arr, x["pe"], side="right")) / len(pe_arr) * 100, 1)
            if pb_vals:
                pb_arr = _np.array(sorted(pb_vals), dtype=float)
                for x in hist:
                    if x["pb"] is not None:
                        x["pb_pct"] = round(float(_np.searchsorted(pb_arr, x["pb"], side="right")) / len(pb_arr) * 100, 1)
        except Exception as _e:
            print(f"  ⚠️  分位曲线补算失败(降级，仅快照有分位): {_e}")
        # 每交易日保留（上限 ~1250 行 ≈ 5年），超出按日期抽样
        if len(hist) > 1250:
            step = len(hist) // 1250
            hist = hist[::step]
            if hist[-1]["date"] != today:
                hist.append(hist[-1])
        # 乐咕 quantile 列时有时无（8/20 起 NaN、最新行给 0.0 异常）→ 用自算分位回填快照
        try:
            if snap.get("pe_pct_10y") in (None, 0):
                last = next((x for x in reversed(hist) if x.get("pe_pct") is not None), None)
                if last:
                    snap["pe_pct_10y"] = last["pe_pct"]
            if snap.get("pb_pct_10y") in (None, 0):
                last = next((x for x in reversed(hist) if x.get("pb_pct") is not None), None)
                if last:
                    snap["pb_pct_10y"] = last["pb_pct"]
        except Exception:
            pass

    therm = {"date": today, "snapshot": snap, "history": hist,
             "sources": {"pe_pb": "乐咕乐股", "spot": "腾讯gtimg", "bond": "中美国债",
                          "gdp": "国家统计局", "below_net": "乐咕乐股"}}
    _write_both("market_thermometer.json", therm)
    print(f"  快照: 格雷厄姆={snap['graham']} 巴菲特={snap['buffett']} 破净率={snap['below_net_ratio']}% "
          f"PE中位={snap['pe_median']} PE分位10y={snap['pe_pct_10y']}% PB分位10y={snap['pb_pct_10y']}% "
          f"国债10Y={snap['bond_10y']}% ERP={snap['erp']}%")

# ═══════════════════════════════ 块② 估值分位 ═══════════════════════════════
def build_valuation_band():
    print("\n📊 块② 估值分位（命中股 PE/PB 分位 + PE-Band）")
    import akshare as ak

    # 命中股：金钻 + 信号（四喜/三线/双线）
    targets = {}
    try:
        gd = json.load(open(os.path.join(DEPLOY_OUT, "golden_diamond.json"), encoding="utf-8"))
        for s in gd.get("stocks", []):
            targets[s["code"]] = {"name": s["name"], "tag": "金钻:" + s.get("primary", "")}
    except Exception as e:
        print(f"  ⚠️  金钻数据读取失败: {e}")
    try:
        d = json.load(open(os.path.join(BASE, "signals.json"), encoding="utf-8"))
        for s in d.get("observation_pool", []):
            sc = s.get("score") or {}
            sigs = sc.get("signals") or []
            if sigs:
                targets[s["code"]] = {"name": s["name"], "tag": "信号:" + "|".join(sigs[:2])}
    except Exception as e:
        print(f"  ⚠️  信号数据读取失败: {e}")

    print(f"  命中股: {len(targets)} 只")
    items = []
    for i, (code, meta) in enumerate(targets.items()):
        code6 = code[-6:] if code and code[0] in "shsz" else code
        it = {"code": code, "name": meta["name"], "tag": meta["tag"],
              "pe": None, "pb": None, "pe_pct_5y": None, "pb_pct_5y": None,
              "band_low": None, "band_mid": None, "band_high": None}
        # 百度估值：历史 PE/PB（近五年）
        for ind, key in (("市盈率(TTM)", "pe"), ("市净率", "pb")):
            df = _safe(lambda ind=ind: ak.stock_zh_valuation_baidu(symbol=code6, indicator=ind, period="近五年"), retries=1)
            if df is not None and len(df):
                col = [c for c in df.columns if "value" in c.lower() or "数值" in c]
                col = col or list(df.columns)
                try:
                    series = df[col[0]].astype(float).dropna()
                    if len(series):
                        cur = float(series.iloc[-1])
                        it[key] = round(cur, 2)
                        it[key + "_pct_5y"] = round(float((series < cur).sum()) / len(series) * 100, 1)
                except Exception:
                    pass
        # PE-Band 通道（近5年 PE 低/中/高 × 当前每股收益近似）
        if it["pe"] and it["pe_pct_5y"] is not None:
            df = _safe(lambda: ak.stock_zh_valuation_baidu(symbol=code6, indicator="市盈率(TTM)", period="近五年"), retries=1)
            if df is not None and len(df):
                col = [c for c in df.columns if "value" in c.lower() or "数值" in c]
                col = col or list(df.columns)
                try:
                    series = df[col[0]].astype(float).dropna()
                    if len(series) >= 20:
                        it["band_low"] = round(float(series.quantile(0.2)), 2)
                        it["band_mid"] = round(float(series.median()), 2)
                        it["band_high"] = round(float(series.quantile(0.8)), 2)
                except Exception:
                    pass
        items.append(it)
        if (i + 1) % 15 == 0:
            print(f"    ...{i+1}/{len(targets)}")
        time.sleep(0.4)

    obj = {"date": _dt.date.today().isoformat(), "count": len(items), "items": items}
    _write_both("valuation_band.json", obj)
    print(f"  完成，{len([i for i in items if i['pe_pct_5y'] is not None])} 只有 PE 分位")

# ═══════════════════════════════ 全球波动率面板（VIX / 美股三指数 / A股QVIX） ═══════════════════════════════
def build_vix():
    print("\n📈 块④ 全球波动率面板（VIX / 美股三指数 / A股 QVIX）")
    import akshare as ak
    import requests as _req

    today = _dt.date.today().isoformat()
    obj = {"date": today, "cboe_vix": None, "us": [], "a_share": [], "vix_history": []}

    # 1. CBOE 官方 VIX 历史 CSV（免费，权威）
    try:
        r = _req.get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
                     timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        lines = [ln for ln in r.text.strip().splitlines() if ln]
        rows = []
        for ln in lines[1:]:
            p = ln.split(",")
            if len(p) >= 5:
                try:
                    d = _dt.datetime.strptime(p[0].strip(), "%m/%d/%Y").date()
                    rows.append({"date": d.isoformat(), "close": round(float(p[4]), 2)})
                except Exception:
                    pass
        rows.sort(key=lambda x: x["date"])
        if rows:
            last = rows[-1]
            prev = rows[-2] if len(rows) > 1 else None
            obj["cboe_vix"] = {"value": last["close"], "prev": prev["close"] if prev else None,
                               "date": last["date"],
                               "chg": round(last["close"] - prev["close"], 2) if prev else None,
                               "chg_pct": round((last["close"] / prev["close"] - 1) * 100, 2) if prev and prev["close"] else None}
            obj["vix_history"] = rows[-260:]  # 近1年
            print(f"  CBOE VIX: {last['close']} ({last['date']}) 历史 {len(rows)} 条")
    except Exception as e:
        print(f"  ⚠️  CBOE VIX 失败: {e}")

    # 2. 美股三指数（新浪实时，需 Referer）
    try:
        r = _req.get("https://hq.sinajs.cn/list=gb_dji,gb_ixic,gb_inx",
                     headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}, timeout=12)
        r.encoding = "gbk"
        us_names = {"gb_dji": "道琼斯", "gb_ixic": "纳斯达克", "gb_inx": "标普500"}
        for ln in r.text.strip().splitlines():
            m = ln.split("=", 1)
            if len(m) < 2 or "hq_str_gb_" not in m[0]:
                continue
            code = m[0].replace("var hq_str_", "").replace("=", "").strip()
            body = m[1].strip().strip('"').split(",")
            if len(body) < 3 or not body[0]:
                continue
            try:
                val = float(body[1])
                chg_pct = float(body[2])
                obj["us"].append({"code": code, "name": us_names.get(code, body[0]),
                                  "value": round(val, 2), "chg_pct": round(chg_pct, 2)})
            except Exception:
                pass
        print(f"  美股三指数: {len(obj['us'])} 个")
    except Exception as e:
        print(f"  ⚠️  新浪美股失败: {e}")

    # 3. A股 QVIX（期权隐含波动率）+ 指数 20日年化波动率
    a_share_defs = [
        ("科创50", "sh000688", "index_option_kcb_qvix"),
        ("创业板指", "sz399006", "index_option_cyb_qvix"),
    ]
    for name, idx_code, qvix_fn in a_share_defs:
        it = {"name": name, "code": idx_code, "value": None, "qvix": None, "vol20": None}
        try:  # QVIX
            df = getattr(ak, qvix_fn)()
            if df is not None and len(df):
                it["qvix"] = round(float(df.iloc[-1]["close"]), 2)
        except Exception as e:
            print(f"  ⚠️  {name} QVIX 失败: {e}")
        try:  # 指数日线 → 20日年化波动率
            df = ak.stock_zh_index_daily(symbol=idx_code)
            if df is not None and len(df) > 25:
                close = df["close"].astype(float).tail(21)
                ret = close.pct_change().dropna()
                it["vol20"] = round(float(ret.std() * (252 ** 0.5) * 100), 2)
                it["value"] = round(float(close.iloc[-1]), 2)
        except Exception as e:
            print(f"  ⚠️  {name} 指数日线失败: {e}")
        obj["a_share"].append(it)
        print(f"  {name}: QVIX={it['qvix']} vol20={it['vol20']}% value={it['value']}")

    _write_both("vix_panel.json", obj)
    print(f"  ✅ vix_panel.json")


def build_institutional_flow():
    print("\n📊 块③ 股东户数趋势（全市场报告期对比）")
    import akshare as ak

    # 取最近两个报告期
    gdhs_all = {}
    for rep in ("20260331", "20251231"):
        df = _safe(lambda rep=rep: ak.stock_zh_a_gdhs(rep), retries=1)
        if df is not None and len(df):
            for _, r in df.iterrows():
                code = str(r.get("代码", "")).zfill(6)
                gdhs_all.setdefault(code, {})[rep] = {
                    "num": _num(r.get("股东户数-本次")), "prev": _num(r.get("股东户数-上次")),
                    "chg_pct": _num(r.get("股东户数-增减比例")), "mv": _num(r.get("总市值")),
                    "asof": r.get("股东户数统计截止日-本次")}
        time.sleep(1.0)

    # 命中股 + 池内 Top30
    targets = {}
    try:
        gd = json.load(open(os.path.join(DEPLOY_OUT, "golden_diamond.json"), encoding="utf-8"))
        for s in gd.get("stocks", []):
            targets[s["code"]] = {"name": s["name"], "tag": "金钻:" + s.get("primary", "")}
    except Exception:
        pass
    try:
        d = json.load(open(os.path.join(BASE, "signals.json"), encoding="utf-8"))
        for s in d.get("observation_pool", []):
            sc = s.get("score") or {}
            if sc.get("signals"):
                targets[s["code"]] = {"name": s["name"], "tag": "信号"}
    except Exception:
        pass

    items = []
    for code, meta in targets.items():
        code6 = code[-6:]
        g = gdhs_all.get(code6)
        if not g:
            continue
        latest = g.get("20260331") or {}
        prev = g.get("20251231") or {}
        items.append({
            "code": code, "name": meta["name"], "tag": meta["tag"],
            "holders_latest": latest.get("num"), "holders_prev": prev.get("num"),
            "holders_chg_pct": latest.get("chg_pct"),
            "asof": latest.get("asof"), "mv_yi": round(latest["mv"] / 1e8, 1) if latest.get("mv") else None,
        })
    items.sort(key=lambda x: (x["holders_chg_pct"] or 0))

    obj = {"date": _dt.date.today().isoformat(), "report": "2026-03-31 vs 2025-12-31",
           "count": len(items), "items": items}
    _write_both("institutional_flow.json", obj)
    print(f"  完成，{len(items)} 只命中股有户数数据")

def _num(v):
    try:
        f = float(v)
        return None if f != f else round(f, 2)
    except Exception:
        return None


def _spot_from_gtimg():
    """腾讯 gtimg 批量拉全A快照 → 总市值/中位PE/PB（60只/批 ≈ 77批，公开接口无key）"""
    import requests as _req
    try:
        codes = json.load(open(os.path.join(BASE, "data", "all_a_codes.json"), encoding="utf-8"))
    except Exception as e:
        print(f"  ⚠️  all_a_codes.json 读取失败: {e}")
        return None
    batch = [c["code"] for c in codes]
    total_mv = 0.0
    pes, pbs = [], []
    n = 0
    for i in range(0, len(batch), 60):
        chunk = batch[i:i + 60]
        try:
            r = _req.get("https://qt.gtimg.cn/q=" + ",".join(chunk), timeout=10)
            r.encoding = "gbk"
            for line in r.text.strip().split(";"):
                if "=" not in line:
                    continue
                body = line.split("=", 1)[1].strip().strip('"')
                f = body.split("~")
                if len(f) < 46:
                    continue
                try:
                    pe = float(f[39]) if f[39] else None
                    pb = float(f[43]) if f[43] else None
                    mv = float(f[44]) if f[44] else None
                    if pe and pe > 0:
                        pes.append(pe)
                    if pb and pb > 0:
                        pbs.append(pb)
                    if mv and mv > 0:
                        total_mv += mv
                        n += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"  ⚠️  gtimg 批次 {i//60+1} 失败: {e}")
        time.sleep(0.15)
    if not n:
        return None
    pes.sort()
    pbs.sort()
    return {"total_mv_yi": round(total_mv, 0),
            "pe_median": round(pes[len(pes) // 2], 2),
            "pb_median": round(pbs[len(pbs) // 2], 2),
            "n": n}

if __name__ == "__main__":
    print("═══ touzid 数据抓取 ═══")
    if SKIP_SPOT:
        print("(--no-spot 模式：跳过 gtimg 全市场市值扫描)")
    if VIX_ONLY:
        build_vix()
    elif INST_ONLY:
        build_institutional_flow()
    elif THERMO_ONLY:
        build_thermometer()
    else:
        # 默认（主站日更）：温度计 + 估值分位 + VIX；股东户数由周更 workflow 单独跑 --inst-only
        build_thermometer()
        build_valuation_band()
        build_vix()
    print("\n═══ 完成 ═══")
