# Stallingen.xyz (Astro)

Dutch directory for caravanstalling, camperstalling and self-storage. Django-overzicht family.

## Run

```bash
cd sites/stallingen
npm install
npm run dev
```

Dev server: [http://127.0.0.1:43881](http://127.0.0.1:43881)

## Build

```bash
npm run build
npm run preview
```

## Data

- `src/content/stallingen/*.json` — scraped + triage (separate scrape process)
- `src/data/cities.json` - Group A after 1c (Semrush NL volumes)
- `src/lib/city-intents.ts` - titles/descriptions + city H2s from phrase_these NL
- `migration/semrush/` — place NL exports here (do not reuse basisschool/keramiek CSVs)
- `migration/assets/heroes/` — city heroes (synced to `public/heroes` on prebuild)

**Scrape vs Semrush:** scrape = listing inventory on the live site; Semrush = KD + volume for keywords/cities.

## Design

Blue CSS tokens (porcelain + cobalt) in `src/styles/global.css`. Brand: **Stallingen.xyz**. See `migration/design/`.

## Hosting

GitHub: `bruske0102/sites-stallingen` (site-only push at repo root). Worker name: `stallingen`.  
CF **Root directory = empty**. See `migration/GO_LIVE_NOW.md` for CF Worker + Builds, Email Routing, domain, GSC+Bing.

## Locked decisions

See `migration/DECISIONS.md` — brand Stallingen.xyz, stallingen only (no coaches/lifestyle junk), SBO-equivalent N/A.
