import csv, ast, json, collections, io
p = r"references/raw/yang2sonic_maptable(1).csv"
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
print("data rows:", len(rows))
sp = collections.Counter(r["spine"] for r in rows)
for k,v in sp.items(): print(repr(k), v)
