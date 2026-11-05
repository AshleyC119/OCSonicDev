import csv
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
for i in range(60,70):
    r=rows[i]; print(i, "|", r["yang_key"]); print("     yv=",r["yang_value"],"| sk=",r["sonic_key"],"| sv=",r["sonic_value"])
print()
for i in range(608,620):
    r=rows[i]; print(i, "|", r["yang_key"]); print("     yv=",r["yang_value"],"| sk=",r["sonic_key"],"| sv=",r["sonic_value"])
print()
for tok in ["services","SNMP"]:
    print("=== sonics containing",tok)
    for i,r in enumerate(rows):
        if tok in r["sonic_value"]: print("  ",i,r["spine"],"|",r["sonic_key"],"|",r["sonic_value"])
