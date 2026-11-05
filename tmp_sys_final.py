# -*- coding: utf-8 -*-
import json, csv, re, math, collections, hashlib, os
DOC = r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
CSV = r"references/raw/yang2sonic_maptable(1).csv"
doc = json.load(open(DOC, encoding="utf-8-sig"))
rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))

# ---------------- flatten + matcher
def flatten(node, path, out):
    if isinstance(node, dict):
        if not node: out.append((tuple(path), {}))
        for k,v in node.items(): flatten(v, path+[str(k)], out)
    elif isinstance(node, list): out.append((tuple(path), node))
    else: out.append((tuple(path), node))
leaves=[]; flatten(doc, [], leaves)
def seg_rx(seg):
    parts = re.split(r'(\$[^$]+\$)', seg); rx="^"
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p)>2: rx+="(.+?)"
        elif p: rx+=re.escape(p)
    return rx+"$"
def litchars(pattern): return sum(len(re.sub(r'\$[^$]+\$','',s)) for s in pattern.split("//"))
def match(pattern):
    segs=pattern.split("//"); rxs=[seg_rx(s) for s in segs]; res=[]
    for path,val in leaves:
        if len(path)!=len(segs): continue
        b={}; ok=True
        for p,(rx,seg) in zip(path, zip(rxs,segs)):
            m=re.fullmatch(rx,p)
            if not m: ok=False; break
            names=re.findall(r'\$([^$]+)\$',seg)
            for name,g in zip(names,m.groups()):
                if name in b and b[name]!=g: ok=False; break
                b[name]=g
            if not ok: break
        if ok: res.append((path,val,b))
    return res

MY = ["system//","components//component","YANG_VALIDATION//config","DEVICE_METADATA//localhost",
 "LLDP_GLOBAL//global","NTP//global","SNMP//snmp","TACPLUS//global","SYSLOG_SERVER//syslog_server",
 "TELEMETRY//gnmi","telemetry-system//","SYSTEM_PORT//","BUFFER_POOL//","BUFFER_PROFILE//","BUFFER_QUEUE//",
 "BUFFER_PG//","PBR_RULE//","PBR_NHG//","PBR_NHG_MEMBER//","BGP_VRF//","BGP_VRF_LEAKING_IPV4//","BGP_VRF_LEAKING_IPV6//"]
def is_mine(sp): return any(sp==m or sp.startswith(m) for m in MY)
myrows=[(i,r) for i,r in enumerate(rows) if is_mine(r["spine"])]
spines=[]
for i,r in myrows:
    if r["spine"] not in spines: spines.append(r["spine"])

# walk to find dead-at segment
def dead_reason(pattern):
    segs=pattern.split("//"); node=doc; depth=0
    for i,s in enumerate(segs):
        key=None
        if "$" in s:
            # resolve against known keys: try to find a dict key matching regex
            rx=seg_rx(s); cand=[k for k in node if re.fullmatch(rx,k)] if isinstance(node,dict) else []
            if not cand: return (i, "no matching key for placeholder segment '%s'"%s, "/".join(segs[:i]))
            key=cand[0]
        else:
            if isinstance(node,dict) and s in node: key=s
            else: return (i, "missing key '%s'"%s, "/".join(segs[:i]))
        node=node[key]; depth=i+1
    return (depth, "full path exists (unexpected)", "")

outcomes={}
for i,r in myrows:
    mm=match(r["yang_key"])
    outcomes[i]={"spine":r["spine"],"yang_key":r["yang_key"],"matches":[(list(p),v,b) for p,v,b in mm]}
# ---------------- emission derivation (hand-derived, per rule)
res={}; lists={}
def add(t,k,f,v,rule,path):
    res[(t,k,f)] = (v,rule,path)
def addlist(t,k,f,v,rule,path):
    lists.setdefault((t,k,f),[]).append(v)
    res.setdefault((t,k,f), ("<LIST>",rule,path))
S=doc["system"]
# monitor-link 187-195
for gk,g in S["monitor-link"]["groups"]["group"].items():
    updelay=g.get("downlink",{}).get("config",{}).get("up-delay")
    for name,node in g["interfaces"]["interface"].items():
        is_b=name.startswith("Bridge-Aggregation")
        for direction in ("uplink","downlink"):
            if direction not in node: continue
            if is_b:
                if direction!="downlink": continue
                t,k,rule="PORTCHANNEL","PortChannel"+name[len("Bridge-Aggregation"):],188
            else:
                t,k,rule="PORT",name,(193 if direction=="uplink" else 194)
            p=f"system/monitor-link/groups/group/{gk}/interfaces/interface/{name}/{direction}/config/enable"
            add(t,k,"updelaytime",updelay,rule,p); add(t,k,"linkmode",direction,rule,p)
            add(t,k,"groupid",gk,rule,p); add(t,k,"option","add",rule,p)
        p=f"system/monitor-link/groups/group/{gk}/interfaces/interface/{name}/config/threshold"
        add(("PORTCHANNEL" if is_b else "PORT"), ("PortChannel"+name[len("Bridge-Aggregation"):] if is_b else name), "threshold", node["config"]["threshold"], (189 if is_b else 195), p)
# aaa
A=S["aaa"]
add("AAA","account","commands","tacacs+",196,"system/aaa/accounting/events/event/command/config/accounting-method")
add("AAA","authorization","commands","tacacs+",197,"system/aaa/authorization/events/event/command/config/authorization-method")
add("AAA","authentication","login","tacacs+,local",198,"system/aaa/authentication/events/event/login/config/authentication-method")
for srv,sn in A["server-groups"]["server-group"]["tencent_scheme"]["servers"]["server"].items():
    b=f"system/aaa/server-groups/server-group/tencent_scheme/servers/server/{srv}"
    add("TACPLUS_SERVER",srv,"tcp_port",sn["config"]["tcp-port"],200,b+"/config/tcp-port")
    add("TACPLUS_SERVER",srv,"priority",sn["config"]["priority"],201,b+"/config/priority")
    add("TACPLUS","global","passkey",sn["tacacs"]["config"]["secret-key"],202,b+"/tacacs/config/secret-key")
# config/arp/nd
C=S["config"]
add("DEVICE_METADATA","localhost","hostname",C["hostname"],204,"system/config/hostname")
add("DEVICE_METADATA","localhost","hwsku",C["hwsku"],205,"system/config/hwsku")
add("DEVICE_METADATA","localhost","type",C["role"],207,"system/config/role")
add("SHELL","passwd","passwd",C["login-shell"],210,"system/config/login-shell")
add("ZTP","flg","run",C["ztp-status"],211,"system/config/ztp-status")
add("DEVICE_METADATA","localhost","arp_to_route",S["arp"]["config"]["arp-to-route"],214,"system/arp/config/arp-to-route")
add("DEVICE_METADATA","localhost","nd_to_route",S["nd"]["config"]["nd-to-route"],215,"system/nd/config/nd-to-route")
add("DEVICE_METADATA","localhost","ndmask_v6",S["nd"]["config"]["ndmask-v6"],216,"system/nd/config/ndmask-v6")
# grpc
G=S["grpc"]["config"]
add("TELEMETRY","gnmi","status","enable",217,"system/grpc/config/enable")
add("TELEMETRY","usrpwd","password",G["password"],220,"system/grpc/config/password")
add("TELEMETRY","serverTls","type",G["tls-type"],221,"system/grpc/config/tls-type")
add("TELEMETRY","usrpwd","username",G["username"],222,"system/grpc/config/username")
# hash
H=S["hash"]["global"]["config"]
add("SWITCH","switch","ecmp_hash_alg",H["algorithm-ecmp"],225,"system/hash/global/config/algorithm-ecmp")
add("SWITCH","switch","ecmp_hash_seed",H["ecmp-hash-seed"],227,"system/hash/global/config/ecmp-hash-seed")
add("SWITCH","switch","lag_hash_seed",H["lag-hash-seed"],228,"system/hash/global/config/lag-hash-seed")
# logging
for srv,sn in S["logging"]["remote-servers"]["remote-server"].items():
    b=f"system/logging/remote-servers/remote-server/{srv}"
    add("SYSLOG_SERVER","syslog_server","level","notice",254,b+"/config/host")
    addlist("SYSLOG_SERVER","syslog_server","servers",srv,254,b+"/config/host")
    add("SYSLOG_SERVER","syslog_server","level","info",255,b+"/selectors/selector/LOCAL2 INFORMATIONAL/config/severity")
# ntp
for srv in S["ntp"]["servers"]["server"]:
    res[("NTP_SERVER",srv,None)]=({},256,f"system/ntp/servers/server/{srv}/config/address")
# snmp
for cname in S["snmp"]["communities"]["community"]:
    b=f"system/snmp/communities/community/{cname}"
    add("SNMP","snmp","snmp_location","public",257,b+"/config/name")
    add("SNMP","snmp","snmp_rocommunity",cname,257,b+"/config/name")
# counter
CM={"buffer-pool":("BUFFER_POOL",259,278),"buffer-pool-watermark":("BUFFER_POOL_WATERMARK",260,279),"pg":("PG",261,280),
 "queue-watermark":("QUEUE_WATERMARK",262,281),"pg-watermark":("PG_WATERMARK",263,282),"pfcwd":("PFCWD",265,284),
 "queue":("QUEUE",266,289),"port":("PORT",267,285),"port-phy":("PORT_PHY",269,287),"acl":("ACL",270,288),"policer":("POLICER",272,291)}
for sec,node in S["counter"].items():
    if sec not in CM: continue
    t,re_,rp=CM[sec]; cfg=node["config"]
    add("FLEX_COUNTER_TABLE",t,"FLEX_COUNTER_STATUS","enable" if cfg["enable"]=="true" else "disable",re_,f"system/counter/{sec}/config/enable")
    add("FLEX_COUNTER_TABLE",t,"POLL_INTERVAL",cfg["poll-interval"],rp,f"system/counter/{sec}/config/poll-interval")
# dns
for srv in S["dns"]["servers"]["server"]:
    addlist("DNS","server","ip",srv,348,f"system/dns/servers/server/{srv}/address")
# sampling
SF=S["sampling"]["sflow"]
for name,node in SF["interfaces"]["interface"].items():
    cfg=node["config"]; b=f"system/sampling/sflow/interfaces/interface/{name}/config"
    add("SFLOW_SESSION",name,"sample_rate",cfg["sample-rate"],364,b+"/sample-rate")
    add("SFLOW_SESSION",name,"admin_state","up" if cfg["enable"]=="true" else "down",365,b+"/enable")
    add("SFLOW_SESSION",name,"sample_stage",cfg["direction"],366,b+"/direction")
c=SF["config"]
add("SFLOW","global","agent_id",c["source-interface"],367,"system/sampling/sflow/config/source-interface")
add("SFLOW","global","admin_state","up" if c["enable"]=="true" else "down",368,"system/sampling/sflow/config/enable")
add("SFLOW","global","max_datagram_size",c["datagram-size"],369,"system/sampling/sflow/config/datagram-size")
add("SFLOW","global","cpu_rate_limit",c["cpu-rate-limit"],370,"system/sampling/sflow/config/cpu-rate-limit")
for col,cn in SF["collectors"]["collector"].items():
    for ip,sn in cn["servers"]["server"].items():
        b=f"system/sampling/sflow/collectors/collector/{col}/servers/server/{ip}/config"
        add("SFLOW_COLLECTOR",col,"collector_ip",sn["config"]["address"],371,b+"/address")
        add("SFLOW_COLLECTOR",col,"collector_port",sn["config"]["port"],372,b+"/port")
# components
def log2(v):
    f=float(eval(v)) if "/" in str(v) else float(v)
    r=math.log2(f); return str(int(r)) if abs(r-round(r))<1e-9 else repr(r)
BUF=doc["components"]["component"]["buffer"]["integrated-circuit"]["chip"]
sh=BUF["buffers"]["buffer"]["SHARED_BUFFER"]["interfaces"]["interface"]
hd=BUF["buffers"]["buffer"]["HEADROOM"]["interfaces"]["interface"]
sl=BUF["buffers"]["buffer"]["SHARED_BUFFER"]["slices"]["slice"]["sliceall"]
hsl=BUF["buffers"]["buffer"]["HEADROOM"]["slices"]["slice"]["sliceall"]
CP="components/component/buffer/integrated-circuit/chip/buffers/buffer"
add("BUFFER_NOTIFICATION","BUFFER_POOL","pool_share_th",sl["output"]["config"]["alarm-threshold"],673,CP+"/SHARED_BUFFER/slices/slice/sliceall/output/config/alarm-threshold")
add("BUFFER_POOL","ingress_lossy_pool","mode",sl["input"]["config"]["limit-mode"].lower(),674,CP+"/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-mode")
add("BUFFER_POOL","ingress_lossy_pool","size",sl["input"]["config"]["limit-threshold"],675,CP+"/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-threshold")
add("BUFFER_POOL","ingress_lossy_pool","type","ingress",675,CP+"/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-threshold")
add("BUFFER_POOL","ingress_lossy_pool","xoff",hsl["input"]["config"]["limit-threshold"],676,CP+"/HEADROOM/slices/slice/sliceall/input/config/limit-threshold")
for name,node in sh.items():
    b=f"{CP}/SHARED_BUFFER/interfaces/interface/{name}"
    oc=node["output"]["queues"]["queue"]["queue5"]["config"]; ic=node["input"]["queues"]["queue"]["queue5"]["config"]
    add("BUFFER_QUEUE",name+"|5","profile","[BUFFER_PROFILE|egress_profile_"+name+"_5]",677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","dynamic_th",log2(oc["limit-threshold"]),677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","pool","[BUFFER_POOL|egress_lossy_pool]",677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","size",oc["min-threshold"],678,b+"/output/queues/queue/queue5/config/min-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","queue_share_th",oc["alarm-threshold"],679,b+"/output/queues/queue/queue5/config/alarm-threshold")
    add("BUFFER_PG",name+"|5","profile","[BUFFER_PROFILE|ingress_profile_"+name+"_5]",681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","dynamic_th",log2(ic["limit-threshold"]),681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","pool","[BUFFER_POOL|ingress_lossy_pool]",681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","xon_offset",ic["xon-offset-threshold"],682,b+"/input/queues/queue/queue5/config/xon-offset-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","size",ic["min-threshold"],683,b+"/input/queues/queue/queue5/config/min-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","pg_shared_th",ic["alarm-threshold"],684,b+"/input/queues/queue/queue5/config/alarm-threshold")
    hn=hd[name]["input"]["queues"]["queue"]["queue5"]["config"]
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","xoff",hn["limit-threshold"],685,f"{CP}/HEADROOM/interfaces/interface/{name}/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","pg_hdrm_th",hn["alarm-threshold"],686,f"{CP}/HEADROOM/interfaces/interface/{name}/input/queues/queue/queue5/config/alarm-threshold")
bm=BUF["buffer-monitor"]["config"]
add("BUFFER_NOTIFICATION","Suppress","time",bm["suppress-time"],691,CP+"/buffer-monitor/config/suppress-time")
add("BUFFER_NOTIFICATION","Suppress","number",bm["suppress-num"],692,CP+"/buffer-monitor/config/suppress-num")
# YANG_VALIDATION
YV=doc["YANG_VALIDATION"]["config"]
add("YANG_VALIDATION","config","enable","True" if YV["enable"]=="true" else "False",733,"YANG_VALIDATION/config/enable")
add("YANG_VALIDATION","config","intercept","True" if YV["intercept"]=="true" else "False",734,"YANG_VALIDATION/config/intercept")

# ---------------- build lines & per-row emission counts
lines=[]
row_emit=collections.Counter()
for (t,k,f),(v,rule,path) in res.items():
    if f is None: lhs=f"{t}|{k}"; val={}
    else: lhs=f"{t}|{k}|{f}"; val=v
    if (t,k,f) in lists: val=lists[(t,k,f)]
    lines.append((lhs, json.dumps(val, ensure_ascii=False), rule, path))
    row_emit[rule]+=1
lines.sort(key=lambda x:x[0])
os.makedirs("audit", exist_ok=True)
with open("audit/system.expected.txt","w",encoding="utf-8",newline="\n") as fh:
    for lhs,val,rule,path in lines:
        fh.write(f"{lhs} = {val}  # row {rule}; {path}\n")
print("expected lines:", len(lines))
# save outcomes
cnt=collections.Counter()
for i,o in outcomes.items():
    a=rows[i]["spine"]
    cnt[a]+=1
sp=collections.Counter()
for i,o in outcomes.items():
    if any(True for _ in o["matches"]): sp[rows[i]["spine"]]+=1
for s in spines:
    print(f"{s}: rules={cnt[s]} fire={sp.get(s,0)} emits={sum(row_emit[i] for i in outcomes if rows[i]['spine']==s)}")
json.dump({"outcomes":{str(k):{"spine":v["spine"],"yang_key":v["yang_key"],
   "matches":[{"path":"/".join(p),"value":val,"bind":b} for p,val,b in v["matches"]],
   "emits":row_emit.get(k,0)} for k,v in outcomes.items()}}, open("tmp_sys_outcomes.json","w",encoding="utf-8"), indent=0)
