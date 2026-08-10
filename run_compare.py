import json, importlib.util, importlib.machinery

BASE = "/Users/samt/golden_stock_observer"
KR = json.load(open(f"{BASE}/output/kline_raw.json"))

spec5 = importlib.util.spec_from_file_location("server5", f"{BASE}/golden_diamond_viewer/server.py")
server5 = importlib.util.module_from_spec(spec5); spec5.loader.exec_module(server5)
loader2 = importlib.machinery.SourceFileLoader("server2", f"{BASE}/_backup_window_cmp/server.py.bak")
spec2 = importlib.util.spec_from_loader("server2", loader2)
server2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(server2)

def sigs(server):
    up = set(); buy = set(); bad = 0
    for st in KR:
        rows = [{**r, "close": r.get("last", r.get("close"))} for r in (st.get("kline") or [])]
        if len(rows) < 30:
            continue
        try:
            r = server.analyze(rows)
        except Exception:
            bad += 1
            continue
        c = st.get("code")
        for sig in r.get("signals", []):
            t = sig.get("type", "")
            if t == "金钻起涨":
                up.add(c)
            elif t == "买入":
                buy.add(c)
    return up, buy, bad

up5, buy5, b5 = sigs(server5)
up2, buy2, b2 = sigs(server2)
print("金钻起涨  n-5:", len(up5), " n-2:", len(up2), " 纯窗口新增:", sorted(up5 - up2))
print("买入      n-5:", len(buy5), " n-2:", len(buy2), " 纯窗口新增:", sorted(buy5 - buy2))
print("analyze报错 n-5:", b5, " n-2:", b2)
