# -*- coding: utf-8 -*-
import json, collections
DOC = r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
doc = json.load(open(DOC, encoding="utf-8-sig"))
res = {}      # (table,key,field) -> (value, rule, path)
lists = {}    # (table,key,field) -> list ; list_combination targets
def add(t,k,f,v,rule,path,kind="str"):
    if f is None: res[(t,k,None)] = (v,rule,path)
    else: res[(t,k,f)] = (v,rule,path)
def addlist(t,k,f,v,rule,path):
    lists.setdefault((t,k,f), []).append(v)
    # keep a placeholder entry so key/table is created
    res.setdefault((t,k,f), ("<LIST>", rule, path))

S = doc["system"]
# ---------- A. system//monitor-link (rows 187-195)
ml = S["monitor-link"]["groups"]["group"]
for gk, g in ml.items():
    updelay = g.get("downlink",{}).get("config",{}).get("up-delay")
    for name, node in g["interfaces"]["interface"].items():
        thr = node.get("config",{}).get("threshold")
        is_bridge = name.startswith("Bridge-Aggregation")
        for direction in ("uplink","downlink"):
            if direction not in node: continue
            dpath = f"system/monitor-link/groups/group/{gk}/interfaces/interface/{name}/{direction}/config/enable"
            if is_bridge:
                if direction=="downlink":
                    iid = name[len("Bridge-Aggregation"):]
                    t,k,rule = "PORTCHANNEL","PortChannel"+iid,188
                else:
                    continue  # row 187 has no matching uplink leaf
            else:
                t,k,rule = "PORT",name,(193 if direction=="uplink" else 194)
            add(t,k,"updelaytime",updelay,rule,dpath)
            add(t,k,"linkmode",direction,rule,dpath)
            add(t,k,"groupid",gk,rule,dpath)
            add(t,k,"option","add",rule,dpath)
        tpath = f"system/monitor-link/groups/group/{gk}/interfaces/interface/{name}/config/threshold"
        if is_bridge:
            add("PORTCHANNEL","PortChannel"+name[len("Bridge-Aggregation"):],"threshold",thr,189,tpath)
        else:
            add("PORT",name,"threshold",thr,195,tpath)

# ---------- B. system//aaa (196-202)
A = S["aaa"]
add("AAA","account","commands","tacacs+",196,"system/aaa/accounting/events/event/command/config/accounting-method")
add("AAA","authorization","commands","tacacs+",197,"system/aaa/authorization/events/event/command/config/authorization-method")
add("AAA","authentication","login","tacacs+,local",198,"system/aaa/authentication/events/event/login/config/authentication-method")
for srv, sn in A["server-groups"]["server-group"]["tencent_scheme"]["servers"]["server"].items():
    base=f"system/aaa/server-groups/server-group/tencent_scheme/servers/server/{srv}"
    add("TACPLUS_SERVER",srv,"tcp_port",sn["config"]["tcp-port"],200,base+"/config/tcp-port")
    add("TACPLUS_SERVER",srv,"priority",sn["config"]["priority"],201,base+"/config/priority")
    add("TACPLUS","global","passkey",sn["tacacs"]["config"]["secret-key"],202,base+"/tacacs/config/secret-key")

# ---------- C. system//config, arp, nd (204-216)
C = S["config"]
add("DEVICE_METADATA","localhost","hostname",C["hostname"],204,"system/config/hostname")
add("DEVICE_METADATA","localhost","hwsku",C["hwsku"],205,"system/config/hwsku")
add("DEVICE_METADATA","localhost","type",C["role"],207,"system/config/role")
add("SHELL","passwd","passwd",C["login-shell"],210,"system/config/login-shell")
add("ZTP","flg","run",C["ztp-status"],211,"system/config/ztp-status")
add("DEVICE_METADATA","localhost","arp_to_route",S["arp"]["config"]["arp-to-route"],214,"system/arp/config/arp-to-route")
add("DEVICE_METADATA","localhost","nd_to_route",S["nd"]["config"]["nd-to-route"],215,"system/nd/config/nd-to-route")
add("DEVICE_METADATA","localhost","ndmask_v6",S["nd"]["config"]["ndmask-v6"],216,"system/nd/config/ndmask-v6")

# ---------- D. grpc 217,220,221,222
G=S["grpc"]["config"]
add("TELEMETRY","gnmi","status","enable",217,"system/grpc/config/enable")
add("TELEMETRY","usrpwd","password",G["password"],220,"system/grpc/config/password")
add("TELEMETRY","serverTls","type",G["tls-type"],221,"system/grpc/config/tls-type")
add("TELEMETRY","usrpwd","username",G["username"],222,"system/grpc/config/username")

# ---------- E. hash 225,227,228
H=S["hash"]["global"]["config"]
add("SWITCH","switch","ecmp_hash_alg",H["algorithm-ecmp"],225,"system/hash/global/config/algorithm-ecmp")
add("SWITCH","switch","ecmp_hash_seed",H["ecmp-hash-seed"],227,"system/hash/global/config/ecmp-hash-seed")
add("SWITCH","switch","lag_hash_seed",H["lag-hash-seed"],228,"system/hash/global/config/lag-hash-seed")

# ---------- F. logging 254,255
for srv, sn in S["logging"]["remote-servers"]["remote-server"].items():
    base=f"system/logging/remote-servers/remote-server/{srv}"
    add("SYSLOG_SERVER","syslog_server","level","notice",254,base+"/config/host")
    addlist("SYSLOG_SERVER","syslog_server","servers",srv,254,base+"/config/host")
    add("SYSLOG_SERVER","syslog_server","level","info",255,base+"/selectors/selector/LOCAL2 INFORMATIONAL/config/severity")

# ---------- G. ntp 256
for srv in S["ntp"]["servers"]["server"]:
    res[("NTP_SERVER",srv,None)] = ({},256,f"system/ntp/servers/server/{srv}/config/address")

# ---------- H. snmp 257
for cname, cn in S["snmp"]["communities"]["community"].items():
    base=f"system/snmp/communities/community/{cname}"
    add("SNMP","snmp","snmp_location","public",257,base+"/config/name")
    add("SNMP","snmp","snmp_rocommunity",cname,257,base+"/config/name")

# ---------- I. counter 259-296
CNT=S["counter"]
COUNTER_MAP = {  # yaml section -> (sonic table, rule_enable, rule_poll)
 "buffer-pool":("BUFFER_POOL",259,278), "buffer-pool-watermark":("BUFFER_POOL_WATERMARK",260,279),
 "pg":("PG",261,280), "queue-watermark":("QUEUE_WATERMARK",262,281), "pg-watermark":("PG_WATERMARK",263,282),
 "pfcwd":("PFCWD",265,284), "queue":("QUEUE",266,289), "port":("PORT",267,285),
 "port-phy":("PORT_PHY",269,287), "acl":("ACL",270,288), "policer":("POLICER",272,291),
}
for sec, node in CNT.items():
    if sec not in COUNTER_MAP: continue
    t,re_,rp = COUNTER_MAP[sec]
    cfg=node["config"]
    add("FLEX_COUNTER_TABLE",t,"FLEX_COUNTER_STATUS", "enable" if cfg["enable"]=="true" else "disable", re_, f"system/counter/{sec}/config/enable")
    add("FLEX_COUNTER_TABLE",t,"POLL_INTERVAL", cfg["poll-interval"], rp, f"system/counter/{sec}/config/poll-interval")

# ---------- J. dns 348
for srv in S["dns"]["servers"]["server"]:
    addlist("DNS","server","ip",srv,348,f"system/dns/servers/server/{srv}/address")

# ---------- K. sampling 364-372
SF=S["sampling"]["sflow"]
for name, node in SF["interfaces"]["interface"].items():
    cfg=node["config"]; base=f"system/sampling/sflow/interfaces/interface/{name}/config"
    add("SFLOW_SESSION",name,"sample_rate",cfg["sample-rate"],364,base+"/sample-rate")
    add("SFLOW_SESSION",name,"admin_state","up" if cfg["enable"]=="true" else "down",365,base+"/enable")
    add("SFLOW_SESSION",name,"sample_stage",cfg["direction"],366,base+"/direction")
c=SF["config"]
add("SFLOW","global","agent_id",c["source-interface"],367,"system/sampling/sflow/config/source-interface")
add("SFLOW","global","admin_state","up" if c["enable"]=="true" else "down",368,"system/sampling/sflow/config/enable")
add("SFLOW","global","max_datagram_size",c["datagram-size"],369,"system/sampling/sflow/config/datagram-size")
add("SFLOW","global","cpu_rate_limit",c["cpu-rate-limit"],370,"system/sampling/sflow/config/cpu-rate-limit")
for col, cn in SF["collectors"]["collector"].items():
    for ip, sn in cn["servers"]["server"].items():
        base=f"system/sampling/sflow/collectors/collector/{col}/servers/server/{ip}/config"
        add("SFLOW_COLLECTOR",col,"collector_ip",sn["config"]["address"],371,base+"/address")
        add("SFLOW_COLLECTOR",col,"collector_port",sn["config"]["port"],372,base+"/port")

# ---------- L. components 673-697
import math
BUF=doc["components"]["component"]["buffer"]["integrated-circuit"]["chip"]
sh=BUF["buffers"]["buffer"]["SHARED_BUFFER"]["interfaces"]["interface"]
hd=BUF["buffers"]["buffer"]["HEADROOM"]["interfaces"]["interface"]
sl=BUF["buffers"]["buffer"]["SHARED_BUFFER"]["slices"]["slice"]["sliceall"]
add("BUFFER_NOTIFICATION","BUFFER_POOL","pool_share_th",sl["output"]["config"]["alarm-threshold"],673,
    "components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice/sliceall/output/config/alarm-threshold")
add("BUFFER_POOL","ingress_lossy_pool","mode",sl["input"]["config"]["limit-mode"].lower(),674,
    "components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-mode")
add("BUFFER_POOL","ingress_lossy_pool","size",sl["input"]["config"]["limit-threshold"],675,
    "components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-threshold")
add("BUFFER_POOL","ingress_lossy_pool","type","ingress",675,
    "components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/slices/slice/sliceall/input/config/limit-threshold")
hd_sl = BUF["buffers"]["buffer"]["HEADROOM"]["slices"]["slice"]["sliceall"]
add("BUFFER_POOL","ingress_lossy_pool","xoff",hd_sl["input"]["config"]["limit-threshold"],676,
    "components/component/buffer/integrated-circuit/chip/buffers/buffer/HEADROOM/slices/slice/sliceall/input/config/limit-threshold")
def log2(v):
    f=eval(v) if '/' in str(v) else float(v)
    f=float(f)
    r=math.log2(f)
    return str(int(r)) if r==int(r) else repr(r)
for name, node in sh.items():
    b=f"components/component/buffer/integrated-circuit/chip/buffers/buffer/SHARED_BUFFER/interfaces/interface/{name}"
    oq=node["output"]["queues"]["queue"]["queue5"]; ocfg=oq["config"]
    iq=node["input"]["queues"]["queue"]["queue5"]; icfg=iq["config"]
    add("BUFFER_QUEUE",name+"|5","profile","[BUFFER_PROFILE|egress_profile_"+name+"_5]",677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","dynamic_th",log2(ocfg["limit-threshold"]),677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","pool","[BUFFER_POOL|egress_lossy_pool]",677,b+"/output/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","egress_profile_"+name+"_5","size",ocfg["min-threshold"],678,b+"/output/queues/queue/queue5/config/min-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","queue_share_th",ocfg["alarm-threshold"],679,b+"/output/queues/queue/queue5/config/alarm-threshold")
    add("BUFFER_PG",name+"|5","profile","[BUFFER_PROFILE|ingress_profile_"+name+"_5]",681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","dynamic_th",log2(icfg["limit-threshold"]),681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","pool","[BUFFER_POOL|ingress_lossy_pool]",681,b+"/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","xon_offset",icfg["xon-offset-threshold"],682,b+"/input/queues/queue/queue5/config/xon-offset-threshold")
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","size",icfg["min-threshold"],683,b+"/input/queues/queue/queue5/config/min-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","pg_shared_th",icfg["alarm-threshold"],684,b+"/input/queues/queue/queue5/config/alarm-threshold")
    hnode=hd[name]["input"]["queues"]["queue"]["queue5"]["config"]
    add("BUFFER_PROFILE","ingress_profile_"+name+"_5","xoff",hnode["limit-threshold"],685,
        f"components/component/buffer/integrated-circuit/chip/buffers/buffer/HEADROOM/interfaces/interface/{name}/input/queues/queue/queue5/config/limit-threshold")
    add("BUFFER_NOTIFICATION",name+"|5","pg_hdrm_th",hnode["alarm-threshold"],686,
        f"components/component/buffer/integrated-circuit/chip/buffers/buffer/HEADROOM/interfaces/interface/{name}/input/queues/queue/queue5/config/alarm-threshold")
bm=BUF["buffer-monitor"]["config"]
add("BUFFER_NOTIFICATION","Suppress","time",bm["suppress-time"],691,"components/component/buffer/integrated-circuit/chip/buffer-monitor/config/suppress-time")
add("BUFFER_NOTIFICATION","Suppress","number",bm["suppress-num"],692,"components/component/buffer/integrated-circuit/chip/buffer-monitor/config/suppress-num")

# ---------- M. YANG_VALIDATION 733-734
YV=doc["YANG_VALIDATION"]["config"]
add("YANG_VALIDATION","config","enable","True" if YV["enable"]=="true" else "False",733,"YANG_VALIDATION/config/enable")
add("YANG_VALIDATION","config","intercept","True" if YV["intercept"]=="true" else "False",734,"YANG_VALIDATION/config/intercept")

# ---------- emit
lines=[]
for (t,k,f),(v,rule,path) in res.items():
    if f is None:
        lhs=f"{t}|{k}"
        val={}
    else:
        lhs=f"{t}|{k}|{f}"
        val=v
    if (t,k,f) in lists: val=lists[(t,k,f)]
    lines.append((lhs, json.dumps(val, ensure_ascii=False), rule, path))
lines.sort(key=lambda x:x[0])
out=[]
for lhs,val,rule,path in lines:
    out.append(f"{lhs} = {val}  # row {rule}; {path}")
open("tmp_sys_expected_body.txt","w",encoding="utf-8").write("\n".join(out))
print("lines:", len(lines))
print("tables:", collections.Counter(t for t,k,f in res))
import json as _j
print("sample:"); print("\n".join(out[:3])); print("..."); print("\n".join(out[-3:]))

