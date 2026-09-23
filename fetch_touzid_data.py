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
import socket

# 全局 socket 超时（2026-09-15 增 · 防 hang）：akshare 底层走 urllib3，未显式传 timeout 时
# 使用 socket 全局默认值，而默认是 None（永不超时）—— 实测 build_valuation_band() 的百度估值接口
# （ak.stock_zh_valuation_baidu）会在中途某只股票上永久阻塞（363 只跑到 15 只后停滞 2 分钟无任何输出）。
socket.setdefaulttimeout(15)

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
LIST_BLOCKS = "--list-blocks" in sys.argv   # 只打印将要执行的块（供守卫做行为级测试）
VIX_SETTLE_HHMM = "16:15"            # VIX 每日结算时刻（美东）· 早于此视为盘中价


def _resolve_blocks():
    """返回本次要执行的块清单（唯一权威，供 main 与 --list-blocks 共用）。

    🔴 2026-09-23 修：原 `if VIX_ONLY: … elif THERMO_ONLY: …` 链式判断 ——
       同时传 `--thermo-only --vix-only` 时 **VIX 胜出、温度计整块不执行**，且不报错。
       而云端 `daily-update` 与本机盘前缺口补跑正是这条组合命令 →
       `market_thermometer.json` 在云端与盘前**永远补不上**：
       窗口缺口天天报「温度计滞后」、补跑天天"成功"、产物却停在上一交易日。
    """
    if not (THERMO_ONLY or VIX_ONLY or INST_ONLY):
        return ["thermometer", "valuation", "vix"]      # 默认（主站日更全量）
    out = []
    if THERMO_ONLY:
        out.append("thermometer")
    if VIX_ONLY:
        out.append("vix")
    if INST_ONLY:
        out.append("inst")
    return out


def _data_date_str():
    """数据日 = 按「当日 A 股收盘是否已过」判定所属交易日。

    2026-09-15 修（铁律 9/23 家族 · 生成日 ≠ 数据日）：
      ① 原为 datetime.date.today()（= 生成日）→ 盘前/盘中跑会把「上一交易日收盘口径」的
         dataset 标成当日（实测 valuation_band 停在 9/11 却始终自述最新）；
      ② 00:0x 的跨零点调度会把 T 日数据写成 T+1（与 fetch_sector_flow / national_team_etf 同族 bug）。
    判据与 fetch_sector_flow.py::_data_date / fetch_national_team_etf.py 保持一致。
    """
    try:
        from market_calendar import is_trading_day, last_trading_day
        _now = _dt.datetime.now()
        _d = _now.date()
        if is_trading_day(_d) and _now.hour >= 15:
            return str(_d)
        return str(last_trading_day(_d - _dt.timedelta(days=1)))
    except Exception:
        return _dt.date.today().isoformat()

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

    # ── 历史序列（近5年；口径分指标：PE/PB/国债 = 月频（乐咕月序列 + 当月滚动点），
    #    破净率 = 日频（乐咕 REST 日序列，2026-09-23 起并入，见下方补充段）；巴菲特指数待积累）──
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
        # ── 破净率日频补充（2026-09-23）──
        # 乐咕破净率 REST 是日序列（2005 起），而 PE/PB 源为月序列 → 原 history 只有 ~62 个月频点，
        # 前端「破净率%」曲线被稀释成月频。此处并入日频破净率点：
        # ① 仅并入 ≤ 现有末条日期的点 → data_day（=hist[-1].date）与日期自洽契约保持不变；
        # ② 已存在的日期不重复；③ 只带 date/below_net_ratio 两键 —— 前端 renderThermoChart 按指标
        #    过滤 null（hist.filter(h => h[metric] != null)），缺键行对其他指标天然不可见，安全。
        if below_map and hist:
            _have = {str(x.get("date"))[:10] for x in hist}
            _last_d = str(hist[-1].get("date"))[:10]
            _extra = []
            for _d in sorted(below_map.keys()):
                _dd = str(_d)[:10]
                if _dd in _have or _dd < "2021-08-01" or _dd > _last_d:
                    continue
                if below_map.get(_d) is None:
                    continue
                _extra.append({"date": _dd, "below_net_ratio": below_map[_d]})
            if _extra:
                hist.extend(_extra)
                hist.sort(key=lambda x: str(x.get("date"))[:10])
                print(f"  破净率日频补充: +{len(_extra)} 点（月频 {len(hist) - len(_extra)} → 合计 {len(hist)}）")
        # 每交易日保留（上限 ~1250 行 ≈ 5年），超出按日期抽样
        if len(hist) > 1250:
            step = len(hist) // 1250
            _tail = hist[-1]
            hist = hist[::step]
            # 🔴 2026-09-23 修正：原 `hist.append(hist[-1])` 是自追加同一行（等于没补），
            #    抽样后真实末条可能被丢弃 → data_day 锚定跟着变旧；改为保留抽样前的真实末条
            if hist[-1] is not _tail and str(hist[-1].get("date"))[:10] != str(_tail.get("date"))[:10]:
                hist.append(_tail)
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

    # 🔴 2026-09-15 修复：原 `date` 直接取生成日（today）→ 跨零点调度（实测 2026-09-15 00:13）
    #    会把「9/14 收盘的估值快照」标成 9/15，且与 history 最新键（9/14）自相矛盾，
    #    属静默失效（有值但日期错位）。改为锚定数据日 = PE/PB 序列最后一行日期。
    data_day = today
    if hist:
        _ld = str(hist[-1].get("date") or "")[:10]
        if _ld:
            data_day = _ld
    snap["date"] = data_day
    if data_day != today:
        print(f"  ℹ️  温度计日期锚定数据日 {data_day}（生成日 {today}，跨零点调度）")

    therm = {"date": data_day, "snapshot": snap, "history": hist,
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

    obj = {"date": _data_date_str(), "generated_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "count": len(items), "items": items}
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
                               "chg_pct": round((last["close"] / prev["close"] - 1) * 100, 2) if prev and prev["close"] else None,
                               "source": "csv"}
            obj["vix_history"] = rows[-260:]  # 近1年
            print(f"  CBOE VIX: {last['close']} ({last['date']}) 历史 {len(rows)} 条")
    except Exception as e:
        print(f"  ⚠️  CBOE VIX 失败: {e}")

    # 1b. CBOE 延时报价兜底（2026-09-23 新增）
    #     🔴 根因：CBOE 的 `VIX_History.csv` **发布滞后** —— 实测 2026-09-22 美股收盘
    #     3.5 小时后（北京 09-23 07:32）该文件末行仍是 09-21，而当日 A 股/美股指数
    #     与新浪等源均已到 09-22 → 页面「CBOE VIX 恐慌指数」长期停在上一交易日。
    #     官方 delayed_quotes 接口在美东 16:15 结算后即给出当日收盘（实测
    #     last_trade_time=2026-09-22T16:15:01 / current_price=14.21）。
    #     口径纪律：**只在「报价日 > CSV 末日 且 已过 16:15 结算时刻」时补最新一根** ——
    #     盘中运行时 last_trade_time 是当日且值未定盘，**不得**当作收盘写入（会污染近1年曲线）。
    try:
        _r2 = _req.get("https://cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json",
                       timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        _qd = (_r2.json() or {}).get("data") or {}
        _lt = str(_qd.get("last_trade_time") or "")          # "2026-09-22T16:15:01"
        _qdate, _qhhmm = _lt[:10], _lt[11:16]
        _qval = _qd.get("current_price")
        _qpv = _qd.get("prev_day_close")
        if _qdate and _qval and _qhhmm >= VIX_SETTLE_HHMM:
            if rows and _qdate > rows[-1]["date"]:
                rows.append({"date": _qdate, "close": round(float(_qval), 2)})
                _prev = rows[-2]
            elif not rows:                                    # CSV 整体失败 → 仅用报价
                rows.append({"date": _qdate, "close": round(float(_qval), 2)})
                _prev = {"close": _qpv} if _qpv else None
            else:
                _prev = None                                 # CSV 已含当日，无需要补
            if _prev is not None:
                _pc = _prev.get("close")
                _lc = rows[-1]["close"]
                obj["cboe_vix"] = {"value": _lc, "prev": _pc, "date": rows[-1]["date"],
                                   "chg": round(_lc - _pc, 2) if _pc else None,
                                   "chg_pct": round((_lc / _pc - 1) * 100, 2) if _pc else None,
                                   "settled_at": _lt, "source": "csv+delayed_quote"}
                obj["vix_history"] = rows[-260:]
                print(f"  CBOE VIX 兜底: CSV 末 {_qdate} 前缺当日 → 用官方延时报价补 "
                      f"{rows[-1]['date']} 收盘 {_lc}（结算 {_lt}）")
        elif _qdate and obj.get("cboe_vix"):
            # 未过结算时刻（盘中）→ 保留 CSV 收盘，另记盘中读数供追溯，**不进 history**
            obj["cboe_vix"]["intraday"] = {"value": round(float(_qval), 2) if _qval else None,
                                           "time": _lt}
            print(f"  ℹ️  VIX 盘中读数 {_qval}（{_lt}）未达 16:15 结算，不写入收盘序列")
    except Exception as e:
        print(f"  ⚠️  CBOE VIX 延时报价兜底失败（保留 CSV 口径）: {e}")

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

    # 2026-09-13 修复：原 date 直接取「生成日」（today）→ 非交易日重跑会把页面「数据日期」
    # 写成生成日（实测周日重跑写入 2026-09-13，而 VIX/美股实际是 09-11 收盘）。
    # 治本 = 取实际数据日：A股 最新交易日 与 CBOE VIX 数据日（最新已收盘美股交易日）取较晚者。
    try:
        try:
            from market_calendar import is_trading_day, last_trading_day
            # 🔴 2026-09-15 补全 9/13 的修复：原 `last_trading_day()` 无参 = 今天，
            #    在交易日盘前重跑会把「9/14 收盘数据」锚成 9/15（实测 A股锚 2026-09-15）。
            #    正确口径 = 最近一个『已收盘』交易日：当日收盘前 → 上一交易日。
            _d = _dt.date.today()
            if is_trading_day(_d) and _dt.datetime.now().hour >= 15:
                _a_anchor = str(_d)
            else:
                _a_anchor = str(last_trading_day(_d - _dt.timedelta(days=1)))
        except Exception:
            _a_anchor = obj["date"]
        _us_anchor = (obj.get("cboe_vix") or {}).get("date") or obj["date"]
        obj["date"] = max(_a_anchor, _us_anchor)
        obj["generated_at"] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        # 两个锚显式落盘（2026-09-23）：面板「数据日期」取较晚者，但两锚可能不同日
        # （A股 9/22、CBOE 9/21）→ 前端 CBOE 卡自带日期、段落 meta 用 date；
        # 落盘 a_anchor/us_anchor 让守卫与排错能直接判「谁落后」，不必反推。
        obj["a_anchor"] = _a_anchor
        obj["us_anchor"] = _us_anchor
        print(f"  数据日期 {obj['date']}（A股锚 {_a_anchor} / 美股锚 {_us_anchor}）")
        _write_both("vix_panel.json", obj)
    except Exception as e:
        print(f"  ⚠️  数据日锚定失败（保留生成日 {obj['date']}）: {e}")


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
    blocks = _resolve_blocks()
    if LIST_BLOCKS:
        # 只输出块清单后立即退出（不写盘、不发请求）→ 供 check_touzid_panel.py 行为级断言
        print(",".join(blocks))
        raise SystemExit(0)
    print("待执行块: " + " → ".join(blocks))
    RUNNERS = {"thermometer": build_thermometer, "valuation": build_valuation_band,
               "vix": build_vix, "inst": build_institutional_flow}
    for b in blocks:
        RUNNERS[b]()
    print("\n═══ 完成 ═══")
