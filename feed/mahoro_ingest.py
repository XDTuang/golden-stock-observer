#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mahoro 私有库入库器（2026-11-13）
================================================================
把 ~/Library/.../goldenstock/feed_mahoro/<date>/*.txt 建成可分析的私有仓：
  · sqlite 全文库（items + tags + attachments + FTS5 trigram）
  · 每日确定性 tar.gz 日片（冷备载体，推 private 仓）
  · manifest（行级 iid/sha256/bytes，用于恢复与三方对账）

🔴 红线：本脚本产物**全部落在仓库之外**；任何 --out 落在 public repo 内直接 exit 2。

用法
----
  python3 feed/mahoro_ingest.py --dedupe-index --dry-run   # 预览索引清洗（90337→54422）
  python3 feed/mahoro_ingest.py --dedupe-index             # 执行（写 .bak 后原子替换）
  python3 feed/mahoro_ingest.py --audit-files              # 只读体检（iid 缺失/同 iid 多 file/孤儿行）
  python3 feed/mahoro_ingest.py --backfill                 # 全量回填（约 19 min 单进程）
  python3 feed/mahoro_ingest.py --day 2026-11-13           # 单日
  python3 feed/mahoro_ingest.py --since 2026-11-01         # 区间增量
  python3 feed/mahoro_ingest.py --rebuild-fts              # 重建 FTS
  python3 feed/mahoro_ingest.py --rebuild-from-slices      # 用日片+manifest 重建 DB

退出码：0 全绿 / 1 有跳过（解析失败 <1%）/ 2 致命（路径/DB/schema）
"""
import os
import re
import sys
import json
import gzip
import time
import glob
import shutil
import sqlite3
import hashlib
import tarfile
import argparse
import datetime

REPO = os.path.expanduser("~/golden_stock_observer")
RAW = os.path.expanduser("~/Library/Application Support/goldenstock/feed_mahoro")
INDEX_FILE = os.path.join(RAW, "index.json")
STORE = os.path.expanduser("~/Library/Application Support/goldenstock/mahoro_store")
DB = os.path.join(STORE, "db", "mahoro.sqlite3")
SLICES = os.path.join(STORE, "slices")
MANIFEST_DIR = os.path.join(STORE, "manifest", "daily")
MANIFEST_SUMMARY = os.path.join(STORE, "manifest", "summary.json")
LOGS = os.path.join(STORE, "logs")
FMT = "%Y-%m-%d %H:%M"

SEP = "-" * 40
# 标题字段可能跨行（实测 13 例）→ 非贪婪匹配到「来源:」行
RE_HDR = re.compile(
    r"^标题:\s*(?P<title>.*?)\n"
    r"来源:\s*(?P<source>.*)\n"
    r"发布时间:\s*(?P<pub>.*)\n"
    r"分类:\s*(?P<cat>.*)\n"
    r"条目ID:\s*(?P<iid>.*)\n"
    r"归档号:\s*(?P<fid>.*)\n"
    r"抓取时间:\s*(?P<fetched>.*)\n"
    r"-{10,}\n", re.M | re.S)


def assert_private_path(p: str):
    rp = os.path.realpath(REPO)
    ap = os.path.realpath(os.path.abspath(p))
    if os.path.commonpath([ap, rp]) == rp:
        sys.exit(f"❌ 拒绝写入 public 仓库路径: {p}")


def norm(s: str) -> str:
    return (s or "").replace("\r\n", "\n").strip()


def load_index() -> dict:
    with open(INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


def atomic_write_json(path: str, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def parse_file(path: str):
    """→ dict(title, source_label, pub, cat, iid, fid, fetched, body, sha256, bytes, chars) / None"""
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    m = RE_HDR.match(raw)
    if not m:
        return None
    body = norm(raw[m.end():])
    d = {k: (m.group(k) or "").strip() for k in ("title", "source", "pub", "cat", "iid", "fid", "fetched")}
    d["title"] = re.sub(r"\s+", " ", d["title"]).strip()
    d["source_label"] = re.sub(r"（.*?）\s*$", "", d["source"]).strip() or d["source"]
    d["body"] = body
    d["chars"] = len(body)
    d["bytes"] = len(body.encode("utf-8"))
    d["sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return d


def date_dirs():
    out = []
    for p in sorted(glob.glob(os.path.join(RAW, "2*"))):
        if os.path.isdir(p) and re.match(r"^\d{4}-\d{2}-\d{2}$", os.path.basename(p)):
            out.append(os.path.basename(p))
    return out


# ───────────────────────── 索引清洗 ─────────────────────────

def cmd_dedupe_index(dry: bool):
    idx = load_index()
    entries = idx.get("entries", [])
    before = len(entries)

    groups = {}
    for e in entries:
        f = e.get("file") or ""
        groups.setdefault(f, []).append(e)

    kept, dropped, hdr_cache, no_hdr = [], 0, {}, 0
    multi = [(f, rows) for f, rows in groups.items() if len(rows) > 1]

    for f, rows in groups.items():
        if len(rows) == 1:
            kept.append(rows[0])
            continue
        # 多行组：读文件头（只读 8 行），保留 id == 文件头归档号 的那行
        path = os.path.join(RAW, f)
        hdr = None
        if os.path.exists(path):
            try:
                head = open(path, encoding="utf-8", errors="replace").read(600)
                hm = RE_HDR.match(head)
                hdr = {k: (hm.group(k) or "").strip() for k in ("iid", "fid", "cat")} if hm else None
            except Exception:
                hdr = None
        if hdr is None:
            no_hdr += 1
        pick = None
        if hdr and hdr.get("fid"):
            pick = next((r for r in rows if str(r.get("id")) == hdr["fid"]), None)
        if pick is None:
            pick = max(rows, key=lambda r: str(r.get("fetched_at") or ""))
        kept.append(pick)
        dropped += len(rows) - 1
        if hdr:
            hdr_cache[f] = hdr

    # 用文件头补 iid / category（不碰标题与正文）
    enriched = 0
    for e in kept:
        h = hdr_cache.get(e.get("file") or "")
        if h:
            if h.get("iid") and e.get("iid") != h["iid"]:
                e["iid"] = h["iid"]; enriched += 1
            if h.get("cat") and not e.get("category"):
                e["category"] = h["cat"]

    print(f"[dedupe] 行数 {before} → {len(kept)}（删 {dropped} 行 / 多行组 {len(multi)} / 无头文件 {no_hdr} / 补 iid {enriched}）")
    if dry:
        print("[dedupe] dry-run：未落盘")
        return 0

    bak = INDEX_FILE + "." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(INDEX_FILE, bak)
    print(f"[dedupe] 已备份 → {bak}")
    idx["entries"] = kept
    idx["version"] = 2
    atomic_write_json(INDEX_FILE, idx)

    # 自检：唯一 file 数 == 行数
    files = {e.get("file") for e in kept}
    print(f"[dedupe] 自检：行数 {len(kept)} / 唯一 file {len(files)} → {'✅' if len(kept) == len(files) else '❌'}")
    return 0 if len(kept) == len(files) else 1


# ───────────────────────── 体检 ─────────────────────────

def cmd_audit_files():
    idx = load_index()
    entries = idx.get("entries", [])
    by_file, by_iid, orphans = {}, {}, []
    for e in entries:
        f = e.get("file") or ""
        by_file.setdefault(f, []).append(e)
        if e.get("iid"):
            by_iid.setdefault(e["iid"], set()).add(f)
        if f and not os.path.exists(os.path.join(RAW, f)):
            orphans.append(f)

    disk = sum(len(glob.glob(os.path.join(RAW, d, "*.txt"))) for d in date_dirs())
    n_iid_missing = sum(1 for e in entries if not e.get("iid"))
    multi_file = {k: v for k, v in by_iid.items() if len(v) > 1}

    print("=== mahoro 索引/文件体检 ===")
    print(f"  索引行数            : {len(entries)}")
    print(f"  唯一 file           : {len(by_file)}")
    print(f"  磁盘 txt 数         : {disk}")
    print(f"  索引缺 iid 的行      : {n_iid_missing}")
    print(f"  同 iid 多 file 的组  : {len(multi_file)}")
    print(f"  索引有但文件不存在的 : {len(orphans)}")
    for f in orphans[:5]:
        print(f"     orphan: {f}")
    for iid, fs in list(multi_file.items())[:5]:
        print(f"     dup iid {iid}: {sorted(fs)[:3]}")
    ok = (n_iid_missing == 0) and (len(multi_file) == 0) and (len(orphans) == 0)
    print("判定:", "✅ 可安全清洗" if ok else "⚠️ 需先处理上述项（清洗仍会执行，但请人工确认 multi/dup 组）")
    return 0


# ───────────────────────── schema ─────────────────────────

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA page_size=4096;
PRAGMA mmap_size=1073741824;
PRAGMA cache_size=-131072;

CREATE TABLE IF NOT EXISTS sources(
  src_name TEXT PRIMARY KEY, label TEXT, kind TEXT,
  weight REAL DEFAULT 1.0, first_seen TEXT, last_seen TEXT, item_count INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS items(
  iid TEXT PRIMARY KEY,
  fid TEXT, date TEXT NOT NULL, src_name TEXT NOT NULL, source_label TEXT,
  category TEXT, author TEXT, title TEXT NOT NULL, body TEXT NOT NULL,
  url TEXT, chars INTEGER NOT NULL, bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
  file TEXT NOT NULL UNIQUE, file_mtime TEXT, file_size INTEGER,
  published_at TEXT, fetched_at TEXT, ingested_at TEXT NOT NULL,
  rev INTEGER DEFAULT 1, rewritten INTEGER DEFAULT 0);

CREATE INDEX IF NOT EXISTS ix_items_date ON items(date);
CREATE INDEX IF NOT EXISTS ix_items_src_date ON items(src_name, date);
CREATE INDEX IF NOT EXISTS ix_items_pub ON items(published_at);
CREATE INDEX IF NOT EXISTS ix_items_sha ON items(sha256);
CREATE INDEX IF NOT EXISTS ix_items_chars ON items(date, chars DESC);

CREATE TABLE IF NOT EXISTS tags(
  iid TEXT NOT NULL, tag TEXT NOT NULL, kind TEXT NOT NULL, hits INTEGER DEFAULT 1,
  PRIMARY KEY(iid, tag, kind));
CREATE INDEX IF NOT EXISTS ix_tags_tag ON tags(tag, kind);

CREATE TABLE IF NOT EXISTS attachments(
  sha256 TEXT PRIMARY KEY, iid TEXT NOT NULL, kind TEXT NOT NULL, ext TEXT,
  bytes INTEGER DEFAULT 0, path TEXT, source_url TEXT, fetched_at TEXT,
  status TEXT DEFAULT 'local');
CREATE INDEX IF NOT EXISTS ix_att_iid ON attachments(iid);

CREATE TABLE IF NOT EXISTS ingest_runs(
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT,
  mode TEXT, files_seen INTEGER DEFAULT 0, items_new INTEGER DEFAULT 0,
  items_upd INTEGER DEFAULT 0, parse_fail INTEGER DEFAULT 0,
  slice_written INTEGER DEFAULT 0, bytes_in INTEGER DEFAULT 0,
  status TEXT, note TEXT);

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
  title, body, content='items', content_rowid='rowid',
  tokenize='trigram', detail=none, columnsize=0);
"""

TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
  INSERT INTO items_fts(rowid,title,body) VALUES (new.rowid,new.title,new.body);
END;
CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
  INSERT INTO items_fts(items_fts,rowid,title,body) VALUES('delete',old.rowid,old.title,old.body);
END;
CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
  INSERT INTO items_fts(items_fts,rowid,title,body) VALUES('delete',old.rowid,old.title,old.body);
  INSERT INTO items_fts(rowid,title,body) VALUES (new.rowid,new.title,new.body);
END;
"""


def db_open(create=True) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    if create:
        conn.executescript(DDL)
    return conn


UPSERT = """
INSERT INTO items(iid,fid,date,src_name,source_label,category,author,title,body,url,chars,bytes,
                  sha256,file,file_mtime,file_size,published_at,fetched_at,ingested_at)
VALUES(:iid,:fid,:date,:src_name,:source_label,:category,:author,:title,:body,:url,:chars,:bytes,
       :sha256,:file,:file_mtime,:file_size,:published_at,:fetched_at,:ingested_at)
ON CONFLICT(iid) DO UPDATE SET
  fid=excluded.fid, title=excluded.title, chars=excluded.chars, bytes=excluded.bytes,
  sha256=excluded.sha256, file=excluded.file, file_mtime=excluded.file_mtime,
  file_size=excluded.file_size, ingested_at=excluded.ingested_at,
  rev = items.rev + (excluded.sha256 <> items.sha256),
  rewritten = items.rewritten OR (excluded.sha256 <> items.sha256),
  body = CASE WHEN excluded.sha256 <> items.sha256 THEN excluded.body ELSE items.body END,
  author = COALESCE(items.author, excluded.author),
  url = COALESCE(items.url, excluded.url)
WHERE excluded.sha256 <> items.sha256
   OR IFNULL(items.fid,'') <> IFNULL(excluded.fid,'')
   OR IFNULL(items.file,'') <> IFNULL(excluded.file,'')
"""


def write_slice(date: str) -> tuple:
    """确定性打包：gzip mtime=0 + tar mtime/uid/gid=0 + 排序 → 同日重跑字节一致"""
    files = sorted(glob.glob(os.path.join(RAW, date, "*.txt")))
    if not files:
        return (False, 0, 0)
    outdir = os.path.join(SLICES, date[:4])
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{date}.tar.gz")
    tmp = out + ".tmp"
    with open(tmp, "wb") as fo:
        with gzip.GzipFile(fileobj=fo, mode="wb", compresslevel=6, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                for f in files:
                    ti = tar.gettarinfo(f, arcname=f"{date}/{os.path.basename(f)}")
                    ti.mtime = 0
                    ti.uid = ti.gid = 0
                    ti.uname = ti.gname = ""
                    with open(f, "rb") as fh:
                        tar.addfile(ti, fh)
    os.replace(tmp, out)
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    return (True, os.path.getsize(out), sha)


def write_manifest(date: str, rows: list, slice_info: tuple):
    """rows: [(iid,fid,src,cat,title,chars,bytes,sha,file,pub)]"""
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    path = os.path.join(MANIFEST_DIR, f"{date}.jsonl.gz")
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=6) as f:
        for r in sorted(rows, key=lambda x: x[0]):
            f.write(json.dumps({
                "iid": r[0], "fid": r[1], "date": date, "src": r[2], "cat": r[3],
                "title": r[4], "chars": r[5], "bytes": r[6], "sha256": r[7],
                "file": r[8], "pub": r[9],
            }, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    return path


def update_summary():
    days = sorted({os.path.basename(p)[:-7] for p in glob.glob(os.path.join(SLICES, "*", "*.tar.gz"))})
    total = 0
    conn = db_open(create=False)
    try:
        row = conn.execute("SELECT COUNT(*) n, IFNULL(SUM(chars),0) c, MAX(date) d FROM items").fetchone()
        total, chars, latest = row["n"], row["c"], row["d"]
    except Exception:
        total, chars, latest = 0, 0, ""
    conn.close()
    summary = {
        "updated_at": datetime.datetime.now().strftime(FMT),
        "total_items": total, "total_chars": chars, "latest_date": latest,
        "slice_days": len(days), "first_slice": days[0] if days else "",
        "last_slice": days[-1] if days else "",
        "slices": {},
    }
    for d in days[-90:]:
        p = os.path.join(SLICES, d[:4], f"{d}.tar.gz")
        summary["slices"][d] = {"bytes": os.path.getsize(p),
                                "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
    atomic_write_json(MANIFEST_SUMMARY, summary)
    return summary


def enrich_index(mapping: dict) -> int:
    """把文件头解析出的 iid/category/chars/bytes/sha256 回写到 index.json（v2 富化）"""
    if not mapping:
        return 0
    idx = load_index()
    n = 0
    for e in idx.get("entries", []):
        m = mapping.get(e.get("file") or "")
        if not m:
            continue
        changed = False
        for k in ("iid", "category", "chars", "bytes", "sha256"):
            if m.get(k) and e.get(k) != m[k]:
                e[k] = m[k]
                changed = True
        if changed:
            n += 1
    if n:
        bak = INDEX_FILE + ".bak_enrich_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(INDEX_FILE, bak)
        idx["version"] = 2
        atomic_write_json(INDEX_FILE, idx)
        print(f"[ingest] 索引富化 {n} 行（备份 {os.path.basename(bak)}）")
    return n


def cmd_ingest(days: list, mode: str, no_slice: bool, workers: int, only_missing: bool = False):
    started = datetime.datetime.now()
    conn = db_open()
    # 全量回填：先删触发器、插完 rebuild（快 3-5×）
    bulk = (mode == "backfill")
    if bulk:
        conn.executescript("DROP TRIGGER IF EXISTS items_ai; DROP TRIGGER IF EXISTS items_ad;"
                           "DROP TRIGGER IF EXISTS items_au;")

    seen = new = upd = fail = 0
    bytes_in = 0
    touched_days = []
    index_map = {}
    existing = set()
    if only_missing:
        existing = {r[0] for r in conn.execute("SELECT file FROM items")}
        print(f"   only-missing：库内已有 {len(existing)} 个文件")
    index_map = {}
    for date in days:
        files = sorted(glob.glob(os.path.join(RAW, date, "*.txt")))
        if not files:
            continue
        touched_days.append(date)
        rows_for_manifest = []
        for fp in files:
            rel = os.path.join(date, os.path.basename(fp))
            if only_missing and rel in existing:
                continue
            seen += 1
            d = parse_file(fp)
            if d is None:
                fail += 1
                continue
            st = os.stat(fp)
            rec = {
                "iid": d["iid"] or f"file:{rel}",
                "fid": d["fid"], "date": date,
                "src_name": "", "source_label": d["source_label"],
                "category": d["cat"], "author": None,
                "title": d["title"] or "(无标题)", "body": d["body"],
                "url": None, "chars": d["chars"], "bytes": d["bytes"],
                "sha256": d["sha256"], "file": rel,
                "file_mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime(FMT),
                "file_size": st.st_size, "published_at": d["pub"],
                "fetched_at": d["fetched"], "ingested_at": started.strftime(FMT),
            }
            # src_name 从文件名或 sidecar 兜底（txt 头只有中文 label）
            rec["src_name"] = src_of(rel)
            existed = conn.execute("SELECT 1 FROM items WHERE iid=?", (rec["iid"],)).fetchone() is not None
            try:
                conn.execute(UPSERT, rec)
            except sqlite3.IntegrityError:
                # file 唯一约束冲突（同 file 换了 iid）→ 把旧行迁到新 iid 后再 upsert
                conn.execute("UPDATE OR IGNORE items SET iid=? WHERE file=?", (rec["iid"], rel))
                conn.execute(UPSERT, rec)
            if existed:
                upd += 1
            else:
                new += 1
            bytes_in += d["bytes"]
            index_map[rel] = {"iid": d["iid"], "category": d["cat"], "chars": d["chars"],
                              "bytes": d["bytes"], "sha256": d["sha256"]}
            index_map[rel] = {"iid": d["iid"], "category": d["cat"], "chars": d["chars"],
                              "bytes": d["bytes"], "sha256": d["sha256"]}
            rows_for_manifest.append((rec["iid"], rec["fid"], rec["src_name"], rec["category"],
                                      rec["title"], rec["chars"], rec["bytes"], rec["sha256"],
                                      rel, rec["published_at"]))
        conn.commit()
        if not no_slice:
            ok, sz, sha = write_slice(date)
            write_manifest(date, rows_for_manifest, (ok, sz, sha))
            print(f"   日片 {date}: {len(files)} 篇 / {sz/1e6:.2f} MB / sha {sha[:8]}")
        print(f"  ✓ {date}: {len(files)} 篇（累计 new={new} upd={upd} fail={fail}）")

    if bulk:
        conn.executescript(TRIGGERS)
        print("   重建 FTS…")
        t0 = time.time()
        conn.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
        conn.commit()
        print(f"   FTS rebuild {time.time()-t0:.1f}s")

    if bulk or mode == "day":
        enrich_index(index_map)

    if bulk or mode == "day":
        enrich_index(index_map)

    dur = (datetime.datetime.now() - started).total_seconds()
    conn.execute("""INSERT INTO ingest_runs(started_at,finished_at,mode,files_seen,items_new,
                    items_upd,parse_fail,bytes_in,status)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                 (started.strftime(FMT), datetime.datetime.now().strftime(FMT), mode,
                  seen, new, upd, fail, bytes_in, "ok" if fail == 0 else "partial"))
    conn.commit()
    conn.close()
    update_summary()
    print(f"[ingest] {mode}: 扫描 {seen} / 新增 {new} / 更新 {upd} / 解析失败 {fail} / {dur:.1f}s")
    return 0 if fail * 200 < max(seen, 1) else 1


def src_of(rel: str) -> str:
    """从文件名 <date>_<label>_<title>_<short>.txt 反解源标签 → src_name（供统计）"""
    base = os.path.basename(rel)
    parts = base.split("_")
    label = parts[1] if len(parts) > 1 else ""
    for k, v in LABEL2SRC.items():
        if label == k:
            return v
    return label or "unknown"


LABEL2SRC = {
    "金斧头": "zsxq_jinfutou", "逻辑与思考": "zsxq_logic", "树枝报告": "zsxq_shuzhi",
    "观澜台": "zsxq_guanlantai", "180KResearch": "zsxq_180kresearch",
    "Vito行研札记": "zsxq_vito", "智堡Wisburg": "gmail_wisburg",
}


def cmd_rebuild_fts():
    conn = db_open()
    t0 = time.time()
    conn.execute("INSERT INTO items_fts(items_fts) VALUES('rebuild')")
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM items_fts").fetchone()[0]
    conn.close()
    print(f"[fts] rebuild 完成：{n} 行 / {time.time()-t0:.1f}s")
    return 0


def cmd_audit_db():
    conn = db_open(create=False)
    checks = {}
    checks["items"] = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    checks["dates"] = conn.execute("SELECT COUNT(DISTINCT date) FROM items").fetchone()[0]
    checks["chars"] = conn.execute("SELECT IFNULL(SUM(chars),0) FROM items").fetchone()[0]
    checks["dup_fid"] = conn.execute(
        "SELECT COUNT(*) FROM (SELECT fid FROM items GROUP BY fid HAVING COUNT(*)>1)").fetchone()[0]
    checks["fts"] = conn.execute("SELECT COUNT(*) FROM items_fts").fetchone()[0]
    checks["rewritten"] = conn.execute("SELECT COUNT(*) FROM items WHERE rewritten=1").fetchone()[0]
    print("=== DB 体检 ===")
    for k, v in checks.items():
        print(f"  {k:10}: {v}")
    conn.close()
    ok = checks["items"] == checks["fts"]
    if checks["dup_fid"]:
        print(f"  注：fid 撞号 {checks['dup_fid']} 组属历史遗留（原 next_fid 只认 3 位），"
              f"已修，存量文件名不改；manifest 以 iid 为准")
    print("判定:", "✅" if ok else "⚠️ items≠fts（FTS 未同步）")
    return 0 if ok else 1


def cmd_reslice():
    """用「磁盘文件 + DB 行」重建全部日片与 manifest（only-missing 补数据后收口用）"""
    conn = db_open(create=False)
    n = 0
    for date in date_dirs():
        rows = conn.execute(
            """SELECT iid,fid,src_name,category,title,chars,bytes,sha256,file,published_at
               FROM items WHERE date=? ORDER BY iid""", (date,)).fetchall()
        ok, sz, sha = write_slice(date)
        if not ok:
            continue
        write_manifest(date, [tuple(r) for r in rows], (ok, sz, sha))
        n += 1
        print(f"  {date}: {len(rows)} 条 / {sz/1e6:.2f} MB")
    conn.close()
    s = update_summary()
    print(f"[reslice] {n} 天 ｜ summary total={s['total_items']}")
    return 0


def cmd_enrich_from_db():
    """用 DB 里已有的 iid/category/chars/bytes/sha256 反哺 index.json（不重读文件，~2s）"""
    conn = db_open(create=False)
    rows = conn.execute("SELECT file,iid,category,chars,bytes,sha256 FROM items").fetchall()
    conn.close()
    mapping = {r["file"]: {"iid": r["iid"], "category": r["category"], "chars": r["chars"],
                           "bytes": r["bytes"], "sha256": r["sha256"]} for r in rows}
    n = enrich_index(mapping)
    print(f"[enrich] 从 DB 反哺 {n} 行（DB {len(mapping)} 条）")
    return 0


def cmd_refresh_summary():
    s = update_summary()
    print(f"[summary] total={s['total_items']} latest={s['latest_date']} slices={s['slice_days']}")
    return 0


def cmd_dups():
    conn = db_open(create=False)
    rows = conn.execute("""SELECT iid, COUNT(*) n, GROUP_CONCAT(file, ' | ') FROM items
                           GROUP BY iid HAVING n>1 ORDER BY n DESC LIMIT 10""").fetchall()
    print(f"[dups] 同 iid 多行 {len(rows)} 组（应为 0；>0 表示上游同 id 被写成多个文件）")
    for r in rows:
        print(f"  {r[0]} x{r[1]}: {r[2][:160]}")
    conn.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description="mahoro 私有库入库器")
    ap.add_argument("--dedupe-index", action="store_true", help="清洗 index.json 重复行（按 file 归组）")
    ap.add_argument("--audit-files", action="store_true", help="只读体检：索引 vs 磁盘 vs iid")
    ap.add_argument("--audit-db", action="store_true", help="只读体检：DB 三方一致")
    ap.add_argument("--backfill", action="store_true", help="全量回填（全部日期目录）")
    ap.add_argument("--day", default="", help="单日 YYYY-MM-DD")
    ap.add_argument("--since", default="", help="起始日 YYYY-MM-DD")
    ap.add_argument("--rebuild-fts", action="store_true")
    ap.add_argument("--enrich-index", action="store_true", help="用 DB 反哺 index.json（iid/sha 等）")
    ap.add_argument("--reslice", action="store_true", help="从磁盘+DB 重建全部日片与 manifest")
    ap.add_argument("--refresh-summary", action="store_true", help="刷新 manifest/summary.json")
    ap.add_argument("--dups", action="store_true", help="列出同 iid 多行组")
    ap.add_argument("--workers", type=int, default=1, help="保留参数（读文件为 per-open 延迟，暂单进程）")
    ap.add_argument("--no-slice", action="store_true", help="不生成日片/manifest")
    ap.add_argument("--only-missing", action="store_true", help="只处理 DB 里还没有的文件")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in (DB, SLICES, MANIFEST_DIR, LOGS):
        assert_private_path(p)

    if args.dedupe_index:
        return cmd_dedupe_index(args.dry_run)
    if args.audit_files:
        return cmd_audit_files()
    if args.audit_db:
        return cmd_audit_db()
    if args.rebuild_fts:
        return cmd_rebuild_fts()
    if args.enrich_index:
        return cmd_enrich_from_db()
    if args.reslice:
        return cmd_reslice()
    if args.refresh_summary:
        return cmd_refresh_summary()
    if args.dups:
        return cmd_dups()

    days = date_dirs()
    if args.day:
        days = [args.day]
    elif args.since:
        days = [d for d in days if d >= args.since]
    elif not args.backfill:
        # 默认：最近 2 个有文件目录（夜间增量）
        days = days[-2:]

    if args.dry_run:
        total = sum(len(glob.glob(os.path.join(RAW, d, "*.txt"))) for d in days)
        print(f"[dry] 将处理 {len(days)} 天 / {total} 篇：{days[:3]}…{days[-1:]}")
        return 0

    mode = "backfill" if args.backfill else ("day" if args.day else "incr")
    return cmd_ingest(days, mode, args.no_slice, args.workers, only_missing=args.only_missing)


if __name__ == "__main__":
    sys.exit(main())
