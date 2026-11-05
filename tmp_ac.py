import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
for t in ['ACL_TABLE','BGP_COMMS','QUEUE']:
    v=out[t]; print('==',t,len(v)); print(json.dumps(dict(list(v.items())[:4]),indent=1,ensure_ascii=False)[:900])
rep=json.load(open('outputs/translate_report.json',encoding='utf-8'))
print('warnings',len(rep['warnings']))
for w in rep['warnings'][:20]: print(' ',w)
