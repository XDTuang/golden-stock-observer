#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 三星/海力士收盘价抓取（stock.fengle.me 无 15 分钟延迟看板）
=====================================================================
抓取 stock.fengle.me 页面 RSC 流中的 NAVER 实时行情数据，
提取 三星电子(005930.KS) 与 SK海力士(000660.KS) 最近交易日收盘价。

输出: output/kr_stocks.json + deploy/output/kr_stocks.json
  {
    "date": "2026-08-26",            # 最近交易日（localTradedAt）
    "source": "stock.fengle.me (NAVER 实时, 无延迟)",
    "stocks": [
      {"code":"000660","name":"SK하이닉스","close":1688000,"chg":10000,"pct":0.60},
      {"code":"005930","name":"삼성전자","close":261500,"chg":4500,"pct":1.75}
    ]
  }

用法:
  python fengle_kr.py            # 抓取并写 output + deploy/output
  python fengle_kr.py --dry-run  # 仅打印结果
"""
import os, re, sys, json, shutil, subprocess, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
URL = "https://stock.fengle.me"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
WANT = {"000660", "005930"}


def fetch(url, timeout=30, retries=3):
    """curl 抓取（更稳）+ 指数退避重试；低频访问避免触发风控"""
    for i in range(retries):
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", str(timeout), "-A", UA, url],
                capture_output=True, timeout=timeout + 10)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", errors="ignore")
        except Exception:
            pass
        if i < retries - 1:
            import time
            time.sleep(3 * (i + 1))
    return ""


def parse(html):
    flows = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    blob = "".join(flows).replace('\\"', '"')
    dec = json.JSONDecoder()
    found = {}

    def take(basic):
        code = basic.get("itemCode") or basic.get("reutersCode")
        if code not in WANT or code in found:
            return
        close = basic.get("closePrice", "")
        chg = basic.get("compareToPreviousClosePrice", "")
        pct = basic.get("fluctuationsRatio", "")
        ta = basic.get("localTradedAt", "") or basic.get("tradedAt", "")
        found[code] = {
            "code": code,
            "name": basic.get("stockName", ""),
            "close": int(close.replace(",", "")) if close and close.replace(",", "").isdigit() else None,
            "chg": int(chg.replace(",", "")) if chg and chg.replace(",", "").isdigit() else None,
            "pct": float(pct) if pct else None,
            "traded_at": ta,
        }

    # ① initialData.basic（主看板）
    for sm in re.finditer(r'"initialData":\s*\{', blob):
        try:
            obj, _ = dec.raw_decode(blob, sm.end() - 1)
            take(obj.get("basic", {}))
        except Exception:
            continue
    # ② industryCompareInfo 数组（行业对比，含另一只）
    for sm in re.finditer(r'"industryCompareInfo":\s*\[', blob):
        try:
            arr, _ = dec.raw_decode(blob, sm.end() - 1)
            for it in arr:
                take(it)
        except Exception:
            continue
    return found


def main():
    dry = "--dry-run" in sys.argv
    html = fetch(URL)
    found = parse(html)
    if not found:
        print("❌ 未解析到 000660/005930 数据（页面结构可能变化）")
        sys.exit(1)

    # 交易日 = localTradedAt 日期（任一股票）
    date = ""
    for v in found.values():
        if v.get("traded_at"):
            date = v["traded_at"][:10]
            break

    result = {
        "date": date,
        "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "stock.fengle.me (NAVER 实时, 无延迟)",
        "stocks": [found.get("000660"), found.get("005930")],
    }
    def _fmt(v, spec):
        """None 安全格式化。

        2026-08-28 修复：数据源的 compareToPreviousClosePrice 字段缺失时，
        parse() 会把 chg 置为 None（见 take()），原写法 `{None:+,}` 直接抛
        TypeError，导致本脚本崩溃 → 云端 daily-review-market.yml 连续两天 failure。
        缺失一律显示「—」，不做推算，避免编造数值。
        """
        return format(v, spec) if isinstance(v, (int, float)) else "—"

    for s in result["stocks"]:
        if s:
            print(f"  {s['code']} {s['name']} 收 {_fmt(s.get('close'), ',')} "
                  f"涨跌 {_fmt(s.get('chg'), '+,')} ({_fmt(s.get('pct'), '+.2f')}%) "
                  f"@ {s.get('traded_at') or '—'}")

    if dry:
        return result

    os.makedirs(os.path.join(BASE, "output"), exist_ok=True)
    for out in ("output/kr_stocks.json", "deploy/output/kr_stocks.json"):
        p = os.path.join(BASE, out)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写入 output/kr_stocks.json（交易日 {date}）")

    # 合并进 market.json（asia.kr_stocks），供每日复盘 2 板块数据驱动渲染
    mkt_paths = ("deploy/data/daily_review/market.json", "data/daily_review/market.json")
    for mp in mkt_paths:
        p = os.path.join(BASE, mp)
        if not os.path.exists(p):
            continue
        mkt = json.load(open(p, encoding="utf-8"))
        mkt.setdefault("asia", {})["kr_stocks"] = result
        with open(p, "w", encoding="utf-8") as f:
            json.dump(mkt, f, ensure_ascii=False, indent=2)
        print(f"✅ 已合并 asia.kr_stocks → {mp}")
    return result


if __name__ == "__main__":
    main()
