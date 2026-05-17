const form = document.getElementById("brief");
const status = document.getElementById("status");

const DEFAULT_OPTIONS = {
  class_level: Array.from({length:12}, (_,i) => ({ value: i+1, label: `Class ${i+1}` })),
  language: ["English", "Hindi", "Tamil", "Telugu", "Bengali"],
  aspect: ["16:9", "9:16", "1:1"],
  style: ["2D animated", "Pixar", "cinematic", "whiteboard", "anime", "stop-motion"],
  voice_id: [{ value: "21m00Tcm4TlvDq8ikWAM", label: "Rachel (en, calm)" }],
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

populate();
