#!/usr/bin/env python3
"""Push a day JSON file to the daily briefing site."""
import json, sys, urllib.request
from pathlib import Path

SITE = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-site-url').read_text().strip()
TOKEN = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-update-token').read_text().strip()
path = Path(sys.argv[1])
data = path.read_bytes()
json.loads(data)
req = urllib.request.Request(
    f'{SITE}/api/update',
    data=data,
    headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=60) as r:
    print(r.read().decode())
