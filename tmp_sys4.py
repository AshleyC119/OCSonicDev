import json
p = r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
doc = json.load(open(p, encoding="utf-8-sig"))
print("system keys:", list(doc["system"].keys()))
for k,v in doc["system"].items():
    print(f"  system/{k}: {json.dumps(v)[:600]}")
print()
print("components:", json.dumps(doc["components"])[:3000])
