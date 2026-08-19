#!/usr/bin/env python3
"""精简 signals.json 并同步所有数据文件到 deploy/ 目录（站点产物构建器）

职责（单一构建路径的核心一步）：
  1. 从 output/signals.json（全量）生成 deploy/signals.json（精简）：
     - stocks: 仅移除前端不渲染的 ema_detail
     - observation_pool: 仅保留卡片所需字段（大头瘦身，原可占 20MB+）
  2. 复制辅助数据（top10 / 板块 / ETF）到 deploy/output/
  3. 复制龙虎榜数据到 deploy/
  4. 调用 rebuild_html.py 生成 fetch 版 index.html（根 + deploy）
  5. 确保 deploy/.nojekyll（关闭 Jekyll，保证 output/ 子目录正常服务）
  6. 产出 deploy/build_manifest.json（构建时间 / 新鲜度 / 各文件体积）

所有写入均走原子替换，避免中断损坏线上产物。
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
import glob
import datetime as _dt

BASE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(BASE, "deploy")
# 云端(GitHub Actions, PYTHON=python) / 本机(未设 PYTHON 时用当前解释器) 均可移植。
# 曾经硬编码本机绝对路径，导致云端 rebuild_html.py 从未执行成功、deploy/index.html
# 长期停留在旧版本（实时盯盘 tab 每次数据更新后被旧页面覆盖而"消失"）。
PYTHON_BIN = os.environ.get("PYTHON", sys.executable)

# stocks 数组：保留 kline_preview(迷你K线) / four_volume(四量图) / 各 *_detail(详情弹窗)
# 仅移除前端完全未使用的 ema_detail。
STOCK_STRIP_KEYS = ["ema_detail"]

# observation_pool 数组：卡片模板只读少量字段，无需存全量股票对象。
# 详情弹窗通过 _stockDataMap[code] 从 stocks 数组查表，故池内不必重复存储大体积字段。
POOL_KEEP_KEYS = [
    "code", "name", "market", "has_data", "date", "pool_date",
    "ema_score", "close", "change_pct",
    "score",            # 含 grade/signals/signal_count/total_score/ema_strong
    "target_prices", "industry",
    "chan_buy", "golden_diamond", "inst_red", "uptrend",
    "old_duck_head", "strong_stock",
]


def _atomic_write(path: str, obj) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=".slm_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, default=str)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ── 金钻统一：信号选股 tab 的金钻字段对齐「兜宝金钻」tab 真值源 ──
def _parse_date(s):
    if not s:
        return None
    try:
        return _dt.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _date_diff_days(d1, d2):
    a, b = _parse_date(d1), _parse_date(d2)
    if not a or not b:
        return None
    return (a - b).days


def _shift_date(s, delta_days):
    d = _parse_date(s)
    if not d:
        return ""
    return (d + _dt.timedelta(days=delta_days)).strftime("%Y-%m-%d")


def unify_golden_diamond(data):
    """将 signals.json 的 golden_diamond / golden_diamond_detail 统一为「兜宝金钻」策略
    真值源（output/golden_diamond.json），保证信号选股 tab 的金钻与兜宝金钻 tab
    100% 一致，消除两套独立扫描带来的数量漂移。

    实现：用 golden_diamond.json 的命中集（兜宝金钻 tab 的同一产物）覆盖写入；
    非命中股票清空旧标注，确保信号选股「金钻」筛选结果与兜宝金钻 tab 完全对齐。
    """
    gd_path = os.path.join(BASE, "output", "golden_diamond.json")
    if not os.path.exists(gd_path):
        print("  ⚠️ golden_diamond.json 不存在，跳过金钻统一")
        return
    with open(gd_path, "r", encoding="utf-8") as f:
        gd = json.load(f)
    data_date = gd.get("data_date", "")

    mapping = {}
    for st in gd.get("stocks", []):
        code = st.get("code")
        if not code:
            continue
        primary = st.get("primary", "")
        if not primary:
            continue
        # 天→日，兼容前端 (\d+)日 解析与下游评分
        if "天" in primary and "日" not in primary:
            primary = primary.replace("天", "日")
        # 取主信号（与 golden_diamond_scan._primary 同优先级）
        sig = None
        for s in st.get("signals", []):
            if s.get("type", "").replace("天", "日") == primary:
                sig = s
                break
        if not sig and st.get("signals"):
            sig = st["signals"][0]
        sig_date = sig.get("date", "") if sig else ""

        detail = {
            "signal_type": primary,
            "window_days": 5,
            "golden_trend": (st.get("golden_trend") or [0])[-1],
            "golden_bull": (st.get("golden_bull") or [0])[-1],
            "in_red_zone": True,
            "signal_date": sig_date,
            "days_ago": _date_diff_days(data_date, sig_date),
        }
        sd = (sig.get("detail") or {}) if sig else {}
        if "pct" in sd:
            detail["pct_chg"] = sd["pct"]
            detail["is_yang"] = sd.get("yang")
        if "dy2" in sd:
            detail["ddx_last"] = sd["dy2"]
        # 红区黄柱连续：补 streak 信息（前端展示「连续N日」）
        if primary.startswith("红区黄柱连续"):
            m = re.search(r"(\d+)日", primary)
            n = int(m.group(1)) if m else (sig.get("streak") or 0)
            detail["streak_len"] = n
            detail["streak_end"] = sig_date
            detail["streak_start"] = _shift_date(sig_date, -(n - 1)) if sig_date else ""
        mapping[code] = {"primary": primary, "detail": detail}

    n_set = 0
    n_cleared = 0
    for stock in data.get("stocks", []):
        code = stock.get("code")
        if code in mapping:
            m = mapping[code]
            stock["golden_diamond"] = m["primary"]
            stock["golden_diamond_detail"] = m["detail"]
            n_set += 1
        elif stock.get("golden_diamond"):
            # 清空旧标注，保证与兜宝金钻策略完全一致
            stock["golden_diamond"] = ""
            stock["golden_diamond_detail"] = {}
            n_cleared += 1

    # 观测池（卡片用白名单字段）同步 golden_diamond 标签，保持展示一致
    for stock in data.get("observation_pool", []):
        code = stock.get("code")
        if code in mapping:
            stock["golden_diamond"] = mapping[code]["primary"]
        else:
            stock["golden_diamond"] = ""

    print(f"  🔗 金钻统一：{n_set} 只沿用兜宝金钻策略，{n_cleared} 只旧标注已清空")


def slim_signals():
    src = os.path.join(BASE, "output", "signals.json")
    dst = os.path.join(DEPLOY, "signals.json")

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ── 自包含新鲜度：构建步骤直接计算，不依赖 data_pipeline 先算 ──
    import sys as _sys
    _sys.path.insert(0, BASE)
    import market_calendar as _mc

    data_date = data.get("data_date")
    if not data_date:
        _dates = [s.get("date") for s in data.get("stocks", []) if s.get("date")]
        if _dates:
            data_date = max(_dates)
    if data_date:
        data["data_date"] = data_date
        data["freshness"] = _mc.eval_freshness(data_date)
    else:
        data["freshness"] = {}

    # 移除每只股票的冗余字段
    for stock in data.get("stocks", []):
        for key in STOCK_STRIP_KEYS:
            stock.pop(key, None)

    # ── 金钻统一：信号选股对齐「兜宝金钻」真值源 ──
    unify_golden_diamond(data)

    # observation_pool：仅保留白名单字段（大幅瘦身）
    for stock in data.get("observation_pool", []):
        trimmed = {k: stock.get(k) for k in POOL_KEEP_KEYS if k in stock}
        # 原地替换为精简对象
        stock.clear()
        stock.update(trimmed)

    # ── 拆分 stocks 为独立文件（避免 4MB+ 单文件被 GitHub Pages CDN 截断） ──
    stocks = data.pop("stocks", [])
    # 保留完整版（含 stocks）供下次构建作为源 → 根 signals.json 必须是完整版
    _atomic_write(os.path.join(DEPLOY, "signals_full.json"), {**data, "stocks": stocks})
    _atomic_write(dst, data)  # 精简版 signals.json（~10KB，不含 stocks）
    stocks_dst = os.path.join(DEPLOY, "output", "stocks.json")
    _atomic_write(stocks_dst, stocks)  # 独立 stocks.json（~4.4MB）

    src_size = os.path.getsize(src) / 1024 / 1024
    dst_size = os.path.getsize(dst) / 1024 / 1024
    stocks_size = os.path.getsize(stocks_dst) / 1024 / 1024
    print(f"  signals.json: {src_size:.1f}MB -> {dst_size:.1f}MB (slim, 无stocks)")
    print(f"  output/stocks.json: {stocks_size:.1f}MB ({len(stocks)} stocks)")
    data["stocks"] = stocks  # 恢复供返回值使用
    return data


def copy_file(src_name, dst_subdir=""):
    src = os.path.join(BASE, "output", src_name)
    if not os.path.exists(src):
        src = os.path.join(BASE, src_name)
        if not os.path.exists(src):
            print(f"  ⚠️ {src_name} 不存在，跳过")
            return 0
    if dst_subdir:
        dst_dir = os.path.join(DEPLOY, dst_subdir)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, src_name)
    else:
        dst = os.path.join(DEPLOY, src_name)
    shutil.copy2(src, dst)
    return os.path.getsize(dst)


def main():
    print("═══ 精简数据并同步到 deploy/ ═══")
    os.makedirs(DEPLOY, exist_ok=True)

    # 1. 精简 signals.json
    print("\n[1/5] 精简 signals.json...")
    data = slim_signals()
    stock_count = len(data.get("stocks", []))
    pool_count = len(data.get("observation_pool", []))
    print(f"  stocks: {stock_count}, observation_pool(entries): {pool_count}")

    # 2. 复制辅助数据文件
    print("\n[2/5] 复制辅助数据...")
    sizes = {}
    sizes["output/top10_history.json"] = copy_file("top10_history.json", "output")
    sizes["output/sector_flow.json"] = copy_file("sector_flow.json", "output")
    sizes["output/national_team_etf.json"] = copy_file("national_team_etf.json", "output")
    sizes["output/golden_diamond.json"] = copy_file("golden_diamond.json", "output")
    sizes["output/golden_diamond_history.json"] = copy_file("golden_diamond_history.json", "output")
    sizes["output/sector_golden_diamond_history.json"] = copy_file("sector_golden_diamond_history.json", "output")
    # 研报加强（星球研报接入，命中股票的研报标签数据）
    sizes["output/report_analysis.json"] = copy_file("report_analysis.json", "output")
    # 观测池历史（按日期缓存，供前端日期选择器读取；全字段含细化指标供 XLS 导出）
    sizes["output/observation_pool.json"] = copy_file("observation_pool.json", "output")
    # 重要事件日历（按月缓存，东财财经日历接口抓取）
    for ec in glob.glob(os.path.join(BASE, "output", "event_calendar_*.json")):
        shutil.copy2(ec, os.path.join(DEPLOY, "output", os.path.basename(ec)))

    # 2.5 复制指数 K 线数据
    for kfile in ["sh_index_kline.json", "sz_index_kline.json", "cyb_index_kline.json", "kc50_index_kline.json", "hs300_index_kline.json"]:
        copy_file(kfile, "output")

    # 2.55 复制金钻门控文件（gate_scan 成功产出时，主动从 output 同步到 deploy）
    # 关键：此前缺这段复制逻辑，gate_scan 即使成功，deploy 里仍是旧数据（如 08-13 跑出 08-12 的 gate_data）
    for gate_f in ["gate_data.json", "golden_pool_manifest.json", "golden_pool_meta.json"]:
        src_g = os.path.join(BASE, "output", gate_f)
        if os.path.exists(src_g):
            shutil.copy2(src_g, os.path.join(DEPLOY, "output", gate_f))
    # golden_pool_*.json 分片也同步
    for fp in glob.glob(os.path.join(BASE, "output", "golden_pool_*.json")):
        shutil.copy2(fp, os.path.join(DEPLOY, "output", os.path.basename(fp)))
    if os.path.exists(os.path.join(BASE, "output", "gate_data.json")):
        print("  ✓ 金钻门控文件已从 output 同步到 deploy（gate_data + 分片）")

    # 2.6 兜底：金钻门控分片缺失时生成空 manifest（云端 gate_scan 失败时避免前端 404）
    manifest_dst = os.path.join(DEPLOY, "output", "golden_pool_manifest.json")
    meta_dst = os.path.join(DEPLOY, "output", "golden_pool_meta.json")
    gate_data_dst = os.path.join(DEPLOY, "output", "gate_data.json")
    if not os.path.exists(manifest_dst):
        # 从最近的 deploy（如果有）找 meta 文件名，否则用默认
        meta_name = "golden_pool_meta.json"
        # 生成最小可用结构：空 parts 让前端显示"今日金钻池为空"
        os.makedirs(os.path.dirname(manifest_dst), exist_ok=True)
        with open(manifest_dst, "w", encoding="utf-8") as f:
            json.dump({"parts": [], "meta": meta_name, "data_date": "", "scope_size": 0}, f, ensure_ascii=False)
        print(f"  ⚠️  分片清单缺失，已生成空 manifest.json (兜底)")
    if not os.path.exists(meta_dst):
        os.makedirs(os.path.dirname(meta_dst), exist_ok=True)
        with open(meta_dst, "w", encoding="utf-8") as f:
            json.dump({"data_date": "", "updated_at": "", "pool": {"label": "原始兜宝金钻", "scope_size": 0, "overview": {"total": 0}, "stocks": [], "chan": {"total": 0, "codes": []}}, "sector": {"label": "板块前100·换手≥4%", "scope_size": 0, "overview": {"total": 0}, "stocks": [], "chan": {"total": 0, "codes": []}}}, f, ensure_ascii=False)
        print(f"  ⚠️  meta 缺失，已生成空 meta.json (兜底)")
    if not os.path.exists(gate_data_dst):
        os.makedirs(os.path.dirname(gate_data_dst), exist_ok=True)
        with open(gate_data_dst, "w", encoding="utf-8") as f:
            json.dump({"data_date": "", "updated_at": "", "default_gate": "pool", "gates": {}}, f, ensure_ascii=False)
        print(f"  ⚠️  gate_data 缺失，已生成空 gate_data.json (兜底)")

    # 2.7 兜底升级：仅当 gate_data 整体为空（所有档 stocks 均为空且无任何命中）时，
    # 用 golden_diamond.json 反向构建最小可用的 gate_data。
    # 注意：不能只看 pool 档——TOP800 可能真实 0 命中但 all_a/sector 有命中（如 2026-08-19），
    # 若误触发会覆盖掉正常的 all_a/sector 数据。
    with open(os.path.join(DEPLOY, "output", "gate_data.json"), "r", encoding="utf-8") as f:
        _gd = json.load(f)
    _gates_all = _gd.get("gates", {})
    _all_empty = True
    for _gk, _gv in _gates_all.items():
        _stocks_cnt = len(_gv.get("stocks") or [])
        _ov_total = (_gv.get("overview") or {}).get("total") or 0
        if _stocks_cnt > 0 or _ov_total > 0:
            _all_empty = False
            break
    if _all_empty:
        _gd_src = os.path.join(DEPLOY, "output", "golden_diamond.json")
        if os.path.exists(_gd_src):
            with open(_gd_src, "r", encoding="utf-8") as f:
                _gds = json.load(f)
            _dd = _gds.get("data_date", "")
            _ov = _gds.get("overview", {})
            _stocks = _gds.get("stocks", [])
            # pool 档：把金钻命中作为最小可用的池（让前端能渲染命中行）
            _pool_stocks = []
            for s in _stocks:
                _p = s.get("primary") or (s.get("signals", [{}])[0].get("type", "") if s.get("signals") else "")
                _pool_stocks.append({
                    "code": s.get("code", ""), "name": s.get("name", ""),
                    "market": s.get("market", ""),
                    "primary": _p, "signals": s.get("signals", []) or [],
                    "pct_chg": s.get("pct_chg"), "close": s.get("close"),
                })
            _gd["data_date"] = _dd
            _gd["updated_at"] = _gds.get("updated_at", "")
            _gd["default_gate"] = "pool"
            # scope_size 取真实 TOP800 universe（与 gate_scan.load_top800_codes 一致），而非 0 hits
            try:
                _top800 = len(json.load(open(os.path.join(BASE, "output", "kline_raw.json"), encoding="utf-8")))
            except Exception:
                _top800 = 0
            _gd["gates"] = {
                "pool": {"label": "原始兜宝金钻(云端兜底)", "scope_size": _top800,
                         "overview": _ov, "stocks": _pool_stocks,
                         "chan": {"total": 0, "codes": []}},
                "sector_top100_to4": {"label": "板块前100·换手≥4%(云端兜底)", "scope_size": 0,
                                      "overview": {"total": 0}, "stocks": [], "chan": {"total": 0, "codes": []}},
            }
            with open(os.path.join(DEPLOY, "output", "gate_data.json"), "w", encoding="utf-8") as f:
                json.dump(_gd, f, ensure_ascii=False)
            print(f"  🛡️  gate_data 兜底升级：用 golden_diamond.json 构造池 ({len(_pool_stocks)} 只命中)")

    # 3. 复制龙虎榜数据
    print("\n[3/5] 复制龙虎榜数据...")
    lh_src = os.path.join(BASE, "lh_calendar.json")
    lh_dst = os.path.join(DEPLOY, "lh_calendar.json")
    if os.path.exists(lh_src):
        shutil.copy2(lh_src, lh_dst)
        sizes["lh_calendar.json"] = os.path.getsize(lh_dst)
        print(f"  lh_calendar.json: {sizes['lh_calendar.json']/1024:.0f} KB")
    else:
        print("  ⚠️ lh_calendar.json 不存在（deploy 中已有则保留）")

    # 4. 重新生成 index.html（fetch 版）
    print("\n[4/5] 重新生成 index.html...")
    ret = os.system(f'cd "{BASE}" && "{PYTHON_BIN}" rebuild_html.py')
    if ret == 0:
        print("  ✅ index.html 已生成并同步到 deploy/")
    else:
        print("  ⚠️ rebuild_html.py 失败")

    # 4.1 注入实时盯盘 tab（幂等：已存在则跳过）。
    #     此前仅在本地手动注入，云端每次 rebuild 后 tab 即丢失（被旧页面覆盖）。
    ret = os.system(f'cd "{BASE}" && "{PYTHON_BIN}" inject_realtime_tab.py')
    if ret == 0:
        print("  ✅ 实时盯盘 tab 已注入 index.html / index_template.html / deploy/index.html")
    else:
        print("  ⚠️ inject_realtime_tab.py 执行异常（不影响主流程）")

    # 5. 确保 .nojekyll + 构建清单
    print("\n[5/5] .nojekyll + 构建清单...")
    nojekyll = os.path.join(DEPLOY, ".nojekyll")
    open(nojekyll, "a").close()
    print(f"  ✓ deploy/.nojekyll")

    # 构建清单（供发布闸门与排障使用）
    manifest = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "freshness": data.get("freshness", {}),
        "data_date": data.get("data_date"),
        "stock_count": stock_count,
        "sizes_kb": {k: round(v / 1024, 1) for k, v in sizes.items() if v},
        "signals_json_kb": round(os.path.getsize(os.path.join(DEPLOY, "signals.json")) / 1024, 1),
        "index_html_kb": round(os.path.getsize(os.path.join(DEPLOY, "index.html")) / 1024, 1),
    }
    _atomic_write(os.path.join(DEPLOY, "build_manifest.json"), manifest)
    print(f"  ✓ deploy/build_manifest.json")

    # 汇总
    print("\n═══ 同步完成 ═══")
    for f in sorted(os.listdir(DEPLOY)):
        fp = os.path.join(DEPLOY, f)
        if os.path.isfile(fp):
            print(f"  {f}: {os.path.getsize(fp)/1024:.0f} KB")
        elif os.path.isdir(fp):
            for sf in sorted(os.listdir(fp)):
                sfp = os.path.join(fp, sf)
                if os.path.isfile(sfp):
                    print(f"  {f}/{sf}: {os.path.getsize(sfp)/1024:.0f} KB")


if __name__ == "__main__":
    main()
