import csv, io, json
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i in range(641,670):
    r=rows[i]
    print(f"[{i}] YK={r['yang_key']}\n   YV={r['yang_value']}\n   SK={r['sonic_key']}\n   SV={r['sonic_value']}")
