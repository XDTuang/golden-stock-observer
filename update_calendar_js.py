#!/usr/bin/env python3
"""
更新 index_template.html 中的机游共振日历JS函数
使用真实的 LHB_CALENDAR_DATA 六维分类数据
"""
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(BASE, "index_template.html")

# 读取文件
with open(TEMPLATE, 'r', encoding='utf-8') as f:
    content = f.read()

# 新的 JS 函数
NEW_JS = '''
// ═══════════ 机游共振日历 (六维分类) ═══════════
let calCurrentDate = new Date();
let LHB_CALENDAR_DATA = null;

// 六维分类配置
const CATEGORY_CONFIG = {
  "纯共振":   {color: "#e74c3c", bg: "#fde8e8", label: "纯共振",   desc: "机>0.8亿且游资>0.8亿"},
  "准共振":   {color: "#e67e22", bg: "#fef2e8", label: "准共振",   desc: "机>0.8亿且游资0.5~0.8亿"},
  "机构独买": {color: "#9b59b6", bg: "#f3e8f9", label: "机构独买", desc: "机构买入≥4亿"},
  "游资主导": {color: "#f97316", bg: "#fff2e8", label: "游资主导", desc: "游资活跃"},
  "机构大卖": {color: "#27ae60", bg: "#e8f8f0", label: "机构大卖", desc: "净卖出>1亿"},
  "不达标":   {color: "#95a5a6", bg: "#f0f0f0", label: "不达标",   desc: "其他"}
};

// 加载龙虎榜日历数据
async function loadLhbData() {
  try {
    const r = await fetch('./lh_calendar.json');
    if (r.ok) {
      LHB_CALENDAR_DATA = await r.json();
      console.log('✅ 龙虎榜数据加载成功:', Object.keys(LHB_CALENDAR_DATA).length, '天');
    }
  } catch(e) {
    console.warn('⚠️ 龙虎榜数据加载失败:', e);
    LHB_CALENDAR_DATA = null;
  }
}

// 构建日历数据（直接使用 LHB_CALENDAR_DATA）
function buildCalendarData() {
  if (!LHB_CALENDAR_DATA) return {};
  return LHB_CALENDAR_DATA;
}

// 统计某天的六维分类数量
function countCategories(stocks) {
  const counts = {};
  Object.keys(CATEGORY_CONFIG).forEach(k => counts[k] = 0);
  stocks.forEach(s => {
    const cat = s.category || "不达标";
    if (counts[cat] !== undefined) counts[cat]++;
    else counts["不达标"]++;
  });
  return counts;
}

function renderCalendar() {
  const data = buildCalendarData();
  const y = calCurrentDate.getFullYear();
  const m = calCurrentDate.getMonth();
  
  document.getElementById('calMonthLabel').textContent = `${y}年${m+1}月`;
  
  // 统计六维分类
  let totalDays = 0, totalStocks = 0;
  const catTotals = {};
  Object.keys(CATEGORY_CONFIG).forEach(k => catTotals[k] = 0);
  
  Object.keys(data).forEach(d => {
    const arr = data[d];
    totalDays++;
    totalStocks += arr.length;
    const counts = countCategories(arr);
    Object.keys(counts).forEach(k => catTotals[k] += counts[k]);
  });
  
  // 渲染统计卡片
  const statsHtml = Object.keys(CATEGORY_CONFIG).map(k => {
    const cfg = CATEGORY_CONFIG[k];
    return `<div class="cal-stat" style="border-color:${cfg.color}">
      <div class="cval" style="color:${cfg.color}">${catTotals[k]}</div>
      <div class="clabel">${cfg.label}</div>
    </div>`;
  }).join('');
  
  document.getElementById('calStats').innerHTML = `
    <div class="cal-stat days">
      <div class="cval">${totalDays}</div>
      <div class="clabel">活跃交易日</div>
    </div>
    ${statsHtml}
    <div class="cal-stat stocks">
      <div class="cval">${totalStocks}</div>
      <div class="clabel">总股票数</div>
    </div>
  `;
  
  // 日历网格
  const firstDay = new Date(y, m, 1);
  const lastDay = new Date(y, m + 1, 0);
  const startDow = (firstDay.getDay() + 6) % 7; // 周一=0
  const daysInMonth = lastDay.getDate();
  
  let html = '';
  let dayNum = 1;
  const todayStr = new Date().toISOString().substring(0,10);
  
  for (let row = 0; row < 6; row++) {
    if (dayNum > daysInMonth) break;
    html += '<tr>';
    for (let col = 0; col < 7; col++) {
      const cellIdx = row * 7 + col;
      if (cellIdx < startDow || dayNum > daysInMonth) {
        html += '<td class="other-month"></td>';
        continue;
      }
      
      const dateKey = `${y}-${String(m+1).padStart(2,'0')}-${String(dayNum).padStart(2,'0')}`;
      const dayData = data[dateKey] || [];
      const isToday = dateKey === todayStr;
      
      let cellClass = '';
      if (isToday) cellClass += ' today';
      if (dayData.length > 0) cellClass += ' has-data';
      
      const weekendClass = (col === 5 || col === 6) ? 'weekend' : '';
      
      html += `<td class="${cellClass}" onclick="showCalDetail('${dateKey}')">
        <span class="cal-day-num ${weekendClass}">${dayNum}</span>`;
      
      if (dayData.length > 0) {
        const counts = countCategories(dayData);
        
        // 显示六维分类徽章
        html += '<div class="cal-cell-body">';
        
        // 优先显示重要分类
        const priorityCats = ["纯共振", "准共振", "机构独买", "游资主导", "机构大卖"];
        priorityCats.forEach(cat => {
          if (counts[cat] > 0) {
            const cfg = CATEGORY_CONFIG[cat];
            html += `<span class="cal-cat-badge" style="background:${cfg.bg};color:${cfg.color};border:1px solid ${cfg.color}" title="${cfg.desc}">
              ${cfg.label.substring(0,2)}:${counts[cat]}
            </span>`;
          }
        });
        
        html += '</div>';
      }
      
      html += '</td>';
      dayNum++;
    }
    html += '</tr>';
  }
  
  document.getElementById('calBody').innerHTML = html;
  
  // 底部汇总表
  renderCalAllTable(data);
}

function showCalDetail(dateKey) {
  const data = buildCalendarData();
  const arr = data[dateKey] || [];
  
  const detailEl = document.getElementById('calDetail');
  const titleEl = document.getElementById('calDetailTitle');
  titleEl.textContent = `📅 ${dateKey} 龙虎榜详情 (${arr.length}只)`;
  
  if (arr.length === 0) {
    detailEl.style.display = 'none';
    return;
  }
  
  detailEl.style.display = 'block';
  
  // 按分类分组
  const grouped = {};
  Object.keys(CATEGORY_CONFIG).forEach(k => grouped[k] = []);
  arr.forEach(s => {
    const cat = s.category || "不达标";
    if (grouped[cat]) grouped[cat].push(s);
    else grouped["不达标"].push(s);
  });
  
  let tbody = '';
  Object.keys(CATEGORY_CONFIG).forEach(cat => {
    const stocks = grouped[cat];
    if (stocks.length === 0) return;
    
    const cfg = CATEGORY_CONFIG[cat];
    tbody += `<tr style="background:${cfg.bg}">
      <td colspan="6" style="font-weight:600;color:${cfg.color};padding:8px;">
        ${cfg.label} (${stocks.length}只) — ${cfg.desc}
      </td>
    </tr>`;
    
    stocks.forEach(s => {
      const chg = s.chg_pct >= 0 ? `+${s.chg_pct.toFixed(2)}%` : `${s.chg_pct.toFixed(2)}%`;
      const chgColor = s.chg_pct >= 0 ? '#e74c3c' : '#27ae60';
      const netColor = s.net_amt >= 0 ? '#e74c3c' : '#27ae60';
      tbody += `<tr>
        <td>${s.code}</td>
        <td style="font-weight:600;">${s.name}</td>
        <td style="color:${netColor};font-weight:600;">${s.net_amt >= 0 ? '+' : ''}${s.net_amt.toFixed(2)}亿</td>
        <td style="color:${chgColor};font-weight:600;">${chg}</td>
        <td>${s.reason || '—'}</td>
        <td>${s.turnover ? s.turnover.toFixed(2) + '%' : '—'}</td>
      </tr>`;
    });
  });
  
  document.querySelector('#calDetailTable tbody').innerHTML = tbody;
}

function renderCalAllTable(data) {
  let tbody = '';
  const dates = Object.keys(data).sort((a,b) => b.localeCompare(a)); // 降序
  
  dates.forEach(d => {
    const dayData = data[d];
    // 按分类排序：纯共振 > 准共振 > 机构独买 > 游资主导 > 机构大卖 > 不达标
    const catOrder = {"纯共振":0,"准共振":1,"机构独买":2,"游资主导":3,"机构大卖":4,"不达标":5};
    dayData.sort((a,b) => {
      const ca = catOrder[a.category] !== undefined ? catOrder[a.category] : 99;
      const cb = catOrder[b.category] !== undefined ? catOrder[b.category] : 99;
      return ca - cb;
    }).forEach(s => {
      const cfg = CATEGORY_CONFIG[s.category] || CATEGORY_CONFIG["不达标"];
      const chg = s.chg_pct >= 0 ? `+${s.chg_pct.toFixed(2)}%` : `${s.chg_pct.toFixed(2)}%`;
      const chgColor = s.chg_pct >= 0 ? '#e74c3c' : '#27ae60';
      const netColor = s.net_amt >= 0 ? '#e74c3c' : '#27ae60';
      
      tbody += `<tr>
        <td style="white-space:nowrap;">${d}</td>
        <td>${s.code}</td>
        <td style="font-weight:600;">${s.name}</td>
        <td>
          <span class="cat-badge" style="background:${cfg.bg};color:${cfg.color};padding:2px 8px;border-radius:4px;font-size:12px;">
            ${cfg.label}
          </span>
        </td>
        <td style="color:${netColor};font-weight:600;">${s.net_amt >= 0 ? '+' : ''}${s.net_amt.toFixed(2)}亿</td>
        <td style="color:${chgColor};font-weight:600;">${chg}</td>
        <td>${s.reason || '—'}</td>
      </tr>`;
    });
  });
  
  document.querySelector('#calAllTable tbody').innerHTML = tbody || '<tr><td colspan="7" style="text-align:center;padding:20px;color:#999;">暂无龙虎榜数据</td></tr>';
}

function changeCalMonth(delta) {
  calCurrentDate.setMonth(calCurrentDate.getMonth() + delta);
  renderCalendar();
}

async function initPage() {
  if (!SIGNALS_DATA || !SIGNALS_DATA.stocks) {
    document.body.innerHTML = '<div style="text-align:center;padding:100px;font-size:18px;">暂无信号数据，请先运行 data_pipeline.py 生成数据</div>';
    return;
  }
  buildStockDataMap();
  document.getElementById('updateTime').textContent = '更新: ' + (SIGNALS_DATA.generated_at||'未知').substring(0,19);
  renderStats();
  renderTopTable();
  renderShortTerm();
  renderLongTerm();
  renderCharts();
  renderSignalPickCards();
  
  // 加载龙虎榜数据并渲染日历
  await loadLhbData();
  renderCalendar();
}
'''

# 定位并替换 JS 函数
# 找到 "机游共振日历" 标记开始的位置
start_marker = "// ═══════════ 机游共振日历"
end_marker = "\n// ═══════"

# 如果找不到新标记，找旧标记
if start_marker not in content:
    start_marker = "// ===== 机游共振日历"
    
if start_marker in content:
    start_idx = content.index(start_marker)
    # 找到 initPage 函数结束的位置
    # 查找下一个顶级函数或脚本结束
    remaining = content[start_idx:]
    
    # 找到 initPage 函数结束的大括号
    # 简单方法：找到 "function initPage()" 然后找到对应的结束
    init_page_idx = remaining.index("function initPage()")
    # 从 initPage 开始，找到函数结束 (最后一个 })
    # 计算括号平衡
    brace_count = 0
    in_function = False
    end_idx = init_page_idx
    
    for i in range(init_page_idx, len(remaining)):
        if remaining[i] == '{':
            brace_count += 1
            in_function = True
        elif remaining[i] == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                end_idx = i + 1
                break
    
    # 现在 end_idx 是 initPage 函数结束的相对位置
    # 还要找到后面的 DOMContentLoaded 事件监听器
    remaining2 = remaining[end_idx:]
    dom_idx = remaining2.find("document.addEventListener('DOMContentLoaded")
    if dom_idx == -1:
        dom_idx = remaining2.find('document.addEventListener("DOMContentLoaded')
    
    if dom_idx != -1:
        end_idx += dom_idx + 50  # 跳过整个事件监听器
        # 找到结束的 });
        brace_count = 0
        for i in range(dom_idx, len(remaining2)):
            if remaining2[i] == '{':
                brace_count += 1
            elif remaining2[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx += i + 1
                    break
    
    # 实际替换的结束位置
    actual_end = start_idx + end_idx
    
    # 替换
    content = content[:start_idx] + NEW_JS + content[actual_end:]
    
    print(f"✅ 已替换机游共振日历JS函数 (位置: {start_idx}~{actual_end})")
else:
    print("❌ 未找到机游共振日历标记，尝试在 </script> 前插入")
    # 在 </script> 前插入
    script_end = content.rindex("</script>")
    content = content[:script_end] + NEW_JS + content[script_end:]
    print("✅ 已在 </script> 前插入新JS函数")

# 更新 CSS 样式
NEW_CSS = '''
  /* 机游共振日历 - 六维分类 */
  .calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding: 10px 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 8px;
    color: white;
  }
  
  .cal-stats {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 15px;
  }
  
  .cal-stat {
    padding: 8px 15px;
    background: white;
    border-radius: 6px;
    text-align: center;
    min-width: 80px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border: 2px solid #e0e0e0;
    transition: all 0.2s;
  }
  
  .cal-stat:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  
  .cal-stat .cval {
    font-size: 20px;
    font-weight: 700;
    color: #2c3e50;
  }
  
  .cal-stat .clabel {
    font-size: 11px;
    color: #7f8c8d;
    margin-top: 2px;
  }
  
  .calendar-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  .calendar-table th {
    background: #34495e;
    color: white;
    padding: 10px;
    font-size: 13px;
    font-weight: 600;
  }
  
  .calendar-table td {
    border: 1px solid #ecf0f1;
    padding: 8px;
    vertical-align: top;
    height: 100px;
    width: 14.28%;
    position: relative;
  }
  
  .calendar-table td.today {
    background: #fff9e6;
    box-shadow: inset 0 0 0 2px #f39c12;
  }
  
  .calendar-table td.has-data {
    background: #f8f9ff;
  }
  
  .calendar-table td.other-month {
    background: #f8f9fa;
  }
  
  .cal-day-num {
    display: inline-block;
    width: 28px;
    height: 28px;
    line-height: 28px;
    text-align: center;
    border-radius: 50%;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
  }
  
  .cal-day-num.weekend {
    color: #95a5a6;
  }
  
  .cal-day-num.resonance {
    background: #e74c3c;
    color: white;
  }
  
  .cal-cell-body {
    margin-top: 5px;
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
  }
  
  .cal-cat-badge {
    display: inline-block;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    line-height: 1.4;
  }
  
  .cal-stock-tag {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    max-width: 60px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .cal-stock-tag.both {
    background: #fde8e8;
    color: #e74c3c;
  }
  
  .cal-stock-tag.inst-only {
    background: #e8f4fd;
    color: #3498db;
  }
  
  .cal-stock-tag.hot-only {
    background: #fff2e8;
    color: #f97316;
  }
  
  .cat-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }
  
  #calDetail {
    margin-top: 20px;
    padding: 15px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  #calDetailTable {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
  }
  
  #calDetailTable th {
    background: #34495e;
    color: white;
    padding: 8px;
    font-size: 13px;
  }
  
  #calDetailTable td {
    padding: 6px 8px;
    border-bottom: 1px solid #ecf0f1;
    font-size: 13px;
  }
  
  #calAllTable {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  #calAllTable th {
    background: #34495e;
    color: white;
    padding: 10px;
    font-size: 13px;
    font-weight: 600;
  }
  
  #calAllTable td {
    padding: 8px;
    border-bottom: 1px solid #ecf0f1;
    font-size: 13px;
  }
  
  #calAllTable tr:hover {
    background: #f8f9ff;
  }
'''

# 检查是否已有日历CSS，如果有则替换，没有则添加
if ".calendar-header" in content:
    print("⚠️  日历CSS已存在，跳过")
else:
    # 在 </style> 前添加CSS
    style_end = content.rindex("</style>")
    content = content[:style_end] + NEW_CSS + content[style_end:]
    print("✅ 已添加日历CSS样式")

# 保存
with open(TEMPLATE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 更新完成: {TEMPLATE}")
print("   请运行 python data_pipeline.py 重新生成 index.html")
