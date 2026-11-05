import csv, json, re, collections
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
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
pats=[(r["yang_key"].split("//"), [seg_rx(s) for s in r["yang_key"].split("//")]) for r in rows]
covered=set()
for path,val in leaves:
    for segs,rxs in pats:
        if len(path)!=len(segs): continue
        if all(re.fullmatch(rx,p) for rx,p in zip(rxs,path)):
            covered.add(path); break
mine = [ (p,v) for p,v in leaves if p and p[0] in ("system","components","YANG_VALIDATION") ]
unc = [(p,v) for p,v in mine if p not in covered]
print("my-area leaves:", len(mine), "covered:", len(mine)-len(unc), "uncovered:", len(unc))
cnt = collections.Counter()
for p,v in unc:
    cnt[p[0]+"/"+ (p[1] if len(p)>1 else "")] += 1
print("\nuncovered by 2nd-level:")
for k,v in cnt.most_common(): print(f"  {k}: {v}")
print("\nuncovered CONFIG leaves (path contains /config/ or ends config) excluding trivial name/address:")
seen=set()
for p,v in unc:
    if "config" in p:
        key="/".join(p[:3])
        if key in seen: continue
        seen.add(key)
        print("  ", "/".join(p), "=>", json.dumps(v)[:60])
