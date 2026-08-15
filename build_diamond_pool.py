#!/usr/bin/env python3
"""生成「兜宝金钻」分片数据 golden_pool.* —— 主站(output/)与钻石副站(diamond_site/output/)共用。

数据来源: output/golden_diamond.json（原始兜宝金钻机制产出，含每只股票 250 日 K线 + 金钻三子真值数组）

设计要点:
  1. 每只 stock 保留完整字段（含 kline 250日K线 + golden_bull/golden_trend/gt2/red_zone/yellow_bar 真值）。
     kline 是点开个股后主图/副图/四量图/判定明细渲染的必需数据，必须带上
     （早期为瘦身剔除 kline 导致副站点开个股全空白，已修正）。
  2. 按体积自动拆分成分片 golden_pool_0.json... + golden_pool_meta.json + golden_pool_manifest.json，
     解决 github.io 对单大文件(>800KB)限速传不动的问题。每只含 kline 后总体积约 4.6MB，
     故 MAX_PART_KB 设为 500，自动拆成 ~10 片（每片 <520KB，远小于 800KB 上限）。
  3. 同时写入主站 output/ 与钻石副站 diamond_site/output/，两站前端都按 manifest.parts 并行加载。
  4. 隔离: 钻石副站 output/ 移除沙盒 gate_data.json（线上本就 404）；主站 output/ 保留（沙盒预览用，无害）。
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import pandas as pd  # noqa: E402  最强金钻逐票滑动窗口 DataFrame 构建
from signals import compute_four_volume, check_chan_buy_signal  # noqa: E402  机构翻多 + 缠论买点（与回测同源）

DS_OUT = os.path.join(BASE, "diamond_site", "output")
MAIN_OUT = os.path.join(BASE, "output")
GD = os.path.join(BASE, "output", "golden_diamond.json")
GATE = os.path.join(BASE, "output", "gate_data.json")
MAX_PART_KB = 500  # 每分片目标上限(KB)，含 kline 后总体积~4.6MB → 自动拆 ~10 片，均 <800KB github.io 上限


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_target(out_dir, parts, meta, manifest, remove_gate):
    os.makedirs(out_dir, exist_ok=True)
    # 清理旧分片：股票数量减少时，残留的 golden_pool_*.json 已过时（manifest 不再指向），
    # 不清理会导致线上仓库堆积冗余分片、且可能误加载旧数据。
    import glob
    for old in glob.glob(os.path.join(out_dir, "golden_pool_*.json")):
        os.remove(old)
    part_names = []
    for i, part in enumerate(parts):
        fn = f"golden_pool_{i}.json"
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
            json.dump({"stocks": part}, f, ensure_ascii=False)
        sz = os.path.getsize(os.path.join(out_dir, fn)) / 1024
        part_names.append(fn)
        print(f"  [{os.path.basename(out_dir)}] 分片 {fn}: {len(part)} 只 | {sz:.0f} KB")
    with open(os.path.join(out_dir, "golden_pool_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    with open(os.path.join(out_dir, "golden_pool_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    print(f"  [{os.path.basename(out_dir)}] meta + manifest 已写 | 总分片={len(part_names)}")
    if remove_gate:
        gpath = os.path.join(out_dir, "gate_data.json")
        if os.path.exists(gpath):
            os.remove(gpath)
            print(f"  [{os.path.basename(out_dir)}] 已移除 gate_data.json (隔离)")


def compute_strongest(stocks, window=5):
    """最强金钻 = 金钻三形态任一(买入/金钻起涨/红区黄柱连续) + 机构翻多 + 缠论买点，window 日内齐备。

    对每只金钻命中股票，从其金钻信号日起 window 日内逐日滑动，检查是否同时出现
    「机构翻多(收盘价 > 机构牛线1)」与「缠论买点(近2交易日内买字)」。
    与回测 v7b 同源（signals.compute_four_volume + signals.check_chan_buy_signal）。

    返回 {code: {"signal_date", "jg_date", "chan_date", "ready_date"}}。
    """
    strongest = {}
    for s in stocks:
        code = s.get("code")
        kline = s.get("kline", [])
        if len(kline) < 60:
            continue
        sigs = s.get("signals", []) or []
        sig_date = sigs[0].get("date") if sigs else s.get("signal_date")
        if not sig_date:
            continue
        dates = [r.get("date") for r in kline]
        try:
            i0 = dates.index(sig_date)
        except ValueError:
            continue
        n = len(kline)
        jg_day = chan_day = ready_idx = None
        for j in range(i0, min(i0 + window, n)):
            sub = kline[:j + 1]
            try:
                df = pd.DataFrame([{
                    "date": r["date"], "open": r["open"],
                    "close": r.get("close", r.get("last")),
                    "high": r["high"], "low": r["low"], "volume": r["volume"],
                } for r in sub])
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                if jg_day is None and compute_four_volume(df).get("jg_now"):
                    jg_day = dates[j]
                if chan_day is None:
                    ok, det = check_chan_buy_signal(df)
                    if ok:
                        chan_day = det.get("buy_date") or dates[j]
            except Exception:
                continue
            if jg_day is not None and chan_day is not None:
                ready_idx = j
                break
        if jg_day is not None and chan_day is not None:
            strongest[code] = {
                "signal_date": sig_date,
                "jg_date": jg_day,
                "chan_date": chan_day,
                "ready_date": dates[ready_idx],
            }
    return strongest


def _mark_strongest(stocks, strongest):
    """给 stocks 里命中最强金钻的项打 strongest 标记，返回命中的 code 有序列表。"""
    for s in stocks:
        if s.get("code") in strongest:
            s["strongest"] = True
            s["strongest_detail"] = strongest[s["code"]]
    return [c for c in strongest]


def main():
    gd = load(GD)

    # scope_size / chan 优先从 gate_data pool 档取（更贴近门控语义）
    scope_size = len(gd.get("stocks", []))
    chan = {"total": 0, "codes": []}
    if os.path.exists(GATE):
        g = load(GATE)
        pool = g.get("gates", {}).get("pool", {})
        if pool.get("scope_size"):
            scope_size = pool["scope_size"]
        if pool.get("chan"):
            chan = pool["chan"]
        # 板块前100·换手≥4% 档：从 gate_data.json 提取（含每只 kline + 金钻真值），前端按门控展示
        sec = g.get("gates", {}).get("sector_top100_to4", {})
        sector_obj = {
            "label": sec.get("label", "板块前100·换手≥4%"),
            "scope_size": sec.get("scope_size", 0),
            "overview": dict(sec.get("overview", {})),
            "chan": sec.get("chan", {"total": 0, "codes": []}),
            "stocks": sec.get("stocks", []),
        }
        # sector 档最强金钻（同一口径，跟随当前门控）
        strongest_sector = compute_strongest(sector_obj["stocks"])
        _mark_strongest(sector_obj["stocks"], strongest_sector)
        sector_obj["overview"]["strongest"] = len(strongest_sector)
        sector_obj["overview"]["strongest_codes"] = list(strongest_sector)
        # 全A市场档：从 gate_data.json 提取（含每只 kline + 金钻真值），前端按门控展示
        all_a = g.get("gates", {}).get("all_a", {})
        all_a_obj = {
            "label": all_a.get("label", "全A市场"),
            "scope_size": all_a.get("scope_size", 0),
            "overview": dict(all_a.get("overview", {})),
            "chan": all_a.get("chan", {"total": 0, "codes": []}),
            "stocks": all_a.get("stocks", []),
        }
        # all_a 档最强金钻（同一口径）
        strongest_all_a = compute_strongest(all_a_obj["stocks"])
        _mark_strongest(all_a_obj["stocks"], strongest_all_a)
        all_a_obj["overview"]["strongest"] = len(strongest_all_a)
        all_a_obj["overview"]["strongest_codes"] = list(strongest_all_a)
    else:
        sector_obj = None
        all_a_obj = None

    stocks = []
    for s in gd.get("stocks", []):
        ns = dict(s)  # 保留全部字段（含 kline 250日K线，点开个股渲染主图/副图/四量图/明细必需）
        primary = s.get("primary", "") or ""
        ns["golden_diamond"] = primary  # 前端用 r.golden_diamond 判断信号
        sigs = s.get("signals", []) or []
        detail = {}
        if sigs:
            sd = sigs[0].get("detail", {}) or {}
            detail = {
                "pct_chg": sd.get("pct"),
                "signal_date": sigs[0].get("date"),
                "days_ago": s.get("days_ago"),
                "golden_trend": s.get("golden_trend"),
                "golden_bull": s.get("golden_bull"),
                "ddx_last": sd.get("dy2"),
                "window_days": 5,
            }
        ns["golden_diamond_detail"] = detail
        ns["has_data"] = True
        ns["score"] = {"signal_count": 1 if primary else 0}
        stocks.append(ns)

    # ── 最强金钻：金钻三形态任一 + 机构翻多 + 缠论买点，5日内齐备 ──
    strongest_pool = compute_strongest(stocks)
    strongest_codes = _mark_strongest(stocks, strongest_pool)

    overview = gd.get("overview", {})
    # 命中总数(overview.total)保持不变（三形态并集）；最强金钻为独立子集卡片，不叠加进 total
    overview["strongest"] = len(strongest_codes)
    overview["strongest_codes"] = strongest_codes
    data_date = gd.get("data_date")
    updated_at = gd.get("updated_at")

    # 估算体积决定分片数
    total_kb = len(json.dumps(stocks, ensure_ascii=False)) / 1024
    n_parts = max(1, int(total_kb / MAX_PART_KB) + (1 if total_kb % MAX_PART_KB else 0))
    chunk = max(1, (len(stocks) + n_parts - 1) // n_parts)
    parts = [stocks[i:i + chunk] for i in range(0, len(stocks), chunk)]
    part_names = [f"golden_pool_{i}.json" for i in range(len(parts))]

    meta = {
        "data_date": data_date,
        "updated_at": updated_at,
        "default_gate": "pool",
        "pool": {
            "label": "原始兜宝金钻",
            "scope_size": scope_size,
            "overview": overview,
            "chan": chan,
        },
        "all_a": all_a_obj if all_a_obj else {
            "label": "全A市场",
            "scope_size": 0,
            "overview": {},
            "chan": {"total": 0, "codes": []},
            "stocks": [],
        },
        "sector": sector_obj if sector_obj else {
            "label": "板块前100·换手≥4%",
            "scope_size": 0,
            "overview": {},
            "chan": {"total": 0, "codes": []},
            "stocks": [],
        },
    }
    manifest = {
        "meta": "golden_pool_meta.json",
        "parts": part_names,
        "data_date": data_date,
        "total": len(stocks),
    }

    # 主站 output/（保留 gate_data.json 沙盒数据）
    write_target(MAIN_OUT, parts, meta, manifest, remove_gate=False)
    # 钻石副站 diamond_site/output/（隔离移除 gate_data.json）
    write_target(DS_OUT, parts, meta, manifest, remove_gate=True)

    print(f"✅ 生成完成 | stocks={len(stocks)} | data_date={data_date} | 总分片={len(parts)}")


if __name__ == "__main__":
    main()
