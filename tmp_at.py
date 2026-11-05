import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
print('BMC:',json.dumps(out['BMC'],ensure_ascii=False))
print('DNS:',json.dumps(out['DNS'],ensure_ascii=False))
