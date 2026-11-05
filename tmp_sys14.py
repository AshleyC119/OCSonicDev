import csv, re, ast
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
print("=== sonic_values containing [ or ] inside a string literal")
for i,r in enumerate(rows):
    try: sv = ast.literal_eval(r["sonic_value"])
    except Exception: sv = r["sonic_value"]
    s = repr(sv)
    if "[" in r["sonic_value"]:
        # find inner brackets within string literals
        strs = re.findall(r"'([^']*)'", r["sonic_value"])
        inner = [x for x in strs if "[" in x or "]" in x]
        if inner:
            print(i, r["spine"], "| sv=", r["sonic_value"], "| inner:", inner)
print()
print("=== empty_dict rows")
for i,r in enumerate(rows):
    if "empty_dict" in r["yang_value"] or "empty_dict" in r["sonic_value"]:
        print(i, r["spine"], "| yk=", r["yang_key"], "| yv=", r["yang_value"], "| sk=", r["sonic_key"], "| sv=", r["sonic_value"])
