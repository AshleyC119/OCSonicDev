import sys
sys.path.insert(0,'tools')
from audit_diff import load
from pathlib import Path
exp=load(Path('audit/system.expected.txt'))
eng=load(Path('outputs/translate_details.txt'))
bp=[e for e in exp if e[0]=='BUFFER_PROFILE']
print('expected BUFFER_PROFILE lines:',len(bp))
missing=[e for e in bp if e not in eng]
print('missing:',len(missing))
print('sample exp:',bp[0])
print('present in engine?', bp[0] in eng)
