import sys, collections
sys.path.insert(0,'.')
from translator.rules import load_rules
from translator.ocdoc import OcDocument
from translator.engine import Translator
rules=load_rules('references/raw/yang2sonic_maptable(1).csv')
doc=OcDocument.load('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt')
t=Translator(rules,doc); t.translate()
unmatched=t.report.unmatched_leaves
# try case-insensitive exact
import re
def ci_match(rule, segs):
    if len(segs)!=len(rule.segments): return False
    for p,s in zip(rule.segments,segs):
        rx=re.compile(p.regex.pattern.replace('.*','.*'),re.DOTALL|re.IGNORECASE)
        if rx.fullmatch(s) is None: return False
    return True
hits=collections.Counter()
examples={}
for path in unmatched:
    segs=path.split('//')
    for r in rules:
        if ci_match(r,segs):
            hits[r.index]+=1
            examples.setdefault(r.index,path)
print('case-insensitive additional matches:',sum(hits.values()),'rules:',len(hits))
for i,c in hits.most_common(10): print(i,c,examples[i])
