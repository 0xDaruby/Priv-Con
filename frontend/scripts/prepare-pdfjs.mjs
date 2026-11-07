import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Copy only trusted installed runtime assets. No network fetches or document data.
const require = createRequire(import.meta.url);
const packageRoot = dirname(require.resolve("pdfjs-dist/package.json"));
const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(frontendRoot, "public", "pdfjs");
const { version } = JSON.parse(await readFile(join(packageRoot, "package.json"), "utf8"));
await mkdir(join(target, "worker"), { recursive: true });
await cp(join(packageRoot, "build", "pdf.worker.min.mjs"), join(target, "worker", "pdf.worker.min.mjs"));
for (const folder of ["cmaps", "standard_fonts", "wasm", "iccs"]) {
  await cp(join(packageRoot, folder), join(target, folder), { recursive: true });
}
await cp(join(packageRoot, "LICENSE"), join(target, "LICENSE"));
await writeFile(join(target, "version.json"), `${JSON.stringify({ version })}\n`);
console.log(`Prepared local PDF.js ${version} worker and rendering assets.`);
