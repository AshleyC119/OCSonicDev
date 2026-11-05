import csv, io
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i,r in enumerate(rows):
    if "'NONE'" in r['yang_value'] or "'NONE'" in r['sonic_value']:
        print(f"[{i}] YK: {r['yang_key']}\n    YV: {r['yang_value']}\n    SK: {r['sonic_key']}\n    SV: {r['sonic_value']}\n")
