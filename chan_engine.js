/* 缠论 (Chan theory) pivot detector — faithful port of the given 通达信 formula.
 * Produces per-bar pivot retention: -1 = 买 (buy), 1 = 卖 (sell), 0 = none.
 * Operates on a kline array: [{date, open, high, low, close, volume}, ...] (oldest -> newest).
 * All Tongdaxin primitives are re-implemented on index 0..N-1 (0 = oldest bar).
 */
(function (global) {
  // ---- Tongdaxin primitives (index i, 0 = oldest) ----
  function refV(a, i, n) { return (i - n < 0) ? 0 : a[i - n]; }
  function refXV(a, i, n) { return (i + n >= a.length) ? null : a[i + n]; }
  function hhv(a, i, n) {
    if (n < 1) n = 1;
    if (n > i + 1) n = i + 1;
    let m = -Infinity;
    for (let j = i - n + 1; j <= i; j++) m = Math.max(m, a[j]);
    return m;
  }
  function llv(a, i, n) {
    if (n < 1) n = 1;
    if (n > i + 1) n = i + 1;
    let m = Infinity;
    for (let j = i - n + 1; j <= i; j++) m = Math.min(m, a[j]);
    return m;
  }
  // bars since condition last true (0 if true on current bar); large if never
  function barslast(cond, i) {
    for (let j = i; j >= 0; j--) if (cond[j]) return i - j;
    return i + 1;
  }
  // BACKSET(X,N): for each true bar i, set bars [i-N+1, i] to 1
  function backset(cond, n) {
    const N = cond.length, r = new Array(N).fill(0);
    for (let i = 0; i < N; i++) if (cond[i]) {
      const lo = Math.max(0, i - n + 1);
      for (let j = lo; j <= i; j++) r[j] = 1;
    }
    return r;
  }
  // TOPRANGE(H): consecutive bars ending at i where H[i] is the running max
  function toprange(a, i) {
    let t = 1;
    for (let j = i - 1; j >= 0; j--) { if (a[j] <= a[i]) t++; else break; }
    return t;
  }
  function lowrange(a, i) {
    let t = 1;
    for (let j = i - 1; j >= 0; j--) { if (a[j] >= a[i]) t++; else break; }
    return t;
  }

  function computeChan(k) {
    const N = k.length;
    if (N < 10) return { pivot: new Array(N).fill(0), buy: new Array(N).fill(false), sell: new Array(N).fill(false), last3Buy: [] };
    const H = k.map(r => r.high), L = k.map(r => r.low), C = k.map(r => r.close);

    // ===== 局部高低点预选 (fixed for all levels) =====
    const lowAcond = k.map((r, i) => llv(L, i, 5) < llv(L, i - 1, 4));
    const lowA = backset(lowAcond, 4);
    const lowB = backset(lowA.map((v, i) => v === 0 && refV(lowA, i, 1) === 1), 2);
    const lowC = k.map((r, i) => (lowB[i] === 1 && refV(lowB, i, 1) === 0) ? -1 : 0);

    const highAcond = k.map((r, i) => hhv(H, i, 5) > hhv(H, i - 1, 4));
    const highA = backset(highAcond, 4);
    const highB = backset(highA.map((v, i) => v === 0 && refV(highA, i, 1) === 1), 2);
    const highC = k.map((r, i) => (highB[i] === 1 && refV(highB, i, 1) === 0) ? 1 : 0);

    // 缺口判断
    const gap = k.map((r, i) => L[i] > refV(H, i, 1) ? 1 : (H[i] < refV(L, i, 1) ? -1 : 0));

    // base distance from preselected pivots
    const baseDistH = k.map((r, i) => barslast(highC, i));
    const baseDistL = k.map((r, i) => barslast(lowC, i));
    const smallCycle = k.map((r, i) => lowrange(L, i));
    const bigCycle = k.map((r, i) => toprange(H, i));

    // ===== generic level: produces {high, low} pivot-retention arrays =====
    function levelCompute(prevLow, distH, distL, useInternalS) {
      const lowAA = new Array(N).fill(0), lowAB = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        const dh1 = refV(distH, i, 1), dl1 = refV(distL, i, 1);
        if (lowC[i] === -1 && dh1 > dl1 && llv(L, i, distH[i] + 1) < llv(L, i - 1, distH[i - 1] + 1)) lowAA[i] = -1;
        if (lowC[i] === -1 && dl1 <= dh1 && (distL[i] >= 4 || llv(gap, i, distL[i]) === -1 || llv(L, i, distL[i] + 2) < llv(L, i - 1, distL[i - 1] + 1))) lowAB[i] = -1;
      }
      const lowS = new Array(N).fill(0);
      for (let i = 0; i < N; i++) { if ((lowAA[i] === -1 || lowAB[i] === -1) && L[i] < refV(H, i, distH[i] + 1)) lowS[i] = -1; }
      const effLow = useInternalS ? lowS : prevLow;

      const yupan = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        const a = (distL[i] < 4 && hhv(gap, i, distL[i]) !== 1);
        const b = (refV(effLow, i, distL[i]) === 0);
        if (a || b) yupan[i] = 1;
      }
      const panduan = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (highC[i] === 1 && refV(distL, i, 1) <= refV(distH, i, 1) && yupan[i] === 1 &&
            bigCycle[i] > refV(smallCycle, i, distL[i] + 1) && bigCycle[i] > refV(smallCycle, i, distL[i]) && bigCycle[i] > refV(bigCycle, i, distH[i])) panduan[i] = 1;
      }
      const highA2 = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (highC[i] === 1 && refV(distL, i, 1) > refV(distH, i, 1) && hhv(H, i, distL[i] + 1) > hhv(H, i - 1, distL[i - 1] + 1)) highA2[i] = 1;
      }
      const highB2 = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (highC[i] === 1 && refV(distL, i, 1) <= refV(distH, i, 1) && refV(effLow, i, distL[i]) === -1 && (distL[i] >= 4 || hhv(gap, i, distL[i]) === 1)) highB2[i] = 1;
      }
      const high = new Array(N).fill(0);
      for (let i = 0; i < N; i++) { if ((highA2[i] === 1 || highB2[i] === 1 || panduan[i] === 1) && H[i] > refV(L, i, distL[i] + 1)) high[i] = 1; }

      const yupanA = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        const a = (distH[i] < 4 && hhv(gap, i, distH[i]) !== 1);
        const b = (refV(high, i, distH[i]) === 0);
        if (a || b) yupanA[i] = 1;
      }
      const panduanA = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (lowC[i] === -1 && refV(distH, i, 1) <= refV(distL, i, 1) && yupanA[i] === 1 &&
            smallCycle[i] > refV(bigCycle, i, distH[i] + 1) && smallCycle[i] > refV(bigCycle, i, distH[i]) && smallCycle[i] > refV(smallCycle, i, distL[i])) panduanA[i] = -1;
      }
      const lowA22 = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (lowC[i] === -1 && refV(distH, i, 1) > refV(distL, i, 1) && llv(L, i, distH[i] + 1) < llv(L, i - 1, distH[i - 1] + 1)) lowA22[i] = -1;
      }
      const lowB22 = new Array(N).fill(0);
      for (let i = 0; i < N; i++) {
        if (lowC[i] === -1 && refV(distH, i, 1) <= refV(distL, i, 1) && (distH[i] >= 4 || llv(gap, i, distH[i]) === -1 || panduanA[i] === -1)) lowB22[i] = -1;
      }
      const low = new Array(N).fill(0);
      for (let i = 0; i < N; i++) { if ((lowA22[i] === -1 || lowB22[i] === -1) && L[i] < refV(H, i, distH[i] + 1)) low[i] = -1; }
      return { high, low };
    }

    // base level (prevLow = internal 低保留S)
    const base = levelCompute(null, baseDistH, baseDistL, true);
    // X level (distance from base retention)
    const distH_A = k.map((r, i) => barslast(base.high.map(v => v === 1), i));
    const distL_A = k.map((r, i) => barslast(base.low.map(v => v === -1), i));
    const X = levelCompute(base.low, distH_A, distL_A, false);
    // YX level (distance from X retention)
    const distH_YA = k.map((r, i) => barslast(X.high.map(v => v === 1), i));
    const distL_YA = k.map((r, i) => barslast(X.low.map(v => v === -1), i));
    const YX = levelCompute(X.low, distH_YA, distL_YA, false);

    // final 极点保留
    const pivot = new Array(N).fill(0);
    for (let i = 0; i < N; i++) {
      const dH = refV(distH_YA, i, 1), dL = refV(distL_YA, i, 1);
      let aaad = 0;
      if (YX.high[i] === 1 && YX.low[i] === -1) {
        if (H[i] > refV(H, i, dH + 2)) aaad = 1;
        else if (L[i] < refV(L, i, dL + 2)) aaad = -1;
      }
      pivot[i] = (aaad === 0) ? (YX.high[i] + YX.low[i]) : aaad;
    }
    const buy = pivot.map(v => v === -1);
    const sell = pivot.map(v => v === 1);

    // last consecutive 3 trading-day buy bars
    const last3 = [];
    for (let i = N - 3; i < N; i++) if (i >= 0 && buy[i]) last3.push({ i, date: k[i].date });

    return { pivot, buy, sell, last3Buy: last3 };
  }

  const api = { computeChan };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (global) global.ChanEngine = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
