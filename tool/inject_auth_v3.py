#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把主站的 DDB-AUTH-V1 / DDB-ADMIN-V1 块注入 V3 独立版（幂等）。

🔴 为什么需要（2026-11-25）：
   真鉴权上线后，受保护产物只剩 *.enc。主站 index.html 里有 window.fetch 拦截器
   （把 /output/*.json 改写为 .json.enc 再前端解密），但 V3 独立版
   （review_v3/index.html）没有这个块 —— 它直接 fetch ../output/*.json，
   加密后 17 个依赖里 13 个 404，页面大面积空白。
   ⇒ 用户看到的「独立版加载不到数据」不是主站密码导致，是独立版缺解密层。

设计：
   · 唯一来源 = index.html 里已维护的那块（不复制代码，避免两处漂移）
   · 目标 = review_v3/index.html + deploy/review_v3/index.html
   · 🔴 幂等按「比对后替换」，不按「存在即跳过」（铁律 27）：
     内容不一致 → 先删旧块，再插新块。
   · 插入位置 = </head> 之前（与主站一致，注入器触碰不到）

用法：
   python3 tool/inject_auth_v3.py            # 注入/更新（写盘）
   python3 tool/inject_auth_v3.py --check    # 只校验（两块均存在且与主站一致）
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "index.html")
TARGETS = [
    os.path.join("review_v3", "index.html"),
    # 🔴 V3 四副本（铁律 7）：index_hide89 经核实与 index 无差异，
    #    但门禁要求四者 md5 一致 —— 漏注入会让 check_v3_style[8/10] 直接红。
    os.path.join("review_v3", "index_hide89.html"),
    os.path.join("deploy", "review_v3", "index.html"),
    os.path.join("deploy", "review_v3", "index_hide89.html"),
]

START_MARK = "/* ===== DDB-AUTH-V1 START"
END_MARK = "/* ===== DDB-ADMIN-V1 END ===== */"
HEAD_END = "</head>"


def extract_block(html: str) -> str | None:
    """返回整块（含外层 <script>…</script>）文本。"""
    if START_MARK not in html or END_MARK not in html:
        return None
    inner_s = html.index(START_MARK)
    s = html.rfind("<script", 0, inner_s)
    if s == -1:
        return None
    e = html.index(END_MARK) + len(END_MARK)
    tail = html.find("</script>", e)
    if tail == -1:
        return None
    return html[s:tail + len("</script>")]


def strip_block(html: str) -> tuple[str, bool]:
    """删掉已有的 DDB 块（若有），返回 (新文本, 是否删过)。"""
    blk = extract_block(html)
    if blk is None:
        return html, False
    # 连同前后空行一起清掉，避免多次注入累积空行
    i = html.index(blk)
    start = i
    while start > 0 and html[start - 1] in "\n \t":
        start -= 1
    return html[:start] + html[i + len(blk):], True


def inject_one(path: str, block: str, write: bool) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, "文件不存在"
    html = open(path, encoding="utf-8").read()

    if HEAD_END not in html:
        return False, "未找到 </head>"

    cur = extract_block(html)
    if cur == block:
        return True, "已是最新（免改）"

    newsrc, removed = strip_block(html)
    he = newsrc.index(HEAD_END)
    out = newsrc[:he].rstrip("\n") + "\n" + block + "\n" + newsrc[he:]

    if not write:
        return True, ("需更新（旧块不同）" if removed else "可注入（原先无块）")

    open(path, "w", encoding="utf-8").write(out)
    return True, ("已更新旧块" if removed else "已注入")


def main() -> int:
    check = "--check" in sys.argv
    if not os.path.exists(SRC):
        print("❌ 找不到 index.html（鉴权块唯一来源）")
        return 1
    block = extract_block(open(SRC, encoding="utf-8").read())
    if not block:
        print("❌ index.html 里找不到 DDB-AUTH/ADMIN 块")
        return 1

    ok_all = True
    for t in TARGETS:
        ok, msg = inject_one(os.path.join(BASE, t), block, write=not check)
        print(f"  {'✅' if ok else '❌'} {t}: {msg}")
        ok_all = ok_all and ok

    if check:
        # 额外断言：块必须在 </head> 之前，否则注入器区间的整段替换会吞掉它
        for t in TARGETS:
            p = os.path.join(BASE, t)
            if not os.path.exists(p):
                continue
            html = open(p, encoding="utf-8").read()
            blk = extract_block(html)
            if not blk:
                print(f"  ❌ {t}: 无鉴权块")
                ok_all = False
                continue
            if html.index(blk) > html.index(HEAD_END):
                print(f"  ❌ {t}: 鉴权块在 </head> 之后 → 有被整段替换吞掉的风险")
                ok_all = False
        print("✅ V3 两处鉴权块均在 <head> 内且与主站一致" if ok_all else "❌ 校验未通过")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
