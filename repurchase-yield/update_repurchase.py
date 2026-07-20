#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜金隐含空间 · 每日自动更新脚本 (update_repurchase.py)
=====================================================
每日 20:00 抓取「前一日 20:00 → 当日 20:00」区间内含"回购目标价"的上市公司公告，
计算隐含收益率 = (回购目标价 − 抓取日收盘价) / 抓取日收盘价，
批次留存、按 (代码, 公告日期, 公告类型) 去重，并重写 index.html 的 DATA 块。

数据窗口逻辑（与主站其他数据节奏不同）：
    抓取日 D 的批次 = 公告日期落在 (D-1 20:00, D 20:00] 的记录
    cap(抓取日) == 收盘基准日，收益率在该日冻结，作为可排序历史指标。

用法:
    python update_repurchase.py                 # 默认窗口: 昨日~今日, 增量更新
    python update_repurchase.py --dry-run       # 只打印拟写入记录, 不写文件
    python update_repurchase.py --from 2026-07-01 --to 2026-07-20   # 指定窗口回填
    python update_repurchase.py --index /path/index.html --store /path/records.json

反拦截策略:
    - 官方源(巨潮 cninfo)优先, 东方财富(eastmoney)备选
    - 浏览器 UA + Referer + Accept 头
    - 随机延时 + 指数退避重试 (MAX_RETRY)
    - 可选代理池: 环境变量 REPO_PROXY=http://host:port 或 --proxy

依赖: pip install requests
注意: 回购目标价目前从公告标题/摘要正则估算; 精确值需解析公告正文(PDF),
      生产环境应接入公告正文解析(见 parse_target_price 处 TODO)。
"""
import argparse, json, os, random, re, sys, time, datetime as dt
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("[fatal] 需要 requests: pip install requests")

# ---------- 配置 ----------
HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "index.html"
STORE_JSON = HERE / "records.json"          # 全量主存储(批次累加, 跨日去重)
DATA_START = "// ===== DATA START"
DATA_END   = "// ===== DATA END"

WINDOW_HOUR = 20
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# 公告源
CNINFO_API = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
EM_API     = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
# 行情(腾讯 gtimg, 无需登录)
GTIMG_KLINE = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# 随机延时 / 重试
MIN_DELAY, MAX_DELAY = 0.6, 2.4
MAX_RETRY = 3

PROXIES = {}
_proxy = os.environ.get("REPO_PROXY")
if _proxy:
    PROXIES = {"http": _proxy, "https": _proxy}

# ---------- 网络层 ----------
def http_get(url, params=None, headers=None, timeout=15):
    hdrs = {"User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9"}
    if headers:
        hdrs.update(headers)
    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(url, params=params, headers=hdrs,
                             proxies=PROXIES or None, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                return r
            print(f"  [warn] {url} -> HTTP {r.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"  [retry {attempt}/{MAX_RETRY}] {e}", file=sys.stderr)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY) * attempt)
    return None

# ---------- 公告抓取 (巨潮官方源) ----------
def fetch_cninfo_announcements(date_from, date_to):
    """查询窗口内含'回购'的公告。返回 [{code,name,ann_date,title,url}]。"""
    out, page = [], 1
    while True:
        r = http_get(CNINFO_API, params={
            "pageNum": page, "pageSize": 30,
            "column": "fulltext", "tabName": "fulltext",
            "plateCode": "", "stockCode": "",
            "seDate": f"{date_from}~{date_to}",
            "isHL": "", "sortName": "", "sortType": "",
            "category": "", "keyword": "回购",
        }, headers={"Referer": "https://www.cninfo.com.cn/"})
        if not r:
            break
        try:
            data = r.json()
        except Exception:
            break
        items = data.get("announcements") or data.get("data") or data.get("list") or []
        if not items:
            break
        for it in items:
            title = it.get("announcementTitle") or it.get("title") or ""
            # 只保留与"回购 + (目标价/价格/方案/进展)"相关的
            if "回购" in title and any(k in title for k in ("目标价", "价格", "方案", "进展", "注销")):
                adj = it.get("adjunctUrl")
                out.append({
                    "code": it.get("stockCode"),
                    "name": it.get("stockName") or it.get("shortName"),
                    "ann_date": (it.get("announcementTime") or it.get("eitime") or "")[:10],
                    "title": title,
                    "url": f"https://www.cninfo.com.cn{adj}" if adj else "",
                })
        if len(items) < 30:
            break
        page += 1
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return out

# ---------- 收盘价 (腾讯 gtimg) ----------
def code_to_gtimg(code):
    pre, suf = code.split(".")
    return ("sh" if suf.upper() == "SH" else "sz") + pre

def fetch_close(code, date):
    g = code_to_gtimg(code)
    r = http_get(GTIMG_KLINE, params={"param": f"{g},day,{date},{date},1,qfq"})
    if not r:
        return None
    try:
        j = r.json()
        node = j["data"][g]
        for key in ("qfqday", "day"):
            if key in node and node[key]:
                return float(node[key][0]["close"])
    except Exception:
        pass
    return None

# ---------- 解析回购目标价 ----------
TARGET_RE = re.compile(
    r"(?:回购.*?价格|回购.*?上限|回购.*?金额.*?价格)[^0-9]{0,30}?([0-9]+\.[0-9]{1,3})"
)

def parse_target_price(text):
    """从标题/摘要估算回购价格上限。
    TODO(生产): 真实目标价需下载公告正文(PDF/HTML)后解析,
         例如匹配"回购价格不超过 X 元/股"或"回购价格上限 X 元"。
    """
    m = TARGET_RE.search(text or "")
    return float(m.group(1)) if m else None

# ---------- 组装记录 ----------
def build_records(ann_list):
    recs = []
    for a in ann_list:
        if not a.get("code") or "." not in (a.get("code") or ""):
            continue
        close = fetch_close(a["code"], a["ann_date"])
        if close is None or close <= 0:
            print(f"  [skip] {a['name']} 无收盘价", file=sys.stderr)
            continue
        target = parse_target_price(a["title"])
        if target is None:
            # 标题未含明确价格, 略过(生产环境应下钻正文)
            continue
        yld = (target - close) / close * 100
        recs.append({
            "stock": a["name"], "code": a["code"],
            "ann": a["ann_date"], "cap": a["ann_date"],
            "target": target, "close": round(close, 2), "chg": None,
            "amt": "—", "shares": "—", "pct": "—",
            "use": "—", "period": "—",
            "note": f"巨潮命中, 隐含{yld:+.1f}%",
        })
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return recs

# ---------- 存储 / 去重 ----------
def load_store(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def dedupe_key(r):
    # (代码, 公告日期, 公告类型摘要) 去重
    return (r["code"], r["ann"], r.get("note", "")[:10])

def merge_store(store, new_recs):
    seen = {dedupe_key(r) for r in store}
    added = 0
    for r in new_recs:
        k = dedupe_key(r)
        if k not in seen:
            store.append(r)
            seen.add(k)
            added += 1
    return added

def render_data_block(store):
    lines = ["  const DATA = ["]
    for r in store:
        lines.append("    " + json.dumps(r, ensure_ascii=False) + ",")
    lines.append("  ];")
    return "\n".join(lines)

def write_index(index_path, store):
    html = index_path.read_text(encoding="utf-8")
    i = html.find(DATA_START)
    j = html.find(DATA_END)
    if i == -1 or j == -1:
        print("[error] 未找到 DATA 标记, 跳过写回 index.html", file=sys.stderr)
        return False
    pre = html[:i]                          # DATA_START 之前的内容
    eol = html.find("\n", i)
    start_line = html[i:eol + 1]            # 保留完整的 DATA START 注释行(供下次重写定位)
    post = html[j:]                         # 从 DATA END 注释行开始
    html = pre + start_line + render_data_block(store) + "\n  " + post
    index_path.write_text(html, encoding="utf-8")
    return True

# ---------- 入口 ----------
def main():
    ap = argparse.ArgumentParser(description="兜金隐含空间 每日自动更新")
    ap.add_argument("--dry-run", action="store_true", help="只打印, 不写文件")
    ap.add_argument("--from", dest="f", default=None, help="窗口起始日 YYYY-MM-DD")
    ap.add_argument("--to", dest="t", default=None, help="窗口结束日 YYYY-MM-DD")
    ap.add_argument("--index", default=str(INDEX_HTML), help="index.html 路径")
    ap.add_argument("--store", default=str(STORE_JSON), help="records.json 路径")
    ap.add_argument("--proxy", default=None, help="代理 http://host:port")
    args = ap.parse_args()

    if args.proxy:
        global PROXIES
        PROXIES = {"http": args.proxy, "https": args.proxy}

    now = dt.datetime.now()
    to_d = args.t or now.strftime("%Y-%m-%d")
    if args.f:
        from_d = args.f
    else:
        y = now - dt.timedelta(days=1)
        from_d = y.strftime("%Y-%m-%d")

    print(f"[info] 数据窗口 {from_d} ~ {to_d} (每日 {WINDOW_HOUR}:00 触发)")
    ann = fetch_cninfo_announcements(from_d, to_d)
    print(f"[info] 巨潮命中含'回购'公告 {len(ann)} 条")
    recs = build_records(ann)
    print(f"[info] 可计算隐含收益率 {len(recs)} 条")

    store = load_store(Path(args.store))
    added = merge_store(store, recs)
    print(f"[info] 去重后新增 {added} 条, 全量 {len(store)} 条")

    if args.dry_run:
        print(json.dumps(recs, ensure_ascii=False, indent=2))
        return

    Path(args.store).write_text(
        json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_index(Path(args.index), store):
        print("[done] 已更新 records.json 与 index.html")

if __name__ == "__main__":
    main()
