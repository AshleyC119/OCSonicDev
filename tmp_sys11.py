import json
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
sysd = doc["system"]
for key in ["aaa","config","arp","nd","grpc","hash","logging","ntp","snmp","counter","dns","sampling"]:
    print("=====", key)
    print(json.dumps(sysd[key], indent=1)[:2500])
    print()
