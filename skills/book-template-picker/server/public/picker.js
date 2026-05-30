// Book-template picker UI. Vanilla JS, no deps. Renders the gallery from
// /templates.json, enforces the min/max selection from /config.json, and POSTs
// the chosen template ids (+ page count) to /submit. Reference thumbnails come
// from /refs/<path> (served by the server from seed/template-references/).

const galleryEl = document.getElementById("gallery");
const statsEl = document.getElementById("stats");
const obsEl = document.getElementById("observations");
const titleEl = document.getElementById("title");
const statusEl = document.getElementById("sel-status");
const confirmBtn = document.getElementById("confirm");
const pageCountEl = document.getElementById("page-count");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const tPortrait = document.getElementById("t-portrait");
const tLandscape = document.getElementById("t-landscape");

let cfg = { mode: "shortlist", minPick: 2, maxPick: 4, pageCount: 0, title: "Pick your book layouts" };
let orientation = "portrait";
const selected = new Set();

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function refName(ref) {
  return (ref.split("/").pop() || "").replace(/\.jpg$/i, "").replace(/_/g, " ");
}

function renderStats(stats) {
  statsEl.replaceChildren();
  for (const s of stats || []) {
    const cell = el("div", "stat");
    cell.appendChild(el("div", "num", s.number));
    cell.appendChild(el("div", "lab", s.label));
    statsEl.appendChild(cell);
  }
}

function renderObservations(obs) {
  obsEl.replaceChildren();
  for (const o of obs || []) {
    const card = el("div", "obs");
    card.appendChild(el("span", "ico", o.icon));
    card.appendChild(el("h3", null, o.title));
    card.appendChild(el("p", null, o.desc));
    obsEl.appendChild(card);
  }
}

function buildCard(t, index) {
  const card = el("div", "tcard");
  card.dataset.id = t.id;

  card.appendChild(el("div", "bignum", String(index + 1)));

  const check = el("div", "checkdot", "✓");
  card.appendChild(check);

  // ── Info column ──
  const info = el("div", "tinfo");

  const badge = el("span", "badge", t.frequency);
  badge.style.backgroundColor = (t.badgeColor || "#4a8a5a") + "20";
  badge.style.color = t.badgeColor || "#2f6a3f";
  info.appendChild(badge);

  info.appendChild(el("h2", "tname", t.name));
  info.appendChild(el("p", "tnick", t.nickname));
  info.appendChild(el("p", "tdesc", t.description));

  const meta = el("div", "meta-grid");
  const cells = [
    ["Text Position", t.textPosition],
    ["Text Wrapping", t.textWrapping],
    ["Image BG", t.imageBg],
    ["Aspect · Canvas", `${t.aspect} · ${t.canvas}`],
  ];
  for (const [k, v] of cells) {
    const c = el("div", "meta-cell");
    c.appendChild(el("div", "k", k));
    c.appendChild(el("div", "v", v));
    meta.appendChild(c);
  }
  info.appendChild(meta);

  const fb = el("div", "freqbar");
  const fbSpan = el("span");
  fbSpan.style.width = `${t.frequencyPercent || 5}%`;
  fbSpan.style.backgroundColor = t.badgeColor || "#4a8a5a";
  fb.appendChild(fbSpan);
  info.appendChild(fb);

  const tags = el("div", "tags");
  for (const tag of t.tags || []) tags.appendChild(el("span", "tag", tag));
  info.appendChild(tags);

  // Reference images
  const refs = el("div", "refs");
  refs.appendChild(el("div", "refs-label", `Reference images (${(t.refs || []).length})`));
  const row = el("div", "refs-row");
  for (const ref of t.refs || []) {
    const img = new Image();
    img.src = `/refs/${ref}`;
    img.alt = refName(ref);
    img.addEventListener("click", (e) => {
      e.stopPropagation();
      openLightbox(`/refs/${ref}`);
    });
    row.appendChild(img);
  }
  refs.appendChild(row);
  info.appendChild(refs);

  card.appendChild(info);

  // ── Wireframe column ──
  const wire = el("div", "twire");
  const frame = el("div", "frame " + (t.orientation === "portrait" ? "portrait" : "landscape"));
  frame.dataset.tmplOrientation = t.orientation;
  const wf = new Image();
  wf.src = `/static/wireframes/${t.wireframe}`;
  wf.alt = `${t.name} wireframe`;
  frame.appendChild(wf);
  wire.appendChild(frame);
  wire.appendChild(el("div", "cap", `Native: ${t.orientation === "portrait" ? "Portrait A4" : "Landscape A3"}`));
  card.appendChild(wire);

  card.addEventListener("click", () => toggleSelect(t.id, card));

  return card;
}

function toggleSelect(id, card) {
  if (selected.has(id)) {
    selected.delete(id);
    card.classList.remove("selected");
  } else {
    if (selected.size >= cfg.maxPick) {
      flashStatus(`Maximum ${cfg.maxPick} templates. Deselect one first.`);
      return;
    }
    selected.add(id);
    card.classList.add("selected");
  }
  updateStatus();
}

let flashTimer = null;
function flashStatus(msg) {
  statusEl.textContent = msg;
  statusEl.classList.remove("ready");
  clearTimeout(flashTimer);
  flashTimer = setTimeout(updateStatus, 2200);
}

function updateStatus() {
  const n = selected.size;
  const ok = n >= cfg.minPick && n <= cfg.maxPick;
  confirmBtn.disabled = !ok;
  statusEl.classList.toggle("ready", ok);
  if (n < cfg.minPick) statusEl.textContent = `Pick at least ${cfg.minPick} templates (${n} selected).`;
  else if (n > cfg.maxPick) statusEl.textContent = `Too many — maximum ${cfg.maxPick} (${n} selected).`;
  else statusEl.textContent = `${n} selected — ready to confirm.`;
}

function setOrientation(o) {
  orientation = o;
  tPortrait.classList.toggle("active", o === "portrait");
  tLandscape.classList.toggle("active", o === "landscape");
  // The toggle reframes EVERY wireframe panel to the chosen page shape so the
  // user can preview how each layout reads in their target orientation.
  for (const frame of galleryEl.querySelectorAll(".twire .frame")) {
    frame.classList.toggle("portrait", o === "portrait");
    frame.classList.toggle("landscape", o === "landscape");
  }
}

function openLightbox(src) {
  lightboxImg.src = src;
  lightbox.hidden = false;
}
lightbox.addEventListener("click", () => { lightbox.hidden = true; lightboxImg.src = ""; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !lightbox.hidden) { lightbox.hidden = true; lightboxImg.src = ""; } });

tPortrait.addEventListener("click", () => setOrientation("portrait"));
tLandscape.addEventListener("click", () => setOrientation("landscape"));

confirmBtn.addEventListener("click", async () => {
  if (confirmBtn.disabled) return;
  confirmBtn.disabled = true;
  statusEl.classList.remove("ready");
  statusEl.textContent = "Saving…";
  const body = {
    templates: Array.from(selected),
    page_count: parseInt(pageCountEl.value || "0", 10) || 0,
  };
  try {
    const r = await fetch("/submit", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    statusEl.classList.add("ready");
    statusEl.textContent = "Saved. Switch back to Claude — this tab will close.";
    setTimeout(() => window.close(), 1400);
  } catch (err) {
    confirmBtn.disabled = false;
    statusEl.textContent = `Error: ${err.message || err}`;
  }
});

async function init() {
  try { cfg = { ...cfg, ...(await (await fetch("/config.json")).json()) }; } catch {}
  titleEl.textContent = cfg.title;
  if (cfg.pageCount > 0) pageCountEl.value = String(cfg.pageCount);

  let data = { templates: [] };
  try { data = await (await fetch("/templates.json")).json(); } catch (e) {
    statusEl.textContent = "Failed to load templates.";
    return;
  }

  renderStats(data.stats);
  renderObservations(data.observations);
  galleryEl.replaceChildren();
  (data.templates || []).forEach((t, i) => galleryEl.appendChild(buildCard(t, i)));
  setOrientation("portrait");
  updateStatus();
}

init();
