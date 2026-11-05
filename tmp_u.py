import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
for t in ['ACL_TABLE','ACL_RULE','PORT','PORTCHANNEL','VLAN','VLAN_MEMBER','VLAN_INTERFACE','LOOPBACK_INTERFACE','MGMT_INTERFACE','DEVICE_METADATA','BGP_PEER_RANGE','BGP_NEIGHBOR_IPV4','BGP_COMMS','BGP_ROUTEMAPS']:
    if t not in out: continue
    print('='*10,t)
    s=json.dumps(out[t],indent=1,ensure_ascii=False)
    print(s[:1800])
