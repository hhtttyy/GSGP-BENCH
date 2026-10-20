/**
 * Zero-dependency local preview for GSGP-Bench.
 *
 * Serves ./site and runs the real worker/index.js, so /api/analyze behaves the
 * same as it will on Cloudflare Workers. AI_MOCK defaults to "1" here; real
 * credentials are read from .dev.vars if present.
 *
 *   node scripts/dev-server.mjs
 *   PORT=4173 AI_MOCK=0 node scripts/dev-server.mjs
 */
import http from "node:http";
import path from "node:path";
import { readFile, stat } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import worker from "../worker/index.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "../site");
const repoRoot = path.resolve(here, "..");
const port = Number(process.env.PORT || 4173);

function loadDevVars() {
  const vars = {};
  try {
    const raw = readFileSync(path.join(repoRoot, ".dev.vars"), "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
      if (!match) continue;
      vars[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  } catch {
    // .dev.vars is optional.
  }
  return vars;
}

const devVars = loadDevVars();
const env = {
  ...devVars,
  ...process.env,
  AI_MOCK: process.env.AI_MOCK ?? devVars.AI_MOCK ?? "1"
};

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".pdf": "application/pdf",
  ".zip": "application/zip",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8"
};

const assets = {
  async fetch(request) {
    const url = new URL(request.url);
    let pathname = decodeURIComponent(url.pathname);
    let filePath = path.resolve(siteRoot, "." + pathname);
    if (filePath !== siteRoot && !filePath.startsWith(siteRoot + path.sep)) {
      return new Response("Forbidden", { status: 403 });
    }
    try {
      let info = await stat(filePath).catch(() => null);
      if (info && info.isDirectory()) {
        filePath = path.join(filePath, "index.html");
        info = await stat(filePath).catch(() => null);
      }
      if (!info || !info.isFile()) {
        return new Response("Not found", {
          status: 404,
          headers: { "content-type": "text/plain; charset=utf-8" }
        });
      }
      const body = request.method === "HEAD" ? null : await readFile(filePath);
      return new Response(body, {
        status: 200,
        headers: {
          "content-type": MIME[path.extname(filePath).toLowerCase()] || "application/octet-stream",
          "content-length": String(info.size),
          "cache-control": "no-store"
        }
      });
    } catch (error) {
      console.error("Static read failed", filePath, error.message);
      return new Response("Internal error", { status: 500 });
    }
  }
};

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return chunks.length ? Buffer.concat(chunks) : undefined;
}

const server = http.createServer(async (req, res) => {
  try {
    const url = `http://${req.headers.host || `localhost:${port}`}${req.url || "/"}`;
    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (Array.isArray(value)) value.forEach((item) => headers.append(key, item));
      else if (value != null) headers.set(key, value);
    }
    const hasBody = req.method !== "GET" && req.method !== "HEAD";
    const body = hasBody ? await readBody(req) : undefined;
    const request = new Request(url, { method: req.method, headers, body });
    const response = await worker.fetch(request, { ...env, ASSETS: assets });
    res.statusCode = response.status;
    response.headers.forEach((value, key) => res.setHeader(key, value));
    const buffer = Buffer.from(await response.arrayBuffer());
    res.end(buffer);
  } catch (error) {
    console.error("Dev server error", error);
    res.statusCode = 500;
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ error: { code: "DEV_SERVER_ERROR", message: error.message } }));
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`GSGP-Bench local preview: http://127.0.0.1:${port}`);
  console.log(`AI_MOCK=${env.AI_MOCK}${env.AI_MOCK === "1" ? " (labelled local mock)" : ""}`);
});
