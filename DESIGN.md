# DESIGN.md — 兜是宝 · 金钻观察 (Aurum Terminal)

> 设计系统规范 · 供 AI 编程代理（Cursor / Claude Code / Google Stitch）直接消费
> 风格定位：**深色金融终端 + 琥珀金英雄色** · Stripe 的工程精度 × Apple 的排版克制
> 生成规则：所有色值精确到 HEX/rgba，所有间距/阴影可复制到 CSS 直接使用

---

## 1. Visual Theme & Atmosphere（视觉主题与氛围）

**品牌设计哲学**
兜是宝金钻是一套 A 股技术共振信号系统（机构+游资+金钻三因子）。产品气质应像一台专业交易终端：冷静、信息密度高、但被一抹「珠宝金」点亮——金色既是品牌符号（金钻/钻石），也承担唯一英雄强调色，引导用户聚焦高优信号。

**视觉基调**：深色金融终端 · 极简数据优先 · 克制而贵气

**核心视觉特征关键词**
`金融终端` · `琥珀金英雄色` · `发丝级边框` · `玻璃质感卡片` · `tabular-nums 数字对齐`

**光影与质感倾向**
- 表面：深色微渐变 + 1px 发丝边框（`rgba(255,255,255,.06)`），非纯扁平
-  elevation：低饱和深黑环境阴影 + 金色微辉（仅英雄元素）
-  玻璃：登录门/浮层使用 `backdrop-filter: blur(14px)` 毛玻璃
-  数字：等宽数字（`font-variant-numeric: tabular-nums`）保证表格列对齐

---

## 2. Color Palette & Roles（调色板与角色）

### Primary / Brand Gold（品牌金 · 英雄色）
| 角色 | HEX | CSS 变量 | 使用场景 |
|------|-----|----------|----------|
| 琥珀金 | `#e6b53c` | `--gold` | 英雄强调、主按钮、激活行左条、品牌字形、K线金钻趋势线 |
| 亮金 | `#f0c04e` | `--gold-strong` | hover/active 提亮、金色辉光 |
| 金底 | `rgba(230,181,60,.10)` | `--gold-bg` | 金标签底、金统计卡底 |
| 金底强 | `rgba(230,181,60,.16)` | `--gold-bg-strong` | 选中态背景 |

### Accent / Interactive（交互蓝 · 次级）
| 角色 | HEX | CSS 变量 | 使用场景 |
|------|-----|----------|----------|
| 交互蓝 | `#6b85fa` | `--accent` | 通用交互、聚焦环、导航激活字、链接 |
| 浅蓝 | `#8ba0fb` | `--accent-light` | hover 提亮 |
| 蓝底 | `rgba(107,133,250,.10)` | `--accent-bg` | 行 hover、聚焦背景 |
| 蓝底强 | `rgba(107,133,250,.16)` | `--accent-bg-hover` | 选中背景 |

### Signal Colors（信号语义色）
| 信号 | HEX | CSS 变量 | 含义 |
|------|-----|----------|------|
| 起涨红 | `#ff7b7b` | `--red` | 金钻起涨（强势启动） |
| 红底 | `rgba(255,123,123,.10)` | `--red-bg` | 红标签底 |
| 买入青 | `#5fd4e6` | `--cyan` | 买入（回调结束回补） |
| 绿 | `#4ade80` | `--green` | 正向/新增/上涨 |
| 绿底 | `rgba(74,222,128,.10)` | `--green-bg` | 绿标签底 |
| 紫 | `#b794f4` | `--purple` | 缠论信号 |
| 紫底 | `rgba(183,148,244,.12)` | `--purple-bg` | 紫标签底 |

### Neutral / Gray Scale（中性灰阶 · 深色）
| 角色 | HEX | CSS 变量 |
|------|-----|----------|
| 根背景 | `#0a0c12` | `--bg-root` |
| 表面 | `#11141d` | `--bg-surface` |
| 卡片 | `#151926` | `--bg-card` |
| 卡片 hover | `#1b2030` | `--bg-card-hover` |
| 次级块 | `#1a1f2e` | `--bg-subtle` |
| 输入底 | `#11141d` | `--bg-input` |
| 浮层 | `rgba(10,12,18,.80)` | `--bg-overlay` |

### Surface & Borders（边框）
| 角色 | HEX | CSS 变量 |
|------|-----|----------|
| 主边框 | `#252b3b` | `--border` |
| 浅边框 | `#1f2433` | `--border-light` |
| 聚焦边框 | `#e6b53c` | `--border-focus` |

### Text（文字）
| 角色 | HEX | CSS 变量 |
|------|-----|----------|
| 主文 | `#e8ebf2` | `--text` |
| 次文 | `#9aa1b8` | `--text-secondary` |
| 弱文 | `#656c82` | `--text-muted` |
| 反白 | `#0a0c12` | `--text-inverse` |

### Semantic Colors（语义色）
| 角色 | HEX | CSS 变量 |
|------|-----|----------|
| 成功 | `#34d399` | `--success` |
| 警告 | `#fbbf24` | `--warning` |
| 危险 | `#f87171` | `--danger` |
| 信息 | `#60a5fa` | `--info` |

### Shadow Colors（阴影色）
所有阴影基于纯黑 `rgba(0,0,0,…)`，英雄金辉用 `rgba(230,181,60,…)`。

---

## 3. Typography Rules（排版规则）

**Font Family**
```css
--font-sans: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC',
             'Microsoft YaHei', system-ui, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'SF Mono', 'JetBrains Mono', ui-monospace, 'Menlo', monospace;
```

**Type Scale**
| Token | 用途 | Size | Weight | Line-Height | Letter-Spacing | 备注 |
|-------|------|------|--------|-------------|----------------|------|
| Display Hero | 页面大标题 | 34px/2.125rem | 800 | 1.15 | -0.02em | 金钻总览标题 |
| H1 | 区块标题 | 22px/1.375rem | 700 | 1.3 | -0.01em | 跟踪卡标题 |
| H2 | 面板标题 | 16px/1rem | 600 | 1.4 | 0 | 卡片/面板头 |
| H3 | 子标题 | 14px/.875rem | 600 | 1.45 | 0 | 组内小标题 |
| Body | 正文 | 13px/.8125rem | 400 | 1.6 | 0 | 分析/说明文字 |
| Small | 辅助 | 12px/.75rem | 400 | 1.5 | 0 | 标签/脚注 |
| Stat Num | 统计数字 | 28px/1.75rem | 800 | 1 | -0.01em | `tabular-nums` |
| Nano | 极细 | 11px/.6875rem | 500 | 1.4 | 0.02em | 徽章/角标 |

**设计哲学**
- 标题字重 700–800 制造权威感，配合负字距（`-0.01 ~ -0.02em`）收紧现代感（Apple 风）。
- 正文 13px / 行高 1.6，保证高密度数据下的可读性；分析段落行高 1.8 更松弛。
- 所有数字（统计、价格、占比）强制 `font-variant-numeric: tabular-nums`，列对齐是金融产品的底线。
- 中文优先 `PingFang SC`，英文/数字优先 `-apple-system`，西文混排不跳字。

---

## 4. Component Stylings（组件样式）

### Buttons
```css
/* Primary — 金色英雄按钮 */
.btn-primary{background:var(--gold);color:#1a1205;border:none;border-radius:10px;
  padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer;
  box-shadow:0 4px 14px rgba(230,181,60,.28);transition:filter .15s,transform .15s;}
.btn-primary:hover{filter:brightness(1.06);}
.btn-primary:active{transform:translateY(1px);}

/* Secondary — 蓝边按钮 */
.btn-secondary{background:var(--accent-bg);color:var(--accent-light);border:1px solid var(--border);
  border-radius:10px;padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;}
.btn-secondary:hover{background:var(--accent-bg-hover);border-color:var(--accent);}

/* Ghost — 透明按钮 */
.btn-ghost{background:transparent;color:var(--text-secondary);border:1px solid var(--border);
  border-radius:10px;padding:8px 14px;font-size:13px;cursor:pointer;}
.btn-ghost:hover{color:var(--text);background:var(--bg-subtle);}

/* Danger — 危险操作 */
.btn-danger{background:rgba(248,113,113,.12);color:var(--danger);border:1px solid rgba(248,113,113,.3);
  border-radius:10px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.btn-danger:hover{background:rgba(248,113,113,.2);}
```
> 触摸目标最小高度 36px；主按钮带金色辉光阴影。

### Cards
```css
.card{background:linear-gradient(180deg,#161b29 0%,#131722 100%);
  border:1px solid var(--border);border-radius:14px;padding:16px 18px;
  box-shadow:var(--shadow-card);}
.card-hover:hover{box-shadow:var(--shadow-card-hover);border-color:rgba(230,181,60,.25);
  transform:translateY(-1px);transition:all .2s ease;}
```

### Inputs
```css
.input{background:var(--bg-input);border:1px solid var(--border);color:var(--text);
  border-radius:10px;padding:9px 12px;font-size:13px;outline:none;transition:border-color .15s,box-shadow .15s;}
.input::placeholder{color:var(--text-muted);}
.input:focus{border-color:var(--border-focus);box-shadow:0 0 0 3px rgba(230,181,60,.14);}
```

### Navigation
```css
.nav-btn{color:var(--text-secondary);background:transparent;border:none;padding:7px 14px;
  border-radius:9px;font-size:13px;cursor:pointer;transition:all .15s;}
.nav-btn:hover{color:var(--text);background:var(--bg-card);}
.nav-btn.active{color:var(--accent-light);background:var(--bg-card);box-shadow:var(--shadow-sm);}
```

### Badges / Tags
```css
.tag{display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:600;}
.tag.up{background:var(--red-bg);color:var(--red);}
.tag.buy{background:rgba(95,212,230,.12);color:var(--cyan);}
.tag.hz{background:var(--gold-bg);color:var(--gold);}
```

### Modals / Dialogs
```css
.overlay{position:fixed;inset:0;background:var(--bg-overlay);backdrop-filter:blur(14px);
  display:flex;align-items:center;justify-content:center;z-index:10000;
  animation:fade .2s ease;}
.modal{background:linear-gradient(180deg,#1a2030,#151926);border:1px solid var(--border);
  border-radius:18px;padding:28px 32px;box-shadow:var(--shadow-popup);
  animation:rise .25s cubic-bezier(.2,.8,.2,1);}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes rise{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
```

---

## 5. Layout Principles（布局原则）

**Spacing System**（4px 基数）
`--sp-1:4px · --sp-2:8px · --sp-3:12px · --sp-4:16px · --sp-6:24px · --sp-8:32px · --sp-12:48px`

**Grid System**
- 金钻页主布局：`grid-template-columns: minmax(300px,360px) 1fr; gap:16px`（左列表 / 右图表）
- 统计卡：`repeat(4,1fr)`；信号卡：`repeat(4,1fr)`；对比卡：`1fr 1fr`

**Container**
- 最大宽度：1280px；页面左右 padding：20px（桌面）/ 14px（移动）

**Section Spacing**
- 区块间距 14px；区块内 padding 16–18px；标题与内容间距 12px

**留白哲学**
数据密集但呼吸感充足：卡片间留 14–16px 缝隙，统计数字上下留白充足以突出量级；不堆砌分割线，用发丝边框与微阴影区分层级而非粗线。

---

## 6. Depth & Elevation（深度与层级）

**Shadow System**
```css
--shadow-xs:   0 1px 2px rgba(0,0,0,.30);
--shadow-sm:   0 1px 3px rgba(0,0,0,.40);
--shadow-card: 0 1px 2px rgba(0,0,0,.40), 0 10px 30px rgba(0,0,0,.30);
--shadow-card-hover: 0 4px 12px rgba(0,0,0,.45), 0 18px 50px rgba(0,0,0,.38);
--shadow-popup: 0 12px 40px rgba(0,0,0,.55);
--shadow-gold: 0 8px 30px rgba(230,181,60,.18);
```

**Surface Layers**
`--bg-root(最底)` → `--bg-surface` → `--bg-card(卡片)` → `--bg-card-hover(浮起)` → `--bg-overlay(毛玻璃浮层)`

**Z-index Scale**
`gate/overlay:10000 · sticky-th:50 · tooltip:200 · modal:10000`

**Backdrop Effects**
```css
backdrop-filter: blur(14px);
background: rgba(10,12,18,.80);  /* 登录门/浮层 */
```

---

## 7. Do's and Don'ts（设计规范与禁忌）

**Do's**
1. 金色仅用于英雄元素（主按钮、激活指示、品牌字），别到处撒金。
2. 所有数字用 `tabular-nums`，表格列必须对齐。
3. 卡片用发丝边框 + 低饱和深阴影区分层级，避免粗黑线。
4. 深色背景层级用 `#0a0c12 → #151926` 的微妙递进，而非纯黑平涂。
5. 交互反馈统一 0.15–0.25s ease，hover 用亮度/位移而非颜色跳变。
6. 聚焦态用金色环（`box-shadow:0 0 0 3px rgba(230,181,60,.14)`）。
7. 信号语义色严格对应：红=起涨 / 青=买入 / 金=红区黄柱。

**Don'ts**
1. 不要用高亮黄 `#f6e05e` 当 UI 强调色（太刺眼），改用琥珀金 `#e6b53c`。
2. 不要在深色背景上用纯白大面块，会破坏终端沉浸感。
3. 不要用圆角 < 8px 的「硬」按钮，保持 10–14px 现代圆角。
4. 不要给表格行加重边框，用 hover 底色 + 激活左条即可。
5. 不要混用多种强调色（金+蓝+紫同时存在时，紫仅限缠论、蓝仅限通用交互）。
6. 不要让正文小于 12px，弱文不小于 11px。
7. 不要对大数据列表做入场动画，性能优先。

---

## 8. Responsive Behavior（响应式行为）

**Breakpoints**
| 名称 | 范围 | 备注 |
|------|------|------|
| mobile | `< 640px` | 单列堆叠 |
| tablet | `640–880px` | 列表/图表转单列 |
| desktop | `880–1280px` | 双列主布局 |
| wide | `> 1280px` | 最大宽度封顶 1280px |

**Touch Targets**：最小 36×36px；按钮 padding 保证可点区域 ≥ 40px 高。

**折叠策略**
- `< 880px`：`.gd-layout` 转 `grid-template-columns:1fr`（列表在上、图表在下）
- 统计卡 `repeat(4,1fr)` → `repeat(2,1fr)`
- 信号卡 / 对比卡 → 单列
- 表格横向可滚动（`overflow-x:auto`）

**Font Scaling**
- 桌面基准 13px 正文；移动端保持 13px，Display Hero 34→28px；统计数字 28→24px。
- 不整体缩放根字号，靠 type scale token 调整，避免布局错位。

---

## 9. Agent Prompt Guide（AI 代理提示指南）

**Quick Reference**
- 主题：深色金融终端，英雄色琥珀金 `#e6b53c`，信号色 红`#ff7b7b`/青`#5fd4e6`/金`#e6b53c`。
- 字体：`-apple-system, 'PingFang SC'`；数字必加 `tabular-nums`。
- 圆角：按钮/输入 10px，卡片 14px，胶囊标签 999px。
- 阴影：`--shadow-card` 卡片，`--shadow-gold` 金色辉光。
- 间距：4px 基数，区块 14–16px。

**Component Prompts（可直接复制）**
1. `用 DESIGN.md 的 Aurum Terminal 规范生成一个「金钻信号统计卡」组件：4 列，每列顶部 3px 色条（红/青/金/蓝），大号 tabular-nums 数字 + 标签，深色玻璃卡片。`
2. `基于 DESIGN.md 生成一个深色登录门 modal：居中毛玻璃卡片，金色标题「💎 兜宝金钻」，密码输入框 + 进入按钮（金色主按钮），错误提示红字。`
3. `用本规范做一个金融数据表格行组件：hover 金色微底，激活行左侧 3px 金条，单元格 12px，价格列 tabular-nums 右对齐。`
4. `生成金色主按钮 + 蓝边次按钮 + 幽灵按钮的一组，hover/active 态按 DESIGN.md 的阴影与位移规范。`
5. `做一个「近 N 交易日演化」跟踪卡：可折叠头部（金色宝石图标 + 标题），内部含统计条、对比双卡（新增/移除/保持）、日期下拉。`
6. `用规范生成 K线图面板外壳：深色卡片、顶部标题栏（左标题右 meta）、底部控制条（缩放按钮 + 范围滑块 + 形态筛选胶囊）。`

**Iteration Guide（迭代建议）**
1. 改色先改 CSS 变量（`:root` / `[data-theme=dark]`），不要硬编码 HEX 进组件。
2. 新增组件必须复用 `--bg-card / --border / --shadow-card`，保持表面语言一致。
3. 任何数字展示加 `font-variant-numeric: tabular-nums`。
4. 深色背景层级递进用变量，禁止 `#000` 平涂。
5. hover 动效用 `filter:brightness()` 或 `translateY`，避免 `background` 硬切。
6. 响应式先保证 `< 880px` 单列可用，再细化宽屏。
7. 图表颜色走 `gdColors()` → 全局变量，别在 canvas 里写死 HEX。
8. 交付前核对：9 章节变量是否全部被组件引用，无孤儿色值。
9. 毛玻璃浮层必须配 `backdrop-filter` + 半透明底，否则发灰。
10. 提交前在移动端真机宽度（375px）过一遍主流程（登录→列表→图表→跟踪卡）。
