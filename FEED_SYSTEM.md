# 投喂系统（Feed System）架构文档

兜来米金融 · 主站每日复盘投喂分析系统。四环节解耦：**投喂 → 归档 → 复盘 → 推送**，环节间仅以 JSON 衔接，可独立替换升级。

## 一、架构总览

```
┌────────────────────────────────────────────────────────────┐
│ ① 投喂入口（三式）                                          │
│    A. 目录式  feed_inbox/{日常投喂,专家投喂}/  丢文件即投喂    │
│    B. 网页式  deploy/feed_inbox.html          表单生成投喂文件 │
│    C. 对话式  专家对话「投喂：…」由 agent 调 feed_submit.py   │
├────────────────────────────────────────────────────────────┤
│ ② 自动归档  feed_archive.py                                │
│    扫描 inbox → feed_archive/YYYY-MM-DD/ → feed_index.json  │
│    命名规范: YYYY-MM-DD_来源_标题.ext；自动去重/关键词/补录   │
├────────────────────────────────────────────────────────────┤
│ ③ 定时复盘  daily_feed_review.py                           │
│    本地 launchd 19:30（周一~五）+ 云端 Actions 08:15 双跑     │
│    汇总当日投喂 + 拉 signals/golden_diamond → 交叉分析+预测  │
├────────────────────────────────────────────────────────────┤
│ ④ 结果推送  push_to_site.py + inject_feed_review.py        │
│    feed_review_latest.json → deploy/output/                 │
│    前端每日复盘 tab「投喂复盘」板块动态 fetch 渲染             │
└────────────────────────────────────────────────────────────┘
```

## 二、文件清单

| 文件 | 职责 |
|---|---|
| `feed_inbox/` | 投喂箱（日常投喂 / 专家投喂 两个子目录） |
| `feed_submit.py` | 投喂提交（A/C 共用，自动规范命名） |
| `feed_archive.py` | 自动归档 + 索引（去重 / 关键词 / 补录自愈） |
| `feed_archive/feed_index.json` | 检索索引（分类 / 来源 / 关键词 / 日期） |
| `daily_feed_review.py` | 复盘引擎（投喂 × 盘面交叉分析 + 规则预测） |
| `push_to_site.py` | 推送 feed_review JSON 到 deploy/output/ |
| `inject_feed_review.py` | 幂等注入前端「投喂复盘」板块（卡片 + JS） |
| `feed_inbox.html` | 网页投喂入口（部署于 deploy/） |
| `feed_review.sh` | 本地一键流程（归档→复盘→推送） |
| `com.goldenstock.feed.plist` | launchd 定时（周一~五 19:30） |
| `.github/workflows/feed-review-cloud.yml` | 云端补跑（周一~五 08:15） |

## 三、投喂命名规范

```
{YYYY-MM-DD}_{来源}_{标题}.{ext}
来源: 对话 / 研报 / 观点 / 文档 / 新闻 / 其他
示例: 2026-08-26_研报_光模块景气.txt
```

## 四、复盘产出结构（feed_review_latest.json）

```json
{
  "data_date": "2026-08-26",
  "generated_at": "...",
  "source": "local | cloud",
  "feeds": [ {category, source, title, keywords} ],
  "market": { signals: {...}, golden: {...}, top10: [...] },
  "cross_analysis": [ {feed, related_stocks, sentiment, verdict: 共振/背离/无匹配} ],
  "prediction": { bias: 偏多/中性/偏空, reasons, t1_focus, risks, pending_ai }
}
```

## 五、运维

- 本地一键：`bash feed_review.sh`
- 手动归档：`python feed_archive.py`（`--dry-run` 预览）
- 投喂：`python feed_submit.py --cat 日常 --src 研报 --title "光模块景气" --file a.pdf`
- 复盘：`python daily_feed_review.py [--date YYYY-MM-DD] [--no-feed]`
- launchd 启用：`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.goldenstock.feed.plist`
- 前端注入（升级时）：`python inject_feed_review.py`（幂等）

## 六、红线

1. **知识星球低频**：每星球每天 1 次检索（专家对话内），防拉黑
2. **数据隔离**：机游共振（lh_calendar）结论仅限主站复盘，副站（diamond_site）不得展示
3. **数据溯源**：投喂带来源标签，复盘文件可回溯
4. **预测边界**：规则预测为机械可解释结果，深度预测 `pending_ai=true` 待本机 agent / 专家补全
5. **不构成投资建议**：仅供个人学习优化金融知识
