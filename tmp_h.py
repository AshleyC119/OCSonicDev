import json
d=json.loads(open('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt',encoding='utf-8-sig').read())
iface=d['interfaces']['interface']
for k in ['Eth200GE1','Bridge-Aggregation1','Vlan2','Loopback0','eth0','BMC']:
    print('---',k)
    print(json.dumps(iface[k],indent=1)[:1800])
