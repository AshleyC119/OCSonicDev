import json
d=json.loads(open('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt',encoding='utf-8-sig').read())
a=d['acl']['acl-sets']['acl-set']
print('acl-set keys:',list(a))
for k in a:
    v=dict(a[k]); v.pop('acl-entries',None)
    print('---',k); print(json.dumps(v,indent=1))
print('=== acl interfaces'); print(json.dumps(d['acl']['interfaces'],indent=1)[:1500])
print('=== system logging'); print(json.dumps(d['system']['logging'],indent=1)[:1500])
print('=== system dns'); print(json.dumps(d['system']['dns'],indent=1)[:800])
