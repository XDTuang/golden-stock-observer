#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日复盘段落重写：0 / 4 / 5 / 5.5 / 7 段
数据源：8/28 A股收盘 + 8/28 美股/商品收盘 + 8/28-29 公开源宏观新闻
（周六 8/29 执行，基准日 = 2026-08-28，指引日 = 8/31 周一）
"""
import re, os, sys, json

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "deploy", "data", "daily_review", "analysis.html")

# ─────────────────────────────────────────────────────────────
# 0 · 结论先行（速览卡）
# ─────────────────────────────────────────────────────────────
CARD0 = '''
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:6px 0">
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">8/31 开盘预判</div><div style="font-weight:700;color:var(--green)">低开承压 · 结构分化</div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">关注板块</div><div style="font-weight:600">房地产链 · 农业种业 · 化工PTFE</div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">风险等级</div><div style="font-weight:700;color:var(--red)">高（贵金属破位 + 关税尾部）</div></div>
    <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;padding:8px 10px">
      <div class="dr-tag">关键事件</div><div style="font-weight:600">9/1 中国官方PMI · 9/2 ADP · 9/4 非农</div></div>
  </div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:8px">
    <b>一句话结论：</b>沃什 Jackson Hole 首秀<b>明确转鹰</b>（"若通胀不能清晰回落至2%，联储还有工作要做"），
    <b>9月加息概率由 35.4% 跳升至 55.7%</b>——这是本周末最大的变量重定价。
    隔夜后果：<b>2年期美债 +11.35bp 创月内新高、曲线显著趋平、美元指数 99.68（+0.55%）、
    COMEX 黄金 -3.43% 失守 4500 并跌破 200 日均线、白银 -4.48%、英伟达 -4.57%、费半 -2.69%</b>。
    <br><br>
    <b>对 A 股 8/31 的映射（两空一多）：</b><br>
    ① <b>利空贵金属</b>——8/28 深中华A 7板、莱绅通灵2板、山东黄金走强属"黄金抱团"，隔夜金价破位构成<b>直接反杀</b>；
    ② <b>利空 AI 硬件链</b>——英伟达 -4.57%、韩国三星 -3.38%/海力士 -4.45%，8/28 A股光通信/CPO/PCB/存储已现高位分歧（电子净流出186.85亿、半导体-128.30亿），周一或延续调整；
    ③ <b>利多房地产链</b>——8/28 央行+金融监管总局+证监会+住建部四部门齐发新政（房贷期限30年→40年、现房销售、房企再融资/REITs），是周一<b>少数明确正向催化</b>。
    <br><br>
    <b>尾部风险（最高优先级）：特朗普政府正考虑对半导体征收新一轮全面关税</b>，或波及笔记本、游戏机、服务器等含芯片终端——一旦落地对科技链为系统性冲击，需持续跟踪。
  </div>
'''

# ─────────────────────────────────────────────────────────────
# 4 · 重点宏观信息
# ─────────────────────────────────────────────────────────────
CARD4 = '''
  <div class="dr-note"><b>本段口径：</b>8/28（周五）A股收盘 + 8/28 美股/商品/美债收盘 + 8/28-29 公开源宏观新闻（华尔街见闻早餐、陆家嘴/经济日报财经早餐、The Edge、财联社）。<b>核心事件：沃什 Jackson Hole 首秀（8/28 22:00 北京时间）已落地，偏鹰。</b></div>

  <div class="dr-tag" style="margin:10px 0 4px">① 美联储 · 沃什鹰派转向（本周末最重要变量）</div>
  <table class="dr-tbl">
    <thead><tr><th>项目</th><th>变化</th><th>解读</th></tr></thead>
    <tbody>
      <tr><td>9月加息概率（CME）</td><td class="dr-up">35.4% → <b>55.7%</b></td><td>单日跳升 20 个百分点，市场重定价</td></tr>
      <tr><td>沃什核心表态</td><td colspan="2">"若基础通胀不能清晰且足够快速回落至 2%，联储<b>还有工作要做</b>"；承认金融条件<b>并不显得限制性</b>；2% 目标"坚定不移、不容更改"；主张"更安静的美联储"、反对过度前瞻指引</td></tr>
      <tr><td>机构跟进</td><td colspan="2"><b>巴克莱、法国兴业银行预测 9 月与 12 月各加息一次</b>；美联储前官员称讲话"提前为 9 月加息埋下伏笔"；英国央行行长贝利赞同其对前瞻指引的批评</td></tr>
      <tr><td>反向数据（降温证据）</td><td class="dr-dn">非农初步下修 7.9 万人</td><td>美国劳工统计局：截至 2026/3 一年下修约 7.9 万（远小于 2025 年 86.2 万），但与市场预期"上修 18.3 万"相反 → 就业降温但未剧烈恶化</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">② 美债 · 美元 · 汇率（曲线显著趋平）</div>
  <table class="dr-tbl">
    <thead><tr><th>品种</th><th>收益率/点位</th><th>变化</th></tr></thead>
    <tbody>
      <tr><td>2 年期美债</td><td>4.343%</td><td class="dr-up">+11.35bp（创一个月新高）</td></tr>
      <tr><td>3 年期美债</td><td>4.400%</td><td class="dr-up">+10.25bp</td></tr>
      <tr><td>5 年期美债</td><td>4.481%</td><td class="dr-up">+8.29bp</td></tr>
      <tr><td>10 年期美债</td><td><b>4.714%</b></td><td class="dr-up">+3.97bp</td></tr>
      <tr><td>30 年期美债</td><td>5.206%</td><td class="dr-up">+1.46bp</td></tr>
      <tr><td>美元指数</td><td><b>99.68</b></td><td class="dr-up">+0.55%（两个半月最大单日涨幅，全周 +0.6%）</td></tr>
      <tr><td>离岸人民币</td><td>6.7314</td><td class="dr-dn">跌 121 个基点</td></tr>
      <tr><td>欧元 / 日元</td><td>1.158 / 160.11</td><td class="dr-dn">欧元 -0.61%；美元兑日元 +0.45%</td></tr>
    </tbody>
  </table>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--orange);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>曲线形态：</b>短端（2Y +11.35bp）升幅远大于长端（30Y +1.46bp），<b>收益率曲线显著趋平</b>——典型"加息预期升温 + 长期增长信心未同步走强"组合，对成长股估值最不友好。
    欧债同向上行：英 10Y 5.062%、法 4.124%、德 3.276%、意 4.097%、西 3.725%。
  </div>

  <div class="dr-tag" style="margin:10px 0 4px">③ 贵金属 · 有色（黄金技术破位是重点）</div>
  <table class="dr-tbl">
    <thead><tr><th>品种</th><th>收盘</th><th>日变化</th><th>周变化</th></tr></thead>
    <tbody>
      <tr><td>COMEX 黄金</td><td>4504.10 美元/盎司</td><td class="dr-dn">-3.43%</td><td class="dr-dn">-3.77%</td></tr>
      <tr><td>COMEX 白银</td><td>67.09 美元/盎司</td><td class="dr-dn">-4.48%</td><td class="dr-dn">-4.67%</td></tr>
      <tr><td>LME 铜</td><td>14285.0 美元/吨</td><td class="dr-up">+0.02%</td><td class="dr-up">+0.49%</td></tr>
      <tr><td>LME 铝</td><td>3242.0 美元/吨</td><td class="dr-up">+0.23%</td><td class="dr-up">+0.14%</td></tr>
      <tr><td>LME 锌</td><td>3879.5 美元/吨</td><td class="dr-dn">-0.12%</td><td class="dr-up">+1.48%</td></tr>
      <tr><td>LME 镍</td><td>16770.0 美元/吨</td><td class="dr-dn">-0.64%</td><td class="dr-dn">-1.69%</td></tr>
      <tr><td>LME 锡</td><td>54495.0 美元/吨</td><td class="dr-dn">-1.55%</td><td>—</td></tr>
    </tbody>
  </table>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>⚠️ 黄金技术破位：</b>现货黄金一度报 4464 美元，<b>失守 4500 整数关并跌破 200 日均线</b>；国内金饰克价一夜大跌近 40 元。
    供给侧动态：俄铝拟临时封存部分原料产能（每吨铝亏损约 400 美元，年损失约 8 亿美元）；南美四国签署战略矿产合作协议。夜盘氧化铝 +2.24%。
  </div>

  <div class="dr-tag" style="margin:10px 0 4px">④ 原油 · 能源（供应端利空密集）</div>
  <table class="dr-tbl">
    <thead><tr><th>品种</th><th>收盘</th><th>周变化</th></tr></thead>
    <tbody>
      <tr><td>WTI 原油</td><td>83.44 美元/桶</td><td class="dr-dn">-4.16%</td></tr>
      <tr><td>布伦特原油</td><td>88.29 美元/桶</td><td class="dr-dn">-5.06%（三周来首次周线下跌）</td></tr>
    </tbody>
  </table>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--green);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>供应端四大利空：</b>① <b>委内瑞拉政府确认与美国达成石油协议</b>；② 特朗普称美获逾 650 亿桶委石油储量"多数控制权"（雪佛龙即将完成谈判将合资企业迁至新框架，美国防部另与委内瑞拉大亨谈大规模交易）；
    ③ <b>委内瑞拉考虑退出欧佩克</b>；④ 霍尔木兹海峡原油运输量已恢复至冲突前 2/3（伊朗在临时协议期售出约 9000 万桶，但总统称美遵守承诺前不开放海峡）。
    另：投机资金削减布伦特净多头；美国石油钻井 447 口（前值 452）；8 月美国产量均值 1383 万桶/日。
    <br><b>⚠️ 背离信号：上期所原油 2610 合约夜盘收涨 3.66%</b>，与国际盘微跌背离，周一开盘需观察是否补跌。
    国内成品油：发改委 8/28 24 时上调汽柴油（汽油 +375 元/吨、柴油 +360 元/吨）。
  </div>

  <div class="dr-tag" style="margin:10px 0 4px">⑤ 国内政策（8/28 四部门齐发，房地产组合拳）</div>
  <table class="dr-tbl">
    <thead><tr><th>部门</th><th>核心内容</th></tr></thead>
    <tbody>
      <tr><td>央行 + 金融监管总局</td><td>《改革完善房地产信贷管理意见》：<b>个人房贷期限由 30 年延长至 40 年</b>；开发贷主办银行制，预售项目贷款≤5 年、现房销售≤7 年；存量浮动利率房贷可协商调整或置换；阶段性失收可协商延后/展期</td></tr>
      <tr><td>金融监管总局</td><td><b>"五箭齐发"</b>：商品住房开发贷款、个人住房贷款、商业地产贷款、城市更新项目贷款、信托公司房地产信托业务 5 项管理办法（试行）</td></tr>
      <tr><td>证监会</td><td>支持上市房企<b>再融资、并购重组</b>，发行公司债/CMBS/ABS，推动 REITs 高质量发展与扩募</td></tr>
      <tr><td>住建部 + 自然资源部 + 金融监管总局</td><td>有序推行<b>现房销售</b>：新出让项目优先现房销售，购房资金全部入监管账户，实现"交房即交证"；预售门槛提高（单体主体结构封顶）</td></tr>
      <tr><td>财政部</td><td>地方附加税启动立法，幅度税率 <b>11%–13%</b>；个人转让上市公司限售股按 <b>20%</b> 税率征个税</td></tr>
      <tr><td>央行公开市场</td><td>8/28 开展 200 亿 7 天逆回购（利率 1.40%）+ 3330 亿隔夜；当日到期 5985 亿，<b>单日净回笼 2455 亿元</b></td></tr>
      <tr><td>发改委</td><td>全国投资工作推进会议：加快专项债发行使用、推进"十五五"重大工程、系统推进"六张网"（含全国一体化算力网，已纳入 145 万 PFLOPS 智能算力监测）；《物流网建设实施方案》2030 年物流费用/GDP 降至 13.1%</td></tr>
      <tr><td>其他</td><td>新修订《农业法》通过（2027/1/1 施行，保障粮食安全供给）；标普确认中国主权评级 <b>A+/A-1、展望稳定</b></td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">⑥ 地缘 · 关税（尾部风险）</div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>🔴 最高优先级尾部风险：特朗普政府考虑对半导体征收新一轮全面关税</b>——方案或大幅扩大受征税科技产品范围，不仅含芯片，还可能波及笔记本电脑、游戏机、数据中心服务器等使用芯片的终端产品。
    <br>另：美国财长贝森特将在下周 G20 财长及央行行长会议发出"强烈信号"，以美元体系准入为筹码要求各国配合对伊制裁。
    外交部回应美国或制裁与伊朗有业务往来的中国银行：反对非法单边制裁的立场一贯、明确。
  </div>
'''

# ─────────────────────────────────────────────────────────────
# 5 · 重点科技信息
# ─────────────────────────────────────────────────────────────
CARD5 = '''
  <div class="dr-note"><b>本段口径：</b>8/28 美股科技收盘 + 8/28 晚间 A 股公告/产业新闻。<b>外围基调：AI 硬件承压（英伟达 -4.57%、费半 -2.69%），软件云服务逆势走强（亚马逊 +3.97%、赛富时 +1.57%）——风格由"硬"向"软"切换的信号。</b></div>

  <div class="dr-tag" style="margin:10px 0 4px">① 存储 / 半导体（业绩兑现，但外围杀跌）</div>
  <table class="dr-tbl">
    <thead><tr><th>标的/事件</th><th>内容</th><th>方向</th></tr></thead>
    <tbody>
      <tr><td><b>长鑫科技</b> H1</td><td>营收 <b>1503 亿元（+873.6%）</b>、净利 <b>776 亿元大幅扭亏</b>；经营性现金流 1311.6 亿，总资产 4680.8 亿，净资产半年翻倍至 1347.2 亿；<b>LPDDR6 已送样，峰值速率 12800Mbps</b>，下半年供给紧缺格局延续</td><td class="dr-up">强兑现</td></tr>
      <tr><td><b>有研硅</b></td><td>拟收购山东有研艾斯及山东有研半导体股权，<b>预计构成重大资产重组，下周一（8/31）停牌</b></td><td class="dr-up">催化</td></tr>
      <tr><td>香农芯创 H1</td><td>净利 36.4 亿 / +2207%，海普存储业务收入 +996%</td><td class="dr-up">强兑现</td></tr>
      <tr><td>美股存储链</td><td>韩国：三星电子 <b>-3.38%</b>、SK 海力士 <b>-4.45%</b>（韩国综合指数 -1.79%）</td><td class="dr-dn">外围杀跌</td></tr>
      <tr><td>英伟达</td><td><b>-4.57%</b>；安谋 -6.33%；费城半导体指数 <b>-2.69%</b>；罗素2000 -1.4%（小盘与科技对利率最敏感）</td><td class="dr-dn">领跌</td></tr>
      <tr><td>软件云服务</td><td>亚马逊 <b>+3.97%</b>、赛富时（Salesforce）+1.57%、谷歌 +1%——<b>逆势走强</b></td><td class="dr-up">风格切换</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">② AI 算力 / 材料（产业趋势未变，节奏受外围压制）</div>
  <table class="dr-tbl">
    <thead><tr><th>环节</th><th>信号</th></tr></thead>
    <tbody>
      <tr><td>算力平台</td><td>英伟达 <b>Vera Rubin 量产提速</b>；Rubin Ultra 正交背板材料选定 PTFE 方向</td></tr>
      <tr><td>高端铜箔</td><td>2026 年 AI 服务器专用高端铜箔需求约 <b>2.4 万吨，同比 +260%</b></td></tr>
      <tr><td>覆铜板</td><td>覆铜板龙头<b>年内第七次涨价</b>；电子布库存降至 3 天以内（超级紧缺延续至明年）</td></tr>
      <tr><td>PTFE 产业链</td><td>上游树脂（昊华科技/东岳集团/巨化股份）→ 中游高频覆铜板（生益科技/中英科技/华正新材/南亚新材）→ 下游高速 PCB（沪电/胜宏/深南）；配套薄膜（沃特/肯特）与辅料（联瑞新材/菲利华/铜冠铜箔/隆扬电子）</td></tr>
      <tr><td>ETF 资金</td><td><b>16 只创业板算力 ETF + 创业板金融科技 ETF 快速获批</b>（易方达、华夏、嘉实等 10 家 + 华泰柏瑞等 6 家），上报仅三周即获批</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">③ 指数调整 / 制度</div>
  <table class="dr-tbl">
    <thead><tr><th>项目</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td>科创50 样本调整</td><td><b>9/11 收市后生效</b>：调入睿创微纳、华丰科技、屹唐股份、影石创新、盛合晶微（科创100 调入杰普特、长光华芯、凯赛生物等 10 只）</td></tr>
      <tr><td>港交所改革</td><td>研究《主板上市规则》增设第 18D 章、GEM 与主板合并（约 300 家创业板公司或可直接转主板）</td></tr>
      <tr><td>券商接入规范</td><td>中证协与中基协《证券公司交易信息系统接入管理规范（试行）》施行</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">④ 互联网 / 消费 / 金融</div>
  <table class="dr-tbl">
    <thead><tr><th>标的</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td>美团 Q2</td><td>收入 1046.43 亿（+14.40%），经调整 EBITDA 40.98 亿（+47.30%），经调整溢利净额 25.24 亿（+69.00%）；新业务亏损收窄至 17.39 亿</td></tr>
      <tr><td>MiniMax</td><td>B 端收入增长超七倍，占比升至八成（撕掉"C 端公司"标签）</td></tr>
      <tr><td>苹果</td><td>上调 AppleTV+ 月费至 14.99 美元（原 12.99），年费 99→119 美元；AppleOne 个人版 19.95→21.95 美元</td></tr>
      <tr><td>六大行半年报</td><td>工行净利 1736.82 亿居首，建行 1695.64 亿、农行 1463.81 亿；中行增速 5.10% 居首，农行/邮储/建行/交行均超 4%</td></tr>
    </tbody>
  </table>
'''

# ─────────────────────────────────────────────────────────────
# 5.5 · K3 产业信号验证
# ─────────────────────────────────────────────────────────────
CARD55 = '''
  <div class="dr-note"><b>K3 框架：</b>对 8/28 盘面主线做 6 重交叉验证（语料 × 接口资金 × 龙虎榜 × 研报 × 外围映射 × 技术形态），识别"<b>真共振</b>"与"<b>伪共振</b>"。基准日 8/28（周五）收盘。</div>

  <div class="dr-tag" style="margin:10px 0 4px">8/28 盘面事实（验证起点）</div>
  <table class="dr-tbl">
    <thead><tr><th>指数</th><th>收盘</th><th>日涨跌</th><th>周涨跌</th></tr></thead>
    <tbody>
      <tr><td>上证指数</td><td>3952.18</td><td class="dr-dn">-0.11%</td><td class="dr-up">+1.2%</td></tr>
      <tr><td>深证成指</td><td>13953.07</td><td class="dr-dn">-0.68%</td><td class="dr-dn">-1%</td></tr>
      <tr><td>创业板指</td><td>3424.40</td><td class="dr-dn">-1.41%</td><td class="dr-dn">-3.42%</td></tr>
      <tr><td>科创50</td><td>1662.15</td><td class="dr-dn">-1.85%</td><td class="dr-up">+0.52%</td></tr>
      <tr><td>北证50</td><td>—</td><td class="dr-dn">-1.04%</td><td class="dr-dn">-1.08%</td></tr>
    </tbody>
  </table>
  <div class="dr-note">成交 2.10-2.12 万亿（缩量 242 亿）；<b>涨 3013 / 跌 2390</b>，涨停 82（前日 77）、跌停 2、封板率 84%、炸板率 16%、连板晋级率 50%；情绪打分 <b>98 分（复苏）</b>。
  <b>核心特征：指数收绿但个股涨多跌少 → 资金由高位科技向低位周期/消费切换</b>。</div>

  <div class="dr-tag" style="margin:10px 0 4px">6 重验证矩阵</div>
  <table class="dr-tbl">
    <thead><tr><th>#</th><th>维度</th><th>信号</th><th>判定</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>投喂语料</td><td>农业种业（厄尔尼诺+粮食危机）、化工 PTFE/农化、黄金、AI 应用端四条新主线被多篇语料同时点名</td><td class="dr-up">共振</td></tr>
      <tr><td>2</td><td>接口资金流</td><td>电子净流出 <b>186.85 亿</b>、半导体 <b>-128.30 亿</b>（高位 AI 硬件失血）；成交前 50 几乎被 AI 硬件霸榜但多为净流出 → <b>放量滞涨</b></td><td class="dr-dn">背离</td></tr>
      <tr><td>3</td><td>龙虎榜/情绪</td><td>深中华A 7 板（黄金珠宝，年内最高连板）、万向德农 9 天 6 板（农业种业）；高标分歧加剧、炸板率 16%</td><td class="dr-up">结构性共振</td></tr>
      <tr><td>4</td><td>研报/星球</td><td>化工利润 1-7 月 <b>+56.6%</b>（化纤 +107.7%）；PTFE 从辅材变主材；CCL 第七次涨价；长鑫/长存 DRAM 景气</td><td class="dr-up">共振</td></tr>
      <tr><td>5</td><td>外围映射</td><td>英伟达 -4.57%、费半 -2.69%、韩国半导体股大跌；<b>黄金破位 -3.43%</b></td><td class="dr-dn">利空未兑现</td></tr>
      <tr><td>6</td><td>技术形态</td><td>科创50 -1.85% 领跌；创业板周跌 3.42% 最弱；上证周涨 1.2% 相对抗跌</td><td class="dr-dn">分化</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">验证结论：真共振 vs 伪共振</div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--green);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>✅ 真共振（4 重以上印证，可持续）：</b><br>
    ① <b>农业种业</b>——语料（厄尔尼诺+芝加哥小麦 3 年新高+摩通警告粮食危机）+ 情绪（万向德农 9天6板、敦煌种业/新赛股份/金健米业涨停）+ 政策（新《农业法》2027 施行）+ 研报（农业从防守品种升级为全球再通胀主线）。<b>四重印证，主线最硬</b>。<br>
    ② <b>化工 PTFE / 农化</b>——语料（Rubin Ultra 选定 PTFE）+ 业绩（1-7 月化学原料和制品利润 +56.6%）+ 涨价（CCL 第七次、H 酸年内 +150%）+ 涨停潮（昊华科技/沃特股份 2 板、新农股份 3 板、金牛化工/赤天化/泸天化/红宝丽首板）。
  </div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>❌ 伪共振 / 待证伪（周一重点观察）：</b><br>
    ① <b>黄金贵金属</b>——8/28 抱团最紧（深中华A 7 板、莱绅通灵 2 板、山东黄金 H1 高增），但<b>隔夜 COMEX 黄金 -3.43% 失守 4500 并跌破 200 日均线</b>，沃什鹰派直接反杀。<b>这是"盘内最强"与"外围最弱"的正面冲突，周一高标大概率剧烈分歧</b>。<br>
    ② <b>AI 硬件链</b>——8/28 成交前 50 霸榜但资金净流出（放量滞涨），叠加英伟达 -4.57%、韩国半导体股大跌、<b>半导体关税风险</b>三重压力，8/28 的"高位分歧"周一或转为"退潮确认"。
  </div>
'''

# ─────────────────────────────────────────────────────────────
# 7 · 次日开盘指引（8/31 周一）
# ─────────────────────────────────────────────────────────────
CARD7 = '''
  <div class="dr-note"><b>指引日：2026-08-31（周一）。</b>隔夜外围：美股三大指数小幅收跌、<b>AI 硬件领跌</b>；美债短端跳升、曲线趋平；美元走强；<b>黄金白银暴跌</b>；原油微跌但供应利空密集。国内：房地产四部门新政（重大正向催化）。</div>

  <div class="dr-tag" style="margin:10px 0 4px">① 开盘三段预判</div>
  <table class="dr-tbl">
    <thead><tr><th>时段</th><th>预判</th><th>依据</th></tr></thead>
    <tbody>
      <tr><td>集合竞价</td><td><b>低开</b>（沪指 -0.2% ~ -0.5%）</td><td>外围 AI 硬件杀跌 + 黄金破位 + 美元走强；房地产新政部分对冲</td></tr>
      <tr><td>早盘（9:30-11:00）</td><td><b>分化加剧</b>，贵金属与 AI 硬件补跌，地产链/农业/化工相对抗跌</td><td>8/28 已现"指数跌但个股涨"的切换特征，周一方向将被外围强化</td></tr>
      <tr><td>午后</td><td>取决于<b>地产链能否接力</b>；若地产放量则指数有望修复</td><td>四部门新政是周一唯一明确增量催化，资金承接力是关键变量</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">② 板块多空清单</div>
  <table class="dr-tbl">
    <thead><tr><th>方向</th><th>板块</th><th>逻辑</th><th>代表标的</th></tr></thead>
    <tbody>
      <tr><td class="dr-up">多</td><td><b>房地产链</b></td><td>房贷 30→40 年 + 现房销售 + 房企再融资/REITs + 金融监管总局五办法，四部门齐发</td><td>我爱我家、香江控股、深物业A、万科A、保利发展</td></tr>
      <tr><td class="dr-up">多</td><td><b>农业种业</b></td><td>四重印证（语料+情绪+政策+研报），厄尔尼诺+粮食危机，万向德农 9天6板</td><td>万向德农、敦煌种业、新赛股份、登海种业、隆平高科</td></tr>
      <tr><td class="dr-up">多</td><td><b>化工 PTFE/农化</b></td><td>利润 +56.6% 兑现 + CCL 第七次涨价 + Rubin Ultra PTFE 定方向</td><td>昊华科技、沃特股份、生益科技、联瑞新材、巨化股份</td></tr>
      <tr><td class="dr-dn">空</td><td><b>贵金属</b></td><td>隔夜 COMEX 黄金 -3.43% 破 200 日均线，沃什鹰派直接反杀 8/28 抱团</td><td>深中华A（7板高位）、莱绅通灵、山东黄金、湖南黄金</td></tr>
      <tr><td class="dr-dn">空</td><td><b>AI 硬件链</b></td><td>英伟达 -4.57%、费半 -2.69%、韩国半导体股大跌 + 8/28 已净流出（电子 -186.85 亿）</td><td>中际旭创、新易盛、胜宏科技、兆易创新、澜起科技</td></tr>
      <tr><td style="color:var(--orange)">观察</td><td><b>半导体材料</b></td><td>有研硅 8/31 停牌重组（板块情绪扰动）；叠加关税风险，多空交织</td><td>有研硅（停牌）、华特气体、正帆科技、沪硅产业</td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">③ 关键事件雷达（下周）</div>
  <table class="dr-tbl">
    <thead><tr><th>时间</th><th>事件</th><th>影响</th></tr></thead>
    <tbody>
      <tr><td><b>9/1 09:30</b></td><td>中国 8 月官方 PMI</td><td>首个国内数据验证点，影响顺周期与整体风险偏好</td></tr>
      <tr><td>9/1</td><td>MLCC / 半导体芯片 / 锂电池消费税 / 国家基本药物目录</td><td>产业催化密集</td></tr>
      <tr><td><b>9/2 20:15</b></td><td>美国 8 月 ADP 就业</td><td>非农前哨，直接影响 9 月加息定价</td></tr>
      <tr><td>9/3</td><td>特斯拉 Cybercab 发布会、世界动力电池大会</td><td>智驾/锂电主题催化</td></tr>
      <tr><td>9/3 20:30 / 22:00</td><td>美国初请失业金 / 8 月 ISM 服务业</td><td>就业与服务业景气</td></tr>
      <tr><td><b>9/4 20:30</b></td><td><b>美国 8 月非农就业</b></td><td><b>本周最大变量</b>——决定 9 月加息与否（当前概率 55.7%）</td></tr>
      <tr><td>9/9</td><td>苹果 2026 秋季发布会</td><td>消费电子链</td></tr>
      <tr><td>9/11 收市后</td><td>科创50 样本调整生效</td><td>调入睿创微纳、华丰科技、屹唐股份、影石创新、盛合晶微（被动资金调仓）</td></tr>
      <tr><td>9/16</td><td>美联储议息会议</td><td><b>加息与否的最终裁决</b></td></tr>
    </tbody>
  </table>

  <div class="dr-tag" style="margin:10px 0 4px">④ 风险等级与应对</div>
  <div class="dr-note" style="background:var(--bg-subtle);border-left:3px solid var(--red);padding:8px 12px;border-radius:6px;margin-top:6px">
    <b>风险等级：高。</b>三层风险叠加：<br>
    ① <b>高概率高冲击</b>——贵金属板块补跌：8/28 抱团最紧的深中华A（7 板）与黄金股，隔夜金价破位后高标分歧风险极大，一旦炸板回撤幅度深；<br>
    ② <b>中概率高冲击</b>——AI 硬件退潮确认：8/28 已放量滞涨且资金净流出，外围英伟达 -4.57% 若映射，科创50（前日 -1.85%）或继续领跌；<br>
    ③ <b>低概率但极高冲击（尾部）</b>——<b>特朗普政府对半导体征全面关税</b>：若落地，将冲击全科技链（含服务器、笔电、游戏机等终端），需列为最大黑天鹅。<br>
    <b>应对建议：</b>周一<b>不宜追高贵金属与 AI 硬件</b>；关注地产链与农业/化工的承接力；若非农（9/4）前市场持续定价加息，需压低仓位等待 9/16 议息落地。
  </div>
  <div class="dr-note" style="color:var(--text-dim);font-size:12px;margin-top:8px">
    数据来源：8/28 收盘（沪深/港股接口）+ 8/28 美股/商品/美债收盘（华尔街见闻早餐、陆家嘴财经早餐、经济日报财经早餐、The Edge Malaysia）+ 8/28-29 公开源新闻池（664 条：宏观209/政策254/产业129/科技114）+ 用户投喂 19 份素材。仅供个人学习优化金融知识，不构成投资建议。
  </div>
'''


# 段落配置：(起始注释锚点, 结束注释锚点, 新标题, 内容, 名称)
# 说明：本文件各段落结构为  注释 → <div class="dr-h">标题</div> → <div class="dr-card">内容</div>
#       dr-h 在 dr-card **外部**，故必须用注释锚点定位，不能用 rfind('<div class="dr-card"')。
ATTR_0 = (
    'data-preopen="低开承压 · 结构分化" '
    'data-style="房地产链 · 农业种业 · 化工PTFE" '
    'data-risk="高（贵金属破位 + 关税尾部）" '
    'data-event="9/1 官方PMI · 9/2 ADP · 9/4 非农 · 9/16 议息" '
    'data-agent-note="沃什鹰派重定价：9月加息概率 35.4%→55.7%，黄金 -3.43% 破 200 日均线直指贵金属反杀；周一两空一多（贵金属/AI硬件承压，房地产四部门新政是唯一明确增量催化）" '
    'data-agent-detail="沃什鹰派重定价：9月加息概率 35.4%→55.7%，黄金 -3.43% 破 200 日均线直指贵金属反杀；周一两空一多' + chr(10) + chr(10) +
    '对 A 股 8/31 的映射（两空一多）：' + chr(10) +
    '① 利空贵金属——8/28 深中华A 7板、莱绅通灵2板、山东黄金走强属黄金抱团，隔夜金价破位构成直接反杀；' + chr(10) +
    '② 利空 AI 硬件链——英伟达 -4.57%、韩国三星 -3.38%/海力士 -4.45%，8/28 A股光通信/CPO/PCB/存储已现高位分歧（电子净流出186.85亿、半导体-128.30亿），周一或延续调整；' + chr(10) +
    '③ 利多房地产链——8/28 央行+金融监管总局+证监会+住建部四部门齐发新政（房贷期限30年→40年、现房销售、房企再融资/REITs），是周一唯一明确增量催化。' + chr(10) + chr(10) +
    '尾部风险（最高优先级）：特朗普政府正考虑对半导体征新一轮全面关税，或波及笔记本、游戏机、服务器等含芯片终端——一旦落地对科技链为系统性冲击，需持续跟踪。"'
)
ATTR_7 = (
    'data-dir="低开承压 · 结构分化（两空一多）" '
    'data-style-op="空：贵金属/AI硬件；多：房地产链/农业/化工PTFE" '
    'data-risk-event="9/1 PMI · 9/2 ADP · 9/4 非农 · 半导体关税尾部风险" '
    'data-plan="①贵金属高标（深中华A 7板）分歧勿追 ②AI硬件退潮确认 ③地产放量观察 ④非农（9/4）前压低仓位"'
)
SECTIONS = [
    ("<!-- 0 结论先行", "<!-- 0.5 深度判读",
     "0 · 结论先行（速览卡 · 8/31 指引）", CARD0, "0段", ATTR_0),
    ("<!-- 3 隔夜美股", "<!-- 4 重点宏观",
     "3 · 隔夜美股复盘（双日表 · V2 核心升级）", CARD3, "3段", ""),
    ("<!-- 4 重点宏观", "<!-- 5 重点科技",
     "4 · 重点宏观信息（沃什鹰派转向 · 8/28-29 落地）", CARD4, "4段", ""),
    ("<!-- 5 重点科技", "<!-- 5.5 K3",
     "5 · 重点科技信息（产业链信号 · 8/28 兑现 + 外围杀跌）", CARD5, "5段", ""),
    ("<!-- 5.5 K3", "<!-- 6 新闻整合",
     "5.5 · K3 产业信号验证（6 重验证 · 真共振 vs 伪共振）", CARD55, "5.5段", ""),
    ("<!-- 7 开盘指引", "<!-- 9 来源",
     "7 · 次日开盘指引（8/31 周一）", CARD7, "7段", ATTR_7),
]


def main():
    h = open(SRC, encoding="utf-8").read()

    def replace_section(h, anchor_s, anchor_e, title, body, name, attrs=''):
        s = h.find(anchor_s)
        e = h.find(anchor_e)
        if s == -1 or e == -1 or e <= s:
            print(f"⚠️ {name}: 锚点未找到 (start={s}, end={e})")
            return h, False
        # 结束锚点处可能有前置空行，保留
        attr_html = (' ' + attrs.strip()) if attrs and attrs.strip() else ''
        new_sec = (
            f'{anchor_s} · 8/28 复盘 -->\n'
            f'<div class="dr-h">{title}</div>\n'
            f'<div class="dr-card" style="margin-top:4px"{attr_html}>\n'
            f'{body}\n'
            f'  </div>\n\n'
        )
        h = h[:s] + new_sec + h[e:]
        return h, True

    changed = 0
    for a_s, a_e, title, body, name, attrs in SECTIONS:
        h, ok = replace_section(h, a_s, a_e, title, body, name, attrs)
        if ok:
            changed += 1
            print(f"✅ 已重写 {name}")

    # 头部日期标签
    old_tag = "复盘日 2026-08-26（周三）｜ 指引日 08-27（周四）"
    if old_tag in h:
        h = h.replace(old_tag, "复盘日 2026-08-28（周五）｜ 指引日 08-31（周一）")
        print("✅ 头部日期标签已更新")

    open(SRC, "w", encoding="utf-8").write(h)
    print(f"\n💾 {SRC}（{len(h)} chars，重写 {changed}/{len(SECTIONS)} 段）")
    return changed == len(SECTIONS)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
