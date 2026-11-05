import csv, json
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
print("rows with 'factors' in yang_key:")
for i,r in enumerate(rows):
    if "factors" in r["yang_key"]: print(i, r["spine"], "|", r["yang_key"], "|", r["yang_value"], "|", r["sonic_key"], "|", r["sonic_value"])
print()
print("roots check stp/bfd/default:")
for target in ["stp","bfd","default"]:
    hits=[i for i,r in enumerate(rows) if r["yang_key"].split("//")[0]==target]
    print(target, len(hits))
print()
print("rows mentioning list_value / list_2_string / string_combination anywhere in my range:")
for i,r in enumerate(rows):
    if any(d in (r["yang_value"]+r["sonic_value"]) for d in ["list_value","list_2_string","string_combination"]):
        print(i, r["spine"], "|", r["yang_value"], "|", r["sonic_key"], "|", r["sonic_value"])
