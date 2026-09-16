/* ═══ NEWS-POOL-BEGIN ═══
   ⚠️ 本块由 review/patch_news_pool.py 管理（源 = review/news_pool_block.js）。
   本块承载两段渲染逻辑：① 6·新闻池（drLoadNewsPool / drMoreNews）
                          ② 信息窗口条（drLoadWindow，读 output/window_latest.json）
   手工修改会被下次 patch 静默回退 —— 改这里请改源文件后重跑 patch 脚本。
   5 处副本须一致：index.html / index_template.html / deploy/index.html /
                   daily_review_tab_snippet.js / inject_daily_review_tab.py */
/* ═══════ 6·新闻整合：公开新闻池（窗口滚动池 output/daily_news_window.json） ═══════
   2026-09-16 改造（信息窗口模型 · 方案 A）：
   ① 数据源由「当日副本 daily_news_latest.json」→「N 日滚动池 daily_news_window.json」——
      跨周末/长假时周六周日的新闻不再被整池覆盖；滚动池不可用时回退当日副本（降级不白屏）。
   ② 展示口径：**按日期分组（倒序）+ 每天收敛展示 DR_NEWS_SHOW_N 条**，
      点「显示更多」按同一步长递增展开；组标题标注「窗口内」（= 本推演纳入的 [基准日]∪span）
      与交易日 / 非交易日，跨周末时周末两组不再凭空消失。 */
const DR_NEWS_SHOW_N = 6;
function drMoreNews(btn) {
  const ul = btn.previousElementSibling;
  if (!ul) return;
  const hid = ul.querySelectorAll('li[hidden]');
  for (let i = 0; i < DR_NEWS_SHOW_N && i < hid.length; i++) hid[i].removeAttribute('hidden');
  const left = ul.querySelectorAll('li[hidden]').length;
  if (left <= 0) btn.remove();
  else btn.textContent = '显示更多（还有 ' + left + ' 条）';
}
function drLoadNewsPool() {
  const el = document.getElementById('drNewsPool');
  if (!el) return;
  const esc = s => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const hm = t => { const m = String(t || '').match(/\d{2}:\d{2}/); return m ? m[0] : ''; };
  const LI = (x, i) => {
    const t = esc(x.title || '');
    const u = esc(x.url || '');
    const body = u
      ? `<a href="${u}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none;border-bottom:1px dotted var(--border)">${t}</a>`
      : t;
    const tg = (x.tags || []).slice(0, 2).map(g => `<span class="dr-tag" style="font-size:10.5px">${esc(g)}</span>`).join(' ');
    const meta = [esc(x.source || ''), hm(x.time)].filter(Boolean).join(' · ');
    return `<li style="margin:1px 0"${i >= DR_NEWS_SHOW_N ? ' hidden' : ''}>${tg ? tg + ' ' : ''}${body} <span style="color:var(--text-muted);font-size:11.5px;white-space:nowrap">${meta}</span></li>`;
  };
  const UL = 'margin:2px 0 0 18px;padding:0;font-size:12.5px;line-height:1.7';
  const WD = ['日', '一', '二', '三', '四', '五', '六'];
  const render = d => {
    const w = (d && d.window) || {};
    const news = (d && d.news) || [];
    const byDay = (d && d.by_day && Object.keys(d.by_day).length) ? d.by_day : null;
    if (!byDay && !news.length) { el.innerHTML = '<div class="dr-note">新闻池为空（output/daily_news_window.json）</div>'; return; }
    const srcs = Object.keys((d && d.sources) || {}).filter(k => (d.sources[k] || 0) > 0);
    const inWin = w.display_days || [];
    let h = '<div class="dr-tag" style="margin-bottom:6px">窗口 ' + esc(w.data_date || '—') + ' 收盘 → 指引 ' + esc(w.for_date || '—')
      + (w.span_is_weekend_cross ? ' ｜ <b>跨非交易日</b>' : '')
      + ' ｜ 滚动池 ' + (d.keep_days || 0) + ' 天 / ' + ((d.covered_days || []).length) + ' 日 · 共 ' + (d.total || news.length) + ' 条'
      + (srcs.length ? ' ｜ 源：' + esc(srcs.join(' / ')) : '') + '</div>';
    if (!byDay) {
      const TAGS = ['宏观', '科技', '政策', '产业', '美股映射', '持仓'];
      TAGS.forEach(tag => {
        const arr = news.filter(x => (x.tags || []).indexOf(tag) >= 0);
        if (!arr.length) return;
        h += `<div style="margin-top:8px"><b>${tag}</b> <span class="dr-tag">${arr.length}</span></div>`;
        h += `<ul style="${UL}">${arr.slice(0, 200).map(LI).join('')}</ul>`;
        const rest = arr.length - DR_NEWS_SHOW_N;
        if (rest > 0) h += `<div class="dr-more" onclick="drMoreNews(this)">显示更多（还有 ${rest} 条）</div>`;
      });
      h += '<div class="dr-note" style="color:var(--text-muted)">滚动池缺失 → 已降级为当日副本视图；请检查 output/daily_news_window.json。</div>';
      el.innerHTML = h;
      return;
    }
    Object.keys(byDay).sort().reverse().forEach((ds, gi) => {
      const arr = (byDay[ds] || []).slice().sort((a, b) => String(b.time || '').localeCompare(String(a.time || '')));
      if (!arr.length) return;
      const dd = new Date(ds + 'T00:00:00');
      const ok = !isNaN(dd.getTime());
      const wk = ok ? '周' + WD[dd.getDay()] : '';
      const trd = ok && dd.getDay() >= 1 && dd.getDay() <= 5;
      const inThis = inWin.indexOf(ds) >= 0;
      h += `<details style="margin:6px 0 0"${gi === 0 ? ' open' : ''}>`
        + `<summary style="cursor:pointer;font-size:12.5px"><b>${esc(ds.slice(5))}</b> ${wk}`
        + `<span class="dr-tag" style="margin-left:4px">${arr.length} 条</span>`
        + (inThis ? '<span class="dr-tag" style="margin-left:4px">窗口内</span>'
                  : '<span class="dr-tag" style="margin-left:4px;opacity:.55">窗口外</span>')
        + (trd ? '' : '<span class="dr-tag" style="margin-left:4px">非交易日</span>')
        + '</summary>'
        + `<ul style="${UL}">${arr.slice(0, 200).map(LI).join('')}</ul>`;
      const rest = arr.length - DR_NEWS_SHOW_N;
      if (rest > 0) h += `<div class="dr-more" onclick="drMoreNews(this)">显示更多（还有 ${rest} 条）</div>`;
      h += '</details>';
    });
    h += '<div class="dr-note" style="color:var(--text-muted)">新闻为公开源自动抓取（东财全球 / 财经早餐 / 新浪全球 / 同花顺全球 / 富途全球）；'
      + '滚动池保留近 ' + (d.keep_days || 0) + ' 个日历日，跨周末/长假累积不覆盖；「窗口内」= 本推演纳入的日期（[基准日] ∪ 增量 span）。'
      + '分类标签由数据文件自带，仅供信息参考，未经核实者按传闻处理。</div>';
    el.innerHTML = h;
  };
  fetch('./output/daily_news_window.json', { cache: 'no-store' })
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(render)
    .catch(() => fetch('./output/daily_news_latest.json', { cache: 'no-store' })
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(render)
      .catch(err => {
        el.innerHTML = `<div class="dr-note">新闻池加载失败：${esc((err && err.message) || err)}（数据源 output/daily_news_window.json）</div>`;
      }));
}

/* ── 信息窗口条（2026-09-16）：读 output/window_latest.json ──
   用户口径：次日推演 = 前一收盘日**全部信息** + 当天盘前增量；跨周末自动补周六周日。
   本函数只渲染**事实**（承接了哪天、增量覆盖哪几天、覆盖了多少条、缺口有哪些），不做推断；
   缺口（missing）非空时必须显式红/金字提示，禁静默（铁律：不静默漏读）。 */
function drLoadWindow() {
  const el = document.getElementById('drWindow');
  if (!el) return;
  const esc = s => (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  fetch('./output/window_latest.json', { cache: 'no-store' })
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(w => {
      const c = w.carry || {};
      const cov = w.covered || [];
      let h = '<div class="dr-h" style="margin-top:0">🪟 信息窗口'
        + '<span class="dr-tag" style="margin-left:6px">' + esc(w.session || '') + ' · output/window_latest.json</span></div>';
      h += '<div style="font-size:12.5px;line-height:1.9">'
        + '<b>承接</b> ' + esc(w.data_date || '—') + ' 收盘复盘'
        + '<span class="dr-tag" style="margin-left:4px">' + esc((c.ref || '').split('/').pop() || '—') + '</span>'
        + (c.bias ? '<span class="dr-tag" style="margin-left:4px">倾向 ' + esc(c.bias) + '</span>' : '')
        + (c.stale ? '<span class="dr-tag" style="margin-left:4px;color:var(--gold)">承接滞后</span>' : '')
        + '<br><b>指引</b> ' + esc(w.for_date || '—')
        + '　<b>增量</b> ' + esc((w.span || []).join(' / ') || '—')
        + (w.span_is_weekend_cross ? ' <span class="dr-tag" style="color:var(--gold)">跨非交易日 · 周末/假期已自动补齐</span>' : '')
        + '<br><b>覆盖</b> ';
      h += cov.length
        ? cov.map(x => esc(String(x.date).slice(5)) + (x.is_trading_day ? '' : '(非交易日)')
            + ' 新闻' + (x.news || 0) + '·投喂' + (x.feeds || 0)).join('　')
        : '—';
      h += '</div>';
      const miss = w.missing || [];
      if (miss.length) {
        h += '<div class="dr-note" style="color:var(--gold)">⚠️ 数据缺口 ' + miss.length + ' 项（显式提示 · 不静默）：<br>'
          + miss.map(m => '· ' + esc(m)).join('<br>') + '</div>';
      } else {
        h += '<div class="dr-note" style="color:var(--text-muted)">✅ 窗口无缺口</div>';
      }
      h += '<div class="dr-note" style="color:var(--text-muted)">窗口 = 承接层（上一份收盘复盘结论）∪ 基准层（'
        + esc(w.data_date || '—') + ' 收盘全套）∪ 增量层（' + esc(w.span_text || '—')
        + '，含周末/节假日、连续无洞）；「美东 T 日收盘」按北京时间归入 T+1 到达日。</div>';
      el.innerHTML = h;
    })
    .catch(err => {
      el.innerHTML = '<div class="dr-note">信息窗口加载失败：' + esc((err && err.message) || err) + '（output/window_latest.json）</div>';
    });
}

/* ═══ NEWS-POOL-END ═══ */
