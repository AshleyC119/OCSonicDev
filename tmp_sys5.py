import json
p = r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt"
doc = json.load(open(p, encoding="utf-8-sig"))
def flat(node, path, out):
    if isinstance(node, dict):
        if not node: out.append(("/".join(path), {}))
        for k,v in node.items(): flat(v, path+[k], out)
    elif isinstance(node, list):
        out.append(("/".join(path), node))
    else:
        out.append(("/".join(path), node))
out=[]
for r in ["stp","lldp","bfd","YANG_VALIDATION","default","components"]:
    flat(doc[r],[r],out)
for pth,val in out:
    print(pth, "=>", json.dumps(val)[:120])
