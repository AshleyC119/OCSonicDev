import sys; sys.path.insert(0,'.')
from translator.rules import load_rules
from translator.ocdoc import OcDocument
rules=load_rules('references/raw/yang2sonic_maptable(1).csv')
doc=OcDocument.load('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt')
leaf=doc.get(('interfaces','interface','BMC','bmc','config','gateway-ip'))
print('leaf:',leaf)
r=rules[68]; print('rule68 pattern:',[s.raw for s in r.segments]); print('match:',r.match(leaf.segments) if leaf else None)
print('selectors:',[(s.kind,s.value) for s in r.selectors],'sv',r.sv_entries,'sk',r.sk_templates)
# which rules match the leaf?
for rule in rules:
    if leaf and rule.match(leaf.segments): print(' matched rule',rule.index,rule.yang_key[:80],rule.specificity)
