import csv
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
for pat in ["stp","bfd","default//","//default//","default"]:
    hits=[(i,r["spine"],r["yang_key"]) for i,r in enumerate(rows) if pat in r["yang_key"] or pat in r["spine"]]
    print("=== pattern",repr(pat),"hits:",len(hits))
    for h in hits[:15]: print("  ",h)
print()
# which spines' yang_key root is not one of the 15 OC roots
import json
doc=json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt",encoding="utf-8-sig"))
roots=set(doc.keys())
from collections import Counter, defaultdict
c=Counter(); dead=defaultdict(list)
for i,r in enumerate(rows):
    root=r["yang_key"].split("//")[0]
    c[root]+=1
    if root not in roots: dead[root].append(i)
for k,v in c.items(): print(f"root {k!r}: {v} rows {'DEAD' if k not in roots else 'OK'}")
print()
print("dead roots:", {k:(len(v),v[:3],v[-3:]) for k,v in dead.items()})
