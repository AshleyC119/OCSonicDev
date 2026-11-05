import csv, io, json, collections
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
print("rows:",len(rows))
c=collections.Counter(r['spine'] for r in rows)
for k,v in c.most_common(): print(f"{v:5d}  {k}")
