import csv, io, re
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
import ast
seen=set()
for i,r in enumerate(rows):
    sk=r['sonic_key']
    try:
        v=ast.literal_eval(sk); parts = v if isinstance(v,list) else [v]
    except Exception:
        parts=[sk]
    for t in parts:
        if not isinstance(t,str): continue
        for seg in t.split('//'):
            if seg.isupper() and '$' not in seg and seg not in seen:
                seen.add(seg); print(f"[{i}] bare-uppercase key segment {seg!r} in {t}")
