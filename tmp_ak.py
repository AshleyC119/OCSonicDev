import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
for t in ['BMC','MGMT_INTERFACE','LOOPBACK','LOOPBACK_INTERFACE','VLAN','VLAN_INTERFACE']:
    print('==',t); print(json.dumps(out[t],indent=1,ensure_ascii=False)[:1200])
print('== PORT Eth400GE27'); print(json.dumps(out['PORT']['Eth400GE27'],indent=1,ensure_ascii=False))
print('== PORT Eth200GE1'); print(json.dumps(out['PORT']['Eth200GE1'],indent=1,ensure_ascii=False))
print('== PORTCHANNEL1'); print(json.dumps(out['PORTCHANNEL']['PortChannel1'],indent=1,ensure_ascii=False))
