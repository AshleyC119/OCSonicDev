import sys; sys.path.insert(0,'tools')
from audit_diff import load
from pathlib import Path
exp=load(Path('audit/system.expected.txt')); eng=load(Path('outputs/translate_details.txt'))
print([e for e in exp if e not in eng])
