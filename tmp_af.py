import json,collections
lines=open('outputs/translate_details.txt',encoding='utf-8').read().splitlines()
c=collections.Counter()
for l in lines:
    t=l.split('|')[0]
    c[t]+=1
print(dict(c))
print('---- DSCP/TC/QUEUE/SCHEDULER/PORT_QOS')
for l in lines:
    if l.startswith(('DSCP_TO_TC_MAP','TC_TO_QUEUE_MAP','SCHEDULER','PORT_QOS_MAP')):
        print(l)
