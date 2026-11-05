import csv, io, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
def pl(t):
    try: return ast.literal_eval(t)
    except Exception: return None
print("multi-SK rows: check sv wrapping")
bad=[]
for i,r in enumerate(rows):
    sk=pl(r['sonic_key']); sk=sk if isinstance(sk,list) else [sk]
    sv=pl(r['sonic_value']); sv=sv if isinstance(sv,list) else [sv]
    if len(sk)>1:
        wrapped=all(isinstance(e,list) and len(e)==1 and isinstance(e[0],list) for e in sv)
        if not wrapped: bad.append((i,len(sk),r['sonic_value']))
print("multi-SK rows:",sum(1 for r in rows if isinstance(pl(r['sonic_key']),list)),"not wrapped:",bad[:10])
print("single-SK rows with inner-list candidate entries:")
cnt=0
for i,r in enumerate(rows):
    sk=pl(r['sonic_key']); sk=sk if isinstance(sk,list) else [sk]
    if len(sk)!=1: continue
    sv=pl(r['sonic_value']); sv=sv if isinstance(sv,list) else [sv]
    e=sv[0]
    if isinstance(e,list) and len(e)==1 and isinstance(e[0],list):
        cnt+=1
        if cnt<15: print(' ',i,e)
print("count:",cnt)
