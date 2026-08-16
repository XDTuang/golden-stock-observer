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
import json, os, re, subprocess, time, random, datetime, sys, urllib.request

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


def _find_zsxq_cli():
    """查找 zsxq-cli（优先 PATH，launchd 环境 PATH 不含时 fallback 到 WorkBuddy connector 完整路径）。"""
    import shutil
    p = shutil.which('zsxq-cli')
    if p:
        return 'zsxq-cli'
    for c in [
        '/Users/samt/.workbuddy/binaries/node/cli-connector-packages/bin/zsxq-cli',
        os.path.expanduser('~/.workbuddy/binaries/node/cli-connector-packages/bin/zsxq-cli'),
    ]:
        if os.path.exists(c):
            return c
    return 'zsxq-cli'  # 兜底：subprocess 抛 FileNotFoundError，被 try/except 容错


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

    # 4. 龙虎榜（最近一个有数据的交易日，跳过非交易日空数据）
    p = os.path.join(BASE, 'lh_calendar.json')
    if os.path.exists(p):
        lh = json.load(open(p, encoding='utf-8'))
        latest_lh = []
        for _k in sorted(lh.keys(), reverse=True):
            if lh[_k]:
                latest_lh = lh[_k]
                break
        for s in latest_lh:
            add(s.get('code'), s.get('name'), 'lhb')

    return stocks


def _fetch_group_via_http(gid, token, retries=3):
    """HTTP API 直调拉取单个星球最近主题（云端/有 token 时）。返回 report dict 列表。

    付费星球接口偶发返回 succeeded=false（限流抖动），故内置重试 + 随机间隔。
    """
    url = f"https://api.zsxq.com/v2/groups/{gid}/topics?scope=all&count=20"
    headers = {
        'Cookie': f'zsxq_access_token={token}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if not data.get('succeeded'):
                last_err = RuntimeError('succeeded=false')
                if attempt < retries - 1:
                    time.sleep(random.uniform(2, 4))
                    continue
                raise last_err
            out = []
            for t_item in (data.get('resp_data', {}) or {}).get('topics', []):
                talk = t_item.get('talk', {}) or {}
                out.append({
                    'group': t_item.get('group', {}).get('name', ''),
                    'title': t_item.get('title', '') or '',
                    'content': talk.get('text', '') or '',
                    'create_time': t_item.get('create_time', '') or '',
                    'files': talk.get('files', []) or [],
                    'type': t_item.get('type', ''),
                })
            return out
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(random.uniform(2, 4))
                continue
    raise last_err


def fetch_zsxq_reports():
    """拉取各星球最近主题（每天一次，按日期缓存；低频 + 随机间隔模仿普通用户）。

    优先用 ZSXQ_ACCESS_TOKEN（环境变量/GitHub Secrets）直调 HTTP API（云端可用）；
    无 token 时回退到本机 zsxq-cli（WorkBuddy 登录态）。
    """
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
    token = os.environ.get('ZSXQ_ACCESS_TOKEN', '').strip()
    if token:
        # 云端 / 有 token：HTTP API 直调（知识星球 api.zsxq.com，无需本机 zsxq-cli）
        print(f"  🌐 使用 HTTP API 直调（token 已配置）")
        for gid, gname in GROUPS:
            print(f"  📡 拉取 [{gname}] 最近主题...")
            try:
                items = _fetch_group_via_http(gid, token)
                for it in items:
                    it['group'] = it['group'] or gname
                    reports.append(it)
                print(f"    ✓ {len(items)} 条")
            except Exception as e:
                print(f"    ⚠️ 拉取失败: {type(e).__name__}: {str(e)[:120]}")
            # 模仿普通用户阅览频次：随机间隔 2-5 秒
            time.sleep(random.uniform(2, 5))
    else:
        # 本机无 token：回退 zsxq-cli
        print(f"  💻 无 token，回退本机 zsxq-cli")
        cli = _find_zsxq_cli()
        for gid, gname in GROUPS:
            print(f"  📡 拉取 [{gname}] 最近主题...")
            try:
                r = subprocess.run(
                    [cli, 'group', '+topics', '--group-id', gid, '--limit', '30', '--json'],
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
            except FileNotFoundError:
                print(f"    ⚠️ zsxq-cli 不存在，跳过")
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
