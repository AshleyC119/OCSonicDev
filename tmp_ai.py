import sys, collections
sys.path.insert(0,'.')
from translator.rules import load_rules
from translator.ocdoc import OcDocument
from translator.engine import Translator
rules=load_rules('references/raw/yang2sonic_maptable(1).csv')
doc=OcDocument.load('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt')
t=Translator(rules,doc); t.translate()
c=collections.Counter(); ex={}
for p in t.report.unmatched_leaves:
    segs=p.split('//')
    # canonicalise numeric ids and ip-like keys
    tail='//'.join(segs[-2:])
    c[tail]+=1; ex.setdefault(tail,p)
for tail,n in c.most_common(45): print(f"{n:5d} {tail:45s} e.g. {ex[tail][:110]}")
