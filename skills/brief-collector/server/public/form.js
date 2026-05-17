const form = document.getElementById("brief");
const status = document.getElementById("status");

const DEFAULT_OPTIONS = {
  class_level: Array.from({length:12}, (_,i) => ({ value: i+1, label: `Class ${i+1}` })),
  language: ["English", "Hindi", "Hinglish", "Tamil", "Bengali", "Marathi"],
  aspect: ["16:9", "9:16", "1:1"],
  style: ["2D animated", "Pixar", "cinematic", "whiteboard", "anime", "stop-motion"],
  duration_seconds: [15, 30, 45, 60, 90, 120],
  ambient_category: [
    { value: "ambient_calm", label: "Calm" },
    { value: "ambient_playful", label: "Playful" },
    { value: "ambient_drama", label: "Drama" },
    { value: "none", label: "No ambient" },
  ],
};

function fillSelect(sel, values) {
  while (sel.firstChild) sel.removeChild(sel.firstChild);
  for (const v of values) {
    const opt = document.createElement("option");
    if (typeof v === "object" && v !== null) {
      opt.value = String(v.value);
      opt.textContent = String(v.label ?? v.value);
    } else {
      opt.value = String(v);
      opt.textContent = String(v);
    }
    sel.appendChild(opt);
  }
}

async function populate() {
  let opts = {};
  try { opts = await (await fetch("/form-options.json")).json(); } catch { opts = {}; }
  for (const sel of form.querySelectorAll("select[data-options]")) {
    const key = sel.dataset.options;
    fillSelect(sel, opts[key] || DEFAULT_OPTIONS[key] || []);
  }
  refreshConditional();
}

function refreshConditional() {
  for (const node of form.querySelectorAll("[data-show-when]")) {
    const [k, v] = node.dataset.showWhen.split("=");
    const field = form[k];
    let current = null;
    if (field instanceof RadioNodeList) {
      current = Array.from(field).find(r => r.checked)?.value;
    } else if (field) {
      current = field.value;
    }
    node.classList.toggle("active", current === v);
  }
}

form.addEventListener("change", refreshConditional);

// ─── Voice combobox ────────────────────────────────────────────────────────
//
// Mirrors Edustack publisher/generate VoiceComboBox behaviour with vanilla JS:
//   - Live fetch from /voices (server proxies ElevenLabs) on language change.
//   - Search input filters; without a query we paginate 10 + 10 on scroll.
//   - Preview play/stop with one shared <audio> element.
//   - The hidden field `voice_id` (and `voice_name`) is what gets submitted.

const PAGE = 10;
const voiceCombo = document.getElementById("voice-combo");
const voiceSearch = document.getElementById("voice-search");
const voicePlay = document.getElementById("voice-play");
const voiceList = document.getElementById("voice-list");
const voiceIdField = document.getElementById("voice-id");
const voiceNameField = document.getElementById("voice-name");
const voiceError = document.getElementById("voice-error");

const audio = new Audio();
let allVoices = [];           // VoiceEntry[]
let displayN = PAGE;
let selectedId = "";
let selectedName = "";
let playingId = null;
let isOpen = false;

audio.addEventListener("ended", () => setPlaying(null));
audio.addEventListener("error", () => setPlaying(null));

function setPlaying(id) {
  playingId = id;
  voicePlay.dataset.playing = id && id === selectedId ? "true" : "false";
  voicePlay.querySelector("span").textContent =
    id && id === selectedId ? "Stop" : "Play";
  // Update per-row indicators
  for (const row of voiceList.querySelectorAll(".voice-row")) {
    const rowId = row.dataset.voiceId;
    const btn = row.querySelector(".voice-row-play");
    if (btn) {
      btn.dataset.playing = rowId === id ? "true" : "false";
      btn.querySelector("span").textContent = rowId === id ? "Stop" : "Play";
    }
  }
}

function togglePreview(voice) {
  if (!voice?.preview_url) return;
  if (playingId === voice.voice_id) {
    audio.pause();
    setPlaying(null);
    return;
  }
  audio.src = voice.preview_url;
  audio.play().then(() => setPlaying(voice.voice_id)).catch(() => setPlaying(null));
}

function selectVoice(v) {
  selectedId = v.voice_id;
  selectedName = v.name;
  voiceIdField.value = v.voice_id;
  voiceNameField.value = v.name;
  voiceSearch.value = v.name;
  renderList();
}

function isSearching() {
  const q = (voiceSearch.value || "").trim().toLowerCase();
  return q.length > 0 && q !== selectedName.toLowerCase();
}

function filteredVoices() {
  if (!isSearching()) return allVoices;
  const q = voiceSearch.value.trim().toLowerCase();
  return allVoices.filter((v) =>
    v.name.toLowerCase().includes(q) ||
    Object.values(v.labels || {}).some((l) => String(l || "").toLowerCase().includes(q))
  );
}

function renderList() {
  while (voiceList.firstChild) voiceList.removeChild(voiceList.firstChild);

  if (!isOpen) {
    voiceList.hidden = true;
    return;
  }
  voiceList.hidden = false;

  const filtered = filteredVoices();
  if (filtered.length === 0) {
    const div = document.createElement("div");
    div.className = "voice-list-empty";
    div.textContent = isSearching()
      ? `No voices match “${voiceSearch.value}”.`
      : (allVoices.length === 0 ? "No voices available." : "No matches.");
    voiceList.appendChild(div);
    return;
  }

  const slice = isSearching() ? filtered : filtered.slice(0, displayN);

  for (const v of slice) {
    const row = document.createElement("div");
    row.className = "voice-row";
    row.dataset.voiceId = v.voice_id;
    row.role = "option";
    row.dataset.active = v.voice_id === selectedId ? "true" : "false";

    const info = document.createElement("div");
    info.className = "voice-row-info";
    const nameEl = document.createElement("div");
    nameEl.className = "voice-row-name";
    nameEl.textContent = v.name;
    info.appendChild(nameEl);
    const labelParts = Object.values(v.labels || {}).filter(Boolean).slice(0, 3);
    if (labelParts.length) {
      const lab = document.createElement("div");
      lab.className = "voice-row-labels";
      lab.textContent = labelParts.join(" · ");
      info.appendChild(lab);
    }
    row.appendChild(info);

    if (v.preview_url) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "voice-row-play";
      btn.dataset.playing = playingId === v.voice_id ? "true" : "false";
      const icon = document.createElement("span");
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "▶";
      const text = document.createElement("span");
      text.textContent = playingId === v.voice_id ? "Stop" : "Play";
      btn.appendChild(icon);
      btn.appendChild(text);
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        togglePreview(v);
      });
      row.appendChild(btn);
    }

    row.addEventListener("mousedown", (e) => e.preventDefault()); // keep input focused
    row.addEventListener("click", () => {
      selectVoice(v);
      closeList();
    });
    voiceList.appendChild(row);
  }

  // Sentinel
  if (!isSearching() && displayN < filtered.length) {
    const more = document.createElement("div");
    more.className = "voice-list-empty";
    more.textContent = `${filtered.length - displayN} more — scroll to load`;
    voiceList.appendChild(more);
  }
}

function openList() {
  isOpen = true;
  renderList();
}

function closeList() {
  isOpen = false;
  voiceSearch.value = selectedName || "";
  renderList();
  voiceSearch.blur();
}

voiceSearch.addEventListener("focus", () => openList());
voiceSearch.addEventListener("input", () => {
  displayN = PAGE;
  if (!isOpen) openList(); else renderList();
});
voiceList.addEventListener("scroll", () => {
  if (isSearching()) return;
  if (voiceList.scrollTop + voiceList.clientHeight >= voiceList.scrollHeight - 80) {
    displayN += PAGE;
    renderList();
  }
});
document.addEventListener("mousedown", (e) => {
  if (!voiceCombo.contains(e.target)) closeList();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && isOpen) closeList();
});

voicePlay.addEventListener("click", () => {
  const v = allVoices.find((x) => x.voice_id === selectedId);
  if (v) togglePreview(v);
});

async function loadVoicesFor(language) {
  voiceError.hidden = true;
  voiceError.textContent = "";
  voiceSearch.placeholder = "Loading voices…";
  voiceSearch.value = "";
  selectedId = "";
  selectedName = "";
  voiceIdField.value = "";
  voiceNameField.value = "";
  allVoices = [];
  displayN = PAGE;
  renderList();

  try {
    const r = await fetch(`/voices?language=${encodeURIComponent(language)}`);
    const data = await r.json();
    if (data.error) {
      voiceError.hidden = false;
      voiceError.textContent = `Voices: ${data.error}${data.message ? ` — ${data.message}` : ""}`;
      voiceSearch.placeholder = "Voices unavailable";
      return;
    }
    allVoices = Array.isArray(data.voices) ? data.voices : [];
    if (allVoices.length > 0) {
      selectVoice(allVoices[0]);
      voiceSearch.placeholder = "Search voices…";
    } else {
      voiceSearch.placeholder = "No voices found";
    }
  } catch (e) {
    voiceError.hidden = false;
    voiceError.textContent = `Voices fetch failed: ${e.message || e}`;
    voiceSearch.placeholder = "Voices unavailable";
  }
}

const langSelect = form.querySelector("select[name=language]");
langSelect.addEventListener("change", () => loadVoicesFor(langSelect.value));

// ── Submit ─────────────────────────────────────────────────────────────────

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  status.textContent = "Saving…";
  const fd = new FormData(form);
  const brief = {
    topic: fd.get("topic"),
    class_level: Number(fd.get("class_level")),
    language: fd.get("language"),
    style: fd.get("style"),
    aspect: fd.get("aspect"),
    script_mode: fd.get("script_mode"),
    duration_seconds: fd.get("script_mode") === "standard" ? Number(fd.get("duration_seconds")) : null,
    chapter_source: fd.get("script_mode") === "word_to_word"
      ? { kind: fd.get("chapter_text") ? "text" : fd.get("chapter_url") ? "url" : "file",
          ref: fd.get("chapter_text") || fd.get("chapter_url") || (fd.get("chapter_file")?.name ?? null) }
      : null,
    character_mode: fd.get("character_mode"),
    image_mode: fd.get("image_mode"),
    ambient_category: fd.get("ambient_category"),
    subtitles_enabled: form.subtitles_enabled.checked,
    annotations_enabled: form.annotations_enabled.checked,
    voice_id: fd.get("voice_id"),
    voice_name: fd.get("voice_name"),
    notes: fd.get("notes") || "",
  };
  try {
    const r = await fetch("/submit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(brief) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    status.textContent = "Saved. Switch back to Claude — this tab will close.";
    setTimeout(() => window.close(), 1500);
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
});

// ── Init ───────────────────────────────────────────────────────────────────

await populate();
await loadVoicesFor(langSelect.value || "English");
