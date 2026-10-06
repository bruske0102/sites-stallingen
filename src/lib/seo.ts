/** Clean scraped Blogger meta for modern SERP titles/descriptions. */

const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
const EMOJI_RE = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu;

export function stripMetaNoise(raw: string): string {
  return String(raw || "")
    .replace(EMAIL_RE, " ")
    .replace(/[✅✓✔ᐅ►▪•]+/g, " ")
    .replace(EMOJI_RE, " ")
    .replace(/\s+/g, " ")
    .replace(/\s([,.·|])/g, "$1")
    .replace(/([,.·|])\s*([,.·|])/g, "$1")
    .trim()
    .replace(/^[,.·|\s]+|[,.·|\s]+$/g, "");
}

/** Prefer a clean title under ~60 chars for SERPs. */
export function shopTitle(opts: {
  metaTitle?: string | null;
  naam: string;
  plaats: string;
  telefoon?: string | null;
}): string {
  const cleaned = stripMetaNoise(opts.metaTitle || "");
  if (cleaned && cleaned.length >= 8) {
    return cleaned.length > 65
      ? cleaned.slice(0, 62).trim().replace(/[,.·|\s-]+$/, "") + "…"
      : cleaned;
  }
  if (opts.telefoon) return `${opts.naam} ${opts.telefoon} · stalling ${opts.plaats}`;
  return `${opts.naam} · stalling ${opts.plaats}`;
}

export function shopDescription(opts: {
  metaDescription?: string | null;
  naam: string;
  plaats: string;
  telefoon?: string | null;
  website?: boolean;
}): string {
  const cleaned = stripMetaNoise(opts.metaDescription || "");
  if (cleaned && cleaned.length >= 40) {
    return cleaned.length > 160 ? cleaned.slice(0, 157).trim() + "…" : cleaned;
  }
  return `${opts.naam} - stalling in ${opts.plaats}: adres${
    opts.telefoon ? " en telefoonnummer" : ""
  }${opts.website ? " en website" : ""}. Route en contact - bel voor beschikbaarheid en tarief.`;
}
