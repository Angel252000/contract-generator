"use strict";

const $ = (s) => document.querySelector(s);
const paper = $("#paper");
const menu = $("#aiMenu");
const DRAFT_KEY = "contract-generator:draft";
let selectedType = "";
let lastRequest = null;
let savedRange = null;
let busy = false;

// El HTML que entra al editor viene de Markdown generado por la IA: siempre sanitizado.
const toHtml = (md) => DOMPurify.sanitize(marked.parse(md));
const toInlineHtml = (md) => DOMPurify.sanitize(marked.parseInline(md));

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.style.display = "block";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.style.display = "none"), 3500);
}

function setStatus(text) {
  $("#status").textContent = text;
}

// --- Borrador local (solo en este navegador) ---
const storage = {
  get() { try { return localStorage.getItem(DRAFT_KEY); } catch { return null; } },
  set(v) { try { localStorage.setItem(DRAFT_KEY, v); } catch { /* sin almacenamiento */ } },
};
let saveTimer;
function saveDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => storage.set(paper.innerHTML), 400);
}
paper.addEventListener("input", saveDraft);
if (storage.get()) $("#resume").hidden = false;
$("#resume").addEventListener("click", () => {
  paper.innerHTML = DOMPurify.sanitize(storage.get() || "");
  showEditor();
  setStatus("Borrador recuperado");
});

// --- Paso 1: formulario ---
document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    const on = chip.getAttribute("aria-pressed") !== "true";
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
    chip.setAttribute("aria-pressed", String(on));
    selectedType = on ? chip.dataset.type : "";
  }),
);

function collect() {
  const details = {};
  document.querySelectorAll("[data-detail]").forEach((i) => (details[i.dataset.detail] = i.value));
  return { description: $("#description").value, type: selectedType, details };
}

function showEditor() {
  $("#start").hidden = true;
  $("#editorView").hidden = false;
}

function setBusy(value) {
  busy = value;
  ["#generate", "#regen", ...[...document.querySelectorAll("[data-export]")].map((b) => "#" + b.id)]
    .forEach((s) => ($(s).disabled = value));
}

async function generate(req) {
  if (!req.description.trim() && !req.type) {
    toast("Describe el contrato o elige un tipo.");
    return;
  }
  lastRequest = req;
  setBusy(true);
  showEditor();
  setStatus("Redactando…");
  paper.innerHTML = "";
  paper.classList.add("streaming");
  paper.contentEditable = "false";
  let md = "";
  let pending = false;
  const render = () => { paper.innerHTML = toHtml(md); pending = false; };
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `Error ${res.status}`);
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const events = buf.split("\n\n");
      buf = events.pop();
      for (const ev of events) {
        if (!ev.startsWith("data: ")) continue;
        const data = JSON.parse(ev.slice(6));
        if (data.error) throw new Error(data.error);
        if (data.text) {
          md += data.text;
          if (!pending) { pending = true; requestAnimationFrame(render); }
        }
      }
    }
    render();
    setStatus("Borrador listo");
  } catch (err) {
    render();
    setStatus("Error");
    toast(err.message || "No se pudo generar el contrato.");
  } finally {
    paper.classList.remove("streaming");
    paper.contentEditable = "true";
    setBusy(false);
    storage.set(paper.innerHTML);
  }
}

$("#generate").addEventListener("click", () => generate(collect()));
$("#description").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate(collect());
});
$("#regen").addEventListener("click", () => lastRequest ? generate(lastRequest) : generate(collect()));
$("#back").addEventListener("click", () => {
  $("#editorView").hidden = true;
  $("#start").hidden = false;
  $("#resume").hidden = !storage.get();
  menu.style.display = "none";
});

// --- Menú IA sobre la selección ---
document.addEventListener("selectionchange", () => {
  if (busy) return;
  const sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed || !paper.contains(sel.anchorNode) || sel.toString().trim().length < 3) {
    if (!menu.matches(":hover")) menu.style.display = "none";
    return;
  }
  savedRange = sel.getRangeAt(0).cloneRange();
  const rect = savedRange.getBoundingClientRect();
  menu.style.display = "flex";
  const maxLeft = window.scrollX + document.documentElement.clientWidth - menu.offsetWidth - 8;
  const left = Math.min(Math.max(8, rect.left + window.scrollX), maxLeft);
  const top = rect.top + window.scrollY - menu.offsetHeight - 8;
  menu.style.left = left + "px";
  menu.style.top = (top < window.scrollY ? rect.bottom + window.scrollY + 8 : top) + "px";
});

menu.addEventListener("mousedown", (e) => e.preventDefault()); // no perder la selección
menu.querySelectorAll("button").forEach((b) =>
  b.addEventListener("click", async () => {
    if (!savedRange) return;
    const range = savedRange;
    const text = range.toString();
    menu.style.display = "none";
    setBusy(true);
    setStatus("Editando con IA…");
    try {
      const res = await fetch("/api/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, action: b.dataset.action, context: paper.innerText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      range.deleteContents();
      const tpl = document.createElement("template");
      // Varias líneas → bloques Markdown; una línea → texto en línea
      tpl.innerHTML = text.includes("\n") ? toHtml(data.text) : toInlineHtml(data.text);
      range.insertNode(tpl.content);
      window.getSelection().removeAllRanges();
      saveDraft();
      setStatus("Cambio aplicado");
    } catch (err) {
      setStatus("Error");
      toast(err.message || "No se pudo editar el texto.");
    } finally {
      setBusy(false);
      savedRange = null;
    }
  }),
);

// --- Exportar ---
const title = () => paper.querySelector("h1")?.textContent.trim() || "Contrato";
function fileName(ext) {
  const base = title().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return (base || "contrato") + "." + ext;
}
function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function standaloneHtml() {
  const esc = title().replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c]);
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${esc}</title>
<style>body{font:12pt/1.6 Georgia,serif;max-width:760px;margin:40px auto;color:#111}h1{text-align:center;font-size:18pt}h2{font-size:12pt;margin-top:20px}</style>
</head><body>${paper.innerHTML}</body></html>`;
}

$("#dlDocx").addEventListener("click", async () => {
  setStatus("Preparando Word…");
  try {
    const res = await fetch("/api/export/docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html: paper.innerHTML, title: title() }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `Error ${res.status}`);
    download(await res.blob(), fileName("docx"));
    setStatus("Word descargado");
  } catch (err) {
    setStatus("Error");
    toast(err.message || "No se pudo exportar a Word.");
  }
});
$("#dlHtml").addEventListener("click", () => download(new Blob([standaloneHtml()], { type: "text/html" }), fileName("html")));
$("#print").addEventListener("click", () => window.print());
$("#copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(paper.innerText);
    toast("Contrato copiado.");
  } catch {
    toast("No se pudo copiar.");
  }
});
