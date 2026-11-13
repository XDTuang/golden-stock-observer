#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mahoro 私有库检索器（2026-11-13）—— 只读，供推演按需回查
================================================================
设计约束：**输出必须小**。单篇默认截 2400 字节（≈3KB），并标注「截取 x/y 字」，
避免 agent 误把片段当全文；关键词检索只给摘要行（snippet 32 字），要细节再 --id。

用法
----
  python3 feed/mahoro_query.py --id zsxq:45548254451584858 [--bytes 2400]
  python3 feed/mahoro_query.py --id F20261113-091
  python3 feed/mahoro_query.py --kw 光模块 [--days 3] [--src zsxq_shuzhi] [--limit 20]
  python3 feed/mahoro_query.py --date 2026-11-13 [--limit 50]
  python3 feed/mahoro_query.py --ticker 300308 [--days 30]
  python3 feed/mahoro_query.py --slots 30 [--slot-bytes 2500] [--days 2]   # 给 21:10 提要档
  python3 feed/mahoro_query.py --stats

退出码：0 有结果 / 1 无结果
"""
import os
import re
import sys
import json
import math
import sqlite3
import argparse
import datetime

STORE = os.path.expanduser("~/Library/Application Support/goldenstock/mahoro_store")
DB = os.path.join(STORE, "db", "mahoro.sqlite3")
SRC_LABEL = {
    "gmail_wisburg": "智堡", "zsxq_180kresearch": "180K", "zsxq_vito": "Vito",
    "zsxq_guanlantai": "观澜台", "zsxq_shuzhi": "树枝", "zsxq_logic": "逻辑",
    "zsxq_jinfutou": "金斧头",
}
SRC_W = {"gmail_wisburg": 2.2, "zsxq_180kresearch": 2.0, "zsxq_vito": 1.9,
         "zsxq_guanlantai": 1.7, "zsxq_shuzhi": 1.5, "zsxq_logic": 1.2, "zsxq_jinfutou": 1.0}


def conn_ro():
    if not os.path.exists(DB):
        sys.exit("❌ 私有库不存在：先跑 feed/mahoro_ingest.py --backfill")
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=20)


def q_id(c, key, nbytes):
    row = c.execute("""SELECT iid,fid,date,src_name,category,title,url,chars,published_at,body
                       FROM items WHERE iid=? OR fid=? LIMIT 1""", (key, key)).fetchone()
    if not row:
        return None
    iid, fid, date, src, cat, title, url, chars, pub, body = row
    # 按字节截取：默认从头 2400B；若给了 --at-kw 则居中
    raw = body.encode("utf-8")
    cut = raw[:nbytes]
    while cut and (cut[-1] & 0xC0) == 0x80:      # 避免切碎多字节
        cut = cut[:-1]
    frag = cut.decode("utf-8", errors="ignore")
    out = [
        f"[{fid}] {title}",
        f"源={SRC_LABEL.get(src, src)} ｜ 发布={pub} ｜ 分类={cat or '-'} ｜ 全文字数={chars}",
        f"iid={iid}",
        f"--- 片段（前 {len(frag)} / {chars} 字）---",
        frag,
    ]
    if chars > len(frag):
        out.append(f"...（已截断，需更长用 --bytes {min(nbytes*2, 20000)}；全文仅在本机库）")
    return "\n".join(out)


def q_kw(c, kw, days, src, limit):
    d0 = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    if len(kw) >= 3:
        sql = """SELECT i.iid,i.fid,i.date,i.src_name,i.title,i.chars,
                        snippet(items_fts,1,'«','»','…',32)
                 FROM items_fts JOIN items i ON i.rowid=items_fts.rowid
                 WHERE items_fts MATCH ? AND i.date>=? AND (?='' OR i.src_name=?)
                   AND instr(i.body,?)>0
                 ORDER BY i.date DESC LIMIT ?"""
        rows = c.execute(sql, (kw, d0, src, src, kw, limit)).fetchall()
    else:
        sql = """SELECT iid,fid,date,src_name,title,chars,
                        substr(body, max(1, instr(body,?) - 40), 90)
                 FROM items WHERE date>=? AND (?='' OR src_name=?) AND body LIKE ?
                 ORDER BY date DESC, chars DESC LIMIT ?"""
        rows = c.execute(sql, (kw, d0, src, src, f"%{kw}%", limit)).fetchall()
    if not rows:
        return []
    out = [f"命中 {len(rows)} 条（{kw} / 近 {days} 天）"]
    for iid, fid, d, s, t, ch, snip in rows:
        snip_clean = re.sub(r"\s+", " ", snip or "")[:80]
        out.append(f"  {fid} | {d} | {SRC_LABEL.get(s, s)} | {ch}字 | {t[:40]}\n"
                   f"     …{snip_clean}…  id={iid}")
    out.append(f"\n（看全文片段：--id <iid> --bytes 2400）")
    return out


def q_date(c, d, limit):
    rows = c.execute("""SELECT iid,fid,src_name,title,chars FROM items WHERE date=?
                        ORDER BY chars DESC LIMIT ?""", (d, limit)).fetchall()
    return [f"{fid} | {SRC_LABEL.get(s, s)} | {ch}字 | {t[:48]} | id={iid}"
            for iid, fid, s, t, ch in rows]


def q_ticker(c, tk, days):
    d0 = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    rows = c.execute("""SELECT iid,fid,date,src_name,title,chars FROM items
                        WHERE date>=? AND (title LIKE ? OR body LIKE ?)
                        ORDER BY date DESC LIMIT 30""", (d0, f"%{tk}%", f"%{tk}%")).fetchall()
    return [f"{fid} | {d} | {SRC_LABEL.get(s, s)} | {ch}字 | {t[:44]} | id={iid}"
            for iid, fid, d, s, t, ch in rows]


def q_slots(c, n, slot_bytes, days):
    """给 21:10 提要档：按 score 取前 N 条，每条给「头部 + 正文前 slot_bytes」"""
    d0 = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    rows = c.execute("""SELECT iid,fid,date,src_name,category,title,chars,published_at,body
                        FROM items WHERE date>=? """, (d0,)).fetchall()
    def score(r):
        iid, fid, d, s, cat, t, ch, pub, body = r
        w = SRC_W.get(s, 1.0)
        len_f = 0.6 + 0.4 * min(1.0, math.log10(1 + max(ch or 0, 1)) / 3.6)
        fresh = 1.0
        try:
            age = (datetime.datetime.now() - datetime.datetime.strptime(pub[:16], "%Y-%m-%d %H:%M")).total_seconds() / 3600
            fresh = 1.0 if age <= 18 else 0.9 ** (age / 24)
        except Exception:
            pass
        return w * len_f * fresh
    rows = sorted(rows, key=score, reverse=True)[:n]
    print(json.dumps([{
        "n": i + 1, "iid": r[0], "fid": r[1], "date": r[2],
        "src": SRC_LABEL.get(r[3], r[3]), "title": r[5], "chars": r[6],
    } for i, r in enumerate(rows)], ensure_ascii=False, indent=1))
    print("\n--- 以下为正文片段（供改写提要，禁摘录原句；每条 ≤%d B）---" % slot_bytes)
    for i, r in enumerate(rows, 1):
        body = (r[8] or "")[:slot_bytes]
        print(f"\n### [{i}] {r[1]} | {SRC_LABEL.get(r[3], r[3])} | {r[6]}字 | {r[5][:50]}")
        print(f"iid={r[0]}")
        print(body)
    return []


def q_stats(c):
    n, ch, dmin, dmax = c.execute(
        "SELECT COUNT(*), IFNULL(SUM(chars),0), MIN(date), MAX(date) FROM items").fetchone()
    print(f"items={n} ｜ 字数={ch/1e4:.1f} 万 ｜ 区间 {dmin} → {dmax}")
    print("分源：")
    for s, nn, cc in c.execute("""SELECT src_name, COUNT(*), SUM(chars) FROM items
                                  GROUP BY src_name ORDER BY COUNT(*) DESC"""):
        print(f"  {SRC_LABEL.get(s, s):8} {nn:>6} 篇 / {cc/1e4:>7.1f} 万字")
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="")
    ap.add_argument("--kw", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--ticker", default="")
    ap.add_argument("--slots", type=int, default=0)
    ap.add_argument("--slot-bytes", type=int, default=2500)
    ap.add_argument("--bytes", type=int, default=2400)
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--src", default="")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    c = conn_ro()
    lines = []
    if args.id:
        s = q_id(c, args.id, args.bytes)
        if not s:
            c.close()
            sys.exit(f"❌ 未找到 {args.id}")
        print(s)
    elif args.kw:
        lines = q_kw(c, args.kw, args.days, args.src, args.limit)
        print("\n".join(lines) if lines else f"（无命中：{args.kw}）")
    elif args.date:
        lines = q_date(c, args.date, args.limit)
        print("\n".join(lines) if lines else f"（{args.date} 无数据）")
    elif args.ticker:
        lines = q_ticker(c, args.ticker, args.days)
        print("\n".join(lines) if lines else f"（{args.ticker} 近 {args.days} 天无命中）")
    elif args.slots:
        q_slots(c, args.slots, args.slot_bytes, args.days)
    elif args.stats:
        q_stats(c)
    else:
        ap.print_help()
    c.close()
    return 0 if (args.id or lines or args.slots) else 1


if __name__ == "__main__":
    sys.exit(main())
