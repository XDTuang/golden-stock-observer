# 方案 A：外部定时触发器 → GitHub workflow_dispatch

> 背景（2026-09-04 排查实证）：GitHub Actions 的 `schedule` 对这个仓库存在**队列积压延迟**。
> 9/1–9/3 三天每天 8 档**全部触发**，但除 UTC 06:15（北京 14:15，延迟 10–14 分钟）外，
> 其余 7 档全部延迟 20~314 分钟、落到收盘后 → `fetch_realtime.py` 判"非盘中"不写文件 → 云端盘中数据归零。
> `schedule` 由 GitHub 平台调度、免费账号优先级低，无法靠改档位根治 → 改用**外部定时器打 `workflow_dispatch`**（手动触发不受队列延迟影响，按下即跑）。

## 原理

```
腾讯云 SCF 定时触发器（北京 9:45-14:45 每 30 分钟）
        │  POST https://api.github.com/repos/XDTuang/golden-stock-observer/
        │      actions/workflows/realtime-monitor.yml/dispatches   (Bearer PAT)
        ▼
GitHub 立即新建 run（workflow_dispatch，无 schedule 排队）
        ▼
fetch_realtime.py 抓取 → 提交推送 realtime.json + deploy 副本
```

`realtime-monitor.yml` 已声明 `on: workflow_dispatch`（2026-09-01 起就带），**无需改 workflow**。

## 你需要准备的唯一东西：GitHub PAT

1. GitHub → 右上角头像 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. 填：
   - **Repository access**：Only select repositories → `XDTuang/golden-stock-observer`
   - **Permissions → Actions**：`Read and write`（触发 workflow_dispatch 必需；无需 Contents 权限）
   - Expiration：建议 90 天（到期后需重发，云函数内更新环境变量即可）
3. 生成后**立即复制保存**（只显示一次）。Token 形如 `github_pat_xxxxxxxx`。

## 载体一：腾讯云 SCF 云函数（推荐，你有腾讯云环境）

1. 腾讯云控制台 → 云函数 → 新建（**从头开始**）：
   - 函数名：`gh-dispatch-realtime`；运行环境：Python 3.9；创建方式：**在线编辑**
   - 把本目录 `scf_dispatch.py` 全文粘贴进 `index.py`（无第三方依赖）
   - 创建方式选「本地上传 zip」亦可（上传本目录）
2. 配置：
   - **环境变量**：`GITHUB_TOKEN` = 上面创建的 PAT
   - **触发器 → 创建定时触发器**：
     - 触发周期：自定义 Cron
     - Cron 表达式（北京时间，宽松版一条搞定）：
       `0 15,45 9,10,11,13,14 * * * *`
       （= 9:15 / 9:45 / 10:15 / 10:45 / 11:15 / 11:45 / 13:15 / 13:45 / 14:15 / 14:45；
       9:15 与 11:45 会被脚本状态机判非盘中自动跳过，无副作用）
3. 测试：控制台「测试」按钮 → 期望返回 `{"code": 204, ...}`（204 = GitHub 接受 dispatch 无 body）
4. 验证：GitHub Actions 页应**立即**出现一条 `实时盯盘盘中更新` 的新 run（event 列 = manual）

费用：免费额度内（每月 40 万次调用 + 40 万 GBs，本场景每月约 180 次调用、几乎为 0 GBs）≈ **0 元**。

## 载体二：cron-job.org（不依赖腾讯云，纯网页）

1. 注册 cron-job.org → Create cronjob
2. 配置：
   - URL：`https://api.github.com/repos/XDTuang/golden-stock-observer/actions/workflows/realtime-monitor.yml/dispatches`
   - Method：`POST`
   - Content-Type：`application/json`
   - Body：`{"ref":"main"}`
   - **Request headers**：`Authorization: Bearer <你的 PAT>`
   - Schedule：每 30 分钟（自定义 Cron，北京时区）
   - **每次超时**：GitHub API 无 body 返回 204，2xx 即成功
3. 免费版限制：每分钟请求次数低，本场景无碍。注意 URL 仅用 https。

## 与实验的关系（2026-09-04 起的双轨）

- **实验**：`realtime-monitor.yml` 已把 schedule 从 8 档精简为 4 档（北京 10:15/11:15/13:15/14:15），
  观察 9/4 下午与 9/7 周一延迟是否改善（减少排队量假设）。
- **方案 A**（本文件）：外部 8 档 dispatch 为准时主力。两者若同时运行，同一时刻会双触发 →
  workflow 有 `concurrency: group realtime-monitor`（cancel-in-progress: false）串行，
  第二次跑检测 `git diff --cached --quiet` 无变化即跳过推送 → 无害但浪费一次 runner 分钟。
- **收敛方案**（A 上线稳定后）：把 `realtime-monitor.yml` 的 schedule 段删至 1 档
  （北京 14:15，历史最可靠档，作 PAT 失效时的兜底），其余 7 档完全交给外部触发器。

## 故障排查速查

| 症状 | 原因 | 处置 |
|---|---|---|
| 返回 401 | Token 过期/错误 | 重新生成 PAT，更新环境变量 |
| 返回 403 | PAT 无 Actions 权限 或 仓库不匹配 | 检查 fine-grained 权限与仓库范围 |
| 返回 404 | workflow 文件名/仓库名错 | 核对 WORKFLOW/REPO 常量 |
| 云函数超时 | GitHub API 偶发慢 | 无需处理，下次触发自动重试 |
| 线上无新 run | 触发器没生效 | 控制台手动「测试」，看返回码 |
