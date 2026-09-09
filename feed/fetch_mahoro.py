#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · mahoro 研报信息流抓取器（增量投喂）
=========================================================
数据源：https://data.mahoro.cn （只读研报信息流 API，Bearer token 认证）

设计要点
--------
1. **产物落在仓库外**（默认）：~/Library/Application Support/goldenstock/feed_mahoro/
   原因：源内容为付费星球/订阅邮件的二手汇总，站方要求"自用、别转发、别公开"。
   仓库 XDTuang/golden-stock-observer 是 public，原文一律不入库、不 push。
   --emit-inbox 为显式开关，才写入 feed/inbox/日常投喂/ 参与现有归档链路（需自行确认版权）。
2. **增量水位线 + seen_ids 双保险**：watermark 回退 60 秒（重叠窗口，避免同分钟边界漏条），
   seen_ids 做幂等去重（避免重复落盘）。状态文件独立于仓库。
3. **order=asc 翻页**：中途挂掉水位线停在已处理位置，重跑不丢；cursor 为 keyset，不用 offset。
4. **匿名化红线**：不落盘 author 字段，来源只写星球标签（已匿名）。
5. **无第三方依赖**：仅 Python 标准库（urllib/json/re/datetime）。

用法
----
  python3 feed/fetch_mahoro.py                     # 增量：从上次水位线拉到最新
  python3 feed/fetch_mahoro.py --since 2026-09-07  # 指定起点（配合首次回填）
  python3 feed/fetch_mahoro.py --source gmail_wisburg,zsxq_vito
  python3 feed/fetch_mahoro.py --q 光模块          # 标题+正文子串过滤
  python3 feed/fetch_mahoro.py --count-only --since 2026-09-08 --until 2026-09-08
  python3 feed/fetch_mahoro.py --dry-run           # 只打印将落盘的文件，不写盘
  python3 feed/fetch_mahoro.py --emit-inbox        # 额外写入 feed/inbox/日常投喂/（版权自负）
  python3 feed/fetch_mahoro.py --min-chars 200     # 正文过短的碎片跳过（默认 0=不跳）
  python3 feed/fetch_mahoro.py --status            # 查看状态与配额

退出码：0 成功 / 2 认证失败 / 3 配额耗尽 / 4 网络或服务端错误
"""
import os, sys, re, json, time, argparse, datetime, urllib.request, urllib.parse, urllib.error

BASE = "https://data.mahoro.cn"
TOKEN_FILE = os.path.expanduser("~/.config/mahoro/token")
DATA_ROOT = os.path.expanduser("~/Library/Application Support/goldenstock/feed_mahoro")
STATE_FILE = os.path.join(DATA_ROOT, "_state", "mahoro_state.json")
INDEX_FILE = os.path.join(DATA_ROOT, "index.json")
RUNS_LOG = os.path.join(DATA_ROOT, "_state", "runs.log")

# 仓库内 inbox（仅 --emit-inbox 时使用）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX_DIR = os.path.join(REPO_ROOT, "feed", "inbox", "日常投喂")

# 源 → 中文短标签（用于文件名，必须不含下划线）
LABELS = {
    "gmail_wisburg": "智堡Wisburg",
    "zsxq_180kresearch": "180KResearch",
    "zsxq_guanlantai": "观澜台",
    "zsxq_jinfutou": "金斧头",
    "zsxq_logic": "逻辑与思考",
    "zsxq_shuzhi": "树枝报告",
    "zsxq_vito": "Vito行研札记",
}
# 进 inbox 时的来源归一（对齐 feed_archive.py 的 SRC_MAP）
SRC_MAP = {"gmail_wisburg": "研报", "zsxq_180kresearch": "研报", "zsxq_vito": "研报",
           "zsxq_guanlantai": "观点", "zsxq_jinfutou": "观点", "zsxq_logic": "观点",
           "zsxq_shuzhi": "观点"}

FMT = "%Y-%m-%d %H:%M"


# ─────────────────────────── 基础工具 ───────────────────────────

def load_token() -> str:
    tok = os.environ.get("MAHORO_API_KEY", "").strip()
    if not tok and os.path.exists(TOKEN_FILE):
        tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
    if not tok:
        sys.exit("❌ 未找到 token：请写入 ~/.config/mahoro/token 或设置环境变量 MAHORO_API_KEY")
    return tok


def api_get(path: str, params: dict = None, tok: str = "", timeout: int = 30):
    """返回 (status, data_or_rawstr, headers)。429 由外层处理。"""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + tok,
        "User-Agent": "goldenstock-feed/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


def err_code(payload) -> str:
    """从 401/403/429 响应里取 detail.code"""
    if isinstance(payload, dict):
        d = payload.get("detail")
        if isinstance(d, dict):
            return str(d.get("code", ""))
        if isinstance(d, str):
            return d
    return ""


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"watermark": "", "seen_ids": [], "runs": 0, "total_items": 0}


def save_state(st: dict):
    st["seen_ids"] = st.get("seen_ids", [])[-30000:]  # 有上限，防无限膨胀
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    st["updated_at"] = datetime.datetime.now().strftime(FMT)
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def load_index() -> dict:
    if os.path.exists(INDEX_FILE):
        try:
            return json.load(open(INDEX_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "updated_at": "", "entries": []}


def save_index(idx: dict):
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    idx["updated_at"] = datetime.datetime.now().strftime(FMT)
    json.dump(idx, open(INDEX_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def log_run(line: str):
    os.makedirs(os.path.dirname(RUNS_LOG), exist_ok=True)
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")


def safe_title(t: str, maxlen: int = 60) -> str:
    """文件名安全化：去非法字符、压缩空白、截断（保留可读中文）"""
    t = re.sub(r'[\s/\\:*?"<>|\r\n\t]+', " ", (t or "").strip())
    t = re.sub(r"\s{2,}", " ", t).strip().strip(".。 ")
    if len(t) > maxlen:
        t = t[:maxlen].rstrip()
    return t or "untitled"


def next_fid(idx: dict, date: str) -> str:
    """F{YYYYMMDD}-{当日序号:03d}，与 feed_archive.py 编号体系一致"""
    ymd = date.replace("-", "")
    seq = 0
    for e in idx["entries"]:
        if str(e.get("date", ""))[:10] != date:
            continue
        m = re.match(r"F\d{8}-(\d{3})$", str(e.get("id", "")))
        if m:
            seq = max(seq, int(m.group(1)))
    return f"F{ymd}-{seq + 1:03d}"


def shift(wm: str, seconds: int) -> str:
    """水位线平移（回退用），返回 'YYYY-MM-DDTHH:MM'"""
    try:
        dt = datetime.datetime.strptime(wm, FMT) + datetime.timedelta(seconds=seconds)
        return dt.strftime("%Y-%m-%dT%H:%M")
    except Exception:
        return wm.replace(" ", "T")


# ─────────────────────────── 抓取主流程 ───────────────────────────

def fetch_all(tok, since=None, until=None, sources=None, q=None,
              limit=100, fields="full", max_pages=200, dry=False):
    """按 cursor 翻页拉全量，返回 (items, pages, calls)"""
    items, cursor, pages, calls = [], None, 0, 0
    while pages < max_pages:
        p = {"order": "asc", "limit": limit, "fields": fields}
        if since:
            p["since"] = since
        if until:
            p["until"] = until
        if sources:
            p["source"] = sources
        if q:
            p["q"] = q
        if cursor:
            p["cursor"] = cursor

        status, data, headers = api_get("/api/v1/feed", p, tok)
        calls += 1
        if status == 429:
            code = err_code(data)
            if code == "QUOTA_EXHAUSTED":
                print("❌ 当日流量额度用尽（QUOTA_EXHAUSTED），0 点后重置")
                log_run(f"QUOTA_EXHAUSTED after {pages} pages")
                sys.exit(3)
            wait = int(headers.get("Retry-After") or 30)
            print(f"  ⏳ RATE_LIMITED，退避 {wait}s …")
            time.sleep(wait)
            continue
        if status in (401, 403):
            print(f"❌ 认证/授权失败 {status}: {err_code(data)}")
            print("   401 三种：NO_AUTH / BAD_AUTH_SCHEME / INVALID_TOKEN；403 = source 不在授权范围")
            sys.exit(2)
        if status != 200 or not isinstance(data, dict):
            print(f"❌ 请求失败 status={status} body={str(data)[:300]}")
            sys.exit(4)

        batch = data.get("items", [])
        items += batch
        pages += 1
        if dry:
            print(f"   [dry] 第 {pages} 页 +{len(batch)} 条")
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        time.sleep(0.4)  # 温和限速，远低于 60/分
    return items, pages, calls


def main():
    ap = argparse.ArgumentParser(description="mahoro 研报信息流抓取（增量投喂）")
    ap.add_argument("--since", default="", help="起点 YYYY-MM-DD[ HH:MM]，默认读状态水位线")
    ap.add_argument("--until", default="", help="终点（含当天/当时）")
    ap.add_argument("--source", default="", help="逗号分隔源名，默认全部授权源")
    ap.add_argument("--q", default="", help="标题+正文子串过滤")
    ap.add_argument("--limit", type=int, default=100, help="每页条数 1-100")
    ap.add_argument("--min-chars", type=int, default=0, help="正文少于该字符数则跳过（0=不跳过）")
    ap.add_argument("--max-pages", type=int, default=200, help="翻页上限保护")
    ap.add_argument("--count-only", action="store_true", help="只计数不落盘（走 fields=meta，省流量）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将落盘的文件名")
    ap.add_argument("--emit-inbox", action="store_true",
                    help="额外写入仓库内 feed/inbox/日常投喂/（⚠️ 原文将进入 public 仓库，须自担版权）")
    ap.add_argument("--recheck-days", type=int, default=0,
                    help="补扫近 N 天：先 meta 扫 id、再对未见 id 取全文（应对上游延迟补录历史条目）")
    ap.add_argument("--backfill", action="store_true", help="回填模式：忽略水位线，从 --since 拉起")
    ap.add_argument("--reset-state", action="store_true", help="清空水位线与 seen_ids")
    ap.add_argument("--status", action="store_true", help="查看状态、配额与源清单后退出")
    args = ap.parse_args()

    tok = load_token()
    os.makedirs(DATA_ROOT, exist_ok=True)

    # 状态/配额查询
    status, meta, _ = api_get("/api/v1/meta", tok=tok)
    if status == 200 and isinstance(meta, dict):
        if args.status:
            print("=" * 56)
            print(f"label           : {meta.get('label')}")
            print(f"sources         : {', '.join(meta.get('sources', []))}")
            print(f"rate_per_min    : {meta.get('rate_per_min')}")
            print(f"daily_quota_mb  : {meta.get('daily_quota_mb')}")
            print(f"used_today_mb   : {meta.get('used_today_mb')}")
            print(f"usage_today     : {meta.get('usage_today')}")
            print(f"earliest_readable: {meta.get('earliest_readable')}")
            print(f"feed_updated_at : {meta.get('feed_updated_at')}")
            st = load_state()
            print("-" * 56)
            print(f"本地 watermark  : {st.get('watermark') or '(空)'}")
            print(f"本地 seen_ids   : {len(st.get('seen_ids', []))}")
            print(f"本地累计        : {st.get('total_items', 0)} 条 / {st.get('runs', 0)} 次")
            print(f"产物根目录      : {DATA_ROOT}")
            idx = load_index()
            print(f"索引条目        : {len(idx['entries'])}")
            return
        print(f"🔑 label={meta.get('label')}  配额 {meta.get('used_today_mb')}/{meta.get('daily_quota_mb')} MB"
              f"  上游更新 {meta.get('feed_updated_at')}")
    elif status in (401, 403):
        print(f"❌ meta 认证失败 {status}: {err_code(meta)}")
        sys.exit(2)

    if args.reset_state:
        save_state({"watermark": "", "seen_ids": [], "runs": 0, "total_items": 0})
        print("🧹 状态已重置")

    st = load_state()
    idx = load_index()

    # 起点：显式 --since > 水位线（回退 60 秒重叠）
    if args.since:
        since = args.since.replace(" ", "T")
        if len(since) == 10:
            since += "T00:00"
    elif args.backfill or not st.get("watermark"):
        since = ""
    else:
        since = shift(st["watermark"], -60)

    until = args.until.replace(" ", "T") if args.until else ""
    if until and len(until) == 10:
        until += "T23:59"

    # ── 只计数 ──
    if args.count_only:
        items, pages, calls = fetch_all(tok, since, until, args.source, args.q,
                                       args.limit, "meta", args.max_pages, dry=True)
        per = {}
        for it in items:
            per[it.get("source", "?")] = per.get(it.get("source", "?"), 0) + 1
        print(f"📊 条数 {len(items)}  页数 {pages}  请求 {calls}")
        print(f"   分源: {json.dumps(per, ensure_ascii=False)}")
        log_run(f"count-only since={since} until={until} -> {len(items)} 条")
        return

    # ── 抓正文 ──
    print(f"⬇️  拉取中… since={since or '(全量)'} until={until or '(最新)'}"
          f"{' source=' + args.source if args.source else ''}{' q=' + args.q if args.q else ''}")

    if args.recheck_days:
        # 补扫模式：上游会延迟补录历史条目（实测 2026-09-09 同一区间两次请求 409 → 851 条），
        # 单靠水位线会永久漏掉补录内容。先 meta 扫 id（便宜），只对未见过的 id 取全文。
        since_n = (datetime.datetime.now() -
                   datetime.timedelta(days=args.recheck_days)).strftime("%Y-%m-%dT%H:%M")
        meta_items, mpages, mcalls = fetch_all(tok, since_n, until, args.source, None,
                                               args.limit, "meta", args.max_pages)
        known_ids = set(st.get("seen_ids", []))
        new_ids = [it for it in meta_items if it.get("id") and it["id"] not in known_ids]
        print(f"🔍 补扫近 {args.recheck_days} 天：{len(meta_items)} 条在库，未见 {len(new_ids)} 条 → 逐条取全文")
        items, pages, calls = [], mpages, mcalls
        for n, mit in enumerate(new_ids, 1):
            s2, d2, _ = api_get("/api/v1/feed/" + urllib.parse.quote(mit["id"], safe=""), tok=tok)
            if s2 == 200 and isinstance(d2, dict):
                one = d2.get("item") if isinstance(d2.get("item"), dict) else d2
                if isinstance(one, dict) and one.get("id"):
                    items.append(one)
            elif s2 == 429:
                print("  ⏳ 补扫遇限频，退避 30s"); time.sleep(30)
            if n % 25 == 0:
                print(f"   …{n}/{len(new_ids)}")
            time.sleep(0.2)
        print(f"   取回 {len(items)} 条全文（{calls + len(new_ids)} 次请求）")
    else:
        items, pages, calls = fetch_all(tok, since, until, args.source, args.q,
                                       args.limit, "full", args.max_pages)
        print(f"   取回 {len(items)} 条（{pages} 页 / {calls} 次请求）")

    seen = set(st.get("seen_ids", []))
    written, skipped_dup, skipped_short = 0, 0, 0

    for it in items:
        iid = it.get("id", "")
        src = it.get("source", "")
        pub = (it.get("published_at") or "")[:16]
        date = pub[:10] or datetime.datetime.now().strftime("%Y-%m-%d")
        title = it.get("title") or ""
        text = it.get("text") or ""

        # 去重唯一键 = 条目 id。⚠️ 绝不可用 (日期+源+标题)：
        # 实测 zsxq_logic 存在「#📚行业研报✅」这类合集标题，同一标题下挂着 25 篇完全不同的研报，
        # 按标题去重会静默误杀最值钱的内容（2026-09-09 首次回填即踩此坑，误杀 36 组）。
        if iid and iid in seen:
            skipped_dup += 1
            continue
        if args.min_chars and len(text) < args.min_chars:
            skipped_short += 1
            seen.add(iid)
            continue

        label = LABELS.get(src, src or "未知源")
        clean = safe_title(title)
        fid = next_fid(idx, date)
        day_dir = os.path.join(DATA_ROOT, date)
        # 文件名附 id 短码：同标题不同内容（合集类帖子）不会互相覆盖
        short = re.sub(r"\W", "", iid)[-8:] or ("%08d" % (written + 1))
        fname = f"{date}_{label}_{clean}_{short}.txt"
        fpath = os.path.join(day_dir, fname)

        body = (
            f"标题: {title}\n"
            f"来源: {label}（{it.get('source_label') or src}）\n"
            f"发布时间: {pub}\n"
            f"分类: {it.get('category') or '-'}\n"
            f"条目ID: {iid}\n"
            f"归档号: {fid}\n"
            f"抓取时间: {datetime.datetime.now().strftime(FMT)}\n"
            f"{'-' * 40}\n\n"
            f"{text}\n"
        )

        if args.dry_run:
            print(f"   [dry] {fname}  ({len(text)} 字)")
        else:
            os.makedirs(day_dir, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(body)
            if args.emit_inbox:
                os.makedirs(INBOX_DIR, exist_ok=True)
                inbox_name = f"{date}_{SRC_MAP.get(src, '其他')}_{clean}_{short}.txt"
                with open(os.path.join(INBOX_DIR, inbox_name), "w", encoding="utf-8") as f:
                    f.write(body)

        idx["entries"].append({
            "id": fid,
            "date": date,
            "src_name": src,
            "source": LABELS.get(src, src),
            "title": title,
            "chars": len(text),
            "file": os.path.join(date, fname),
            "published_at": pub,
            "fetched_at": datetime.datetime.now().strftime(FMT),
        })
        seen.add(iid)
        written += 1

    # 水位线推进：本次最大 published_at（asc 顺序）
    if items:
        last_pub = max((it.get("published_at") or "")[:16] for it in items)
        if last_pub and (not st.get("watermark") or last_pub > st["watermark"]):
            st["watermark"] = last_pub

    st["seen_ids"] = sorted(seen)
    st["runs"] = st.get("runs", 0) + 1
    st["total_items"] = st.get("total_items", 0) + written
    st["last_run"] = datetime.datetime.now().strftime(FMT)

    if not args.dry_run:
        save_index(idx)
        save_state(st)
        log_run(f"fetch since={since or '-'} -> 新写入 {written}，去重 {skipped_dup}，"
                f"过短跳过 {skipped_short}；水位线 {st.get('watermark')}")
    else:
        print("   [dry-run] 未写盘、未推进水位线")

    print(f"✅ 新写入 {written} 条 | 去重跳过 {skipped_dup} | 过短跳过 {skipped_short}")
    print(f"   产物: {DATA_ROOT}/<日期>/   索引: {INDEX_FILE}")
    print(f"   水位线: {st.get('watermark') or '(空)'}")
    if args.emit_inbox and written:
        print(f"   ⚠️  已同时写入 {INBOX_DIR}（原文进入 public 仓库，请自行确认版权与发布范围）")


if __name__ == "__main__":
    main()
