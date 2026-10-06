// Runs in front of static assets (run_worker_first in wrangler.jsonc).
import map from "./redirects.json";

const ID_PATTERNS = [/^\/zoeken\/(\d+)\/?$/];

const redirect = (to, url) => Response.redirect(new URL(to, url.origin).toString(), 301);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let p;
    try {
      p = decodeURI(url.pathname);
    } catch {
      p = url.pathname;
    }
    const withSlash = p.endsWith("/") ? p : p + "/";
    // Don't append "/" for file-like paths (e.g. sitemap-index.xml) — that
    // matched "/sitemap-index.xml/" → "/sitemap-index.xml" and looped 301.
    const looksLikeFile = p.split("/").pop()?.includes(".") ?? false;
    const direct = map.paths[p] || (!looksLikeFile && map.paths[withSlash]);
    if (direct) return redirect(direct, url);

    for (const re of ID_PATTERNS) {
      const m = p.match(re);
      if (m && map.ids[m[1]]) return redirect(map.ids[m[1]], url);
    }

    const last = p.slice(p.lastIndexOf("/") + 1);
    if (!p.endsWith("/") && !last.includes(".")) {
      const probe = await env.ASSETS.fetch(new URL(url.pathname + "/", url.origin));
      if (probe.status === 200) return redirect(url.pathname + "/" + url.search, url);
    } else {
      const res = await env.ASSETS.fetch(request);
      if (res.status !== 404) return res;
    }

    const notFound = await env.ASSETS.fetch(new URL("/404.html", url.origin));
    if (notFound.status === 200) {
      return new Response(notFound.body, {
        status: 404,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
    return new Response("Niet gevonden", { status: 404 });
  },
};
