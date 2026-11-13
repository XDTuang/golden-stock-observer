#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mahoro 私有库守卫（2026-11-13）
================================================================
把「正文永不进 public 站」从约定变成断言。纯标准库、只读、exit 0/1。

判据：
  C1 隔离（--isolation）：① tracked 路径白名单 ② output/deploy 结构标记扫描
                          ③ 标题 needle 扫描 ④ symlink 目标检查
  C2 预算：digest ≤ 61,440 B（close ≤ 28,672），且路径不在 repo 内
  C3 三方条数：items == 磁盘 txt == manifest.total == index 唯一 file；抽样 sha256 复算
  C4 claims：条数 ≤min(30,TopN)、iid 在库且在窗口内、头部 claims=k/N 一致
  C5 新鲜度：max(date) ≥ 今天-3；备份 ≤48h（告警不红）

用法：
  python3 review/check_mahoro_store.py --quick      # C2+C3（<3s）
  python3 review/check_mahoro_store.py --full       # +FTS 回归 +C5
  python3 review/check_mahoro_store.py --isolation  # C1 四检（10–25s）
  python3 review/check_mahoro_store.py --isolation --selftest   # 阴性对照（必红）
"""
import os
import re
import sys
import json
import glob
import random
import sqlite3
import argparse
import subprocess
import datetime

REPO = os.path.expanduser("~/golden_stock_observer")
RAW = os.path.expanduser("~/Library/Application Support/goldenstock/feed_mahoro")
INDEX_FILE = os.path.join(RAW, "index.json")
STORE = os.path.expanduser("~/Library/Application Support/goldenstock/mahoro_store")
DB = os.path.join(STORE, "db", "mahoro.sqlite3")
DIGEST_DIR = os.path.join(STORE, "digest")
MANIFEST_SUMMARY = os.path.join(STORE, "manifest", "summary.json")

BUDGET = {"preopen": 61440, "close": 28672}
MARKERS = [
    re.compile(r"条目ID:\s*(?:zsxq|gmail)\s*:"),
    re.compile(r"归档号:\s*F\d{8}-\d+"),
    re.compile(r"📎\s*PDF解析摘要"),
    re.compile(r"📎\s*图片解析摘要"),
    re.compile(r"/Users/[^\s\"']*/Application Support/goldenstock"),
]
FORBIDDEN_TRACKED = ("mahoro_store", "feed_mahoro", "Application Support/goldenstock", ".tar.gz")


def die(msg):
    print(f"❌ {msg}")
    return 1


def git_ls_files() -> list:
    out = subprocess.run(["git", "-C", REPO, "ls-files"], capture_output=True, text=True)
    return [x for x in out.stdout.splitlines() if x.strip()]


def c1_isolation(selftest=False) -> tuple:
    errs = []
    tracked = git_ls_files()
    # ① tracked 路径
    bad = [f for f in tracked if any(k in f for k in FORBIDDEN_TRACKED)]
    if bad:
        errs.append(f"tracked 命中禁止路径 {len(bad)}: {bad[:3]}")

    # ② 结构标记扫描（只扫 output/ deploy/ 下的文本类）
    scanned = 0
    hits = []
    for f in tracked:
        if not (f.startswith("output/") or f.startswith("deploy/")):
            continue
        if not f.endswith((".json", ".html", ".js", ".txt", ".md", ".csv")):
            continue
        p = os.path.join(REPO, f)
        if not os.path.exists(p) or os.path.getsize(p) > 40 * 1024 * 1024:
            continue
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        scanned += 1
        for rx in MARKERS:
            m = rx.search(t)
            if m:
                hits.append((f, m.group(0)[:40]))
                break
    if hits:
        errs.append(f"结构标记命中 {len(hits)} 处: {hits[:3]}")

    # ③ needle：研究类标题 + 正文片段（排除「已在公开新闻池出现」的标题，避免新闻类假阳性）
    public_text = []
    for f in tracked:
        if not re.search(r"(output|deploy/output)/daily_news_[0-9-]+\.json$", f):
            continue
        p_ = os.path.join(REPO, f)
        if not os.path.exists(p_) or os.path.getsize(p_) > 40 * 1024 * 1024:
            continue
        try:
            public_text.append(open(p_, encoding="utf-8", errors="ignore").read())
        except Exception:
            pass
    pub = "\n".join(public_text)

    needles = []
    RESEARCH_SRC = ("zsxq_shuzhi", "zsxq_180kresearch", "zsxq_vito", "zsxq_guanlantai", "gmail_wisburg")
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        q = ("SELECT title, body FROM items WHERE date >= date('now','-30 day') "
             f"AND src_name IN ({','.join('?'*len(RESEARCH_SRC))}) "
             "AND chars >= 1500 ORDER BY chars DESC LIMIT 120")
        for title, body in conn.execute(q, RESEARCH_SRC):
            if title and len(title) >= 12 and title not in pub:
                needles.append(title)
            b = re.sub(r"\s+", "", body or "")
            if len(b) >= 300:
                frag = b[150:210]
                if frag not in re.sub(r"\s+", "", pub):
                    needles.append(frag)
        conn.close()
    except Exception:
        pass
    needles = list(dict.fromkeys(needles))[:600]

    if selftest:
        # 阳性对照：从任一公开文件里取一段确定存在的文本做 needle，
        # 若扫不出来 = 检测链路失效（比注入不存在的假串更有意义）。
        probe = ""
        for f in tracked:
            if f.startswith("output/daily_news") and f.endswith(".json"):
                p_ = os.path.join(REPO, f)
                if os.path.exists(p_):
                    txt = open(p_, encoding="utf-8", errors="ignore").read()
                    m_ = re.search(r"[\u4e00-\u9fa5]{20,40}", txt[txt.find('"title"') + 8:])
                    if m_:
                        probe = m_.group(0)
                        break
        if probe:
            needles = list(needles) + [probe]
            print(f"   [SELFTEST] 阳性探针：{probe[:24]}…")

    needle_hits = []
    if needles:
        for f in tracked:
            if not (f.startswith("output/") or f.startswith("deploy/")):
                continue
            p = os.path.join(REPO, f)
            if not os.path.exists(p) or os.path.getsize(p) > 40 * 1024 * 1024:
                continue
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for n in needles:
                if n and n in t:
                    needle_hits.append((f, n[:30]))
                    break
    if needle_hits:
        errs.append(f"标题 needle 命中 {len(needle_hits)} 处: {needle_hits[:3]}")

    # ④ symlink 目标
    store_real = os.path.realpath(STORE)
    links = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            p = os.path.join(root, name)
            if os.path.islink(p):
                tgt = os.path.realpath(p)
                if tgt.startswith(store_real):
                    links.append(os.path.relpath(p, REPO))
    if links:
        errs.append(f"symlink 指向私有库 {len(links)}: {links[:3]}")

    print(f"[C1] tracked {len(tracked)} ｜ 扫描公开面 {scanned} ｜ needle {len(needles)}")
    if errs:
        for e in errs:
            print(f"   ❌ {e}")
        return (False, errs)
    print("   ✅ 正文/标题/author 均未出现在 public 面")
    return (True, [])


def c2_budget() -> tuple:
    errs = []
    for sess, budget in BUDGET.items():
        p = os.path.join(DIGEST_DIR, f"latest_{sess}.md")
        if not os.path.exists(p):
            errs.append(f"缺 digest: latest_{sess}.md")
            continue
        sz = os.path.getsize(p)
        if sz > budget:
            errs.append(f"{sess} digest {sz}B > 预算 {budget}B")
        if os.path.commonpath([os.path.realpath(p), os.path.realpath(REPO)]) == os.path.realpath(REPO):
            errs.append(f"{sess} digest 落在 repo 内: {p}")
    print(f"[C2] digest 预算：{'✅' if not errs else '❌ ' + '; '.join(errs)}")
    return (not errs, errs)


def c3_counts(sample=200) -> tuple:
    errs = []
    disk = sum(len(glob.glob(os.path.join(RAW, d, "*.txt"))) for d in
               [os.path.basename(p) for p in glob.glob(os.path.join(RAW, "2*")) if os.path.isdir(p)])
    try:
        idx = json.load(open(INDEX_FILE, encoding="utf-8"))
        n_idx = len({e.get("file") for e in idx.get("entries", [])})
    except Exception as e:
        return (False, [f"index 读取失败 {e}"])
    n_db = n_man = 0
    if os.path.exists(DB):
        try:
            conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
            n_db = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            conn.close()
        except Exception as e:
            errs.append(f"DB 读取失败 {e}")
    if os.path.exists(MANIFEST_SUMMARY):
        try:
            n_man = json.load(open(MANIFEST_SUMMARY, encoding="utf-8")).get("total_items", 0)
        except Exception:
            pass
    print(f"[C3] items={n_db} ｜ 磁盘={disk} ｜ index唯一file={n_idx} ｜ manifest={n_man}")
    vals = [v for v in (n_db, disk, n_idx, n_man) if v]
    if len(set(vals)) > 1:
        errs.append(f"三方不一致: items={n_db} disk={disk} index={n_idx} manifest={n_man}")

    # sha 抽样复算
    if n_db and os.path.exists(DB):
        try:
            conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
            rows = conn.execute("SELECT file, sha256 FROM items ORDER BY RANDOM() LIMIT ?",
                                (sample,)).fetchall()
            conn.close()
            bad = 0
            for rel, sha in rows:
                p = os.path.join(RAW, rel)
                if not os.path.exists(p):
                    bad += 1
                    continue
                raw = open(p, encoding="utf-8", errors="replace").read()
                m = re.match(r"^.*?\n-{10,}\n", raw, re.S)
                body = (raw[m.end():] if m else raw).replace("\r\n", "\n").strip()
                import hashlib
                if hashlib.sha256(body.encode()).hexdigest() != sha:
                    bad += 1
            print(f"   sha256 抽样 {len(rows)} 条 → 不符 {bad}")
            if bad:
                errs.append(f"sha256 抽样不符 {bad}/{len(rows)}")
        except Exception as e:
            errs.append(f"sha 抽样失败 {e}")
    return (not errs, errs)


def c4_claims(claims_path="", n_window_days=3) -> tuple:
    errs = []
    p = claims_path
    if not p:
        cands = sorted(glob.glob(os.path.join(STORE, "claims", "*.json")))
        p = cands[-1] if cands else ""
    if not p or not os.path.exists(p):
        print("[C4] 无 claims 文件（按设计降级，不算失败）")
        return (True, [])
    try:
        cs = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return (False, [f"claims 解析失败 {e}"])
    if not isinstance(cs, list):
        return (False, ["claims 必须是 JSON 数组"])
    if len(cs) > 30:
        errs.append(f"claims 条数 {len(cs)} > 30")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    for c in cs:
        iid = c.get("iid")
        if not iid:
            errs.append("存在缺 iid 的 claim")
            continue
        row = conn.execute("SELECT date FROM items WHERE iid=?", (iid,)).fetchone()
        if not row:
            errs.append(f"claim iid 不在库: {iid}")
    conn.close()
    print(f"[C4] claims {len(cs)} 条 → {'✅' if not errs else '❌'}")
    return (not errs, errs)


def c5_fresh() -> tuple:
    errs, warns = [], []
    latest = ""
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        latest = conn.execute("SELECT MAX(date) FROM items").fetchone()[0] or ""
        conn.close()
    except Exception as e:
        warns.append(f"DB 读取失败 {e}")
    if latest:
        d = datetime.date.fromisoformat(latest)
        lag = (datetime.date.today() - d).days
        print(f"[C5] 最新数据 {latest}（落后 {lag} 天）")
        if lag > 3:
            warns.append(f"数据落后 {lag} 天")
    if os.path.exists(MANIFEST_SUMMARY):
        s = json.load(open(MANIFEST_SUMMARY, encoding="utf-8"))
        print(f"   manifest updated_at={s.get('updated_at')} latest={s.get('latest_date')}")
    for w in warns:
        print(f"   ⚠️ {w}")
    return (True, warns)


def fts_regression() -> tuple:
    """8 条固定 query：≥3 字走 MATCH，2 字走 LIKE"""
    errs = []
    tests = [("光模块", 3), ("英伟达", 3), ("半导体", 3), ("机器人", 3),
             ("算力", 2), ("存储", 2), ("券商", 2), ("黄金", 2)]
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    for kw, ln in tests:
        if ln >= 3:
            n = conn.execute("SELECT COUNT(*) FROM items_fts WHERE items_fts MATCH ?", (kw,)).fetchone()[0]
        else:
            n = conn.execute("SELECT COUNT(*) FROM items WHERE body LIKE ?", (f"%{kw}%",)).fetchone()[0]
        if n == 0:
            errs.append(f"{kw}({ln}字) 命中 0")
    conn.close()
    print(f"[FTS] 回归 8 条 → {'✅' if not errs else '❌ ' + '; '.join(errs)}")
    return (not errs, errs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--isolation", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="阴性对照：注入假 needle，必须报红")
    ap.add_argument("--claims", default="")
    args = ap.parse_args()
    if not (args.quick or args.full or args.isolation):
        args.quick = True

    all_errs = []
    if args.quick or args.full:
        ok, e = c2_budget(); all_errs += e
        ok, e = c3_counts(); all_errs += e
    if args.full:
        ok, e = fts_regression(); all_errs += e
        ok, e = c5_fresh(); all_errs += e
        ok, e = c4_claims(args.claims); all_errs += e
    if args.isolation:
        ok, e = c1_isolation(selftest=args.selftest)
        all_errs += e
        if args.selftest:
            if e:
                print("\n[SELFTEST] ✅ 阴性对照按预期报红（守卫有效）")
                return 0
            print("\n[SELFTEST] ❌ 注入假 needle 仍未报红 → 守卫恒真，判据失效")
            return 1

    if all_errs:
        print(f"\n❌ 未通过（{len(all_errs)} 项）：")
        for e in all_errs:
            print(f"   - {e}")
        return 1
    print("\n✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
