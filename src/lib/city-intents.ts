/**
 * Semrush NL city/intent research for Stallingen.xyz (2026-10-06).
 * Volumes from phrase_these database=nl. Do not invent numbers.
 * City titles use opslag / self storage / stalling / caravanstalling (inventory match).
 * fietsenstalling is related (often municipal) and can still trigger A+ volume.
 * A+ = inventory vol >= 200 or fietsenstalling vol >= 200 or listings >= 8.
 */
import { listingCount } from "./nl-count";
export type CityIntentFlags = {
  volume: number;
  kd?: number | null;
  primaryPhrase: string;
};
export const CITY_INTENTS: Record<string, CityIntentFlags> = {
  "aalsmeer": { volume: 0, kd: null, primaryPhrase: "stalling aalsmeer" },
  "alkmaar": { volume: 0, kd: null, primaryPhrase: "stalling alkmaar" },
  "almelo": { volume: 0, kd: null, primaryPhrase: "stalling almelo" },
  "almere": { volume: 590, kd: 26, primaryPhrase: "opslag almere" },
  "alphen": { volume: 0, kd: null, primaryPhrase: "stalling alphen" },
  "alphen-aan-den-rijn": { volume: 0, kd: null, primaryPhrase: "stalling alphen aan den rijn" },
  "amersfoort": { volume: 210, kd: 23, primaryPhrase: "opslag amersfoort" },
  "amsterdam": { volume: 590, kd: 22, primaryPhrase: "opslag amsterdam" },
  "amsterdam-duivendrecht": { volume: 0, kd: null, primaryPhrase: "stalling amsterdam duivendrecht" },
  "arnhem": { volume: 210, kd: 24, primaryPhrase: "opslag arnhem" },
  "assendelft": { volume: 0, kd: null, primaryPhrase: "stalling assendelft" },
  "baarlo": { volume: 0, kd: null, primaryPhrase: "stalling baarlo lb" },
  "baarn": { volume: 0, kd: null, primaryPhrase: "stalling baarn" },
  "bergen-op-zoom": { volume: 0, kd: null, primaryPhrase: "stalling bergen op zoom" },
  "best": { volume: 0, kd: null, primaryPhrase: "stalling best" },
  "beusichem": { volume: 0, kd: null, primaryPhrase: "stalling beusichem" },
  "beverwijk": { volume: 0, kd: null, primaryPhrase: "stalling beverwijk" },
  "budel": { volume: 0, kd: null, primaryPhrase: "stalling budel" },
  "delft": { volume: 210, kd: 22, primaryPhrase: "opslag delft" },
  "den-bosch": { volume: 0, kd: null, primaryPhrase: "stalling den bosch" },
  "dronryp": { volume: 0, kd: null, primaryPhrase: "stalling dronryp" },
  "eindhoven": { volume: 320, kd: 19, primaryPhrase: "opslag eindhoven" },
  "emmen": { volume: 0, kd: null, primaryPhrase: "stalling emmen" },
  "enschede": { volume: 0, kd: null, primaryPhrase: "stalling enschede" },
  "goes": { volume: 0, kd: null, primaryPhrase: "stalling goes" },
  "groningen-gemeente": { volume: 210, kd: 19, primaryPhrase: "self storage groningen" },
  "gronsveld": { volume: 0, kd: null, primaryPhrase: "stalling gronsveld" },
  "haarlem": { volume: 480, kd: 15, primaryPhrase: "opslag haarlem" },
  "heerenveen": { volume: 0, kd: null, primaryPhrase: "stalling heerenveen" },
  "hei-en-boeicop": { volume: 0, kd: null, primaryPhrase: "stalling hei- en boeicop" },
  "helmond": { volume: 0, kd: null, primaryPhrase: "stalling helmond" },
  "hengelo": { volume: 0, kd: null, primaryPhrase: "stalling hengelo ov" },
  "hilversum": { volume: 0, kd: null, primaryPhrase: "stalling hilversum" },
  "hoorn": { volume: 0, kd: null, primaryPhrase: "stalling hoorn nh" },
  "kampen": { volume: 0, kd: null, primaryPhrase: "stalling kampen" },
  "kelpen-oler": { volume: 0, kd: null, primaryPhrase: "stalling kelpen-oler" },
  "kerkrade": { volume: 0, kd: null, primaryPhrase: "stalling kerkrade" },
  "kudelstaart": { volume: 0, kd: null, primaryPhrase: "stalling kudelstaart" },
  "leek": { volume: 0, kd: null, primaryPhrase: "stalling leek" },
  "leeuwarden": { volume: 0, kd: null, primaryPhrase: "stalling leeuwarden" },
  "leiden": { volume: 170, kd: 21, primaryPhrase: "opslag leiden" },
  "leiderdorp": { volume: 0, kd: null, primaryPhrase: "stalling leiderdorp" },
  "liempde": { volume: 0, kd: null, primaryPhrase: "stalling liempde" },
  "maastricht": { volume: 0, kd: null, primaryPhrase: "stalling maastricht" },
  "marum": { volume: 0, kd: null, primaryPhrase: "stalling marum" },
  "meppel": { volume: 0, kd: null, primaryPhrase: "stalling meppel" },
  "middelburg": { volume: 0, kd: null, primaryPhrase: "stalling middelburg" },
  "nieuwegein": { volume: 0, kd: null, primaryPhrase: "stalling nieuwegein" },
  "nieuwerkerk": { volume: 0, kd: null, primaryPhrase: "stalling nieuwerkerk zld" },
  "nijmegen": { volume: 390, kd: 30, primaryPhrase: "opslag nijmegen" },
  "noordwijk": { volume: 0, kd: null, primaryPhrase: "stalling noordwijk zh" },
  "oss": { volume: 0, kd: null, primaryPhrase: "stalling oss" },
  "purmerend": { volume: 0, kd: null, primaryPhrase: "stalling purmerend" },
  "roosendaal": { volume: 0, kd: null, primaryPhrase: "stalling roosendaal" },
  "rotterdam": { volume: 480, kd: 22, primaryPhrase: "opslag rotterdam" },
  "sas-van-gent": { volume: 0, kd: null, primaryPhrase: "stalling sas van gent" },
  "schellinkhout": { volume: 0, kd: null, primaryPhrase: "stalling schellinkhout" },
  "schiedam": { volume: 0, kd: null, primaryPhrase: "stalling schiedam" },
  "terneuzen": { volume: 0, kd: null, primaryPhrase: "stalling terneuzen" },
  "tilburg": { volume: 260, kd: 22, primaryPhrase: "opslag tilburg" },
  "utrecht-gemeente": { volume: 480, kd: 34, primaryPhrase: "opslag utrecht" },
  "veenendaal": { volume: 0, kd: null, primaryPhrase: "stalling veenendaal" },
  "venray": { volume: 0, kd: null, primaryPhrase: "stalling venray" },
  "vijfhuizen": { volume: 0, kd: null, primaryPhrase: "stalling vijfhuizen nh" },
  "vlissingen": { volume: 0, kd: null, primaryPhrase: "stalling vlissingen" },
  "volendam": { volume: 0, kd: null, primaryPhrase: "stalling volendam" },
  "wijchen": { volume: 0, kd: null, primaryPhrase: "stalling wijchen" },
  "wijdenes": { volume: 0, kd: null, primaryPhrase: "stalling wijdenes" },
  "wormerveer": { volume: 0, kd: null, primaryPhrase: "stalling wormerveer" },
  "woudenberg": { volume: 0, kd: null, primaryPhrase: "stalling woudenberg" },
  "zaamslag": { volume: 0, kd: null, primaryPhrase: "stalling zaamslag" },
  "zaandam": { volume: 0, kd: null, primaryPhrase: "stalling zaandam" },
  "zwolle": { volume: 260, kd: 17, primaryPhrase: "opslag zwolle" },
  "utrecht": { volume: 480, kd: 34, primaryPhrase: "opslag utrecht" },
  "groningen": { volume: 210, kd: 19, primaryPhrase: "self storage groningen" },
};

export const INTENT_BLOG_LINKS = {
  opslag: { href: "/blog/binnen-of-buitenstalling/", label: "Binnen of buitenstalling" },
  box: { href: "/blog/caravanstalling/", label: "Caravanstalling" },
  kiezen: { href: "/blog/caravanstalling-kosten/", label: "Caravanstalling kosten" },
} as const;

export function cityIntent(plaatsSlug: string): CityIntentFlags | undefined {
  return CITY_INTENTS[plaatsSlug];
}

export function isHighTrafficCity(plaatsSlug: string): boolean {
  const row = CITY_INTENTS[plaatsSlug];
  return Boolean(row && row.volume >= 200);
}

export function cityPageTitle(opts: {
  stad: string; plaatsSlug: string; n: number; aPlus?: boolean;
}): string {
  const { stad, plaatsSlug, n } = opts;
  const intent = CITY_INTENTS[plaatsSlug];
  if (n <= 0) return `Stalling ${stad}`;
  if (intent && intent.volume >= 200) {
    const label = intent.primaryPhrase.charAt(0).toUpperCase() + intent.primaryPhrase.slice(1);
    return `${label}: ${listingCount(n)} met adres`;
  }
  return `Stalling ${stad}: ${listingCount(n)} met adres`;
}

export function cityPageDescription(opts: {
  stad: string; plaatsSlug: string; n: number; provincieNaam: string; aPlus?: boolean;
}): string {
  const { stad, n, provincieNaam } = opts;
  return `Vergelijk ${listingCount(n)} stalling en opslag in ${stad} (${provincieNaam}): adres en telefoon.`;
}
