#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""market.json 数据完整性守卫（2026-09-10 新增）

背景：2026-09-10 V3 页全站卡「加载中…」，根因是 us_kline.us_sox.latest.close = null
      → review_v3/index.html 的 renderUsDual 直接 .toLocaleString() 抛 TypeError
      → main() reject → 后续所有段永不渲染。
用法：每次更新 data/daily_review/market.json 后运行
      python3 review/check_market_json.py
退出码：0 = 通过；1 = 发现空值（须补数据，不要靠前端兜底）
"""
import json, sys, io, os

PATH = 'data/daily_review/market.json'
REQUIRED = ['date', 'updated_at', 'quotes', 'us_kline']
errs, warns = [], []

try:
    d = json.load(io.open(PATH, encoding='utf-8'))
except Exception as e:
    print('❌ 无法解析 %s: %s' % (PATH, e)); sys.exit(1)

for k in REQUIRED:
    if k not in d: errs.append('缺少顶层字段: %s' % k)

uk = d.get('us_kline') or {}
if not uk: errs.append('us_kline 为空')

for k, v in uk.items():
    if not isinstance(v, dict):
        errs.append('us_kline.%s 不是对象' % k); continue
    pr, lt = v.get('prev') or {}, v.get('latest') or {}
    if pr.get('close') is None:
        errs.append('us_kline.%s.prev.close 为 null（V3 双日表会显示「—」；建议用 latest.close/(1+chg_pct/100) 反推）' % k)
    if lt.get('close') is None:
        errs.append('us_kline.%s.latest.close 为 null（V3 双日表会显示「—」）' % k)
    if pr.get('date') is None or lt.get('date') is None:
        warns.append('us_kline.%s 缺日期' % k)

q = d.get('quotes') or {}
if not q: errs.append('quotes 为空')
for k, v in q.items():
    if isinstance(v, dict) and v.get('error') is None and v.get('close') is None and v.get('price') is None:
        warns.append('quotes.%s 无 close/price' % k)

if errs:
    print('❌ market.json 校验未通过（%d 项）:' % len(errs))
    for e in errs: print('   -', e)
if warns:
    print('⚠️  提醒（%d 项，不阻断）:' % len(warns))
    for w in warns[:10]: print('   -', w)
if not errs:
    print('✅ market.json 校验通过 | us_kline %d 标的 | quotes %d 项 | updated_at %s'
          % (len(uk), len(q), d.get('updated_at')))
sys.exit(1 if errs else 0)
