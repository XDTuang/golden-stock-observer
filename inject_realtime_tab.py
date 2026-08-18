#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 realtime_tab_snippet.html 同步进主站 index.html / index_template.html /
deploy/index.html 的 tab-realtime 内容区（短线信号 tab 之前）。
幂等：导航按钮缺失则插入；tab 内容区已存在则用【最新 snippet】整体替换（支持升级同步）。
用法: python inject_realtime_tab.py [目标文件]  （默认上述三文件）"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = os.path.join(BASE, "realtime_tab_snippet.html")

TARGETS = ["index.html", "index_template.html", os.path.join("deploy", "index.html")]
if len(sys.argv) > 1:
    TARGETS = [sys.argv[1]]

snippet = open(SNIPPET, encoding="utf-8").read()
anchor = "<!-- Tab: 短线信号 -->"
start_marker = "<!-- Tab: 实时盯盘 -->"


def _block():
    return (
        "\n<!-- Tab: 实时盯盘 -->\n"
        '<div class="tab-content" id="tab-realtime">\n'
        + snippet +
        "\n</div>\n\n"
    )


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
    # ② tab 内容区：已存在 → 用最新 snippet 整体替换；不存在 → 在短线信号前插入
    if 'id="tab-realtime"' in idx:
        if start_marker in idx and anchor in idx:
            s = idx.index(start_marker)
            e = idx.index(anchor)
            idx = idx[:s] + _block() + idx[e:]
            changed = True
            print(f"✅ {tname}: 已用最新 snippet 更新 tab 内容区")
        else:
            print(f"⚠️ {tname}: 存在 tab 但缺锚点，跳过内容同步")
    elif anchor in idx:
        idx = idx.replace(anchor, _block() + anchor, 1)
        changed = True
        print(f"✅ {tname}: 已插入 tab 内容区（{len(_block())} 字符）")
    else:
        print(f"⚠️ {tname}: 未找到 tab 锚点，跳过内容注入")
    if changed:
        open(path, "w", encoding="utf-8").write(idx)
