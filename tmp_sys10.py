import json, csv
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
ifaces = doc["system"]["monitor-link"]["groups"]["group"]["1"]["interfaces"]["interface"]
print(json.dumps(ifaces["Eth400GE27"], indent=1))
print(json.dumps(ifaces["Bridge-Aggregation13"], indent=1))
print()
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
for tok in ["linkmode","updelaytime","//groupid","PACKET_ACTION","//option"]:
    print("=== sonic tokens",tok)
    for i,r in enumerate(rows):
        if tok in r["sonic_key"]: print("  ",i,r["spine"],"|",r["sonic_key"],"|",r["yang_key"][:90])
