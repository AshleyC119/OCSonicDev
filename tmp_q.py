import csv, io, ast, collections
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
def pl(t):
    try: return ast.literal_eval(t)
    except Exception: return t
bad=0
for i,r in enumerate(rows):
    sk=pl(r['sonic_key']); sk=sk if isinstance(sk,list) else [sk]
    yv=pl(r['yang_value']); yv=yv if isinstance(yv,list) else [yv]
    sv=pl(r['sonic_value']); sv=sv if isinstance(sv,list) else [sv]
    if not(len(sk)==len(yv)==len(sv)):
        bad+=1
        print(f"[{i}] len sk={len(sk)} yv={len(yv)} sv={len(sv)}")
        print('   YK',r['yang_key']); print('   YV',r['yang_value'],' SV',r['sonic_value'],' SK',r['sonic_key'])
print('mismatches:',bad,'of',len(rows))
