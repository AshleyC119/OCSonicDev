import csv, io, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
def sk(r):
    s=r['sonic_key']
    try:
        v=ast.literal_eval(s); return v
    except Exception: return s
for i in [0,2,6,12,23,49,58,60,61,62,64,71,88,96,98,102,121,137,138,144,150,154,157,187]:
    r=rows[i]
    print(f"[{i}] YK={r['yang_key']}")
    print(f"     YV={r['yang_value']}")
    print(f"     SK={sk(r)!r}  (type {type(sk(r)).__name__}, len {len(sk(r)) if isinstance(sk(r),list) else 1})")
    print(f"     SV={r['sonic_value']}")
    print()
