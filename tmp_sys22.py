import re, csv
rows = list(csv.DictReader(open(r"references/raw/yang2sonic_maptable(1).csv", encoding="utf-8-sig")))
def segs(k): return k.split("//")
def lit_segments(k):
    # count segments with no placeholder at all
    return sum(1 for s in segs(k) if "$" not in s)
def any_literal_segments(k):
    return sum(1 for s in segs(k) if re.sub(r'\$[^$]+\$','',s))
def lit_chars(k):
    return sum(len(re.sub(r'\$[^$]+\$','',s)) for s in segs(k))
for pair in [(187,193),(188,194),(189,195)]:
    a,b=pair
    print(pair)
    for i in pair:
        k=rows[i]["yang_key"]
        print(f"  row {i}: lit_segments={lit_segments(k)} any_literal={any_literal_segments(k)} lit_chars={lit_chars(k)}")
