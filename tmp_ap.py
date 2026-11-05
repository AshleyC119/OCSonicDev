import csv, io, json
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i in range(344,360):
    r=rows[i]
    print(f"[{i}] YK={r['yang_key']}\n   YV={r['yang_value']}\n   SK={r['sonic_key']}\n   SV={r['sonic_value']}")
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
print('DNS:',json.dumps(out['DNS'],ensure_ascii=False))
for l in open('outputs/translate_details.txt',encoding='utf-8'):
    if l.startswith('DNS'): print(l.strip())
