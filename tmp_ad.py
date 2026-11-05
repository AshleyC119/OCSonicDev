import json, sys, collections
sys.path.insert(0,'.')
from translator.rules import load_rules
from translator.ocdoc import OcDocument
from translator.engine import Translator
rules=load_rules('references/raw/yang2sonic_maptable(1).csv')
doc=OcDocument.load('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt')
t=Translator(rules,doc); t.translate()
fired=t.report.rule_fires
roots=set()
for leaf in doc.leaves: roots.add(leaf.segments[0])
print('doc roots:',sorted(roots))
buckets=collections.defaultdict(list)
for r in rules:
    if r.index in fired: continue
    yk=r.yang_key
    seg=yk.split('//')
    # root present in doc?
    root=seg[0]
    key='root-absent' if root not in roots else 'root-present'
    buckets[(root,key)].append(r)
for (root,key),rs in sorted(buckets.items()):
    print(f"{len(rs):4d}  {root:28s} {key}   e.g. {rs[0].yang_key[:110]}")
