import csv, io, ast, collections
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
print(repr(rows[58]['sonic_value']))
print(repr(rows[0]['sonic_value']))
# depth analysis: shape signature
def shape(x):
    if isinstance(x,list):
        if not x: return "[]"
        inner = sorted(set(shape(y) for y in x))
        return "["+",".join(inner)+"]"
    return "s"
sig=collections.Counter()
examples={}
for i,r in enumerate(rows):
    v=ast.literal_eval(r['sonic_value'])
    s=shape(v)
    sig[s]+=1
    examples.setdefault(s,i)
for s,c in sig.most_common():
    print(f"{c:4d}  {s}   e.g. row {examples[s]}: {rows[examples[s]]['sonic_value']}")
