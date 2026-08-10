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

BASE = os.path.dirname(os.path.abspath(__file__))
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
            "overview": sec.get("overview", {}),
            "chan": sec.get("chan", {"total": 0, "codes": []}),
            "stocks": sec.get("stocks", []),
        }
    else:
        sector_obj = None

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

    overview = gd.get("overview", {})
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
