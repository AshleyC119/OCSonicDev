import json
d=json.loads(open('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt',encoding='utf-8-sig').read())
ni=d['network-instances']['network-instance']
print('keys:',list(ni))
print(json.dumps(ni['global'],indent=1)[:3000])
print('=== mgt_vrf')
print(json.dumps(ni['mgt_vrf'],indent=1)[:2000])
