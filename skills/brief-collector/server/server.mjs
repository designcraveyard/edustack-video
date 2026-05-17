#!/usr/bin/env node
// Localhost brief-collector. Binds 127.0.0.1:0, opens browser, exits cleanly on submit.
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve, dirname, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));

const args = Object.fromEntries(
  process.argv.slice(2).reduce((a, v, i, arr) => {
    if (v.startsWith("--")) a.push([v.slice(2), arr[i + 1]]);
    return a;
  }, [])
);
const runDir = resolve(args["run-dir"] || process.cwd());
const pluginRoot = resolve(__dirname, "..", "..", "..");
await mkdir(runDir, { recursive: true });

const formOptionsPath = join(pluginRoot, "seed", "form-options.json");
const formOptions = existsSync(formOptionsPath)
  ? JSON.parse(await readFile(formOptionsPath, "utf8"))
  : {};

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "application/javascript",
  ".json": "application/json",
};

const server = createServer(async (req, res) => {
  try {
    if (req.method === "GET" && (req.url === "/" || req.url === "/index.html")) {
      const body = await readFile(join(__dirname, "public", "index.html"));
      res.writeHead(200, { "content-type": MIME[".html"] });
      return res.end(body);
    }
    if (req.method === "GET" && req.url === "/form-options.json") {
      res.writeHead(200, { "content-type": MIME[".json"] });
      return res.end(JSON.stringify(formOptions));
    }
    if (req.method === "GET" && req.url.startsWith("/static/")) {
      const file = join(__dirname, "public", req.url.replace("/static/", ""));
      const body = await readFile(file);
      res.writeHead(200, { "content-type": MIME[extname(file)] || "application/octet-stream" });
      return res.end(body);
    }
    if (req.method === "POST" && req.url === "/submit") {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const brief = JSON.parse(Buffer.concat(chunks).toString("utf8"));
      await writeFile(join(runDir, "brief.json"), JSON.stringify(brief, null, 2));
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
      console.log("BRIEF_OK");
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
  console.log(`Brief UI: ${url}`);
  console.log(`Output:   ${runDir}/brief.json`);
  const opener = process.platform === "darwin" ? "open" : "xdg-open";
  spawn(opener, [url], { stdio: "ignore", detached: true }).unref();
});
