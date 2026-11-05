import csv, io, collections, json
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
groups=collections.OrderedDict()
for i,r in enumerate(rows):
    groups.setdefault(r['spine'],[]).append((i,r))
out=open('tmp_dump.txt','w',encoding='utf-8')
for spine,items in groups.items():
    out.write(f"\n===== {spine}  ({len(items)} rows) =====\n")
    for i,r in items:
        out.write(f"[{i}] YK: {r['yang_key']}\n")
        out.write(f"    YV: {r['yang_value']}\n")
        out.write(f"    SK: {r['sonic_key']}\n")
        out.write(f"    SV: {r['sonic_value']}\n")
out.close()
import os; print(os.path.getsize('tmp_dump.txt'))
