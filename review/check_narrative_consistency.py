#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
叙述 ↔ 数据 一致性守卫（2026-09-29 立 · 第十四道门禁）

━━ 为什么需要它 ━━
2026-09-29 一天内出现 **两次**「页面叙述的数字 ≠ 数据产物的实际值」：
  ① 上午：`fetch_sector_flow` 修复后资金列由 9/24 推进至 9/28
     → 四象限 4/6/5/16 → 2/8/5/16，而 `analysis.html` 仍写旧值（已修 21 处）。
  ② 同一日稍后：云端 `daily-review-news` 抢跑（新闻池 total 306 → 584）
     → 象限再迁移 4 项 → 1/11/6/13，页面又落后（本次即由本守卫暴露）。

**共同根因**：四象限分布是**手写叙述**（非脚本生成）。数据侧 `cross_analysis.json`
每天（且**云端白天也可能抢跑重算**）都会变，页面数字**不会自动跟着变** ——
不报错、不空白，只是「页面说的和数据不是一回事」。

⇒ 本守卫把「页面必须 == 数据」从「靠 agent 记性」升级为「**脚本强制**」，
   并提供 `--fix` 让修复也是**一条命令**（消除人为遗漏空间）。

━━ 检查维度 ━━
  [1] 四象限分布（硬断言）—— 覆盖**三种写法**
      (a) **全式**「共振 A / 背离 B / 暗线 C / 双冷 D」
      (b) **斜杠简写**「A/B/C/D」（例：「前版 4/6/5/16 → 回炉后 2/8/5/16」）
      (c) **四卡式**「共振 A = 7」（§0 四象限速览卡逐卡列举；可带/不带字母）
          🔴 2026-09-30 补：此前 (c) 未被覆盖 → 四卡数字改了但守卫仍报绿
             （「有定义无守卫」型静默失效）。现每卡按**其自报象限**逐张断言。
      (a)(b) 中判定为**当前值**的命中，必须逐项等于 `output/cross_analysis.json` 的实际分布；
      (c) 每张卡的值必须等于**该卡自报象限**的实际值（无需分组，逐卡独立断言）。
      · 准入（仅简写）：前后 60 字符内须含「共振/背离/暗线/双冷/象限/迁移」之一，
        避免把日期、比例等无关的 A/B/C/D 误纳入。
      · 分类（当前 vs 历史）：取命中点**前 30 字符**内**最后出现的标记词**——
        当前类 = 变为 / 回炉后 / 本版 / 现为 / 当前 / 判定为 / 更新为 / 已更正为；
        历史类 = 前版 / 上一版 / 上版 / 旧版 / 此前 / 由。
        （实测例：「由 4/6/5/16 变为 2/8/5/16」→ 前者判历史、后者判当前；
               「前版 4/6/5/16 → 回炉后 2/8/5/16」→ 同样正确）
        无法判定者计入 `unknown`，**按失败处理**（提示人工确认，不自动改）。
      · 数字必须**全部同源**：多处当前值不容许出现两种互不相同的写法。
  [2] 归因句复核提醒（软提示，不改文件）
      当象限数字与上一版不同时，打印「迁移主因」类叙述的位置，
      提醒 agent 复核（该句是语义判断，脚本不代改）。

━━ 用法 ━━
  python3 review/check_narrative_consistency.py          # 检查（红灯 → 退出码 1）
  python3 review/check_narrative_consistency.py --fix    # 自动修数字（仅机械部分）
  python3 review/check_narrative_consistency.py -v       # 打印所有命中位置
  python3 review/check_narrative_consistency.py --allow-missing
      # 页面确无象限全式时放行（默认判失败 —— §0 速览卡按约定应含）

━━ 注意 ━━
· **纯本地、零网络、亚秒级、幂等** —— 可在任何档位、任何时刻安全运行
  （盘中也可跑：只读 JSON + HTML，不触发任何数据源）。
· 修完仍需跑 `check_analysis_style.py`（排版）与 `patch_dk_css.py --check`（色板）。
· 🔴 本守卫只保证「数字一致」。**归因/结论层的表述需 agent 按最新数据复核**。
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS = os.path.join(ROOT, "data", "daily_review", "analysis.html")
DEPLOY_ANALYSIS = os.path.join(ROOT, "deploy", "data", "daily_review", "analysis.html")
CROSS = os.path.join(ROOT, "output", "cross_analysis.json")
DEPLOY_CROSS = os.path.join(ROOT, "deploy", "output", "cross_analysis.json")

QUADS = ("共振", "背离", "暗线", "双冷")

# 「共振 A / 背离 B / 暗线 C / 双冷 D」全式（空格容错）
FULL_RE = re.compile(
    r"共振\s*(\d+)\s*/\s*背离\s*(\d+)\s*/\s*暗线\s*(\d+)\s*/\s*双冷\s*(\d+)"
)
# 斜杠简写 A/B/C/D（需结合上下文准入 + 标记词分类）
SLASH_RE = re.compile(r"(?<![\d.])(\d{1,2})/(\d{1,2})/(\d{1,2})/(\d{1,2})(?![\d.])")
# 四卡式「共振 A = 7」（字母可省；等号两侧容错空格/全角括号）
#   2026-09-30 补：§0 速览卡用此写法，此前未被覆盖 → 静默漏检
CARD_RE = re.compile(r"(共振|背离|暗线|双冷)\s*[（(]?\s*([ABCD])?\s*[)）]?\s*=\s*(\d{1,2})")

# 当前值标记（命中点之前最后出现者决定归属）
CUR_MARKS = ("变为", "回炉后", "本版", "现为", "当前", "判定为", "更新为", "已更正为", "修正为")
# 历史引用标记
HIST_MARKS = ("前版", "上一版", "上版", "旧版", "此前", "由", "上一交易日", "较上一版")
# 简写形态的准入上下文关键词（避免误纳日期/比例）
QUAD_CTX = ("共振", "背离", "暗线", "双冷", "象限", "迁移")
CLASS_WIN = 30      # 分类窗口（前 N 字符）
CTX_WIN = 60        # 准入窗口（前后各 N 字符）

# 归因句关键词（软提示）
ATTRIB_KEYS = ("迁移主因", "象限迁移", "迁移全部发生", "迁移主因已")

# 「象限类」问题标记 —— `--fix` 修完后这些视为已消解，其余（BOM / 副本 / 属性）仍拦截
QUAD_PROB_KEYS = ("当前值", "不同源", "无法判定", "四象限", "未找到任何四象限")


def c(code, s):
    """ANSI 着色（非 tty 时不着色）"""
    if not sys.stdout.isatty():
        return s
    m = {"r": "31", "g": "32", "y": "33", "b": "36", "d": "2"}
    return f"\033[{m.get(code, '0')}m{s}\033[0m"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def quadrant_true(path=CROSS):
    """从 cross_analysis.json 读出真实四象限分布"""
    d = load_json(path)
    items = d.get("items") or []
    q = {k: 0 for k in QUADS}
    for it in items:
        v = it.get("verdict")
        if v in q:
            q[v] += 1
    meta = {
        "flow_date": d.get("flow_date"),
        "data_date": d.get("data_date"),
        "news_window_days": d.get("news_window_days"),
        "n_items": len(items),
        "flow_raw_latest": d.get("flow_raw_latest"),
    }
    return q, meta


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def section_of(text, pos):
    """命中点所属段标题（往前找最近的 dr-h）"""
    head = text.rfind('class="dr-h"', 0, pos)
    if head < 0:
        return "（头部注释 / 前导区）"
    seg = text[head: head + 90]
    seg = re.sub(r"<[^>]+>", "", seg)
    return seg.strip()[:34] or "（未命名段）"


def classify(pre):
    """按「命中点之前最后出现的标记词」判定：cur / hist / unknown"""
    lc = max([pre.rfind(k) for k in CUR_MARKS] + [-1])
    lh = max([pre.rfind(k) for k in HIST_MARKS] + [-1])
    if lc < 0 and lh < 0:
        return "unknown"
    return "cur" if lc > lh else "hist"


def scan(text):
    """返回 [{'span','vals','kind','form','sect','line','raw'}]；kind ∈ cur/hist/unknown"""
    out = []
    # ── (a) 全式 ─────────────────────────────────────────
    for m in FULL_RE.finditer(text):
        vals = tuple(int(x) for x in m.groups())
        pre = text[max(0, m.start() - CLASS_WIN): m.start()]
        # 全式**默认当前**：含「变为 / 本版 / 现为」等当前标记即为当前；
        # 仅当窗口内出现明确历史标记（前版 / 上一版 …）且无当前标记时才判历史。
        # （2026-09-30 改：旧逻辑「遇历史标记即历史」会把「由上一版 2/1/15/13 变为 共振 7/…」
        #   这句里的**当前值**误判为历史 → 静默漏检。）
        out.append({
            "span": (m.start(), m.end()),
            "vals": vals,
            "kind": "hist" if classify(pre) == "hist" else "cur",
            "form": "full",
            "sect": section_of(text, m.start()),
            "line": line_of(text, m.start()),
            "raw": m.group(0),
        })
    # ── (b) 斜杠简写 ─────────────────────────────────────
    full_spans = [h["span"] for h in out]
    for m in SLASH_RE.finditer(text):
        s, e = m.span()
        if any(a <= s < b for a, b in full_spans):
            continue                                    # 与全式重叠 → 跳过
        ctx = text[max(0, s - CTX_WIN): e + CTX_WIN]
        pre30 = text[max(0, s - CLASS_WIN): s]
        # 准入：① 邻域含象限类词；或
        #      ② 紧前出现**当前值标记词** —— 例「… → 上一版盘前 2/1/15/13 → 本版 7/4/10/10」，
        #         此类链式表述末尾的「本版 X/Y/Z/W」也是本版读数，此前因邻域无象限词而**漏检**。
        if not any(k in ctx for k in QUAD_CTX) and classify(pre30) != "cur":
            continue                                    # 非象限语境 → 不纳入
        pre = text[max(0, s - CLASS_WIN): s]
        out.append({
            "span": (s, e),
            "vals": tuple(int(x) for x in m.groups()),
            "kind": classify(pre),
            "form": "slash",
            "sect": section_of(text, s),
            "line": line_of(text, s),
            "raw": m.group(0),
        })
    # ── (c) 四卡式「共振 A = 7」──────────────────────────
    #   每卡**自报象限** → 逐卡独立断言（不需分组）；未被 (a)(b) 覆盖
    occupied = [h["span"] for h in out]
    for m in CARD_RE.finditer(text):
        s, e = m.span()
        if any(a <= s < b for a, b in occupied):
            continue                                    # 与全式/简写重叠 → 跳过
        quad, letter, val = m.group(1), m.group(2) or "", int(m.group(3))
        pre = text[max(0, s - CLASS_WIN): s]
        out.append({
            "span": (s, e),
            "vals": None,                               # 单卡只有本象限一值
            "quad": quad,
            "letter": letter,
            "val": val,
            # 四卡**默认当前**（卡片本身即「本版读数」的断言）；
            # 仅当紧邻前文出现明确历史标记时才判历史（如「前版 共振 A = 2」）
            "kind": "hist" if classify(pre) == "hist" else "cur",
            "form": "card",
            "sect": section_of(text, s),
            "line": line_of(text, s),
            "raw": m.group(0),
        })
    out.sort(key=lambda h: h["span"][0])
    return out


def fmt(q):
    return "共振 %d / 背离 %d / 暗线 %d / 双冷 %d" % (q["共振"], q["背离"], q["暗线"], q["双冷"])


def main():
    ap = argparse.ArgumentParser(description="叙述↔数据一致性守卫（四象限）")
    ap.add_argument("--fix", action="store_true", help="自动把页面「当前值」改为数据侧实际值")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印全部命中位置")
    ap.add_argument("--allow-missing", action="store_true", help="页面无象限全式时放行")
    args = ap.parse_args()

    problems, warns = [], []
    fix_resolved = False

    # ── 前置：文件在位 ─────────────────────────────────────
    for p in (ANALYSIS, CROSS):
        if not os.path.exists(p):
            print(c("r", f"❌ 缺少文件：{os.path.relpath(p, ROOT)}"))
            return 1

    true_q, meta = quadrant_true()
    true_str = fmt(true_q)
    text = open(ANALYSIS, encoding="utf-8").read()
    bom_ok = text.startswith("\ufeff")

    print("═" * 74)
    print("  叙述 ↔ 数据 一致性守卫（四象限）")
    print("═" * 74)
    print(f"  数据侧 cross_analysis.json")
    print(f"    flow_date={meta['flow_date']}  data_date={meta['data_date']}  "
          f"items={meta['n_items']}  新闻窗口={meta['news_window_days']} 日")
    print(f"    真实分布 → {c('b', true_str)}")
    print(f"  页面 data/daily_review/analysis.html")
    print(f"    BOM={'✅' if bom_ok else '❌ 缺失'}  长度={len(text):,}")
    print("─" * 74)

    hits = scan(text)
    nfull = sum(1 for h in hits if h["form"] == "full")
    cards = [h for h in hits if h["form"] == "card"]
    cur = [h for h in hits if h["kind"] == "cur" and h["form"] != "card"]
    cur_cards = [h for h in cards if h["kind"] == "cur"]
    hist = [h for h in hits if h["kind"] == "hist"]
    unk = [h for h in hits if h["kind"] == "unknown"]

    print("  [1] 四象限分布")
    print(f"      命中 {len(hits)} 处（全式 {nfull} / 简写 {len(hits) - nfull - len(cards)}"
          f" / 四卡 {len(cards)}）"
          f" → 当前值 {len(cur) + len(cur_cards)} · 历史 {len(hist)} · 待判 {len(unk)}")

    if args.verbose:
        TAG = {"cur": "当前", "hist": "历史", "unknown": "待判"}
        FORM = {"full": "全式", "slash": "简写", "card": "四卡"}
        for h in hits:
            print(f"        [{TAG[h['kind']]}/{FORM[h['form']]}] L{h['line']:<6} "
                  f"@{h['span'][0]:<8} [{h['sect']}]  {h['raw']}")

    if not hits:
        msg = ("页面中未找到任何四象限表述 —— "
               "§0 速览卡按约定应含「共振 A / 背离 B / 暗线 C / 双冷 D」；"
               "若页面结构已变更，请同步更新本守卫")
        if args.allow_missing:
            warns.append(msg)
            print(c("y", f"      ⚠️ {msg}"))
        else:
            problems.append(msg)
            print(c("r", f"      ❌ {msg}"))
    elif not cur and not cur_cards:
        warns.append("无可断言的当前值（命中全部被判为历史引用）")
        print(c("y", "      ⚠️ 无可断言当前值（命中全部为历史引用）"))
    else:
        want = (true_q["共振"], true_q["背离"], true_q["暗线"], true_q["双冷"])
        bad = [h for h in cur if h["vals"] != want]
        distinct = {h["vals"] for h in cur}
        if len(distinct) > 1:
            problems.append(f"「当前值」象限出现 {len(distinct)} 种互不相同的写法：{sorted(distinct)}")
            print(c("r", f"      ❌ 当前值不同源：{sorted(distinct)}"))
        if bad:
            problems.append(f"{len(bad)} 处「当前值」与数据侧不一致")
            for h in bad:
                print(c("r", f"      ❌ L{h['line']} @{h['span'][0]} [{h['sect']}] ({h['form']})"))
                print(f"           页面  {h['raw']}")
                print(f"           数据  {true_str}")
        if not bad and len(distinct) == 1:
            print(c("g", f"      ✅ 与数据侧一致（{len(cur)} 处）"))

    # ── (c) 四卡逐卡断言 ──────────────────────────────────
    if cards:
        want_map = {k: true_q[k] for k in QUADS}
        # 同一象限出现两种不同卡值 → 页面自相矛盾
        seen = {}
        dup = []
        for h in cur_cards:
            seen.setdefault(h["quad"], set()).add(h["val"])
        for q, vs in seen.items():
            if len(vs) > 1:
                dup.append(f"{q}{sorted(vs)}")
        cbad = [h for h in cur_cards if h["val"] != want_map[h["quad"]]]
        if dup:
            problems.append(f"四卡同象限出现多种值：{'、'.join(dup)}")
            print(c("r", f"      ❌ 四卡同象限不自洽：{'、'.join(dup)}"))
        if cbad:
            problems.append(f"{len(cbad)} 处「四卡当前值」与数据侧不一致")
            print(c("r", f"      ❌ 四卡 {len(cbad)} 张与数据侧不一致："))
            for h in cbad:
                print(f"           L{h['line']:<6} @{h['span'][0]:<8} [{h['sect']}]  "
                      f"{h['raw']}  → 数据侧 {h['quad']} = {want_map[h['quad']]}")
        elif not dup:
            print(c("g", f"      ✅ 四卡 {len(cur_cards)} 张逐张与数据侧一致"
                         f"（共振 {want_map['共振']} / 背离 {want_map['背离']} /"
                         f" 暗线 {want_map['暗线']} / 双冷 {want_map['双冷']}）"))

    if unk:
        problems.append(f"{len(unk)} 处象限写法无法判定当前/历史（须人工确认）")
        print(c("r", f"      ❌ {len(unk)} 处命中无法判定当前/历史："))
        for h in unk:
            print(f"           L{h['line']:<6} @{h['span'][0]:<8} [{h['sect']}]  {h['raw']}")

    # ── [2] 归因句复核提醒 ────────────────────────────────
    print(f"  [2] 归因 / 迁移叙述复核（软提示）")
    attr_pos = []
    for k in ATTRIB_KEYS:
        for m in re.finditer(re.escape(k), text):
            attr_pos.append((m.start(), m.group(0)))
    if attr_pos:
        print(f"      检测到 {len(attr_pos)} 处「迁移主因 / 象限迁移」类叙述 —— "
              f"象限数字变更时须一并复核（脚本不代改）")
        for pos, k in sorted(set(attr_pos))[:6]:
            print(f"        L{line_of(text, pos):<6} [{section_of(text, pos)}]  {k}")
        if problems:
            warns.append("象限数字有变更 → 请复核上述「迁移主因」句是否仍成立")
    else:
        print("      （未检测到归因句）")

    # ── BOM 与副本 ───────────────────────────────────────
    if not bom_ok:
        problems.append("analysis.html 缺少 UTF-8 BOM")
    if os.path.exists(DEPLOY_ANALYSIS):
        dtext = open(DEPLOY_ANALYSIS, encoding="utf-8").read()
        if dtext != text:
            problems.append("root ↔ deploy 的 analysis.html 内容不一致")
            print(c("r", "      ❌ root ↔ deploy 的 analysis.html 不一致"))
        else:
            print(c("g", "      ✅ root ↔ deploy 的 analysis.html 一致"))
    if os.path.exists(DEPLOY_CROSS):
        try:
            dq, _ = quadrant_true(DEPLOY_CROSS)
            if dq != true_q:
                problems.append(f"root ↔ deploy 的 cross_analysis 象限不一致（{true_q} vs {dq}）")
                print(c("r", f"      ❌ root↔deploy cross_analysis 象限不一致：{true_q} vs {dq}"))
        except Exception as e:
            warns.append(f"deploy cross_analysis 读取失败：{e}")

    # ── --fix ────────────────────────────────────────────
    if args.fix:
        want = (true_q["共振"], true_q["背离"], true_q["暗线"], true_q["双冷"])
        want_map = {k: true_q[k] for k in QUADS}
        slash_str = "%d/%d/%d/%d" % want
        out = text
        n_full = n_slash = n_card = 0
        # 目标 = 全式/简写的当前值异值 + 四卡的当前值异值；从后往前替换避免位移
        targets = [(x, None) for x in cur if x["vals"] != want]
        targets += [(x, want_map[x["quad"]]) for x in cur_cards
                    if x["val"] != want_map[x["quad"]]]
        for h, card_val in sorted(targets, key=lambda t: -t[0]["span"][0]):
            s, e = h["span"]
            if h["form"] == "full":
                rep, n_full = true_str, n_full + 1
            elif h["form"] == "slash":
                rep, n_slash = slash_str, n_slash + 1
            else:
                rep = (h["quad"] + (" " + h["letter"] if h["letter"] else "")
                       + " = " + str(card_val))
                n_card += 1
            out = out[:s] + rep + out[e:]
        n = n_full + n_slash + n_card
        if n:
            with open(ANALYSIS, "w", encoding="utf-8") as f:
                f.write(out)
            # 同步 deploy
            if os.path.exists(DEPLOY_ANALYSIS):
                with open(DEPLOY_ANALYSIS, "w", encoding="utf-8") as f:
                    f.write(out)
            print("─" * 74)
            print(c("g", f"  🔧 --fix 已替换 {n} 处（全式 {n_full} / 简写 {n_slash}"
                         f" / 四卡 {n_card}）→ 当前值 {true_str}"))
            print("     （历史引用未动；root + deploy 已同步写入）")
            print(c("y", "     ⚠️ 仍需人工/agent 复核归因句与结论层表述，并重跑排版门禁"))
        else:
            print("─" * 74)
            print("  🔧 --fix：无需替换（当前值已与数据一致）")
        # 修完复检
        text2 = open(ANALYSIS, encoding="utf-8").read()
        hits2 = scan(text2)
        cur2 = [h for h in hits2 if h["kind"] == "cur" and h["form"] != "card"]
        cards2 = [h for h in hits2 if h["kind"] == "cur" and h["form"] == "card"]
        bad2 = [h for h in cur2 if h["vals"] != want]
        bad2 += [h for h in cards2 if h["val"] != want_map[h["quad"]]]
        if not bad2 and (cur2 or cards2):
            fix_resolved = True
            print(c("g", f"  ✅ 复检通过：全部 {len(cur2)} 处「当前值」"
                         f"+ {len(cards2)} 张四卡 = 数据侧真实分布"))

    # ── 结论 ─────────────────────────────────────────────
    # `--fix` 已把机械项修好 → 只保留「非象限类」问题继续拦截
    # （象限类问题形如「N 处当前值不一致」「不同源」「无法判定」——它们在 --fix 后已消解）
    if fix_resolved:
        problems = [p for p in problems if not any(k in p for k in QUAD_PROB_KEYS)]
        if not problems:
            print("═" * 74)
            print(c("g", "  ✅ 通过（--fix 已修复全部机械项）"))
            print(c("y", "  ⚠️ 仍需人工/agent 复核：「迁移主因」等归因句与结论层表述是否仍成立；"))
            print(c("y", "     并重跑 check_analysis_style.py / patch_dk_css.py --check 后再提交"))
            print("═" * 74)
            return 0

    print("═" * 74)
    if problems:
        print(c("r", "  ❌ 未通过 —— 叙述与数据不一致"))
        for p in problems:
            print(f"     · {p}")
        print()
        print("  修复：")
        print("     python3 review/check_narrative_consistency.py --fix   # 机械修数字")
        print("     → 再复核归因句 / 结论层  → 重跑 check_analysis_style.py 与")
        print("       patch_dk_css.py --check  → 同步 deploy → 提交")
        print("═" * 74)
        return 1
    if warns:
        print(c("y", "  ⚠️ 通过（含提醒）"))
        for w in warns:
            print(f"     · {w}")
        print("═" * 74)
        return 0
    print(c("g", "  ✅ 通过 —— 页面象限与数据产物一致，副本同步"))
    print("═" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
