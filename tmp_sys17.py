import csv, json, re
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
# any rule starting with placeholder or non-root path?
for i,r in enumerate(rows):
    first = r["yang_key"].split("//")[0]
    if "$" in first: print("wildcard root:", i, r["yang_key"])
print("done root check")
def flatten(node, path, out):
    if isinstance(node, dict):
        if not node: out.append((tuple(path), {}))
        for k,v in node.items(): flatten(v, path+[str(k)], out)
    elif isinstance(node, list): out.append((tuple(path), node))
    else: out.append((tuple(path), node))
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
leaves=[]; flatten(doc, [], leaves)
def seg_rx(seg):
    parts = re.split(r'(\$[^$]+\$)', seg); rx="^"
    for p in parts:
        if p.startswith("$") and p.endswith("$") and len(p)>2: rx+="(.+?)"
        elif p: rx+=re.escape(p)
    return rx+"$"
def lits(pattern): return sum(len(re.sub(r'\$[^$]+\$','',s)) for s in pattern.split("//"))
compiled=[(i,r["yang_key"].split("//"),[seg_rx(s) for s in r["yang_key"].split("//")],lits(r["yang_key"])) for i,r in enumerate(rows)]
# For leaves in my areas, list all candidate rules
mine_prefixes = ("system","components","YANG_VALIDATION")
conflicts=[]
for path,val in leaves:
    if not path or path[0] not in mine_prefixes: continue
    cands=[]
    for i,segs,rxs,li in compiled:
        if len(path)!=len(segs): continue
        if all(re.fullmatch(rx,p) for rx,p in zip(rxs,path)):
            cands.append(i)
    if len(cands)>1:
        # check specificity ties
        best=max(lits(rows[i]["yang_key"]) for i in cands)
        top=[i for i in cands if lits(rows[i]["yang_key"])==best]
        if len(top)>1: conflicts.append(("/".join(path), cands, top))
print("leaves with MULTIPLE candidate rules:", len(conflicts))
for c in conflicts[:40]: print(c)
