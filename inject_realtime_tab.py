#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 realtime_tab_snippet.html 注入主站 index.html / index_template.html 的
tab-realtime 内容区（短线信号 tab 之前）。
用法: python inject_realtime_tab.py [目标文件]  （默认 index.html 与 index_template.html）"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(BASE, "realtime_tab_snippet.html")

TARGETS = ["index.html", "index_template.html"]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

snippet = open(SNIPPET, encoding="utf-8").read()
anchor = "<!-- Tab: 短线信号 -->"

for tname in TARGETS:
    path = os.path.join(BASE, tname)
    idx = open(path, encoding="utf-8").read()
    changed = False
    # ① 导航按钮：总览 与 短线信号 之间
    btn_anchor = ('<button class="nav-btn active" data-tab="overview">总览</button>\n'
                  '<button class="nav-btn" data-tab="short">短线信号</button>')
    if 'data-tab="realtime"' not in idx:
        if btn_anchor in idx:
            idx = idx.replace(btn_anchor,
                '<button class="nav-btn active" data-tab="overview">总览</button>\n'
                '<button class="nav-btn" data-tab="realtime">👁 实时盯盘</button>\n'
                '<button class="nav-btn" data-tab="short">短线信号</button>', 1)
            changed = True
            print(f"✅ {tname}: 已插入导航按钮")
        else:
            print(f"⚠️ {tname}: 未找到导航锚点，跳过按钮注入")
    # ② tab 内容区：短线信号 tab 之前
    if 'id="tab-realtime"' not in idx:
        if anchor in idx:
            block = (
                "\n<!-- Tab: 实时盯盘 -->\n"
                '<div class="tab-content" id="tab-realtime">\n'
                + snippet +
                "\n</div>\n\n"
            )
            idx = idx.replace(anchor, block + anchor, 1)
            changed = True
            print(f"✅ {tname}: 已插入 tab 内容区（{len(block)} 字符）")
        else:
            print(f"⚠️ {tname}: 未找到 tab 锚点，跳过内容注入")
    else:
        print(f"ℹ️ {tname}: tab 内容区已存在")
    if changed:
        open(path, "w", encoding="utf-8").write(idx)
