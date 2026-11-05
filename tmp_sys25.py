import csv, json, re, collections
rows=list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv",encoding="utf-8-sig")))
doc=json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt",encoding="utf-8-sig"))
def flatten(n,p,out):
    if isinstance(n,dict):
        if not n: out.append((tuple(p),{}))
        for k,v in n.items(): flatten(v,p+[str(k)],out)
    elif isinstance(n,list): out.append((tuple(p),n))
    else: out.append((tuple(p),n))
leaves=[]; flatten(doc,[],leaves)
def seg_rx(seg):
    parts=re.split(r'(\$[^$]+\$)',seg); rx="^"
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p)>2: rx+="(.+?)"
        elif p: rx+=re.escape(p)
    return rx+"$"
comp=[(i,r["spine"],r["yang_key"].split("//"),[seg_rx(s) for s in r["yang_key"].split("//")]) for i,r in enumerate(rows)]
mine_prefixes=("system","components","YANG_VALIDATION","YANG_VALIDATION")
mine_spines=set()
for i,sp,segs,rxs in comp:
    pass
MY=["system//","components//component","YANG_VALIDATION//config","DEVICE_METADATA//localhost","LLDP_GLOBAL//global","NTP//global","SNMP//snmp","TACPLUS//global","SYSLOG_SERVER//syslog_server","TELEMETRY//gnmi","telemetry-system//","SYSTEM_PORT//","BUFFER_POOL//","BUFFER_PROFILE//","BUFFER_QUEUE//","BUFFER_PG//","PBR_RULE//","PBR_NHG//","PBR_NHG_MEMBER//","BGP_VRF//","BGP_VRF_LEAKING_IPV4//","BGP_VRF_LEAKING_IPV6//"]
def is_mine(sp): return any(sp==m or sp.startswith(m) for m in MY)
cross=0
for path,val in leaves:
    if not path or path[0] not in ("system","components","YANG_VALIDATION"): continue
    cands=[]
    for i,sp,segs,rxs in comp:
        if len(path)!=len(segs): continue
        if all(re.fullmatch(rx,p) for rx,p in zip(rxs,path)): cands.append((i,sp))
    if any(not is_mine(sp) for i,sp in cands):
        cross+=1
        print("CROSS:", "/".join(path), cands)
print("cross-group candidate leaves:", cross)
