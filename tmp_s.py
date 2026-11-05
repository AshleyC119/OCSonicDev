import json, collections
rep=json.load(open('outputs/translate_report.json',encoding='utf-8'))
print(json.dumps(rep['summary'],indent=1))
print('warnings:',len(rep['warnings']))
for w in rep['warnings'][:30]: print(' ',w)
groups=collections.Counter()
for p in rep['unmatched_leaves']:
    segs=p.split('//')
    groups['//'.join(segs[:3])]+=1
print('\n--- unmatched by 3-seg prefix (top 40):')
for k,v in groups.most_common(40): print(f"{v:5d}  {k}")
print('\n--- suppressed:',rep['suppressed_leaves'])
