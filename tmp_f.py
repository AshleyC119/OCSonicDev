import json
d=json.loads(open('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt',encoding='utf-8-sig').read())
print(json.dumps(d['acl'],indent=1)[:4000])
