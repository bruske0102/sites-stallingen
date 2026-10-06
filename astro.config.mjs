// @ts-check
import { defineConfig } from "astro/config";
import redirects from "./src/integrations/redirects.mjs";

export default defineConfig({
  site: "https://stallingen.xyz",
  output: "static",
  trailingSlash: "always",
  build: {
    format: "directory",
  },
  // Static preview needs this; Worker also 301s via redirects.json / instellingen.redirects
  redirects: {
    "/cookies/": "/p/disclaimer/",
  },
  integrations: [redirects()],
  server: {
    host: "127.0.0.1",
    port: 43881,
  },
  vite: {
    server: {
      watch: {
        ignored: ["**/migration/**", "**/preview/**"],
      },
      // Pagefind index lives in public/pagefind (gitignored); allow local /zoeken/.
      fs: {
        allow: ["..", "./public/pagefind"],
      },
    },
  },
});
