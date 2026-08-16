#!/usr/bin/env python3
"""研报分析模块 —— 星球研报接入的后续处理（每日更新管线 Step 3.5）

四类命中股票做研报加强分析：
  1. TOP10（top10_history 最新日）
  2. 信号选股（observation_pool）
  3. 兜宝金钻（golden_diamond stocks）
  4. 龙虎榜（lh_calendar 最新日）

研报来源：知识星球（zsxq-cli）加入的星球近 3 日主题。
频率控制（重要）：每星球每天仅 1 次 group +topics，星球间随机 sleep 2-5 秒，
模仿普通用户阅览频次，避免被拉黑；拉取结果按日期缓存，当天重复跑复用缓存。

容错：zsxq-cli 不存在（如 GitHub Actions 云端）或拉取失败时，若已有
report_analysis.json 则保留不动（不覆盖、不中断主流程）。
"""
import json, os, re, subprocess, time, random, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
CACHE = os.path.join(OUT, "zsxq_reports_cache.json")
RESULT = os.path.join(OUT, "report_analysis.json")

# 用户加入的星球（研报相关）。部分星球可能未开通 Skill 权限，拉取失败会跳过。
GROUPS = [
    ("28888815114151", "新的免费 行业研讯社"),
    ("15552841141582", "🍁简单复盘-调研纪要"),
    ("28888222154481", "180K Research"),
    ("88885515521412", "💰逻辑与思考-投资有道"),
    ("51111528282424", "哆唻咪学习宝"),
]

# 附件后缀 → 非文字（PPT/音频/PDF 等），仅提示「卖方机构推荐」
NON_TEXT_EXT = ('.ppt', '.pptx', '.pdf', '.mp3', '.m4a', '.wav', '.aac', '.amr', '.mp4', '.mov', '.avi')


def today_str():
    return datetime.date.today().strftime('%Y-%m-%d')


def collect_target_stocks():
    """四类股票去重，返回 {code: {code, name, sources[]}}"""
    stocks = {}

    def add(code, name, src):
        if not code or not name:
            return
        code = code.lower()
        # 龙虎榜 code 无前缀，补前缀
        if not code.startswith(('sh', 'sz')):
            code = ('sh' if code.startswith(('60', '68', '90')) else 'sz') + code
        if code not in stocks:
            stocks[code] = {'code': code, 'name': name, 'sources': []}
        if src not in stocks[code]['sources']:
            stocks[code]['sources'].append(src)

    # 1. TOP10
    p = os.path.join(OUT, 'top10_history.json')
    if os.path.exists(p):
        d = json.load(open(p, encoding='utf-8'))
        latest = d[sorted(d.keys())[-1]]
        for s in latest.get('top10', []):
            add(s.get('code'), s.get('name'), 'top10')

    # 2. 信号选股（observation_pool）
    p = os.path.join(OUT, 'signals.json')
    if os.path.exists(p):
        sig = json.load(open(p, encoding='utf-8'))
        for s in sig.get('observation_pool', []):
            add(s.get('code'), s.get('name'), 'signal')

    # 3. 兜宝金钻
    p = os.path.join(OUT, 'golden_diamond.json')
    if os.path.exists(p):
        gd = json.load(open(p, encoding='utf-8'))
        for s in gd.get('stocks', []):
            add(s.get('code'), s.get('name'), 'gd')

    # 4. 龙虎榜（最新日）
    p = os.path.join(BASE, 'lh_calendar.json')
    if os.path.exists(p):
        lh = json.load(open(p, encoding='utf-8'))
        latest_lh = lh[sorted(lh.keys())[-1]]
        for s in latest_lh:
            add(s.get('code'), s.get('name'), 'lhb')

    return stocks


def fetch_zsxq_reports():
    """拉取各星球最近主题（每天一次，按日期缓存；低频 + 随机间隔模仿普通用户）。"""
    t = today_str()
    if os.path.exists(CACHE):
        try:
            cached = json.load(open(CACHE, encoding='utf-8'))
            if cached.get('fetched_date') == t:
                print(f"  ↺ 复用今日研报缓存 ({len(cached.get('reports', []))} 条)")
                return cached.get('reports', [])
        except Exception:
            pass
    reports = []
    for gid, gname in GROUPS:
        print(f"  📡 拉取 [{gname}] 最近主题...")
        try:
            r = subprocess.run(
                ['zsxq-cli', 'group', '+topics', '--group-id', gid, '--limit', '30', '--json'],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0 or not r.stdout.strip():
                print(f"    ⚠️ 跳过（无权限或返回空）")
                time.sleep(random.uniform(2, 5))
                continue
            data = json.loads(r.stdout)
            for t_item in data.get('topics_brief', []):
                reports.append({
                    'group': gname,
                    'title': t_item.get('title', '') or '',
                    'content': t_item.get('content', '') or '',
                    'create_time': t_item.get('create_time', '') or '',
                    'files': t_item.get('files', []) or [],
                    'type': t_item.get('type', ''),
                })
        except Exception as e:
            print(f"    ⚠️ 拉取失败: {e}")
        # 模仿普通用户阅览频次：随机间隔 2-5 秒
        time.sleep(random.uniform(2, 5))
    json.dump({'fetched_date': t, 'reports': reports}, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"  ✓ 拉取完成，共 {len(reports)} 条主题")
    return reports


def filter_recent(reports, days=3):
    """筛选近 N 日内的主题（时区对齐）"""
    now = datetime.datetime.now().astimezone()
    cutoff = now - datetime.timedelta(days=days)
    recent = []
    for r in reports:
        try:
            ct = datetime.datetime.fromisoformat(r['create_time'])
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=now.tzinfo)
        except Exception:
            continue
        if ct >= cutoff:
            recent.append(r)
    return recent


def classify_format(r):
    """判断研报格式：text（文字）/ non_text（PPT/音频等）"""
    files = r.get('files', [])
    if not files:
        content = (r.get('content') or '').strip()
        return ('text', content) if content else ('empty', '')
    for f in files:
        fname = f.get('name', f.get('file_name', '')) if isinstance(f, dict) else str(f)
        ext = os.path.splitext(fname.lower())[1]
        if ext in NON_TEXT_EXT:
            return ('non_text', fname)
    return ('non_text', '')


def match_reports(stocks, recent):
    """匹配股票名 → 研报加强结果"""
    result = {}
    for code, s in stocks.items():
        name = s['name']
        if not name or len(name) < 2:
            continue
        matched = []
        for r in recent:
            text = (r.get('title') or '') + '\n' + (r.get('content') or '')
            if name in text:
                fmt, payload = classify_format(r)
                matched.append({
                    'group': r.get('group'),
                    'title': r.get('title'),
                    'content': r.get('content'),
                    'create_time': r.get('create_time'),
                    'format': fmt,
                    'payload': payload,
                })
        if matched:
            result[code] = {'code': code, 'name': name, 'sources': s['sources'], 'reports': matched}
    return result


def main():
    stocks = collect_target_stocks()
    print(f"四类股票去重：{len(stocks)} 只")

    # zsxq-cli 不存在（云端）→ 保留已有结果，不覆盖
    try:
        reports = fetch_zsxq_reports()
    except FileNotFoundError:
        print("  ⚠️ zsxq-cli 不可用（云端环境），保留已有 report_analysis.json")
        if os.path.exists(RESULT):
            print("  ✓ 已有研报结果，保持不变")
            return 0
        reports = []

    recent = filter_recent(reports, days=3)
    print(f"近 3 日主题：{len(recent)} 条")

    result = match_reports(stocks, recent)
    print(f"研报加强命中：{len(result)} 只")

    out = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'target_count': len(stocks),
        'report_count': len(recent),
        'matched': result,
    }
    json.dump(out, open(RESULT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"✅ 已输出 {RESULT}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
