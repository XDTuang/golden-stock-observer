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
    - 默认源: 新浪个股公告(sina) — 按股票池(默认主站当日 Top800)逐股扫, 下钻正文正则抠"回购价格上限"
    - 备选源: 巨潮 cninfo(部分网络被风控, 用 --source cninfo 切换)
    - 浏览器 UA + Referer + Accept 头
    - 随机延时 + 指数退避重试 (MAX_RETRY)
    - 可选代理池: 环境变量 REPO_PROXY=http://host:port 或 --proxy

依赖: pip install requests
注意: 回购目标价从新浪公告正文正则提取(回购价格上限 X 元/股);
      非"集中竞价设目标价"类(如回购注销/减资)已过滤, 不计入隐含收益率。
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

# 公告源(新浪个股公告, 稳定且正文可直接解析目标价) —— 默认首选
SINA_BULLETIN = "https://money.finance.sina.com.cn/corp/go.php/vCB_AllBulletin/stockid/{code}/page/{page}.phtml"
SINA_HOST     = "https://money.finance.sina.com.cn"
SINA_ROW_RE   = re.compile(r'(\d{4}-\d{2}-\d{2})&nbsp;<a[^>]*href=\'([^\']+)\'>(.*?)</a>')
# 非"集中竞价回购设目标价"类的回购公告(无隐含收益率意义), 跳过
REPO_EXCLUDE  = ("注销", "减资", "通知债权人", "限制性股票", "减持已回购", "法律意见书",
                 "核查意见", "股东大会", "实施", "进展公告")
# 目标价正则(按优先级匹配)
PRICE_RES = [
    re.compile(r'回购价格[^0-9]{0,8}不超过[^\d]{0,3}([0-9]+\.[0-9]{1,3})'),
    re.compile(r'回购价格上限[^\d]{0,3}([0-9]+\.[0-9]{1,3})'),
    re.compile(r'回购股份[^0-9]{0,20}?价格[^0-9]{0,8}不超过[^\d]{0,3}([0-9]+\.[0-9]{1,3})'),
    re.compile(r'不超过([0-9]+\.[0-9]{1,3})元/股'),
    re.compile(r'回购价格.{0,20}?([0-9]+\.[0-9]{1,3})元'),
]

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

# ---------- 股票池加载 (默认覆盖全策略宇宙 Top800) ----------
def load_pool(override=None):
    """返回 (codes列表, 来源说明)。优先级:
       1) --pool 指定文件
       2) 主站 signals.json -> stocks[].code   (当日成交额 TOP800, 每日主管线刷新)
       3) 本目录 pool.json 快照                (可由 signals.json 导出, 离线兜底)
       4) 仓库根 candidate_pool.json           (旧 64 只)
    codes 为腾讯格式 sh/sz/bj + 6位。"""
    candidates = []
    if override:
        candidates.append(("指定 --pool", Path(override)))
    candidates.append(("signals.json (Top800)", HERE.parent / "signals.json"))
    candidates.append(("pool.json 快照", HERE / "pool.json"))
    candidates.append(("candidate_pool.json", HERE.parent / "candidate_pool.json"))
    for label, p in candidates:
        if not p.exists():
            continue
        try:
            arr = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [warn] 读取 {label} 失败: {e}", file=sys.stderr)
            continue
        if isinstance(arr, dict):
            arr = arr.get("stocks") or arr.get("data") or []
        codes = []
        if isinstance(arr, list):
            for x in arr:
                if isinstance(x, str):
                    codes.append(x)
                elif isinstance(x, dict) and x.get("code"):
                    codes.append(x["code"])
        codes = [c for c in codes if isinstance(c, str) and len(c) >= 7
                 and c[:2] in ("sh", "sz", "bj")]
        if codes:
            return codes, f"{label} -> {len(codes)}只"
    return [], "无可用股票池"

# ---------- 公告抓取 (新浪个股公告, 按股票池逐股扫) ----------
def pool_code_to_full(raw):
    """'sh600186' -> '600186.SH'"""
    pre, six = raw[:2], raw[2:]
    exg = {"sh": "SH", "sz": "SZ", "bj": "BJ"}.get(pre, "SH")
    return f"{six}.{exg}"

def fetch_sina_announcements(date_from, date_to, pool_override=None):
    """按股票池(默认主站当日 Top800)逐股扫新浪公告, 返回窗口内含'回购目标价'的公告。
    返回 [{code, name, ann_date, title, target}]。"""
    pool, src = load_pool(pool_override)
    if not pool:
        print("  [warn] 股票池缺失, 跳过新浪源", file=sys.stderr)
        return []
    print(f"  [info] 股票池: {src}")
    out, seen = [], set()
    for raw in pool:
        six = raw[2:] if raw[:2] in ("sh", "sz", "bj") else raw
        full = pool_code_to_full(raw)
        for page in range(1, 4):
            url = SINA_BULLETIN.format(code=six, page=page)
            r = http_get(url, headers={"Referer": "https://finance.sina.com.cn/"})
            if not r:
                break
            r.encoding = "gb2312"
            rows = list(SINA_ROW_RE.finditer(r.text))
            if not rows:
                break
            oldest = rows[-1].group(1)
            for m in rows:
                date, href, title = m.group(1), m.group(2), m.group(3)
                if not (date_from <= date <= date_to):
                    continue
                if "回购" not in title or any(k in title for k in REPO_EXCLUDE):
                    continue
                name = title.split("：")[0].split(":")[0]
                key = (full, date, name)
                if key in seen:
                    continue
                seen.add(key)
                detail = SINA_HOST + href if href.startswith("/") else href
                target = parse_target_from_detail(detail)
                if target is None:
                    continue
                out.append({"code": full, "name": name,
                            "ann_date": date, "title": title, "target": target})
            if oldest < date_from:
                break
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return out

def parse_target_from_detail(url):
    """下钻新浪公告正文, 正则提取'回购价格上限 X 元/股'。"""
    r = http_get(url, headers={"Referer": "https://finance.sina.com.cn/"})
    if not r:
        return None
    r.encoding = "gb2312"
    txt = re.sub(r"<[^>]+>", " ", r.text)
    txt = re.sub(r"\s+", " ", txt)
    for p in PRICE_RES:
        m = p.search(txt)
        if m:
            return float(m.group(1))
    return None

# ---------- 收盘价 (腾讯 gtimg) ----------
def code_to_gtimg(code):
    pre, suf = code.split(".")
    return ("sh" if suf.upper() == "SH" else "sz") + pre

def fetch_close(code, date):
    """腾讯 gtimg 日线收盘价。gtimg 返回 qfqday/day 为数组的数组:
       [日期, 开, 收, 高, 低, 量...], 收盘价在索引 2。
       公告日若为非交易日, 向前回退最多 3 个交易日取收盘。"""
    g = code_to_gtimg(code)
    for back in range(0, 4):
        d = (dt.datetime.strptime(date, "%Y-%m-%d") - dt.timedelta(days=back)).strftime("%Y-%m-%d")
        r = http_get(GTIMG_KLINE, params={"param": f"{g},day,{d},{d},1,qfq"})
        if not r:
            continue
        try:
            j = r.json()
            if not isinstance(j.get("data"), dict):
                continue
            node = j["data"].get(g)
            if not isinstance(node, dict):
                continue
            for key in ("qfqday", "day"):
                arr = node.get(key)
                if arr and isinstance(arr[0], (list, tuple)) and len(arr[0]) >= 3:
                    return float(arr[0][2])
        except Exception:
            continue
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
        target = a.get("target")
        if target is None:
            target = parse_target_price(a["title"])
        if target is None:
            continue
        yld = (target - close) / close * 100
        src = "新浪" if "target" in a else "巨潮"
        recs.append({
            "stock": a["name"], "code": a["code"],
            "ann": a["ann_date"], "cap": a["ann_date"],
            "target": target, "close": round(close, 2), "chg": None,
            "amt": "—", "shares": "—", "pct": "—",
            "use": "—", "period": "—",
            "note": f"{src}命中, 隐含{yld:+.1f}%",
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
    # (代码, 公告日期, 股票名) 去重, 避免同股同日重复入库
    return (r["code"], r["ann"], r["stock"])

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
    global PROXIES
    ap = argparse.ArgumentParser(description="兜金隐含空间 每日自动更新")
    ap.add_argument("--dry-run", action="store_true", help="只打印, 不写文件")
    ap.add_argument("--from", dest="f", default=None, help="窗口起始日 YYYY-MM-DD")
    ap.add_argument("--to", dest="t", default=None, help="窗口结束日 YYYY-MM-DD")
    ap.add_argument("--index", default=str(INDEX_HTML), help="index.html 路径")
    ap.add_argument("--store", default=str(STORE_JSON), help="records.json 路径")
    ap.add_argument("--pool", default=None, help="股票池 json 路径(覆盖默认 Top800)")
    ap.add_argument("--source", default="sina", choices=["sina", "cninfo"],
                    help="公告源: sina(默认, 新浪逐股扫+正文抠价) / cninfo(巨潮)")
    ap.add_argument("--proxy", default=None, help="代理 http://host:port")
    args = ap.parse_args()

    if args.proxy:
        PROXIES = {"http": args.proxy, "https": args.proxy}

    now = dt.datetime.now()
    to_d = args.t or now.strftime("%Y-%m-%d")
    if args.f:
        from_d = args.f
    else:
        y = now - dt.timedelta(days=1)
        from_d = y.strftime("%Y-%m-%d")

    print(f"[info] 数据窗口 {from_d} ~ {to_d} (每日 {WINDOW_HOUR}:00 触发)")
    if args.source == "cninfo":
        ann = fetch_cninfo_announcements(from_d, to_d)
        tag = "巨潮"
    else:
        ann = fetch_sina_announcements(from_d, to_d, args.pool)
        tag = "新浪"
    print(f"[info] {tag}命中含'回购目标价'公告 {len(ann)} 条")
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
