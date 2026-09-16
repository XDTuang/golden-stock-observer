#!/usr/bin/env python3
"""用已有JSON数据重新生成 index.html（fetch 版：数据由前端异步加载外部 JSON）

加载策略（fetch 版，契合 GitHub Pages 部署模型）：
  - 前端 initPage() 对 window.SIGNALS_DATA 等做存在性守卫，
    无内联数据时自动 fetch 以下外部文件（均由 github_pages_deploy.sh 部署到 Pages 根目录）：
      * signals.json                     （主信号数据，体积最大 ~4.3MB）
      * output/national_team_etf.json   （国家队ETF资金流）
      * output/sector_flow.json         （板块资金流）
      * output/top10_history.json       （TOP10历史）
      * lh_calendar.json                （龙虎榜日历）
  - 这样 index.html 仅含 HTML+JS+CSS（约 212KB），在 GitHub Pages 限速网络下可快速出壳，
    数据异步加载并显示加载状态，避免 4.9MB 内联导致浏览器白屏超时。

注意：本脚本只负责“生成外壳”，不内联任何业务数据；业务数据的抓取/精简/扫描
仍由 fetch_pool.py / golden_diamond_scan.py / slim_signals.py 等固化机制产出。
"""
import json
import os
import re
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE, "index_template.html")
output_html = os.path.join(BASE, "index.html")
deploy_dir = os.path.join(BASE, "deploy")

with open(template_path, 'r', encoding='utf-8') as f:
    html = f.read()

# fetch 版：不内联任何业务数据，全部由前端异步加载外部 JSON
data_loader_comment = (
    "// 数据加载策略：全部由前端通过 fetch() 异步加载外部 JSON\n"
    "//   signals.json / output/*.json / lh_calendar.json 已由部署脚本发布到 Pages 根目录\n"
    "//   initPage()/loadLhbData() 对 window.X 做存在性守卫，无内联时自动 fetch\n"
    "//   这样 index.html 仅为 HTML+JS+CSS 外壳（约 200KB），避免大内联致白屏"
)
html = html.replace('// DATA_PLACEHOLDER', data_loader_comment)

# 更新标题日期
# 2026-09-11 治本：原实现用「不含版本号的旧串」做 str.replace（old='…信号池 v'），
#   模板里已有 v2026-08-29 → 替换后拼成 v2026-09-092026-08-29（线上实测污染）。
#   改用正则整体吃掉旧版本号，保证幂等（重复运行结果恒定）。
today = datetime.now().strftime('%Y-%m-%d')
# 🔴 2026-09-15 治本（铁律 9 同族）：原取「生成日」→ 盘前/非交易日/补跑重跑会把标题
#    写成未来日或非交易日（实测 2026-09-15 09:xx 时标题仍停在 v2026-09-11）。
#    改为锚定「信号池数据日」。
# 🔴 2026-09-16 再治本：原读 `output/signals.json` —— 那是 **slim 的输入（全量中转，~22MB，
#    本机独有）**，其 data_date 会比发布版滞后（实测 09-16 时它仍是 2026-09-14，而发布版
#    root `signals.json` 已是 2026-09-15）→ 标题被锚到过期一天。
#    正确判据 = **发布版 root `signals.json`**（= 前端 fetch 的那份、Pages 根实际加载）；
#    仅当它缺失/无 data_date 时才回退 output/signals.json，最后才回退生成日。
try:
    _dd = ""
    for _cand, _label in ((os.path.join(BASE, "signals.json"), "root 发布版"),
                          (os.path.join(BASE, "output", "signals.json"), "output 全量中转")):
        try:
            _sg = json.load(open(_cand, encoding="utf-8"))
            _v = str(_sg.get("data_date") or "")[:10]
            if len(_v) == 10 and _v[4] == "-":
                _dd = _v
                break
            print(f"  ⚠️  {_label} 的 data_date 非法（{_sg.get('data_date')!r}），继续回退下一源")
        except Exception as _e2:
            print(f"  ⚠️  {_label} 读取失败：{_e2}")
    if _dd:
        if _dd != today:
            print(f"  ℹ️  标题版本号锚定数据日 {_dd}（生成日 {today}）")
        today = _dd
    else:
        raise ValueError("两个 signals.json 均无可用 data_date")
except Exception as _e:
    print(f"  ⚠️  信号池数据日读取失败，标题回退生成日 {today}: {_e}")
html, _n = re.subn(r'(兜金观测 — 量化信号池 v)[\d\-]*', rf'\g<1>{today}', html)
if _n != 1:
    raise SystemExit(f'❌ title 版本号替换命中 {_n} 处（期望 1 处），已中止以免写坏 index.html')

# 🔴 2026-09-16 治本（铁律 2 三处同步）：模板自身也是「三处同步」的成员，但本脚本一直只把
#    index_template.html 当**源**读、从不回写 → 模板标题随日期推进越落越旧
#    （实测 2026-09-16 时 index/deploy 已是 v2026-09-15，模板仍是 v2026-09-14）。
#    一旦走「模板 → index」的直拷路径（非本脚本），标题就会回退一天。
#    故在此把模板标题同步为同一 data_date，保证三处版本号恒等。
try:
    with open(template_path, 'r', encoding='utf-8') as f:
        _tpl = f.read()
    _tpl2, _tn = re.subn(r'(兜金观测 — 量化信号池 v)[\d\-]*', rf'\g<1>{today}', _tpl)
    if _tn != 1:
        print(f'  ⚠️  index_template.html title 替换命中 {_tn} 处（期望 1），跳过模板回写')
    elif _tpl2 != _tpl:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(_tpl2)
        print(f'  ✅ index_template.html 标题已同步至 v{today}')
    else:
        print(f'  ✓ index_template.html 标题已是 v{today}（免改）')
except Exception as _e:
    print(f'  ⚠️  index_template.html 标题回写失败：{_e}')

with open(output_html, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = os.path.getsize(output_html) / 1024
print(f'index.html 已重新生成(fetch版): {output_html} ({size_kb:.0f} KB)')

# 同步到 deploy 目录
if os.path.isdir(deploy_dir):
    deploy_html = os.path.join(deploy_dir, 'index.html')
    with open(deploy_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  已同步到 deploy/index.html ({size_kb:.0f} KB)')
