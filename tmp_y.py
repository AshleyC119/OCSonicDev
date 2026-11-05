import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
for t in ['VLAN','VLAN_MEMBER','VLAN_INTERFACE','LOOPBACK_INTERFACE','BGP_COMMS','BGP_NEIGHBOR_IPV4','QUEUE','PFC_WD_TABLE','DNS','SYSLOG_SERVER','ACL_TABLE','BGP_PEER_RANGE','BGP_GLOBALCONFIG','SCHEDULER','WRED_PROFILE','PFC_WARNING_CONFIG_TABLE','FLEX_COUNTER_TABLE']:
    print('='*8,t)
    v=out.get(t,{})
    items=list(v.items())[:6]
    print(json.dumps(dict(items),indent=1,ensure_ascii=False)[:1500])
    print(' total keys:',len(v))
