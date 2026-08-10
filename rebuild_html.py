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
import os
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
today = datetime.now().strftime('%Y-%m-%d')
html = html.replace(
    '兜金观测 — 量化信号池 v',
    f'兜金观测 — 量化信号池 v{today}'
)

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
