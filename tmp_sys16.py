import csv
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
for tok in ["DSCP_TO_TC_MAP","TC_TO_QUEUE_MAP","SCHEDULER","WRED_PROFILE","EBST_PROFILE","BUFFER_PROFILE","BUFFER_POOL"]:
    print("=== rows defining/touching", tok)
    for i,r in enumerate(rows):
        if tok in r["sonic_key"]:
            print("  ",i,r["spine"],"|",r["sonic_key"],"|",r["sonic_value"])
