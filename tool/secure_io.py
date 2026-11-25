#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""受保护产物的安全读取：明文优先 → 同名 .enc 解密 → deploy 副本。

为什么需要（2026-11-25 事故）：
    真鉴权加密上线后，累积型产物（lh_calendar / national_team_etf /
    top10_history / sector_flow.history / golden_diamond_history）的明文被 purge，
    仓库里只剩 .enc。但生成脚本仍按「if os.path.exists(明文): json.load」读历史 →
    读不到 → 从空 dict 开始 → 每天只写当天 → 累积数据被静默覆盖成「只有一天」。
    实测：lh_calendar 30 天 → 1 天、national_team_etf 215 天 → 1 天、
    top10_history / sector_flow 各 20 天 → 1 天。

设计要点：
    🔴 本模块**永不抛异常、永不 exit**。取不到就返回 default —— 采集脚本是
    best-effort（`|| echo 跳过`），因读历史失败而整条链崩掉，比少一天历史更糟。
    密钥来源：DDB_DATA_KEY 环境变量（CI）> .secret/keys.json（本机）。都缺则跳过解密。

用法：
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tool"))
    from secure_io import load_json_any
    d = load_json_any("output/national_team_etf.json", {"history": {}})

约定：**只在读历史/读旧产物时用本模块**；写仍走原 save 函数（写明文，
加密由 protect_assets --encrypt 统一处理）。
"""
from __future__ import annotations

import base64
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL = os.path.dirname(os.path.abspath(__file__))
_DEPLOY = os.path.join(BASE, "deploy")
_KEYS_FILE = os.path.join(BASE, ".secret", "keys.json")

_warned: set[str] = set()


def _load_key():
    """返回 32 字节数据密钥，取不到返回 None（不抛、不 exit）。"""
    env = os.environ.get("DDB_DATA_KEY", "").strip()
    if env:
        try:
            key = base64.b64decode(env)
            if len(key) == 32:
                return key
        except Exception:  # noqa: BLE001
            pass
    if os.path.exists(_KEYS_FILE):
        try:
            with open(_KEYS_FILE, encoding="utf-8") as f:
                key = base64.b64decode(json.load(f)["data_key"])
            if len(key) == 32:
                return key
        except Exception:  # noqa: BLE001
            pass
    return None


def _unseal(key, blob: bytes) -> bytes:
    if _TOOL not in sys.path:
        sys.path.insert(0, _TOOL)
    from protect_assets import unseal  # noqa: PLC0415
    return unseal(key, blob)


def _candidates(rel: str) -> list[str]:
    """明文 → 本地密文 → deploy 明文 → deploy 密文。"""
    if os.path.isabs(rel):
        return [rel, rel + ".enc"]
    p = os.path.join(BASE, rel)
    dp = os.path.join(_DEPLOY, rel)
    return [p, p + ".enc", dp, dp + ".enc"]


def load_json_any(rel: str, default=None):
    """读受保护产物为 JSON。全部失败返回 default（只对同一路径告警一次）。"""
    for path in _candidates(rel):
        if not os.path.exists(path):
            continue
        try:
            if path.endswith(".enc"):
                key = _load_key()
                if key is None:
                    if rel not in _warned:
                        print(f"  ⚠️ {rel}.enc 需要密钥，但既无 DDB_DATA_KEY 也无 .secret/keys.json"
                              f" → 按无历史处理", file=sys.stderr)
                        _warned.add(rel)
                    continue
                with open(path, "rb") as f:
                    return json.loads(_unseal(key, f.read()))
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:  # noqa: BLE001
            if rel not in _warned:
                print(f"  ⚠️ {os.path.relpath(path, BASE)} 读取失败（{type(exc).__name__}），"
                      f"尝试下一个来源", file=sys.stderr)
                _warned.add(rel)
            continue
    return default


def load_json_lenient(rel: str, default):
    """load_json_any 的别名，语义更明确：拿不到就用 default 继续跑。"""
    return load_json_any(rel, default)
