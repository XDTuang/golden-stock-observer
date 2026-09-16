#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新闻池 JS 块（6·新闻整合）统一补丁器 —— 5 处副本的唯一同步入口
==================================================================
背景（2026-09-16）：
  「6·新闻整合」的渲染 JS 在仓库里有 **5 处副本**，必须逐字一致，否则 rebuild 或
  注入器会用旧版覆盖线上新版：

    index.html / index_template.html / deploy/index.html      ← 主站三副本
    daily_review_tab_snippet.js                                ← 注入器读的 JS 源
    inject_daily_review_tab.py                                 ← 注入器内置兜底（远离源文件时用）

  先前靠正则 `/* …6·新闻整合.*?\\n}\\n` 定位，**一旦新代码内部出现 `\\n}\\n` 就会提前截断**
  （本次新闻池改造正踩中：新函数 drMoreNews 的结束行即 `}`）→ 替换只覆盖前半段且不再幂等。
  现改为**显式块标记**定位：

    /* ═══ NEWS-POOL-BEGIN ═══ */ … /* ═══ NEWS-POOL-END ═══ */

  本脚本把 `review/news_pool_block.js`（唯一权威源）整段刷进上述 5 处。

用法：
  python3 review/patch_news_pool.py            # 打补丁（首次会自动补上块标记）
  python3 review/patch_news_pool.py --check    # 只校验 5 处是否与源一致（CI/门禁用）
  python3 review/patch_news_pool.py --dry-run  # 只打印将改动的文件
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "review", "news_pool_block.js")
TARGETS = [
    "index.html",
    "index_template.html",
    "deploy/index.html",
    "daily_review_tab_snippet.js",
    "inject_daily_review_tab.py",
]
BEGIN = "/* ═══ NEWS-POOL-BEGIN ═══"
END = "/* ═══ NEWS-POOL-END ═══ */"
# 首次（无标记）时的启发式边界：6·新闻整合注释 → 8·数据自检区注释之前
HEUR = re.compile(r"/\* ═══════ 6·新闻整合[\s\S]*?(?=/\* ═══════ 8·数据自检区)")


def read_src():
    with open(SRC, encoding="utf-8") as f:
        t = f.read()
    if BEGIN not in t or END not in t:
        sys.exit(f"❌ 源文件缺少块标记：{SRC}")
    return t if t.endswith("\n") else t + "\n"


def locate(t):
    """返回 (start, end) 块在文本中的区间；无标记时返回 None。"""
    i, j = t.find(BEGIN), t.find(END)
    if i < 0 or j < 0:
        return None
    return i, j + len(END) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验一致性，不写盘")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = read_src()
    src_md5 = hashlib.md5(src.encode()).hexdigest()[:10]
    print(f"═══ 新闻池块同步（源 review/news_pool_block.js · {len(src)} 字符 · md5 {src_md5}）═══")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bk = os.path.join(BASE, "_backups", f"newspool_patch_{stamp}")
    bad, patched = [], 0

    for rel in TARGETS:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            bad.append(f"{rel} 不存在")
            continue
        with open(p, encoding="utf-8") as f:
            t = f.read()
        loc = locate(t)
        if loc is None:
            m = HEUR.search(t)
            if not m:
                bad.append(f"{rel} 未找到块标记，也未能用启发式边界定位（6·新闻整合 → 8·数据自检区）")
                print(f"  ❌ {rel}")
                continue
            cur = t[m.start():m.end()]
            # 新块紧跟一行空行，保持与后续注释的间距
            new = src + "\n"
            if args.check:
                bad.append(f"{rel} 无块标记（旧格式，需打补丁）")
                print(f"  ⚠️  {rel} 无标记（启发式可定位 {len(cur)} 字符）")
                continue
            print(f"  🔧 {rel} 首补标记：{len(cur)} → {len(new)} 字符")
        else:
            cur = t[loc[0]:loc[1]]
            if cur == src + "\n" or cur == src:
                print(f"  ✅ {rel} 已一致")
                continue
            new = src + "\n"
            if args.check:
                bad.append(f"{rel} 与源不一致（现 {len(cur)} / 源 {len(new)} 字符）")
                print(f"  ❌ {rel} 不一致：{len(cur)} → {len(new)}")
                continue
            print(f"  🔧 {rel} 同步：{len(cur)} → {len(new)} 字符")

        if args.dry_run:
            print("     （dry-run 不落盘）")
            continue
        os.makedirs(bk, exist_ok=True)
        shutil.copy2(p, os.path.join(bk, rel.replace("/", "__")))
        t2 = t[:m.start()] + new + t[m.end():] if loc is None else t[:loc[0]] + new + t[loc[1]:]
        with open(p, "w", encoding="utf-8") as f:
            f.write(t2)
        patched += 1

    if not args.dry_run and patched:
        print(f"\n备份 → {os.path.relpath(bk, BASE)}")
    print(f"\n{'✅' if not bad else '❌'} 新闻池块同步："
          + ("5 处全部一致" if not bad else f"{len(bad)} 处待处理"))
    for b in bad:
        print(f"   · {b}")
    return 1 if bad and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
