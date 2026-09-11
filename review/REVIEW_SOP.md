# 每日复盘推演 SOP（标准作业流程）

> 适用：任何会话（本机 / 手机端）收到「推演」「盘前推演」「22:00 盘中推演」「收盘复盘」指令时执行。
> 固化日期：2026-09-03　工作目录：`/Users/samt/golden_stock_observer`

## 步骤 0 · 前置同步（每次推演必做）

```bash
bash review/sync_feed_before_review.sh
```

作用：
1. `git pull` 拉取仓库最新（拿到浏览器 / 手机端投喂的新素材与推演请求）
   - 工作区有未提交改动时会跳过 pull（正常，推演结束统一提交时会 rebase）
2. 归档 `feed/inbox/` 新投喂（`feed_archive.py` → `feed/archive/YYYY-MM-DD/`，自动更新 `feed_index.json`）
3. 读取 `commands/pending/` 的推演请求备注并归档到 `commands/done/`

> 说明：投喂以**本机 agent 处理为主**，浏览器投喂是突发补充；手机端推演命令一天 ≤5 次。
> 因此**不做常驻轮询**，只在推演时按需跑一次即可。

## 步骤 1 · 抓数据

| 推演类型 | 抓什么 | 注意 |
|---|---|---|
| 盘前版（09:05） | 昨夜美股收盘（akshare `stock_us_daily`）+ 今早亚太开盘（新浪 znb 日韩 + fengle 韩存储双雄） | A股 9:30 前**禁跑全量** `fetch_daily_review_market.py`（会把 A股/商品/汇率刷成开盘前状态），只更新 `us_kline` + `asia` |
| 盘中版（22:00） | 美股盘中 1h（gtimg）+ ADP/NFP 预期 | 产物要标注「盘中 1h」+ 风险声明，不是收盘价 |
| 收盘复盘（15:00 后） | A股收盘 + 龙虎榜 + 板块资金流 | 可跑全量 |

写入 `data/daily_review/market.json`，**改完同步 deploy 副本**。

## 步骤 2 · 读素材

- 当日归档：`feed/archive/YYYY-MM-DD/F*.txt`（`F{YYYYMMDD}-{当日序号:03d}`）
- 前一日归档（仍在线参考）
- 用 `Read` 工具**实际读取**图片/PDF（模型具备视觉能力，禁止靠文件名推断）

## 步骤 3 · 改写 analysis.html 段落

需要更新的段落：

| 段 | 内容 | 关键点 |
|---|---|---|
| 0 | 结论先行速览卡 | 🚨 必须带 `data-preopen` 等属性（防 JS 覆盖） |
| 0.5 | 深度判读 + 四象限 | 需含 2×2 grid（自检第 3 项） |
| 1 | 昨日 A 股走势总结 | 每日滚动（指数 / 量能 / 资金流向 / 4~5 条结构特征） |
| 1.1 | 当日 TOP10 | 🚨 标题日期必须写「**最新交易日**」而非硬编码日期（数据由 JS 从 `top10_history.json` 动态加载；写死日期会每天显示过期） |
| 1.2 | 当日金钻（三重门控合并去重） | 🚨 **纯动态渲染**：HTML 只留容器 `<div id="drTblDiamond"></div>`，标题固定「1.2 · 当日金钻 · 三重门控合并去重（动态）」；数据全部由 `drLoadDiamond()` 从 `gate_data.json`（门控 + `chan` 缠论明细）JOIN `valuation_band` / `institutional_flow` / `golden_diamond_history` 渲染。**禁止在 HTML 内写死金钻数据，禁止回退为「三个门控分类」分表版式**（与 V3 独立版 1.2 段同构；改动日期 2026-09-10）。⚠️ 自包含 `<style>` **必须保留** `.dr-scroll{overflow-x:auto}` + `.dr-scroll td,.dr-scroll th{white-space:nowrap}`（该 style 注入晚于 index.html，缺失会导致 12 列表格被 `.dr-tbl td` 的 `white-space:normal` 覆盖而严重折行） |
| 3 | 隔夜美股双日表 | 🚨 **硬编码**，必须手动滚动到最新双日 |
| 4 | 重点宏观 | 🚨 **硬编码，必须每日滚动**（2026-09-11 补入清单）：① 中国段（最新国内数据，无新数据须显式标注）② 海外段（美债收益率 / 加息概率 / 油价 / 贵金属）③ **今日事件日历**（必须是**当天**日期，禁留前一日事件） |
| 5 | 重点科技 | 🚨 **硬编码，必须每日滚动**（2026-09-11 补入清单）：存储 / 半导体、光通信 / CPO、AI 应用 / 海外巨头、能源资源 **4 线**，每线数据须取**最近一个美股收盘日**，禁留前一日预判 |
| 5.5 | 产业链/景气度评估 | 🚨 **硬编码，必须每日滚动**（2026-09-11 补入清单）：存储 / 光通信 / 油运 / 金刚石 / 消费 **5 线**，每线须含「**今日观察要点**」（当日口径的观察/风控语，禁留前一日「9/xx 竞价看…」式预判） |
| 7.1 | K3 产业信号验证 | 主题 / 验证 / 内容 三列表。🔴 **每行「内容」格的最后一句结论句必须带 `class="k3c k3c-{go\|cond\|risk\|verify}"` 语义色**（2026-09-11 起）：手写裸文本后跑 `python3 build_k3_conclusions.py` 自动上色。详见「步骤 3.6」 |
| 7.2 | 重点观测股推演 | 🔴 **禁止手写，改由脚本生成**（2026-09-11 改造）：`python3 build_obs_section.py` → 分层 L1/L2 + 原生 `<details>` 纯 CSS 折叠卡。L1 全池关键位从 `obs_deduce_latest.json` **机械计算**（零人工估计、日期自动滚动）；L2 重点票三情景由 agent 写 `output/obs_scenarios.json`。**红线**：L1 触发线=纯客观表述（无动作词）；L2 动作列固定「推测专家操作」口径 + 段首红线声明。详见「步骤 3.5」 |
| 7.3 | 次日开盘指引 | 🚨 标题必须含「K3」+ 周几特征（防覆盖成「7 ·」） |
| 9 | 来源 | 更新素材份数 |

## 步骤 3.5 · 生成 7.2 段（脚本，非手写）

```bash
cd /Users/samt/golden_stock_observer
python3 build_obs_section.py --data-date 2026-09-10   # 🔴 建议显式指定数据日（见下）
python3 build_obs_section.py --dry-run                # 只出片段 output/obs_section.html，不改页面
```

🔴 **数据日锚定（2026-09-11 补 · 实测踩到）**：脚本默认读 `output/obs_deduce_latest.json`，但该文件**永远是最新交易日**——而盘前推演页面用的是**上一交易日**数据。例：9/11 盘前页面口径为 9/10 收盘，但 16:40 的 `com.goldenstock.backtest` 调度已把 `obs_deduce_latest` 刷成 **9/11**，此时不带参数运行会让 L1 关键位与页面其他段落**数据日错位**。故：
- 盘前推演 → **必须** `--data-date <上一交易日>`（从 `data/daily_review_history/<T>/obs_deduce_auto_<T>.json` 读）
- 脚本会校验 `obs_scenarios.json` 的 `data_date` 与观测池 `date`：**不一致直接报错退出**（防用错数据日），可用 `--allow-mismatch` 强制但会导致 L1/L2 口径不一致
- 7.2 段标题内的「数据日 YYYY-MM-DD 收盘」由脚本按实际数据源自动写入，**不要手改**

**分层结构（用户 2026-09-11 拍板）**

| 层 | 覆盖 | 内容 | 产出方式 |
|---|---|---|---|
| **L2** | 重点 5–8 只 | 三情景（A/B/C）+ 概率 + 机制路径 + 推测专家操作 | agent 写 `output/obs_scenarios.json` |
| **L1** | 全池（当前 32 只） | 支撑 MA5/MA10、压力 high10、结构位 low10、MA5 偏离、5 日、量比 + 客观触发线 | **脚本机械计算**，零人工估计 |

**L2 选票四象限**（沿用现有样本，可调）：① A股持仓 ∩ 观测池 ② 强势核心（MA5 偏离最低的多头）③ 超买风险（MA5 偏离最大）④ 事件负向最明确 ⑤ 弱势代表（空头 + 跌幅最大）。

**关键实现约束**
- 交互 = 原生 `<details>` + 纯 CSS：`analysis.html` 经 `ana.innerHTML = t` 注入后 `<script>` **不执行**，但 `<style>` 会被 `drScopeInjectedStyles` 作用域化后生效 → 纯 CSS 是唯一零 JS 依赖的可行路径。
- 样式块以 `/* OBS-FOLD-CSS v1` 为标记**整块替换**（可安全迭代脚本）；`.obs-*` 类名全局作用域，改名前先 grep 主站是否已占用 `obs-` 前缀。
- 7.2 段边界锚点：`<!-- 7.2 重点观测股` → `<!-- 7.4 操作预案`。⚠️ **实际段落顺序是 7.2 → 7.4 → 7.3**，不要按序号去找 `7.3` 当终点。
- ⚠️ **跳过此步 → 7.2 段回退为手写静态大表**（脚本产出不参与其他 rebuild 流程，必须显式调用）。

## 步骤 3.6 · 7.1 段结论句语义色（脚本上色，非手写）

```bash
cd /Users/samt/golden_stock_observer
python3 build_k3_conclusions.py            # 生成 + 替换 root 与 deploy 副本（幂等，可反复跑）
python3 build_k3_conclusions.py --dry-run  # 只报告分类结果，不写文件
```

**背景（2026-09-11 用户反馈）**：7.1 每行「内容」格最后一句是结论句，原先只用 `<b>` 加粗 → 不够醒目，且无法区分四种不同性质的结论。

**四类语义色（与第二列 `dr-up`/`dr-caution`/`dr-dn` 色系呼应）**

| 类名 | 语义 | 颜色 | 呼应第二列 | 典型句式 |
|---|---|---|---|---|
| `k3c-go` | 可执行·相对占优 | 红 | ✅ 真共振 | 「…可作为…」「…可低吸…」 |
| `k3c-cond` | 有条件·待确认 | 橙 | ⚠️ | 「但…」「…尚需…」「…未确认」 |
| `k3c-risk` | 风险·回避 | 绿 | ❌ 伪共振 | 「不追高/不补仓/不接刀」「…承压」「…不成立」 |
| `k3c-verify` | 待验证变量·方法论 | 蓝 | （跨行） | 「验证变量：…」「需以…验证」 |

**分类为关键词规则**（`RULES` 顺序敏感：verify → risk → go → cond 兜底），脚本会打印**每一行的判定依据**；有新语气未覆盖时打印 ⚠️「未匹配」清单，此时需人工在 `analysis.html` 里直接指定 class 后重跑。

**关键实现约束**
- 结论句定位 = 每行第 3 个 `<td>` 内**最后一个 `<b>…</b>`**（统计已验证 11/11 成立）。脚本保留 `<b>` 只加外层 `<span>` → 即使 CSS 失效也仍是加粗，不会退化。
- 样式块以 `/* K3C-CONCLUSION-CSS v1` 为标记**整块替换**（可安全迭代脚本）；`.k3c*` 为类选择器，**不受** `drScopeInjectedStyles` 裸标签改写影响。
- 图例 `.k3c-legend` 必须插在 `<table>` **之前**（放 `<table>` 内会被浏览器 foster-parent 移出）。
- 两主题自适应：底色 in default（浅色）`.13~.15` / `@media (prefers-color-scheme:dark)` `.16~.17`；字色与色条用 `var(--red/orange/green/blue)`（这 4 个变量在暗色分支未重定义，两主题同值）。
- `review/check_analysis_style.py` 已加 **[8/8] 守卫**：7.1 段每一数据行都带 `k3c-*` + CSS 块=1 + 图例=1，任一不满足即 ❌ 并提示跑本脚本。
- ⚠️ **跳过此步 → 7.1 段结论句退回「只有加粗」的旧观感**（用户明确反馈过的问题）。

## 步骤 4 · 更新 feed_review

`output/feed_review_latest.json`：
- `feeds`：当日全部素材（从 `feed_index.json` 取，带 digest）
- `ai_synthesis`：`conclusion_first` / `theme_resonance` / `holding_map` / `t1_radar` / `risks`
- 🚨 **数据契约**：`holding_map.theme_aligned/caution/us` 必须是**字符串数组**（前端 `chips()` 硬编码，dict 会显示 `[object Object]`）；`theme_resonance` 每项需 `weight` + `related_stocks`（否则显示 `[]`）

写三处：`output/` + `output/feed_review_YYYY-MM-DD.json` + `deploy/output/`

## 步骤 5 · 防坑检查（逐项确认）

**排版（design token 体系）**
- 语义色 class：`dk-main`（红）/ `dk-caution`（橙）/ `dk-risk`（红加粗）/ `dk-data`（蓝）/ `dk-neutral`（灰）/ `dk-dn`（绿·跌）
- 🆕 **7.1 段结论句语义色**（2026-09-11）：`k3c-go`（红·可执行）/ `k3c-cond`（橙·有条件）/ `k3c-risk`（绿·回避）/ `k3c-verify`（蓝·待验证）— 见「步骤 3.6」
- 🆕 **未定义类 = 静默无色**（2026-09-11 自检教训）：实测 `dk-dn`(13 处)、`dr-caution`(4 处)、`dr-wrap`(54 处) 在 HTML 中被使用但**全站无 CSS 定义** → 这些标记完全不起作用，用户看到的只是普通文字。**新增 class 时必须在 `analysis.html` 自包含 `<style>` 内同步补定义**，`[9/9]` 守卫会红灯提示。
- 字号统一 12.5px（占比需 >80%）
- 表格：`.dr-tbl td` 默认换行（三处 index CSS 已治本），长文本 td 加 `dr-wrap`

**防 JS 覆盖**
- 0 段：`data-preopen` 属性存在 → `drDeriveSections` 会跳过
- 7.3 段：标题含「K3」/ 周几 + 正文含「大势预判 / 主线策略 / 回避清单」→ 跳过改写
- 1.2 段：容器 `id="drTblDiamond"` 存在 + 标题含「三重门控合并去重」→ 内容由 `drLoadDiamond()` 渲染，HTML 内**不得**出现金钻股票行（防写死数据与分表版式回退）

**7.2 段（分层折叠卡 · 2026-09-11 改造）**
- 跑完 `build_obs_section.py` 后，自检行须显示 `折叠卡 = L1 全池 32 只 + L2 重点 N 只`（当前 39），数量不符会打 ✗
- `analysis.html` 内 `/* OBS-FOLD-CSS v1` 出现次数须 **= 1**（>1 = 样式块重复插入，说明标记查找失效）
- root 与 deploy 副本须逐字节一致（脚本已自动同步，异常时手动 `cp`）
- 红线：L2 动作列表头固定「推测专家操作」，段首红线声明（不构成对读者的建议）须在
- 场景数据滞后检查：`obs_scenarios.json` 的 `data_date` 须与 `obs_deduce_latest.json` 的 `date` 一致，脚本会在不一致时打 ⚠

**7.1 段（结论句语义色 · 2026-09-11 改造）**
- 跑完 `build_k3_conclusions.py` 后，自检行须显示 `数据行 = 已上色`（当前 11/11），不等会打 ⚠️ 未匹配清单
- `analysis.html` 内 `/* K3C-CONCLUSION-CSS v1` 出现次数须 **= 1**，`class="k3c-legend"` 须 **= 1**
- 自带 `[8/8]` 守卫已覆盖以上三项，直接跑 `python3 review/check_analysis_style.py` 即可

**注入样式作用域化（2026-09-10 治本）**
- `analysis.html` 自包含 `<style>` 里的 `body{padding:20px;max-width:980px}` / `:root{...}` / `h2,h3,h4` / `code` / `b,strong` 等**越界规则**，经 `renderDailyReview()` 的 `ana.innerHTML = t` 注入后会**全局生效** → 曾把整站限宽 980px（`.main` 的 1480px 沦为死代码）并覆盖主站配色变量与字体。
- 现状：`index.html` 的 `drScopeInjectedStyles(ana)` 在注入后自动把这些规则作用域化到 `#drAnalysis`（body/html 丢弃、`:root`→`#drAnalysis`、裸标签加前缀、`.dr-*` 类规则保留）。**analysis.html 无需修改**——其中的 `body{max-width:980px}` 是为 file:// 独立打开的限宽阅读体验而保留。
- 自检 `[7/7]` 守卫三份 index 是否保留该调用；重构 `renderDailyReview()` 时若丢失调用，整站会再次变窄。

**双写同步（防回退）**
```bash
cp data/daily_review/analysis.html deploy/data/daily_review/analysis.html
cp data/daily_review/market.json  deploy/data/daily_review/market.json
# index.html ×3：index.html / index_template.html / deploy/index.html
```
> 🔴 任何只改 `index.html` 不反向同步 `index_template.html` 的改动，都会被 `update_data.sh` 重建时覆盖回退。

**自检**
```bash
python3 review/check_analysis_style.py   # 老站排版：必须全过（[0] BOM + [9/9] 未定义类 + [10/10] 空转引用 + [11/11] 段落顺序/段号）
python3 review/check_v3_style.py         # V3 独立版：四副本一致性 + 语义色 + 兜底（必须全过）
python3 review/check_market_json.py      # 数据完整性：us_kline 不得有 null close（必须 ✅）
```

> 🔴 **2026-09-11（晚）· 7.x 段落顺序与段号复发 bug（用户报「7 段排在 7.4 后、7.3 未见」）**
> 两个都**有前科**，必须机器化守卫：
> ① **段落顺序错**：`analysis.html` 的 7.x 一直是 `7.1 → 7.2 → 7.4 → 7.3`（e545530 起 7 个版本全如此），
> 而 `build_obs_section.py` 的 `END_ANCHOR` 还写着 `"<!-- 7.4 操作预案"` —— **迁就了错误顺序**、把它固化。
> **已重排为 `7.1 → 7.2 → 7.3 → 7.4`**，`END_ANCHOR` 同步改为 `"<!-- 7.3 次日开盘指引"`（7.2 的下一段）。
> 🔴 **两者必须同时改**，否则切片边界会吃掉错内容。
> ② **段号被 JS 抹掉**：`drDeriveSections` 里 `h7.textContent = '7 · 次日开盘指引（…）'` 硬编码**裸段号**，
> 把 7.3 覆盖成「7 ·」。该行曾在 `229a20a` 修为 `'7.3 · '`，但 `0070ddd` 重构时**基于旧副本编辑 → 静默回退**
> （与铁律 9 注入器快照回退同源）。**治本 = 不再写死段号**，改为从原标题提取 7.x 前缀（兜底 7.3），抗内容变化与重构覆盖。
> > 修法要点：改这类「JS 覆盖标题」的代码时，**永远从原文提取段号**（`match(/^(7\.\d+)/)`），不要硬编码 —— 硬编码必被下次重构带走。
> ③ **新增守卫 `[11/11]`**：校验 ① 7.x 顺序（必须 7.1/7.2/7.3/7.4 各一段且升序）；② 5 个文件不得出现裸段号硬编码
> （`textContent = '7 · ` 形式）。已反向测试：顺序颠倒 → 红灯退出码 1；插回裸段号 → 红灯退出码 1。
> ⚠️ **`analysis.html` 由 agent 每日手写**：新写时 7.x 段必须按 `7.1 → 7.2 → 7.3 → 7.4` 排列，否则 `[11/11]` 红灯。

> 🔴 **2026-09-11 自检发现（已治本，留档防复发）**
> ① **`rebuild_html.py` title 版本号拼接 bug**：原实现 `html.replace('兜金观测 — 量化信号池 v', '…v' + today)`
> 用**不含版本号的旧串**做替换，模板里已有 `v2026-08-29` → 生成 `v2026-09-092026-08-29`（线上实测污染）。
> 已改为正则 `re.sub(r'(…信号池 v)[\d\-]*', …)` 整体吃掉旧版本号 + 命中数必须 =1 否则中止。
> **新增 title 后需检查版本号只有一处、格式为 `vYYYY-MM-DD`。**
> ② **`index_hide89.html` 双份漂移**：`review_v3/index_hide89.html` 与 `deploy/review_v3/index_hide89.html`
> 语义相同（均 = index.html 的同内容副本，不含隐藏 8/9 段逻辑），但本地 deploy 侧曾落后线上 1 个版本
> （86801 vs 88533 字节，停在 2026-09-08 的旧实现：`num()` 无兜底 → 全页卡「加载中…」；缠论列读 obs_deduce → 全空）。
> SOP 推送清单里仍列着它 → **一旦推送即把线上正确版回退成旧 bug 版**。
> 治本：V3 视为**四副本同内容结构**，`check_v3_style.py [1/7]` 强制四份逐字节一致；改动后必须 `cp` 到其余三份。

> 🔴 **2026-09-11 下午 · 空转容器清理（用户授权「空转容器可清理」）**
> 主题 = 静默失效第 2 类「**JS 引用无容器**」：页面不报错、不崩溃，只是功能永不生效。
> **清理清单（共 10 个容器 + 2 个函数）**：
> | 对象 | 位置 | 证据 | 处置 |
> |---|---|---|---|
> | `drTblA` / `drTblH` / `drTblUs` | `drFillTables()` 内 3 行 | 容器只在 `data/daily_review_history/` 历史归档，当前 analysis.html 已无 | 删 3 行；**保留 `drTblHK`**（容器仍在，函数整体保留） |
> | `drTblObs` | `drLoadObserveStocks()` | 函数首行 `if (!box) return` 即退出 → 整函数（含标题日期动态化）死代码 | 删函数 + 调用（`drNextBizDay` 另有 2 处使用，保留） |
> | `drCmdBtn` | `drCmdModalInit()` | 依赖的按钮不存在；其写入目标 `commands/pending/` 目录已废弃 | 删注释块 + 61 行函数 + 调用 |
> | `allGrid` | 全局 `renderAll()` | 无 `data-tab="all"` 按钮触发，且**无 null 守卫**（定时炸弹型） | **加守卫**，保留函数（「全部」tab 是否永久废弃交用户决定） |
> | `drTblAsia` / `drTblComm` / `drAsiaNote` | `analysis.html` 静态 HTML | 零 JS 引用 → 内含的「日韩数据加载中…」「商品利率数据加载中…」**永久残留** | 删容器（`drAsiaTable` 要找的含 KOSPI 的 `table.dr-tbl` 在 analysis.html 中本就不存在，该函数早已静默 return） |
> **未动（有引用方，非遗留）**：`drNewsPool`（`review/build_share_html.py` 引用）、`drBacktestBody`/`drMacroBody`/`drNewsBody` 等 6 个（`inject_daily_auto_blocks.py` 注入）、`drCmdModal`（JS 动态创建）。
> **防呆**：新增 `check_analysis_style.py [10/10]` 空转引用守卫 —— 孤儿 id 允许存在，但**每个引用点必须有空值守卫**，无守卫即红灯退出码 1（已反向测试）。
> ⚠️ **analysis.html 是 agent 每日手写的**：生成时**不要再写**上述已删除的占位容器（尤其 `<div id="drTblAsia">日韩数据加载中…</div>` 这类，写了就是永久残留）。

> 🔴 **全站语义色板（2026-09-11 统一 · 用户授权自行裁决）**
> `dk-risk` 由**红**改**绿**：其标注内容全是跌向/利空（低开偏弱、杀跌、补跌、杀估值、外盘收跌），
> 按 A 股「涨红跌绿」惯例应为绿；此前与 7.1 段 `k3c-risk`(绿)、第二列 `dr-dn`(绿) **同名不同色**，同一语义两种颜色。
> **统一后色板**（老站 `analysis.html` 与 V3 `review_v3/index.html` 一致）：
> 红 `--red` = 看多/主线/可执行（`dk-main`/`k3c-go`）｜ 橙 `--orange` = 观察/有条件（`dk-caution`/`k3c-cond`）
> ｜ 绿 `--green` = 利空/回避/风险/跌（`dk-risk`/`k3c-risk`/`dk-dn`/`dr-dn`）｜ 蓝 `--blue` = 数据/方法论（`dk-data`/`k3c-verify`）｜ 灰 `--text-muted` = 中性。

> 🔴 **2026-09-10 事故**：`us_kline.us_sox.latest.close = null` → V3 页 `renderUsDual`
> 直接 `.toLocaleString()` 抛 TypeError → `main()` reject → **全页永久卡「加载中…」**（老站不受影响）。
> 双治本：① V3 页新增 `num()` 空值兜底 + `main()` 逐段 try/catch 隔离（单段失败不再拖垮全页）；
> ② 新增 `review/check_market_json.py` 门禁，market.json 每次更新后必跑。
> 新增 `us_kline` 标的时必须同时给 `prev.close` 与 `latest.close`；
> 若只有 `latest.close` 与 `prev.chg_pct`，可用 `prev.close = latest.close / (1 + chg_pct/100)` 反推。

**浏览器实测**：本地 `http://127.0.0.1:8080/`（deploy 为根）→ 登录 → 每日复盘 → 检查：
- 0 段速览卡 / 7.3 标题未被覆盖
- 表格 0 溢出、`[object Object]` = 0、`undefined` = 0

**V3 页实测**：`http://127.0.0.1:8080/review_v3/` → 检查：
- **无任何「加载中…」残留**（全站渲染完成的唯一判据）
- 0 段「推演开盘」显示 agent 结论（非规则打分回退）
- 控制台无 `[V3] 段渲染失败` 报错
- 🆕 **结论卡按性质着色**（2026-09-11 改造）：`ai_synthesis.conclusion_first` 的每个 `【标题】正文` 块由 `renderConclusion()`
  按标题关键词分类 → 左侧色条 + 标题色 + 首句加粗（`rc-risk` **绿** / `rc-main` 红 / `rc-caution` 橙 / `rc-data` 蓝 / 无匹配则金）。
  > 🔴 2026-09-11 色板统一：`dk-risk` 由红改绿（= 利空/回避/风险），与老站 7.1 的 `k3c-risk`(绿) 一致；详见上方「全站语义色板」。
  分类规则在 `renderConclusion` 内的 `RC` 数组（顺序敏感：risk → caution → data → main 兜底）。

**V3 副本与代码规则（2026-09-11 立）**
- V3 是**四副本同内容**结构：`review_v3/index.html` / `review_v3/index_hide89.html` /
  `deploy/review_v3/index.html` / `deploy/review_v3/index_hide89.html`。
  改任一份后**必须 `cp review_v3/index.html` 到其余三份**，否则 `[1/7]` 红灯（且推送旧副本 = 线上回退）。
- V3 固定暗色主题（无 `prefers-color-scheme` 分支），语义色变量与老站同名（`--red/--orange/--blue/--green`）。
- 文本归一化必须用 `asArr` / `asText`（白名单含 `event`）/ `asTxt` 三件套，渲染一律 `esc(asTxt(x))`；
  **禁用** `esc(asText(x) || x)`（对象会变 `[object Object]`）——`[4/7]` 守卫会红灯。

## 步骤 6 · 提交推送

沙箱环境下 git 写操作会被 `index.lock`（带 `com.apple.provenance`）阻塞，**需交用户终端执行**：

```zsh
cd /Users/samt/golden_stock_observer && rm -f .git/index.lock && git add -A data/ feed/ review/ commands/ index.html index_template.html && git add -f deploy/data/daily_review/analysis.html deploy/data/daily_review/market.json deploy/output/feed_review_latest.json deploy/output/feed_review_YYYY-MM-DD.json deploy/index.html && git commit -m "..." && git pull --rebase origin main && git push origin main
```

> V3 相关改动（**四副本同内容**：`review_v3/index.html` + `review_v3/index_hide89.html` + `deploy/review_v3/` 同名两份）
> 若不在 `review/` 下，需显式逐个点名（新增文件每个都要带 `-f`）：
> `git add review_v3/index.html review_v3/index_hide89.html && git add -f deploy/review_v3/index.html deploy/review_v3/index_hide89.html`
> ⚠️ 2026-09-11 教训：**漏掉 `deploy/review_v3/index_hide89.html` 会留下旧版**，下次推送即回退线上正确版。
> 推送前先跑 `python3 review/check_v3_style.py`（`[1/7]` 四副本一致性必须通过）。

> 🔴 **`output/` 绝不能放进 `git add -A`**（2026-09-03/09-04 连续两次踩坑）：
> `output/` 在 `.gitignore` 里，显式 `git add -A output/` 会打印
> "The following paths are ignored by one of your .gitignore files: output" 并**以非 0 退出**，
> 导致 `&&` 链中断、commit 根本没执行（表现：看似跑过命令但线上没更新）。
> 正确做法：`-A` 只带未被忽略的目录（data/ feed/ review/ commands/），
> `output` 与 `deploy` 下的文件**逐个点名 + `-f`**（它们虽被 ignore 但已跟踪，点名即可加）。
>
> `deploy/` 与 `output/` 都被 `.gitignore` 忽略，`git add` 必须加 `-f`。

推送后校验：
```bash
python3 review/verify_push.py --git    # git 协议，无 rate limit
```

## 关键原则

- 推演产物是「分析」不是「执行」——**必须用户手动授权才推送上线**
- 09:05 与 22:00 框架相同，抓取数据不同
- 19:00–21:30 推演窗口已作废（捕获不到美股盘中数据）
- 22:00 版美股是盘中数据，须标注「盘中 1h」+ 风险声明
