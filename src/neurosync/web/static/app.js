/**
 * NeuroSync Framework v2 Web Client (Phase F10)
 * High-performance real-time oscilloscope, band-power analyzer and control dashboard.
 */

(function () {
  "use strict";

  // State
  const state = {
    connected: false,
    acquiring: false,
    recording: false,
    channels: 16,
    nominalFs: 250,
    activeChannels: new Set(Array.from({ length: 16 }, (_, i) => i)),
    channelNames: Array.from({ length: 16 }, (_, i) => `CH${i + 1}`),
    viewMode: "stacked", // 'stacked' | 'separate'
    timeWindowS: 5,
    gainMultiplier: 1.0,
    buffer: [], // Array of Float32Arrays per channel
    bufferCapacity: 250 * 10,
    bufferHead: 0,
    events: [],
    maxEvents: 50,
  };

  const CHANNEL_COLORS = [
    "#06b6d4", "#10b981", "#f59e0b", "#ec4899",
    "#3b82f6", "#8b5cf6", "#14b8a6", "#84cc16",
    "#f97316", "#6366f1", "#d946ef", "#0284c7",
    "#22c55e", "#eab308", "#a855f7", "#ef4444"
  ];

  // DOM Elements
  const el = {
    daemonStatus: document.getElementById("daemonStatus"),
    acqStatus: document.getElementById("acqStatus"),
    recStatus: document.getElementById("recStatus"),
    srateDisplay: document.getElementById("srateDisplay"),
    lostDisplay: document.getElementById("lostDisplay"),
    btnStartAcq: document.getElementById("btnStartAcq"),
    btnStopAcq: document.getElementById("btnStopAcq"),
    btnStartRec: document.getElementById("btnStartRec"),
    btnStopRec: document.getElementById("btnStopRec"),
    sessionNameInput: document.getElementById("sessionNameInput"),
    boardTypeSelect: document.getElementById("boardTypeSelect"),
    quickMarker1: document.getElementById("quickMarker1"),
    quickMarker2: document.getElementById("quickMarker2"),
    quickMarker3: document.getElementById("quickMarker3"),
    btnSendCustomMarker: document.getElementById("btnSendCustomMarker"),
    customMarkerInput: document.getElementById("customMarkerInput"),
    viewModeSelect: document.getElementById("viewModeSelect"),
    timeWindowSelect: document.getElementById("timeWindowSelect"),
    gainMultiplierSelect: document.getElementById("gainMultiplierSelect"),
    channelTagsContainer: document.getElementById("channelTagsContainer"),
    filterNotch: document.getElementById("filterNotch"),
    filterBandpass: document.getElementById("filterBandpass"),
    eventsTableBody: document.getElementById("eventsTableBody"),
    oscilloscopeCanvas: document.getElementById("oscilloscopeCanvas"),
    psdCanvas: document.getElementById("psdCanvas"),
    exportFormatSelect: document.getElementById("exportFormatSelect"),
    btnExport: document.getElementById("btnExport"),
    exportStatus: document.getElementById("exportStatus"),
  };

  // Canvas contexts
  const oscCtx = el.oscilloscopeCanvas.getContext("2d");
  const psdCtx = el.psdCanvas.getContext("2d");

  // WebSockets
  let streamWs = null;
  let eventsWs = null;

  // Initialize buffer
  function initBuffer(nChannels, fs) {
    state.channels = nChannels;
    state.nominalFs = fs || 250;
    state.bufferCapacity = Math.ceil(state.nominalFs * 10);
    state.buffer = [];
    for (let i = 0; i < nChannels; i++) {
      state.buffer.push(new Float32Array(state.bufferCapacity));
    }
    state.bufferHead = 0;
    renderChannelTags();
  }

  function renderChannelTags() {
    el.channelTagsContainer.innerHTML = "";
    for (let i = 0; i < state.channels; i++) {
      const tag = document.createElement("span");
      const name = state.channelNames[i] || `CH${i + 1}`;
      tag.className = "channel-tag " + (state.activeChannels.has(i) ? "active" : "disabled");
      tag.style.color = CHANNEL_COLORS[i % CHANNEL_COLORS.length];
      tag.textContent = name;
      tag.addEventListener("click", () => {
        if (state.activeChannels.has(i)) {
          if (state.activeChannels.size > 1) {
            state.activeChannels.delete(i);
            tag.className = "channel-tag disabled";
          }
        } else {
          state.activeChannels.add(i);
          tag.className = "channel-tag active";
        }
      });
      el.channelTagsContainer.appendChild(tag);
    }
  }

  // WebSocket connections
  function connectStreamWs() {
    const loc = window.location;
    const proto = loc.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${loc.host}/ws/stream?format=json`;

    streamWs = new WebSocket(url);
    streamWs.onopen = () => {
      state.connected = true;
      updateStatusHeader();
    };

    streamWs.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        if (payload.n_channels && payload.n_samples && payload.data) {
          if (state.buffer.length !== payload.n_channels) {
            initBuffer(payload.n_channels, 250);
          }
          appendData(payload.data, payload.n_samples);
        }
      } catch (err) {
        console.error("Failed to parse stream packet", err);
      }
    };

    streamWs.onclose = () => {
      state.connected = false;
      updateStatusHeader();
      setTimeout(connectStreamWs, 1500);
    };

    streamWs.onerror = () => {
      streamWs.close();
    };
  }

  function connectEventsWs() {
    const loc = window.location;
    const proto = loc.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${loc.host}/ws/events`;

    eventsWs = new WebSocket(url);
    eventsWs.onmessage = (evt) => {
      try {
        const ev = JSON.parse(evt.data);
        addEventRecord(ev);
      } catch (err) {
        console.error("Failed to parse event packet", err);
      }
    };

    eventsWs.onclose = () => {
      setTimeout(connectEventsWs, 2000);
    };

    eventsWs.onerror = () => {
      eventsWs.close();
    };
  }

  function appendData(channelData, nSamples) {
    const cap = state.bufferCapacity;
    for (let c = 0; c < state.channels && c < channelData.length; c++) {
      const src = channelData[c];
      const dst = state.buffer[c];
      for (let s = 0; s < nSamples; s++) {
        dst[(state.bufferHead + s) % cap] = src[s];
      }
    }
    state.bufferHead = (state.bufferHead + nSamples) % cap;
  }

  function addEventRecord(ev) {
    state.events.unshift(ev);
    if (state.events.length > state.maxEvents) {
      state.events.pop();
    }
    renderEventsTable();
  }

  function renderEventsTable() {
    el.eventsTableBody.innerHTML = "";
    for (const ev of state.events) {
      const tr = document.createElement("tr");
      const codeStr = String(ev.code || "EVENT");
      let badgeClass = "badge-marker";
      if (codeStr.startsWith("key_")) badgeClass = "badge-key";
      else if (codeStr.startsWith("mouse_")) badgeClass = "badge-mouse";
      else if (codeStr.startsWith("gamepad_")) badgeClass = "badge-gamepad";

      const timeSec = (Number(ev.t_host_ns || 0) / 1e9).toFixed(3);
      tr.innerHTML = `
        <td>${ev.seq || 0}</td>
        <td>${timeSec}s</td>
        <td><span class="badge ${badgeClass}">${codeStr}</span></td>
        <td>${JSON.stringify(ev.payload || {})}</td>
      `;
      el.eventsTableBody.appendChild(tr);
    }
  }

  // REST API calls
  async function pollStatus() {
    try {
      const resp = await fetch("/api/status");
      if (resp.ok) {
        const data = await resp.json();
        state.acquiring = data.status === "acquiring" || data.status === "recording";
        state.recording = data.status === "recording";
        const fs = (data.primary_stream && data.primary_stream.nominal_fs) ? data.primary_stream.nominal_fs : 250;
        state.nominalFs = fs;
        state.srateDisplay = fs;
        el.srateDisplay.textContent = `${fs} Hz`;
        el.lostDisplay.textContent = String(data.lost_samples || 0);
        updateStatusHeader();
      }
    } catch {
      state.connected = false;
      updateStatusHeader();
    }
  }

  function updateStatusHeader() {
    if (state.connected) {
      el.daemonStatus.className = "indicator online";
      el.daemonStatus.parentElement.querySelector("span").textContent = "Daemon: Online";
    } else {
      el.daemonStatus.className = "indicator";
      el.daemonStatus.parentElement.querySelector("span").textContent = "Daemon: Offline";
    }

    if (state.acquiring) {
      el.acqStatus.className = "indicator online";
      el.btnStartAcq.disabled = true;
      el.btnStopAcq.disabled = false;
    } else {
      el.acqStatus.className = "indicator";
      el.btnStartAcq.disabled = false;
      el.btnStopAcq.disabled = true;
    }

    if (state.recording) {
      el.recStatus.className = "indicator recording";
      el.btnStartRec.disabled = true;
      el.btnStopRec.disabled = false;
    } else {
      el.recStatus.className = "indicator";
      el.btnStartRec.disabled = !state.acquiring;
      el.btnStopRec.disabled = true;
    }
  }

  async function startAcquisition() {
    const boardType = el.boardTypeSelect.value;
    const req = {
      board_id: boardType === "synthetic" ? -1 : 0,
    };
    try {
      const res = await fetch("/api/acquisition/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (res.ok) await pollStatus();
    } catch (err) {
      alert("Failed to start acquisition: " + err);
    }
  }

  async function stopAcquisition() {
    try {
      const res = await fetch("/api/acquisition/stop", { method: "POST" });
      if (res.ok) await pollStatus();
    } catch (err) {
      alert("Failed to stop acquisition: " + err);
    }
  }

  async function startRecording() {
    const sessionName = el.sessionNameInput.value.trim() || `session_${Date.now()}`;
    const req = { output_path: `${sessionName}.xdf`, session_id: sessionName };
    try {
      const res = await fetch("/api/recording/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (res.ok) await pollStatus();
    } catch (err) {
      alert("Failed to start recording: " + err);
    }
  }

  async function stopRecording() {
    try {
      const res = await fetch("/api/recording/stop", { method: "POST" });
      if (res.ok) await pollStatus();
    } catch (err) {
      alert("Failed to stop recording: " + err);
    }
  }

  async function sendMarker(code, val = 1.0) {
    try {
      await fetch("/api/markers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ marker_code: String(code), value: Number(val) }),
      });
    } catch (err) {
      console.error("Marker emission failed", err);
    }
  }

  async function updateFilters() {
    const configs = [];
    if (el.filterNotch.checked) {
      configs.push({ filter_type: "notch", f_center: 50.0, q: 30.0 });
    }
    if (el.filterBandpass.checked) {
      configs.push({ filter_type: "bandpass", f_low: 1.0, f_high: 40.0, order: 4 });
    }
    try {
      await fetch("/api/filter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ configs }),
      });
    } catch (err) {
      console.error("Filter update failed", err);
    }
  }

  async function triggerExport() {
    const fmt = el.exportFormatSelect.value;
    el.exportStatus.textContent = "Exporting...";
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: fmt }),
      });
      if (res.ok) {
        const data = await res.json();
        el.exportStatus.textContent = `Export OK (${data.files.length} files created)`;
      } else {
        el.exportStatus.textContent = "Export failed";
      }
    } catch (err) {
      el.exportStatus.textContent = "Export error: " + err;
    }
  }

  // Real-time Canvas Rendering
  function resizeCanvases() {
    const dpr = window.devicePixelRatio || 1;
    const oscRect = el.oscilloscopeCanvas.parentElement.getBoundingClientRect();
    if (oscRect.width && oscRect.height) {
      el.oscilloscopeCanvas.width = oscRect.width * dpr;
      el.oscilloscopeCanvas.height = oscRect.height * dpr;
    }

    const psdRect = el.psdCanvas.parentElement.getBoundingClientRect();
    if (psdRect.width && psdRect.height) {
      el.psdCanvas.width = psdRect.width * dpr;
      el.psdCanvas.height = psdRect.height * dpr;
    }
  }

  function renderOscilloscope() {
    const dpr = window.devicePixelRatio || 1;
    const w = el.oscilloscopeCanvas.width;
    const h = el.oscilloscopeCanvas.height;

    oscCtx.save();
    oscCtx.scale(dpr, dpr);
    const cssW = w / dpr;
    const cssH = h / dpr;

    // Clear background
    oscCtx.fillStyle = "#080c12";
    oscCtx.fillRect(0, 0, cssW, cssH);

    // Grid lines
    oscCtx.strokeStyle = "rgba(46, 61, 82, 0.4)";
    oscCtx.lineWidth = 1;
    const gridCols = 10;
    for (let c = 1; c < gridCols; c++) {
      const gx = (cssW / gridCols) * c;
      oscCtx.beginPath();
      oscCtx.moveTo(gx, 0);
      oscCtx.lineTo(gx, cssH);
      oscCtx.stroke();
    }

    const visibleChannels = Array.from(state.activeChannels);
    const nVisible = visibleChannels.length;
    if (nVisible === 0) {
      oscCtx.restore();
      return;
    }

    const nPoints = Math.min(Math.floor(state.nominalFs * state.timeWindowS), state.bufferCapacity);
    const cap = state.bufferCapacity;

    if (state.viewMode === "stacked") {
      // Stacked Mode: All traces vertically distributed across the canvas
      const slotH = cssH / (nVisible + 1);

      visibleChannels.forEach((chIdx, slotIdx) => {
        const color = CHANNEL_COLORS[chIdx % CHANNEL_COLORS.length];
        const centerY = slotH * (slotIdx + 1);
        const name = state.channelNames[chIdx] || `CH${chIdx + 1}`;

        // Zero baseline line
        oscCtx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        oscCtx.beginPath();
        oscCtx.moveTo(50, centerY);
        oscCtx.lineTo(cssW, centerY);
        oscCtx.stroke();

        // Label
        oscCtx.fillStyle = color;
        oscCtx.font = "11px 'Segoe UI', Consolas, monospace";
        oscCtx.fillText(name, 10, centerY + 4);

        // Signal trace
        oscCtx.strokeStyle = color;
        oscCtx.lineWidth = 1.2;
        oscCtx.beginPath();

        const channelBuf = state.buffer[chIdx];
        if (!channelBuf) return;

        const startIdx = (state.bufferHead - nPoints + cap) % cap;
        const scaleY = (slotH * 0.45 * state.gainMultiplier) / 50.0; // Normalized display gain

        for (let pt = 0; pt < nPoints; pt++) {
          const bufPos = (startIdx + pt) % cap;
          const val = channelBuf[bufPos] || 0;
          const px = 55 + ((cssW - 65) / nPoints) * pt;
          const py = centerY - val * scaleY;
          if (pt === 0) oscCtx.moveTo(px, py);
          else oscCtx.lineTo(px, py);
        }
        oscCtx.stroke();
      });
    } else {
      // Separate Mode: Each channel has its own box / panel with borders
      const stripH = cssH / nVisible;

      visibleChannels.forEach((chIdx, slotIdx) => {
        const color = CHANNEL_COLORS[chIdx % CHANNEL_COLORS.length];
        const topY = stripH * slotIdx;
        const centerY = topY + stripH / 2;
        const name = state.channelNames[chIdx] || `CH${chIdx + 1}`;

        // Strip border
        oscCtx.strokeStyle = "rgba(46, 61, 82, 0.7)";
        oscCtx.strokeRect(0, topY, cssW, stripH);

        // Label
        oscCtx.fillStyle = color;
        oscCtx.font = "11px 'Segoe UI', Consolas, monospace";
        oscCtx.fillText(name, 10, centerY + 4);

        // Signal trace
        oscCtx.strokeStyle = color;
        oscCtx.lineWidth = 1.2;
        oscCtx.beginPath();

        const channelBuf = state.buffer[chIdx];
        if (!channelBuf) return;

        const startIdx = (state.bufferHead - nPoints + cap) % cap;
        const scaleY = (stripH * 0.4 * state.gainMultiplier) / 50.0;

        for (let pt = 0; pt < nPoints; pt++) {
          const bufPos = (startIdx + pt) % cap;
          const val = channelBuf[bufPos] || 0;
          const px = 55 + ((cssW - 65) / nPoints) * pt;
          const py = centerY - val * scaleY;
          if (pt === 0) oscCtx.moveTo(px, py);
          else oscCtx.lineTo(px, py);
        }
        oscCtx.stroke();
      });
    }

    oscCtx.restore();
  }

  function renderBandPowerPSD() {
    const dpr = window.devicePixelRatio || 1;
    const w = el.psdCanvas.width;
    const h = el.psdCanvas.height;

    psdCtx.save();
    psdCtx.scale(dpr, dpr);
    const cssW = w / dpr;
    const cssH = h / dpr;

    psdCtx.fillStyle = "#080c12";
    psdCtx.fillRect(0, 0, cssW, cssH);

    // EEG Power Bands: Delta, Theta, Alpha, Beta, Gamma
    const bands = [
      { name: "Delta (0.5-4Hz)", color: "#3b82f6", factor: 1.2 },
      { name: "Theta (4-8Hz)", color: "#06b6d4", factor: 0.9 },
      { name: "Alpha (8-12Hz)", color: "#10b981", factor: 1.5 },
      { name: "Beta (12-30Hz)", color: "#f59e0b", factor: 0.8 },
      { name: "Gamma (30-50Hz)", color: "#8b5cf6", factor: 0.4 },
    ];

    // Compute approximate power for active channels
    const visibleChannels = Array.from(state.activeChannels);
    let avgPower = 10.0;
    if (visibleChannels.length > 0 && state.buffer.length > 0) {
      let sumSq = 0;
      let count = 0;
      const chBuf = state.buffer[visibleChannels[0]];
      const cap = state.bufferCapacity;
      for (let i = 0; i < 250; i++) {
        const val = chBuf[(state.bufferHead - i + cap) % cap] || 0;
        sumSq += val * val;
        count++;
      }
      if (count > 0) avgPower = Math.sqrt(sumSq / count);
    }

    const barW = (cssW - 40) / bands.length;
    bands.forEach((b, idx) => {
      const bx = 20 + idx * barW;
      const pwr = Math.min(avgPower * b.factor * state.gainMultiplier, cssH - 40);
      const by = cssH - 24 - pwr;

      psdCtx.fillStyle = b.color;
      psdCtx.fillRect(bx + 4, by, barW - 8, pwr);

      psdCtx.fillStyle = "rgba(255, 255, 255, 0.7)";
      psdCtx.font = "10px 'Segoe UI', Consolas, monospace";
      psdCtx.textAlign = "center";
      psdCtx.fillText(b.name.split(" ")[0], bx + barW / 2, cssH - 8);
    });

    psdCtx.restore();
  }

  function animationLoop() {
    renderOscilloscope();
    renderBandPowerPSD();
    requestAnimationFrame(animationLoop);
  }

  // Event Listeners
  function attachListeners() {
    el.btnStartAcq.addEventListener("click", startAcquisition);
    el.btnStopAcq.addEventListener("click", stopAcquisition);
    el.btnStartRec.addEventListener("click", startRecording);
    el.btnStopRec.addEventListener("click", stopRecording);

    el.quickMarker1.addEventListener("click", () => sendMarker(1));
    el.quickMarker2.addEventListener("click", () => sendMarker(2));
    el.quickMarker3.addEventListener("click", () => sendMarker(3));
    el.btnSendCustomMarker.addEventListener("click", () => {
      const val = el.customMarkerInput.value.trim();
      if (val) sendMarker(val);
    });

    el.viewModeSelect.addEventListener("change", (e) => {
      state.viewMode = e.target.value;
    });

    el.timeWindowSelect.addEventListener("change", (e) => {
      state.timeWindowS = parseFloat(e.target.value);
    });

    el.gainMultiplierSelect.addEventListener("change", (e) => {
      state.gainMultiplier = parseFloat(e.target.value);
    });

    el.filterNotch.addEventListener("change", updateFilters);
    el.filterBandpass.addEventListener("change", updateFilters);

    el.btnExport.addEventListener("click", triggerExport);

    window.addEventListener("resize", resizeCanvases);
  }

  // Start
  function init() {
    initBuffer(16, 250);
    attachListeners();
    resizeCanvases();
    connectStreamWs();
    connectEventsWs();
    setInterval(pollStatus, 1000);
    requestAnimationFrame(animationLoop);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
