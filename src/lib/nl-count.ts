export function nlCount(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`;
}
export const LISTING_NOUN = { singular: "stalling", plural: "stallingen" } as const;
export function listingCount(n: number): string {
  return nlCount(n, LISTING_NOUN.singular, LISTING_NOUN.plural);
}
