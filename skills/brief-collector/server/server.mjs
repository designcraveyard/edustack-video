#!/usr/bin/env node
// Localhost brief-collector. Binds 127.0.0.1:0, opens browser, exits cleanly on submit.
//
// Endpoints
//   GET  /                         — form HTML
//   GET  /form-options.json        — dropdown seed values
//   GET  /voices?language=English  — live ElevenLabs voices, scored + sorted
//   GET  /static/<file>            — CSS/JS assets
//   POST /submit                   — writes brief.json and exits
//
// .config lookup: the run dir is `<output>/runs/<run_id>`, so the output root
// is two levels up. From there we read `.config/elevenlabs.key` to authorize
// the GET /v1/voices proxy.

import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
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
const outputRoot = resolve(runDir, "..", "..");           // <output>/runs/<run_id> → <output>
const configDir = join(outputRoot, ".config");
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
  ".svg": "image/svg+xml",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

// ── ElevenLabs proxy with 5-min in-memory cache, language-aware scoring ──────

const VOICES_TTL_MS = 5 * 60 * 1000;
const voicesCache = new Map();   // key = language, value = { ts, voices }

function readElevenLabsKey() {
  const p = join(configDir, "elevenlabs.key");
  if (!existsSync(p)) return null;
  return readFileSync(p, "utf8").trim() || null;
}

// Mirror Edustack's scoring intent: surface region-appropriate accents first.
function scoreVoice(v, language) {
  const labels = Object.values(v.labels || {}).map((s) => String(s).toLowerCase());
  let score = 0;
  const lang = String(language || "").toLowerCase();
  const isIndian = lang === "hindi" || lang === "hinglish" || lang === "tamil" || lang === "bengali" || lang === "marathi";
  if (isIndian) {
    if (labels.some((l) => l.includes("indian"))) score += 100;
    if (labels.some((l) => l.includes("hindi") || l.includes("tamil") || l.includes("bengali") || l.includes("marathi"))) score += 60;
  } else if (lang === "english") {
    if (labels.some((l) => l.includes("american") || l.includes("british"))) score += 40;
  }
  if (labels.some((l) => l.includes("narration") || l.includes("conversational"))) score += 8;
  if (v.preview_url) score += 1;
  return score;
}

async function fetchVoices(language) {
  const key = readElevenLabsKey();
  if (!key) {
    return { error: "no_eleven_key", message: "ElevenLabs key missing at .config/elevenlabs.key" };
  }
  const cached = voicesCache.get(language);
  if (cached && Date.now() - cached.ts < VOICES_TTL_MS) {
    return { voices: cached.voices };
  }
  try {
    const res = await fetch("https://api.elevenlabs.io/v1/voices", {
      headers: { "xi-api-key": key },
    });
    if (!res.ok) {
      return { error: `eleven_${res.status}`, message: (await res.text()).slice(0, 300) };
    }
    const data = await res.json();
    const raw = Array.isArray(data.voices) ? data.voices : [];
    const slim = raw.map((v) => ({
      voice_id: v.voice_id,
      name: v.name,
      preview_url: v.preview_url || "",
      labels: v.labels || {},
    }));
    slim.sort((a, b) => scoreVoice(b, language) - scoreVoice(a, language) || a.name.localeCompare(b.name));
    voicesCache.set(language, { ts: Date.now(), voices: slim });
    return { voices: slim };
  } catch (e) {
    return { error: "transport", message: String(e).slice(0, 300) };
  }
}

// ── HTTP server ──────────────────────────────────────────────────────────────

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
    if (req.method === "GET" && req.url.startsWith("/voices")) {
      const u = new URL(req.url, "http://localhost");
      const language = u.searchParams.get("language") || "English";
      const out = await fetchVoices(language);
      res.writeHead(200, { "content-type": MIME[".json"], "cache-control": "no-store" });
      return res.end(JSON.stringify(out));
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

      // Persist a stable on-disk copy of pasted chapter text so the
      // script-writer has a consistent file to read regardless of input
      // method. URL + file-path kinds are resolved lazily by Phase 1.
      const src = brief.chapter_source;
      if (src && src.kind === "text" && typeof src.ref === "string" && src.ref.trim()) {
        const sourceDir = join(runDir, "source");
        await mkdir(sourceDir, { recursive: true });
        const chapterPath = join(sourceDir, "chapter.txt");
        await writeFile(chapterPath, src.ref, "utf8");
        // Rewrite ref to the on-disk path so phase_script reads a file
        // either way. Keep kind="text" — the script-writer skill knows
        // both forms.
        brief.chapter_source = { kind: "text", ref: chapterPath };
      }

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
  if (!existsSync(join(configDir, "elevenlabs.key"))) {
    console.log("Warning: no ElevenLabs key found at .config/elevenlabs.key — voice list will be empty.");
  }
  // Cross-platform browser launch. See book-template-picker/server.mjs for
  // the rationale — Windows previously fell through to `xdg-open` and silently
  // failed.
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
