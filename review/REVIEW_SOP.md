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
| 3 | 隔夜美股双日表 | 🚨 **硬编码**，必须手动滚动到最新双日 |
| 7.1 | K3 产业信号验证 | 主题 / 验证 / 内容 三列表 |
| 7.2 | 重点观测股推演 | 长文本 `<td>` 必须加 `class="dr-wrap"` |
| 7.3 | 次日开盘指引 | 🚨 标题必须含「K3」+ 周几特征（防覆盖成「7 ·」） |
| 9 | 来源 | 更新素材份数 |

## 步骤 4 · 更新 feed_review

`output/feed_review_latest.json`：
- `feeds`：当日全部素材（从 `feed_index.json` 取，带 digest）
- `ai_synthesis`：`conclusion_first` / `theme_resonance` / `holding_map` / `t1_radar` / `risks`
- 🚨 **数据契约**：`holding_map.theme_aligned/caution/us` 必须是**字符串数组**（前端 `chips()` 硬编码，dict 会显示 `[object Object]`）；`theme_resonance` 每项需 `weight` + `related_stocks`（否则显示 `[]`）

写三处：`output/` + `output/feed_review_YYYY-MM-DD.json` + `deploy/output/`

## 步骤 5 · 防坑检查（逐项确认）

**排版（design token 体系）**
- 语义色 class：`dk-main`（红）/ `dk-caution`（橙）/ `dk-risk`（红加粗）/ `dk-data`（蓝）/ `dk-neutral`（灰）
- 字号统一 12.5px（占比需 >80%）
- 表格：`.dr-tbl td` 默认换行（三处 index CSS 已治本），长文本 td 加 `dr-wrap`

**防 JS 覆盖**
- 0 段：`data-preopen` 属性存在 → `drDeriveSections` 会跳过
- 7.3 段：标题含「K3」/ 周几 + 正文含「大势预判 / 主线策略 / 回避清单」→ 跳过改写

**双写同步（防回退）**
```bash
cp data/daily_review/analysis.html deploy/data/daily_review/analysis.html
cp data/daily_review/market.json  deploy/data/daily_review/market.json
# index.html ×3：index.html / index_template.html / deploy/index.html
```
> 🔴 任何只改 `index.html` 不反向同步 `index_template.html` 的改动，都会被 `update_data.sh` 重建时覆盖回退。

**自检**
```bash
python3 review/check_analysis_style.py   # 必须 6/6 全过
```

**浏览器实测**：本地 `http://127.0.0.1:8080/`（deploy 为根）→ 登录 → 每日复盘 → 检查：
- 0 段速览卡 / 7.3 标题未被覆盖
- 表格 0 溢出、`[object Object]` = 0、`undefined` = 0

## 步骤 6 · 提交推送

沙箱环境下 git 写操作会被 `index.lock`（带 `com.apple.provenance`）阻塞，**需交用户终端执行**：

```zsh
cd /Users/samt/golden_stock_observer && rm -f .git/index.lock && git add -A data/ feed/ review/ commands/ index.html index_template.html && git add -f deploy/data/daily_review/analysis.html deploy/data/daily_review/market.json deploy/output/feed_review_latest.json deploy/output/feed_review_YYYY-MM-DD.json deploy/index.html && git commit -m "..." && git pull --rebase origin main && git push origin main
```

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
