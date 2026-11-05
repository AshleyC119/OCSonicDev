import csv, io, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
def shape(x):
    if isinstance(x,list):
        if not x: return "[]"
        return "["+",".join(sorted(set(shape(y) for y in x)))+"]"
    return "s"
for i,r in enumerate(rows):
    v=ast.literal_eval(r['sonic_value'])
    if shape(v)!='[[s]]':
        print(f"[{i}] YK={r['yang_key']}")
        print(f"     YV={r['yang_value']}")
        print(f"     SV={r['sonic_value']}")
