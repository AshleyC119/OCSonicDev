import json
d=json.loads(open('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt',encoding='utf-8-sig').read())
q=d['qos']
print('qos keys',list(q))
print('--- interfaces sample')
k=list(q['interfaces']['interface'])[0]
print(json.dumps(q['interfaces']['interface'][k],indent=1)[:2500])
print('--- global', json.dumps(q['global'],indent=1)[:1200])
print('--- int root'); print(json.dumps(d['int']['interfaces']['interface'][list(d['int']['interfaces']['interface'])[0]],indent=1)[:800])
print('--- lacp iface'); print(json.dumps(d['lacp']['interfaces']['interface'][list(d['lacp']['interfaces']['interface'])[0]],indent=1)[:600])
print('--- lldp iface'); print(json.dumps(d['lldp']['interfaces']['interface'][list(d['lldp']['interfaces']['interface'])[0]],indent=1)[:400])
