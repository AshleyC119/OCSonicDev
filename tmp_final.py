import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
print('tables',len(out),'keys',sum(len(v) for v in out.values()))
print('fields',sum(len(f) if isinstance(f,dict) else 0 for v in out.values() for f in v.values()))
