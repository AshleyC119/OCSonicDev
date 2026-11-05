import csv, io, collections, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
print("=== distinct yang_value (full)")
seen=collections.Counter(r['yang_value'] for r in rows)
for k,v in seen.most_common(): print(f"{v:4d} {k}")
