import csv, io, collections, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
# distinct "scalar directives" in yang_value
tok=collections.Counter()
for r in rows:
    try: v=ast.literal_eval(r['yang_value'])
    except Exception as e: print('BODYV', r['yang_value']); continue
    s=str(v)
    tok[s]+=1
print("distinct yang_value literal shapes:", len(tok))
for k,v in tok.most_common(40): print(v,k[:160])
print("----- sonic_value shapes")
tok2=collections.Counter()
for r in rows:
    try: v=ast.literal_eval(r['sonic_value'])
    except Exception as e: print('BODYSV', r['sonic_value']); continue
    tok2[str(v)]+=1
print("distinct:", len(tok2))
for k,v in tok2.most_common(40): print(v,k[:200])
