#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_v3 债/汇/币扩展数据抓取（2026-09-04 二期 · 独立脚本，不依赖/不修改老站任何文件）

源（全部无 key、国内可达，2026-09-04 实测）：
  BTC     新浪 hq.sinajs.cn  fx_sbtcusd  f[1]=现价 f[5]=昨结 f[17]=日期（GBK，需 Referer）
  ETH     腾讯 qt.gtimg.cn   usETHE      灰度质押以太坊 ETF（美股代理，非现货）f[3]现 f[4]昨收 f[32]涨跌% f[30]日期
  USD/JPY 新浪 hq.sinajs.cn  fx_susdjpy  f[1]=现价 f[5]=昨结 f[-1]=日期
  DXY     新浪 hq.sinajs.cn  DINIW       美元指数 f[1]=现价 f[5]=昨结 f[-1]=日期
  备注：新浪 fx_s 加密族实测仅 BTC/LTC/XRP/BCH 有数据，ETH/EOS/ADA 为空；
        国际加密 API（CoinGecko/Coinbase/Kraken/Binance/OKX/Bitstamp/CoinCap）国内全部不可达或需 key。

产出（双写）：
  review_v3/global_ext.json
  deploy/review_v3/global_ext.json   （8080 预览/发布副本）

跑法：python3 review_v3/fetch_global_ext.py
调度建议：交易日盘前/盘后随 market.json 一起跑（可挂 launchd 或手动）。
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根
OUT_MAIN = os.path.join(ROOT, 'review_v3', 'global_ext.json')
OUT_DEPLOY = os.path.join(ROOT, 'deploy', 'review_v3', 'global_ext.json')

SINA_URL = 'https://hq.sinajs.cn/list=fx_sbtcusd,fx_susdjpy,DINIW'
GTIMG_URL = 'https://qt.gtimg.cn/q=usETHE'


def _get(url, referer=None, timeout=15, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
            if referer:
                req.add_header('Referer', referer)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if i == retries:
                raise
            time.sleep(1.5)


def _pct(now, prev):
    try:
        now = float(now)
        prev = float(prev)
        if not prev:
            return None
        return round((now / prev - 1) * 100, 2)
    except Exception:
        return None


def parse_sina(raw):
    """新浪 hq.sinajs.cn 多代码返回（GBK）。统一取 f[1]=现价 f[5]=昨结，日期取最后一个 YYYY-MM-DD 字段。"""
    text = raw.decode('gbk', errors='ignore')
    out = {}
    for m in re.finditer(r'var hq_str_([A-Za-z0-9_]+)="([^"]*)";', text):
        code, body = m.group(1), m.group(2)
        if not body:
            continue
        f = body.split(',')
        if len(f) < 6:
            continue
        try:
            price = float(f[1])
            prev = float(f[5])
        except ValueError:
            continue
        src_date = ''
        for v in reversed(f):
            if re.match(r'^\d{4}-\d{2}-\d{2}$', v.strip()):
                src_date = v.strip()
                break
        name = f[9] if len(f) > 9 and not re.match(r'^[\d.\-]+$', f[9]) else code
        out[code] = {
            'price': round(price, 4),
            'prev_close': round(prev, 4),
            'chg_pct': _pct(price, prev),
            'src_date': src_date,
            'name_raw': name,
        }
    return out


def parse_gtimg_us(raw):
    """腾讯美股（GBK，~ 分隔）。f[1]=名称 f[3]=现价 f[4]=昨收 f[32]=涨跌幅% f[30]=日期时间。"""
    text = raw.decode('gbk', errors='ignore')
    out = {}
    for m in re.finditer(r'v_([A-Za-z0-9_.]+)="([^"]*)";', text):
        code, body = m.group(1), m.group(2)
        f = body.split('~')
        if len(f) < 33:
            continue
        try:
            price = float(f[3])
            prev = float(f[4])
        except ValueError:
            continue
        chg = None
        try:
            chg = round(float(f[32]), 2)
        except ValueError:
            chg = _pct(price, prev)
        out[code] = {
            'price': price,
            'prev_close': prev,
            'chg_pct': chg,
            'src_date': (f[30] or '')[:10],
            'name_raw': f[1],
        }
    return out


def main():
    items = {}

    # ── 新浪三合一：BTC / USDJPY / DXY ──
    try:
        sina = parse_sina(_get(SINA_URL, referer='https://finance.sina.com.cn'))
        if 'fx_sbtcusd' in sina:
            d = sina['fx_sbtcusd']
            items['btc'] = {
                'name': 'BTC 比特币（现货）', 'price': d['price'], 'prev_close': d['prev_close'],
                'chg_pct': d['chg_pct'], 'src_date': d['src_date'],
                'source': '新浪 fx_sbtcusd', 'proxy': False,
            }
        if 'fx_susdjpy' in sina:
            d = sina['fx_susdjpy']
            items['usdjpy'] = {
                'name': 'USD/JPY 美元日元', 'price': d['price'], 'prev_close': d['prev_close'],
                'chg_pct': d['chg_pct'], 'src_date': d['src_date'],
                'source': '新浪 fx_susdjpy', 'proxy': False,
            }
        if 'DINIW' in sina:
            d = sina['DINIW']
            items['dxy'] = {
                'name': '美元指数 DXY', 'price': d['price'], 'prev_close': d['prev_close'],
                'chg_pct': d['chg_pct'], 'src_date': d['src_date'],
                'source': '新浪 DINIW', 'proxy': False,
            }
        print(f"[global-ext] 新浪: BTC={'✓' if 'btc' in items else '✗'} USDJPY={'✓' if 'usdjpy' in items else '✗'} DXY={'✓' if 'dxy' in items else '✗'}")
    except Exception as e:
        print(f"[global-ext] 新浪源失败（非致命）: {type(e).__name__} {str(e)[:80]}")

    # ── 腾讯：ETH（灰度 ETHE 代理）──
    try:
        gt = parse_gtimg_us(_get(GTIMG_URL))
        if 'usETHE' in gt:
            d = gt['usETHE']
            items['eth'] = {
                'name': 'ETH 以太坊（灰度 ETHE 代理）', 'price': d['price'], 'prev_close': d['prev_close'],
                'chg_pct': d['chg_pct'], 'src_date': d['src_date'],
                'source': '腾讯 usETHE · 美股 ETF 代理（非现货）', 'proxy': True,
            }
        print(f"[global-ext] 腾讯: ETH={'✓' if 'eth' in items else '✗'}")
    except Exception as e:
        print(f"[global-ext] 腾讯源失败（非致命）: {type(e).__name__} {str(e)[:80]}")

    # ── 组装输出 ──
    src_dates = [v['src_date'] for v in items.values() if v.get('src_date')]
    doc = {
        'date': max(src_dates) if src_dates else '',
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'note': '债/汇/币扩展数据 · 新浪fx_s+DINIW（现货）+ 腾讯usETHE（ETH代理）。ETH 无免费现货源（新浪无代码/国际API国内不可达），以灰度ETHE美股代理替代。',
        'items': items,
    }
    for path in (OUT_MAIN, OUT_DEPLOY):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(doc, fp, ensure_ascii=False, indent=1)
        print(f"[global-ext] 写出 {path}（{os.path.getsize(path)}B, {len(items)}/4 项）")
    return 0 if items else 1


if __name__ == '__main__':
    sys.exit(main())
