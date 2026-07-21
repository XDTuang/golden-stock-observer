# 兜金观测 · GitHub Actions 每日自动更新方案

> 目标：把主站（golden-stock-observer）+ 金钻副站（golden-diamond-observer）两个 GitHub Pages 站点的盘后数据更新，
> 从本地 launchd 迁移到 **GitHub Actions**，实现"本地零依赖、纯云端自动跑"。
> 本文档供周六实施参考。CloudBase 同步另议，未包含在本方案。

---

## 0. 一句话结论

**完全可行，且比腾讯云 Lighthouse 方案更省事**：纯 Serverless、零运维、公开库免费无限时长。
唯一硬前提是——**流水线 `.py` 脚本当前被 `.gitignore` 忽略，必须提交进仓库**，否则 Actions checkout 后无代码可跑。

---

## 1. 现状与依赖盘点（已核实）

| 项 | 结论 |
|----|------|
| 主站仓库 | `git@github.com:XDTuang/golden-stock-observer.git`（分支 `main`，Pages 直接服务根目录） |
| 副站仓库 | `git@github.com:XDTuang/golden-diamond-observer.git`（独立仓库，`diamond_site/` 内容即其根） |
| 数据源 | 腾讯公开行情接口（无需 API Key） |
| Python 依赖 | `requests` + `pandas`（其余为标准库） |
| 流水线脚本 | `fetch_pool.py` `golden_diamond_scan.py` `build_gd_history.py` `gate_scan.py` `build_diamond_pool.py` `slim_signals.py` `_build_diamond.py` `build_sector_gd_history.py` —— **全部被 `.gitignore` 的 `*.py` 忽略** |
| 密钥需求 | 主站/副站更新本身**不需要任何密钥**；仅需一个能写副站仓库的 PAT（见 §4） |

---

## 2. 必须改的 4 件事（硬前提）

### 2.1 解忽略流水线脚本（最关键）
`.gitignore` 第 30 行 `*.py` 把所有 Python 脚本排除。需对流水线脚本开白名单，二选一：
- **方案 A**（推荐，最干净）：把 `*.py` 规则改为只忽略不需要的，并对流水线脚本逐个 `!` 放行；
- **方案 B**：直接在 `git add -f` 时强制加入这些文件并跟踪。

> 这其实顺带修复了历史隐患：之前 `git clone` 拿不到完整可运行代码，任何人（含未来的你）都无法复现。

### 2.2 新增 `requirements.txt`
```
requests
pandas
```
Actions 第一步 `pip install -r requirements.txt`。

### 2.3 跨仓库推送副站
副站是独立 git 仓库，根目录 = 本地 `diamond_site/` 内容。Actions 内：
1. 克隆 `golden-diamond-observer` 到临时目录（用 PAT）；
2. 把构建出的 `diamond_site/*` 同步进该克隆；
3. 提交并 `git push`。

### 2.4 健壮性与时区
- 定时用 **UTC cron**：`35 8 * * 1-5`（对应北京时间周一至五 16:35）。
- 给 `gate_scan.py` 套 `timeout 600`，防止无人值守时网络卡死烧光 6 小时配额。
- 加 `concurrency` 防止重叠运行。

---

## 3. Workflow 文件示意

路径：`.github/workflows/daily-update.yml`

```yaml
name: 兜金观测每日盘后更新
on:
  schedule:
    - cron: "35 8 * * 1-5"      # 北京时间 周一~周五 16:35
  workflow_dispatch:            # 支持手动触发

concurrency:
  group: daily-update
  cancel-in-progress: false

permissions:
  contents: write               # 推主站自身仓库

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4

      - name: Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: 安装依赖
        run: pip install -r requirements.txt

      - name: 跑主链路（fetch→scan→build→slim）
        run: |
          timeout 600 bash update_data.sh

      - name: 部署主站（GitHub Pages 服务 main 分支根目录）
        run: bash github_pages_deploy.sh
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: 部署金钻副站（跨仓库）
        env:
          DIAMOND_PAT: ${{ secrets.DIAMOND_PAT }}
        run: |
          git config --global user.email "bot@github.com"
          git config --global user.name "github-actions"
          rm -rf /tmp/diamond && git clone "https://x-access-token:${DIAMOND_PAT}@github.com/XDTuang/golden-diamond-observer.git" /tmp/diamond
          rm -rf /tmp/diamond/* /tmp/diamond/.nojekyll
          cp -R diamond_site/. /tmp/diamond/
          touch /tmp/diamond/.nojekyll
          cd /tmp/diamond
          git add -A
          if ! git diff --cached --quiet; then
            git commit -m "数据更新: $(date '+%Y-%m-%d %H:%M')"
            git push origin main
          fi
```

> 注：`github_pages_deploy.sh` 当前用 `git push origin main` 推主站，Actions 内靠 `permissions: contents: write` + 默认 `GITHUB_TOKEN` 即可，无需额外配置。

---

## 4. 上线前准备（Secrets / 凭证）

| 名称 | 用途 | 获取 |
|------|------|------|
| `DIAMOND_PAT` | 写 `golden-diamond-observer` 仓库 | GitHub → Settings → Developer settings → Personal access tokens → 勾选 `repo` 权限，存为仓库 Secret |
| （可选）`CLOUDBASE_*` | 若日后把 CloudBase 同步也搬上 Actions | 另议，不在本方案范围 |

> 主站自身推送用默认 `GITHUB_TOKEN`，**不要**用它去推副站（跨仓库需显式 PAT）。

---

## 5. 与现方案 / 腾讯云方案对比

| 维度 | 本地 launchd | 腾讯云 Lighthouse | **GitHub Actions（本文）** |
|------|-------------|------------------|--------------------------|
| 是否需常开机器 | 是 | 是（VM 常驻） | **否（Serverless）** |
| 运维成本 | 低 | 中（系统/依赖/SSH） | **极低** |
| 费用 | 0 | ~¥50/月 | **公开库免费无限** |
| 密钥管理 | 本地 | 实例内 | **GitHub Secrets** |
| 迁移改动 | — | 搬 `.py`+配 cron+预置凭证 | 搬 `.py`+加 `requirements.txt`+配 PAT |

**结论**：GitHub Actions 是"本地零依赖"目标的最简路径，优先于 Lighthouse。

---

## 6. 已知坑（务必处理）

1. **`gate_scan.py` 网络悬挂**：必须 `timeout 600` 包裹，否则卡死到 6h 超时。
2. **GitHub cron 偶发延迟**：共享 runner 可能晚几分钟到几小时，盘后场景无影响。
3. **60 天闲置自动暂停**：仓库 60 天无提交则定时任务被禁用——本任务每天有提交，不会触发。
4. **`.py` 必须进仓库**：见 §2.1，否则 Actions 空跑。
5. **`pandas` 安装较慢**：Actions 首次装约 1–2 分钟，可接受；可加依赖缓存进一步加速。

---

## 7. 实施检查清单（周六照做）

- [ ] 1. 解除 `.gitignore` 对 8 个流水线 `.py` 的忽略，提交
- [ ] 2. 新增 `requirements.txt`（`requests` + `pandas`），提交
- [ ] 3. 新建 `.github/workflows/daily-update.yml`（见 §3）
- [ ] 4. 仓库 Settings → Secrets 添加 `DIAMOND_PAT`
- [ ] 5. 手动跑一次 `workflow_dispatch` 验证全链路（观察 ~15 分钟）
- [ ] 6. 验证主站 + 副站 Pages 均刷新、数据正常
- [ ] 7. 观察 3–5 个交易日稳定后，关闭本地 `com.goldenstock.daily` launchd 任务
- [ ] 8. （可选）把 CloudBase 同步也搬上 Actions，注销本地主链路

---

## 8. 回滚方案

- 任一环节异常：删掉 `.github/workflows/daily-update.yml` 即回到"纯本地 launchd"状态，互不影响。
- 副站推错：副站仓库 `git revert` 最后一次 Actions 提交即可。
