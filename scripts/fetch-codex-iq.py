#!/usr/bin/env python3
"""Fetch Codex Radar IQ metrics and merge into Neuma day JSON (section id: codexiq)."""
import json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_URL = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-site-url').read_text().strip()
TOKEN = Path('/home/box/sand-data/agents/fb520e9d-5d10-483f-ab42-88fa609421aa/secrets/briefing-update-token').read_text().strip()
TZ = ZoneInfo('Asia/Singapore')
UA = {'User-Agent': 'NeumaBriefing/1.0', 'Accept': 'application/json'}

def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

def today():
    return datetime.now(TZ).strftime('%Y-%m-%d')

def fetch_latest_day():
    try:
        req = urllib.request.Request(f'{SITE_URL}/api/latest', headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def empty_day(date):
    return {
        'date': date,
        'updatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'sections': [
            {'id': 'ai', 'title': 'AI / LLM 热点', 'summary': '', 'items': []},
            {'id': 'women40', 'title': '40+ 女性热点', 'summary': '', 'items': []},
            {'id': 'pharma', 'title': '健康医药产业', 'summary': '', 'items': []},
        ],
    }

def build_section(metrics, insights):
    points = sorted(metrics.get('points') or [], key=lambda p: (-float(p.get('iq') or 0), p.get('model') or '', p.get('effort') or ''))
    updated = metrics.get('source_updated_at') or ''
    # headline: best few
    top = points[:3]
    top_bits = [f"{p['model']} / {p['effort']} IQ {p['iq']}" for p in top]
    summary = 'Codex 雷达 · DeepSWE 智力效率。今日领先：' + ('；'.join(top_bits) if top_bits else '暂无数据')

    items = []
    items.append({
        'title': f"今日 GPT / Codex IQ 概览（DeepSWE）",
        'summary': (
            f"数据更新 {updated}。24h 采样 {metrics.get('runs_24h_total')} 次，"
            f"累计 {metrics.get('runs_total')} 次。评分模式：{metrics.get('mode')}。"
            f"以下按 IQ 从高到低列出主要 model × effort 组合。"
        ),
        'date': today(),
        'sources': [
            {'label': 'Codex 雷达', 'url': 'https://codexradar.com/'},
            {'label': 'GPT IQ Index (镜像)', 'url': 'https://www.hvoy.ai/en/codex-radar/'},
        ],
    })

    # recommendations
    for rec in (insights.get('recommendations') or [])[:4]:
        parts = []
        for it in (rec.get('items') or [])[:3]:
            parts.append(f"{it.get('model')} / {it.get('effort')}（IQ {it.get('iq')}，约 ${it.get('average_cost_usd')} / {it.get('average_duration_minutes')} 分钟）")
        if not parts:
            continue
        items.append({
            'title': f"推荐场景：{rec.get('title')}",
            'summary': '；'.join(parts) + '。' + (rec.get('rule') or ''),
            'date': today(),
            'sources': [{'label': 'Codex 雷达推荐', 'url': 'https://codexradar.com/'}],
        })

    # alerts
    alerts = insights.get('degradation_alerts') or []
    if isinstance(alerts, dict):
        alerts = list(alerts.values()) if alerts else []
    if not isinstance(alerts, list):
        alerts = []
    for alert in alerts[:5]:
        if not isinstance(alert, dict):
            continue
        title = alert.get('title') or alert.get('key') or '能力波动提醒'
        body = alert.get('summary') or alert.get('detail') or json.dumps(alert, ensure_ascii=False)[:400]
        items.append({
            'title': f"波动提醒：{title}",
            'summary': str(body),
            'date': today(),
            'sources': [{'label': 'Codex 雷达', 'url': 'https://codexradar.com/'}],
        })

    # top model rows (skip ultra obscure low IQ)
    for p in points[:14]:
        iq = p.get('iq')
        items.append({
            'title': f"{p.get('model')} · {p.get('effort')} — IQ {iq}",
            'summary': (
                f"通过 {p.get('passed')}/{p.get('total')}（加权 {p.get('weighted_passed')}/{p.get('weighted_total')}）。"
                f"均价约 ${p.get('average_price_usd')}，均时约 {p.get('average_minutes')} 分钟，"
                f"24h 运行 {p.get('runs_24h')} 次。"
            ),
            'date': (p.get('source_updated_at') or updated or today())[:10],
            'sources': [
                {'label': '智力效率', 'url': 'https://codexradar.com/'},
            ],
        })

    return {
        'id': 'codexiq',
        'title': 'Codex IQ 雷达',
        'summary': summary,
        'items': items,
    }

def merge_section(day, section):
    sections = day.get('sections') or []
    out = []
    seen = False
    for s in sections:
        if s.get('id') == 'codexiq':
            out.append(section)
            seen = True
        else:
            out.append(s)
    if not seen:
        out.append(section)
    # preferred order
    order = ['ai', 'women40', 'pharma', 'codexiq']
    by = {s['id']: s for s in out if s.get('id')}
    ordered = [by[i] for i in order if i in by]
    for s in out:
        if s.get('id') not in order:
            ordered.append(s)
    day['sections'] = ordered
    day['updatedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return day

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
    metrics = get_json('https://codexradar.com/api/intelligence-efficiency-metrics')
    try:
        insights = get_json('https://codexradar.com/api/radar-insights')
    except Exception:
        insights = {}
    section = build_section(metrics, insights)
    local_path = Path(f'/workspace/daily-briefing-site/data/{date}.json')
    local = None
    if local_path.exists():
        try:
            local = json.loads(local_path.read_text(encoding='utf-8'))
        except Exception:
            local = None
    live = fetch_latest_day()
    if local and local.get('date') == date:
        day = local
    elif live and live.get('date') == date:
        day = live
    else:
        day = empty_day(date)
    day = merge_section(day, section)
    out = Path(f'/workspace/daily-briefing-site/data/{date}.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(day, ensure_ascii=False, indent=2), encoding='utf-8')
    print(push(day))
    print('items', len(section['items']), 'summary', section['summary'][:120])

if __name__ == '__main__':
    main()
