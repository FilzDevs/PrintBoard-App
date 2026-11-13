/* ============================================================================
   PrintBoard Studio 1.0 — Core Application Engine (Easy & Advanced Mode)
   Zero-dependency reactive SPA + HTML5 Canvas Telemetry, Bed Mesh 2D/3D,
   Exclude Object Map, G-Code Layer Visualizer & Quote Calculator.
   ============================================================================ */

const STATE_LABELS = {
  printing: "Druck läuft",
  paused: "Pausiert",
  complete: "Fertig",
  error: "Fehler",
  cancelled: "Abgebrochen",
  standby: "Bereit",
  offline: "Offline",
};

const STATE_COLORS = {
  printing: "#00E5FF",
  paused: "#F59E0B",
  complete: "#10B981",
  error: "#F43F5E",
  cancelled: "#FB923C",
  standby: "#10B981",
  offline: "#64748B",
};

const CHART_PALETTE = [
  "#00E5FF", "#8B5CF6", "#F59E0B", "#10B981", "#F43F5E", "#3B82F6", "#EC4899"
];

const MODEL_SITES = [
  { name: "Printables", url: "https://www.printables.com", desc: "Prusa Community-Plattform mit Wettbewerben & geprüften Profilen", color: "#FA6831", tag: "TOP" },
  { name: "MakerWorld", url: "https://makerworld.com", desc: "Bambu Lab Ökosystem mit 3MF-Druckprofilen & Punktesystem", color: "#10B981", tag: "3MF" },
  { name: "Thingiverse", url: "https://www.thingiverse.com", desc: "Das größte klassische Archiv für Open-Source 3D-Modelle", color: "#3B82F6", tag: "KLASSIKER" },
  { name: "Thangs", url: "https://thangs.com", desc: "Geometrische 3D-Suchmaschine über alle großen Plattformen", color: "#8B5CF6", tag: "META-SUCHE" },
  { name: "MyMiniFactory", url: "https://www.myminifactory.com", desc: "Kuratierte Tabletop-, Gaming- & Design-Objekte", color: "#06B6D4", tag: "KURATIERT" },
  { name: "Cults3D", url: "https://cults3d.com", desc: "Unabhängiger Marktplatz für Designer, Art-Toys & Gadgets", color: "#EC4899", tag: "DESIGN" },
];

// Crisp inline SVG icons
const ICONS = {
  printers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 17h10"/><rect x="9" y="6" width="6" height="4" rx="1"/><path d="M12 10v3"/></svg>',
  gcode: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
  spool: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="3" x2="12" y2="9"/><line x1="12" y1="15" x2="12" y2="21"/></svg>',
  queue: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><polygon points="4 4 7 6 4 8 4 4" fill="currentColor"/><circle cx="5" cy="12" r="1.5"/><circle cx="5" cy="18" r="1.5"/></svg>',
  camera: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="14" height="12" rx="2"/><polygon points="22 7 16 12 22 17 22 7"/></svg>',
  maintenance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
  stats: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>',
  library: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
  globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>',
  flame: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
  bolt: '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  sparkle: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>',
};

// Global Application Store
const App = {
  state: {
    mode: "easy",          // "easy" | "advanced"
    theme: "obsidian",     // "obsidian" | "carbon" | "amethyst" | "light"
    controls_enabled: true,
    sim_enabled: true,
    auto_dispatch: false,
    autostart: false,
    is_desktop: false,
    printers: [],
    statuses: {},
    temp_history: {},
    spools: [],
    filaments: [],
    vendors: [],
    locations: [],
    materials: [],
    spoolman_url: "",
    spoolman_connected: false,
    drying_presets: [],
    drying_timers: [],
    queue: [],
    maintenance: {},
    maintenance_tasks: [],
    printer_hours: {},
    models_dir: "",
    slicer_cmd: "",
    detected_slicers: [],
    notify_cfg: {},
    cost_rates: { eur_kg: 24, kwh: 0.30, watts: 150, wear: 0.15, labor_h: 25, margin_pct: 35, fail_pct: 8, vat_pct: 19 },
  },
  ui: {
    view: "dashboard",          // dashboard | detail | gcode | spoolman | queue | cameras | maintenance | stats | library | discover | settings
    selectedPrinterId: null,
    detailTab: "cockpit",       // cockpit | motion | exclude | bedmesh | files | console
    printerDetails: { files: [], macros: [], console: [] },
    jogStep: 10,
    bedMesh3D: true,
    spoolTab: "spools",         // spools | filaments | drying | server
    spoolSearch: "",
    spoolMatFilter: "all",
    statsTab: "analytics",      // analytics | quote
    historyData: null,
    quoteForm: { grams: 65, hours: 2.5, copies: 1, prep_mins: 10, waste_pct: 5, file_name: "" },
    quoteResult: null,
    libraryData: { files: [], subfolders: [], models_dir: "" },
    libQuery: "",
    libCat: "all",
    libSub: "",
    selectedLibPath: null,
    gcodeData: null,
    gcodeLayerIdx: 0,
    gcodeIso: false,
    gcodeShowTravel: true,
    gcodePlaying: false,
    gcodeAnimTimer: null,
    camsList: [],
    camsFitCover: false,
    maintPrinterId: null,
    modal: null,                // null | { type, data }
    cmdOpen: false,
    cmdQuery: "",
  },

  async apiGet(url) {
    const r = await fetch(url);
    return await r.json();
  },

  async apiPost(url, data = {}) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await r.json();
  },

  toast(msg, kind = "info") {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = "toast-item";
    const col = kind === "error" ? "var(--danger)" : (kind === "ok" ? "var(--ok)" : "var(--accent)");
    el.style.borderLeftColor = col;
    el.innerHTML = `<span style="color:${col};font-weight:900">●</span> <span>${esc(msg)}</span>`;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.25s ease";
      setTimeout(() => el.remove(), 260);
    }, 3600);
  },
};

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtHms(sec) {
  if (sec === null || sec === undefined || sec <= 0) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m} min`;
}

function fmtTemp(v) {
  return v === null || v === undefined ? "—" : Number(v).toFixed(1);
}

function spoolName(sp) {
  if (!sp) return "Keine Spule";
  const fil = sp.filament || {};
  const v = (fil.vendor || {}).name || "";
  const n = fil.name || "Filament";
  const m = fil.material ? ` [${fil.material}]` : "";
  return `#${sp.id} ${v ? v + " " : ""}${n}${m}`;
}

function spoolColor(sp) {
  if (!sp) return "#64748B";
  const fil = sp.filament || sp;
  const hex = String(fil.color_hex || "06B6D4").replace("#", "");
  return "#" + hex.slice(0, 6);
}

function renderRadialGaugeSVG(progress, color, label, sublabel, thumbB64, size = 86) {
  const pct = Math.max(0, Math.min(1, Number(progress || 0)));
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct);
  const clipId = "clip_" + Math.random().toString(36).slice(2, 8);
  const imgLayer = thumbB64
    ? `<defs><clipPath id="${clipId}"><circle cx="${size / 2}" cy="${size / 2}" r="${r - 4}"/></clipPath></defs>
       <image href="${thumbB64}" x="8" y="8" width="${size - 16}" height="${size - 16}" clip-path="url(#${clipId})" preserveAspectRatio="xMidYMid slice" opacity="0.38"/>
       <circle cx="${size / 2}" cy="${size / 2}" r="${r - 4}" fill="rgba(5,8,15,0.55)"/>`
    : "";
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="flex-shrink:0">
      ${imgLayer}
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--bg-elevated-2)" stroke-width="5.5"/>
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="5.5"
        stroke-linecap="round" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"
        transform="rotate(-90 ${size / 2} ${size / 2})" style="transition: stroke-dashoffset 0.45s ease"/>
      <text x="50%" y="47%" text-anchor="middle" fill="var(--text-main)" font-size="${size >= 90 ? 15 : 13}" font-weight="800">${esc(label)}</text>
      <text x="50%" y="66%" text-anchor="middle" fill="${color}" font-size="7.5" font-weight="800">${esc(String(sublabel || "").slice(0, 10).toUpperCase())}</text>
    </svg>
  `;
}

/* ============================================================================
   Canvas Renderers (Thermal Chart, Donut Chart, Monthly Bar, Bed Mesh, Exclude Object, G-Code Viewer)
   ============================================================================ */

function drawThermalCanvas(canvasId, seriesMap, targetsMap = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padL = 40, padR = 14, padT = 28, padB = 20;
  const cw = Math.max(40, w - padL - padR);
  const ch = Math.max(30, h - padT - padB);

  ctx.clearRect(0, 0, w, h);

  let maxTemp = 260;
  const entries = Object.entries(seriesMap || {});
  entries.forEach(([, pts]) => {
    pts.forEach((v) => { if (v + 20 > maxTemp) maxTemp = v + 20; });
  });
  maxTemp = Math.min(320, Math.ceil(maxTemp / 50) * 50);

  // Grid lines
  ctx.font = "600 10px Inter, sans-serif";
  [0, 0.5, 1].forEach((f) => {
    const gy = padT + ch * (1 - f);
    ctx.strokeStyle = "rgba(148, 163, 184, 0.14)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, gy);
    ctx.lineTo(w - padR, gy);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#64748B";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round(f * maxTemp)}°`, padL - 6, gy + 3);
  });

  if (!entries.length) {
    ctx.fillStyle = "#64748B";
    ctx.textAlign = "center";
    ctx.font = "500 12px Inter, sans-serif";
    ctx.fillText("Warte auf Live-Temperaturdaten …", padL + cw / 2, padT + ch / 2);
    return;
  }

  let legX = w - padR;
  entries.slice(0, 6).forEach(([name, pts], idx) => {
    if (!pts || !pts.length) return;
    const col = CHART_PALETTE[idx % CHART_PALETTE.length];
    const cur = pts[pts.length - 1];
    const tgt = targetsMap[name] || 0;

    // Legend item
    const lbl = `${name}: ${cur.toFixed(1)}°C${tgt > 0 ? ` / ${tgt.toFixed(0)}°` : ""}`;
    ctx.font = "700 10.5px Inter, sans-serif";
    const tw = ctx.measureText(lbl).width + 18;
    legX -= tw;
    if (legX > 10) {
      ctx.fillStyle = col;
      ctx.fillRect(legX, 8, 8, 8);
      ctx.textAlign = "left";
      ctx.fillText(lbl, legX + 12, 16);
    }

    // Target line
    if (tgt > 0) {
      const ty = padT + ch * (1 - Math.min(1, tgt / maxTemp));
      ctx.strokeStyle = col;
      ctx.globalAlpha = 0.45;
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(padL, ty);
      ctx.lineTo(w - padR, ty);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // Curve + Gradient fill
    const n = pts.length;
    ctx.beginPath();
    pts.forEach((v, i) => {
      const px = padL + cw * (n === 1 ? 1 : i / (Math.max(20, n) - 1));
      const py = padT + ch * (1 - Math.max(0, Math.min(1, v / maxTemp)));
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = col;
    ctx.lineWidth = 2.2;
    ctx.stroke();

    const lastX = padL + cw * (n === 1 ? 1 : (n - 1) / (Math.max(20, n) - 1));
    ctx.lineTo(lastX, padT + ch);
    ctx.lineTo(padL, padT + ch);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, padT, 0, padT + ch);
    grad.addColorStop(0, col + "38");
    grad.addColorStop(1, col + "00");
    ctx.fillStyle = grad;
    ctx.fill();
  });
}

function drawDonutCanvas(canvasId, segments, centerTop, centerSub) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const valid = (segments || []).filter((s) => s.value > 0);
  const total = valid.reduce((a, b) => a + b.value, 0);
  const r = Math.min(h * 0.38, 46);
  const cx = r + 16;
  const cy = h / 2;

  if (total <= 0) {
    ctx.strokeStyle = "rgba(148,163,184,0.2)";
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#64748B";
    ctx.font = "500 12px Inter, sans-serif";
    ctx.fillText("Keine Daten", cx + r + 20, cy + 4);
    return;
  }

  let angle = -Math.PI / 2;
  valid.forEach((seg) => {
    const span = (seg.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, angle, angle + span);
    ctx.strokeStyle = seg.color;
    ctx.lineWidth = 11;
    ctx.stroke();
    angle += span;
  });

  ctx.fillStyle = "var(--text-main)";
  ctx.textAlign = "center";
  ctx.font = "800 13px Inter, sans-serif";
  ctx.fillStyle = "#F8FAFC";
  ctx.fillText(centerTop || "", cx, cy + 1);
  if (centerSub) {
    ctx.fillStyle = "#94A3B8";
    ctx.font = "800 8px Inter, sans-serif";
    ctx.fillText(centerSub, cx, cy + 13);
  }

  // Legend
  const lx = cx + r + 20;
  let ly = Math.max(18, cy - (valid.slice(0, 5).length * 20) / 2 + 8);
  valid.slice(0, 5).forEach((seg) => {
    ctx.fillStyle = seg.color;
    ctx.beginPath();
    ctx.roundRect(lx, ly - 8, 9, 9, 2.5);
    ctx.fill();

    ctx.fillStyle = "#CBD5E1";
    ctx.font = "600 11.5px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(String(seg.label).slice(0, 16), lx + 14, ly);

    ctx.fillStyle = seg.color;
    ctx.font = "700 11.5px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(seg.unit || String(seg.value), w - 6, ly);
    ly += 21;
  });
}

function drawBedMeshCanvas(canvasId, bedMesh, is3D = true) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !bedMesh || !bedMesh.probed_matrix) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const mat = bedMesh.probed_matrix;
  const rows = mat.length;
  const cols = mat[0].length;
  const minV = bedMesh.min_val ?? -0.1;
  const maxV = bedMesh.max_val ?? 0.1;
  const span = Math.max(0.02, maxV - minV);

  function heightColor(v) {
    const t = Math.max(0, Math.min(1, (v - minV) / span));
    // Cool Blue -> Emerald Green (0) -> Warm Amber -> Crimson Red
    if (t < 0.35) {
      const k = t / 0.35;
      return `rgb(${Math.round(6 + k * 10)}, ${Math.round(130 + k * 55)}, ${Math.round(240 - k * 110)})`;
    } else if (t < 0.65) {
      const k = (t - 0.35) / 0.3;
      return `rgb(${Math.round(16 + k * 229)}, ${Math.round(185 - k * 27)}, ${Math.round(129 - k * 118)})`;
    } else {
      const k = (t - 0.65) / 0.35;
      return `rgb(244, ${Math.round(158 - k * 95)}, ${Math.round(11 + k * 83)})`;
    }
  }

  if (!is3D) {
    // 2D Heatmap with millimeter cell readouts
    const pad = 28;
    const cw = (w - pad * 2) / cols;
    const ch = (h - pad * 2) / rows;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const val = mat[rows - 1 - r][c];
        const x = pad + c * cw;
        const y = pad + r * ch;
        ctx.fillStyle = heightColor(val);
        ctx.fillRect(x + 1, y + 1, cw - 2, ch - 2);
        ctx.fillStyle = "#040810";
        ctx.font = "800 10px JetBrains Mono, monospace";
        ctx.textAlign = "center";
        ctx.fillText((val >= 0 ? "+" : "") + val.toFixed(3), x + cw / 2, y + ch / 2 + 4);
      }
    }
    return;
  }

  // 3D Isometric Surface Plot
  const cx = w * 0.5;
  const cy = h * 0.56;
  const scaleX = Math.min(w, h) * 0.52 / Math.max(rows, cols);
  const scaleY = scaleX * 0.52;
  const zScale = 240;

  function project(r, c, z) {
    const nr = r - (rows - 1) / 2;
    const nc = c - (cols - 1) / 2;
    const px = cx + (nc - nr) * scaleX;
    const py = cy + (nc + nr) * scaleY - z * zScale;
    return [px, py];
  }

  // Draw reference zero plane
  ctx.strokeStyle = "rgba(0, 229, 255, 0.22)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const [z0x, z0y] = project(0, 0, 0);
  const [z1x, z1y] = project(0, cols - 1, 0);
  const [z2x, z2y] = project(rows - 1, cols - 1, 0);
  const [z3x, z3y] = project(rows - 1, 0, 0);
  ctx.moveTo(z0x, z0y); ctx.lineTo(z1x, z1y); ctx.lineTo(z2x, z2y); ctx.lineTo(z3x, z3y); ctx.closePath();
  ctx.stroke();

  // Draw quads back-to-front
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const v00 = mat[r][c];
      const v01 = mat[r][c + 1];
      const v11 = mat[r + 1][c + 1];
      const v10 = mat[r + 1][c];
      const avg = (v00 + v01 + v11 + v10) / 4;

      const [p0x, p0y] = project(r, c, v00);
      const [p1x, p1y] = project(r, c + 1, v01);
      const [p2x, p2y] = project(r + 1, c + 1, v11);
      const [p3x, p3y] = project(r + 1, c, v10);

      ctx.beginPath();
      ctx.moveTo(p0x, p0y);
      ctx.lineTo(p1x, p1y);
      ctx.lineTo(p2x, p2y);
      ctx.lineTo(p3x, p3y);
      ctx.closePath();
      ctx.fillStyle = heightColor(avg);
      ctx.globalAlpha = 0.84;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "rgba(5, 8, 15, 0.65)";
      ctx.lineWidth = 1.1;
      ctx.stroke();
    }
  }
}

function drawExcludeObjectCanvas(canvasId, eoData) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !eoData) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const pad = 24;
  const plateSize = Math.min(w - pad * 2, h - pad * 2);
  const ox = (w - plateSize) / 2;
  const oy = (h - plateSize) / 2;
  const bedMax = 350.0;

  // Build plate background + grid
  ctx.fillStyle = "#080D16";
  ctx.strokeStyle = "rgba(0, 229, 255, 0.35)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(ox, oy, plateSize, plateSize, 10);
  ctx.fill();
  ctx.stroke();

  ctx.strokeStyle = "rgba(148, 163, 184, 0.1)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 7; i++) {
    const gx = ox + (plateSize * i) / 7;
    const gy = oy + (plateSize * i) / 7;
    ctx.beginPath(); ctx.moveTo(gx, oy); ctx.lineTo(gx, oy + plateSize); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(ox, gy); ctx.lineTo(ox + plateSize, gy); ctx.stroke();
  }

  const excluded = new Set(eoData.excluded_objects || []);
  const current = eoData.current_object;

  (eoData.objects || []).forEach((obj) => {
    const isEx = excluded.has(obj.name);
    const isCur = obj.name === current && !isEx;
    const poly = obj.polygon || [];
    if (poly.length >= 3) {
      ctx.beginPath();
      poly.forEach(([x, y], i) => {
        const px = ox + (x / bedMax) * plateSize;
        const py = oy + plateSize - (y / bedMax) * plateSize;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fillStyle = isEx ? "rgba(244, 63, 94, 0.18)" : (isCur ? "rgba(0, 229, 255, 0.28)" : "rgba(16, 185, 129, 0.18)");
      ctx.fill();
      ctx.strokeStyle = isEx ? "#F43F5E" : (isCur ? "#00E5FF" : "#10B981");
      ctx.lineWidth = isCur ? 2.5 : 1.5;
      ctx.stroke();
    }
    const [cx, cy] = obj.center || [175, 175];
    const px = ox + (cx / bedMax) * plateSize;
    const py = oy + plateSize - (cy / bedMax) * plateSize;
    ctx.fillStyle = "#F8FAFC";
    ctx.font = "700 10.5px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(obj.name.slice(0, 20), px, py + 4);
  });
}

function drawGcodeLayerCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  const gd = App.ui.gcodeData;
  if (!canvas || !gd || !gd.layers || !gd.layers.length) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 20) return;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  ctx.clearRect(0, 0, w, h);

  const [minX, minY, maxX, maxY] = gd.bbox || [50, 50, 200, 200];
  const spanX = Math.max(20, maxX - minX);
  const spanY = Math.max(20, maxY - minY);
  const pad = 32;
  const scale = Math.min((w - pad * 2) / spanX, (h - pad * 2) / spanY);
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  const idx = Math.max(0, Math.min(gd.layers.length - 1, App.ui.gcodeLayerIdx));
  const iso = App.ui.gcodeIso;

  function toScreen(x, y, z = 0) {
    const dx = (x - cx) * scale;
    const dy = (y - cy) * scale;
    if (!iso) {
      return [w / 2 + dx, h / 2 - dy];
    }
    const isoX = (dx - dy) * 0.72;
    const isoY = (dx + dy) * 0.38 - z * 2.2;
    return [w / 2 + isoX, h * 0.62 + isoY];
  }

  // Draw subtle ghost of previous 3 layers for depth perception
  const startGhost = Math.max(0, idx - (iso ? 6 : 2));
  for (let l = startGhost; l < idx; l++) {
    const lay = gd.layers[l];
    ctx.strokeStyle = "rgba(59, 130, 246, 0.16)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    lay.segments.forEach(([x1, y1, x2, y2, isExt]) => {
      if (!isExt) return;
      const [sx1, sy1] = toScreen(x1, y1, lay.z);
      const [sx2, sy2] = toScreen(x2, y2, lay.z);
      ctx.moveTo(sx1, sy1);
      ctx.lineTo(sx2, sy2);
    });
    ctx.stroke();
  }

  // Active layer
  const activeLayer = gd.layers[idx];
  if (!activeLayer) return;

  if (App.ui.gcodeShowTravel) {
    ctx.strokeStyle = "rgba(245, 158, 11, 0.35)";
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    activeLayer.segments.forEach(([x1, y1, x2, y2, isExt]) => {
      if (isExt) return;
      const [sx1, sy1] = toScreen(x1, y1, activeLayer.z);
      const [sx2, sy2] = toScreen(x2, y2, activeLayer.z);
      ctx.moveTo(sx1, sy1);
      ctx.lineTo(sx2, sy2);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.strokeStyle = "#00E5FF";
  ctx.lineWidth = 2.2;
  ctx.lineCap = "round";
  ctx.beginPath();
  let lastPt = null;
  activeLayer.segments.forEach(([x1, y1, x2, y2, isExt]) => {
    if (!isExt) return;
    const [sx1, sy1] = toScreen(x1, y1, activeLayer.z);
    const [sx2, sy2] = toScreen(x2, y2, activeLayer.z);
    ctx.moveTo(sx1, sy1);
    ctx.lineTo(sx2, sy2);
    lastPt = [sx2, sy2];
  });
  ctx.stroke();

  if (lastPt) {
    ctx.fillStyle = "#10B981";
    ctx.beginPath();
    ctx.arc(lastPt[0], lastPt[1], 4.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

/* ============================================================================
   Actions & Backend Dispatchers
   ============================================================================ */

async function setMode(mode) {
  App.state.mode = mode;
  renderAll();
  await App.apiPost("/api/mode", { mode });
  App.toast(mode === "easy" ? "Easy Mode aktiviert — Fokus auf 1-Klick Bedienung" : "Advanced Pro Mode aktiviert — Volle Telemetrie & Farm-Steuerung", "ok");
}

async function setTheme(theme) {
  App.state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  await App.apiPost("/api/mode", { theme });
}

async function toggleSimMode(enabled) {
  App.state.sim_enabled = enabled;
  const res = await App.apiPost("/api/mode", { sim_enabled: enabled });
  if (res.state) Object.assign(App.state, res.state);
  renderAll();
  App.toast(enabled ? "Virtueller Demo-Fuhrpark zugeschaltet" : "Virtueller Demo-Fuhrpark ausgeblendet", "ok");
}

function navigate(view, printerId = null) {
  if (App.ui.gcodeAnimTimer) {
    clearInterval(App.ui.gcodeAnimTimer);
    App.ui.gcodeAnimTimer = null;
    App.ui.gcodePlaying = false;
  }
  App.ui.view = view;
  if (printerId !== null) {
    App.ui.selectedPrinterId = printerId;
  }
  renderAll();
  if (view === "detail" && App.ui.selectedPrinterId) {
    loadPrinterDetails(App.ui.selectedPrinterId);
  } else if (view === "library") {
    loadLibrary();
  } else if (view === "gcode" && !App.ui.gcodeData) {
    loadGcodePreview({});
  } else if (view === "stats") {
    loadHistoryStats();
    calculateQuoteNow();
  } else if (view === "cameras") {
    loadWebcams();
  } else if (view === "maintenance") {
    loadHistoryStats();
  }
}

async function sendControl(printerId, action, params = {}) {
  const res = await App.apiPost("/api/control", { printer_id: printerId, action, params });
  if (res.error) {
    App.toast("Fehler: " + res.error, "error");
  } else {
    App.toast(`Befehl '${action}' ausgeführt`, "ok");
    await pollState();
    if (App.ui.view === "detail" && App.ui.selectedPrinterId === printerId) {
      loadPrinterDetails(printerId);
    }
  }
}

async function sendBatchControl(batch, action, params = {}) {
  const res = await App.apiPost("/api/control", { batch, action, params });
  if (res.error) {
    App.toast("Fehler: " + res.error, "error");
  } else {
    App.toast(`Flotten-Befehl (${batch}) ausgeführt`, "ok");
    await pollState();
  }
}

async function loadPrinterDetails(pid) {
  const res = await App.apiGet(`/api/printer/details?printer_id=${encodeURIComponent(pid)}`);
  App.ui.printerDetails = res || { files: [], macros: [], console: [] };
  if (App.ui.view === "detail") renderContent();
}

async function loadLibrary() {
  const q = encodeURIComponent(App.ui.libQuery || "");
  const c = encodeURIComponent(App.ui.libCat || "all");
  const s = encodeURIComponent(App.ui.libSub || "");
  const res = await App.apiGet(`/api/library/list?query=${q}&category=${c}&subfolder=${s}`);
  App.ui.libraryData = res || { files: [], subfolders: [], models_dir: "" };
  if (!App.ui.selectedLibPath && App.ui.libraryData.files.length) {
    App.ui.selectedLibPath = App.ui.libraryData.files[0].path;
  }
  if (App.ui.view === "library") renderContent();
}

async function loadGcodePreview({ path = "", printer_id = "", filename = "" }) {
  const qs = new URLSearchParams();
  if (path) qs.set("path", path);
  if (printer_id) qs.set("printer_id", printer_id);
  if (filename) qs.set("filename", filename);
  const res = await App.apiGet(`/api/gcode/analyze?${qs.toString()}`);
  App.ui.gcodeData = res;
  App.ui.gcodeLayerIdx = Math.max(0, Math.floor(((res.layers || []).length - 1) * 0.65));
  if (App.ui.view === "gcode") renderContent();
}

async function loadHistoryStats() {
  const res = await App.apiGet("/api/history");
  App.ui.historyData = res;
  if (App.ui.view === "stats" || App.ui.view === "maintenance") renderContent();
}

async function calculateQuoteNow() {
  const f = App.ui.quoteForm;
  const r = App.state.cost_rates;
  const res = await App.apiPost("/api/costs/quote", {
    grams: f.grams,
    hours: f.hours,
    copies: f.copies,
    prep_mins: f.prep_mins,
    waste_pct: f.waste_pct,
    eur_kg: r.eur_kg,
    watts: r.watts,
    kwh: r.kwh,
    wear: r.wear,
    labor_h: r.labor_h,
    margin_pct: r.margin_pct,
    fail_pct: r.fail_pct,
    vat_pct: r.vat_pct,
  });
  if (res.quote) {
    App.ui.quoteResult = res.quote;
    if (App.ui.view === "stats" && App.ui.statsTab === "quote") renderContent();
  }
}

async function loadWebcams() {
  const res = await App.apiGet("/api/webcams");
  App.ui.camsList = res.cams || [];
  if (App.ui.view === "cameras") renderContent();
}

async function desktopAction(action, payload = {}) {
  const res = await App.apiPost("/api/desktop/action", { action, ...payload });
  if (res.error) {
    App.toast(res.error, "error");
    return null;
  }
  return res.result;
}

/* ============================================================================
   View 1: Fleet Dashboard (Easy Mode & Advanced Pro Mode)
   ============================================================================ */

function renderDashboard() {
  const isEasy = App.state.mode === "easy";
  const printers = App.state.printers || [];
  const statuses = App.state.statuses || {};

  // Easy Mode Guided Quick-Start Hero Banner
  const easyBanner = isEasy ? `
    <div class="easy-hero">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="width:38px;height:38px;border-radius:10px;background:rgba(16,185,129,0.2);color:#10B981;display:flex;align-items:center;justify-content:center">
          ${ICONS.sparkle}
        </div>
        <div>
          <div style="font-weight:800;font-size:14.5px;color:var(--text-main)">Easy-Modus aktiv — 1-Klick Druck-Assistent</div>
          <div style="font-size:12px;color:var(--text-sub)">Wähle direkt eine Aktion oder klicke auf einen Drucker für geführte Bedienung ohne Fachchinesisch.</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="navigate('library')">${ICONS.play} 3D-Datei zum Drucken wählen</button>
        <button class="btn btn-success" onclick="sendBatchControl('all_idle','preheat',{nozzle:210,bed:60})">${ICONS.flame} Alle auf PLA vorheizen</button>
        <button class="btn" onclick="navigate('spoolman')">${ICONS.spool} Spule wechseln</button>
        <button class="btn" onclick="navigate('discover')">${ICONS.globe} Neue 3D-Modelle finden</button>
      </div>
    </div>
  ` : `
    <div class="card" style="margin-bottom:16px;padding:11px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:10px">
        <span class="badge" style="background:rgba(0,229,255,0.14);color:var(--accent);border:1px solid var(--accent)">BATCH FLEET CONTROL</span>
        <span style="font-size:12px;color:var(--text-sub)">Befehle simultan an freie oder druckende Maschinen senden:</span>
      </div>
      <div style="display:flex;gap:7px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="sendBatchControl('all_idle','preheat',{nozzle:210,bed:60})">${ICONS.flame} Freie: PLA (210/60°C)</button>
        <button class="btn btn-sm" onclick="sendBatchControl('all_idle','preheat',{nozzle:240,bed:75})">${ICONS.flame} Freie: PETG (240/75°C)</button>
        <button class="btn btn-sm" onclick="sendBatchControl('all_idle','preheat',{nozzle:255,bed:105})">${ICONS.flame} Freie: ABS (255/105°C)</button>
        <button class="btn btn-sm" onclick="sendBatchControl('all_idle','preheat',{nozzle:0,bed:0})">❄ Freie Abkühlen</button>
        <button class="btn btn-sm btn-warn" onclick="sendBatchControl('all_printing','pause')">⏸ Alle Pausieren</button>
        <button class="btn btn-sm btn-danger" onclick="if(confirm('NOT-AUS (M112) für ALLE Drucker auslösen?')) sendBatchControl('all','emergency_stop')">⚠ Flotten NOT-AUS</button>
      </div>
    </div>
  `;

  const cardsHtml = printers.map((p) => {
    const st = statuses[p.id] || { state: "offline" };
    const state = st.error ? "offline" : (st.state || "offline");
    const col = STATE_COLORS[state] || "#00E5FF";
    const stateTxt = STATE_LABELS[state] || state.toUpperCase();
    const prog = Number(st.progress || 0);
    const pctStr = state === "printing" || state === "paused" ? `${Math.round(prog * 100)}%` : (state === "complete" ? "100%" : (state === "offline" ? "OFF" : "IDLE"));
    const isBambu = p.printer_type === "bambu";
    const sp = st.active_spool;
    const temps = st.temps || [];
    const nozzleT = temps[0] ? `${fmtTemp(temps[0][1])}°C${temps[0][2] > 0 ? ` / ${temps[0][2].toFixed(0)}°` : ""}` : "—";
    const bedT = temps[1] ? `${fmtTemp(temps[1][1])}°C${temps[1][2] > 0 ? ` / ${temps[1][2].toFixed(0)}°` : ""}` : "—";
    const remTxt = st.remaining ? `Rest: ${fmtHms(st.remaining)}${st.eta ? ` (Fertig ~${st.eta})` : ""}` : (state === "standby" ? "Bereit für Druckauftrag" : `Laufzeit: ${fmtHms(st.duration)}`);

    const proMetaRow = !isEasy && state !== "offline" ? `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px">
        <div class="telemetry-cell" style="padding:6px 8px">
          <div class="telemetry-lbl">SCHICHT</div>
          <div class="mono" style="font-size:11.5px;font-weight:700">${st.layer || 0}/${st.total_layers || "—"}</div>
        </div>
        <div class="telemetry-cell" style="padding:6px 8px">
          <div class="telemetry-lbl">SPEED / FLOW</div>
          <div class="mono" style="font-size:11.5px;font-weight:700">${Math.round((st.speed_factor || 1) * 100)}% · ${Math.round((st.extrude_factor || 1) * 100)}%</div>
        </div>
        <div class="telemetry-cell" style="padding:6px 8px">
          <div class="telemetry-lbl">Z-OFFSET</div>
          <div class="mono" style="font-size:11.5px;font-weight:700;color:var(--accent)">${Number(st.z_offset || 0).toFixed(3)}</div>
        </div>
        <div class="telemetry-cell" style="padding:6px 8px">
          <div class="telemetry-lbl">LÜFTER</div>
          <div class="mono" style="font-size:11.5px;font-weight:700">${Math.round((st.fan_speed || 0) * 100)}%</div>
        </div>
      </div>
    ` : "";

    return `
      <div class="card card-interactive" id="pcard-${esc(p.id)}" onclick="navigate('detail','${esc(p.id)}')">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:8px;min-width:0">
            <span style="font-size:16px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.name)}</span>
            <span class="badge" style="background:var(--bg-elevated-2);color:var(--text-sub);border:1px solid var(--border)">
              ${isBambu ? "BAMBU LAB" : "KLIPPER"}
            </span>
            ${p.is_sim ? `<span class="badge" style="background:rgba(139,92,246,0.18);color:#C084FC;border:1px solid rgba(139,92,246,0.4)">DEMO</span>` : ""}
          </div>
          <span class="badge" id="pstate-${esc(p.id)}" style="background:rgba(15,23,42,0.65);color:${col};border:1px solid ${col}">
            ● ${esc(stateTxt)}
          </span>
        </div>

        <div style="display:flex;align-items:center;gap:15px">
          <div id="pgauge-${esc(p.id)}">
            ${renderRadialGaugeSVG(state === "complete" ? 1 : prog, col, pctStr, stateTxt, st.thumb_b64, isEasy ? 94 : 84)}
          </div>
          <div style="flex:1;min-width:0">
            <div id="pfile-${esc(p.id)}" style="font-weight:700;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text-main)">
              ${esc(st.filename || (state === "offline" ? "Nicht im Netzwerk erreichbar" : "Kein aktiver Druckauftrag"))}
            </div>
            <div id="prem-${esc(p.id)}" style="font-size:12px;color:var(--text-sub);margin-top:3px">
              ${esc(remTxt)}
            </div>
            <div id="ptemps-${esc(p.id)}" style="display:flex;gap:12px;margin-top:7px;font-size:12px;font-weight:700">
              <span>🔥 Düse: <b style="color:var(--accent)">${nozzleT}</b></span>
              <span>🛏 Bett: <b style="color:#F59E0B">${bedT}</b></span>
            </div>
            <div style="display:flex;align-items:center;gap:7px;margin-top:7px;font-size:11.5px;color:var(--text-sub)">
              <span style="width:11px;height:11px;border-radius:50%;background:${spoolColor(sp)};display:inline-block;border:1px solid rgba(255,255,255,0.3)"></span>
              <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                ${sp ? `${esc(spoolName(sp))} · <b>${Math.round(sp.remaining_weight || 0)} g</b>` : "Keine Spoolman-Spule zugewiesen"}
              </span>
            </div>
          </div>
        </div>

        ${proMetaRow}

        <div class="progress-track" style="margin:12px 0 11px 0">
          <div class="progress-fill" id="pbar-${esc(p.id)}" style="width:${Math.round(prog * 100)}%;background:${col}"></div>
        </div>

        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap" onclick="event.stopPropagation()">
          <button class="btn btn-sm btn-primary" onclick="navigate('detail','${esc(p.id)}')">
            ${isEasy ? "Drucker-Assistent öffnen" : "Cockpit & Steuerung"}
          </button>
          ${(state === "printing" || state === "paused") ? `
            <button class="btn btn-sm ${state === 'paused' ? 'btn-success' : 'btn-warn'}" onclick="sendControl('${esc(p.id)}','${state === 'paused' ? 'resume' : 'pause'}')">
              ${state === "paused" ? "▶ Fortsetzen" : "⏸ Pause"}
            </button>
          ` : `
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:210,bed:60})" title="PLA Vorheizen (210/60°C)">🔥 PLA</button>
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:240,bed:75})" title="PETG Vorheizen (240/75°C)">🔥 PETG</button>
          `}
          <button class="btn btn-sm" style="margin-left:auto" onclick="openPrinterModal('${esc(p.id)}')" title="Drucker bearbeiten">⚙</button>
        </div>
      </div>
    `;
  }).join("");

  const emptyHtml = !printers.length ? `
    <div class="card" style="text-align:center;padding:42px 20px">
      <div style="font-size:18px;font-weight:800;margin-bottom:8px">Noch kein 3D-Drucker verbunden</div>
      <div style="color:var(--text-sub);max-width:520px;margin:0 auto 18px auto">
        Füge deinen Klipper / Moonraker oder Bambu Lab Drucker hinzu oder aktiviere den interaktiven Demo-Fuhrpark zum sofortigen Testen aller Funktionen.
      </div>
      <div style="display:flex;gap:10px;justify-content:center">
        <button class="btn btn-primary btn-lg" onclick="openPrinterModal()">+ Drucker hinzufügen (inkl. Netzwerk-Scanner)</button>
        <button class="btn btn-lg" onclick="toggleSimMode(true)">⚡ Demo-Fuhrpark aktivieren</button>
      </div>
    </div>
  ` : "";

  const bentoAnalytics = !isEasy ? `
    <div class="bento-3">
      <div class="card">
        <div style="font-size:10.5px;font-weight:800;color:var(--text-sub);letter-spacing:0.7px;margin-bottom:6px">
          THERMISCHE ECHTZEIT-TELEMETRIE (°C)
        </div>
        <canvas id="fleet-thermal-canvas" style="width:100%;height:155px;display:block"></canvas>
      </div>
      <div class="card">
        <div style="font-size:10.5px;font-weight:800;color:var(--text-sub);letter-spacing:0.7px;margin-bottom:6px">
          SPOOLMAN BESTAND NACH MATERIAL
        </div>
        <canvas id="fleet-spool-donut" style="width:100%;height:155px;display:block"></canvas>
      </div>
      <div class="card">
        <div style="font-size:10.5px;font-weight:800;color:var(--text-sub);letter-spacing:0.7px;margin-bottom:10px">
          FLOTTEN-AUSLASTUNG & ETA TIMELINE
        </div>
        <div id="fleet-utilization-bars" style="display:flex;flex-direction:column;gap:10px"></div>
      </div>
    </div>
  ` : "";

  return `
    <div class="page-header">
      <div>
        <div class="page-title">
          ${isEasy ? "Meine 3D-Drucker Übersicht" : "Flotten-Kommandozentrale & Live-Telemetrie"}
        </div>
        <div class="page-sub">
          ${isEasy ? "Einfache Überwachung, Restzeit-Anzeige und 1-Klick Steuerung" : "Echtzeit-Überwachung, Batch-Steuerung, Spoolman-Sync und Prozess-Telemetrie für Klipper & Bambu Lab"}
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn" onclick="toggleSimMode(!App.state.sim_enabled)" title="Virtuelle Demo-Drucker ein-/ausblenden">
          ${App.state.sim_enabled ? "🟢 Demo-Fuhrpark: AN" : "⚪ Demo-Fuhrpark: AUS"}
        </button>
        <button class="btn" onclick="navigate('cameras')">${ICONS.camera} Kamera-Matrix</button>
        <button class="btn btn-primary" onclick="openPrinterModal()">${ICONS.plus} Drucker hinzufügen</button>
      </div>
    </div>
    ${easyBanner}
    ${emptyHtml}
    <div class="${isEasy ? 'grid-cards-easy' : 'grid-cards'}">${cardsHtml}</div>
    ${bentoAnalytics}
  `;
}

/* ============================================================================
   View 2: Printer Detail & Control Center (Easy Mode vs Advanced 6-Tab Pro)
   ============================================================================ */

function renderDetail() {
  const pid = App.ui.selectedPrinterId || (App.state.printers[0] && App.state.printers[0].id);
  const p = (App.state.printers || []).find((x) => x.id === pid);
  if (!p) return renderDashboard();

  const st = App.state.statuses[p.id] || { state: "offline" };
  const state = st.error ? "offline" : (st.state || "offline");
  const col = STATE_COLORS[state] || "#00E5FF";
  const prog = Number(st.progress || 0);
  const isEasy = App.state.mode === "easy";
  const isBambu = p.printer_type === "bambu";
  const sp = st.active_spool;
  const det = App.ui.printerDetails || { files: [], macros: [], console: [] };

  const headerBar = `
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <button class="btn" onclick="navigate('dashboard')">${ICONS.back} Übersicht</button>
        <div>
          <div class="page-title">
            ${esc(p.name)}
            <span class="badge" style="background:rgba(15,23,42,0.75);color:${col};border:1px solid ${col}">
              ● ${esc(STATE_LABELS[state] || state)}
            </span>
            <span class="badge" style="background:var(--bg-elevated-2);color:var(--text-sub)">
              ${isBambu ? "Bambu OS" : `Klipper (${esc(st.klipper || 'ready')})`}
            </span>
          </div>
          <div class="page-sub">Host: ${esc(p.host)}:${p.port} · ${st.eta ? `Erwartetes Druckende: <b>${esc(st.eta)}</b>` : "Bereit für Befehle"}</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${(state === "printing" || state === "paused") ? `
          <button class="btn ${state === 'paused' ? 'btn-success' : 'btn-warn'}" onclick="sendControl('${esc(p.id)}','${state === 'paused' ? 'resume' : 'pause'}')">
            ${state === "paused" ? "▶ Druck fortsetzen" : "⏸ Druck pausieren"}
          </button>
          <button class="btn btn-danger" onclick="if(confirm('Aktuellen Druck wirklich abbrechen?')) sendControl('${esc(p.id)}','cancel')">
            ⏹ Druck abbrechen
          </button>
        ` : ""}
        ${!isEasy ? `
          <button class="btn btn-warn" onclick="sendControl('${esc(p.id)}','firmware_restart')">↻ Firmware-Restart</button>
          <button class="btn btn-danger" onclick="if(confirm('SOFORTIGER NOT-AUS (M112) für ${esc(p.name)}?')) sendControl('${esc(p.id)}','emergency_stop')">
            ⚠ NOT-AUS (M112)
          </button>
        ` : ""}
      </div>
    </div>
  `;

  // EASY MODE GUIDED COCKPIT
  if (isEasy) {
    const filesHtml = (det.files || []).slice(0, 8).map((f) => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:9px 12px;background:var(--bg-elevated);border-radius:9px;border:1px solid var(--border-subtle)">
        <div style="min-width:0;flex:1">
          <div style="font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(f.path)}</div>
          <div style="font-size:11px;color:var(--text-sub)">${(Number(f.size || 0) / (1024 * 1024)).toFixed(2)} MB</div>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-sm" onclick="loadGcodePreview({printer_id:'${esc(p.id)}',filename:'${esc(f.path)}'});navigate('gcode')">Vorschau</button>
          <button class="btn btn-sm btn-primary" onclick="sendControl('${esc(p.id)}','start_file',{filename:'${esc(f.path)}'})">▶ Jetzt drucken</button>
        </div>
      </div>
    `).join("") || `<div style="color:var(--text-sub);font-size:12.5px">Keine G-Code-Dateien auf dem Drucker gefunden.</div>`;

    return `
      ${headerBar}
      <div class="bento-2">
        <div style="display:flex;flex-direction:column;gap:16px">
          <!-- Status & Progress Card -->
          <div class="card" style="display:flex;align-items:center;gap:18px">
            ${renderRadialGaugeSVG(state === "complete" ? 1 : prog, col, `${Math.round(prog * 100)}%`, STATE_LABELS[state] || state, st.thumb_b64, 112)}
            <div style="flex:1;min-width:0">
              <div style="font-size:11px;font-weight:800;color:var(--accent);text-transform:uppercase">Aktueller Druckauftrag</div>
              <div style="font-size:16px;font-weight:800;margin:3px 0;word-break:break-all">${esc(st.filename || "Kein aktiver Druckauftrag")}</div>
              <div style="font-size:13px;color:var(--text-sub)">
                Laufzeit: <b>${fmtHms(st.duration)}</b> · Restzeit: <b>${fmtHms(st.remaining)}</b>
                ${st.eta ? ` · <span style="color:var(--ok);font-weight:800">Fertig um ${esc(st.eta)}</span>` : ""}
              </div>
              <div class="progress-track" style="margin-top:10px;height:9px">
                <div class="progress-fill" style="width:${Math.round(prog * 100)}%"></div>
              </div>
            </div>
          </div>

          <!-- 1-Click Preheat Assistant -->
          <div class="card">
            <div style="font-weight:800;font-size:14px;margin-bottom:4px">🔥 1-Klick Schnell-Vorheizen</div>
            <div style="font-size:12px;color:var(--text-sub);margin-bottom:12px">Wähle dein eingelegtes Material — Düse und Druckbett heizen automatisch auf:</div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:8px">
              <button class="btn" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:210,bed:60})"><b>PLA</b> (210 / 60°C)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:240,bed:75})"><b>PETG</b> (240 / 75°C)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:255,bed:105})"><b>ABS/ASA</b> (255 / 105°C)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:225,bed:50})"><b>TPU</b> (225 / 50°C)</button>
              <button class="btn btn-danger" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:0,bed:0})">❄ Abkühlen (0°C)</button>
            </div>
          </div>

          <!-- 1-Click Filament & Spool Assistant -->
          <div class="card">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
              <div>
                <div style="font-weight:800;font-size:14px">🧵 Filament & Spulen-Assistent</div>
                <div style="font-size:12px;color:var(--text-sub)">Aktive Spule: <b>${sp ? esc(spoolName(sp)) : "Keine zugewiesen"}</b></div>
              </div>
              <button class="btn btn-sm btn-primary" onclick="openAssignSpoolModal('${esc(p.id)}')">Spule wechseln …</button>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn" onclick="sendControl('${esc(p.id)}','load_filament')">⬇ Filament einziehen (Load)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','unload_filament')">⬆ Filament auswerfen (Unload)</button>
            </div>
          </div>

          <!-- Simple Guided Positioning -->
          <div class="card">
            <div style="font-weight:800;font-size:14px;margin-bottom:10px">🧭 Einfache Druckkopf-Positionierung</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <button class="btn" onclick="sendControl('${esc(p.id)}','home',{axes:''})">🏠 Alle Achsen Home (G28)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'Z',dist:25})">⬇ Druckbett senken (+25mm)</button>
              <button class="btn" onclick="sendControl('${esc(p.id)}','motors_off')">🔓 Motoren lösen (Frei bewegen)</button>
              <button class="btn" onclick="setMode('advanced')">⚡ Zu Profi-Steuerung wechseln</button>
            </div>
          </div>
        </div>

        <!-- Right column: Ready-to-print files -->
        <div class="card" style="display:flex;flex-direction:column;gap:10px">
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-weight:800;font-size:14.5px">📂 Druckbereite Dateien auf ${esc(p.name)}</div>
              <div style="font-size:12px;color:var(--text-sub)">Mit 1 Klick starten oder im G-Code Visualizer ansehen</div>
            </div>
            <button class="btn btn-sm" onclick="loadPrinterDetails('${esc(p.id)}')">${ICONS.refresh}</button>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;overflow-y:auto;max-height:460px">
            ${filesHtml}
          </div>
        </div>
      </div>
    `;
  }

  // ADVANCED PRO MODE (6 Engineering Tabs)
  const tab = App.ui.detailTab || "cockpit";
  const eo = st.exclude_object;
  const bm = st.bed_mesh;

  const tabsNav = `
    <div class="tab-bar">
      <button class="tab-btn ${tab === 'cockpit' ? 'active' : ''}" onclick="App.ui.detailTab='cockpit';renderContent()">🎛 Cockpit, Speed & Flow</button>
      <button class="tab-btn ${tab === 'motion' ? 'active' : ''}" onclick="App.ui.detailTab='motion';renderContent()">🧭 Jogging, Z-Offset & Makros</button>
      <button class="tab-btn ${tab === 'exclude' ? 'active' : ''}" onclick="App.ui.detailTab='exclude';renderContent()">
        🎯 Exclude Object ${eo && eo.objects ? `(${eo.objects.length})` : ""}
      </button>
      <button class="tab-btn ${tab === 'bedmesh' ? 'active' : ''}" onclick="App.ui.detailTab='bedmesh';renderContent()">
        🗺 Bett-Mesh 2D/3D ${bm ? `(Δ ${bm.variance}mm)` : ""}
      </button>
      <button class="tab-btn ${tab === 'files' ? 'active' : ''}" onclick="App.ui.detailTab='files';renderContent()">📂 Drucker-Dateien (${(det.files || []).length})</button>
      <button class="tab-btn ${tab === 'console' ? 'active' : ''}" onclick="App.ui.detailTab='console';renderContent()">⌨ G-Code Terminal</button>
    </div>
  `;

  let tabBody = "";
  if (tab === "cockpit") {
    const spdPct = Math.round((st.speed_factor || 1) * 100);
    const flwPct = Math.round((st.extrude_factor || 1) * 100);
    const fanPct = Math.round((st.fan_speed || 0) * 100);

    tabBody = `
      <div class="bento-2">
        <div class="card">
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px">
            ${renderRadialGaugeSVG(state === "complete" ? 1 : prog, col, `${Math.round(prog * 100)}%`, state, st.thumb_b64, 96)}
            <div style="flex:1;min-width:0">
              <div style="font-size:15px;font-weight:800;word-break:break-all">${esc(st.filename || "Kein aktiver Druckauftrag")}</div>
              <div style="font-size:12px;color:var(--text-sub);margin-top:4px">
                Schicht: <b>${st.layer || 0} / ${st.total_layers || "—"}</b> · Laufzeit: <b>${fmtHms(st.duration)}</b> · Rest: <b>${fmtHms(st.remaining)}</b>
              </div>
              ${st.eta ? `<div style="margin-top:4px;font-size:12px;color:var(--ok);font-weight:800">⏱ Erwartetes Ende: ${esc(st.eta)}</div>` : ""}
            </div>
          </div>

          <div style="font-size:11px;font-weight:800;color:var(--text-sub);margin-bottom:6px">LIVE PROZESS-OVERRIDES (GESCHWINDIGKEIT, FLUSS & LÜFTER)</div>
          <div style="display:flex;flex-direction:column;gap:10px;background:var(--bg-elevated);padding:12px;border-radius:10px">
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:4px">
                <span>Druckgeschwindigkeit (M220)</span>
                <span class="mono" style="color:var(--accent)">${spdPct}%</span>
              </div>
              <input type="range" min="25" max="250" step="5" value="${spdPct}" onchange="sendControl('${esc(p.id)}','speed',{percent:this.value})"/>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:4px">
                <span>Extrusions-Flussfaktor / Flow (M221)</span>
                <span class="mono" style="color:#8B5CF6">${flwPct}%</span>
              </div>
              <input type="range" min="70" max="140" step="1" value="${flwPct}" onchange="sendControl('${esc(p.id)}','flow',{percent:this.value})"/>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:4px">
                <span>Bauteilkühlung (M106)</span>
                <span class="mono" style="color:#10B981">${fanPct}%</span>
              </div>
              <input type="range" min="0" max="100" step="5" value="${fanPct}" onchange="sendControl('${esc(p.id)}','fan',{percent:this.value})"/>
            </div>
          </div>

          ${isBambu ? `
            <div style="margin-top:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span style="font-size:11.5px;font-weight:700;color:var(--text-sub)">Bambu Speed-Profil:</span>
              ${[[2, "Lautlos (Silent)"], [1, "Standard"], [3, "Sport (124%)"], [4, "Ludicrous (166%)"]].map(([lvl, lbl]) => `
                <button class="btn btn-sm ${st.speed_level === lvl ? 'btn-primary' : ''}" onclick="sendControl('${esc(p.id)}','speed',{level:${lvl},percent:${lvl === 4 ? 166 : (lvl === 3 ? 124 : 100)}})">${lbl}</button>
              `).join("")}
              <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','chamber_light',{on:${!st.chamber_light}})">💡 Kammer-LED</button>
            </div>
          ` : ""}
        </div>

        <div class="card" style="display:flex;flex-direction:column;gap:12px">
          <div style="font-size:11px;font-weight:800;color:var(--text-sub)">TEMPERATUR-SOLLWERTE & SPOOLMAN SLOTS</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div class="telemetry-cell">
              <div class="telemetry-lbl">DÜSE (EXTRUDER)</div>
              <div class="telemetry-val mono">${ st.temps && st.temps[0] ? `${fmtTemp(st.temps[0][1])} °C` : "—" }</div>
              <div style="display:flex;gap:6px;margin-top:6px">
                <input type="number" id="in-nozzle-${esc(p.id)}" placeholder="Soll °C" value="${st.temps && st.temps[0] && st.temps[0][2] ? st.temps[0][2] : 210}" style="padding:5px 8px"/>
                <button class="btn btn-sm btn-primary" onclick="sendControl('${esc(p.id)}','temp',{heater:'extruder',target:document.getElementById('in-nozzle-${esc(p.id)}').value})">Set</button>
              </div>
            </div>
            <div class="telemetry-cell">
              <div class="telemetry-lbl">HEIZBETT (BED)</div>
              <div class="telemetry-val mono">${ st.temps && st.temps[1] ? `${fmtTemp(st.temps[1][1])} °C` : "—" }</div>
              <div style="display:flex;gap:6px;margin-top:6px">
                <input type="number" id="in-bed-${esc(p.id)}" placeholder="Soll °C" value="${st.temps && st.temps[1] && st.temps[1][2] ? st.temps[1][2] : 60}" style="padding:5px 8px"/>
                <button class="btn btn-sm btn-primary" onclick="sendControl('${esc(p.id)}','temp',{heater:'heater_bed',target:document.getElementById('in-bed-${esc(p.id)}').value})">Set</button>
              </div>
            </div>
          </div>

          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:210,bed:60})">PLA 210/60</button>
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:240,bed:75})">PETG 240/75</button>
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:255,bed:105})">ABS/ASA 255/105</button>
            <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:225,bed:50})">TPU 225/50</button>
            <button class="btn btn-sm btn-danger" onclick="sendControl('${esc(p.id)}','preheat',{nozzle:0,bed:0})">Heizung Aus</button>
          </div>

          <div style="flex:1;min-height:135px">
            <canvas id="detail-thermal-canvas" style="width:100%;height:140px;display:block"></canvas>
          </div>

          <div style="display:flex;align-items:center;justify-content:space-between;background:var(--bg-elevated);padding:10px 12px;border-radius:10px">
            <div style="display:flex;align-items:center;gap:9px">
              <span style="width:14px;height:14px;border-radius:50%;background:${spoolColor(sp)};display:inline-block"></span>
              <div>
                <div style="font-size:12.5px;font-weight:700">${sp ? esc(spoolName(sp)) : "Keine Spoolman-Spule zugewiesen"}</div>
                <div style="font-size:11px;color:var(--text-sub)">${sp ? `Restgewicht: ${Math.round(sp.remaining_weight || 0)} g` : "Spule für Kosten- & Gewichts-Tracking wählen"}</div>
              </div>
            </div>
            <button class="btn btn-sm" onclick="openAssignSpoolModal('${esc(p.id)}')">Spule zuweisen …</button>
          </div>
        </div>
      </div>
    `;
  } else if (tab === "motion") {
    const pos = st.position || [0, 0, 0];
    const macrosHtml = (det.macros || []).map((m) => `
      <button class="btn btn-sm mono" onclick="sendControl('${esc(p.id)}','macro',{name:'${esc(m)}'})">${esc(m)}</button>
    `).join("") || `<span style="color:var(--text-sub);font-size:12px">Keine Klipper-Makros geladen.</span>`;

    tabBody = `
      <div class="bento-2">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:800;font-size:14px">🧭 Achsen-Steuerung (Jogging) & Homing</div>
            <div class="mono" style="font-size:12px;color:var(--accent)">
              X ${Number(pos[0] || 0).toFixed(1)} · Y ${Number(pos[1] || 0).toFixed(1)} · Z ${Number(pos[2] || 0).toFixed(2)} (${esc((st.homed || "—").toUpperCase())})
            </div>
          </div>

          <div style="display:flex;gap:7px;margin-bottom:12px;flex-wrap:wrap">
            <button class="btn btn-primary" onclick="sendControl('${esc(p.id)}','home',{axes:''})">🏠 Home All (G28)</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','home',{axes:'X Y'})">Home X/Y</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','home',{axes:'Z'})">Home Z</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','qgl')">Quad Gantry Level</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','z_tilt')">Z-Tilt Adjust</button>
            <button class="btn btn-warn" onclick="sendControl('${esc(p.id)}','motors_off')">M84 Motoren Aus</button>
          </div>

          <div style="display:flex;align-items:center;gap:6px;margin-bottom:12px">
            <span style="font-size:12px;color:var(--text-sub)">Schrittweite:</span>
            ${[0.1, 1, 10, 50, 100].map((s) => `
              <button class="btn btn-sm ${App.ui.jogStep === s ? 'btn-primary' : ''}" onclick="App.ui.jogStep=${s};renderContent()">${s} mm</button>
            `).join("")}
          </div>

          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;max-width:440px">
            <div></div>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'Y',dist:App.ui.jogStep})">▲ Y+</button>
            <div></div>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'Z',dist:App.ui.jogStep})">▲ Z+</button>

            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'X',dist:-App.ui.jogStep})">◀ X-</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','home',{axes:'X Y'})">🏠 XY</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'X',dist:App.ui.jogStep})">X+ ▶</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','home',{axes:'Z'})">🏠 Z</button>

            <div></div>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'Y',dist:-App.ui.jogStep})">▼ Y-</button>
            <div></div>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'Z',dist:-App.ui.jogStep})">▼ Z-</button>
          </div>

          <div style="display:flex;gap:8px;margin-top:14px">
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'E',dist:-10,speed:300})">⬆ Retract (-10mm)</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','jog',{axis:'E',dist:10,speed:300})">⬇ Extrude (+10mm)</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','load_filament')">Filament Laden (+50mm)</button>
            <button class="btn" onclick="sendControl('${esc(p.id)}','unload_filament')">Entladen (-50mm)</button>
          </div>
        </div>

        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <div style="font-weight:800;font-size:14px">🔬 Live Z-Offset Babystepping</div>
              <span class="mono" style="font-size:15px;font-weight:800;color:var(--accent)">${Number(st.z_offset || 0).toFixed(3)} mm</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:7px">
              <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','z_offset',{delta:0.05})">+0.050</button>
              <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','z_offset',{delta:0.01})">+0.010</button>
              <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','z_offset',{delta:-0.01})">-0.010</button>
              <button class="btn btn-sm" onclick="sendControl('${esc(p.id)}','z_offset',{delta:-0.05})">-0.050</button>
            </div>
            <button class="btn btn-sm" style="margin-top:8px;width:100%" onclick="sendControl('${esc(p.id)}','z_offset',{reset:true})">Auf 0.000 mm zurücksetzen</button>
          </div>

          <div class="card" style="flex:1">
            <div style="font-weight:800;font-size:14px;margin-bottom:8px">⚡ Klipper G-Code Makros</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px">${macrosHtml}</div>
          </div>
        </div>
      </div>
    `;
  } else if (tab === "exclude") {
    const objs = (eo && eo.objects) || [];
    const excluded = new Set((eo && eo.excluded_objects) || []);
    const curObj = eo && eo.current_object;

    tabBody = `
      <div class="bento-2">
        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:4px">🎯 Bauplatten-Karte (Klipper Exclude Object)</div>
          <div style="font-size:12px;color:var(--text-sub);margin-bottom:10px">
            Löst sich ein einzelnes Bauteil während eines Mehrfach-Drucks vom Bett, kannst du es hier mit 1 Klick überspringen — alle anderen Bauteile drucken sauber weiter!
          </div>
          <canvas id="exclude-object-canvas" style="width:100%;height:320px;display:block"></canvas>
        </div>
        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:10px">Erkannte Bauteile im aktuellen Job (${objs.length})</div>
          ${objs.length ? `
            <div style="display:flex;flex-direction:column;gap:8px">
              ${objs.map((o) => {
                const isEx = excluded.has(o.name);
                const isCur = o.name === curObj && !isEx;
                return `
                  <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:var(--bg-elevated);border-radius:10px;border:1px solid ${isEx ? 'var(--danger)' : (isCur ? 'var(--accent)' : 'var(--border-subtle)')}">
                    <div>
                      <div class="mono" style="font-weight:700;font-size:13px">${esc(o.name)}</div>
                      <div style="font-size:11px;color:var(--text-sub)">
                        Zentrum: X ${o.center ? o.center[0] : "—"} / Y ${o.center ? o.center[1] : "—"}
                        ${isCur ? ` · <b style="color:var(--accent)">Aktuell unter der Düse</b>` : ""}
                      </div>
                    </div>
                    ${isEx ? `
                      <span class="badge" style="background:rgba(244,63,94,0.18);color:var(--danger)">AUSGESCHLOSSEN</span>
                    ` : `
                      <button class="btn btn-sm btn-danger" onclick="if(confirm('Bauteil ${esc(o.name)} wirklich vom weiteren Druck ausschließen?')) sendControl('${esc(p.id)}','exclude_object',{name:'${esc(o.name)}'})">
                        Bauteil überspringen
                      </button>
                    `}
                  </div>
                `;
              }).join("")}
            </div>
          ` : `
            <div style="color:var(--text-sub);padding:20px 0">
              Für diesen Drucker sind aktuell keine <code>[exclude_object]</code> Geometrien aktiv (oder es läuft kein Mehrteil-Druck).
            </div>
          `}
        </div>
      </div>
    `;
  } else if (tab === "bedmesh") {
    tabBody = `
      <div class="bento-2">
        <div class="card">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
            <div>
              <div style="font-weight:800;font-size:14.5px">🗺 Bett-Nivellierung & Mesh-Topografie</div>
              <div style="font-size:12px;color:var(--text-sub)">
                Profil: <b>${bm ? esc(bm.profile_name) : "Kein Mesh geladen"}</b>
              </div>
            </div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-sm ${App.ui.bedMesh3D ? 'btn-primary' : ''}" onclick="App.ui.bedMesh3D=true;renderContent()">3D Isometrisch</button>
              <button class="btn btn-sm ${!App.ui.bedMesh3D ? 'btn-primary' : ''}" onclick="App.ui.bedMesh3D=false;renderContent()">2D Heatmap (mm)</button>
              <button class="btn btn-sm btn-success" onclick="sendControl('${esc(p.id)}','bed_mesh_calibrate')">Mesh neu kalibrieren</button>
            </div>
          </div>
          ${bm ? `
            <canvas id="bed-mesh-canvas" style="width:100%;height:340px;display:block"></canvas>
          ` : `
            <div style="padding:40px;text-align:center;color:var(--text-sub)">
              Keine Bed-Mesh Matrix von Moonraker gemeldet. Klicke oben auf „Mesh neu kalibrieren“ (<code>BED_MESH_CALIBRATE</code>).
            </div>
          `}
        </div>
        <div class="card" style="display:flex;flex-direction:column;gap:12px">
          <div style="font-weight:800;font-size:14.5px">Mesh-Diagnose & Ebenheits-Analyse</div>
          ${bm ? `
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
              <div class="telemetry-cell">
                <div class="telemetry-lbl">VARIANZ (PEAK-TO-VALLEY)</div>
                <div class="telemetry-val mono" style="color:${bm.variance < 0.15 ? 'var(--ok)' : 'var(--warn)'}">${bm.variance.toFixed(3)} mm</div>
              </div>
              <div class="telemetry-cell">
                <div class="telemetry-lbl">HÖCHSTER PUNKT</div>
                <div class="telemetry-val mono">+${bm.max_val.toFixed(3)} mm</div>
              </div>
              <div class="telemetry-cell">
                <div class="telemetry-lbl">TIEFSTER PUNKT</div>
                <div class="telemetry-val mono">${bm.min_val.toFixed(3)} mm</div>
              </div>
            </div>
            <div style="padding:12px;border-radius:10px;background:var(--bg-elevated);font-size:12.5px">
              <b>Bewertung:</b> ${bm.variance < 0.10
                ? "🟢 Exzellente Planheit (< 0.10 mm) — Perfekt für erste Schichten über das gesamte Druckbett."
                : (bm.variance < 0.22
                  ? "🟡 Gute Planheit (< 0.22 mm) — Klipper gleicht die Unebenheit per Z-Fade problemlos aus."
                  : "🔴 Hohe Abweichung (> 0.22 mm) — Führe <code>QUAD_GANTRY_LEVEL</code> oder <code>Z_TILT_ADJUST</code> vor dem nächsten Druck aus.")}
            </div>
          ` : `<div style="color:var(--text-sub)">Keine Daten verfügbar.</div>`}
        </div>
      </div>
    `;
  } else if (tab === "files") {
    const rows = (det.files || []).map((f) => `
      <tr>
        <td class="mono" style="font-weight:700">${esc(f.path)}</td>
        <td>${(Number(f.size || 0) / (1024 * 1024)).toFixed(2)} MB</td>
        <td>${f.modified ? new Date(f.modified * 1000).toLocaleString("de-DE") : "—"}</td>
        <td style="text-align:right;white-space:nowrap">
          <button class="btn btn-sm btn-primary" onclick="sendControl('${esc(p.id)}','start_file',{filename:'${esc(f.path)}'})">▶ Starten</button>
          <button class="btn btn-sm" onclick="loadGcodePreview({printer_id:'${esc(p.id)}',filename:'${esc(f.path)}'});navigate('gcode')">🔍 Layer-Vorschau</button>
          <button class="btn btn-sm" onclick="App.apiPost('/api/library/action',{action:'download_from_printer',printer_id:'${esc(p.id)}',filename:'${esc(f.path)}'}).then(()=>App.toast('In Bibliothek gespeichert','ok'))">⬇ Bibliothek</button>
          <button class="btn btn-sm btn-danger" onclick="if(confirm('Datei vom Drucker löschen?')) sendControl('${esc(p.id)}','delete_file',{filename:'${esc(f.path)}'})">🗑</button>
        </td>
      </tr>
    `).join("") || `<tr><td colspan="4" style="text-align:center;color:var(--text-sub)">Keine Dateien gefunden</td></tr>`;

    tabBody = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div style="font-weight:800;font-size:14.5px">📂 G-Code Speicher auf ${esc(p.name)}</div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-sm" onclick="loadPrinterDetails('${esc(p.id)}')">${ICONS.refresh} Aktualisieren</button>
            <button class="btn btn-sm btn-primary" onclick="navigate('library')">Aus lokaler Bibliothek hochladen …</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Dateiname</th><th>Größe</th><th>Geändert</th><th style="text-align:right">Aktionen</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  } else if (tab === "console") {
    const lines = (det.console || []).map((c) => {
      const ts = c.time ? new Date(c.time * 1000).toLocaleTimeString("de-DE") : "";
      const isCmd = c.type === "command";
      return `<div style="color:${isCmd ? 'var(--accent)' : '#CBD5E1'}"><span style="color:var(--text-muted)">[${ts}]</span> ${isCmd ? ">> " : "   "}${esc(c.message)}</div>`;
    }).join("") || `<div style="color:var(--text-muted)">Konsole bereit. Gib unten einen G-Code oder Klipper-Befehl ein.</div>`;

    tabBody = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
          <div style="font-weight:800;font-size:14.5px">⌨ Klipper G-Code Terminal</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            ${["G28", "M114", "TURN_OFF_HEATERS", "BED_MESH_PROFILE LOAD=default", "QUAD_GANTRY_LEVEL", "FIRMWARE_RESTART"].map((cmd) => `
              <button class="btn btn-sm mono" onclick="sendControl('${esc(p.id)}','gcode',{script:'${cmd}'})">${cmd}</button>
            `).join("")}
          </div>
        </div>
        <div class="mono selectable" style="background:#04070D;border:1px solid var(--border);border-radius:10px;padding:12px;height:310px;overflow-y:auto;font-size:12px;line-height:1.55">
          ${lines}
        </div>
        <form style="display:flex;gap:8px;margin-top:10px" onsubmit="event.preventDefault();const v=this.elements.cmd.value.trim();if(v){sendControl('${esc(p.id)}','gcode',{script:v});this.reset();}">
          <input type="text" name="cmd" class="mono" placeholder="G-Code Befehl eingeben (z.B. G28, SET_VELOCITY_LIMIT ACCEL=5000, PID_CALIBRATE …)"/>
          <button type="submit" class="btn btn-primary">Senden</button>
        </form>
      </div>
    `;
  }

  return `${headerBar}${tabsNav}${tabBody}`;
}

/* ============================================================================
   View 3: Interactive G-Code Layer & Toolpath Studio (NEW)
   ============================================================================ */

function toggleGcodePlay() {
  if (App.ui.gcodePlaying) {
    clearInterval(App.ui.gcodeAnimTimer);
    App.ui.gcodeAnimTimer = null;
    App.ui.gcodePlaying = false;
    renderContent();
    return;
  }
  App.ui.gcodePlaying = true;
  App.ui.gcodeAnimTimer = setInterval(() => {
    const gd = App.ui.gcodeData;
    if (!gd || !gd.layers || !gd.layers.length) return;
    App.ui.gcodeLayerIdx = (App.ui.gcodeLayerIdx + 1) % gd.layers.length;
    const slider = document.getElementById("gcode-layer-slider");
    const lbl = document.getElementById("gcode-layer-lbl");
    const curL = gd.layers[App.ui.gcodeLayerIdx];
    if (slider) slider.value = App.ui.gcodeLayerIdx;
    if (lbl && curL) lbl.textContent = `Schicht ${curL.num} / ${gd.total_layers} (Z = ${curL.z.toFixed(2)} mm · ${curL.extrude_count} Extrusionspfade)`;
    drawGcodeLayerCanvas("gcode-studio-canvas");
  }, 160);
  renderContent();
}

function renderGcodeStudio() {
  const gd = App.ui.gcodeData || { name: "Lade Vorschau …", layers: [], meta: {}, parsed: {}, total_layers: 0, bbox: [0, 0, 200, 200, 20] };
  const layers = gd.layers || [];
  const idx = Math.max(0, Math.min(layers.length - 1, App.ui.gcodeLayerIdx));
  const curL = layers[idx] || { num: 1, z: 0.2, extrude_count: 0 };
  const bbox = gd.bbox || [0, 0, 200, 200, 20];
  const dimX = Math.max(0, (bbox[2] || 0) - (bbox[0] || 0)).toFixed(1);
  const dimY = Math.max(0, (bbox[3] || 0) - (bbox[1] || 0)).toFixed(1);
  const dimZ = Number(bbox[4] || 0).toFixed(1);

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.gcode} G-Code Layer & Toolpath Studio</div>
        <div class="page-sub">Schichtweise 2D/3D Werkzeugpfad-Analyse, Leerfahrten-Inspektion und Slicer-Telemetrie</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn" onclick="navigate('library')">📂 Andere G-Code aus Bibliothek wählen</button>
        <button class="btn btn-primary" onclick="if(gd.parsed && gd.parsed.grams){App.ui.quoteForm.grams=gd.parsed.grams;App.ui.quoteForm.hours=gd.parsed.hours||2;App.ui.quoteForm.file_name=gd.name;}App.ui.statsTab='quote';navigate('stats')">
          💶 Preis im Angebots-Kalkulator berechnen
        </button>
      </div>
    </div>

    <div class="bento-3" style="grid-template-columns: 2.1fr 1fr; margin-top:0">
      <div class="card" style="display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
          <div>
            <div class="mono" style="font-weight:800;font-size:14.5px;color:var(--accent)">${esc(gd.name)}</div>
            <div id="gcode-layer-lbl" style="font-size:12px;color:var(--text-sub)">
              Schicht ${curL.num} / ${gd.total_layers || layers.length} (Z = ${Number(curL.z || 0).toFixed(2)} mm · ${curL.extrude_count} Extrusionspfade)
            </div>
          </div>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm ${!App.ui.gcodeIso ? 'btn-primary' : ''}" onclick="App.ui.gcodeIso=false;renderContent()">2D Draufsicht</button>
            <button class="btn btn-sm ${App.ui.gcodeIso ? 'btn-primary' : ''}" onclick="App.ui.gcodeIso=true;renderContent()">3D Isometrisch</button>
            <button class="btn btn-sm ${App.ui.gcodeShowTravel ? 'btn-warn' : ''}" onclick="App.ui.gcodeShowTravel=!App.ui.gcodeShowTravel;renderContent()">
              ${App.ui.gcodeShowTravel ? "Leerfahrten: AN" : "Leerfahrten: AUS"}
            </button>
            <button class="btn btn-sm ${App.ui.gcodePlaying ? 'btn-danger' : 'btn-success'}" onclick="toggleGcodePlay()">
              ${App.ui.gcodePlaying ? "⏸ Stopp" : "▶ Schicht-Animation"}
            </button>
          </div>
        </div>

        <canvas id="gcode-studio-canvas" style="width:100%;height:420px;background:#050811;border:1px solid var(--border);border-radius:12px;display:block"></canvas>

        <div style="display:flex;align-items:center;gap:12px;background:var(--bg-elevated);padding:10px 14px;border-radius:10px">
          <span style="font-size:12px;font-weight:800;white-space:nowrap">Schicht-Regler:</span>
          <input type="range" id="gcode-layer-slider" min="0" max="${Math.max(0, layers.length - 1)}" value="${idx}"
            oninput="App.ui.gcodeLayerIdx=Number(this.value);const l=App.ui.gcodeData.layers[this.value];if(l)document.getElementById('gcode-layer-lbl').textContent='Schicht '+l.num+' / '+App.ui.gcodeData.total_layers+' (Z = '+l.z.toFixed(2)+' mm · '+l.extrude_count+' Extrusionspfade)';drawGcodeLayerCanvas('gcode-studio-canvas')"/>
        </div>
      </div>

      <div class="card" style="display:flex;flex-direction:column;gap:12px">
        <div style="font-weight:800;font-size:14.5px">📊 Slicer & Geometrie-Metadaten</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div class="telemetry-cell">
            <div class="telemetry-lbl">BAURAUM (X × Y × Z)</div>
            <div class="telemetry-val mono" style="font-size:13px">${dimX} × ${dimY} × ${dimZ} mm</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-lbl">SCHICHTEN GESAMT</div>
            <div class="telemetry-val mono">${gd.total_layers || layers.length}</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-lbl">DRUCKZEIT (CA.)</div>
            <div class="telemetry-val mono" style="color:var(--accent)">${esc((gd.meta || {})["Druckzeit"] || "—")}</div>
          </div>
          <div class="telemetry-cell">
            <div class="telemetry-lbl">FILAMENTBEDARF</div>
            <div class="telemetry-val mono" style="color:#F59E0B">${esc((gd.meta || {})["Filament (g)"] || "—")}</div>
          </div>
        </div>

        <div style="background:var(--bg-elevated);padding:12px;border-radius:10px;font-size:12.5px;display:flex;flex-direction:column;gap:6px">
          <div><b>Slicer:</b> ${esc((gd.meta || {})["Slicer"] || "Standard G-Code")}</div>
          <div><b>Schichthöhe:</b> ${esc((gd.meta || {})["Schichthöhe"] || "0.20 mm")}</div>
          <div><b>Material:</b> ${esc((gd.meta || {})["Material"] || "PLA / ABS")}</div>
        </div>

        <div style="margin-top:auto;display:flex;flex-direction:column;gap:8px">
          <div style="font-size:11px;color:var(--text-sub)">Legende: <span style="color:#00E5FF;font-weight:700">━ Extrusion</span> · <span style="color:#F59E0B;font-weight:700">┅ Leerfahrt (Travel)</span> · <span style="color:#10B981;font-weight:700">● Düsenposition</span></div>
          <button class="btn btn-primary" onclick="App.apiPost('/api/queue/add',{file:gd.path||gd.name,copies:1,material:'PLA'}).then(()=>{App.toast('Zur Warteschlange hinzugefügt','ok');pollState();})">
            + Zur Druck-Warteschlange hinzufügen
          </button>
        </div>
      </div>
    </div>
  `;
}

/* ============================================================================
   View 4: Spoolman Studio & Filament Drying Assistant
   ============================================================================ */

function renderSpoolman() {
  const isEasy = App.state.mode === "easy";
  const spools = App.state.spools || [];
  const tab = isEasy ? "spools" : (App.ui.spoolTab || "spools");
  const q = (App.ui.spoolSearch || "").toLowerCase();
  const matFilter = App.ui.spoolMatFilter || "all";

  const filteredSpools = spools.filter((s) => {
    const fil = s.filament || {};
    const hay = `${spoolName(s)} ${fil.material || ""} ${s.location || ""}`.toLowerCase();
    if (q && !hay.includes(q)) return false;
    if (matFilter !== "all" && (fil.material || "").toUpperCase() !== matFilter.toUpperCase()) return false;
    return true;
  });

  const tabsBar = !isEasy ? `
    <div class="tab-bar">
      <button class="tab-btn ${tab === 'spools' ? 'active' : ''}" onclick="App.ui.spoolTab='spools';renderContent()">🧵 Spulen-Bestand (${spools.length})</button>
      <button class="tab-btn ${tab === 'drying' ? 'active' : ''}" onclick="App.ui.spoolTab='drying';renderContent()">🌡 Trocknungs-Assistent & Hygroskopie</button>
      <button class="tab-btn ${tab === 'server' ? 'active' : ''}" onclick="App.ui.spoolTab='server';renderContent()">🔗 Spoolman-Server</button>
    </div>
  ` : "";

  if (tab === "drying") {
    const presets = App.state.drying_presets || [];
    const timers = App.state.drying_timers || [];
    const nowSec = Math.floor(Date.now() / 1000);

    return `
      <div class="page-header">
        <div>
          <div class="page-title">🌡 Filament-Trocknungs-Assistent & Hygroskopie-Guide</div>
          <div class="page-sub">Optimale Trocknungstemperaturen, Zeiten und aktive Drybox-Timer gegen Stringing & Schichtfehler</div>
        </div>
      </div>
      ${tabsBar}
      <div class="bento-2">
        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:10px">⏱ Aktive Trocknungs-Timer (${timers.length})</div>
          <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px">
            ${timers.map((t) => {
              const remSec = Math.max(0, (t.ends_at || 0) - nowSec);
              const done = remSec <= 0;
              return `
                <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:var(--bg-elevated);border-radius:10px;border:1px solid ${done ? 'var(--ok)' : 'var(--accent)'}">
                  <div>
                    <div style="font-weight:800;font-size:13px">${esc(t.spool_label)} (${esc(t.material)} @ ${t.temp_c}°C)</div>
                    <div style="font-size:11.5px;color:${done ? 'var(--ok)' : 'var(--text-sub)'}">
                      ${done ? "✓ Trocknung abgeschlossen — Druckbereit!" : `Verbleibend: ${fmtHms(remSec)} (Gesamt: ${t.duration_h}h)`}
                    </div>
                  </div>
                  <button class="btn btn-sm btn-danger" onclick="App.apiPost('/api/spoolman/drying/stop',{id:'${esc(t.id)}'}).then(()=>pollState())">Beenden</button>
                </div>
              `;
            }).join("") || `<div style="color:var(--text-sub);font-size:12.5px">Aktuell läuft kein Trocknungs-Timer. Starte rechts mit 1 Klick einen Drybox-Timer.</div>`}
          </div>

          <div style="font-weight:800;font-size:13.5px;margin-bottom:8px">Neuen Trocknungs-Timer starten</div>
          <form style="display:grid;grid-template-columns:1fr 1fr;gap:8px" onsubmit="event.preventDefault();const f=this.elements;App.apiPost('/api/spoolman/drying/start',{spool_label:f.lbl.value,material:f.mat.value,temp_c:f.temp.value,duration_h:f.hrs.value}).then(()=>{App.toast('Trocknungs-Timer gestartet','ok');pollState();})">
            <input type="text" name="lbl" placeholder="Spule / Drybox Name (z.B. Drybox 1)" required/>
            <input type="text" name="mat" placeholder="Material (z.B. PETG, PA-CF)" value="PETG" required/>
            <input type="number" name="temp" placeholder="Temperatur °C" value="65" required/>
            <input type="number" step="0.5" name="hrs" placeholder="Dauer in Stunden" value="6" required/>
            <button type="submit" class="btn btn-primary" style="grid-column:span 2">+ Trocknungs-Timer starten</button>
          </form>
        </div>

        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:10px">📖 Referenz-Tabelle: Filament-Trocknung</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Material</th><th>Soll-Temp</th><th>Dauer</th><th>Ziel-Feuchte</th><th>Schnellstart</th></tr></thead>
              <tbody>
                ${presets.map((pr) => `
                  <tr>
                    <td style="font-weight:700">${esc(pr.material)}</td>
                    <td class="mono" style="color:var(--accent);font-weight:700">${pr.temp_c} °C</td>
                    <td class="mono">${pr.hours} h</td>
                    <td>${esc(pr.humidity_target)}</td>
                    <td>
                      <button class="btn btn-sm" onclick="App.apiPost('/api/spoolman/drying/start',{spool_label:'${esc(pr.material)} Spule',material:'${esc(pr.material)}',temp_c:${pr.temp_c},duration_h:${pr.hours}}).then(()=>{App.toast('Timer gestartet','ok');pollState();})">
                        ▶ ${pr.hours}h Timer
                      </button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  if (tab === "server") {
    return `
      <div class="page-header">
        <div>
          <div class="page-title">🔗 Spoolman-Server Synchronisation</div>
          <div class="page-sub">Verbinde deinen zentralen Spoolman-Server oder erkenne ihn automatisch aus deinen Klipper-Druckern</div>
        </div>
      </div>
      ${tabsBar}
      <div class="card" style="max-width:680px">
        <div style="font-weight:800;font-size:14.5px;margin-bottom:8px">Spoolman REST API v1 Adresse</div>
        <div style="display:flex;gap:8px;margin-bottom:12px">
          <input type="text" id="sm-url-input" value="${esc(App.state.spoolman_url || '')}" placeholder="z.B. http://192.168.178.170:7912"/>
          <button class="btn" onclick="App.apiPost('/api/spoolman/discover').then(r=>{if(r.url){document.getElementById('sm-url-input').value=r.url;App.toast('Gefunden: '+r.url,'ok');pollState();}else App.toast(r.error||'Nicht gefunden','error');})">Auto-Erkennung</button>
          <button class="btn btn-primary" onclick="App.apiPost('/api/spoolman/save',{url:document.getElementById('sm-url-input').value}).then(()=>{App.toast('Spoolman gespeichert','ok');pollState();})">Speichern</button>
        </div>
        <div style="font-size:12px;color:var(--text-sub)">
          Status: ${App.state.spoolman_connected ? "<b style='color:var(--ok)'>● Verbunden mit Spoolman-Server</b>" : "<b style='color:var(--warn)'>● Lokaler / Demo-Spulenbestand aktiv</b>"}
        </div>
      </div>
    `;
  }

  // Spools Grid
  const spoolCards = filteredSpools.map((s) => {
    const fil = s.filament || {};
    const rem = Number(s.remaining_weight || 0);
    const init = Number(s.initial_weight || fil.weight || 1000);
    const pct = Math.max(0, Math.min(100, Math.round((rem / Math.max(1, init)) * 100)));
    const col = spoolColor(s);
    const isLow = rem < 150;

    return `
      <div class="card" style="display:flex;flex-direction:column;gap:10px;border-color:${isLow ? 'rgba(245,158,11,0.55)' : 'var(--border)'}">
        <div style="display:flex;align-items:center;gap:12px">
          <div style="width:44px;height:44px;border-radius:50%;background:radial-gradient(circle, var(--bg-input) 32%, ${col} 34%, ${col} 68%, var(--bg-elevated) 70%);border:2px solid var(--border);flex-shrink:0"></div>
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:6px">
              <span style="font-weight:800;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(spoolName(s))}</span>
              ${isLow ? `<span class="badge" style="background:rgba(245,158,11,0.18);color:var(--warn)">FAST LEER</span>` : ""}
            </div>
            <div style="font-size:11.5px;color:var(--text-sub)">
              Lagerort: <b>${esc(s.location || "Standard")}</b> · Düse ${fil.settings_extruder_temp || 210}°C / Bett ${fil.settings_bed_temp || 60}°C
            </div>
          </div>
          <div style="text-align:right">
            <div class="mono" style="font-size:16px;font-weight:800;color:${isLow ? 'var(--warn)' : 'var(--text-main)'}">${Math.round(rem)} g</div>
            <div style="font-size:10.5px;color:var(--text-sub)">${pct}% von ${Math.round(init)}g</div>
          </div>
        </div>

        <div class="progress-track">
          <div class="progress-fill" style="width:${pct}%;background:${isLow ? 'var(--warn)' : col}"></div>
        </div>

        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button class="btn btn-sm btn-primary" onclick="openAssignSpoolToPrinterModal(${s.id})">Auf Drucker laden …</button>
          ${!isEasy ? `
            <button class="btn btn-sm" onclick="const w=prompt('Bruttogewicht auf der Waage in Gramm (inkl. Leerspule):','${Math.round(rem + (fil.spool_weight || 200))}');if(w)App.apiPost('/api/spoolman/measure',{spool_id:${s.id},weight:Number(w)}).then(()=>{App.toast('Gewicht aktualisiert','ok');pollState();})">⚖ Wiegen</button>
            <button class="btn btn-sm" onclick="const g=prompt('Verbrauchte Gramm abziehen:','25');if(g)App.apiPost('/api/spoolman/use',{spool_id:${s.id},grams:Number(g)}).then(()=>{App.toast('Gramm abgebucht','ok');pollState();})">− Gramm</button>
            <button class="btn btn-sm btn-danger" style="margin-left:auto" onclick="if(confirm('Spule #${s.id} löschen?'))App.apiPost('/api/spoolman/spool/delete',{id:${s.id}}).then(()=>pollState())">🗑</button>
          ` : ""}
        </div>
      </div>
    `;
  }).join("");

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.spool} ${isEasy ? "Meine Filament-Spulen" : "Spoolman Pro & Trocknungs-Studio"}</div>
        <div class="page-sub">Farben, Restgewichte, Drucker-Zuweisung, Tara-Waage und Filament-Trocknung</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" onclick="openNewSpoolModal()">${ICONS.plus} Neue Spule / Filament anlegen</button>
      </div>
    </div>
    ${tabsBar}
    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <input type="text" placeholder="Spule, Hersteller, Farbe oder Lagerort suchen …" value="${esc(App.ui.spoolSearch)}"
        oninput="App.ui.spoolSearch=this.value;renderContent()" style="max-width:360px"/>
      <select onchange="App.ui.spoolMatFilter=this.value;renderContent()" style="max-width:180px">
        <option value="all">Alle Materialien</option>
        ${["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU"].map((m) => `<option value="${m}" ${App.ui.spoolMatFilter === m ? "selected" : ""}>${m}</option>`).join("")}
      </select>
    </div>
    <div class="grid-cards">${spoolCards}</div>
  `;
}

/* ============================================================================
   View 5: Print Queue & Batch Dispatcher
   ============================================================================ */

function renderQueue() {
  const queue = App.state.queue || [];
  const printers = App.state.printers || [];

  const rows = queue.map((it, idx) => `
    <tr>
      <td class="mono" style="font-weight:800">#${idx + 1}</td>
      <td>
        <div style="font-weight:700">${esc(it.name || it.file)}</div>
        <div style="font-size:11px;color:var(--text-sub)">Hinzugefügt: ${esc(it.added_at || "—")}</div>
      </td>
      <td><span class="badge" style="background:var(--bg-elevated-2);color:var(--accent)">${esc(it.material || "PLA")}</span></td>
      <td>${esc(it.printer_label || "Beliebiger freier Drucker")}</td>
      <td class="mono" style="font-weight:800">${it.copies || 1}×</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn btn-sm" onclick="App.apiPost('/api/queue/move',{id:'${esc(it.id)}',dir:-1}).then(()=>pollState())">↑</button>
        <button class="btn btn-sm" onclick="App.apiPost('/api/queue/move',{id:'${esc(it.id)}',dir:1}).then(()=>pollState())">↓</button>
        <button class="btn btn-sm btn-primary" onclick="App.apiPost('/api/queue/dispatch',{id:'${esc(it.id)}'}).then(r=>{if(r.error)App.toast(r.error,'error');else App.toast('Job gestartet auf '+r.printer,'ok');pollState();})">▶ Jetzt starten</button>
        <button class="btn btn-sm btn-danger" onclick="App.apiPost('/api/queue/remove',{id:'${esc(it.id)}'}).then(()=>pollState())">🗑</button>
      </td>
    </tr>
  `).join("") || `<tr><td colspan="6" style="text-align:center;color:var(--text-sub);padding:26px">Die Druck-Warteschlange ist aktuell leer.</td></tr>`;

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.queue} Farm-Warteschlange & Batch-Dispatcher</div>
        <div class="page-sub">Plane Serienaufträge mit Kopienanzahl und verteile sie automatisch oder per Klick auf freie Drucker</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <label style="display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;cursor:pointer;background:var(--bg-elevated);padding:7px 12px;border-radius:9px;border:1px solid var(--border)">
          <input type="checkbox" ${App.state.auto_dispatch ? "checked" : ""} onchange="App.apiPost('/api/mode',{auto_dispatch:this.checked}).then(()=>pollState())"/>
          Auto-Dispatch bei freiem Drucker
        </label>
        <button class="btn btn-primary" onclick="App.apiPost('/api/queue/dispatch',{}).then(r=>{if(r.error)App.toast(r.error,'error');else App.toast('Auftrag gestartet auf '+r.printer,'ok');pollState();})">
          ${ICONS.play} Nächsten Job sofort verteilen
        </button>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div style="font-weight:800;font-size:13.5px;margin-bottom:10px">Neuen Druckauftrag in die Warteschlange einreihen</div>
      <form style="display:grid;grid-template-columns:2fr 1.2fr 0.7fr 0.8fr auto;gap:8px;align-items:center"
        onsubmit="event.preventDefault();const f=this.elements;const sel=f.pid;App.apiPost('/api/queue/add',{file:f.file.value,printer_id:sel.value,printer_label:sel.options[sel.selectedIndex].text,copies:Number(f.copies.value),material:f.mat.value}).then(()=>{this.reset();App.toast('Zur Warteschlange hinzugefügt','ok');pollState();})">
        <div style="display:flex;gap:6px">
          <input type="text" name="file" id="queue-file-in" placeholder="G-Code Dateipfad oder Dateiname auf Drucker …" required/>
          ${App.state.is_desktop ? `<button type="button" class="btn btn-sm" onclick="desktopAction('pick_gcode').then(p=>{if(p)document.getElementById('queue-file-in').value=p;})">📂</button>` : ""}
        </div>
        <select name="pid">
          <option value="any">Beliebiger freier Drucker</option>
          ${printers.map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}
        </select>
        <input type="number" name="copies" min="1" max="100" value="1" title="Anzahl Kopien"/>
        <input type="text" name="mat" placeholder="Material (PLA)" value="PLA"/>
        <button type="submit" class="btn btn-primary">+ Einreihen</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Pos.</th><th>G-Code Auftrag</th><th>Material</th><th>Ziel-Drucker</th><th>Kopien</th><th style="text-align:right">Aktionen</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

/* ============================================================================
   View 6: Free-Form Multi-Camera & Display Matrix
   ============================================================================ */

function renderCameras() {
  const cams = App.ui.camsList || [];
  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.camera} Freie Multi-Kamera & Display-Leinwand</div>
        <div class="page-sub">Verschiebe und skaliere alle konfigurierten Drucker-Webcams und Touch-Displays frei auf dem Raster</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn" onclick="loadWebcams()">${ICONS.refresh} Streams neu suchen</button>
      </div>
    </div>

    ${cams.length ? `
      <div class="cam-workspace" id="cam-canvas">
        ${cams.map((c, idx) => {
          const col = idx % 2;
          const row = Math.floor(idx / 2);
          const left = 16 + col * 480;
          const top = 16 + row * 340;
          const isIframe = c.service === "iframe" || (c.url || "").includes(":18080") || (c.url || "").includes("/screen");
          return `
            <div class="cam-node" id="camnode-${idx}" style="left:${left}px;top:${top}px;width:460px;height:320px">
              <div class="cam-node-header" onmousedown="startCamDrag(event,'camnode-${idx}')">
                <span style="font-weight:800;font-size:12px"><span class="dot-live"></span> &nbsp;${esc(c.name)}</span>
                <a href="${esc(c.url)}" target="_blank" class="btn btn-sm" style="padding:2px 7px;font-size:10px">Extern ↗</a>
              </div>
              <div class="cam-node-body">
                ${isIframe
                  ? `<iframe src="${esc(c.url)}" style="width:100%;height:100%;border:0"></iframe>`
                  : `<img src="${esc(c.url)}" style="width:100%;height:100%;object-fit:contain" alt="${esc(c.name)}"/>`
                }
              </div>
            </div>
          `;
        }).join("")}
      </div>
    ` : `
      <div class="card" style="text-align:center;padding:44px 20px">
        <div style="font-size:17px;font-weight:800;margin-bottom:8px">Keine aktiven Webcam-Streams im Netzwerk gefunden</div>
        <div style="color:var(--text-sub);max-width:520px;margin:0 auto 16px auto">
          Stelle sicher, dass deine Klipper-Drucker eingeschaltet sind und in Moonraker unter <code>[webcam]</code> ein MJPEG/WebRTC-Stream eingetragen ist.
        </div>
        <button class="btn btn-primary" onclick="loadWebcams()">${ICONS.refresh} Erneut nach Kameras suchen</button>
      </div>
    `}
  `;
}

/* ============================================================================
   View 7: Maintenance & Component Wear Tracker
   ============================================================================ */

function renderMaintenance() {
  const printers = App.state.printers || [];
  const pid = App.ui.maintPrinterId || (printers[0] && printers[0].id) || "";
  const p = printers.find((x) => x.id === pid);
  const hours = Number((App.state.printer_hours || {})[pid] || (p && p.is_sim ? 184.5 : 42.0));
  const tasks = App.state.maintenance_tasks || [];
  const pMaint = (App.state.maintenance || {})[pid] || {};

  const rows = tasks.map((t) => {
    const rec = pMaint[t.key] || {};
    const lastReset = Number(rec.reset_at_hours || 0);
    const used = Math.max(0, hours - lastReset);
    const pct = Math.min(100, Math.round((used / Math.max(1, t.interval_h)) * 100));
    const col = pct < 75 ? "var(--ok)" : (pct < 100 ? "var(--warn)" : "var(--danger)");
    const statusLbl = pct < 75 ? "IN ORDNUNG" : (pct < 100 ? "BALD FÄLLIG" : "WARTUNG FÄLLIG");

    return `
      <tr>
        <td style="font-weight:700">${esc(t.title)}</td>
        <td class="mono">alle ${t.interval_h} h</td>
        <td>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:4px">
            <span><b>${used.toFixed(1)} h</b> seit letzter Wartung (${esc(rec.last_date || "Noch nie")})</span>
            <span class="mono" style="color:${col};font-weight:800">${pct}%</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%;background:${col}"></div></div>
        </td>
        <td><span class="badge" style="background:rgba(15,23,42,0.6);color:${col};border:1px solid ${col}">${statusLbl}</span></td>
        <td style="text-align:right;white-space:nowrap">
          <button class="btn btn-sm btn-success" onclick="App.apiPost('/api/maintenance/reset',{printer_id:'${esc(pid)}',key:'${esc(t.key)}',hours:${hours}}).then(()=>{App.toast('Wartung quittiert','ok');pollState();})">
            ✓ Erledigt
          </button>
          ${!t.builtin ? `<button class="btn btn-sm btn-danger" onclick="App.apiPost('/api/maintenance/delete_task',{key:'${esc(t.key)}'}).then(()=>pollState())">🗑</button>` : ""}
        </td>
      </tr>
    `;
  }).join("");

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.maintenance} Wartungs- & Verschleiß-Tracker</div>
        <div class="page-sub">Überwacht automatisch die realen Druckstunden aus Moonraker und protokolliert Komponenten-Service</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <select onchange="App.ui.maintPrinterId=this.value;renderContent()" style="min-width:210px">
          ${printers.map((pr) => `<option value="${esc(pr.id)}" ${pr.id === pid ? "selected" : ""}>${esc(pr.name)}</option>`).join("")}
        </select>
        <button class="btn btn-primary" onclick="loadHistoryStats()">${ICONS.refresh} Betriebsstunden synchronisieren</button>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:11px;font-weight:800;color:var(--text-sub)">ERFASSTE GESAMT-BETRIEBSZEIT (${p ? esc(p.name) : "—"})</div>
        <div class="mono" style="font-size:22px;font-weight:900;color:var(--accent)">${hours.toFixed(1)} Druckstunden</div>
      </div>
      <form style="display:flex;gap:8px;align-items:center" onsubmit="event.preventDefault();const f=this.elements;App.apiPost('/api/maintenance/add_task',{title:f.title.value,interval_h:Number(f.intv.value)}).then(()=>{this.reset();App.toast('Wartungsintervall angelegt','ok');pollState();})">
        <input type="text" name="title" placeholder="Eigenes Wartungsintervall (z.B. Aktivkohlefilter wechseln)" style="min-width:260px" required/>
        <input type="number" name="intv" value="100" min="5" max="5000" style="width:95px" title="Intervall in Stunden" required/>
        <button type="submit" class="btn">+ Intervall</button>
      </form>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Komponente / Aufgabe</th><th>Intervall</th><th>Verschleiß-Fortschritt</th><th>Status</th><th style="text-align:right">Quittieren</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

/* ============================================================================
   View 8: Statistics & 3D Print Quote / Pricing Calculator (NEW)
   ============================================================================ */

function copyQuoteText() {
  const q = App.ui.quoteResult;
  const f = App.ui.quoteForm;
  if (!q) return;
  const txt = [
    `=== 3D-DRUCK KALKULATION & ANGEBOT (${f.file_name || "Bauteil"}) ===`,
    `Stückzahl: ${q.copies}x | Druckzeit gesamt: ${q.hours_total} h | Filament inkl. Verschnitt: ${q.grams_effective} g`,
    `Materialkosten: ${q.material_eur.toFixed(2)} € | Energiekosten: ${q.energy_eur.toFixed(2)} € | Maschinenverschleiß: ${q.wear_eur.toFixed(2)} €`,
    `Arbeitszeit & Nachbearbeitung: ${q.labor_eur.toFixed(2)} € | Ausfallrisiko-Puffer: ${q.risk_eur.toFixed(2)} €`,
    `Herstellkosten (Selbstkosten): ${q.production_cost_eur.toFixed(2)} € (${q.unit_production_eur.toFixed(2)} € / Stück)`,
    `Verkaufspreis Netto: ${q.net_price_eur.toFixed(2)} € (${q.unit_net_eur.toFixed(2)} € / Stück)`,
    `Verkaufspreis Brutto (inkl. MwSt.): ${q.gross_price_eur.toFixed(2)} € (${q.unit_gross_eur.toFixed(2)} € / Stück)`,
  ].join("\n");
  navigator.clipboard.writeText(txt).then(() => App.toast("Angebot in die Zwischenablage kopiert!", "ok"));
}

function renderStats() {
  const tab = App.ui.statsTab || "analytics";
  const hd = App.ui.historyData || { total: { count: 0, success: 0, hours: 0, filament_g: 0, total_with_wear_eur: 0, per_month: {} }, jobs: [] };
  const tot = hd.total || {};
  const rates = App.state.cost_rates || {};

  const tabsBar = `
    <div class="tab-bar">
      <button class="tab-btn ${tab === 'analytics' ? 'active' : ''}" onclick="App.ui.statsTab='analytics';renderContent()">📊 Flotten-Statistik & Druckhistorie</button>
      <button class="tab-btn ${tab === 'quote' ? 'active' : ''}" onclick="App.ui.statsTab='quote';calculateQuoteNow();renderContent()">💶 Auftrags- & Verkaufspreis-Kalkulator (Quote Studio)</button>
    </div>
  `;

  if (tab === "quote") {
    const f = App.ui.quoteForm;
    const q = App.ui.quoteResult || {
      copies: 1, grams_effective: 68.3, hours_total: 2.5, material_eur: 1.64, energy_eur: 0.11, wear_eur: 0.38,
      labor_eur: 4.17, risk_eur: 0.17, production_cost_eur: 6.47, profit_eur: 2.26, net_price_eur: 8.73,
      vat_eur: 1.66, gross_price_eur: 10.39, unit_production_eur: 6.47, unit_net_eur: 8.73, unit_gross_eur: 10.39,
    };

    return `
      <div class="page-header">
        <div>
          <div class="page-title">💶 3D-Druck Angebots- & Verkaufspreis-Kalkulator</div>
          <div class="page-sub">Berechne exakte Selbstkosten, Strom, Verschleiß, Arbeitszeit, Ausfallrisiko und Kunden-Verkaufspreise</div>
        </div>
        <button class="btn btn-primary" onclick="copyQuoteText()">📋 Angebotstext kopieren</button>
      </div>
      ${tabsBar}
      <div class="bento-2">
        <div class="card" style="display:flex;flex-direction:column;gap:12px">
          <div style="font-weight:800;font-size:14.5px">1. Bauteil- & Prozess-Parameter</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Bauteilname / Projekt</label>
              <input type="text" value="${esc(f.file_name || 'Kundenauftrag Bauteil')}" oninput="App.ui.quoteForm.file_name=this.value"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Stückzahl (Kopien)</label>
              <input type="number" min="1" max="1000" value="${f.copies}" oninput="App.ui.quoteForm.copies=Number(this.value);calculateQuoteNow()"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Filamentgewicht pro Stück (g)</label>
              <input type="number" step="1" value="${f.grams}" oninput="App.ui.quoteForm.grams=Number(this.value);calculateQuoteNow()"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Druckzeit pro Stück (Stunden)</label>
              <input type="number" step="0.1" value="${f.hours}" oninput="App.ui.quoteForm.hours=Number(this.value);calculateQuoteNow()"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Filamentpreis (€ / kg)</label>
              <input type="number" step="0.5" value="${rates.eur_kg}" oninput="App.state.cost_rates.eur_kg=Number(this.value);App.apiPost('/api/costs/save',{eur_kg:Number(this.value)});calculateQuoteNow()"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Strompreis (€ / kWh) & Watt</label>
              <div style="display:flex;gap:6px">
                <input type="number" step="0.01" value="${rates.kwh}" oninput="App.state.cost_rates.kwh=Number(this.value);calculateQuoteNow()"/>
                <input type="number" step="10" value="${rates.watts}" oninput="App.state.cost_rates.watts=Number(this.value);calculateQuoteNow()"/>
              </div>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Rüst- & Nachbearbeitungszeit (Min.)</label>
              <input type="number" step="1" value="${f.prep_mins}" oninput="App.ui.quoteForm.prep_mins=Number(this.value);calculateQuoteNow()"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Gewinnmarge (%) & Ausfallrisiko (%)</label>
              <div style="display:flex;gap:6px">
                <input type="number" step="1" value="${rates.margin_pct}" oninput="App.state.cost_rates.margin_pct=Number(this.value);calculateQuoteNow()"/>
                <input type="number" step="1" value="${rates.fail_pct}" oninput="App.state.cost_rates.fail_pct=Number(this.value);calculateQuoteNow()"/>
              </div>
            </div>
          </div>
        </div>

        <div class="card" style="display:flex;flex-direction:column;gap:12px">
          <div style="font-weight:800;font-size:14.5px">2. Live Kalkulations-Ergebnis (${q.copies}× Stück)</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
            <div class="telemetry-cell">
              <div class="telemetry-lbl">SELBSTKOSTEN</div>
              <div class="telemetry-val mono" style="color:var(--accent)">${q.production_cost_eur.toFixed(2)} €</div>
              <div style="font-size:11px;color:var(--text-sub)">${q.unit_production_eur.toFixed(2)} € / Stk.</div>
            </div>
            <div class="telemetry-cell">
              <div class="telemetry-lbl">NETTO-VERKAUF</div>
              <div class="telemetry-val mono" style="color:#10B981">${q.net_price_eur.toFixed(2)} €</div>
              <div style="font-size:11px;color:var(--text-sub)">+${q.profit_eur.toFixed(2)} € Gewinn</div>
            </div>
            <div class="telemetry-cell" style="border-color:var(--accent)">
              <div class="telemetry-lbl">BRUTTO (INKL. MWST)</div>
              <div class="telemetry-val mono" style="font-size:18px;color:#F59E0B">${q.gross_price_eur.toFixed(2)} €</div>
              <div style="font-size:11px;color:var(--text-sub)">${q.unit_gross_eur.toFixed(2)} € / Stk.</div>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <tbody>
                <tr><td>Materialkosten (${q.grams_effective} g inkl. Verschnitt)</td><td class="mono" style="text-align:right;font-weight:700">${q.material_eur.toFixed(2)} €</td></tr>
                <tr><td>Energiekosten (${q.hours_total} Druckstunden @ ${rates.watts}W)</td><td class="mono" style="text-align:right;font-weight:700">${q.energy_eur.toFixed(2)} €</td></tr>
                <tr><td>Maschinen-Abschreibung & Verschleiß</td><td class="mono" style="text-align:right;font-weight:700">${q.wear_eur.toFixed(2)} €</td></tr>
                <tr><td>Arbeitszeit (Vorbereitung & Support-Entfernung)</td><td class="mono" style="text-align:right;font-weight:700">${q.labor_eur.toFixed(2)} €</td></tr>
                <tr><td>Ausfallrisiko-Aufschlag (${rates.fail_pct}%)</td><td class="mono" style="text-align:right;font-weight:700">${q.risk_eur.toFixed(2)} €</td></tr>
                <tr><td><b>Kalkulatorischer Gewinn (${rates.margin_pct}%)</b></td><td class="mono" style="text-align:right;font-weight:800;color:var(--ok)">+${q.profit_eur.toFixed(2)} €</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // Analytics View
  const jobsRows = (hd.jobs || []).slice(0, 40).map((j) => `
    <tr>
      <td style="font-weight:700">${esc(j.filename)}</td>
      <td>${esc(j.printer_name || "—")}</td>
      <td><span class="badge" style="background:var(--bg-elevated-2);color:${j.status === 'completed' ? 'var(--ok)' : 'var(--warn)'}">${esc(j.status)}</span></td>
      <td class="mono">${j.hours || 0} h</td>
      <td class="mono">${j.grams || 0} g</td>
      <td class="mono" style="font-weight:800;color:var(--accent)">${Number(j.cost_eur || 0).toFixed(2)} €</td>
    </tr>
  `).join("") || `<tr><td colspan="6" style="text-align:center;color:var(--text-sub)">Noch keine abgeschlossenen Druckaufträge in der Historie.</td></tr>`;

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.stats} Statistik, Energiekosten & Angebots-Kalkulator</div>
        <div class="page-sub">Auswertung aller Druckaufträge aus Moonraker inkl. Strom-, Material- und Verschleißrechnung</div>
      </div>
      <button class="btn" onclick="loadHistoryStats()">${ICONS.refresh} Aktualisieren</button>
    </div>
    ${tabsBar}
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px">
      <div class="card"><div class="telemetry-lbl">DRUCKAUFTRÄGE</div><div class="telemetry-val mono" style="font-size:22px;color:var(--accent)">${tot.count || 0}</div></div>
      <div class="card"><div class="telemetry-lbl">ERFOLGSQUOTE</div><div class="telemetry-val mono" style="font-size:22px;color:var(--ok)">${Math.round(tot.success || 0)}%</div></div>
      <div class="card"><div class="telemetry-lbl">GESAMTDAUER</div><div class="telemetry-val mono" style="font-size:22px;color:#8B5CF6">${Number(tot.hours || 0).toFixed(1)} h</div></div>
      <div class="card"><div class="telemetry-lbl">VERBRAUCHTES FILAMENT</div><div class="telemetry-val mono" style="font-size:22px;color:#F59E0B">${(Number(tot.filament_g || 0) / 1000).toFixed(2)} kg</div></div>
      <div class="card"><div class="telemetry-lbl">GESAMTKOSTEN</div><div class="telemetry-val mono" style="font-size:22px;color:#F43F5E">${Number(tot.total_with_wear_eur || tot.total_eur || 0).toFixed(2)} €</div></div>
    </div>
    <div class="card">
      <div style="font-weight:800;font-size:14px;margin-bottom:10px">Letzte Druckaufträge über die gesamte Flotte</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Datei</th><th>Drucker</th><th>Status</th><th>Dauer</th><th>Filament</th><th>Gesamtkosten</th></tr></thead>
          <tbody>${jobsRows}</tbody>
        </table>
      </div>
    </div>
  `;
}

/* ============================================================================
   View 9: 3D Model & G-Code Library
   ============================================================================ */

function renderLibrary() {
  const lib = App.ui.libraryData || { files: [], subfolders: [], models_dir: "" };
  const files = lib.files || [];
  const sel = files.find((f) => f.path === App.ui.selectedLibPath) || files[0] || null;

  const cards = files.map((f) => {
    const isSel = sel && sel.path === f.path;
    return `
      <div class="card card-interactive" style="padding:12px;border-color:${isSel ? 'var(--accent)' : 'var(--border)'}"
        onclick="App.ui.selectedLibPath='${esc(f.path)}';renderContent()">
        <div style="height:110px;background:var(--bg-input);border-radius:9px;display:flex;align-items:center;justify-content:center;margin-bottom:9px;overflow:hidden;border:1px solid var(--border-subtle)">
          ${f.thumb_b64
            ? `<img src="${f.thumb_b64}" style="max-width:100%;max-height:100%;object-fit:contain"/>`
            : `<span class="badge" style="font-size:13px;background:var(--bg-elevated-2);color:var(--accent)">${esc((f.ext || "").replace(".", "").toUpperCase())}</span>`
          }
        </div>
        <div style="font-weight:700;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${esc(f.name)}">${esc(f.name)}</div>
        <div style="font-size:11px;color:var(--text-sub);margin-top:2px">${esc(f.size)} · ${esc(f.modified)}</div>
      </div>
    `;
  }).join("") || `
    <div class="card" style="grid-column:1/-1;text-align:center;padding:36px">
      <div style="font-weight:800;font-size:15px;margin-bottom:6px">Noch keine 3D-Modelle oder G-Codes in diesem Ordner</div>
      <div style="font-size:12.5px;color:var(--text-sub)">Importiere eigene <code>.3mf</code>, <code>.stl</code>, <code>.step</code> oder <code>.gcode</code> Dateien oder lade Modelle über „Modelle entdecken“ herunter.</div>
    </div>
  `;

  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.library} 3D-Modell- & G-Code-Bibliothek</div>
        <div class="page-sub">Ordner: <code>${esc(lib.models_dir || App.state.models_dir)}</code> · Automatische 3MF- & G-Code-Vorschaubilder</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${App.state.is_desktop ? `
          <button class="btn" onclick="desktopAction('open_folder',{path:App.state.models_dir})">📂 Im Dateimanager öffnen</button>
          <button class="btn btn-primary" onclick="desktopAction('import_files').then(()=>loadLibrary())">${ICONS.plus} Dateien importieren</button>
        ` : ""}
        <button class="btn" onclick="const n=prompt('Name für neuen Unterordner:');if(n)App.apiPost('/api/library/action',{action:'create_subfolder',name:n}).then(()=>loadLibrary())">+ Neuer Ordner</button>
        <button class="btn" onclick="loadLibrary()">${ICONS.refresh}</button>
      </div>
    </div>

    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <input type="text" placeholder="Dateiname in Bibliothek suchen …" value="${esc(App.ui.libQuery)}"
        oninput="App.ui.libQuery=this.value;loadLibrary()" style="max-width:340px"/>
      <select onchange="App.ui.libCat=this.value;loadLibrary()" style="max-width:220px">
        <option value="all" ${App.ui.libCat === "all" ? "selected" : ""}>Alle Dateitypen</option>
        <option value="models" ${App.ui.libCat === "models" ? "selected" : ""}>3D-Modelle (.3mf, .stl, .step, .obj)</option>
        <option value="gcode" ${App.ui.libCat === "gcode" ? "selected" : ""}>G-Code (.gcode)</option>
        <option value="archives" ${App.ui.libCat === "archives" ? "selected" : ""}>ZIP-Archive (.zip)</option>
      </select>
      <select onchange="App.ui.libSub=this.value;loadLibrary()" style="max-width:200px">
        <option value="">Alle Unterordner</option>
        ${(lib.subfolders || []).map((sf) => `<option value="${esc(sf)}" ${App.ui.libSub === sf ? "selected" : ""}>${esc(sf)}</option>`).join("")}
      </select>
    </div>

    <div style="display:grid;grid-template-columns:1fr 320px;gap:16px;align-items:start">
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:12px">
        ${cards}
      </div>

      <!-- Right Inspector Card -->
      <div class="card" style="display:flex;flex-direction:column;gap:10px;position:sticky;top:0">
        ${sel ? `
          <div style="height:165px;background:var(--bg-input);border-radius:10px;display:flex;align-items:center;justify-content:center;overflow:hidden;border:1px solid var(--border)">
            ${sel.thumb_b64
              ? `<img src="${sel.thumb_b64}" style="max-width:100%;max-height:100%;object-fit:contain"/>`
              : `<span class="badge" style="font-size:16px;background:var(--bg-elevated-2);color:var(--accent)">${esc((sel.ext || "").replace(".", "").toUpperCase())}</span>`
            }
          </div>
          <div style="font-weight:800;font-size:14.5px;word-break:break-all">${esc(sel.name)}</div>
          <div style="font-size:12px;color:var(--text-sub);display:flex;flex-direction:column;gap:3px">
            <div>Größe: <b>${esc(sel.size)}</b> · Geändert: ${esc(sel.modified)}</div>
            ${Object.entries(sel.meta || {}).map(([k, v]) => `<div>${esc(k)}: <b>${esc(v)}</b></div>`).join("")}
          </div>

          <div style="display:flex;flex-direction:column;gap:7px;margin-top:6px">
            ${[".3mf", ".stl", ".step", ".stp", ".obj"].includes(sel.ext) ? `
              <button class="btn btn-primary" onclick="App.apiPost('/api/library/action',{action:'open_slicer',path:'${esc(sel.path)}'}).then(r=>App.toast(r.error?r.error:'Geöffnet in '+r.slicer,r.error?'error':'ok'))">
                🚀 Im Slicer öffnen (Orca / Prusa / Bambu)
              </button>
            ` : ""}
            ${sel.ext === ".gcode" ? `
              <button class="btn btn-primary" onclick="openSendLibraryGcodeModal('${esc(sel.path)}','${esc(sel.name)}')">
                ▶ An Drucker senden & starten …
              </button>
              <button class="btn" onclick="loadGcodePreview({path:'${esc(sel.path)}'});navigate('gcode')">
                🔍 Im G-Code Layer-Studio prüfen
              </button>
              <button class="btn" onclick="if(${JSON.stringify(sel.parsed || {})}.grams){App.ui.quoteForm.grams=${(sel.parsed && sel.parsed.grams) || 50};App.ui.quoteForm.hours=${(sel.parsed && sel.parsed.hours) || 2};App.ui.quoteForm.file_name='${esc(sel.name)}';}App.ui.statsTab='quote';navigate('stats')">
                💶 Im Angebots-Kalkulator berechnen
              </button>
            ` : ""}
            ${sel.ext === ".zip" ? `
              <button class="btn btn-primary" onclick="App.apiPost('/api/library/action',{action:'unzip',path:'${esc(sel.path)}'}).then(r=>{App.toast(r.count+' Dateien entpackt','ok');loadLibrary();})">
                📦 ZIP-Archiv hier entpacken
              </button>
            ` : ""}
            <button class="btn" onclick="const n=prompt('Neuer Dateiname:','${esc(sel.name)}');if(n)App.apiPost('/api/library/action',{action:'rename',path:'${esc(sel.path)}',new_name:n}).then(()=>loadLibrary())">✏ Umbenennen</button>
            <button class="btn" onclick="App.apiPost('/api/library/action',{action:'duplicate',path:'${esc(sel.path)}'}).then(()=>loadLibrary())">⧉ Duplizieren</button>
            <button class="btn btn-danger" onclick="if(confirm('${esc(sel.name)} wirklich löschen?'))App.apiPost('/api/library/action',{action:'delete',path:'${esc(sel.path)}'}).then(()=>{App.ui.selectedLibPath=null;loadLibrary();})">🗑 Datei löschen</button>
          </div>
        ` : `<div style="color:var(--text-sub);text-align:center;padding:24px 0">Wähle links eine Datei aus</div>`}
      </div>
    </div>
  `;
}

/* ============================================================================
   View 10: Discover 3D Models (Integrated Persistent-Cookie Browser Hub)
   ============================================================================ */

function openModelPlatform(url, idx) {
  if (App.state.is_desktop) {
    desktopAction("open_model_browser", { url, index: idx });
  } else {
    window.open(url, "_blank");
  }
}

function renderDiscover() {
  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.globe} 3D-Modelle entdecken & direkt importieren</div>
        <div class="page-sub">
          ${App.state.is_desktop
            ? `Integrierter 3D-Browser mit persistenten Login-Cookies — Alle Downloads landen automatisch in <code>${esc(App.state.models_dir)}</code>`
            : "Direktzugriff auf die wichtigsten 3D-Druck-Plattformen"}
        </div>
      </div>
      ${App.state.is_desktop ? `
        <button class="btn btn-primary btn-lg" onclick="openModelPlatform('https://www.printables.com', 0)">
          🌐 Integrierten 3D-Modell-Browser öffnen
        </button>
      ` : ""}
    </div>

    <div class="grid-cards">
      ${MODEL_SITES.map((s, idx) => `
        <div class="card card-interactive" onclick="openModelPlatform('${esc(s.url)}', ${idx})">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:17px;font-weight:900;color:${s.color}">${esc(s.name)}</span>
            <span class="badge" style="background:var(--bg-elevated-2);color:${s.color};border:1px solid ${s.color}">${esc(s.tag)}</span>
          </div>
          <div style="font-size:12.5px;color:var(--text-sub);margin-bottom:14px">${esc(s.desc)}</div>
          <button class="btn btn-sm btn-primary" style="width:100%">
            ${App.state.is_desktop ? `In PrintBoard Browser öffnen (${esc(s.name)})` : `${esc(s.name)} im Tab öffnen ↗`}
          </button>
        </div>
      `).join("")}
    </div>
  `;
}

/* ============================================================================
   View 11: Settings & Studio Configuration
   ============================================================================ */

function renderSettings() {
  const realPrinters = (App.state.printers || []).filter((p) => !p.is_sim);
  return `
    <div class="page-header">
      <div>
        <div class="page-title">${ICONS.settings} Studio Einstellungen & Systemkonfiguration</div>
        <div class="page-sub">Design-Themes, Drucker-Flotte, Slicer-Pfad, Spoolman, Webhooks und Demo-Fuhrpark</div>
      </div>
    </div>

    <div class="bento-2">
      <div style="display:flex;flex-direction:column;gap:16px">
        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:10px">🎨 Erscheinungsbild & Bedienmodus</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
            ${[
              ["obsidian", "Obsidian Cyber (Cyan/Dark)"],
              ["carbon", "Voron / Bambu Carbon (Orange)"],
              ["amethyst", "Amethyst Pro (Linear Violet)"],
              ["light", "Daylight Studio (Clean Light)"],
            ].map(([k, lbl]) => `
              <button class="btn ${App.state.theme === k ? 'btn-primary' : ''}" onclick="setTheme('${k}');renderContent()">${lbl}</button>
            `).join("")}
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
              <input type="checkbox" ${App.state.sim_enabled ? "checked" : ""} onchange="toggleSimMode(this.checked)"/>
              <span><b>Virtuellen Demo-Fuhrpark anzeigen</b> (3 interaktive Simulations-Drucker mit Bed-Mesh & Exclude-Object)</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
              <input type="checkbox" ${App.state.autostart ? "checked" : ""} onchange="App.apiPost('/api/settings/save',{autostart:this.checked}).then(()=>{App.toast('Autostart aktualisiert','ok');pollState();})"/>
              <span><b>PrintBoard beim Systemstart automatisch starten</b></span>
            </label>
          </div>
        </div>

        <div class="card">
          <div style="font-weight:800;font-size:14.5px;margin-bottom:10px">📁 3D-Bibliothek & Slicer-Integration</div>
          <form style="display:flex;flex-direction:column;gap:10px" onsubmit="event.preventDefault();const f=this.elements;App.apiPost('/api/settings/save',{models_dir:f.mdir.value,slicer_cmd:f.slicer.value,spoolman_url:f.smurl.value,discord:f.discord.value,tg_token:f.tgtoken.value,tg_chat:f.tgchat.value}).then(()=>{App.toast('Einstellungen gespeichert','ok');pollState();})">
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Modell- & Download-Ordner</label>
              <div style="display:flex;gap:6px">
                <input type="text" name="mdir" id="set-mdir" value="${esc(App.state.models_dir)}"/>
                ${App.state.is_desktop ? `<button type="button" class="btn btn-sm" onclick="desktopAction('pick_folder').then(d=>{if(d)document.getElementById('set-mdir').value=d;})">Ordner wählen …</button>` : ""}
              </div>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Slicer-Befehl (leer = Automatik: ${(App.state.detected_slicers || []).map((s) => s.name).join(", ") || "OrcaSlicer / PrusaSlicer / Bambu Studio"})</label>
              <input type="text" name="slicer" value="${esc(App.state.slicer_cmd)}" placeholder="z.B. orca-slicer oder leer lassen für Automatik"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Spoolman Server-URL</label>
              <input type="text" name="smurl" value="${esc(App.state.spoolman_url)}" placeholder="z.B. http://192.168.178.170:7912"/>
            </div>
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Discord Webhook-URL (für Server-Benachrichtigungen)</label>
              <div style="display:flex;gap:6px">
                <input type="text" name="discord" id="set-discord" value="${esc((App.state.notify_cfg || {}).discord || '')}" placeholder="https://discord.com/api/webhooks/..."/>
                <button type="button" class="btn btn-sm" onclick="App.apiPost('/api/notify/test',{discord:document.getElementById('set-discord').value}).then(r=>App.toast(r.error?r.error:'Discord Test gesendet!',r.error?'error':'ok'))">Testen</button>
              </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <div>
                <label style="font-size:11.5px;color:var(--text-sub)">Telegram Bot-Token</label>
                <input type="text" name="tgtoken" value="${esc((App.state.notify_cfg || {}).tg_token || '')}"/>
              </div>
              <div>
                <label style="font-size:11.5px;color:var(--text-sub)">Telegram Chat-ID</label>
                <input type="text" name="tgchat" value="${esc((App.state.notify_cfg || {}).tg_chat || '')}"/>
              </div>
            </div>
            <button type="submit" class="btn btn-primary">Alle Einstellungen speichern</button>
          </form>
        </div>
      </div>

      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
          <div style="font-weight:800;font-size:14.5px">🖨 Konfigurierte Hardware-Drucker (${realPrinters.length})</div>
          <button class="btn btn-sm btn-primary" onclick="openPrinterModal()">${ICONS.plus} Drucker hinzufügen</button>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px">
          ${realPrinters.map((p) => `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:var(--bg-elevated);border-radius:10px;border:1px solid var(--border-subtle)">
              <div>
                <div style="font-weight:800">${esc(p.name)}</div>
                <div style="font-size:11.5px;color:var(--text-sub)">${esc(p.host)}:${p.port} · ${p.printer_type === "bambu" ? "Bambu Lab LAN" : "Klipper / Moonraker"}</div>
              </div>
              <div style="display:flex;gap:6px">
                <button class="btn btn-sm" onclick="openPrinterModal('${esc(p.id)}')">Bearbeiten</button>
                <button class="btn btn-sm btn-danger" onclick="if(confirm('${esc(p.name)} wirklich entfernen?'))App.apiPost('/api/printers/delete',{id:'${esc(p.id)}'}).then(()=>pollState())">🗑</button>
              </div>
            </div>
          `).join("") || `<div style="color:var(--text-sub);font-size:12.5px">Noch kein physischer Drucker gespeichert. Klicke oben auf „Drucker hinzufügen“.</div>`}
        </div>
      </div>
    </div>
  `;
}

/* ============================================================================
   Modals (Add/Edit Printer with LAN Scanner, Spool Assignment, New Spool, Command Palette)
   ============================================================================ */

function openPrinterModal(printerId = null) {
  const existing = (App.state.printers || []).find((p) => p.id === printerId);
  App.ui.modal = {
    type: "printer",
    data: existing ? { ...existing } : { name: "", host: "", port: 80, printer_type: "moonraker", token: "", bambu_serial: "", bambu_access_code: "", display_url: "", tls: false },
    discovered: [],
    scanning: false,
    testMsg: "",
  };
  renderModal();
}

function openAssignSpoolModal(printerId) {
  App.ui.modal = { type: "assign_spool", printerId };
  renderModal();
}

function openAssignSpoolToPrinterModal(spoolId) {
  App.ui.modal = { type: "assign_spool_to_printer", spoolId };
  renderModal();
}

function openNewSpoolModal() {
  App.ui.modal = { type: "new_spool" };
  renderModal();
}

function openSendLibraryGcodeModal(filePath, fileName) {
  App.ui.modal = { type: "send_gcode", filePath, fileName };
  renderModal();
}

function closeModal() {
  App.ui.modal = null;
  renderModal();
}

function renderModal() {
  const root = document.getElementById("modal-root");
  if (!root) return;
  const m = App.ui.modal;
  if (!m) {
    root.innerHTML = "";
    return;
  }

  if (m.type === "printer") {
    const d = m.data;
    const isBambu = d.printer_type === "bambu";
    root.innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
        <div class="modal-panel">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
            <div style="font-size:17px;font-weight:800">${d.id ? "Drucker bearbeiten" : "Neuen 3D-Drucker verbinden"}</div>
            <button class="btn btn-sm" onclick="closeModal()">✕</button>
          </div>

          <div style="display:flex;flex-direction:column;gap:10px">
            <div>
              <label style="font-size:11.5px;color:var(--text-sub)">Drucker-System</label>
              <select onchange="App.ui.modal.data.printer_type=this.value;App.ui.modal.data.port=(this.value==='bambu'?8883:80);renderModal()">
                <option value="moonraker" ${!isBambu ? "selected" : ""}>Klipper / Moonraker (Fluidd, Mainsail, Creality, Qidi, Voron, RatRig)</option>
                <option value="bambu" ${isBambu ? "selected" : ""}>Bambu Lab (X1, P1, A1 Serie — LAN MQTT)</option>
              </select>
            </div>

            ${!isBambu ? `
              <div style="display:flex;gap:8px;align-items:center">
                <button class="btn btn-sm" style="width:100%" onclick="this.textContent='Scanne lokales Netzwerk …';App.apiGet('/api/printers/discover').then(r=>{App.ui.modal.discovered=r.found||[];renderModal();})">
                  🔍 Lokales Netzwerk automatisch nach Klipper / Moonraker Druckern scannen
                </button>
              </div>
              ${(m.discovered && m.discovered.length) ? `
                <select onchange="const item=App.ui.modal.discovered[this.value];if(item){App.ui.modal.data.name=item.name;App.ui.modal.data.host=item.host;App.ui.modal.data.port=item.port;renderModal();}">
                  <option value="">✓ ${m.discovered.length} Drucker gefunden — zum Übernehmen auswählen …</option>
                  ${m.discovered.map((it, idx) => `<option value="${idx}">${esc(it.name)} (${esc(it.host)}:${it.port})</option>`).join("")}
                </select>
              ` : ""}
            ` : ""}

            <div style="display:grid;grid-template-columns:1.2fr 1.2fr 0.6fr;gap:8px">
              <div>
                <label style="font-size:11.5px;color:var(--text-sub)">Anzeigename</label>
                <input type="text" id="mp-name" value="${esc(d.name)}" placeholder="z.B. Voron 2.4"/>
              </div>
              <div>
                <label style="font-size:11.5px;color:var(--text-sub)">IP-Adresse / Hostname</label>
                <input type="text" id="mp-host" value="${esc(d.host)}" placeholder="z.B. 192.168.178.55"/>
              </div>
              <div>
                <label style="font-size:11.5px;color:var(--text-sub)">Port</label>
                <input type="number" id="mp-port" value="${d.port || (isBambu ? 8883 : 80)}"/>
              </div>
            </div>

            ${isBambu ? `
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                <div>
                  <label style="font-size:11.5px;color:var(--text-sub)">Seriennummer (Bambu)</label>
                  <input type="text" id="mp-serial" value="${esc(d.bambu_serial || '')}" placeholder="01P00A..."/>
                </div>
                <div>
                  <label style="font-size:11.5px;color:var(--text-sub)">LAN Access Code</label>
                  <input type="text" id="mp-code" value="${esc(d.bambu_access_code || '')}" placeholder="8-stelliger Code"/>
                </div>
              </div>
            ` : `
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                <div>
                  <label style="font-size:11.5px;color:var(--text-sub)">API-Key / Token (optional)</label>
                  <input type="text" id="mp-token" value="${esc(d.token || '')}" placeholder="Optional"/>
                </div>
                <div>
                  <label style="font-size:11.5px;color:var(--text-sub)">Display-URL (optional)</label>
                  <input type="text" id="mp-disp" value="${esc(d.display_url || '')}" placeholder="z.B. http://...:18080/"/>
                </div>
              </div>
            `}

            ${m.testMsg ? `<div style="font-size:12px;padding:8px 10px;border-radius:8px;background:var(--bg-elevated);color:var(--accent)">${esc(m.testMsg)}</div>` : ""}

            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px">
              <button class="btn" onclick="
                const payload={
                  id:App.ui.modal.data.id,
                  printer_type:App.ui.modal.data.printer_type,
                  name:document.getElementById('mp-name').value,
                  host:document.getElementById('mp-host').value,
                  port:Number(document.getElementById('mp-port').value),
                  token:document.getElementById('mp-token')?document.getElementById('mp-token').value:'',
                  display_url:document.getElementById('mp-disp')?document.getElementById('mp-disp').value:'',
                  bambu_serial:document.getElementById('mp-serial')?document.getElementById('mp-serial').value:'',
                  bambu_access_code:document.getElementById('mp-code')?document.getElementById('mp-code').value:'',
                };
                Object.assign(App.ui.modal.data,payload);
                App.apiPost('/api/printers/test',payload).then(r=>{App.ui.modal.testMsg=r.ok?r.message:('Fehler: '+r.error);renderModal();});
              ">Verbindung testen</button>
              <button class="btn btn-primary" onclick="
                const payload={
                  id:App.ui.modal.data.id,
                  printer_type:App.ui.modal.data.printer_type,
                  name:document.getElementById('mp-name').value,
                  host:document.getElementById('mp-host').value,
                  port:Number(document.getElementById('mp-port').value),
                  token:document.getElementById('mp-token')?document.getElementById('mp-token').value:'',
                  display_url:document.getElementById('mp-disp')?document.getElementById('mp-disp').value:'',
                  bambu_serial:document.getElementById('mp-serial')?document.getElementById('mp-serial').value:'',
                  bambu_access_code:document.getElementById('mp-code')?document.getElementById('mp-code').value:'',
                };
                App.apiPost('/api/printers/add',payload).then(r=>{if(r.error)App.toast(r.error,'error');else{closeModal();App.toast('Drucker gespeichert','ok');pollState();}});
              ">Speichern</button>
            </div>
          </div>
        </div>
      </div>
    `;
  } else if (m.type === "assign_spool") {
    const spools = App.state.spools || [];
    root.innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
        <div class="modal-panel" style="max-width:520px">
          <div style="font-size:16px;font-weight:800;margin-bottom:12px">Spoolman-Spule für Drucker wählen</div>
          <div style="display:flex;flex-direction:column;gap:7px;max-height:380px;overflow-y:auto">
            <button class="btn" style="justify-content:flex-start" onclick="App.apiPost('/api/spoolman/assign',{printer_id:'${esc(m.printerId)}',spool_id:null}).then(()=>{closeModal();pollState();})">
              — Zuweisung aufheben (Keine Spule) —
            </button>
            ${spools.map((s) => `
              <button class="btn" style="justify-content:space-between" onclick="App.apiPost('/api/spoolman/assign',{printer_id:'${esc(m.printerId)}',spool_id:${s.id}}).then(()=>{closeModal();App.toast('Spule zugewiesen','ok');pollState();})">
                <span style="display:flex;align-items:center;gap:8px">
                  <span style="width:12px;height:12px;border-radius:50%;background:${spoolColor(s)};display:inline-block"></span>
                  <b>${esc(spoolName(s))}</b>
                </span>
                <span class="mono">${Math.round(s.remaining_weight || 0)} g</span>
              </button>
            `).join("")}
          </div>
        </div>
      </div>
    `;
  } else if (m.type === "assign_spool_to_printer") {
    const printers = App.state.printers || [];
    root.innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
        <div class="modal-panel" style="max-width:460px">
          <div style="font-size:16px;font-weight:800;margin-bottom:12px">Auf welchen Drucker soll Spule #${m.spoolId} geladen werden?</div>
          <div style="display:flex;flex-direction:column;gap:8px">
            ${printers.map((p) => `
              <button class="btn btn-primary" onclick="App.apiPost('/api/spoolman/assign',{printer_id:'${esc(p.id)}',spool_id:${m.spoolId}}).then(()=>{closeModal();App.toast('Spule auf '+${JSON.stringify(p.name)}+' geladen','ok');pollState();})">
                🖨 ${esc(p.name)} (${esc(p.host)})
              </button>
            `).join("")}
          </div>
        </div>
      </div>
    `;
  } else if (m.type === "new_spool") {
    root.innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
        <div class="modal-panel" style="max-width:520px">
          <div style="font-size:16px;font-weight:800;margin-bottom:12px">Neues Filament & Spule anlegen</div>
          <form style="display:flex;flex-direction:column;gap:10px" onsubmit="event.preventDefault();const f=this.elements;App.apiPost('/api/spoolman/filament/create',{name:f.name.value,vendor_name:f.vendor.value,material:f.mat.value,color_hex:f.col.value.replace('#',''),weight:Number(f.weight.value),price:Number(f.price.value),settings_extruder_temp:Number(f.ntemp.value),settings_bed_temp:Number(f.btemp.value)}).then(()=>{closeModal();App.toast('Spule angelegt','ok');pollState();})">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <div><label style="font-size:11.5px;color:var(--text-sub)">Bezeichnung</label><input type="text" name="name" placeholder="z.B. PLA Tough Cyan" required/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Hersteller</label><input type="text" name="vendor" value="Polymaker"/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Material</label><input type="text" name="mat" value="PLA" required/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Farbcode (Hex)</label><input type="text" name="col" value="#00E5FF"/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Netto-Gewicht (g)</label><input type="number" name="weight" value="1000"/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Kaufpreis (€)</label><input type="number" step="0.1" name="price" value="22.90"/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Düsentemperatur (°C)</label><input type="number" name="ntemp" value="215"/></div>
              <div><label style="font-size:11.5px;color:var(--text-sub)">Betttemperatur (°C)</label><input type="number" name="btemp" value="60"/></div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px">
              <button type="button" class="btn" onclick="closeModal()">Abbrechen</button>
              <button type="submit" class="btn btn-primary">Anlegen</button>
            </div>
          </form>
        </div>
      </div>
    `;
  } else if (m.type === "send_gcode") {
    const printers = App.state.printers || [];
    root.innerHTML = `
      <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
        <div class="modal-panel" style="max-width:480px">
          <div style="font-size:16px;font-weight:800;margin-bottom:6px">„${esc(m.fileName)}“ an Drucker senden</div>
          <div style="font-size:12px;color:var(--text-sub);margin-bottom:12px">Wähle den Ziel-Drucker und ob der Druck sofort starten soll:</div>
          <div style="display:flex;flex-direction:column;gap:8px">
            ${printers.map((p) => `
              <div style="display:flex;align-items:center;justify-content:space-between;padding:9px 12px;background:var(--bg-elevated);border-radius:9px">
                <span style="font-weight:700">${esc(p.name)}</span>
                <div style="display:flex;gap:6px">
                  <button class="btn btn-sm" onclick="App.apiPost('/api/library/action',{action:'upload_to_printer',printer_id:'${esc(p.id)}',path:'${esc(m.filePath)}',start:false}).then(()=>{closeModal();App.toast('Hochgeladen auf '+${JSON.stringify(p.name)},'ok');})">Nur Upload</button>
                  <button class="btn btn-sm btn-primary" onclick="App.apiPost('/api/library/action',{action:'upload_to_printer',printer_id:'${esc(p.id)}',path:'${esc(m.filePath)}',start:true}).then(()=>{closeModal();App.toast('Druck gestartet auf '+${JSON.stringify(p.name)},'ok');pollState();})">▶ Upload & Start</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>
    `;
  }
}

/* ============================================================================
   Command Palette (Ctrl+K)
   ============================================================================ */

function renderCommandPalette() {
  const root = document.getElementById("cmd-root");
  if (!root) return;
  if (!App.ui.cmdOpen) {
    root.innerHTML = "";
    return;
  }

  const q = (App.ui.cmdQuery || "").toLowerCase();
  const cmds = [
    { label: "Modus wechseln: Easy Mode (Einfache 1-Klick Oberfläche)", run: () => setMode("easy") },
    { label: "Modus wechseln: Advanced Pro Mode (Volle Telemetrie & Farm)", run: () => setMode("advanced") },
    { label: "Ansicht: Flotten-Übersicht & Dashboard", run: () => navigate("dashboard") },
    { label: "Ansicht: G-Code Layer & Toolpath Studio (2D/3D)", run: () => navigate("gcode") },
    { label: "Ansicht: Spoolman & Filament-Trocknungs-Assistent", run: () => navigate("spoolman") },
    { label: "Ansicht: Druck-Warteschlange & Batch-Dispatcher", run: () => navigate("queue") },
    { label: "Ansicht: Freie Kamera-Matrix", run: () => navigate("cameras") },
    { label: "Ansicht: Wartungs- & Verschleiß-Tracker", run: () => navigate("maintenance") },
    { label: "Ansicht: Statistik & Angebots-Kalkulator (Quote Studio)", run: () => { App.ui.statsTab = "quote"; navigate("stats"); } },
    { label: "Ansicht: 3D-Modell- & G-Code-Bibliothek", run: () => navigate("library") },
    { label: "Ansicht: 3D-Modelle im Web entdecken", run: () => navigate("discover") },
    { label: "Aktion: Neuen Drucker hinzufügen", run: () => openPrinterModal() },
    { label: "Aktion: Alle freien Drucker auf PLA vorheizen (210/60°C)", run: () => sendBatchControl("all_idle", "preheat", { nozzle: 210, bed: 60 }) },
    { label: "Design: Obsidian Cyber (Cyan)", run: () => setTheme("obsidian") },
    { label: "Design: Voron / Bambu Carbon (Orange)", run: () => setTheme("carbon") },
    { label: "Design: Amethyst Pro (Violet)", run: () => setTheme("amethyst") },
    { label: "Design: Daylight Studio (Light)", run: () => setTheme("light") },
  ];

  (App.state.printers || []).forEach((p) => {
    cmds.push({ label: `Drucker öffnen: ${p.name} (${p.host})`, run: () => navigate("detail", p.id) });
    cmds.push({ label: `Vorheizen PLA (210/60°C): ${p.name}`, run: () => sendControl(p.id, "preheat", { nozzle: 210, bed: 60 }) });
  });

  const matched = cmds.filter((c) => !q || c.label.toLowerCase().includes(q));
  window._cmdActions = matched.map((c) => c.run);

  root.innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this){App.ui.cmdOpen=false;renderCommandPalette();}">
      <div class="modal-panel" style="max-width:600px">
        <div style="font-size:10.5px;font-weight:800;color:var(--accent);letter-spacing:0.8px;margin-bottom:8px">
          SCHNELLBEFEHLE & NAVIGATION (ESC ZUM SCHLIESSEN)
        </div>
        <input type="text" id="cmd-search-in" placeholder="Tippe einen Befehl, Druckernamen, Vorheizen oder Ansicht …"
          value="${esc(App.ui.cmdQuery)}" oninput="App.ui.cmdQuery=this.value;renderCommandPalette()"
          onkeydown="if(event.key==='Enter' && window._cmdActions && window._cmdActions[0]){App.ui.cmdOpen=false;renderCommandPalette();window._cmdActions[0]();}"/>
        <div style="display:flex;flex-direction:column;gap:4px;margin-top:10px;max-height:320px;overflow-y:auto">
          ${matched.map((c, idx) => `
            <button class="btn" style="justify-content:flex-start;text-align:left" onclick="App.ui.cmdOpen=false;renderCommandPalette();window._cmdActions[${idx}]()">
              ${esc(c.label)}
            </button>
          `).join("")}
        </div>
      </div>
    </div>
  `;
  const inp = document.getElementById("cmd-search-in");
  if (inp) {
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
  }
}

/* ============================================================================
   Master Shell Render & Flicker-Free Live Telemetry Loop
   ============================================================================ */

function renderSidebar() {
  const isEasy = App.state.mode === "easy";
  const v = App.ui.view;
  const qLen = (App.state.queue || []).length;
  const pLen = (App.state.printers || []).length;

  const navItems = isEasy ? [
    { id: "dashboard", label: "Meine Drucker", icon: ICONS.printers, badge: pLen },
    { id: "spoolman", label: "Filament & Spulen", icon: ICONS.spool },
    { id: "library", label: "Meine 3D-Dateien", icon: ICONS.library },
    { id: "discover", label: "Modelle finden", icon: ICONS.globe },
    { id: "cameras", label: "Kamera-Ansicht", icon: ICONS.camera },
    { id: "settings", label: "Einstellungen", icon: ICONS.settings },
  ] : [
    { id: "dashboard", label: "Kommandozentrale", icon: ICONS.printers, badge: pLen },
    { id: "gcode", label: "G-Code Layer Studio", icon: ICONS.gcode, badge: "2D/3D" },
    { id: "spoolman", label: "Spoolman & Trockner", icon: ICONS.spool },
    { id: "queue", label: "Farm-Warteschlange", icon: ICONS.queue, badge: qLen || "" },
    { id: "cameras", label: "Kamera-Matrix", icon: ICONS.camera },
    { id: "maintenance", label: "Wartung & Service", icon: ICONS.maintenance },
    { id: "stats", label: "Statistik & Kalkulator", icon: ICONS.stats },
    { id: "library", label: "3D-Bibliothek", icon: ICONS.library },
    { id: "discover", label: "Modelle im Web", icon: ICONS.globe },
    { id: "settings", label: "Einstellungen", icon: ICONS.settings },
  ];

  const sb = document.getElementById("sidebar-root");
  if (!sb) return;
  sb.innerHTML = `
    <div class="brand-box">
      <div class="brand-logo">PB</div>
      <div class="brand-text-col">
        <div class="brand-title">PRINTBOARD</div>
        <div class="brand-sub">${isEasy ? "✦ Easy Edition" : "⚡ Pro Studio 1.0"}</div>
      </div>
    </div>

    <div class="nav-section-lbl">${isEasy ? "ALLTAGS-MENÜ" : "PROFI-KOMMANDOZENTRALE"}</div>
    <div class="nav-list">
      ${navItems.map((it) => {
        const active = v === it.id || (v === "detail" && it.id === "dashboard");
        return `
          <button class="nav-btn ${active ? 'active' : ''}" onclick="navigate('${it.id}')">
            ${it.icon}
            <span>${esc(it.label)}</span>
            ${it.badge !== undefined && it.badge !== "" ? `<span class="nav-badge">${esc(it.badge)}</span>` : ""}
          </button>
        `;
      }).join("")}
    </div>

    <div class="sidebar-footer">
      <div style="font-size:10px;font-weight:800;color:var(--text-muted);letter-spacing:0.7px">STUDIO DESIGN THEME</div>
      <select onchange="setTheme(this.value)" style="padding:6px 9px;font-size:12px">
        <option value="obsidian" ${App.state.theme === "obsidian" ? "selected" : ""}>Obsidian Cyber (Cyan)</option>
        <option value="carbon" ${App.state.theme === "carbon" ? "selected" : ""}>Voron / Bambu Carbon</option>
        <option value="amethyst" ${App.state.theme === "amethyst" ? "selected" : ""}>Amethyst Pro (Linear)</option>
        <option value="light" ${App.state.theme === "light" ? "selected" : ""}>Daylight Studio (Light)</option>
      </select>
    </div>
  `;
}

function renderTopbar() {
  const tb = document.getElementById("topbar-root");
  if (!tb) return;
  const isEasy = App.state.mode === "easy";
  const printers = App.state.printers || [];
  const statuses = App.state.statuses || {};
  const online = printers.filter((p) => statuses[p.id] && !statuses[p.id].error && statuses[p.id].state !== "offline").length;
  const printing = printers.filter((p) => statuses[p.id] && statuses[p.id].state === "printing").length;
  const watts = printing * 145 + Math.max(0, online - printing) * 15;

  tb.innerHTML = `
    <div class="mode-switch-pill" title="Zwischen einfachem Alltagsmodus und vollem Profi-Modus wechseln (Alt+M)">
      <button class="mode-opt ${isEasy ? 'active-easy' : ''}" onclick="setMode('easy')">
        ✦ EASY MODE
      </button>
      <button class="mode-opt ${!isEasy ? 'active-advanced' : ''}" onclick="setMode('advanced')">
        ⚡ ADVANCED PRO
      </button>
    </div>

    <div class="kpi-pill">
      <span class="${online > 0 ? 'dot-live' : 'dot-warn'}"></span>
      <span>ONLINE: <b id="kpi-online">${online} / ${printers.length}</b></span>
    </div>
    <div class="kpi-pill">
      <span>AKTIVE DRUCKE: <b id="kpi-printing" style="color:var(--accent)">${printing}</b></span>
    </div>
    ${!isEasy ? `
      <div class="kpi-pill">
        <span>SPULEN: <b id="kpi-spools">${(App.state.spools || []).length}</b></span>
      </div>
      <div class="kpi-pill">
        <span>FLOTTEN-LAST: <b id="kpi-watts">~${watts} W</b></span>
      </div>
    ` : ""}

    <div style="margin-left:auto;display:flex;align-items:center;gap:8px">
      <button class="btn btn-sm" onclick="App.ui.cmdOpen=true;App.ui.cmdQuery='';renderCommandPalette()">
        ${ICONS.search} Schnellbefehle & Suche <span class="mono" style="opacity:0.65;font-size:10.5px">[Ctrl+K]</span>
      </button>
    </div>
  `;
}

function renderContent() {
  const c = document.getElementById("content-root");
  if (!c) return;
  const v = App.ui.view;
  if (v === "dashboard") c.innerHTML = renderDashboard();
  else if (v === "detail") c.innerHTML = renderDetail();
  else if (v === "gcode") c.innerHTML = renderGcodeStudio();
  else if (v === "spoolman") c.innerHTML = renderSpoolman();
  else if (v === "queue") c.innerHTML = renderQueue();
  else if (v === "cameras") c.innerHTML = renderCameras();
  else if (v === "maintenance") c.innerHTML = renderMaintenance();
  else if (v === "stats") c.innerHTML = renderStats();
  else if (v === "library") c.innerHTML = renderLibrary();
  else if (v === "discover") c.innerHTML = renderDiscover();
  else if (v === "settings") c.innerHTML = renderSettings();
  else c.innerHTML = renderDashboard();

  refreshCanvases();
}

function refreshCanvases() {
  // 1. Dashboard Bento Canvases
  if (App.ui.view === "dashboard" && App.state.mode === "advanced") {
    const series = {};
    const targets = {};
    (App.state.printers || []).forEach((p) => {
      const hist = (App.state.temp_history || {})[p.id] || [];
      hist.forEach((pt) => {
        (pt.temps || []).slice(0, 2).forEach(([n, cur, tgt]) => {
          const key = `${p.name} · ${n}`;
          if (!series[key]) series[key] = [];
          series[key].push(Number(cur || 0));
          targets[key] = Number(tgt || 0);
        });
      });
    });
    drawThermalCanvas("fleet-thermal-canvas", series, targets);

    // Spool donut
    const matMap = {};
    let totalG = 0;
    (App.state.spools || []).forEach((s) => {
      const m = (s.filament || {}).material || "PLA";
      const w = Number(s.remaining_weight || 0);
      matMap[m] = (matMap[m] || 0) + w;
      totalG += w;
    });
    const segs = Object.entries(matMap).map(([m, g], i) => ({
      label: m,
      value: g,
      color: CHART_PALETTE[i % CHART_PALETTE.length],
      unit: g >= 1000 ? `${(g / 1000).toFixed(2)} kg` : `${Math.round(g)} g`,
    }));
    drawDonutCanvas("fleet-spool-donut", segs, `${(totalG / 1000).toFixed(1)}kg`, "BESTAND");

    // Fleet utilization bars
    const utilEl = document.getElementById("fleet-utilization-bars");
    if (utilEl) {
      utilEl.innerHTML = (App.state.printers || []).slice(0, 4).map((p) => {
        const st = App.state.statuses[p.id] || { state: "offline" };
        const state = st.error ? "offline" : (st.state || "offline");
        const prog = state === "printing" || state === "paused" ? Math.round((st.progress || 0) * 100) : (state === "standby" || state === "complete" ? 100 : 8);
        const col = STATE_COLORS[state] || "#00E5FF";
        const rightTxt = state === "printing" ? `${prog}% ${st.eta ? '· ETA ' + st.eta : ''}` : (STATE_LABELS[state] || state).toUpperCase();
        return `
          <div>
            <div style="display:flex;justify-content:space-between;font-size:11.5px;font-weight:700;margin-bottom:3px">
              <span>${esc(p.name)}</span>
              <span style="color:${col}">${esc(rightTxt)}</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width:${prog}%;background:${col}"></div></div>
          </div>
        `;
      }).join("");
    }
  }

  // 2. Detail Canvases
  if (App.ui.view === "detail" && App.state.mode === "advanced") {
    const pid = App.ui.selectedPrinterId;
    const st = (App.state.statuses || {})[pid] || {};
    if (App.ui.detailTab === "cockpit") {
      const series = {};
      const targets = {};
      const hist = (App.state.temp_history || {})[pid] || [];
      hist.forEach((pt) => {
        (pt.temps || []).forEach(([n, cur, tgt]) => {
          if (!series[n]) series[n] = [];
          series[n].push(Number(cur || 0));
          targets[n] = Number(tgt || 0);
        });
      });
      drawThermalCanvas("detail-thermal-canvas", series, targets);
    } else if (App.ui.detailTab === "exclude" && st.exclude_object) {
      drawExcludeObjectCanvas("exclude-object-canvas", st.exclude_object);
    } else if (App.ui.detailTab === "bedmesh" && st.bed_mesh) {
      drawBedMeshCanvas("bed-mesh-canvas", st.bed_mesh, App.ui.bedMesh3D);
    }
  }

  // 3. G-Code Studio Canvas
  if (App.ui.view === "gcode") {
    drawGcodeLayerCanvas("gcode-studio-canvas");
  }
}

function renderAll() {
  document.documentElement.setAttribute("data-theme", App.state.theme || "obsidian");
  renderSidebar();
  renderTopbar();
  renderContent();
}

// Flicker-free live telemetry patching on poll
async function pollState() {
  try {
    const prevCount = (App.state.printers || []).length;
    const data = await App.apiGet("/api/state");
    const newCount = (data.printers || []).length;
    Object.assign(App.state, data);
    document.documentElement.setAttribute("data-theme", App.state.theme || "obsidian");

    // Update topbar KPIs in-place
    const printers = App.state.printers || [];
    const statuses = App.state.statuses || {};
    const online = printers.filter((p) => statuses[p.id] && !statuses[p.id].error && statuses[p.id].state !== "offline").length;
    const printing = printers.filter((p) => statuses[p.id] && statuses[p.id].state === "printing").length;
    const watts = printing * 145 + Math.max(0, online - printing) * 15;
    const elOn = document.getElementById("kpi-online");
    const elPr = document.getElementById("kpi-printing");
    const elSp = document.getElementById("kpi-spools");
    const elWa = document.getElementById("kpi-watts");
    if (elOn) elOn.textContent = `${online} / ${printers.length}`;
    if (elPr) elPr.textContent = String(printing);
    if (elSp) elSp.textContent = String((App.state.spools || []).length);
    if (elWa) elWa.textContent = `~${watts} W`;

    if (prevCount !== newCount) {
      renderAll();
      return;
    }

    // Patch dashboard cards in-place without re-creating DOM
    if (App.ui.view === "dashboard") {
      printers.forEach((p) => {
        const st = statuses[p.id] || { state: "offline" };
        const state = st.error ? "offline" : (st.state || "offline");
        const col = STATE_COLORS[state] || "#00E5FF";
        const stateTxt = STATE_LABELS[state] || state.toUpperCase();
        const prog = Number(st.progress || 0);
        const pctStr = state === "printing" || state === "paused" ? `${Math.round(prog * 100)}%` : (state === "complete" ? "100%" : (state === "offline" ? "OFF" : "IDLE"));
        const temps = st.temps || [];
        const nozzleT = temps[0] ? `${fmtTemp(temps[0][1])}°C${temps[0][2] > 0 ? ` / ${temps[0][2].toFixed(0)}°` : ""}` : "—";
        const bedT = temps[1] ? `${fmtTemp(temps[1][1])}°C${temps[1][2] > 0 ? ` / ${temps[1][2].toFixed(0)}°` : ""}` : "—";
        const remTxt = st.remaining ? `Rest: ${fmtHms(st.remaining)}${st.eta ? ` (Fertig ~${st.eta})` : ""}` : (state === "standby" ? "Bereit für Druckauftrag" : `Laufzeit: ${fmtHms(st.duration)}`);

        const elState = document.getElementById(`pstate-${p.id}`);
        if (elState) {
          elState.textContent = `● ${stateTxt}`;
          elState.style.color = col;
          elState.style.borderColor = col;
        }
        const elGauge = document.getElementById(`pgauge-${p.id}`);
        if (elGauge) {
          elGauge.innerHTML = renderRadialGaugeSVG(state === "complete" ? 1 : prog, col, pctStr, stateTxt, st.thumb_b64, App.state.mode === "easy" ? 94 : 84);
        }
        const elFile = document.getElementById(`pfile-${p.id}`);
        if (elFile) elFile.textContent = st.filename || (state === "offline" ? "Nicht im Netzwerk erreichbar" : "Kein aktiver Druckauftrag");
        const elRem = document.getElementById(`prem-${p.id}`);
        if (elRem) elRem.textContent = remTxt;
        const elTemps = document.getElementById(`ptemps-${p.id}`);
        if (elTemps) elTemps.innerHTML = `<span>🔥 Düse: <b style="color:var(--accent)">${nozzleT}</b></span><span>🛏 Bett: <b style="color:#F59E0B">${bedT}</b></span>`;
        const elBar = document.getElementById(`pbar-${p.id}`);
        if (elBar) {
          elBar.style.width = `${Math.round(prog * 100)}%`;
          elBar.style.background = col;
        }
      });
    }

    refreshCanvases();
  } catch (e) {
    // Ignore transient network hiccups
  }
}

// Freeform Camera Drag Helper
let _camDrag = null;
function startCamDrag(e, id) {
  const el = document.getElementById(id);
  if (!el) return;
  _camDrag = { el, sx: e.clientX, sy: e.clientY, ox: parseInt(el.style.left, 10) || 0, oy: parseInt(el.style.top, 10) || 0 };
}
window.addEventListener("mousemove", (e) => {
  if (!_camDrag) return;
  _camDrag.el.style.left = Math.max(8, _camDrag.ox + (e.clientX - _camDrag.sx)) + "px";
  _camDrag.el.style.top = Math.max(8, _camDrag.oy + (e.clientY - _camDrag.sy)) + "px";
});
window.addEventListener("mouseup", () => { _camDrag = null; });

// Global Keyboard Shortcuts (Ctrl+K Command Palette, Alt+M Mode Toggle, Esc Close)
window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    App.ui.cmdOpen = !App.ui.cmdOpen;
    App.ui.cmdQuery = "";
    renderCommandPalette();
  } else if (e.altKey && e.key.toLowerCase() === "m") {
    e.preventDefault();
    setMode(App.state.mode === "easy" ? "advanced" : "easy");
  } else if (e.key === "Escape") {
    if (App.ui.cmdOpen) {
      App.ui.cmdOpen = false;
      renderCommandPalette();
    } else if (App.ui.modal) {
      closeModal();
    }
  }
});

window.addEventListener("resize", () => refreshCanvases());

window.addEventListener("DOMContentLoaded", async () => {
  try {
    const initial = await App.apiGet("/api/state");
    Object.assign(App.state, initial);
  } catch (e) {}
  renderAll();
  setInterval(pollState, 2200);
});
