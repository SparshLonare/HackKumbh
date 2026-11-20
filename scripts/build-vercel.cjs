const fs = require("node:fs");
const path = require("node:path");

const apiBase = (process.env.API_BASE_URL || "").replace(/\/+$/, "");
if (!apiBase) {
  throw new Error("Set API_BASE_URL to the Render API URL ending in /api.");
}

let parsed;
try {
  parsed = new URL(apiBase);
} catch {
  throw new Error("API_BASE_URL must be a valid absolute URL ending in /api.");
}

if (parsed.protocol !== "https:" || !parsed.pathname.replace(/\/+$/, "").endsWith("/api")) {
  throw new Error("API_BASE_URL must use https and end in /api.");
}

const repositoryRoot = path.join(__dirname, "..");
const frontendDirectory = path.join(repositoryRoot, "frontend");
const outputDirectory = path.join(repositoryRoot, "vercel-build");
fs.mkdirSync(path.join(outputDirectory, "static"), { recursive: true });
fs.copyFileSync(path.join(frontendDirectory, "index.html"), path.join(outputDirectory, "index.html"));
fs.cpSync(path.join(frontendDirectory, "static"), path.join(outputDirectory, "static"), { recursive: true });

const outputPath = path.join(outputDirectory, "static", "api-config.js");
fs.writeFileSync(
  outputPath,
  `window.MEDI_API_BASE = ${JSON.stringify(apiBase)};\n`,
  "utf8",
);
console.log(`Configured frontend API base: ${parsed.origin}${parsed.pathname}`);
