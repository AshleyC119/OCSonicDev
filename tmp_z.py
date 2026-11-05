import csv, io
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i,r in enumerate(rows):
    if 'STATIC' in r['yang_key'] or ('network-instance//mgt_vrf' in r['yang_key']) or 'MGMT_VRF' in r['sonic_key']:
        print(f"[{i}] YK={r['yang_key']}\n   YV={r['yang_value']}\n   SK={r['sonic_key']}\n   SV={r['sonic_value']}")
