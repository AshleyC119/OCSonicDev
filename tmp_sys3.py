import json
p = r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
doc = json.load(open(p, encoding="utf-8-sig"))
print("roots:", list(doc.keys()))
print()
for k,v in doc.items():
    if isinstance(v, dict):
        print(f"{k}: dict keys({len(v)}) = {list(v.keys())[:8]}")
    else:
        print(f"{k}: {type(v).__name__} = {repr(v)[:100]}")
