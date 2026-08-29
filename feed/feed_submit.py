#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兜来米金融 · 投喂提交入口（方式 A 目录 / 方式 C 对话 共用）
=========================================================
将一条投喂内容写入 feed_inbox/，命名规范：
    {日期}_{来源}_{标题}.{ext}
    - 日期: YYYY-MM-DD（默认今天）
    - 来源: 对话/研报/观点/文档/新闻/其他（映射为检索标签）
    - 标题: 简短描述（中文/英文均可，自动清洗非法字符）

用法:
  python feed_submit.py --cat 日常 --src 对话 --title "永鼎股份放量" --text "8/26 盘中放量，疑似光模块订单传闻"
  python feed_submit.py --cat 专家 --src 观点 --title "缠论参数建议" --file /path/to/note.md
  python feed_submit.py --cat 日常 --src 研报 --title "光模块景气" --file report.pdf --text "800G 需求上修"
"""
import os, sys, re, json, argparse, shutil, datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(BASE, "feed", "inbox")
CATS = {"日常": "日常投喂", "专家": "专家投喂"}
SRC_MAP = {"对话": "对话", "研报": "研报", "观点": "观点", "文档": "文档", "新闻": "新闻", "其他": "其他"}

def clean_title(t: str) -> str:
    t = re.sub(r'[\\/:*?"<>|\s]+', "_", t.strip())
    return t.strip("_")[:40] or "未命名"


def _extract_text(path: str) -> str:
    """从文本型或 PDF 附件抽取前若干字符作为可检索正文；失败或无可提取内容返回空串。
    目的：feed_submit 正文统一以 .txt 存储，feed_archive 才能提取关键词做全文交叉匹配；
    当 --file 给出而 --text 缺省时，自动抽取避免正文为空导致喂料不可检索。"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".txt", ".md", ".json", ".csv", ".py", ".yaml", ".yml", ".log"):
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read(8000)
        if ext == ".pdf":
            try:
                import PyPDF2
                r = PyPDF2.PdfReader(path)
                return "\n".join((p.extract_text() or "") for p in r.pages)[:8000]
            except Exception:
                return ""
    except Exception:
        return ""
    return ""

def main():
    ap = argparse.ArgumentParser(description="投喂提交入口")
    ap.add_argument("--cat", choices=list(CATS), default="日常", help="类别：日常/专家")
    ap.add_argument("--src", choices=list(SRC_MAP), default="对话", help="来源类型")
    ap.add_argument("--title", required=True, help="标题（简短描述）")
    ap.add_argument("--text", default="", help="文本内容（与 --file 可同时）")
    ap.add_argument("--file", default="", help="附件文件路径（图片/PDF/Excel/文档等）")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y-%m-%d"), help="YYYY-MM-DD")
    args = ap.parse_args()

    sub = CATS[args.cat]
    cat_dir = os.path.join(INBOX, sub)
    os.makedirs(cat_dir, exist_ok=True)

    title = clean_title(args.title)
    src = SRC_MAP[args.src]
    # 正文主体统一用 .txt 存储（便于归档关键词提取与全文交叉匹配）；
    # 原附件保留原始扩展名，命名为 {fname}.att{ext}，由 feed_archive 跳过不入库。
    fname = f"{args.date}_{src}_{title}.txt"
    fpath = os.path.join(cat_dir, fname)

    if os.path.exists(fpath):
        print(f"⚠️  已存在同名投喂：{fpath}，跳过（如需覆盖请手动处理）")
        sys.exit(1)

    body_parts = []
    if args.text:
        body_parts.append(args.text.strip())
    if args.file:
        if not os.path.exists(args.file):
            body_parts.append(f"[附件来源] {args.file}（文件不存在）")
        else:
            att_ext = os.path.splitext(args.file)[1].lower() or ".bin"
            att_path = fpath + ".att" + att_ext
            try:
                shutil.copy2(args.file, att_path)
                if not args.text:
                    # 未给正文时，自动抽取附件文本，避免正文为空不可检索
                    extracted = _extract_text(args.file)
                    if extracted:
                        body_parts.append(extracted)
                body_parts.append(f"[附件来源] {args.file}")
            except Exception as e:
                body_parts.append(f"[附件来源] {args.file}（复制失败: {e}）")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(body_parts).strip() + "\n")

    print(f"✅ 已投喂 [{args.cat}] {args.date} {src}·{title}")
    print(f"   文件: {fpath}")
    print(f"   下一步: 运行 feed_archive.py 自动归档（或等待定时任务）")

if __name__ == "__main__":
    main()
