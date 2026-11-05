import json, collections
rep=json.load(open('outputs/translate_report.json',encoding='utf-8'))
for pref in ['components//component','qos//interfaces//interface//Eth400GE27','qos//scheduler-policies','acl//acl-sets','system//monitor-link','network-instances//network-instance//global//protocols','routing-policy//policy-definitions','system//sampling']:
    print('='*20,pref)
    n=0
    for p in rep['unmatched_leaves']:
        if p.startswith(pref):
            print(' ',p); n+=1
            if n>=22: break
