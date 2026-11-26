#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「昨夜收盘推演是否真的上线」守卫（2026-11-26 立）

背景（11-25 事故）：
  11/25 22:00（数据）与 22:15（推演发布）两档**触发了但空跑** —— 无产物、无 error 日志、
  本地零待推提交，远端只剩云端 CI 的提交 ⇒ 页面一整天停在 11-24，用户次日才发现。
  更坑的是：云端 CI 会在凌晨 01:46 / 02:44 把 `market.json` / `daily_news` 等**重新加密提交**，
  所以「远端最近有没有提交这些文件」**不能**作为判据（重加密＝无新数据也会进提交）。

判据（全部真跑代码，读 origin/main 的**解密后内容**，不看提交名/不看文件 mtime）：
  ① `output/v3_reasoning_latest.json.enc` → `data_date == 上一交易日` 且 `for_date == 其下一交易日`
  ② `data/daily_review/analysis.html.enc` → 段内 `data-review-date` **唯一值 == 上一交易日**（且 ≥10 处）
  ③ 软提示：V3 `generated` 早于复盘日收盘（15:00）→ 疑似旧版被重加密顶上来

跑法：
  python3 review/check_night_push.py            # 默认检查「上一交易日」
  python3 review/check_night_push.py --date 2026-11-24   # 指定复盘日（反向测试/补发核对）
  python3 review/check_night_push.py --json     # 机读输出

退出码：0 = 已上线（或尚不适用）｜1 = 未上线（需人工补发）｜2 = 无法判定（fetch 被锁/解密失败）

🔴 依赖 cryptography → 本机 `python3` 没有该库，脚本会自动 re-exec 到
   `~/.workbuddy/binaries/python/envs/default/bin/python`（可用 DDB_PY 覆盖）。
🔴 全程只读：只 `git fetch` + `git show`，绝不写工作区、绝不碰 refs/heads/main。
"""
import argparse
import base64
import datetime as _dt
import json
import os
import re
import subprocess
import sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
except ModuleNotFoundError:  # 本机 python3 无 cryptography → 换解释器重跑
    # 🔴 踩过：`envs/default/bin/python` 是**指向同一 3.13 二进制的 symlink**，
    #    用 realpath 比对会误判「同一个解释器」而放弃重跑 → 改用 env 标记防重入。
    _alt = os.environ.get("DDB_PY") or os.path.expanduser(
        "~/.workbuddy/binaries/python/envs/default/bin/python")
    if os.path.exists(_alt) and not os.environ.get("DDB_PY_REEXEC"):
        os.environ["DDB_PY_REEXEC"] = "1"
        os.execv(_alt, [_alt, os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit("✗ 缺少 cryptography，且未找到备用解释器（可设 DDB_PY 指定）")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
ENC_SUFFIX = ".enc"
V3 = "output/v3_reasoning_latest.json"
REVIEW_HTML = "data/daily_review/analysis.html"


# ─────────────────────────── 基础工具 ───────────────────────────
def sh(args) -> str:
    return subprocess.check_output(args, cwd=BASE, stderr=subprocess.DEVNULL).decode("utf-8", "replace")


def load_key() -> bytes:
    env = os.environ.get("DDB_DATA_KEY", "").strip()
    if env:
        return base64.b64decode(env)
    for p in (os.path.join(BASE, ".secret", "keys.json"),):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return base64.b64decode(json.load(f)["data_key"])
    raise RuntimeError("未找到密钥（.secret/keys.json 或 DDB_DATA_KEY）")


def unseal(key: bytes, blob: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def origin_blob(rel: str):
    """读 origin/main 上某文件（密文优先，回退明文）。返回 (bytes, 说明)"""
    for cand, note in ((rel + ENC_SUFFIX, "密文"), (rel, "明文")):
        try:
            out = subprocess.run(["git", "show", f"origin/main:{cand}"], cwd=BASE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
            return out.stdout, note
        except subprocess.CalledProcessError:
            continue
    return None, "缺失"


def git_lock_present() -> bool:
    return os.path.exists(os.path.join(BASE, ".git", "index.lock")) or os.path.isdir(
        os.path.join(BASE, ".git", "rebase-merge"))


# ─────────────────────────── 交易日历 ───────────────────────────
def _cal():
    sys.path.insert(0, BASE)
    import market_calendar  # noqa: WPS433
    return market_calendar


def prev_trading_day(d: _dt.date) -> _dt.date:
    """严格早于 d 的最近交易日（d 本身是交易日也不返回 d）"""
    cal = _cal()
    cur = d - _dt.timedelta(days=1)
    for _ in range(30):
        if cal.is_trading_day(cur):
            return cur
        cur -= _dt.timedelta(days=1)
    raise RuntimeError("回看 30 天未找到交易日，日历异常")


def next_trading_day(d: _dt.date) -> _dt.date:
    """严格晚于 d 的下一交易日。

    🔴 铁律 26②：market_calendar.next_trading_day() 是「**不早于**」语义，
       直接传 d 会原样返回 d → 必须传 d+1 天。
    """
    return _cal().next_trading_day(d + _dt.timedelta(days=1))


# ─────────────────────────── 主判定 ───────────────────────────
def check(target: _dt.date | None, do_fetch: bool) -> dict:
    today = _dt.date.today()
    target = target or prev_trading_day(today)
    res = {"target": str(target), "for_date_expected": str(next_trading_day(target)),
           "ok": False, "problems": [], "notes": [], "code": 1}

    if do_fetch and not git_lock_present():
        try:
            subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=BASE,
                           timeout=90, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:  # 网络问题不致命：用现有 origin/main 影子
            res["notes"].append(f"fetch 失败（用现有 origin/main 影子）：{e}")
    elif git_lock_present():
        res["notes"].append("本地 git 被占用（index.lock/rebase）→ 跳过 fetch，用现有 origin/main 影子")

    try:
        key = load_key()
    except Exception as e:
        res["problems"].append(f"密钥不可用：{e}")
        res["code"] = 2
        return res

    # ① V3 推演
    blob, note = origin_blob(V3)
    if blob is None:
        res["problems"].append(f"origin/main 上找不到 {V3}(.enc) —— 推演从未上线")
    elif note == "密文":
        try:
            v3 = json.loads(unseal(key, blob))
            dd, fd = v3.get("data_date"), v3.get("for_date")
            res["v3"] = {"data_date": dd, "for_date": fd, "generated": v3.get("generated")}
            if dd != str(target):
                res["problems"].append(f"V3 data_date={dd}（应为 {target}）")
            if fd != res["for_date_expected"]:
                res["problems"].append(f"V3 for_date={fd}（应为 {res['for_date_expected']}）")
            gen = str(v3.get("generated") or "")
            if gen[:10] and gen[:10] < str(target):
                res["notes"].append(f"V3 generated={gen} 早于复盘日 → 疑似旧版被重加密顶上来")
        except Exception as e:
            res["problems"].append(f"V3 解密/解析失败：{e}")
            res["code"] = 2
    else:
        res["notes"].append("origin/main 上 V3 是明文（未加密态），按明文判定")
        try:
            v3 = json.loads(blob)
            res["v3"] = {"data_date": v3.get("data_date"), "for_date": v3.get("for_date")}
            if v3.get("data_date") != str(target):
                res["problems"].append(f"V3 data_date={v3.get('data_date')}（应为 {target}）")
        except Exception as e:
            res["problems"].append(f"V3 解析失败：{e}")
            res["code"] = 2

    # ② 正文段内 data-review-date 唯一值
    blob, note = origin_blob(REVIEW_HTML)
    if blob is None:
        res["problems"].append(f"origin/main 上找不到 {REVIEW_HTML}(.enc)")
    else:
        try:
            html = (unseal(key, blob) if note == "密文" else blob).decode("utf-8-sig", "replace")
            dates = re.findall(r'data-review-date="(\d{4}-\d{2}-\d{2})"', html)
            uniq = sorted(set(dates))
            res["html"] = {"n_segments": len(dates), "dates": uniq}
            if uniq != [str(target)]:
                res["problems"].append(f"正文 data-review-date={uniq or '无'}（应为唯一值 {target}）")
            if len(dates) < 10:
                res["problems"].append(f"正文仅 {len(dates)} 处 data-review-date（<10，疑似未全段更新）")
        except Exception as e:
            res["problems"].append(f"正文解密/解析失败：{e}")
            res["code"] = 2

    if res["code"] != 2:
        res["ok"] = not res["problems"]
        res["code"] = 0 if res["ok"] else 1
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定复盘日 YYYY-MM-DD（默认 = 上一交易日）")
    ap.add_argument("--json", action="store_true", help="机读输出")
    ap.add_argument("--no-fetch", action="store_true", help="不 fetch，只用现有 origin/main 影子")
    a = ap.parse_args()

    target = _dt.date.fromisoformat(a.date) if a.date else None
    try:
        r = check(target, not a.no_fetch)
    except Exception as e:
        print(f"❌ 无法判定（{type(e).__name__}: {e}）")
        return 2

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        head = "✅ 已上线" if r["ok"] else ("⚠️ 无法判定" if r["code"] == 2 else "❌ 未上线")
        print(f"{head} —— 复盘日 {r['target']}（指引日应为 {r['for_date_expected']}）")
        if r.get("v3"):
            print(f"   V3 : data_date={r['v3'].get('data_date')} for_date={r['v3'].get('for_date')}"
                  f" generated={r['v3'].get('generated')}")
        if r.get("html"):
            print(f"   正文: 段 {r['html']['n_segments']} 处 · data-review-date={r['html']['dates']}")
        for p in r["problems"]:
            print(f"   ✗ {p}")
        for n in r["notes"]:
            print(f"   ⚠️  {n}")
        if not r["ok"] and r["code"] == 1:
            print(f"   → 判定：{r['target']} 的收盘推演**没有上线**（22:00/22:15 档可能空跑），需人工补发")
    return r["code"]


if __name__ == "__main__":
    sys.exit(main())
