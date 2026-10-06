// Town groups + redirects, same A/B/C model as other niche directories.
// A = town with ≥1 active stalling; B = large town without stalling; C = 301 → nearest A.

export const PROVINCIES = {
  drenthe: "Drenthe",
  flevoland: "Flevoland",
  friesland: "Friesland",
  gelderland: "Gelderland",
  groningen: "Groningen",
  limburg: "Limburg",
  "noord-brabant": "Noord-Brabant",
  "noord-holland": "Noord-Holland",
  overijssel: "Overijssel",
  utrecht: "Utrecht",
  zeeland: "Zeeland",
  "zuid-holland": "Zuid-Holland",
};

export function afstandKm(a, b) {
  const R = 6371,
    rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad,
    dLon = (b.lon - a.lon) * rad;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export const shopPad = (s) => `/${s.provincie}/${s.plaats}/${s.slug}/`;
export const plaatsPad = (p) => `/${p.provincie}/${p.slug ?? p.plaats}/`;

export const TOON_WEBSITE = new Set(["ok", "verhuisd", "geblokkeerd"]);

export function resolveWebsite(listing, websites = {}) {
  const raw = listing.website?.trim();
  if (!raw) return { websiteStatus: null, websiteUrl: null };
  const w = listing.id != null ? websites[String(listing.id)] : undefined;
  const normalized = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
  const websiteStatus = w?.status ?? "onbekend";
  const websiteUrl =
    !w || TOON_WEBSITE.has(w.status) ? (w?.url ?? normalized) : null;
  return { websiteStatus, websiteUrl };
}

/**
 * @param {object} o
 * @param {object[]} o.listings
 * @param {Record<string, any>} o.plaatsen
 * @param {object} o.instellingen
 * @param {Record<string, any>} [o.websites]
 * @param {object[]} [o.cities] Semrush Group A metadata (content_tier etc.)
 */
export function bouwModel({ listings, plaatsen, instellingen, websites = {}, cities = [] }) {
  const cityByKey = new Map(cities.map((c) => [c.key, c]));

  for (const s of listings) {
    const { websiteStatus, websiteUrl } = resolveWebsite(s, websites);
    s.websiteStatus = websiteStatus;
    s.websiteUrl = websiteUrl;
  }

  const dubbelVan = new Map();
  {
    const gezien = new Map();
    const sorted = [...listings]
      .filter((s) => s.status === "actief")
      .sort((a, b) => a.slug.length - b.slug.length || a.slug.localeCompare(b.slug));
    for (const s of sorted) {
      const k = [s.provincie, s.plaats, s.naam.trim().toLowerCase(), (s.telefoon || "").replace(/\D/g, "")].join("|");
      if (gezien.has(k)) dubbelVan.set(s, gezien.get(k));
      else gezien.set(k, s);
    }
  }
  const perPad = new Map(listings.map((s) => [`${s.provincie}/${s.plaats}/${s.slug}`, s]));
  for (const [kopie, blijft] of Object.entries(instellingen.samenvoegen || {})) {
    if (kopie.startsWith("_") || !perPad.has(kopie) || !perPad.has(blijft)) continue;
    dubbelVan.set(perPad.get(kopie), perPad.get(blijft));
  }

  const actief = listings.filter((s) => s.status === "actief" && !dubbelVan.has(s));
  const gesloten = listings.filter((s) => s.status !== "actief");

  const perPlaats = new Map();
  for (const s of actief) {
    const key = `${s.provincie}/${s.plaats}`;
    if (!perPlaats.has(key)) perPlaats.set(key, []);
    perPlaats.get(key).push(s);
  }

  const plaatsenA = [...perPlaats.entries()].map(([key, lijst]) => {
    const [provincie, slug] = key.split("/");
    const p = plaatsen[key] || {};
    const city = cityByKey.get(key);
    const lat =
      p.lat ??
      (lijst.reduce((t, s) => t + (s.lat || 0), 0) / lijst.length || null);
    const lon =
      p.lon ??
      (lijst.reduce((t, s) => t + (s.lon || 0), 0) / lijst.length || null);
    lijst.sort(
      (a, b) =>
        (a.websiteUrl ? 0 : 1) - (b.websiteUrl ? 0 : 1) ||
        a.naam.localeCompare(b.naam, "nl"),
    );
    return {
      groep: "A",
      key,
      provincie,
      slug,
      plaats: slug,
      naam: city?.naam || p.naam || lijst[0].plaatsnaam || slug,
      lat,
      lon,
      adressen: p.adressen ?? null,
      listings: lijst,
      content_tier: city?.content_tier ?? "data_unique",
      provincieNaam: city?.provincieNaam || PROVINCIES[provincie],
      omgeving: [],
    };
  });
  const aByKey = new Map(plaatsenA.map((p) => [p.key, p]));

  const dichtstbijA = (punt, n = 1, maxKm = Infinity) =>
    plaatsenA
      .filter((p) => p.lat != null && punt.lat != null)
      .map((p) => ({ plaats: p, km: afstandKm(punt, p) }))
      .filter((x) => x.km <= maxKm && x.plaats.key !== punt.key)
      .sort((a, b) => a.km - b.km)
      .slice(0, n);

  const dichtstbijShops = (punt, n, maxKm) =>
    actief
      .filter((s) => s.lat != null && punt.lat != null)
      .map((s) => ({ shop: s, km: afstandKm(punt, s) }))
      .filter((x) => x.km <= maxKm)
      .sort((a, b) => a.km - b.km)
      .slice(0, n);

  const plaatsenB = [];
  const redirects = new Map();
  const extra = instellingen.redirects || {};

  const hoofdVan = new Map();
  const perBag = new Map();
  for (const [key, p] of Object.entries(plaatsen)) {
    if (!p.bag_code) continue;
    if (!perBag.has(p.bag_code)) perBag.set(p.bag_code, []);
    perBag.get(p.bag_code).push(key);
  }
  for (const keys of perBag.values()) {
    if (keys.length < 2) continue;
    const hoofd =
      keys.find((k) => aByKey.has(k)) ||
      [...keys].sort((a, b) => a.length - b.length || a.localeCompare(b))[0];
    for (const k of keys) if (k !== hoofd && !aByKey.has(k)) hoofdVan.set(k, hoofd);
  }

  for (const [key, p] of Object.entries(plaatsen)) {
    if (aByKey.has(key) || hoofdVan.has(key)) continue;
    const oud = `/${key}/`;
    if (extra[oud]) {
      redirects.set(oud, extra[oud]);
      continue;
    }
    if (p.samengevoegd_met && aByKey.has(p.samengevoegd_met)) {
      redirects.set(oud, `/${p.samengevoegd_met}/`);
      continue;
    }
    if (p.lat == null) {
      redirects.set(oud, `/${p.provincie}/`);
      continue;
    }
    const punt = { key, lat: p.lat, lon: p.lon };
    const forceB = new Set(instellingen.groepB?.forcePlaatsen || []);
    const isB =
      forceB.has(key) ||
      ((p.adressen ?? 0) >= instellingen.groepB.minAdressen &&
        (p.zoekvolume == null || p.zoekvolume >= instellingen.groepB.minZoekvolume));
    const buren = dichtstbijShops(punt, instellingen.groepB.aantal, instellingen.groepB.maxKm);
    // Bing URL continuity: forcePlaatsen keep a Group B hub even if no shops within maxKm.
    if (isB && (buren.length || forceB.has(key))) {
      plaatsenB.push({
        groep: "B",
        key,
        provincie: p.provincie,
        slug: p.slug,
        plaats: p.slug,
        naam: p.naam,
        lat: p.lat,
        lon: p.lon,
        adressen: p.adressen,
        buren,
        listings: [],
        content_tier: "data_unique",
        provincieNaam: PROVINCIES[p.provincie],
        dichtstbijePlaatsen: dichtstbijA(punt, 4, instellingen.groepB.maxKm),
        omgeving: [],
      });
      continue;
    }
    const doel = dichtstbijA(punt, 1)[0];
    redirects.set(oud, doel ? plaatsPad(doel.plaats) : `/${p.provincie}/`);
    if (doel && /^(BAG|Wikidata)/.test(p.bron || "")) {
      doel.plaats.omgeving.push({ naam: p.naam, km: doel.km });
    }
  }

  const maxOmgeving = instellingen.omgeving?.max ?? 12;
  for (const a of plaatsenA) {
    const gezien = new Set([a.naam.toLowerCase()]);
    a.omgeving = a.omgeving
      .sort((x, y) => x.km - y.km)
      .filter((o) => !gezien.has(o.naam.toLowerCase()) && gezien.add(o.naam.toLowerCase()))
      .slice(0, maxOmgeving);
  }

  const bKeys = new Set(plaatsenB.map((p) => p.key));
  for (const [kopie, hoofd] of hoofdVan) {
    const doel = aByKey.has(hoofd) || bKeys.has(hoofd) ? `/${hoofd}/` : redirects.get(`/${hoofd}/`);
    redirects.set(`/${kopie}/`, doel || `/${plaatsen[kopie].provincie}/`);
  }

  for (const s of actief) {
    if (s.oude_url && s.oude_url !== shopPad(s)) redirects.set(s.oude_url, shopPad(s));
  }
  // Prefer own plaats when it still has a hub (A or B). Playbook: gesloten → plaats.
  const bByKey = new Map(plaatsenB.map((p) => [p.key, p]));
  for (const s of gesloten) {
    const key = `${s.provincie}/${s.plaats}`;
    const town = aByKey.get(key) || bByKey.get(key);
    const doel = town
      ? plaatsPad(town)
      : dichtstbijA(s, 1)[0]
        ? plaatsPad(dichtstbijA(s, 1)[0].plaats)
        : `/${s.provincie}/`;
    redirects.set(shopPad(s), doel);
    if (s.oude_url) redirects.set(s.oude_url, doel);
  }
  for (const [kopie, bewaard] of dubbelVan) {
    redirects.set(shopPad(kopie), shopPad(bewaard));
    if (kopie.oude_url) redirects.set(kopie.oude_url, shopPad(bewaard));
  }

  // Manual overrides always win (Semrush ranking URLs / wrong-province / B-city shop closes).
  for (const [van, naar] of Object.entries(extra)) {
    if (van.startsWith("_")) continue;
    redirects.set(van, naar);
  }

  const doelVanId = new Map(
    listings.map((s) => [String(s.id), redirects.get(shopPad(s)) || shopPad(s)]),
  );

  const naamTel = new Map();
  for (const p of [...plaatsenA, ...plaatsenB]) {
    naamTel.set(p.naam, (naamTel.get(p.naam) || 0) + 1);
  }
  for (const p of [...plaatsenA, ...plaatsenB]) {
    // Match live Blogger: "Utrecht (gemeente)" / "Groningen (gemeente)" - not "Utrecht (Utrecht)".
    if (String(p.slug || "").includes("gemeente")) {
      p.titelNaam = `${p.naam} (gemeente)`;
    } else if (naamTel.get(p.naam) > 1) {
      // Rare: same town name in different provinces
      const sameProv = [...plaatsenA, ...plaatsenB].filter((x) => x.naam === p.naam);
      const multiProv = new Set(sameProv.map((x) => x.provincie)).size > 1;
      p.titelNaam = multiProv ? `${p.naam} (${PROVINCIES[p.provincie]})` : p.naam;
    } else {
      p.titelNaam = p.naam;
    }
  }

  const perProvincie = Object.fromEntries(Object.keys(PROVINCIES).map((k) => [k, { A: [], B: [] }]));
  for (const p of plaatsenA) perProvincie[p.provincie]?.A.push(p);
  for (const p of plaatsenB) perProvincie[p.provincie]?.B.push(p);
  for (const v of Object.values(perProvincie)) {
    v.A.sort((a, b) => b.listings.length - a.listings.length || a.naam.localeCompare(b.naam, "nl"));
    v.B.sort((a, b) => a.naam.localeCompare(b.naam, "nl"));
  }

  return {
    actief,
    plaatsenA,
    plaatsenB,
    perProvincie,
    redirects,
    doelVanId,
    dichtstbijShops,
    dichtstbijA,
  };
}
