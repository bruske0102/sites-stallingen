import citiesJson from "../data/cities.json";
import demoJson from "../data/listings-demo.json";
import prijzenJson from "../data/prijzen.json";
import websitesJson from "../data/websites.json";
import plaatsenJson from "../data/plaatsen.json";
import instellingenJson from "../data/instellingen.json";
import { bouwModel, shopPad, plaatsPad as plaatsPadMjs } from "./bouw-model.mjs";
import type { City, Listing, WebsiteCheck } from "./model";
import { isAPlus, resolveWebsite } from "./model";

export const cities = citiesJson as City[];
export const websites = websitesJson as Record<string, WebsiteCheck>;
export const instellingen = instellingenJson as {
  site: { naam: string; url: string; email: string };
  groepB: { minAdressen: number; minZoekvolume: number; aantal: number; maxKm: number; forcePlaatsen?: string[]; _forcePlaatsen_uitleg?: string };
  omgeving: { max: number };
  redirects: Record<string, string>;
  samenvoegen: Record<string, string>;
  web3forms: { key: string };
  monetization?: {
    mode: string;
    adsense?: { client: string; slots?: { link?: string; auto?: string } };
    affiliate?: {
      tip?: string;
      [key: string]: string | undefined;
    };
  };
};
export const prijzen = prijzenJson as {
  gecontroleerd: string;
  jaar_label: number;
  disclaimer: string;
  items: { id: string; naam: string; eenheid: string; min: number; max: number; note?: string }[];
};

export type ListingFile = Listing & {
  id?: number | string;
  provincie: string;
  plaats: string;
  slug: string;
  status?: string;
  email?: string | null;
  omschrijving?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  oude_url?: string | null;
};

const scrapedModules = import.meta.glob<ListingFile>("../content/stallingen/*.json", {
  eager: true,
  import: "default",
});

const rawListings: ListingFile[] = Object.values(scrapedModules).filter(Boolean) as ListingFile[];

const model = bouwModel({
  listings: rawListings.map((r) => ({ ...r })),
  plaatsen: plaatsenJson as Record<string, any>,
  instellingen,
  websites,
  cities,
});

export function getModel() {
  return model;
}

export function getCity(provincie: string, plaats: string): City | undefined {
  return cities.find((c) => c.provincie === provincie && c.plaats === plaats);
}

export function getPlaats(provincie: string, plaats: string) {
  return (
    model.plaatsenA.find((p) => p.provincie === provincie && p.slug === plaats) ||
    model.plaatsenB.find((p) => p.provincie === provincie && p.slug === plaats)
  );
}

/** Listing enriched for cards/detail (from model actief). */
export type ShopListing = ListingFile & {
  websiteStatus?: string | null;
  websiteUrl?: string | null;
};

export function listingsFor(city: City): ShopListing[] {
  const plaats = model.plaatsenA.find((p) => p.key === city.key);
  if (plaats) return plaats.listings as ShopListing[];
  // Demo fallback while a city has no scrape yet
  const demo = (demoJson as Record<string, Listing[]>)[city.key] ?? [];
  return demo.map((s) => {
    const { websiteStatus, websiteUrl } = resolveWebsite(s, websites);
    return { ...s, websiteStatus, websiteUrl } as ShopListing;
  });
}

export function scrapedListingCount(): number {
  return model.actief.length;
}

export function allShops(): ShopListing[] {
  return model.actief as ShopListing[];
}

export function findShop(provincie: string, plaats: string, slug: string): ShopListing | undefined {
  return model.actief.find(
    (s) => s.provincie === provincie && s.plaats === plaats && s.slug === slug,
  ) as ShopListing | undefined;
}

export function shopPath(s: { provincie: string; plaats: string; slug: string }): string {
  return shopPad(s);
}

export function plaatsPath(p: { provincie: string; slug?: string; plaats?: string }): string {
  return plaatsPadMjs(p);
}

export function prijs(id: string) {
  return prijzen.items.find((x) => x.id === id);
}

export function bereik(id: string): string {
  const p = prijs(id);
  if (!p) return "";
  const fmt = (n: number) =>
    n < 1 ? `€ ${n.toFixed(2).replace(".", ",")}` : `€ ${Math.round(n)}`;
  if (p.max == null || p.max === p.min) return `vanaf ${fmt(p.min)}`;
  return `${fmt(p.min)} – ${fmt(p.max)}`;
}

export function maandJaar(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("nl-NL", { month: "long", year: "numeric" });
}

export function citiesByProvincie(slug: string): City[] {
  return cities.filter((c) => c.provincie === slug).sort((a, b) => b.listings - a.listings);
}

export { isAPlus };
