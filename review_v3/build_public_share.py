#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V3 复盘推演 · 去隐私分享版生成器

用法：
    python3 review_v3/build_public_share.py [YYYY-MM-DD]
    省略日期则取当天。

输入：  output/v3_reasoning_{date}.json        （agent 产物，含 ai_synthesis 五要素）
输出：  output/v3_reasoning_{date}_public.json （脱敏数据）
        output/V3复盘_{date}_分享版.html       （自包含 HTML，可离线打开 / 可分享）
        {workspace}/V3复盘_{date}_分享版.html  （工作区副本，方便取用）
并镜像到 deploy/ 对应路径。

脱敏规则（三层）：
  L1 剔除指定标的：默认 ST万邦 及所有含「万邦」字样的文本（整条删除，不留痕）
  L2 剥离仓位动作词：减仓 / 减半 / 减一档 / 持有不加 / 清仓 / 锁仓 / 落袋 → 中性技术读数
  L3 改口径：holding_map 标为「参考专家持仓（第三方·非本人）」，声明非交易记录
终检：脚本内置敏感词扫描，有残留直接报错退出。
"""
import json, os, sys, html, shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = '/Users/samt/WorkBuddy/工作'

# ── L1：需要整条剔除的标的关键词（命中即删除该字符串所在的整个条目）──
DROP_KEYWORDS = ['万邦', 'ST万邦']

# ── L2：仓位动作词 → 中性技术读数（保留客观位，剥离操作）──
REPL = [
    ('持有不加，SNDK 跌破 1580 视为映射弹性下调', '技术参考：SNDK 1580 为映射有效线，跌破则映射弹性下调'),
    ('持有不加，SNDK 跌破 1580 = 映射弹性下调并同步减一档', '技术参考：SNDK 1580 为映射有效线，跌破则映射弹性下调'),
    ('持有不加，SNDK 跌破 1580 = 映射弹性下调并同步收紧敞口', '技术参考：SNDK 1580 为映射有效线，跌破则映射弹性下调'),
    ('持有不加，SNDK 跌破 1580 = 映射弹性下调', '技术参考：SNDK 1580 为映射有效线，跌破则映射弹性下调'),
    ('9/8 目标 18.0-18.1 兑现一段；破 16.50 减一档', '技术参考位：上方 18.0-18.1，下方 16.50'),
    ('9/8 目标 18.0-18.1，破 16.50 减一档', '技术参考位：上方 18.0-18.1，下方 16.50'),
    ('9/8 乙酉回血日为目标 18.0-18.1 兑现窗口；破 16.50 减一档。', '技术参考位：上方 18.0-18.1，下方 16.50。'),
    ('监管公告 = 无条件减半（爱丽家居一字跌停为活案例，不可逆）。9/8 乙酉回血日为主兑现窗口',
     '需关注监管公告风险（爱丽家居一字跌停为同类案例，风险不可逆）。技术参考：偏离值 +95% 已达异动临界'),
    ('预案：监管公告 = 无条件减半。', '预案：以监管公告为风险触发信号，参考同类案例（爱丽家居/深中华A）风险不可逆。'),
    ('回血日不追，断板即减不格局', '高位情绪标，仅作情绪温度观测'),
    ('预案：韩股次日回落 >2% = 光通信/存储同步减一档。', '预案：韩股次日回落 >2% 则光通信/存储映射同步下修。'),
    ('预案：收盘有效跌破 = 全面减仓。', '预案：收盘有效跌破则风险敞口全面收缩。'),
    ('收盘有效跌破 = 全面减仓；第一警戒 3900。', '收盘有效跌破则风险敞口全面收缩；第一警戒 3900。'),
    ('预案：不破 5 日线不格局；9/8-9/9 分批兑现。', '技术参考：5 日线为趋势有效性判据；9/8-9/9 为高位分歧观察窗。'),
    ('不破 5 日线不格局。', '技术参考：5 日线为趋势有效性判据。'),
    ('预案：只做已有仓位的管理，新方向一律观察 1-2 日等主线归属明确，不做首日追高。',
     '预案：新方向一律观察 1-2 日等主线归属明确，不做首日追高。'),
    ('预案：周五白天已落袋 = 天然防御。', '预案：CPI 为 FOMC 前最后定价窗，事件前宜降低敞口。'),
    ('预案：周五白天已落袋 = 天然防御', '预案：CPI 为 FOMC 前最后定价窗，事件前宜降低敞口'),
    ('直接冲击长鑫/SNDK 的持有理由', '直接冲击长鑫/SNDK 的映射逻辑'),
    ('三日内浮盈落袋纪律不变。', '三日内为高位分歧观察窗。'),
    ('同时是金牛 18.0-18.1、国芳分批兑现的预设窗口。', '同时是金牛（上方 18.0-18.1）、国芳的预设观察窗口。'),
    ('观察：剑桥能否站稳 200 / 振华股份是否高开兑现 / 沪电深南是否放量。',
     '观察：剑桥能否站稳 200 / 振华股份高开后承接力度 / 沪电深南是否放量。'),
    ('仅作产业观察，不得据此建仓', '仅作产业观察，不纳入技术候选池'),
    ('不得据此建仓', '不纳入技术候选池'),
    ('属兑现区非建仓区', '属高位区间，非布局区'),
    ('属观察不属推荐', '属观察标的'),
    ('非实盘记录', '非交易记录'),
]

# ── 终检敏感词（出现即失败）──
FORBIDDEN = ['万邦', '减一档', '无条件减半', '持有不加', '全面减仓', '落袋',
             '减半', '清仓', '锁仓', '账户', '实盘', '建仓']


def scrub_text(s):
    if not isinstance(s, str):
        return s
    for a, b in REPL:
        s = s.replace(a, b)
    return s


def walk(o):
    if isinstance(o, str):
        return scrub_text(o)
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    return o


def drop_keywords(o, kws):
    """命中关键词的字符串整条删除（连同所在列表项 / 字典值）"""
    if isinstance(o, str):
        return None if any(k in o for k in kws) else o
    if isinstance(o, list):
        out = []
        for x in o:
            r = drop_keywords(x, kws)
            if r is not None:
                out.append(r)
        return out
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            r = drop_keywords(v, kws)
            if r is not None:
                out[k] = r
        return out
    return o


def build_public(date):
    src = os.path.join(ROOT, 'output', f'v3_reasoning_{date}.json')
    if not os.path.exists(src):
        raise SystemExit(f'源文件不存在：{src}')
    d = json.loads(json.dumps(json.load(open(src))))   # deep copy
    syn = d['ai_synthesis']

    syn = walk(syn)                 # L2 剥离动作词
    syn = drop_keywords(syn, DROP_KEYWORDS)   # L1 剔除标的

    # L3 改口径
    hm = syn.get('holding_map') or {}
    syn['holding_map'] = {
        'disclaimer': ('以下为公开渠道整理的「参考专家持仓」映射，非本人持仓、非交易记录，'
                       '仅提供客观技术读数与产业逻辑，不构成任何投资建议。'),
        'theme_aligned': hm.get('theme_aligned', []),
        'caution': hm.get('caution', []),
        'us': hm.get('us', []),
    }
    syn['disclaimer'] = ('【分享版·已脱敏】个人学习用途，不构成任何投资建议。文中「参考专家持仓」为公开渠道整理的'
                         '第三方映射，非本人持仓、非交易记录，已剔除特定标的与仓位动作信息。'
                         '所有数字标注口径与截止日，请自行核对。')
    d['privacy_mode'] = True
    d['privacy_note'] = ('分享版：已剔除指定标的及其全部关联内容；持仓映射改为「参考专家持仓（第三方·非本人）」口径；'
                         '剥离全部仓位操作类表述，仅保留客观技术读数与产业逻辑。')
    d['ai_synthesis'] = syn

    # 终检
    raw = json.dumps(d, ensure_ascii=False)
    bad = [k for k in FORBIDDEN if k in raw]
    if bad:
        raise SystemExit(f'❌ 脱敏终检失败，残留敏感词：{bad}')

    out_json = os.path.join(ROOT, 'output', f'v3_reasoning_{date}_public.json')
    json.dump(d, open(out_json, 'w'), ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(ROOT, 'deploy', 'output'), exist_ok=True)
    shutil.copy(out_json, os.path.join(ROOT, 'deploy', 'output', f'v3_reasoning_{date}_public.json'))
    return d, out_json


def render_html(d):
    syn = d['ai_synthesis']
    e = lambda s: html.escape(str(s or ''))
    W = {'极高': 'w-ext', '高': 'w-high', '中高': 'w-mid', '中': 'w-mid2', '低中': 'w-low', '低': 'w-low2'}

    cf = ''.join(f'<li class="cf-item">{e(c)}</li>' for c in syn['conclusion_first'])

    tr = ''
    for t in syn['theme_resonance']:
        sk = ' · '.join(t.get('related_stocks') or [])
        tr += (f'<tr><td class="th-n">{e(t["theme"])}<div class="stg">{e(t.get("stage",""))}</div></td>'
               f'<td class="c"><span class="wt {W.get(t["weight"],"w-mid2")}">{e(t["weight"])}</span></td>'
               f'<td class="c ev">{e(t.get("evidence",""))}</td><td class="c sk">{e(sk)}</td></tr>')

    hm = syn['holding_map']
    def blk(title, items, cls):
        if not items:
            return ''
        lis = ''.join(f'<li>{e(i)}</li>' for i in items)
        return f'<div class="hm-blk"><div class="hm-t {cls}">{title}</div><ul class="hm-ul">{lis}</ul></div>'
    hm_html = (blk('主题契合', hm.get('theme_aligned', []), 't-red')
               + blk('需谨慎', hm.get('caution', []), 't-org')
               + blk('美股 / 海外映射', hm.get('us', []), 't-grn'))

    t1 = ''
    for r in syn['t1_radar']:
        star = '★' if '★' in (r.get('event', '') + r.get('impact', '')) else ''
        t1 += (f'<tr><td class="tm">{e(r.get("time",""))}</td>'
               f'<td class="ev2">{e(r.get("event",""))}'
               f'{f"<span class=st2>{star}</span>" if star else ""}</td>'
               f'<td class="c">{e(r.get("impact",""))}</td></tr>')

    rk = ''
    for r in syn['risks']:
        p = r.get('prob', '') or ''
        pc = 'r-hi' if '高' in p else ('r-md' if '中' in p else 'r-lo')
        rk += (f'<tr><td class="rn">{e(r["name"])}</td>'
               f'<td class="c"><span class="pb {pc}">{e(r["prob"])}</span></td>'
               f'<td class="c"><span class="pb {pc}">{e(r["impact"])}</span></td>'
               f'<td class="c">{e(r["desc"])}</td></tr>')

    ymd = d.get('data_date', '').replace('-', '')
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3 复盘推演 · {e(d.get('data_date'))} · 分享版（已脱敏）</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font:14px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:32px 20px}}
.wrap{{max-width:1180px;margin:0 auto}}
.hd{{border:1px solid #2a3140;border-radius:14px;padding:24px 28px;background:#12171f;margin-bottom:22px}}
.hd h1{{font-size:22px;font-weight:600;letter-spacing:.5px}}
.hd .sub{{color:#8b95a5;font-size:12.5px;margin-top:8px}}
.badge{{display:inline-block;background:#1d2b1f;color:#5fd68a;border:1px solid #2f5c3a;border-radius:20px;padding:3px 12px;font-size:11.5px;margin-left:10px;vertical-align:middle}}
.privacy{{margin-top:14px;padding:11px 14px;background:#1a1410;border-left:3px solid #d4af37;border-radius:6px;font-size:12px;color:#c9b489}}
h2{{font-size:16px;font-weight:600;margin:30px 0 12px;padding-left:11px;border-left:3px solid #d4af37}}
.cf-ul{{list-style:none}}
.cf-item{{background:#12171f;border:1px solid #232a36;border-radius:9px;padding:13px 16px;margin-bottom:9px;font-size:13.5px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;background:#12171f;border:1px solid #232a36;border-radius:9px;overflow:hidden}}
th{{background:#171d27;color:#c9b489;font-weight:500;text-align:left;padding:10px 12px;border-bottom:1px solid #2a3140;white-space:nowrap}}
td{{padding:10px 12px;border-bottom:1px solid #1c2230;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
.c{{text-align:left}}
.th-n{{font-weight:500;color:#e6edf3;white-space:nowrap}}
.stg{{font-size:11px;color:#7d8798;margin-top:3px}}
.sk{{color:#8b95a5;font-size:11.5px;line-height:1.6}}
.ev{{color:#b6c0cf;font-size:12px;line-height:1.65}}
.ev2{{color:#e6edf3;font-size:12.5px;line-height:1.6}}
.tm{{color:#d4af37;font-family:Menlo,monospace;font-size:11.5px;white-space:nowrap}}
.st2{{color:#f0883e;margin-left:4px}}
.wt{{display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;white-space:nowrap}}
.w-ext{{background:#3a1416;color:#ff7b72;border:1px solid #5c2226}}
.w-high{{background:#3a2410;color:#e3b341;border:1px solid #5c4018}}
.w-mid{{background:#12283a;color:#58a6ff;border:1px solid #1f4463}}
.w-mid2{{background:#1c2230;color:#8b95a5;border:1px solid #2a3140}}
.w-low,.w-low2{{background:#161b26;color:#6e7681;border:1px solid #232a36}}
.hm-blk{{margin-bottom:16px}}
.hm-t{{font-size:13px;font-weight:500;margin-bottom:7px}}
.t-red{{color:#ff7b72}} .t-org{{color:#e3b341}} .t-grn{{color:#5fd68a}}
.hm-ul{{list-style:none}}
.hm-ul li{{background:#12171f;border:1px solid #232a36;border-left:2px solid #2a3140;border-radius:7px;padding:10px 14px;margin-bottom:6px;font-size:12.5px;color:#c3ccd8;line-height:1.65}}
.hm-note{{background:#12171f;border:1px dashed #2a3140;border-radius:8px;padding:11px 14px;font-size:12px;color:#8b95a5;margin-bottom:14px}}
.pb{{display:inline-block;padding:2px 8px;border-radius:5px;font-size:11px;white-space:nowrap}}
.r-hi{{background:#3a1416;color:#ff7b72}}
.r-md{{background:#3a2410;color:#e3b341}}
.r-lo{{background:#1c2230;color:#8b95a5}}
.rn{{font-weight:500;color:#e6edf3;white-space:nowrap}}
.disc{{margin-top:32px;padding:16px 20px;background:#12171f;border:1px solid #232a36;border-radius:10px;font-size:12px;color:#8b95a5;line-height:1.75}}
.disc b{{color:#e3b341}}
.ft{{text-align:center;color:#5a6472;font-size:11.5px;margin-top:22px}}
@media(max-width:820px){{body{{padding:16px 10px}} table{{font-size:11.5px}} td,th{{padding:8px 7px}}}}
@media print{{body{{background:#fff;color:#111;padding:0}} .hd,table,.cf-item,.hm-ul li{{background:#fff;border-color:#ccc}} th{{background:#f2f2f2;color:#333}} .sk,.ev,.ev2,.hm-ul li{{color:#333}} .tm{{color:#8a6d1f}} .disc{{color:#555}}}}
</style></head><body><div class="wrap">

<div class="hd">
  <h1>V3 复盘推演 · {e(d.get('data_date'))}<span class="badge">分享版 · 已脱敏</span></h1>
  <div class="sub">mode {e(d.get('mode'))} · revision {e(d.get('revision'))} · 生成 {e(d.get('generated'))}</div>
  <div class="sub">数据窗口：{e(d.get('data_window'))}</div>
  <div class="privacy">隐私说明：{e(d.get('privacy_note'))}</div>
</div>

<h2>一 · 结论先行</h2>
<ul class="cf-ul">{cf}</ul>

<h2>二 · 主线共振（{len(syn['theme_resonance'])} 条）</h2>
<table><thead><tr><th>主题</th><th>权重</th><th>证据</th><th>相关标的</th></tr></thead><tbody>{tr}</tbody></table>

<h2>三 · 参考专家持仓映射</h2>
<div class="hm-note">{e(hm.get('disclaimer'))}</div>
{hm_html}

<h2>四 · T+1 事件雷达（{len(syn['t1_radar'])} 条）</h2>
<table><thead><tr><th>时间</th><th>事件</th><th>影响</th></tr></thead><tbody>{t1}</tbody></table>

<h2>五 · 风险（概率 × 冲击，{len(syn['risks'])} 条）</h2>
<table><thead><tr><th>风险</th><th>概率</th><th>冲击</th><th>描述与预案</th></tr></thead><tbody>{rk}</tbody></table>

<div class="disc"><b>免责声明</b><br>{e(syn.get('disclaimer'))}</div>
<div class="ft">V3 复盘推演 · 分享版 · 生成于 {e(d.get('generated'))} · 静态自包含，可离线打开</div>
</div></body></html>'''


if __name__ == '__main__':
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    d, out_json = build_public(date)
    doc = render_html(d)

    ymd = date.replace('-', '')
    outs = [os.path.join(ROOT, 'output', f'V3复盘_{ymd}_分享版.html'),
            os.path.join(WORKSPACE, f'V3复盘_{ymd}_分享版.html')]
    for p in outs:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', encoding='utf-8').write(doc)
        print('written', p, os.path.getsize(p), 'B')

    bad = [k for k in FORBIDDEN if k in doc]
    print()
    print('脱敏终检：', '❌ ' + str(bad) if bad else '✅ 0 残留')
    print('外部依赖：', '✅ 无（自包含）' if 'http' not in doc else '⚠️ 有外链')
    if bad:
        sys.exit(1)
