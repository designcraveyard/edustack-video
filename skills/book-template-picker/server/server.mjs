#!/usr/bin/env node
// Localhost book-template picker. Binds 127.0.0.1:0, opens the browser to a
// polished gallery of the 9 book layout templates (ported from layout-gen's
// layout-templates-web), lets the user select 2–4, and writes a handshake JSON
// then exits — same lifecycle contract as the brief-collector server.
//
// Endpoints
//   GET  /                  — gallery HTML
//   GET  /templates.json    — display metadata (public/templates.json)
//   GET  /config.json       — runtime config (mode, min, max, page count, title)
//   GET  /static/<file>     — CSS / JS / wireframe SVG assets
//   GET  /refs/<path>       — reference jpg served from seed/template-references/
//   POST /submit            — writes the selection JSON and exits
//
// Args
//   --out <path>        where to write the selection JSON (required-ish; see default)
//   --run-dir <path>    a run directory; default out becomes <run-dir>/book/template-selection.json
//   --mode <shortlist>  selection mode (only "shortlist" today; reserved for future per-page mode)
//   --min <n>           minimum templates to pick (default 2)
//   --max <n>           maximum templates to pick (default 4)
//   --page-count <n>    prefill the page-count input (default 0 = ask)
//   --title <str>       heading shown in the UI (default "Pick your book layouts")
//   --no-open           don't auto-open the browser (for tests / headless)
//
// Handshake JSON shape:
//   { "templates": ["split-layout", ...], "page_count": 6, "mode": "shortlist", "ts": "..." }

import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve, dirname, extname, normalize, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));

const rawArgs = process.argv.slice(2);
const noOpen = rawArgs.includes("--no-open");
const args = Object.fromEntries(
  rawArgs.reduce((a, v, i, arr) => {
    if (v.startsWith("--")) a.push([v.slice(2), arr[i + 1]]);
    return a;
  }, [])
);

const pluginRoot = resolve(__dirname, "..", "..", "..");      // skills/book-template-picker/server → plugin root
const refsRoot = join(pluginRoot, "seed", "template-references");
const publicDir = join(__dirname, "public");

const mode = args["mode"] || "shortlist";
const minPick = Math.max(1, parseInt(args["min"] || "2", 10) || 2);
const maxPick = Math.max(minPick, parseInt(args["max"] || "4", 10) || 4);
const pageCount = parseInt(args["page-count"] || "0", 10) || 0;
const title = args["title"] || "Pick your book layouts";

const runDir = args["run-dir"] ? resolve(args["run-dir"]) : null;
const outPath = resolve(
  args["out"] ||
    (runDir ? join(runDir, "book", "template-selection.json") : join(process.cwd(), "template-selection.json"))
);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

// Guard against path traversal: resolve the requested path under `base` and
// confirm it stays inside `base`. Cross-platform — uses path.relative()
// instead of comparing string prefixes so Windows backslash separators don't
// break the inside-base check. (The older "base + '/'" approach silently
// 404'd every /static/* and /refs/* request on Windows because the joined
// target uses backslashes while the comparison string used a forward slash.)
function safeJoin(base, relPath) {
  const target = normalize(join(base, decodeURIComponent(relPath)));
  const rel = relative(base, target);
  // ".." anywhere in `rel` means the path tried to escape `base`.
  if (rel.startsWith("..") || rel.split(sep).includes("..")) return null;
  return target;
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://localhost");
    const path = url.pathname;

    if (req.method === "GET" && (path === "/" || path === "/index.html")) {
      const body = await readFile(join(publicDir, "index.html"));
      res.writeHead(200, { "content-type": MIME[".html"] });
      return res.end(body);
    }

    if (req.method === "GET" && path === "/templates.json") {
      const body = await readFile(join(publicDir, "templates.json"));
      res.writeHead(200, { "content-type": MIME[".json"] });
      return res.end(body);
    }

    if (req.method === "GET" && path === "/config.json") {
      res.writeHead(200, { "content-type": MIME[".json"], "cache-control": "no-store" });
      return res.end(JSON.stringify({ mode, minPick, maxPick, pageCount, title }));
    }

    if (req.method === "GET" && path.startsWith("/static/")) {
      const file = safeJoin(publicDir, path.replace("/static/", ""));
      if (!file || !existsSync(file)) return res.writeHead(404).end("not found");
      const body = await readFile(file);
      res.writeHead(200, { "content-type": MIME[extname(file)] || "application/octet-stream" });
      return res.end(body);
    }

    if (req.method === "GET" && path.startsWith("/refs/")) {
      const file = safeJoin(refsRoot, path.replace("/refs/", ""));
      if (!file || !existsSync(file)) return res.writeHead(404).end("ref not found");
      const body = await readFile(file);
      res.writeHead(200, {
        "content-type": MIME[extname(file)] || "application/octet-stream",
        "cache-control": "public, max-age=3600",
      });
      return res.end(body);
    }

    if (req.method === "POST" && path === "/submit") {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      const selection = {
        templates: Array.isArray(payload.templates) ? payload.templates : [],
        page_count: Number.isFinite(payload.page_count) ? payload.page_count : pageCount,
        mode,
        ts: new Date().toISOString(),
      };
      await mkdir(dirname(outPath), { recursive: true });
      await writeFile(outPath, JSON.stringify(selection, null, 2), "utf8");
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true, out: outPath }));
      console.log("PICKER_OK");
      console.log(`Selection: ${selection.templates.join(", ")}${selection.page_count ? ` · ${selection.page_count} pages` : ""}`);
      setTimeout(() => process.exit(0), 100);
      return;
    }

    res.writeHead(404).end("not found");
  } catch (e) {
    res.writeHead(500, { "content-type": "text/plain" }).end(String(e));
  }
});

server.listen(0, "127.0.0.1", () => {
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/`;
  console.log(`Template picker: ${url}`);
  console.log(`Output:          ${outPath}`);
  if (!existsSync(refsRoot)) {
    console.log(`Warning: reference images not found at ${refsRoot} — thumbnails will be blank.`);
  }
  if (noOpen) {
    console.log("(--no-open: browser not launched)");
    return;
  }
  // Cross-platform browser launch. Windows previously fell through to
  // `xdg-open` (a Linux-only command) and silently failed — the server still
  // ran, but the user had to copy-paste the URL from this log into their
  // browser. The `start ""` form (empty title) is the canonical Windows
  // recipe — `start` interprets the first quoted arg as a console title.
  let cmd, cmdArgs;
  if (process.platform === "darwin") {
    cmd = "open"; cmdArgs = [url];
  } else if (process.platform === "win32") {
    cmd = "cmd"; cmdArgs = ["/c", "start", "", url];
  } else {
    cmd = "xdg-open"; cmdArgs = [url];
  }
  spawn(cmd, cmdArgs, { stdio: "ignore", detached: true, shell: false }).unref();
});
