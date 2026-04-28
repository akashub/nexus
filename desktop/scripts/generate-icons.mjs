import sharp from "sharp";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SVG = readFileSync(join(__dirname, "../src/assets/logo.svg"));
const ICONS_DIR = join(__dirname, "../src-tauri/icons");

const targets = [
  { name: "32x32.png", size: 32 },
  { name: "128x128.png", size: 128 },
  { name: "128x128@2x.png", size: 256 },
  { name: "icon.png", size: 512 },
  { name: "Square30x30Logo.png", size: 30 },
  { name: "Square44x44Logo.png", size: 44 },
  { name: "Square71x71Logo.png", size: 71 },
  { name: "Square89x89Logo.png", size: 89 },
  { name: "Square107x107Logo.png", size: 107 },
  { name: "Square142x142Logo.png", size: 142 },
  { name: "Square150x150Logo.png", size: 150 },
  { name: "Square284x284Logo.png", size: 284 },
  { name: "Square310x310Logo.png", size: 310 },
  { name: "StoreLogo.png", size: 50 },
];

for (const { name, size } of targets) {
  await sharp(SVG, { density: 300 })
    .resize(size, size)
    .png()
    .toFile(join(ICONS_DIR, name));
  console.log(`  ${name} (${size}x${size})`);
}

// Generate ICO (use 256px PNG as source)
await sharp(SVG, { density: 300 })
  .resize(256, 256)
  .png()
  .toFile(join(ICONS_DIR, "icon.ico.png"));

// Generate ICNS source (1024px)
await sharp(SVG, { density: 300 })
  .resize(1024, 1024)
  .png()
  .toFile(join(ICONS_DIR, "icon-1024.png"));

console.log("\nDone! Note: icon.icns and icon.ico need manual conversion.");
console.log("For macOS: sips -s format icns icon-1024.png --out icon.icns");
