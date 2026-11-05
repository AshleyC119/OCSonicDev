import csv, io
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i,r in enumerate(rows):
    for col in ('sonic_key','yang_key','sonic_value','yang_value'):
        if '{|' in r[col] or 'ockey=' in r[col]:
            print(f"[{i}] {col}: {r[col]}")
            print(f"     YK={r['yang_key']}\n     YV={r['yang_value']}\n     SK={r['sonic_key']}\n     SV={r['sonic_value']}")
