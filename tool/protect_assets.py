#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兜是宝 · 核心资产加密（AES-256-GCM）

作用：把页面实际 fetch 的核心数据加密为 `<原文件名>.enc`，并可移除明文，
      使 GitHub Pages / 公开仓库上只剩密文。前端登录后由浏览器解密。

密钥来源（优先级）：
  1) 环境变量 DDB_DATA_KEY（base64 32B）—— CI 用（GitHub Actions Secret）
  2) .secret/keys.json 的 data_key —— 本地用

用法：
  python tool/protect_assets.py --list              # 打印清单与状态
  python tool/protect_assets.py --encrypt           # 加密（保留明文）
  python tool/protect_assets.py --encrypt --purge   # 加密并删除明文（发布用）
  python tool/protect_assets.py --check             # 校验：清单中每个文件都有 .enc 且无明文
  python tool/protect_assets.py --decrypt DIR        # 应急：把 .enc 解到 DIR（需密钥）

fail-closed：密钥缺失、清单文件既无明文也无密文 → 非 0 退出，阻断发布。
"""
import argparse
import base64
import json
import os
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(BASE, "deploy")
KEYS_FILE = os.path.join(BASE, ".secret", "keys.json")
ENC_SUFFIX = ".enc"
MANIFEST = os.path.join(DEPLOY, "auth", "protected.json")

# ── 受保护清单 ──────────────────────────────────────────────
# 判据：index.html 实际 fetch 的路径（含动态拼接的命名规则）
PROTECTED = [
    # 根
    "signals.json",
    "lh_calendar.json",
    "realtime.json",
    # 每日复盘
    "data/daily_review/market.json",
    "data/daily_review/analysis.html",
    # output/ 页面直读
    "output/backtest_daily.json",
    "output/cross_analysis.json",
    "output/daily_macro_latest.json",
    "output/daily_news_latest.json",
    "output/daily_news_window.json",
    "output/feed_review_latest.json",
    "output/gate_data.json",
    "output/gate_data_lite.json",
    "output/golden_diamond_history.json",
    "output/golden_pool_manifest.json",
    "output/golden_pool_meta.json",
    "output/institutional_flow.json",
    "output/market_thermometer.json",
    "output/national_team_etf.json",
    "output/obs_deduce_latest.json",
    "output/observation_pool.json",
    "output/report_analysis.json",
    "output/sector_flow.json",
    "output/sector_golden_diamond_history.json",
    "output/stocks.json",
    "output/top10_history.json",
    "output/valuation_band.json",
    "output/vix_panel.json",
    "output/window_latest.json",
    # output/ 指数K线（_idxKlineFiles 映射）
    "output/sh_index_kline.json",
    "output/sz_index_kline.json",
    "output/cyb_index_kline.json",
    "output/kc50_index_kline.json",
    "output/hs300_index_kline.json",
]

# 通配：金钻分片（golden_pool_0..6）与事件日历（按月）
PATTERNS = ["golden_pool_", "event_calendar_"]


def load_key() -> bytes:
    env = os.environ.get("DDB_DATA_KEY", "").strip()
    if env:
        try:
            k = base64.b64decode(env)
        except Exception:
            sys.exit("✗ DDB_DATA_KEY 不是合法 base64")
        if len(k) != 32:
            sys.exit(f"✗ DDB_DATA_KEY 长度 {len(k)}，须 32 字节")
        return k
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, encoding="utf-8") as f:
            return base64.b64decode(json.load(f)["data_key"])
    sys.exit("✗ 未找到密钥：请设置 DDB_DATA_KEY 或先生成 .secret/keys.json")


def resolve() -> list[str]:
    """返回 deploy 下实际存在的受保护文件（相对路径）"""
    out = []
    for rel in PROTECTED:
        if os.path.exists(os.path.join(DEPLOY, rel)):
            out.append(rel)
    odir = os.path.join(DEPLOY, "output")
    if os.path.isdir(odir):
        for name in sorted(os.listdir(odir)):
            if not name.endswith(".json"):
                continue
            if any(name.startswith(p) for p in PATTERNS):
                rel = f"output/{name}"
                if rel not in out:
                    out.append(rel)
    return out


def enc_path(rel: str) -> str:
    return os.path.join(DEPLOY, rel + ENC_SUFFIX)


def seal(key: bytes, data: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def unseal(key: bytes, blob: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def cmd_list() -> int:
    files = resolve()
    print(f"受保护文件 {len(files)} 个（deploy/ 下实际存在）\n")
    total = 0
    for rel in files:
        p = os.path.join(DEPLOY, rel)
        size = os.path.getsize(p)
        total += size
        has_enc = "✓" if os.path.exists(enc_path(rel)) else "·"
        print(f"  [{has_enc}] {size / 1048576:8.2f} MB  {rel}")
    print(f"\n合计明文 {total / 1048576:.1f} MB")
    return 0


def cmd_encrypt(purge: bool) -> int:
    key = load_key()
    files = resolve()
    if not files:
        print("⚠️  清单为空（deploy/ 下未找到受保护文件）")
        return 0
    n_enc = 0
    for rel in files:
        p = os.path.join(DEPLOY, rel)
        with open(p, "rb") as f:
            data = f.read()
        blob = seal(key, data)
        with open(enc_path(rel), "wb") as f:
            f.write(blob)
        n_enc += 1
        if purge:
            os.remove(p)
        print(f"  🔒 {rel} → {rel}{ENC_SUFFIX} ({len(blob)} B)"
              + ("  明文已删" if purge else ""))
    # 落清单：既是 --check 的权威依据，也让「今天该有哪些文件」可审计
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({"v": 1, "count": len(files), "files": files}, f,
                  indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"🧾 受保护清单 → {os.path.relpath(MANIFEST, BASE)}（{len(files)} 条）")
    print(f"\n✅ 已加密 {n_enc} 个文件" + ("，明文已移除" if purge else "（明文保留）"))
    return 0


def cmd_check() -> int:
    """校验（不可空转）：
      ① 清单内每个文件必须存在 .enc
      ② deploy 下不得残留任何受保护明文
      校验对象来自上次加密写下的受保护清单（manifest.json）。
    """
    bad = []

    # ① 依据 manifest（加密时落下的权威清单）
    listed = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            listed = json.load(f).get("files", [])
    if not listed:
        bad.append("受保护清单缺失或为空（未执行过 --encrypt，或清单被删）")

    for rel in listed:
        if not os.path.exists(enc_path(rel)):
            bad.append(f"{rel}: 缺少 {rel}{ENC_SUFFIX}")
        if os.path.exists(os.path.join(DEPLOY, rel)):
            bad.append(f"{rel}: 明文仍在")

    # ② 兜底扫描：清单 + 通配范围内的明文一律视为泄漏
    odir = os.path.join(DEPLOY, "output")
    plain_hits = []
    for rel in PROTECTED:
        p = os.path.join(DEPLOY, rel)
        if os.path.exists(p):
            plain_hits.append(rel)
    if os.path.isdir(odir):
        for name in os.listdir(odir):
            if name.endswith(".json") and any(name.startswith(x) for x in PATTERNS):
                plain_hits.append(f"output/{name}")
    for h in sorted(set(plain_hits)):
        msg = f"{h}: 明文残留（未 purge）"
        if msg not in bad:
            bad.append(msg)

    if bad:
        print("❌ 校验未通过：")
        for b in bad:
            print("   ·", b)
        return 1
    print(f"✅ 校验通过：{len(listed)} 个受保护文件均为密文，且 deploy 下无受保护明文")
    return 0


def cmd_decrypt(outdir: str) -> int:
    key = load_key()
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for root, dirs, names in os.walk(DEPLOY):
        # auth/ 下是凭据（accounts.enc 由 DK_ADMIN 加密），不属数据资产
        dirs[:] = [d for d in dirs if os.path.join(root, d) != os.path.join(DEPLOY, "auth")]
        for name in names:
            if not name.endswith(ENC_SUFFIX):
                continue
            src = os.path.join(root, name)
            rel = os.path.relpath(src, DEPLOY)[: -len(ENC_SUFFIX)]
            dst = os.path.join(outdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as f:
                blob = f.read()
            with open(dst, "wb") as f:
                f.write(unseal(key, blob))
            n += 1
    print(f"✅ 已解密 {n} 个文件 → {outdir}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="核心资产加密 / 校验")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--encrypt", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--decrypt", metavar="DIR")
    ap.add_argument("--purge", action="store_true", help="加密后删除明文")
    a = ap.parse_args()

    if a.list:
        sys.exit(cmd_list())
    if a.encrypt:
        sys.exit(cmd_encrypt(a.purge))
    if a.check:
        sys.exit(cmd_check())
    if a.decrypt:
        sys.exit(cmd_decrypt(a.decrypt))


if __name__ == "__main__":
    main()
