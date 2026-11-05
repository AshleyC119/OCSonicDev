import json
out=json.load(open('outputs/CQ-JLDC-2203-D05-TCS84R-LA200G-019.sonic.json',encoding='utf-8'))
print(len(out),'tables',sum(len(v) for v in out.values()),'keys')
rep=json.load(open('outputs/translate_report.json',encoding='utf-8'))
print('warnings:',rep['warnings'])
