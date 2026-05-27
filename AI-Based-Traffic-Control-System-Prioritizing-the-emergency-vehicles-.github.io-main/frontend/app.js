/* ═══════════════════════════════════════════════════════════════
   app.js — FINAL WORKING VERSION (FIXED)
   ═══════════════════════════════════════════════════════════════ */

const WS_URL   = "ws://localhost:8000/ws";
const API_BASE = "http://localhost:8000";

let ws = null;
let sigMaxTime = 12;

// ── CLOCK ─────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const d = now.toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });
  const t = now.toLocaleTimeString("en-US", { hour12: true, hour:"2-digit", minute:"2-digit", second:"2-digit" });
  const el = document.getElementById("clock");
  if (el) el.textContent = `${d}  |  ${t}`;
}
setInterval(updateClock, 1000);
updateClock();

// ── WEBSOCKET ─────────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("✅ WebSocket Connected");
    setStatus("st-ws", "Connected", true);
    setStatus("st-api", "Online", true);
    setSysOnline(true);
  };

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      console.log("📡 DATA:", data);   // 🔥 DEBUG
      if (data.type === "update") handleUpdate(data);
    } catch(e) {
      console.error("WS parse error:", e);
    }
  };

  ws.onclose = () => {
    console.log("❌ WS Disconnected → Reconnecting...");
    setStatus("st-ws", "Disconnected", false);
    setSysOnline(false);
    setTimeout(connectWS, 2000);
  };

  ws.onerror = () => ws.close();
}

function handleUpdate(data) {
  if (!data.cameras) return;

  Object.values(data.cameras).forEach(cam => {
    if (!cam) return;

    const idx = cam.cam_id;

    // 🎥 VIDEO
    const img = document.getElementById(`camImg${idx}`);
    if (img && cam.frame) {
      img.src = "data:image/jpeg;base64," + cam.frame;
    }

    // Hide overlay
    const overlay = document.getElementById(`overlay${idx}`);
    if (overlay) overlay.classList.add("hidden");

    // FPS
    const fpsEl = document.getElementById(`fps${idx}`);
    if (fpsEl) fpsEl.textContent = `${cam.fps || 0} FPS`;

    // Vehicle count
    const vcEl = document.getElementById(`vc${idx}`);
    if (vcEl) vcEl.textContent = cam.vehicle_count || 0;

    // ETA
    let eta = "—";
    if (cam.vehicles && cam.vehicles.length > 0) {
      eta = Math.min(...cam.vehicles.map(v => v.eta)) + "s";
    }

    const etaEl = document.getElementById(`eta${idx}`);
    if (etaEl) etaEl.textContent = eta;

    // 🚨 Emergency
    const wrap = document.getElementById(`camWrap${idx}`);
    const alert = document.getElementById(`emAlert${idx}`);

    if (cam.emergency) {
      wrap?.classList.add("emergency-cam");
      alert?.classList.remove("hidden");

      if (cam.emergency_info) {
        updateEmergencyPanel(cam.emergency_info, idx + 1);
      }
    } else {
      wrap?.classList.remove("emergency-cam");
      alert?.classList.add("hidden");
    }
  });

  // 🚦 SIGNALS
  if (data.signals) updateSignals(data.signals);

  // 📜 LOGS
  if (data.logs) updateLogs(data.logs);
}

// ── EMERGENCY PANEL ───────────────────────────────────────────
function updateEmergencyPanel(info, camNum) {
  const type = document.getElementById("emType");
  const cam  = document.getElementById("emCam");
  const conf = document.getElementById("emConf");
  const eta  = document.getElementById("emETA");

  if (type) type.textContent = info.type || "—";
  if (cam)  cam.textContent  = `CAM ${camNum}`;
  if (conf) conf.textContent = info.confidence ? `${(info.confidence*100).toFixed(0)}%` : "—";
  if (eta)  eta.textContent  = info.eta ? `${info.eta}s` : "—";
}

// ── SIGNALS ──────────────────────────────────────────────────
const DIRS = ["North", "East", "South", "West"];

function updateSignals(signals) {
  DIRS.forEach(dir => {
    const state = signals[dir];
    ["red","yellow","green"].forEach(color => {
      const el = document.getElementById(`b-${dir}-${color}`);
      if (!el) return;
      el.classList.toggle("lit", state && state.toLowerCase() === color);
    });
  });
}

function updateSignalTimer(timer) {
  if (!timer) return;

  const dirEl = document.getElementById("activeSignalDir");
  const timeEl = document.getElementById("sigTimer");
  const nextEl = document.getElementById("nextSignal");

  if (dirEl) dirEl.textContent = timer.active || "—";
  if (timeEl) timeEl.textContent = `${timer.time_remaining || 0} sec`;
  if (nextEl) nextEl.textContent = timer.next || "—";

  const fill = document.getElementById("sigBarFill");
  if (fill) {
    const pct = Math.min(100, (timer.time_remaining / sigMaxTime) * 100);
    fill.style.width = `${pct}%`;
  }
}

// ── LOGS ─────────────────────────────────────────────────────
function updateLogs(logs) {
  const list = document.getElementById("logList");
  if (!list) return;

  list.innerHTML = logs.map(l => `<div>${l}</div>`).join("");
}

// ── STATUS ───────────────────────────────────────────────────
function setStatus(id, label, active) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = label;
  el.className = "badge" + (active ? " active" : "");
}

function setSysOnline(online) {
  const el = document.getElementById("sysOnline");
  if (!el) return;
  el.innerHTML = `<span class="dot"></span> ${online ? "System Online" : "System Offline"}`;
}

// ── START / STOP ─────────────────────────────────────────────
async function startSystem() {
  try {
    const res = await fetch(`${API_BASE}/start`, {
      method: "POST"
    });

    const data = await res.json();

    if (data.status === "started" || data.status === "already") {
      document.getElementById("startBtn").disabled = true;
      document.getElementById("stopBtn").disabled = false;
    }

  } catch (e) {
    alert("Backend not running on port 8000");
  }
}

async function stopSystem() {
  try {
    const res = await fetch(`${API_BASE}/stop`, {
      method: "POST"
    });

    const data = await res.json();

    if (data.status === "stopped") {
      document.getElementById("startBtn").disabled = false;
      document.getElementById("stopBtn").disabled = true;

      window.started = false;
    }

  } catch (e) {
    console.error(e);
  }
}

function toggleSidebar() {
    document.getElementById("sideNav")
        .classList.toggle("collapsed");
}

// ── INIT ─────────────────────────────────────────────────────
connectWS();
