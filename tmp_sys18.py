import json
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
comp = doc["components"]["component"]["buffer"]["integrated-circuit"]["chip"]["buffers"]["buffer"]
sh = comp["SHARED_BUFFER"]["interfaces"]["interface"]
hd = comp["HEADROOM"]["interfaces"]["interface"]
print("SHARED ifaces:", len(sh), sorted(sh))
print("HEADROOM ifaces:", len(hd), sorted(hd))
print("set equal:", set(sh)==set(hd))
# check queue configs uniform
outs=set(); ins=set(); outmin=set(); inmin=set(); alarm=set(); hdlim=set(); hdalarm=set()
for n,i in sh.items():
    oq=i.get("output",{}).get("queues",{}).get("queue",{})
    iq=i.get("input",{}).get("queues",{}).get("queue",{})
    for qn,q in oq.items():
        outs.add((qn,json.dumps(q.get("config")))); 
    for qn,q in iq.items():
        ins.add((qn,json.dumps(q.get("config"))))
for n,i in hd.items():
    for qn,q in i.get("input",{}).get("queues",{}).get("queue",{}).items():
        hdlim.add((qn,json.dumps(q.get("config"))))
print("output queues:", outs)
print("input queues:", ins)
print("headroom input queues:", hdlim)
ml = doc["system"]["monitor-link"]["groups"]["group"]["1"]["interfaces"]["interface"]
print("monitor ifaces:", len(ml), sorted(ml))
print("ml set == shared?", set(ml)==set(sh))
sf = doc["system"]["sampling"]["sflow"]["interfaces"]["interface"]
print("sflow ifaces:", len(sf), set(sf)==set(sh))
print("sflow distinct:", sorted({json.dumps(v["config"],sort_keys=True) for v in sf.values()}))
