#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 DDB-AUTH-V1 / DDB-ADMIN-V1 注入块迁到 <head> 内（幂等）。

🔴 为什么要迁（2026-11-24 事故）：
   鉴权块原先插在 index.html 第 1802 行附近，而该位置落在
   `<!-- Tab: 实时盯盘 -->`(1601) 与 `<!-- Tab: 短线信号 -->`(2262) 之间 ——
   正是 `inject_realtime_tab.py` 的整段替换区间。于是每次 rebuild 链路
   （slim_signals.py → inject_realtime_tab.py）都会把整个鉴权块（298 行）
   连根删掉，且**不报错**（页面照常打开，只是没登录门槛、数据全空）。
   18:36 那次自动化重建就是这么把三处 index 的鉴权块抹掉的。

   迁移到 <head> 后：注入器只动 tab 区间，永远碰不到它；rebuild_html.py 以
   index_template.html 为源，模板里块在 head → 重建后天然保留。

用法：
   python3 tool/patch_auth_block.py            # 迁移（写盘）
   python3 tool/patch_auth_block.py --check    # 只校验（三处块均在 head 内）
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html")]

START_MARK = "/* ===== DDB-AUTH-V1 START"
END_MARK = "/* ===== DDB-ADMIN-V1 END ===== */"
HEAD_END = "</head>"


def extract_block(html: str) -> tuple[int, int] | None:
    """返回整块（含外层 <script>…</script>）在 html 中的 [s, e) 区间。"""
    if START_MARK not in html or END_MARK not in html:
        return None
    inner_s = html.index(START_MARK)
    # 往前回溯到最近的 <script>
    s = html.rfind("<script", 0, inner_s)
    if s == -1:
        return None
    e = html.index(END_MARK) + len(END_MARK)
    tail = html.find("</script>", e)
    if tail == -1:
        return None
    return s, tail + len("</script>")


def in_head(html: str, pos: int) -> bool:
    he = html.index(HEAD_END) if HEAD_END in html else -1
    return 0 <= pos < he


def migrate_one(path: str, write: bool) -> tuple[bool, str]:
    html = open(path, encoding="utf-8").read()
    span = extract_block(html)
    if span is None:
        return False, "未找到 DDB-AUTH/ADMIN 注入块"
    s, e = span
    if in_head(html, s):
        return True, "已在 <head> 内（免改）"
    if HEAD_END not in html:
        return False, "未找到 </head>，无法迁移"

    block = html[s:e]
    removed = html[:s] + html[e:]
    # 移除后重新定位 </head>（位置可能前移）
    he = removed.index(HEAD_END)
    new = removed[:he].rstrip("\n") + "\n" + block + "\n" + removed[he:]

    if not write:
        return True, "可迁移（未写盘）"
    open(path, "w", encoding="utf-8").write(new)
    return True, "已迁入 <head>"


def main() -> int:
    check = "--check" in sys.argv
    ok_all = True
    for t in TARGETS:
        p = os.path.join(BASE, t)
        if not os.path.exists(p):
            print(f"  ⚠️  {t}: 文件不存在，跳过")
            ok_all = False
            continue
        ok, msg = migrate_one(p, write=not check)
        print(f"  {'✅' if ok else '❌'} {t}: {msg}")
        ok_all = ok_all and ok

    if check and ok_all:
        # 校验模式额外断言：块确实能提取且位置在 head 内
        for t in TARGETS:
            p = os.path.join(BASE, t)
            if not os.path.exists(p):
                continue
            html = open(p, encoding="utf-8").read()
            span = extract_block(html)
            if span is None or not in_head(html, span[0]):
                print(f"  ❌ {t}: 注入块不在 <head> 内 → 下次 rebuild 会丢失")
                ok_all = False
        print("✅ 三处鉴权块均在 <head> 内，注入器不会触碰" if ok_all else "❌ 校验未通过")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
