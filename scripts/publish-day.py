#!/usr/bin/env python3
"""6:30 publisher: merge local 6:00 section files + Codex IQ, then push the site."""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_URL = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-site-url').read_text().strip()
TOKEN = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-update-token').read_text().strip()
DATA = Path('/workspace/daily-briefing-site/data')
TZ = ZoneInfo('Asia/Singapore')
UA = {'User-Agent': 'NeumaBriefing/1.0', 'Accept': 'application/json'}
# Stable tab order: AI / 40+ women / pharma / Codex IQ, then Ezreal explore.
ORDER = ['ai', 'women40', 'pharma', 'codexiq', 'explore']
TITLES = {
    'ai': 'AI / LLM 热点',
    'women40': '40+ 女性热点',
    'pharma': '健康医药产业',
    'codexiq': 'Codex IQ 雷达',
    'explore': '探险 / 好玩的',
}

def today():
    return datetime.now(TZ).strftime('%Y-%m-%d')

def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

def empty_section(sid):
    return {'id': sid, 'title': TITLES[sid], 'summary': '', 'items': []}

def empty_day(date):
    return {
        'date': date,
        'updatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'sections': [empty_section(i) for i in ORDER],
    }

def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))

def section_from_blob(blob, sid):
    if not blob:
        return None
    if isinstance(blob, dict) and blob.get('id') == sid:
        return blob
    if isinstance(blob, dict) and isinstance(blob.get('section'), dict):
        return blob['section']
    if isinstance(blob, dict) and isinstance(blob.get('sections'), list):
        for s in blob['sections']:
            if s.get('id') == sid:
                return s
    return None

def richer(a, b):
    """Keep the section with more items; ties keep the later one if it has a summary."""
    if not a:
        return b
    if not b:
        return a
    na = len(a.get('items') or [])
    nb = len(b.get('items') or [])
    if nb > na:
        return b
    if nb < na:
        return a
    if (b.get('summary') or '') and not (a.get('summary') or ''):
        return b
    return b if (b.get('summary') or a.get('summary')) else a

def merge_sections(*days_or_sections):
    by = {}
    for obj in days_or_sections:
        if not obj:
            continue
        if isinstance(obj, dict) and obj.get('id'):
            by[obj['id']] = richer(by.get(obj['id']), obj)
            continue
        for s in (obj.get('sections') or []):
            if s.get('id'):
                by[s['id']] = richer(by.get(s['id']), s)
    ordered = [by[i] if i in by else empty_section(i) for i in ORDER]
    for sid, s in by.items():
        if sid not in ORDER:
            ordered.append(s)
    return ordered

def push(day):
    data = json.dumps(day, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f'{SITE_URL}/api/update',
        data=data,
        headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()

def main():
    date = today()
    day_path = DATA / f'{date}.json'
    day = load_json(day_path) or empty_day(date)
    if day.get('date') != date:
        day = empty_day(date)

    extras = []
    for sid in ('ai', 'pharma', 'women40', 'codexiq', 'explore'):
        extras.append(section_from_blob(load_json(DATA / f'{date}.{sid}.json'), sid))

    # workspace copies written by 6:00 routines
    extras.append(section_from_blob(load_json(Path(f'/workspace/AI-LLM-热点简报-{date}.json')), 'ai'))
    extras.append(section_from_blob(load_json(Path(f'/workspace/健康医药产业热点简报-{date}.json')), 'pharma'))
    extras.append(section_from_blob(load_json(Path(f'/workspace/40+女性营养健康生活-新闻社媒热点-{date}.json')), 'women40'))

    day['sections'] = merge_sections(day, *extras)
    day['date'] = date
    day['updatedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

    DATA.mkdir(parents=True, exist_ok=True)
    day_path.write_text(json.dumps(day, ensure_ascii=False, indent=2), encoding='utf-8')

    # Codex IQ: reuse fetch script which merges + pushes
    import subprocess
    print(subprocess.check_output(['python3', '/workspace/daily-briefing-site/scripts/fetch-codex-iq.py'], text=True))

    # fetch-codex-iq writes Codex IQ; keep today's 6:00 sidecars for the other three tabs.
    # Never merge /api/latest if it is a different date (richer() would keep yesterday's longer lists).
    after = load_json(day_path) or day
    live = None
    try:
        live = get_json(f'{SITE_URL}/api/latest')
    except Exception:
        pass
    if live and live.get('date') != date:
        live = None
    codex = None
    for blob in (after, live):
        if not blob:
            continue
        for s in (blob.get('sections') or []):
            if s.get('id') == 'codexiq' and (s.get('items') or []):
                codex = s
    day['sections'] = merge_sections(day, *extras, codex)
    day['date'] = date
    day['updatedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    day_path.write_text(json.dumps(day, ensure_ascii=False, indent=2), encoding='utf-8')
    print(push(day))
    counts = [(s['id'], len(s.get('items') or [])) for s in day['sections']]
    print('published', date, counts)

if __name__ == '__main__':
    main()
