import json, sys, collections
sys.path.insert(0,'.')
from translator.rules import load_rules
from translator.ocdoc import OcDocument
from translator.engine import Translator
rules=load_rules('references/raw/yang2sonic_maptable(1).csv')
doc=OcDocument.load('data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt')
t=Translator(rules,doc); t.translate()
fired=t.report.rule_fires
for root in ['interfaces','system','qos','components','acl','routing-policy','lacp','int']:
    print('='*20,root)
    for r in rules:
        if r.index in fired: continue
        if not r.yang_key.startswith(root+'//'): continue
        if root=='network-instances': continue
        print(f"[{r.index}] {r.yang_key}")
        print(f"      YV={r.yang_value}  SK={r.sonic_key}")
