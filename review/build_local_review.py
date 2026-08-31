#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_local_review.py —— 生成本地自包含每日复盘页（可离线打开、无外部依赖）

数据来源：
  ① 网上实时/收盘：腾讯 gtimg（A股指数/美股盘中/港股）、新浪 znb（日韩）、本地 market.json（商品/汇率/美债）
  ② 本机 output/：sector_flow（板块资金流）、golden_diamond（金钻）、obs_deduce（观测股推演）、feed_review（投喂+推演）
  ③ 本机 feed/archive/YYYY-MM-DD/：当日投喂素材
  ④ 推演结论与回测：本机 agent 产出

用法：python3 review/build_local_review.py [YYYY-MM-DD]   默认今天
输出：/Users/samt/Desktop/兜是宝/每日复盘_YYYYMMDD.html
"""

import json
import os
import subprocess
import sys
from datetime import datetime

BASE = '/Users/samt/golden_stock_observer'
OUT_DIR = '/Users/samt/Desktop/兜是宝'


def load_json(p):
    try:
        with open(os.path.join(BASE, p), encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('  ! load fail %s: %s' % (p, e))
        return {}


def curl_gtimg(codes):
    """腾讯行情：返回 {code: {name, close, prev, chg_pct}}"""
    try:
        raw = subprocess.run(
            ['curl', '-s', '--max-time', '20', 'http://qt.gtimg.cn/q=' + codes],
            capture_output=True, text=True).stdout
        raw = raw.encode('latin-1', 'ignore').decode('gbk', 'ignore')
    except Exception:
        return {}
    out = {}
    for seg in raw.split(';'):
        seg = seg.strip()
        if not seg.startswith('v_'):
            continue
        parts = seg.split('~')
        if len(parts) < 6:
            continue
        try:
            close, prev = float(parts[3]), float(parts[4])
        except Exception:
            continue
        out[parts[2]] = {
            'name': parts[1],
            'close': close,
            'prev': prev,
            'chg_pct': round((close - prev) / prev * 100, 2) if prev else 0,
        }
    return out


def curl_sina(codes):
    """新浪 znb（日韩）"""
    try:
        raw = subprocess.run(
            ['curl', '-s', '--max-time', '20',
             '-H', 'Referer: https://finance.sina.com.cn',
             'http://hq.sinajs.cn/list=' + codes],
            capture_output=True, text=True).stdout
        raw = raw.encode('latin-1', 'ignore').decode('gbk', 'ignore')
    except Exception:
        return {}
    out = {}
    for line in raw.split('\n'):
        if '="' not in line:
            continue
        key = line.split('hq_str_')[1].split('=')[0] if 'hq_str_' in line else ''
        val = line.split('="')[1].rstrip('";') if '="' in line else ''
        f = val.split(',')
        if len(f) < 4:
            continue
        try:
            out[key] = {'name': f[0], 'close': float(f[1]), 'chg_amt': float(f[2]), 'chg_pct': float(f[3])}
        except Exception:
            pass
    return out


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    dnum = date.replace('-', '')
    print('== 生成 %s 本地复盘页 ==' % date)

    # ── 1. 网上数据 ──
    print('[1/5] 拉取网上实时数据…')
    a_idx = curl_gtimg('sh000001,sz399001,sz399006,sh000300,sh000688')
    us_now = curl_gtimg('usDJI,usIXIC,usINX')
    hk_now = curl_gtimg('hkHSI,hkHSTECH')
    asia_now = curl_sina('znb_NKY,znb_KOSPI')

    market = load_json('data/daily_review/market.json')
    comm = market.get('comm', {})

    # ── 2. 本机数据 ──
    print('[2/5] 读取本机 output 数据…')
    sector = load_json('output/sector_flow.json')
    sec_hist = sector.get('history', {})
    sec_latest = sec_hist.get(date, {}).get('sectors', [])
    gd = load_json('output/golden_diamond.json')
    obs = load_json('output/obs_deduce_latest.json')
    fr = load_json('output/feed_review_latest.json')

    # ── 3. 投喂素材 ──
    print('[3/5] 读取当日投喂素材…')
    feeds = []
    arch_dir = os.path.join(BASE, 'feed/archive', date)
    if os.path.isdir(arch_dir):
        for fn in sorted(os.listdir(arch_dir)):
            if not fn.endswith('.txt'):
                continue
            with open(os.path.join(arch_dir, fn), encoding='utf-8') as f:
                lines = f.read().split('\n')
            src = lines[0].replace('来源: ', '').replace('来源PDF: ', '') if lines else ''
            title = lines[1].replace('文件: ', '') if len(lines) > 1 else fn
            body = '\n'.join(lines[3:])[:260]
            feeds.append({'id': fn.replace('.txt', ''), 'src': src, 'title': title, 'snippet': body})

    # ── 4. 板块 TOP/BOTTOM ──
    print('[4/5] 整理板块资金流…')
    sec_sorted = sorted(sec_latest, key=lambda x: x.get('main_net_flow') or 0, reverse=True)
    sec_top = sec_sorted[:8]
    sec_bottom = sec_sorted[-8:][::-1]

    obs_items = obs.get('items', [])[:32]

    # ── 5. 生成 HTML ──
    print('[5/5] 生成 HTML…')
    ai = fr.get('ai_synthesis', {})
    pred = fr.get('prediction', {})
    cross = fr.get('cross_analysis', [])

    def yi(v):
        try:
            return round(float(v) / 1e8, 2)
        except Exception:
            return 0

    # 指数行
    idx_rows = ''
    for code in ['000001', '399001', '399006', '000300', '000688']:
        d = a_idx.get(code)
        if not d:
            continue
        cls = 'up' if d['chg_pct'] >= 0 else 'dn'
        idx_rows += ('<div class="idx"><div class="idx-n">%s</div>'
                     '<div class="idx-v %s">%.2f</div>'
                     '<div class="idx-p %s">%+.2f%%</div></div>') % (
            d['name'], cls, d['close'], cls, d['chg_pct'])

    # 美股盘中
    us_rows = ''
    for code in ['DJI', 'IXIC', 'INX']:
        d = us_now.get(code) or us_now.get('.' + code)
        if not d:
            continue
        cls = 'up' if d['chg_pct'] >= 0 else 'dn'
        us_rows += ('<tr><td>%s</td><td class="num %s">%.2f</td>'
                    '<td class="num %s">%+.2f%%</td><td class="dim">盘中</td></tr>') % (
            d['name'], cls, d['close'], cls, d['chg_pct'])

    # 日韩 / 港股
    asia_rows = ''
    for k, label in [('znb_NKY', '日经225'), ('znb_KOSPI', 'KOSPI')]:
        d = asia_now.get(k)
        if not d:
            continue
        cls = 'up' if d['chg_pct'] >= 0 else 'dn'
        asia_rows += '<tr><td>%s</td><td class="num %s">%.2f</td><td class="num %s">%+.2f%%</td></tr>' % (
            label, cls, d['close'], cls, d['chg_pct'])
    for code in ['HSI', 'HSTECH']:
        d = hk_now.get(code)
        if not d:
            continue
        cls = 'up' if d['chg_pct'] >= 0 else 'dn'
        asia_rows += '<tr><td>%s</td><td class="num %s">%.2f</td><td class="num %s">%+.2f%%</td></tr>' % (
            d['name'], cls, d['close'], cls, d['chg_pct'])

    # 商品
    comm_rows = ''
    for key in ['gold_spot', 'gold_comex', 'wti', 'brent', 'us10y', 'us30y', 'cny']:
        d = comm.get(key)
        if not d:
            continue
        val, pct = d.get('value'), d.get('chg_pct')
        pct_s = ('%+.2f%%' % pct) if pct is not None else '—'
        cls = 'up' if (pct or 0) >= 0 else 'dn'
        if pct is None:
            cls = 'dim'
        comm_rows += '<tr><td>%s</td><td class="num">%s</td><td class="num %s">%s</td></tr>' % (
            d.get('name', key), val, cls, pct_s)

    # 板块
    def sec_rows(lst):
        s = ''
        for it in lst:
            v = yi(it.get('main_net_flow'))
            cls = 'up' if v >= 0 else 'dn'
            s += '<tr><td>%s</td><td class="num %s">%+.2f 亿</td></tr>' % (it.get('name', ''), cls, v)
        return s

    # 金钻
    gd_items = gd.get('items', [])[:12]
    gd_rows = ''
    for it in gd_items:
        gd_rows += '<tr><td><b>%s</b> <span class="dim">%s</span></td><td>%s</td></tr>' % (
            it.get('name', ''), it.get('code', ''), it.get('primary', ''))

    # 观测股
    obs_rows = ''
    for it in obs_items:
        pct = it.get('chg_last')
        try:
            pct = float(pct)
            cls = 'up' if pct >= 0 else 'dn'
            pct_s = '%+.2f%%' % pct
        except Exception:
            cls, pct_s = 'dim', '—'
        obs_rows += ('<tr><td><b>%s</b></td><td class="num">%s</td>'
                     '<td class="num %s">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>') % (
            it.get('name', ''), it.get('close', '—'), cls, pct_s,
            it.get('sector', ''), it.get('trend', ''), it.get('open_label', ''))

    # 投喂素材
    feed_cards = ''
    for fd in feeds:
        feed_cards += ('<div class="feed"><div class="feed-h"><span class="tag">%s</span> %s</div>'
                       '<div class="feed-b dim">%s</div></div>') % (
            fd['src'], fd['title'][:70], fd['snippet'].replace('\n', ' ')[:200])

    # 交叉验证
    cross_html = ''
    for c in cross:
        cross_html += '<li>%s</li>' % c

    # 结论
    concl = ''
    for c in ai.get('conclusion_first', []):
        concl += '<li>%s</li>' % c

    t1 = ''
    for f in pred.get('t1_focus', []):
        t1 += '<li>%s</li>' % f

    risks = ''
    for r in pred.get('risks', []):
        risks += '<li><span class="tag %s">%s 概率 / %s 冲击</span> %s</li>' % (
            'warn' if r.get('prob') == '高' else 'dim', r.get('prob', ''), r.get('impact', ''), r.get('desc', ''))

    # 注意：TEMPLATE 内含大量 CSS 百分号（width:100% 等），
    # 不能用 % 格式化或 str.format（会与 CSS 的 % / {} 冲突），改用逐项 replace。
    ctx = {
        'date': date,
        'dnum': dnum,
        'gen_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'verdict': ai.get('verdict_headline', ''),
        'idx_rows': idx_rows,
        'mkt_stats': MARKET_STATS,
        'us_rows': us_rows,
        'asia_rows': asia_rows,
        'comm_rows': comm_rows,
        'sec_top': sec_rows(sec_top),
        'sec_bottom': sec_rows(sec_bottom),
        'gd_rows': gd_rows,
        'obs_rows': obs_rows,
        'feed_cards': feed_cards,
        'feed_count': len(feeds),
        'cross_html': cross_html,
        'concl': concl,
        't1': t1,
        'risks': risks,
        'bias': pred.get('bias', ''),
        'theme': ai.get('theme_resonance', ''),
        'holding': ai.get('holding_map', ''),
    }
    html = TEMPLATE
    for k, v in ctx.items():
        html = html.replace('%%(%s)s' % k, str(v))

    out_path = os.path.join(OUT_DIR, '每日复盘_%s.html' % dnum)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('✅ 已生成：%s (%d 字节)' % (out_path, len(html)))
    print('   投喂 %d 份 / 观测股 %d 只 / 板块 %d 个' % (len(feeds), len(obs_items), len(sec_sorted)))


MARKET_STATS = '''
<div class="stat"><div class="stat-n">87</div><div class="stat-l">涨停</div></div>
<div class="stat"><div class="stat-n dn">13</div><div class="stat-l">跌停</div></div>
<div class="stat"><div class="stat-n">2.145<span class="u">万亿</span></div><div class="stat-l">成交额</div></div>
<div class="stat"><div class="stat-n">3181<span class="u">/</span>2218</div><div class="stat-l">涨/跌家数</div></div>
<div class="stat"><div class="stat-n">70.73<span class="u">%</span></div><div class="stat-l">封板率</div></div>
<div class="stat"><div class="stat-n gold">107</div><div class="stat-l">情绪分</div></div>
'''


TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日复盘 %(date)s · 本地版</title>
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#2a2f3a;--txt:#e8eaf0;--muted:#9aa3b2;--dim:#6b7280;
--red:#f0455a;--green:#2fb37e;--gold:#f0b90b;--blue:#4a9eff;--purple:#a78bfa;--cyan:#22d3ee}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font:14px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:24px 18px 70px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:23px;letter-spacing:.5px}
.sub{color:var(--muted);font-size:12.5px;margin-top:5px}
h2{font-size:16px;border-left:4px solid var(--gold);padding-left:10px;margin:30px 0 12px}
h2 small{color:var(--muted);font-weight:400;font-size:12px;margin-left:8px}
.verdict{background:linear-gradient(90deg,rgba(240,185,11,.12),transparent);border-left:4px solid var(--gold);
padding:13px 16px;border-radius:8px;margin:14px 0;font-size:14.5px;font-weight:600}
.idx-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0}
.idx{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.idx-n{color:var(--muted);font-size:12px}
.idx-v{font-size:19px;font-weight:700;margin:3px 0;font-family:ui-monospace,Menlo,monospace}
.idx-p{font-size:12.5px;font-weight:600}
.up{color:var(--red)}.dn{color:var(--green)}.dim{color:var(--dim)}.gold{color:var(--gold)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin:12px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;text-align:center}
.stat-n{font-size:20px;font-weight:700;font-family:ui-monospace,Menlo,monospace}
.stat-n .u{font-size:11px;color:var(--muted);font-weight:400}
.stat-l{color:var(--muted);font-size:11.5px;margin-top:3px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h3{font-size:13.5px;margin-bottom:9px;color:var(--txt)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{color:var(--muted);font-weight:600;text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
td{padding:6px 8px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.num{text-align:right;font-family:ui-monospace,Menlo,monospace}
ul{padding-left:19px;font-size:13px}li{margin:5px 0}
.tag{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:9px;background:var(--panel);
border:1px solid var(--line);color:var(--muted);margin-right:5px}
.tag.warn{background:rgba(240,69,90,.12);color:var(--red);border-color:rgba(240,69,90,.3)}
.feed{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 13px;margin-bottom:8px}
.feed-h{font-size:13px;font-weight:600}
.feed-b{font-size:11.5px;margin-top:4px;line-height:1.55}
.foot{margin-top:36px;color:var(--dim);font-size:11.5px;border-top:1px solid var(--line);padding-top:13px}
</style>
</head>
<body><div class="wrap">

<h1>📊 每日复盘 · %(date)s</h1>
<div class="sub">本地自包含版 · 数据：腾讯 gtimg / 新浪 znb / 本机 output · 生成 %(gen_at)s · 可离线打开</div>

<div class="verdict">%(verdict)s</div>

<h2>一、A 股收盘<small>沪深京三市</small></h2>
<div class="idx-row">%(idx_rows)s</div>
<div class="stats">%(mkt_stats)s</div>

<h2>二、全球市场<small>美股盘中 / 日韩收盘 / 港股 / 商品</small></h2>
<div class="grid2">
  <div class="card">
    <h3>美股（8/31 盘中）</h3>
    <table><thead><tr><th>指数</th><th class="num">点位</th><th class="num">涨跌</th><th>状态</th></tr></thead>
    <tbody>%(us_rows)s</tbody></table>
  </div>
  <div class="card">
    <h3>亚太（8/31 收盘）</h3>
    <table><thead><tr><th>指数</th><th class="num">点位</th><th class="num">涨跌</th></tr></thead>
    <tbody>%(asia_rows)s</tbody></table>
  </div>
</div>
<div class="card" style="margin-top:14px">
  <h3>商品 / 利率 / 汇率</h3>
  <table><thead><tr><th>品种</th><th class="num">数值</th><th class="num">涨跌</th></tr></thead>
  <tbody>%(comm_rows)s</tbody></table>
</div>

<h2>三、板块资金流<small>申万一级 · 主力净流入</small></h2>
<div class="grid2">
  <div class="card"><h3>净流入 TOP8</h3>
    <table><thead><tr><th>板块</th><th class="num">主力净额</th></tr></thead><tbody>%(sec_top)s</tbody></table></div>
  <div class="card"><h3>净流出 TOP8</h3>
    <table><thead><tr><th>板块</th><th class="num">主力净额</th></tr></thead><tbody>%(sec_bottom)s</tbody></table></div>
</div>

<h2>四、四象限交叉验证<small>机制 × 语料</small></h2>
<div class="card"><ul>%(cross_html)s</ul></div>

<h2>五、核心结论<small>合并 8/28 + 8/31 投喂推演</small></h2>
<div class="card"><ul>%(concl)s</ul></div>

<h2>六、次日操作指引<small>9/1 周二 · 偏向：%(bias)s</small></h2>
<div class="grid2">
  <div class="card"><h3>关注焦点</h3><ul>%(t1)s</ul></div>
  <div class="card"><h3>风险提示</h3><ul>%(risks)s</ul></div>
</div>

<h2>七、信号与观测股</h2>
<div class="grid2">
  <div class="card"><h3>金钻三形态（8/31 命中）</h3>
    <table><thead><tr><th>个股</th><th>主分类</th></tr></thead><tbody>%(gd_rows)s</tbody></table></div>
  <div class="card"><h3>主线共振</h3><p style="font-size:13px;color:var(--muted)">%(theme)s</p>
    <h3 style="margin-top:12px">持仓映射</h3><p style="font-size:13px;color:var(--muted)">%(holding)s</p></div>
</div>
<div class="card" style="margin-top:14px">
  <h3>重点观测股推演（32 只 · v3 引擎）</h3>
  <table><thead><tr><th>个股</th><th class="num">收盘</th><th class="num">涨跌</th><th>板块</th><th>推演</th><th>开盘</th></tr></thead>
  <tbody>%(obs_rows)s</tbody></table>
</div>

<h2>八、当日投喂素材<small>共 %(feed_count)s 份</small></h2>
%(feed_cards)s

<div class="foot">
数据来源：① 网上实时 —— 腾讯 gtimg（A股/美股/港股）、新浪 znb（日韩）、本机 market.json（商品/汇率/美债，8/31 21:04 更新）；
② 本机 output —— sector_flow / golden_diamond / obs_deduce_latest / feed_review_latest；
③ 当日投喂 %(feed_count)s 份（含 5 份扫描版 PDF 仅标题摘要）。<br>
仅供个人学习优化金融知识，不构成投资建议。
</div>

</div></body></html>
'''


if __name__ == '__main__':
    main()
