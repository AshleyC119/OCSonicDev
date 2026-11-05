import csv, io, ast
p='references/raw/yang2sonic_maptable(1).csv'
rows=list(csv.DictReader(io.StringIO(open(p,encoding='utf-8-sig').read())))
for i in [600,601,602,603,604,605,606,607,608,609,610,611,612,613,614,615,616,617,618,619,
          660,661,662,663,664,665,670,671,672,673,674,675,676,677,678,679,680,681,682,690,691,692,693,694,695,696,697,698,699,700,701]:
    r=rows[i]
    print(f"[{i}] YK={r['yang_key']}")
    print(f"     YV={r['yang_value']}")
    print(f"     SK={r['sonic_key']}")
    print(f"     SV={r['sonic_value']}")
