#!/usr/bin/env node
/**
 * Go-live verification for stallingen.
 * Usage: node scripts/verify-golive.mjs [baseUrl]
 * Default baseUrl = http://127.0.0.1:43881
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bouwModel, plaatsPad, shopPad } from "../src/lib/bouw-model.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const base = (process.argv[2] || "http://127.0.0.1:43881").replace(/\/$/, "");
const lees = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));

// Semrush top pages (stalling) + structural must-haves
const SEMRUSH_TOP = [
  "/noord-holland/amsterdam/",
  "/zuid-holland/rotterdam/",
  "/cookies/",
  "/contact/",
  "/bedrijf/toevoegen/",
  "/zoeken/",
  "/p/disclaimer/",
];

const contentDir = path.join(root, "src/content/stallingen");
const listings = fs.existsSync(contentDir)
  ? fs
      .readdirSync(contentDir)
      .filter((f) => f.endsWith(".json"))
      .map((f) => lees(`src/content/stallingen/${f}`))
  : [];
const m = bouwModel({
  listings,
  plaatsen: lees("src/data/plaatsen.json"),
  instellingen: lees("src/data/instellingen.json"),
  websites: lees("src/data/websites.json"),
  cities: lees("src/data/cities.json"),
});
const paths = Object.fromEntries(m.redirects);

async function probe(p) {
  try {
    const res = await fetch(base + p, { redirect: "manual" });
    const loc = res.headers.get("location");
    return { code: res.status, loc: loc ? new URL(loc, base).pathname : null };
  } catch (e) {
    return { code: "ERR", loc: null, err: String(e.message || e) };
  }
}

const instellingen = lees("src/data/instellingen.json");
console.log(`site: ${instellingen.site.url}`);
console.log(`email: ${instellingen.site.email}`);
console.log(`listings actief: ${m.actief.length} · A ${m.plaatsenA.length} · B ${m.plaatsenB.length}`);
console.log(`redirects: ${Object.keys(paths).length}`);
console.log(`probe base: ${base}\n`);

let fail = 0;
for (const p of SEMRUSH_TOP) {
  const r = await probe(p);
  const ok =
    r.code === 200 ||
    r.code === 301 ||
    (typeof r.code === "number" && r.code >= 300 && r.code < 400);
  if (!ok) fail++;
  console.log(`${ok ? "OK" : "FAIL"} ${p} → ${r.code}${r.loc ? " " + r.loc : ""}`);
}

// Spot-check a few listing paths if we have data
for (const s of m.actief.slice(0, 3)) {
  const p = shopPad(s);
  const r = await probe(p);
  const ok = r.code === 200;
  if (!ok) fail++;
  console.log(`${ok ? "OK" : "FAIL"} listing ${p} → ${r.code}`);
}

for (const p of m.plaatsenA.slice(0, 3)) {
  const pathStr = plaatsPad(p);
  const r = await probe(pathStr);
  const ok = r.code === 200;
  if (!ok) fail++;
  console.log(`${ok ? "OK" : "FAIL"} plaats ${pathStr} → ${r.code}`);
}


// Disclaimer: utility page only — noindex + not in sitemap (all niches / future scaffolds)
{
  const discPath = path.join(root, "src/pages/p/disclaimer/index.astro");
  const redirPath = path.join(root, "src/integrations/redirects.mjs");
  const disc = fs.readFileSync(discPath, "utf8");
  const redir = fs.readFileSync(redirPath, "utf8");
  const hasNoindex = /\bnoindex\b/.test(disc);
  const inSitemap = /\$\{site\}\/p\/disclaimer\//.test(redir);
  if (!hasNoindex) fail++;
  console.log(`${hasNoindex ? "OK" : "FAIL"} disclaimer Layout noindex`);
  if (inSitemap) fail++;
  console.log(`${inSitemap ? "FAIL" : "OK"} disclaimer out of sitemap`);
  const r = await probe("/p/disclaimer/");
  if (r.code === 200) {
    const html = await fetch(base + "/p/disclaimer/").then((x) => x.text());
    const robots = /name=["']robots["'][^>]*content=["']noindex/i.test(html)
      || /content=["']noindex[^"']*["'][^>]*name=["']robots["']/i.test(html);
    if (!robots) fail++;
    console.log(`${robots ? "OK" : "FAIL"} /p/disclaimer/ robots noindex,follow`);
  }
}

process.exit(fail ? 1 : 0);
