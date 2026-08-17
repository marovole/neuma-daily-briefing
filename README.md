# Neuma 每日简报 · Daily Briefing

Live site: https://news.neumabio.xyz

中文 UI 每日简报：四个分页 AI/LLM、40+ 女性、健康医药、Codex IQ。
Four tabs: AI/LLM, women 40+, pharma, Codex IQ.

## Run locally

Start the server with node server.js, then open http://localhost:3000

Requires Node 18 or newer.

## Environment

PORT defaults to 3000. UPDATE_TOKEN defaults to changeme (Bearer token for POST /api/update).

Set UPDATE_TOKEN in the environment. Do not commit tokens or .update_token.

## API

- GET /api/latest : newest day JSON
- GET /api/day/:date : one day (YYYY-MM-DD)
- GET /api/archive : date list and section titles
- POST /api/update : write a day; Authorization Bearer UPDATE_TOKEN; body is day JSON with date and sections

## Data layout

JSON lives under data/:
- data/YYYY-MM-DD.json : merged day used by the site
- data/YYYY-MM-DD.ai.json / .women40.json / .pharma.json / .codexiq.json : optional per-tab sources

## Railway

railway.json is Nixpacks-friendly (node server.js). Set UPDATE_TOKEN in the service env before deploy. Do not put the token in the repo.

## License

[MIT](LICENSE) (c) 2026 marovole
