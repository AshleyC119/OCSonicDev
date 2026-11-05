import json
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
ml = doc["system"]["monitor-link"]
print("monitor-link groups:", list(ml["groups"]["group"].keys()))
for gname, g in ml["groups"]["group"].items():
    print("GROUP", gname, "keys:", list(g.keys()))
    ifaces = g["interfaces"]["interface"]
    print("  n interfaces:", len(ifaces))
    for iname, i in ifaces.items():
        dirs = [d for d in ("uplink","downlink") if d in i]
        print(f"   {iname}: dirs={dirs} cfgs={ {k:list(v.get('config',{}).items()) for k,v in i.items() if isinstance(v,dict) and 'config' in v} }")
    for k,v in g.items():
        if k not in ("interfaces",): print("  group key", k, "=", json.dumps(v)[:200])
