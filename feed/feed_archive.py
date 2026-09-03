#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 自动归档引擎（投喂箱 → 按日归档 → 检索索引）
=========================================================
扫描 feed_inbox/{日常投喂,专家投喂} 下所有文件，按命名规范解析：
    {YYYY-MM-DD}_{来源}_{标题}.{ext}
归档到 feed_archive/{YYYY-MM-DD}/，并更新 feed_index.json 检索索引。
已归档文件从 inbox 移除；重复内容自动去重（同日期同标题同来源）。

用法:
  python feed_archive.py             # 归档并更新索引
  python feed_archive.py --dry-run   # 仅预览将归档的文件
  python feed_archive.py --inbox xxx # 指定额外投喂目录
"""
import os, sys, re, json, shutil, datetime, argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(BASE, "feed", "inbox")
ARCHIVE = os.path.join(BASE, "feed", "archive")
INDEX = os.path.join(ARCHIVE, "feed_index.json")
CATS = {"日常投喂": "日常投喂", "专家投喂": "专家投喂"}
SRC_MAP = {"对话": "对话", "研报": "研报", "观点": "观点", "专家": "观点", "文档": "文档", "新闻": "新闻", "其他": "其他"}

NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([^_]+)_(.+?)\.([^.]+)$")


def load_index() -> dict:
    if os.path.exists(INDEX):
        try:
            return json.load(open(INDEX, encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "updated_at": "", "entries": []}


def save_index(idx: dict):
    idx["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs(ARCHIVE, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def parse_name(fname: str):
    m = NAME_RE.match(fname)
    if not m:
        return None
    date, src, title, ext = m.groups()
    src = SRC_MAP.get(src, "其他")
    return {"date": date, "src": src, "title": title, "ext": ext}


def keywords(text: str) -> list:
    # 简单关键词提取：中文 2-6 字词 + 字母数字混合标识（如 800G、300xxx）；
    # 排除纯数字/纯字母单字、来源词等停用词，避免误匹配股票代码
    STOP = {"对话", "研报", "观点", "文档", "新闻", "其他", "专家", "投喂", "关注", "建议", "内容", "今天", "昨日", "当日",
            "跟大家", "汇报", "的情况", "出现", "释放", "拟推出", "的信号", "我们", "你们", "他们", "这个", "那个",
            "可以", "已经", "没有", "就是", "不是", "可能", "如果", "因此", "所以", "而且", "但是", "目前", "后续",
            "整体来看", "受量化", "影响", "属于", "完全", "明显", "进一步", "直接", "反向", "方面", "进行", "通过"}
    toks = re.findall(r"[A-Za-z0-9]{2,}|[一-龥]{2,6}", text or "")
    seen, out = set(), []
    for t in toks:
        if t in STOP or re.fullmatch(r"\d+", t):
            continue
        if t not in seen and t not in out:
            seen.add(t)
            out.append(t)
    return out[:10]


def archive(dry_run=False, extra_inboxes=None):
    idx = load_index()
    existing = {(e["date"], e["source"], e["title"]) for e in idx["entries"]}
    moved = 0

    inboxes = list(CATS.keys())
    if extra_inboxes:
        inboxes += [extra_inboxes]

    for cat in inboxes:
        src_dir = os.path.join(INBOX, cat)
        if not os.path.isdir(src_dir):
            continue
        for fname in sorted(os.listdir(src_dir)):
            fpath = os.path.join(src_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if ".att." in fname:
                # feed_submit 生成的附件副本（xxx.att.pdf 等），非投喂正文，跳过不入库
                print(f"  ⏭️  跳过附件副本（非投喂）: {fname}")
                continue
            info = parse_name(fname)
            if not info:
                print(f"  ⚠️  命名不规范，跳过: {fname}（应为 YYYY-MM-DD_来源_标题.ext）")
                continue
            key = (info["date"], info["src"], info["title"])
            dest_dir = os.path.join(ARCHIVE, info["date"])
            dest = None  # 在生成 new_id / arc_name 后确定

            content = ""
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read(2000)
            except Exception:
                pass

            # ── 归档 ID：F{YYYYMMDD}-{当日序号:03d}（2026-09-03 修复：原用全局总数导致编号错乱）──
            ymd = info["date"].replace("-", "")
            max_seq = 0
            for _e in idx["entries"]:
                if str(_e.get("date", ""))[:10] != info["date"]:
                    continue
                _m = re.match(r"F\d{8}-(\d{3})$", str(_e.get("id", "")))
                if _m:
                    max_seq = max(max_seq, int(_m.group(1)))
            new_id = f"F{ymd}-{max_seq + 1:03d}"
            # 归档文件名统一为 <ID>.<原扩展名>，与 agent 手工归档的 F 编号体系一致
            arc_name = new_id + "." + info["ext"]
            dest = os.path.join(dest_dir, arc_name)

            def make_entry():
                # 二进制附件（PDF/xlsx/图片等）不提取内容关键词，避免乱码词
                kw = keywords(content) if info["ext"] in ("txt", "md") else []
                return {
                    "id": new_id,
                    "date": info["date"],
                    "category": cat,
                    "source": info["src"],
                    "title": info["title"],
                    "file": os.path.join("feed", "archive", info["date"], arc_name),
                    "keywords": kw,
                    "status": "已归档",
                    "archived_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

            if key in existing:
                # 索引已记录 → 去重；若归档文件仍在 inbox 则清理副本
                if os.path.exists(fpath) and not dry_run:
                    os.remove(fpath)
                    print(f"  🧹 已归档副本清理: {fname}")
                else:
                    print(f"  ⏭️  已归档（去重）: {fname}")
                continue
            if os.path.exists(dest):
                # 归档文件已存在但索引缺失（重建索引场景）→ 补录索引并清理 inbox 副本
                if not dry_run:
                    idx["entries"].append(make_entry())
                    os.remove(fpath)
                    print(f"  🔁 补录索引: {fname}")
                else:
                    print(f"  📦 [dry] 补录索引: {fname}")
                moved += 1
                continue

            # 正常归档：inbox → archive/日期/
            if dry_run:
                print(f"  📦 [dry] {fname} → {dest}")
            else:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(fpath, dest)
                idx["entries"].append(make_entry())
                print(f"  ✅ {fname} → archive/{info['date']}/")
            moved += 1

    if not dry_run:
        save_index(idx)
        print(f"\n📇 已归档 {moved} 条，索引总数 {len(idx['entries'])} 条 → {INDEX}")
    else:
        print(f"\n[dry-run] 将归档 {moved} 条")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--inbox", default="", help="额外投喂目录名")
    args = ap.parse_args()
    archive(dry_run=args.dry_run, extra_inboxes=args.inbox or None)
