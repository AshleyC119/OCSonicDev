import csv, json, re, ast
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))

def flatten(node, path, out):
    if isinstance(node, dict):
        if not node: out.append((tuple(path), {}))
        for k,v in node.items(): flatten(v, path+[str(k)], out)
    elif isinstance(node, list):
        out.append((tuple(path), node))
    else:
        out.append((tuple(path), node))
leaves=[]
flatten(doc, [], leaves)

def compile_seg(seg):
    parts = re.split(r'(\$[^$]+\$)', seg)
    rx = "^"
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p)>2:
            rx += "(.+?)"
        elif p:
            rx += re.escape(p)
    rx += "$"
    return rx, [p[1:-1] for p in parts if p.startswith("$") and p.endswith("$") and len(p)>2]

def literal_count(seg):
    parts = re.split(r'(\$[^$]+\$)', seg)
    return sum(len(p) for p in parts if p and not (p.startswith("$") and p.endswith("$")))

def match(pattern):
    segs = pattern.split("//")
    comp = [compile_seg(s) for s in segs]
    lits = sum(literal_count(s) for s in segs)
    res=[]
    for path,val in leaves:
        if len(path)!=len(segs): continue
        b={}
        ok=True
        for (p,(rx,names)) in zip(path,comp):
            m=re.fullmatch(rx,p)
            if not m: ok=False; break
            for name,g in zip(names,m.groups()):
                if name in b and b[name]!=g: ok=False; break
                b[name]=g
            if not ok: break
        if ok: res.append((path,val,b))
    return res,lits

spines_mine = {
 "system//":1,"components//component":1,"YANG_VALIDATION//config":1,"DEVICE_METADATA//localhost":1,
 "LLDP_GLOBAL//global":1,"NTP//global":1,"SNMP//snmp":1,"TACPLUS//global":1,
 "SYSLOG_SERVER//syslog_server":1,"TELEMETRY//gnmi":1,"telemetry-system//":1,
 "SYSTEM_PORT//":1,"BUFFER_POOL//":1,"BUFFER_PROFILE//":1,"BUFFER_QUEUE//":1,"BUFFER_PG//":1,
 "PBR_RULE//":1,"PBR_NHG//":1,"PBR_NHG_MEMBER//":1,"BGP_VRF//":1,"BGP_VRF_LEAKING_IPV4//":1,"BGP_VRF_LEAKING_IPV6//":1,
}
out=[]
tot=0; fire=0
for i,r in enumerate(rows):
    sp=r["spine"]
    if not any(sp==m or sp.startswith(m) for m in spines_mine): continue
    tot+=1
    res,lits=match(r["yang_key"])
    if res:
        fire+=1
        out.append(f"ROW {i} [{sp}] lits={lits} matches={len(res)}")
        for path,val,b in res[:4]:
            out.append(f"    path={'/'.join(path)} value={json.dumps(val)[:60]} bind={b}")
        if len(res)>4: out.append(f"    ... ({len(res)-4} more)")
    else:
        out.append(f"ROW {i} [{sp}] lits={lits} NO-MATCH  key={r['yang_key']}")
print(f"my rows={tot} fire={fire} nomatch={tot-fire}")
open("tmp_sys_match.txt","w",encoding="utf-8").write("\n".join(out))
