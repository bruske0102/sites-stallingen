import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
function sync(from, to) {
  fs.mkdirSync(to, { recursive: true });
  if (!fs.existsSync(from)) return;
  for (const f of fs.readdirSync(from)) {
    if (!/\.(jpe?g|png|webp)$/i.test(f)) continue;
    fs.copyFileSync(path.join(from, f), path.join(to, f));
  }
  console.log("synced", from, "→", to);
}
sync(path.join(root, "migration/assets/heroes"), path.join(root, "public/heroes"));
sync(path.join(root, "migration/blog-export/heroes"), path.join(root, "public/blog-heroes"));
