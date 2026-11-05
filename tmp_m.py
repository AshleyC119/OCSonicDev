import csv, io, ast, re, collections
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
tok=collections.Counter()
for i,r in enumerate(rows):
    try: sv=ast.literal_eval(r['sonic_value'])
    except Exception: continue
    def walk(x):
        if isinstance(x,list):
            for y in x: walk(y)
        elif isinstance(x,str):
            tok[x]+=1
    walk(sv)
print("--- all distinct sonic_value item strings (%d):"%len(tok))
for k,v in sorted(tok.items()): print(f"{v:4d}  {k!r}")
