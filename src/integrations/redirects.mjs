// After every build: compute 301s from A/B/C model → worker/redirects.json
// (Cloudflare Pages _redirects is capped ~2k rules; we need thousands.)
import fs from "node:fs";
import path from "node:path";
import { bouwModel, shopPad, plaatsPad } from "../lib/bouw-model.mjs";

const lees = (p) => JSON.parse(fs.readFileSync(p, "utf8"));

export default function redirects() {
  return {
    name: "stallingen-redirects",
    hooks: {
      "astro:build:done": ({ logger }) => {
        const root = process.cwd();
        const dir = path.join(root, "src/content/stallingen");
        const listings = fs.existsSync(dir)
          ? fs
              .readdirSync(dir)
              .filter((f) => f.endsWith(".json"))
              .map((f) => lees(path.join(dir, f)))
          : [];
        const plaatsen = lees(path.join(root, "src/data/plaatsen.json"));
        const instellingen = lees(path.join(root, "src/data/instellingen.json"));
        const cities = lees(path.join(root, "src/data/cities.json"));
        const websitesF = path.join(root, "src/data/websites.json");
        const websites = fs.existsSync(websitesF) ? lees(websitesF) : {};
        const m = bouwModel({ listings, plaatsen, instellingen, websites, cities });

        const paths = Object.fromEntries(m.redirects);
        const ids = Object.fromEntries(m.doelVanId);
        fs.mkdirSync(path.join(root, "worker"), { recursive: true });
        fs.writeFileSync(
          path.join(root, "worker/redirects.json"),
          JSON.stringify({ paths, ids }),
        );
        logger.info(
          `${Object.keys(paths).length} path redirects + ${Object.keys(ids).length} id redirects → worker/redirects.json`,
        );
        logger.info(`towns: A ${m.plaatsenA.length}, B ${m.plaatsenB.length}`);

        const site = "https://stallingen.xyz";
        // Indexable hubs only: skip /zoeken/, forms, and /p/disclaimer/ (noindex).
        const urls = new Set([
          `${site}/`,
          `${site}/blog/`,
          `${site}/contact/`,
          `${site}/bedrijf/toevoegen/`,
        ]);
        for (const p of m.plaatsenA) urls.add(`${site}${plaatsPad(p)}`);
        for (const p of m.plaatsenB) urls.add(`${site}${plaatsPad(p)}`);
        for (const s of m.actief) urls.add(`${site}${shopPad(s)}`);
        const blogDir = path.join(root, "migration/blog-export/posts");
        if (fs.existsSync(blogDir)) {
          for (const f of fs.readdirSync(blogDir).filter((x) => x.endsWith(".json"))) {
            const post = lees(path.join(blogDir, f));
            if (post.slug) urls.add(`${site}/blog/${post.slug}/`);
          }
        }
        for (const slug of Object.keys(m.perProvincie || {})) {
          urls.add(`${site}/${slug}/`);
        }
        const sorted = [...urls].sort();
        const body = sorted
          .map(
            (u) =>
              `  <url>\n    <loc>${u}</loc>\n    <changefreq>weekly</changefreq>\n  </url>`,
          )
          .join("\n");
        const xml =
          `<?xml version="1.0" encoding="UTF-8"?>\n` +
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
        const dist = path.join(root, "dist");
        if (fs.existsSync(dist)) {
          fs.writeFileSync(path.join(dist, "sitemap-index.xml"), xml);
          fs.writeFileSync(path.join(dist, "sitemap.xml"), xml);
          logger.info(`sitemap: ${sorted.length} URLs → dist/sitemap-index.xml`);
        }
      },
    },
  };
}
