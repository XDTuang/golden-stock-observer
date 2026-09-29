# 数据源反封禁执行细则（2026-09-29 立 · 单源权威）

> **本文件是「东财等接口不可达」处置的唯一操作细则。** automation（08:30 盘前推演 / 22:00 夜间全链路）
> 与任何手工排查**一律以本文件为准**，不要各自发明处置流程。

---

## 一、根因（2026-09-29 实测，非推断）

东财 `/api/qt/*` 系列在**生产分片池**被边缘定点覆盖：

| 主机 | 2026-09-29 实测 | 说明 |
|---|---|---|
| `push2.eastmoney.com` | ❌ `RemoteDisconnected` | 生产主域 |
| `push2delay.eastmoney.com` | ❌ RST | 延时镜像 |
| `push2his.eastmoney.com` | ❌ RST | 历史域（**10:0x 才被封 —— 范围会扩大**） |
| **`push2test.eastmoney.com`** | ✅ **HTTP 200** | 测试节点，`clist` / `stock/get` 均可用 |

**数据等价性已三方对账**（零口径漂移）：

| 行业 | 存量 clist 9/24 | push2test 日线 9/24 | 投喂侧 iFinD 9/24 |
|---|---|---|---|
| 电子 | -228.76 亿 | **-228.76 亿** | **-228.76 亿** |
| 国防军工 | +8.84 亿 | **+8.84 亿** | **+8.84 亿** |
| 医药生物 | -69.00 亿 | **-69.00 亿** | **-69.00 亿** |

### 拒绝的性质 = **频率型临时封禁**（关键）

实测证据链：
1. 同一请求：**先 200、连打数次后稳定 RST**；
2. 全程约 1.5 小时后**自行解除**（09:27 复测 4/4 全 200）；
3. **封禁范围会扩大** —— `push2his` 从「可用」变成「RST」（10:0x 实测）。

⇒ **不是域名不可达、不是永久封禁、不是 TLS/UA/参数问题**（8 种变体含 curl 另一 TLS 栈全部同样被拒）。

### 放大器（本仓代码级责任）

`fetch_sector_flow.py` 旧版：`for attempt in 3` × `for pn in 1..5` = **单次最多 15 请求**、无请求间隔、
UA 自带 `GoldenStockObserver/1.0` 机器人标识、RST 后立即重试、失败 `return {}` + 退出码 0 = **静默**。
且该脚本一天被 4+ 条自动化调用；`fetch_realtime.py`（云端每 30 分钟）直连被封端点。

---

## 二、纪律（硬约束 · 五条）

1. **统一入口**：一切东财调用走 `em_http.py`（唯一入口）。
   - 主机池故障转移：**可用节点置顶**（`push2test` 第一）→ 避免每次先打被封节点（那本身就是无谓送频率）
   - **每台只试 1 次**（🔴 禁对同台重试）
   - 内置 **1.2s 节流**、**健康记忆** `output/em_host_state.json`（全脚本共享）
   - 全不可用 → 抛 `EMUnavailable`（**大声失败**）
2. **RST / 429 之后禁止连续重试** —— 短时高频会触发更广的 IP 级封禁，实测把「当时还活着的端点」一起打死。
3. **失败一律大声**：`source_status` 落盘 + **非零退出码** + stderr 告警；
   🔴 **禁静默保留旧数据冒充当日值**。
4. **遇不可达先探再动**：`python3 em_http.py` 或 `fetch_sector_flow.py --probe` 看是否已自行解除
   （约 1.5 小时自解）；**不要连打同一条链路**。
5. **新增任何东财调用**必须走 `em_http`；若确需直连，自带「每台只 1 次 + 节流 + 非零退出码」三件套。

---

## 三、当前各脚本的东财依赖状态（自查矩阵 · 2026-09-29）

| 脚本 | 东财端点 | 状态 |
|---|---|---|
| `fetch_sector_flow.py` | `clist` / `ulist.np` / `fflow/daykline` | ✅ v4 主机池（可用节点置顶）+ `--probe` / `--backfill` + `source_status` |
| `fetch_realtime.py` | `clist`（板块资金） | ✅ 已走 `em_http`；实测 **0 行 → 100 行** |
| `data_pipeline.py` | `stock/get` | ✅ 已走 `em_http`（保留直连兜底分支） |
| `gate_scan.py` | `clist`（`_push2_cons`） | ✅ **历史遗留死代码**（无调用点，不产生请求）；已就地标注 |
| `fetch_pool.py` | — | ✅ 早已改走系统 curl + 腾讯源 |
| `build_sector_tech.py` | —（源 = 申万宏源官网） | ✅ **非东财**；已加「源新鲜度预探」（1 请求替代 31 请求） |
| `fetch_daily_macro.py` | —（源 = 百度经济日历） | ✅ 非东财 |
| `fetch_touzid_data.py` | —（乐咕 / CBOE） | ✅ 非东财 |

**自查命令**（找出仍直连东财的活跃脚本）：

```bash
cd /Users/samt/Desktop/兜是宝/golden_stock_observer
grep -rn "push2[a-z]*\.eastmoney\.com" --include="*.py" . | grep -v "_backups\|\.git/"
# 逐个判断：是主机池定义 / 已标注死代码 / 兜底分支（可接受），还是活跃直连（须改）
```

---

## 四、处置流程（按症状）

### A. `fetch_sector_flow.py` 退出码 4（东财不可达）

```bash
python3 fetch_sector_flow.py --probe                        # ① 四台健康（每台 1 请求）
python3 fetch_sector_flow.py --backfill 2026-09-23 2026-09-28   # ② 尝试回填（逐只带间隔，遇 RST 即停）
python3 -c "import json;print(json.load(open('output/sector_flow.json'))['source_status'])"
```

- `stale_days = 0` → 已闭环
- `stale_days > 0` → 🔴 **报告必须写明「资金列滞后 N 个交易日」**，并注明「**资金维以价格侧替代**」
  （替代读数：观测池站回 MA5 比例、板块涨跌幅结构、实时盯盘收盘档主力净额）
- 🔴 **不因资金列滞后而跳过推演** —— 宁可不推也要如实标注

### B. 申万 K 线源未出当日行（与封禁无关，设计内时序）

申万宏源官网**盘后发布**、当日常到下午才出 T-1 行。`build_sector_tech.py` 已加预探：
源末条 < 数据日 ⇒ **跳过 31 次必然落后的逐只抓取**，只在 missing 里给一条统一说明。

⇒ 出现「`data_date` = 当日 / `kline_last_date` = 前一日」的**口径差属正常**，段头已标注，**不得混读**。

### C. 修了数据之后（必做）

🔴 **正文叙述必须同步改** —— 否则出现「既说资金不可达、又给当日资金」的自相矛盾（2026-09-29 实测踩到）。
顺序：`build_cross_analysis.py` → `build_sector_tech.py` → 改叙述 → 重跑十三道门禁。

---

## 五、健康自检（可放进任何 automation 的门禁）

```bash
cd /Users/samt/Desktop/兜是宝/golden_stock_observer
python3 em_http.py                     # 东部主机池：≥1 台 ok:true 即通过（每台 1 请求，勿重试）
python3 fetch_sector_flow.py --probe   # 同上，含 clist 路径
```

- **通过**：`ok: true` → 正常继续
- **失败**：记录四台明细 + 按 §四 A 处置

（数据来源：东方财富公开接口 / 申万宏源官网 / 项目自有采集链路。
本文件为**技术操作细则**，与 `review/REVIEW_SOP.md` 同级，随仓库正常推送；
⚠️ 但「推送范围 / 授权 / 协作约定」类**运维纪律**仍不进公开仓库，只写本地记忆 + Obsidian。）
