"""Verify supplied bytes and formats without changing the raw materials."""
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'data/manifest.json').read_text(encoding='utf-8'))
records = manifest['files']
if len(records) != 2 or {x['side'] for x in records} != {'rules', 'oc'}:
    raise ValueError('Expected one rules CSV and one OC document')
for item in records:
    path = (ROOT / item['path']).resolve()
    if ROOT not in path.parents:
        raise ValueError('Material path outside workspace')
    data = path.read_bytes()
    if len(data) != item['bytes'] or sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Material identity mismatch: ' + item['path'])
    if item['side'] == 'rules':
        rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        if len(rows) != item['data_rows'] or list(rows[0]) != item['columns']:
            raise ValueError('Rules CSV structure mismatch')
    else:
        document = json.loads(data.decode('utf-8-sig'))
        if not isinstance(document, dict) or len(document) != item['root_count']:
            raise ValueError('JSON root structure mismatch: ' + item['path'])
print('Verified: rules CSV and OC document; both original hashes match.')
