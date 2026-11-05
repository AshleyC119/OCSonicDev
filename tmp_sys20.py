import json
doc = json.load(open(r"data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt", encoding="utf-8-sig"))
def walk(node, path, out):
    if isinstance(node, dict):
        for k,v in node.items(): walk(v, path+[str(k)], out)
    elif isinstance(node, list):
        out.append(("/".join(path), node))
walk(doc, [], [])
