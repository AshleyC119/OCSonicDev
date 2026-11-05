import csv, io
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i,r in enumerate(rows):
    if 'list_value' in r['yang_value'] or 'list_2_string' in r['yang_value'] or 'string_combination' in r['yang_value'] or 'lowercase' in r['yang_value'] or 'combination' == r['yang_value'][3:-3]:
        print(f"[{i}] {r['yang_key']}\n   YV={r['yang_value']}\n   SK={r['sonic_key']}\n   SV={r['sonic_value']}")
