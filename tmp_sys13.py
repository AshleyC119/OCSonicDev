import csv
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
for d in ["list_combination","combination']","string_combination","list_value","list_2_string"]:
    print("#### directive",d)
    for i,r in enumerate(rows):
        if d in r["yang_value"]:
            print(i, r["spine"], "| yk=", r["yang_key"])
            print("     yv=", r["yang_value"], "| sk=", r["sonic_key"], "| sv=", r["sonic_value"])
