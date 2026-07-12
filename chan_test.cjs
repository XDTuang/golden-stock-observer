const fs = require('fs');
const { computeChan } = require('./chan_engine.js');

const d = JSON.parse(fs.readFileSync('output/golden_diamond.json', 'utf-8'));
const stocks = d.stocks || [];
console.log('金钻池股票数:', stocks.length, ' data_date:', d.data_date);

let hit = 0, totalBuy = 0, last3Hit = 0;
const rows = [];
for (const s of stocks) {
  const k = s.kline || [];
  if (k.length < 60) { rows.push([s.code, s.name, 'kline太短', 0, 0, '']); continue; }
  let res;
  try { res = computeChan(k); } catch (e) { console.error('CRASH', s.code, e.message); continue; }
  const buys = res.buy.filter(Boolean).length;
  totalBuy += buys;
  const l3 = res.last3Buy.length;
  if (l3 > 0) last3Hit++;
  if (buys > 0) hit++;
  rows.push([s.code, s.name, k.length, buys, l3, res.last3Buy.map(b => b.date).join(',')]);
}
console.log('\n有买点信号的股票数:', hit, '/', stocks.length);
console.log('最近3交易日出现缠论买点的股票数:', last3Hit);
console.log('全样本买点总数:', totalBuy);
console.log('\n=== 明细 (code,name,klineLen,buyCount,last3Buy,last3Dates) ===');
rows.sort((a, b) => (b[4] - a[4]));
for (const r of rows) console.log(r.join('\t'));
