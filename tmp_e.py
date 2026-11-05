import csv, io, collections, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
SPECIAL={'ockey','compute','combination','list_combination','string_combination','list_value','list_2_string','empty_dict','NONE','any','ockey_default','lowercase','original','value','[+value+]'}
def specials(s):
    out=set()
    try: v=ast.literal_eval(s)
    except: return {'PARSE'}
    def walk(x):
        if isinstance(x,list):
            for y in x: walk(y)
        elif isinstance(x,str):
            for t in ['ockey','compute','combination','list_combination','string_combination','list_value','list_2_string','empty_dict','NONE','any','ockey_default','lowercase','original','value','ADDRESS','INTERFACE','GROUP','NEIGHBOR','PortChannel','uplink','downlink','AREA','tagged','untagged','add','empty_dict']:
                if t in x: out.add(t)
    walk(v); return out
cnt=collections.Counter()
for r in rows:
    sp = specials(r['yang_value'])|specials(r['sonic_value'])
    cnt[frozenset(sp)]+=1
for k,v in cnt.most_common(30): print(v, sorted(k))
