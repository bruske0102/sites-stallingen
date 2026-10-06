export type ContentTier = "data_unique" | "extended_priority" | "extended_later_hard";

export type City = {
  key: string;
  provincie: string;
  provincieNaam: string;
  plaats: string;
  naam: string;
  listings: number;
  content_tier: ContentTier;
  page_group: string;
  keyword: string;
  volume: number;
  kd: number | null;
  best_position: number | null;
};

export type Listing = {
  id?: number | string;
  naam: string;
  straat?: string | null;
  postcode?: string | null;
  plaatsnaam?: string | null;
  telefoon?: string | null;
  /** Raw scraped URL (may be spam/parked/dead). Prefer websiteUrl for links. */
  website?: string;
  /** From websites.json check; only ok/verhuisd/geblokkeerd become websiteUrl. */
  websiteStatus?: string | null;
  /** Clickable URL when status is linkable; null hides bad outbound links. */
  websiteUrl?: string | null;
  lat?: number;
  lon?: number;
  kenmerken?: Record<string, string[]>;
};

/** Website check (playbook/check_websites.py → src/data/websites.json). */
export const TOON_WEBSITE = new Set(["ok", "verhuisd", "geblokkeerd"]);

export type WebsiteCheck = {
  status: string;
  url?: string;
  final?: string;
  reason?: string;
};

/** Resolve a listing's outbound link from the Phase 1b check map. */
export function resolveWebsite(
  listing: { id?: number | string; website?: string },
  websites: Record<string, WebsiteCheck> = {},
): { websiteStatus: string | null; websiteUrl: string | null } {
  const raw = listing.website?.trim();
  if (!raw) return { websiteStatus: null, websiteUrl: null };
  const w = listing.id != null ? websites[String(listing.id)] : undefined;
  const normalized = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
  const websiteStatus = w?.status ?? "onbekend";
  const websiteUrl =
    !w || TOON_WEBSITE.has(w.status) ? (w?.url ?? normalized) : null;
  return { websiteStatus, websiteUrl };
}

/** A-plus = Semrush extended (incl. hard big cities). Everyone else Group A = A-lite. */
export function isAPlus(city: City): boolean {
  return city.content_tier === "extended_priority" || city.content_tier === "extended_later_hard";
}

const STUDENT = new Set([
  "delft",
  "groningen",
  "groningen-gemeente",
  "amsterdam",
  "utrecht",
  "utrecht-gemeente",
  "wageningen",
  "leiden",
  "nijmegen",
  "maastricht",
  "enschede",
  "tilburg",
  "eindhoven",
  "rotterdam",
]);

export function isStudentCity(city: City): boolean {
  return STUDENT.has(city.plaats);
}

export function plaatsPad(city: City): string {
  return `/${city.provincie}/${city.plaats}/`;
}

export function telHref(n: string): string {
  return n.replace(/[^\d+]/g, "");
}

export function mapsUrl(s: Listing): string | null {
  if (s.lat != null && s.lon != null) {
    return `https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lon}`;
  }
  const q = [s.straat, s.postcode, s.plaatsnaam].filter(Boolean).join(", ");
  if (!q) return null;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
}

export function kenmerkCount(listings: Listing[], needle: RegExp): number {
  let n = 0;
  for (const s of listings) {
    const all = Object.values(s.kenmerken ?? {}).flat().join(" ");
    if (needle.test(all)) n++;
  }
  return n;
}
