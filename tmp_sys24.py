import json, collections
doc=json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt",encoding="utf-8-sig"))
sf=doc["system"]["sampling"]["sflow"]["interfaces"]["interface"]
c=collections.Counter((v["config"]["direction"],v["config"]["sample-rate"]) for v in sf.values())
print("sflow dir/rate:",dict(c))
oc=json.load(open("tmp_sys_outcomes.json",encoding="utf-8"))
import re
def seg_rx(seg):
    parts=re.split(r'(\$[^$]+\$)',seg); rx="^"
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p)>2: rx+="(.+?)"
        elif p: rx+=re.escape(p)
    return rx+"$"
def dead_reason(pattern):
    segs=pattern.split("//"); node=doc
    for i,s in enumerate(segs):
        if "$" in s:
            rx=seg_rx(s)
            if not isinstance(node,dict): return (i,"not a dict before '%s'"%s)
            cand=[k for k in node if re.fullmatch(rx,k)]
            if not cand: return (i,"no key matches '%s'"%s)
            node=node[cand[0]]
        else:
            if isinstance(node,dict) and s in node: node=node[s]
            else: return (i,"missing key '%s'"%s)
    return (len(segs),"full path exists",)
groups=collections.defaultdict(list)
for k,v in oc["outcomes"].items():
    if v["matches"]: continue
    i=int(k); root=v["yang_key"].split("//")[0]
    if root not in doc:
        reason="ROOT '%s' not in document (dead spine group)"%root
        groups[(root,None)].append(i)
    else:
        d=dead_reason(v["yang_key"])
        groups[(root,d[1])].append(i)
for (root,reason),idxs  in sorted(groups.items()):
    print(f"{root}: {len(idxs)} rows {idxs[0]}..{idxs[-1]} :: {reason}")
