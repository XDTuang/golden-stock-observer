#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mahoro 每日 digest 生成器（2026-11-13）
================================================================
产出「元数据 + 机器抽取」的三段式摘要，供推演整段读入（≤60KB）。
🔴 不含原文段落、不含 author、不写进 public 仓库（写入 ~/Library/.../mahoro_store/digest/）。

三段：
  1 聚合   ：日×源 / 源密度 / 分类 / 标的命中 Top15 / 异常
  2 Top200 ：按 score 排序的清单（源·标题·字数·标签·iid·score）
  3 Top30  ：改写提要槽位（由 21:10 档 agent 写 claims/<date>.json 后合入）

用法：
  python3 feed/build_mahoro_digest.py --session preopen
  python3 feed/build_mahoro_digest.py --session close --compact
  python3 feed/build_mahoro_digest.py --days 2026-11-13,2026-11-14 --out /tmp/x.md
"""
import os
import sys
import json
import math
import glob
import sqlite3
import argparse
import datetime

REPO = os.path.expanduser("~/golden_stock_observer")
RAW = os.path.expanduser("~/Library/Application Support/goldenstock/feed_mahoro")
INDEX_FILE = os.path.join(RAW, "index.json")
STORE = os.path.expanduser("~/Library/Application Support/goldenstock/mahoro_store")
DB = os.path.join(STORE, "db", "mahoro.sqlite3")
DIGEST_DIR = os.path.join(STORE, "digest")
CLAIMS_DIR = os.path.join(STORE, "claims")
LOGS = os.path.join(STORE, "logs")

BUDGET = {"preopen": 61440, "close": 28672}
P90_CHARS = 4038

SRC_W = {
    "gmail_wisburg": 2.2, "zsxq_180kresearch": 2.0, "zsxq_vito": 1.9,
    "zsxq_guanlantai": 1.7, "zsxq_shuzhi": 1.5, "zsxq_logic": 1.2, "zsxq_jinfutou": 1.0,
}
SRC_LABEL = {
    "gmail_wisburg": "智堡", "zsxq_180kresearch": "180K", "zsxq_vito": "Vito",
    "zsxq_guanlantai": "观澜台", "zsxq_shuzhi": "树枝", "zsxq_logic": "逻辑",
    "zsxq_jinfutou": "金斧头",
}
SECTOR_LEX = [
    "光模块", "CPO", "光芯片", "PCB", "铜连接", "液冷", "算力", "IDC", "服务器", "存储",
    "半导体设备", "先进封装", "光刻", "EDA", "国产替代", "机器人", "人形机器人", "减速器",
    "固态电池", "锂电", "钠电", "储能", "光伏", "风电", "核电", "可控核聚变", "电网",
    "创新药", "CXO", "医疗器械", "中药", "疫苗", "脑机接口",
    "军工", "商业航天", "低空经济", "卫星", "船舶", "稀土", "黄金", "铜", "铝", "锂",
    "煤炭", "石油", "天然气", "航运", "港口", "化工", "钢铁", "水泥",
    "券商", "银行", "保险", "地产", "基建", "白酒", "食品", "零售", "养殖", "猪产业",
    "AI应用", "大模型", "数据要素", "信创", "鸿蒙", "消费电子", "折叠屏", "AR", "VR",
]


def assert_private_path(p: str):
    rp = os.path.realpath(REPO)
    ap = os.path.realpath(os.path.abspath(p))
    if os.path.commonpath([ap, rp]) == rp:
        sys.exit(f"❌ 拒绝写入 public 仓库路径: {p}")


def load_watchlist() -> set:
    """持仓/观察池标的（用于 hit_f）。取自项目产物，只读。"""
    names = set()
    for rel, keys in (
        ("output/observation_pool.json", ("name", "code")),
        ("output/golden_pool_meta.json", None),
    ):
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if rel.endswith("observation_pool.json"):
            arr = d if isinstance(d, list) else (d.get("stocks") or d.get("items") or [])
            for s in arr:
                if isinstance(s, dict):
                    for k in ("name", "code"):
                        if s.get(k):
                            names.add(str(s[k]))
        else:
            for g in ("all_a", "sector"):
                for s in ((d.get(g) or {}).get("stocks") or []):
                    for k in ("name", "code"):
                        if s.get(k):
                            names.add(str(s[k]))
    return {n for n in names if n and len(n) >= 2}


def db_rows(days: list, watch: set):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=20)
    conn.row_factory = sqlite3.Row
    q = f"""SELECT iid, fid, date, src_name, category, title, chars, published_at
            FROM items WHERE date IN ({",".join("?"*len(days))})"""
    rows = [dict(r) for r in conn.execute(q, days)]
    # 标签命中（只统计，不取正文）
    hit = {}
    if rows:
        q2 = f"""SELECT iid, SUM(CASE WHEN tag IN ({",".join("?"*len(SECTOR_LEX))}) THEN 1 ELSE 0 END) sec
                 FROM tags WHERE iid IN (SELECT iid FROM items WHERE date IN ({",".join("?"*len(days))}))
                 GROUP BY iid"""
        for r in conn.execute(q2, SECTOR_LEX + days):
            hit[r["iid"]] = {"sec": r["sec"]}
    conn.close()
    for r in rows:
        text = r["title"] or ""
        tags = [k for k in SECTOR_LEX if k in text]
        nh = sum(1 for w in watch if w and w in text)
        r["tags"] = tags
        r["hits"] = {"tk": nh, "sec": len(tags)}
    return rows


def index_rows(days: list, watch: set):
    d = json.load(open(INDEX_FILE, encoding="utf-8"))
    rows = []
    for e in d.get("entries", []):
        if (e.get("date") or "")[:10] in days:
            title = e.get("title") or ""
            rows.append({
                "iid": e.get("iid") or "", "fid": e.get("id"), "date": e.get("date"),
                "src_name": e.get("src_name") or "", "category": e.get("category") or "",
                "title": title, "chars": e.get("chars") or 0,
                "published_at": e.get("published_at") or "",
                "tags": [k for k in SECTOR_LEX if k in title],
                "hits": {"tk": sum(1 for w in watch if w and w in title),
                         "sec": len([k for k in SECTOR_LEX if k in title])},
            })
    return rows


def score(r) -> float:
    src = r["src_name"]
    w = SRC_W.get(src, 1.0)
    len_f = 0.6 + 0.4 * min(1.0, math.log10(1 + max(r["chars"], 1)) / math.log10(1 + P90_CHARS))
    hit_f = 1 + 1.0 * min(3, r["hits"]["tk"]) / 3 + 0.5 * min(3, r["hits"]["sec"]) / 3
    fresh = 1.0
    try:
        age_h = (datetime.datetime.now() -
                 datetime.datetime.strptime(r["published_at"][:16], "%Y-%m-%d %H:%M")).total_seconds() / 3600
        fresh = 1.0 if age_h <= 18 else 0.9 ** (age_h / 24)
    except Exception:
        pass
    return round(w * len_f * hit_f * fresh, 2)


def build(days, session, compact, out_path, claims_path):
    watch = load_watchlist()
    src_used = "db"
    rows = []
    if os.path.exists(DB):
        try:
            rows = db_rows(days, watch)
        except Exception as e:
            print(f"⚠️ DB 读取失败（降级 index）: {e}", file=sys.stderr)
    if not rows:
        src_used = "index"
        try:
            rows = index_rows(days, watch)
        except Exception as e:
            print(f"❌ index 也读取失败: {e}", file=sys.stderr)
            return 2
    for r in rows:
        r["score"] = score(r)

    latest = max((r["date"] for r in rows), default="")
    total_chars = sum(r["chars"] for r in rows)

    # claims
    claims = {}
    cp = claims_path or os.path.join(CLAIMS_DIR, f"{latest}.json")
    if os.path.exists(cp):
        try:
            for c in json.load(open(cp, encoding="utf-8")):
                if c.get("iid") and c.get("claim"):
                    claims[c["iid"]] = c
        except Exception:
            pass

    n_top = 80 if compact else 200
    n_claim = 15 if compact else 30
    top = sorted(rows, key=lambda r: -r["score"])[:n_top]

    L = []
    L.append(f"# mahoro digest · {session} · {'/'.join(days)}")
    L.append(f"generated_at: {datetime.datetime.now():%Y-%m-%d %H:%M} ｜ source: {src_used} ｜ store_latest: {latest}")
    L.append(f"total_items: {len(rows)} ｜ total_chars: {total_chars} ｜ claims: {len(claims)}/{n_claim} ｜ 预算: {BUDGET[session]}B")
    L.append("红线：本文件仅本机；不含正文段落、不含作者；禁复制进 public 仓库或页面\n")

    # ── 1 聚合 ──
    L.append("## 1 聚合（元数据）")
    by_src, by_date = {}, {}
    for r in rows:
        by_src.setdefault(r["src_name"], [0, 0])
        by_src[r["src_name"]][0] += 1
        by_src[r["src_name"]][1] += r["chars"]
        by_date.setdefault(r["date"], [0, 0])
        by_date[r["date"]][0] += 1
        by_date[r["date"]][1] += r["chars"]
    L.append("### 1.1 日 × 源")
    L.append("| 日期 | 篇 | 万字 | " + " | ".join(SRC_LABEL.get(s, s) for s in SRC_W) + " |")
    L.append("|---" * (3 + len(SRC_W)) + "|")
    for d in sorted(by_date):
        cnts = [sum(1 for r in rows if r["date"] == d and r["src_name"] == s) for s in SRC_W]
        L.append(f"| {d} | {by_date[d][0]} | {by_date[d][1]/1e4:.2f} | " + " | ".join(str(c) for c in cnts) + " |")

    L.append("\n### 1.2 源密度（篇 / 均字）")
    for s, (n, ch) in sorted(by_src.items(), key=lambda x: -x[1][0]):
        L.append(f"- {SRC_LABEL.get(s, s)}：{n} 篇 / 均 {ch//max(n,1)} 字")

    L.append("\n### 1.3 分类")
    cat = {}
    for r in rows:
        cat[r["category"] or "-"] = cat.get(r["category"] or "-", 0) + 1
    L.append(" · ".join(f"{k}:{v}" for k, v in sorted(cat.items(), key=lambda x: -x[1])[:8]))

    L.append("\n### 1.4 板块命中 Top15（标题级）")
    tag = {}
    for r in rows:
        for t in r["tags"]:
            tag[t] = tag.get(t, 0) + 1
    L.append(" · ".join(f"{k}×{v}" for k, v in sorted(tag.items(), key=lambda x: -x[1])[:15]) or "（无）")

    L.append("\n### 1.5 异常")
    blank = sum(1 for r in rows if (r["title"] or "").strip() in ("", "【入库卡片】"))
    L.append(f"- 占位标题（【入库卡片】/空）：{blank} 篇")
    L.append(f"- 短于 50 字：{sum(1 for r in rows if r['chars'] < 50)} 篇")
    zeros = [SRC_LABEL.get(s, s) for s in SRC_W if s not in by_src]
    L.append(f"- 当日零供给源：{', '.join(zeros) if zeros else '无'}")

    # ── 2 Top200 ──
    L.append(f"\n## 2 Top{n_top}（score 降序；score = 源权重 × 长度因子 × 命中因子 × 新鲜度）")
    for r in top:
        t = (r["title"] or "").replace("|", "/")[:46]
        tags = ",".join(r["tags"][:3]) or "-"
        L.append(f"{r['fid']} | {r['published_at'][5:16]} | {SRC_LABEL.get(r['src_name'], r['src_name'])} | "
                 f"{r['chars']}字 | {t} | {tags} | id={r['iid']} | s={r['score']}")

    # ── 3 claims ──
    L.append(f"\n## 3 Top{n_claim} 改写提要（禁摘录；缺省时直接看第 2 段）")
    if claims:
        rank = {r["iid"]: i for i, r in enumerate(sorted(rows, key=lambda x: -x["score"]))}
        shown = 0
        for iid, c in sorted(claims.items(), key=lambda x: rank.get(x[0], 9999)):
            if shown >= n_claim:
                break
            tick = "/".join(c.get("tickers") or []) or "-"
            L.append(f"- {c.get('fid','')} 【{SRC_LABEL.get(c.get('src',''), c.get('src',''))}】"
                     f"{c['claim']} · {tick} · {c.get('sector','')}")
            shown += 1
    else:
        L.append("（本轮未生成改写提要；请用第 2 段清单，必要时 --id 回查）")

    L.append("\n## 4 回查")
    L.append("python3 feed/mahoro_query.py --id <iid> --bytes 3000   # 单篇 ≤3KB 片段")
    L.append("python3 feed/mahoro_query.py --kw 光模块 --days 3      # 关键词检索")

    text = "\n".join(L) + "\n"
    b = len(text.encode("utf-8"))
    budget = BUDGET[session]
    if b > budget:
        # 裁剪：从第 2 段尾部逐行删，直到进预算（永不裁第 1 段）
        lines = text.split("\n")
        i2 = next((i for i, x in enumerate(lines) if x.startswith("## 2 ")), None)
        i3 = next((i for i, x in enumerate(lines) if x.startswith("## 3 ")), None)
        while b > budget and i2 is not None and i3 is not None and i3 - i2 > 6:
            i3 -= 1
            del lines[i3]
            text = "\n".join(lines) + "\n"
            b = len(text.encode("utf-8"))
        text = text.replace("## 3 ", "（Top 清单已按预算截断）\n\n## 3 ", 1)

    os.makedirs(DIGEST_DIR, exist_ok=True)
    date_tag = latest or datetime.date.today().isoformat()
    final = out_path or os.path.join(DIGEST_DIR, f"{date_tag}_{session}.md")
    assert_private_path(final)
    tmp = final + ".tmp"
    open(tmp, "w", encoding="utf-8").write(text)
    os.replace(tmp, final)
    latest_link = os.path.join(DIGEST_DIR, f"latest_{session}.md")
    shutil_copy(final, latest_link)

    print(f"[digest] {final} ｜ {len(rows)} 篇/{total_chars/1e4:.1f} 万字 ｜ {b} B (预算 {budget}) "
          f"｜ source={src_used} ｜ claims={len(claims)}")
    return 0 if b <= budget else 1


def shutil_copy(src, dst):
    tmp = dst + ".tmp"
    with open(src, "rb") as a, open(tmp, "wb") as b:
        b.write(a.read())
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=["preopen", "close"], default="preopen")
    ap.add_argument("--days", default="", help="逗号分隔；默认取最近 2 个有数据日")
    ap.add_argument("--compact", action="store_true", help="close 版紧凑（默认 close 自动开）")
    ap.add_argument("--out", default="")
    ap.add_argument("--claims", default="")
    args = ap.parse_args()

    if args.days:
        days = [d.strip() for d in args.days.split(",") if d.strip()]
    else:
        ds = sorted({os.path.basename(p) for p in glob.glob(os.path.join(RAW, "2*")) if os.path.isdir(p)})
        days = ds[-2:] if ds else []
    if not days:
        print("❌ 无日期可用")
        return 2
    compact = args.compact or args.session == "close"
    return build(days, args.session, compact, args.out, args.claims)


if __name__ == "__main__":
    sys.exit(main())
