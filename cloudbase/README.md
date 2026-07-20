# 金钻副站 · 国内部署脚手架（腾讯云 CloudBase）

> 目标：把 `diamond_site/`（纯静态站）部署到国内可访问的免费域名（CloudBase 默认子域 `*.tcloudbase.com`），让副站有国内镜像。

## ⚠️ 关键约束（先读）

免费云函数**跑不了 15 分钟的数据管线**：

| 平台 | 免费档函数超时 | 能否跑金钻管线 |
|---|---|---|
| 腾讯云 CloudBase 免费体验版 / 个人版 | **3 秒**（固定） | ❌ 不可能 |
| 阿里云 FC 弹性实例（免费） | 600 秒（10 分钟） | ⚠️ 15 分钟会超时 |
| 阿里云 FC 性能实例（付费） | 86400 秒 | ✅ 但非免费 |

**结论**：免费档下，国内云函数无法独立完成「拉数据 + 构建」。最稳妥的免费方案是——
**计算留在本机（Mac 的 `local_update.sh` 已验证可靠），只用 CloudBase 做国内静态托管**，每天算完把 `diamond_site/` 推上去即可。

---

## 方案 A（推荐 · 免费 · 可靠）：本机算 + CloudBase 托管

### 1. 注册与建环境（你来做，需手机号 + 实名，免费）

**A. 注册账号 + 实名（5 分钟，必须做）**
1. 浏览器打开 https://cloud.tencent.com
2. 右上角「注册」→ 用**微信扫码**注册最省事
3. 注册后点右上角头像 →「**实名认证**」→ 选「个人认证」→ 微信刷脸实名
   - ⚠️ 不实名**无法开通静态托管**，这一步跳过后面会卡住

**B. 进入 CloudBase 控制台**
4. 直接访问：https://console.cloud.tencent.com/tcb （或在首页搜「云开发 CloudBase」→ 点「控制台」）
5. 首次进入会让你「**新建环境**」

**C. 新建免费环境（关键选项）**
6. 点「新建环境」，按要求填：
   - **环境名称**：随意，如 `golden-stock`
   - **计费方式**：选「**免费体验版**」（别选付费套餐；一个账号通常只有 1 个免费名额）
   - **地域**：选「上海」或「广州」（国内节点）
7. 点「**立即开通**」→ 等 1–3 分钟初始化完成

**D. 开通静态网站托管**
8. 环境建好后，左侧菜单找「**静态网站托管**」（有的版本叫「网站托管」）
9. 第一次会显示「未开通」→ 点「**开通**」/「开启」
10. 开通成功后会显示**默认域名**，形如：
    ```
    https://golden-stock-1a2b3c4d.tcloudbase.com
    ```
    ⚠️ 这个域**免备案**就能访问，但访客第一次会弹「访问提醒中转页」，需点一下「确认访问」。

**E. 找到「环境 ID」**
11. 回到环境总览/「**环境设置**」页，有一栏「**环境 ID**」，就是上面域名里 `.tcloudbase.com` 前面的那段（例：`golden-stock-1a2b3c4d`）
12. 把它抄下来（或复制），等下第 3 步要用

> 新手最容易卡住的 3 个点：
> - **实名没做** → 开通托管按钮是灰的。先去实名。
> - **选了付费套餐** → 免费版在「计费方式」里要手动选，默认可能高亮付费项，看清楚再点。
> - **找不到环境 ID** → 它不在托管页，在「环境总览 / 环境设置」里，就是默认域名里 `.tcloudbase.com` 前面的那段字符串。

### 2. 安装 CloudBase CLI（本机一次性）
```bash
npm i -g @cloudbase/cli
tcb login          # 浏览器扫码授权
```

### 3. 部署副站（每次更新后跑一次）
```bash
export CLOUDBASE_ENV_ID="你的环境ID"
bash cloudbase/deploy_cloudbase.sh
```
脚本把 `diamond_site/` 整个目录推到 CloudBase 静态托管根目录。
部署完即可访问：`https://<环境ID>.tcloudbase.com`

> 提示：把上面两行加进你 Mac 的 `local_update.sh` 末尾（在 `_build_diamond.py` 之后），即可盘后自动同步国内镜像。

### 4. 关于「访问提醒中转页」
CloudBase 自 2025-10 起，默认子域访问会先弹「访问提醒中转页」，访客点一次「确认访问」即可（cookie 内短期有效）。
**去掉中转页需绑定已备案自定义域名**（买域名 ~50 元/年 + 免费 ICP 备案 1–20 天）。副站本身有 DDDYB 密码门，中转页影响很小，可先不管。

---

## 方案 B（可选 · 全云端 · 需付费环境）：CloudBase 云函数定时跑

若希望完全不依赖本机，把计算也搬上云，需用 **标准版及以上** 环境（函数超时可设 900s；或改用 HTTP 函数 7200s），并产生少量费用。

### 云函数 `cloudbase/function/index.py`
- 定时触发器：`0 35 17 * * 1-5`（周一至五 17:35，盘后）
- 逻辑：拉取源码 → 跑 `fetch_pool.py` + `golden_diamond_scan.py` → `_build_diamond.py` 构建 → 推送 `diamond_site/` 到 GitHub 部署仓库
- CloudBase 控制台「静态托管 → GitHub 授权」绑定该部署仓库后，**推送即自动部署**到静态托管（无需在函数内调 SDK 上传）
- 环境变量：`GITHUB_TOKEN`（有 repo 写权限的 PAT）、`SOURCE_REPO`、`DEPLOY_REPO`

### 部署函数
```bash
cd cloudbase/function
tcb fn deploy gd-daily --envId <环境ID> --runtime python3   # 在控制台把超时设为 900s 并加定时触发器
```

> 注意：函数从腾讯云内网克隆 GitHub 可能慢/受限，更稳的做法是把 `fetch_pool.py` 等脚本**直接打进函数包**（zip 时包含，不要依赖运行时 git clone）。`index.py` 已同时支持两种模式（设 `PACKAGED=1` 时用函数包内脚本）。

---

## 隔离原则（务必遵守）
- 只推送 `diamond_site/`（index.html + output/*.json），**绝不**推送 `gate_data.json`（沙盒预览，仅本地）。
- `diamond_site/.gitignore` 已忽略 `output/gate_*.json`，本脚手架也只复制 `diamond_site/` 目录，天然隔离。

## 访问地址
- 国内镜像：`https://<环境ID>.tcloudbase.com`（密码 DDDYB）
- 国际原站：`https://XDTuang.github.io/golden-diamond-observer/`（密码 DDDYB）
- 主站：`https://xdtuang.github.io/golden-stock-observer/`
