import json, io
p='data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt'
d=json.loads(open(p,encoding='utf-8-sig').read())
def walk(o, path='', depth=0):
    if depth>3: return
    if isinstance(o, dict):
        for k,v in o.items():
            print('  '*depth + f'{k}  <{type(v).__name__}>' + (f' len={len(v)}' if isinstance(v,(list,dict)) else f' = {v!r}'))
            walk(v, path+'/'+k, depth+1)
    elif isinstance(o, list):
        print('  '*depth + f'[list len={len(o)}] sample={str(o[:1])[:200]}')
walk(d)
