import json
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
print(json.dumps(doc["acl"]["acl-sets"], indent=1)[:1200])
