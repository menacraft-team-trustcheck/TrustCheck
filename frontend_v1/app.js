/**
 * ══════════════════════════════════════════════════════════════
 * MENACRAFT TRUSTCHECK — Frontend Application Logic
 * ══════════════════════════════════════════════════════════════
 * Connects to FastAPI backend at localhost:8000
 * Handles: tab navigation, file uploads, API calls, result rendering
 * ══════════════════════════════════════════════════════════════
 */

const API_BASE = "http://localhost:8000";

// ─── DOM REFERENCES ──────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── TAB NAVIGATION ─────────────────────────────────────────

$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".nav-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $$(".tab-panel").forEach((p) => p.classList.remove("active"));
    $(`#panel-${btn.dataset.tab}`).classList.add("active");
  });
});

// ─── PROVIDER STATUS ────────────────────────────────────────

async function fetchProviderStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    const data = await res.json();

    // Update header pulse
    const pulse = $("#api-pulse");
    const statusText = $("#api-status-text");
    pulse.classList.remove("online", "offline");
    pulse.classList.add("online");
    statusText.textContent = "API Connected";

    // Render provider pills
    const container = $("#provider-status");
    container.innerHTML = "";

    for (const [id, info] of Object.entries(data.providers)) {
      const pill = document.createElement("div");
      pill.className = `provider-pill ${info.connected ? "connected" : "disconnected"}`;
      pill.innerHTML = `
        <span class="provider-dot"></span>
        <span>${info.emoji} <strong>${info.name}</strong></span>
        <span style="margin-left:auto;font-size:0.65rem;opacity:0.6;">${info.connected ? "●" : "○"}</span>
      `;
      container.appendChild(pill);
    }

    // Supabase pill
    const sbPill = document.createElement("div");
    sbPill.className = `provider-pill ${data.supabase_connected ? "connected" : "disconnected"}`;
    sbPill.innerHTML = `
      <span class="provider-dot"></span>
      <span>🗄️ <strong>Supabase</strong></span>
      <span style="margin-left:auto;font-size:0.65rem;opacity:0.6;">${data.supabase_connected ? "●" : "○"}</span>
    `;
    container.appendChild(sbPill);
  } catch (err) {
    const pulse = $("#api-pulse");
    pulse.classList.remove("online");
    pulse.classList.add("offline");
    $("#api-status-text").textContent = "API Offline";
  }
}

fetchProviderStatus();
setInterval(fetchProviderStatus, 30000);

// ─── FILE UPLOAD HANDLERS ───────────────────────────────────

let imageFile = null;
let videoFile = null;
let audioFile = null;
let batchFiles = [];

function setupDropZone(zoneId, inputId, onFile) {
  const zone = $(zoneId);
  const input = $(inputId);

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) onFile(e.dataTransfer.files);
  });
  input.addEventListener("change", () => { if (input.files.length) onFile(input.files); });
}

// Image upload
setupDropZone("#image-drop-zone", "#image-input", (files) => {
  imageFile = files[0];
  const reader = new FileReader();
  reader.onload = (e) => {
    $("#image-preview-img").src = e.target.result;
    $("#image-preview").style.display = "flex";
    $(".upload-zone__inner", $("#image-drop-zone"))?.style && ($("#image-drop-zone .upload-zone__inner").style.display = "none");
    $("#btn-analyze-image").disabled = false;
  };
  reader.readAsDataURL(imageFile);
});

$("#image-remove").addEventListener("click", (e) => {
  e.stopPropagation();
  imageFile = null;
  $("#image-preview").style.display = "none";
  $("#image-drop-zone .upload-zone__inner").style.display = "flex";
  $("#btn-analyze-image").disabled = true;
  $("#image-input").value = "";
});

// Audio upload
setupDropZone("#audio-drop-zone", "#audio-input", (files) => {
  audioFile = files[0];
  if (!audioFile) return;

  const preview = $("#audio-preview");
  const audioEl = $("#audio-preview-el");
  const inner = $("#audio-drop-zone .upload-zone__inner");

  try {
    const url = URL.createObjectURL(audioFile);
    audioEl.src = url;
    preview.style.display = "block";
    inner.style.display = "none";
    $("#btn-analyze-audio").disabled = false;
  } catch (err) {
    console.error("Audio preview failed:", err);
  }
});

$("#audio-remove").addEventListener("click", (e) => {
  e.stopPropagation();
  audioFile = null;
  $("#audio-input").value = "";
  $("#audio-preview").style.display = "none";
  $("#audio-drop-zone .upload-zone__inner").style.display = "flex";
  $("#btn-analyze-audio").disabled = true;
});

// Video upload
setupDropZone("#video-drop-zone", "#video-input", (files) => {
  videoFile = files[0];
  const url = URL.createObjectURL(videoFile);
  $("#video-preview-el").src = url;
  $("#video-preview").style.display = "flex";
  $("#video-drop-zone .upload-zone__inner").style.display = "none";
  $("#btn-analyze-video").disabled = false;
});

$("#video-remove").addEventListener("click", (e) => {
  e.stopPropagation();
  videoFile = null;
  $("#video-preview").style.display = "none";
  $("#video-drop-zone .upload-zone__inner").style.display = "flex";
  $("#btn-analyze-video").disabled = true;
  $("#video-input").value = "";
});

// Video interval slider
$("#video-interval").addEventListener("input", (e) => {
  $("#video-interval-value").textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
});

// Batch upload
setupDropZone("#batch-drop-zone", "#batch-input", (files) => {
  batchFiles = Array.from(files);
  const listEl = $("#batch-file-list");
  listEl.innerHTML = batchFiles.map((f) => `<span class="file-chip">📄 ${f.name}</span>`).join("");
  listEl.style.display = "block";
  $("#btn-analyze-batch").disabled = false;
});

// ─── VERDICT HELPERS ────────────────────────────────────────

function verdictClass(verdict) {
  if (!verdict) return "neutral";
  const v = verdict.toLowerCase();
  if (v.includes("authentic") || v.includes("true") || v.includes("credible") || v.includes("consistent") || v.includes("match"))
    return "success";
  if (v.includes("ai_generated") || v.includes("false") || v.includes("low") || v.includes("inconsistent") || v.includes("mismatch"))
    return "danger";
  if (v.includes("inconclusive") || v.includes("mixed") || v.includes("questionable") || v.includes("uncertain") || v.includes("partial"))
    return "warning";
  return "neutral";
}

function verdictEmoji(verdict) {
  const cls = verdictClass(verdict);
  return { success: "✅", danger: "🚨", warning: "⚠️", neutral: "❓" }[cls];
}

function pctDisplay(val) {
  if (typeof val !== "number") return "N/A";
  return `${Math.round(val * 100)}%`;
}

function scoreGradientClass(val) {
  if (typeof val !== "number") return "";
  if (val >= 0.65) return ""; // default green gradient
  if (val >= 0.35) return "warning";
  return "danger";
}

// ─── IMAGE ANALYSIS ─────────────────────────────────────────

$("#btn-analyze-image").addEventListener("click", async () => {
  if (!imageFile) return;

  const btn = $("#btn-analyze-image");
  btn.classList.add("loading");
  btn.disabled = true;

  const progressSection = $("#image-progress");
  const progressFill = $("#image-progress-fill");
  const progressText = $("#image-progress-text");
  const resultsSection = $("#image-results");

  progressSection.style.display = "block";
  resultsSection.style.display = "none";
  resultsSection.innerHTML = "";

  // Simulate progress steps
  const steps = [
    [15, "🔬 Axis A: AI detection fingerprinting..."],
    [30, "⚡ ELA: Error Level Analysis (local forensics)..."],
    [45, "🔎 Axis B1: Semantic consistency check..."],
    [60, "📰 Axis B2: Claim plausibility & fact-check..."],
    [75, "📍 Axis B3: EXIF geolocation extraction..."],
    [88, "🏛️ Axis C: Domain forensics & source credibility..."],
    [95, "🧠 Synthesis: Weighted scoring + contradiction detection..."],
  ];

  let stepIdx = 0;
  const progressInterval = setInterval(() => {
    if (stepIdx < steps.length) {
      progressFill.style.width = steps[stepIdx][0] + "%";
      progressText.textContent = steps[stepIdx][1];
      stepIdx++;
    }
  }, 2000);

  try {
    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("claim", $("#image-claim").value);
    formData.append("source_name", $("#image-source").value);
    formData.append("source_url", $("#image-url").value);
    formData.append("claimed_location", $("#image-location").value);

    const res = await fetch(`${API_BASE}/analyze/image`, { method: "POST", body: formData });
    const data = await res.json();

    clearInterval(progressInterval);
    progressFill.style.width = "100%";
    progressText.textContent = "✅ Analysis complete!";

    setTimeout(() => {
      progressSection.style.display = "none";
      renderImageResults(data, resultsSection);
      resultsSection.style.display = "block";
    }, 600);
  } catch (err) {
    clearInterval(progressInterval);
    progressText.textContent = `❌ Error: ${err.message}`;
    progressFill.style.width = "100%";
    progressFill.style.background = "var(--gradient-danger)";
  } finally {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
});

function renderImageResults(data, container) {
  const auth = data.authenticity || {};
  const ctx = data.context || {};
  const fc = data.fact_check || {};
  const geo = data.geolocation || {};
  const cred = data.credibility || {};
  const hm = data.heatmap || {};
  const syn = data.synthesis || {};

  // Risk level styling
  const riskColors = {
    CRITICAL: { bg: "rgba(255,23,68,0.15)",   border: "#FF1744", text: "#FF1744",  icon: "🚨" },
    HIGH:     { bg: "rgba(255,145,0,0.15)",   border: "#FF9100", text: "#FF9100",  icon: "⚠️" },
    MEDIUM:   { bg: "rgba(255,214,0,0.12)",   border: "#FFD600", text: "#FFD600",  icon: "🔶" },
    LOW:      { bg: "rgba(0,200,83,0.12)",    border: "#00C853", text: "#00C853",  icon: "✅" },
  };
  const riskLevel = syn.risk_level || "MEDIUM";
  const rc = riskColors[riskLevel] || riskColors.MEDIUM;

  container.innerHTML = `
    <div class="results-header">📊 Verification Results</div>

    <!-- Risk Level Banner -->
    <div style="
      border: 2px solid ${rc.border};
      background: ${rc.bg};
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: flex-start;
      gap: 1.25rem;
    ">
      <div style="
        font-size: 2.5rem;
        font-weight: 900;
        color: ${rc.text};
        line-height: 1;
        min-width: 90px;
        text-align: center;
      ">
        ${rc.icon}<br>
        <span style="font-size: 0.9rem; letter-spacing: 0.1em;">${riskLevel}</span>
      </div>
      <div style="flex: 1;">
        <div style="font-weight: 800; color: var(--text-primary); margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.75rem;">
          <span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted);">🧠 FORENSIC VERDICT</span>
          <span style="font-size: 0.75rem; color: ${rc.text}; background: ${rc.bg}; padding: 2px 8px; border-radius: 99px; border: 1px solid ${rc.border};">
            Risk Score: ${Math.round((syn.risk_score || 0) * 100)}%
          </span>
          ${syn.visual_conflict ? '<span style="font-size: 0.75rem; color: #FF9100; background: rgba(255,145,0,0.1); padding: 2px 8px; border-radius: 99px; border: 1px solid #FF9100;">⚡ STAGED FAKE SIGNAL</span>' : ''}
        </div>
        <p style="font-size: 0.9rem; line-height: 1.65; color: var(--text-primary); margin-bottom: 0.5rem;">
          ${syn.narrative || "Forensic synthesis unavailable."}
        </p>
        ${syn.decisive_factor && syn.decisive_factor !== 'unknown' ? `
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">
          <strong>Decisive factor:</strong> ${syn.decisive_factor}
          &nbsp;·&nbsp;
          <strong>Weights:</strong>
          Visual ${Math.round((syn.axis_weights?.visual || 0.6) * 100)}%
          / Context ${Math.round((syn.axis_weights?.context || 0.25) * 100)}%
          / Source ${Math.round((syn.axis_weights?.source || 0.15) * 100)}%
        </div>` : ''}
      </div>
    </div>

    <!-- Score Cards -->
    <div class="score-grid">
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(auth.verdict)}</div>
        <div class="score-card__value ${scoreGradientClass(auth.confidence)}">${pctDisplay(auth.confidence)}</div>
        <div class="score-card__label">Authenticity</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(ctx.verdict)}</div>
        <div class="score-card__value ${scoreGradientClass(ctx.match_score)}">${pctDisplay(ctx.match_score)}</div>
        <div class="score-card__label">Context</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(fc.verdict)}</div>
        <div class="score-card__value ${scoreGradientClass(fc.score)}">${pctDisplay(fc.score)}</div>
        <div class="score-card__label">Fact Check</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(cred.verdict)}</div>
        <div class="score-card__value ${scoreGradientClass(cred.credibility_score)}">${pctDisplay(cred.credibility_score)}</div>
        <div class="score-card__label">Credibility</div>
      </div>
    </div>

    <div class="hash-display">🔒 SHA-256: ${data.sha256 || "N/A"}</div>

    <!-- Authenticity Detail -->
    ${renderDetailSection("🔬 Axis A: Content Authenticity", auth.verdict, `
      <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.6;">${auth.details || "No details available."}</p>
      <div style="margin-top:0.75rem;">
        <span class="verdict-pill ${verdictClass(auth.verdict)}">${verdictEmoji(auth.verdict)} ${formatVerdict(auth.verdict)}</span>
        <span style="margin-left:0.5rem;font-size:0.75rem;color:var(--text-muted);">Model: ${auth.model_used || "N/A"}</span>
      </div>
    `, true)}

    <!-- Heatmap -->
    ${hm.heatmap_image_base64 ? renderDetailSection("🗺️ ELA Forensic Heatmap", null, `
      <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.5rem; display:flex; gap:0.5rem; align-items:center;">
        <span style="background: rgba(0,200,83,0.15); border: 1px solid #00C853; border-radius: 4px; padding: 2px 7px; color: #00C853;">⚡ LOCAL — Zero API Cost</span>
        <span style="background: rgba(100,100,100,0.1); border: 1px solid #555; border-radius: 4px; padding: 2px 7px;">ELA Mean: ${Math.round((hm.ela_mean || 0) * 100)}%</span>
        <span style="background: rgba(100,100,100,0.1); border: 1px solid #555; border-radius: 4px; padding: 2px 7px;">ELA Max: ${Math.round((hm.ela_max || 0) * 100)}%</span>
      </div>
      <img class="result-image" src="data:image/png;base64,${hm.heatmap_image_base64}" alt="ELA Forensic Heatmap">
      <p class="result-image-caption">Red = JPEG re-save artifacts (editing evidence) · Green = original pixels — Method: Bellingcat ELA</p>
      ${hm.overall_assessment ? `<div class="evidence-box info">${hm.overall_assessment}</div>` : ""}
      ${hm.hotspots?.length ? `<div class="evidence-box contradicting"><strong>Hotspots:</strong> ${hm.hotspots.join("<br>• ")}</div>` : "<div class=\"evidence-box supporting\">No suspicious ELA hotspots detected.</div>"}
    `, true) : ""}

    <!-- Context -->
    ${data.context ? renderDetailSection("🔎 Axis B.1: Contextual Consistency", ctx.verdict, `
      <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.6;">${ctx.analysis || ""}</p>
      ${ctx.supporting_evidence ? `<div class="evidence-box supporting"><strong>Supporting:</strong> ${ctx.supporting_evidence}</div>` : ""}
      ${ctx.contradicting_evidence && ctx.contradicting_evidence !== "None found" ? `<div class="evidence-box contradicting"><strong>Contradicting:</strong> ${ctx.contradicting_evidence}</div>` : ""}
      ${ctx.visual_elements_found?.length ? `<div style="margin-top:0.5rem;"><strong style="font-size:0.75rem;color:var(--text-muted);">Visual Elements:</strong> ${ctx.visual_elements_found.map(e => `<span class="file-chip">${e}</span>`).join("")}</div>` : ""}
    `) : ""}

    <!-- Fact Check -->
    ${data.fact_check ? renderDetailSection("📰 Axis B.2: Fact Check", fc.verdict, `
      <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.6;">${fc.details || ""}</p>
      <div style="margin-top:0.5rem;">
        <span class="verdict-pill ${verdictClass(fc.verdict)}">${verdictEmoji(fc.verdict)} ${formatVerdict(fc.verdict)}</span>
        <span style="margin-left:0.5rem;font-size:0.7rem;color:var(--text-muted);">Source: ${fc.source || "N/A"}</span>
      </div>
      ${fc.google_results?.length ? `<div class="evidence-box info" style="margin-top:0.75rem;">
        <strong>Existing Fact-Checks:</strong><br>
        ${fc.google_results.slice(0, 3).map(r => `• <strong>${r.review_publisher}</strong>: ${r.review_rating} ${r.review_url ? `(<a href="${r.review_url}" target="_blank" style="color:var(--info);">link</a>)` : ""}`).join("<br>")}
      </div>` : ""}
    `) : ""}

    <!-- Geolocation -->
    ${renderDetailSection("📍 Axis B.3: EXIF Forensics & Geolocation", geo.verdict, `
      <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.6;">${geo.details || "No details."}</p>

      ${(geo.forensic_signals?.length) ? `
        <div style="margin-top:0.75rem;">
          ${geo.forensic_signals.map(s =>
            `<div style="font-size:0.8rem; padding:6px 10px; margin-bottom:4px; border-radius:6px; background:rgba(255,145,0,0.08); border-left:3px solid #FF9100; color: var(--text-primary);">⚠️ ${s}</div>`
          ).join("")}
        </div>
      ` : ""}

      ${(geo.camera_info && Object.values(geo.camera_info).some(v => v)) ? `
        <div style="margin-top:0.75rem;">
          <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); margin-bottom:0.4rem;">📷 EXIF Camera Profile</div>
          <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:4px;">
            ${[
              ["Make / Model", (geo.camera_info.make || "") + " " + (geo.camera_info.model || "")],
              ["Captured",     geo.camera_info.datetime],
              ["ISO",          geo.camera_info.iso],
              ["F-Number",     geo.camera_info.f_number ? "f/" + geo.camera_info.f_number : null],
              ["Exposure",     geo.camera_info.exposure_time],
              ["Focal Length", geo.camera_info.focal_length ? geo.camera_info.focal_length + "mm" : null],
              ["Flash",        geo.camera_info.flash],
              ["Software",     geo.camera_info.software],
              ["Resolution",   geo.camera_info.resolution],
            ].filter(([,v]) => v && String(v).trim()).map(([k,v]) => `
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:6px; padding:6px 10px;">
                <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em;">${k}</div>
                <div style="font-size:0.8rem; color:var(--text-primary); font-weight:600; margin-top:2px;">${v}</div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ""}

      ${geo.has_gps && geo.geocoded_location ? `
        <div class="evidence-box info" style="margin-top:0.75rem;">
          <strong>📍 Detected Location:</strong> ${geo.geocoded_location.display_name || "Unknown"}
        </div>
      ` : ""}
    `)}

    <!-- Credibility -->
    ${data.credibility ? renderDetailSection("🏛️ Axis C: Source Credibility", cred.verdict, `
      <p style="font-size:0.85rem;color:var(--text-secondary);line-height:1.6;">${cred.analysis || ""}</p>
      <div style="margin-top:0.5rem;">
        <span class="verdict-pill ${verdictClass(cred.verdict)}">${verdictEmoji(cred.verdict)} ${formatVerdict(cred.verdict)}</span>
        ${cred.bias_direction && cred.bias_direction !== "none" ? `<span class="verdict-pill warning" style="margin-left:0.3rem;">Bias: ${cred.bias_direction} (${cred.bias_severity})</span>` : ""}
      </div>
      ${cred.risk_indicators?.length ? `<div style="margin-top:0.75rem;">${cred.risk_indicators.map(r => `<span class="risk-chip">🚩 ${r}</span>`).join("")}</div>` : ""}
      ${cred.recommendations?.length ? `<div class="evidence-box info" style="margin-top:0.5rem;"><strong>Recommendations:</strong><br>${cred.recommendations.map(r => `• ${r}`).join("<br>")}</div>` : ""}
    `) : ""}

    <!-- Download Certificate -->
    <button class="btn-download" onclick="downloadCertificate()">
      📜 Download Verified Certificate (PDF)
    </button>
  `;

  // Wire up collapsible sections
  container.querySelectorAll(".detail-section__header").forEach((header) => {
    header.addEventListener("click", () => {
      header.parentElement.classList.toggle("open");
    });
  });
}

function renderDetailSection(title, verdict, content, openByDefault = false) {
  const cls = verdict ? verdictClass(verdict) : "neutral";
  return `
    <div class="detail-section ${openByDefault ? "open" : ""}">
      <div class="detail-section__header">
        <span class="detail-section__title">
          ${title}
          ${verdict ? `<span class="verdict-pill ${cls}">${formatVerdict(verdict)}</span>` : ""}
        </span>
        <span class="detail-section__toggle">▼</span>
      </div>
      <div class="detail-section__body">
        <div class="detail-section__content">${content}</div>
      </div>
    </div>
  `;
}

function formatVerdict(v) {
  if (!v) return "N/A";
  return v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── CERTIFICATE DOWNLOAD ───────────────────────────────────

async function downloadCertificate() {
  if (!imageFile) return;

  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("claim", $("#image-claim").value);
  formData.append("source_name", $("#image-source").value);
  formData.append("source_url", $("#image-url").value);
  formData.append("claimed_location", $("#image-location").value);

  try {
    const res = await fetch(`${API_BASE}/report/certificate`, { method: "POST", body: formData });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `TrustCheck_Report.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Failed to download certificate: " + err.message);
  }
}

// ─── VIDEO ANALYSIS ─────────────────────────────────────────

$("#btn-analyze-video").addEventListener("click", async () => {
  if (!videoFile) return;

  const btn = $("#btn-analyze-video");
  btn.classList.add("loading");
  btn.disabled = true;

  const progressSection = $("#video-progress");
  const progressFill = $("#video-progress-fill");
  const progressText = $("#video-progress-text");
  const resultsSection = $("#video-results");

  progressSection.style.display = "block";
  resultsSection.style.display = "none";

  progressFill.style.width = "30%";
  progressText.textContent = "🎬 Extracting and analyzing frames...";

  try {
    const formData = new FormData();
    formData.append("video", videoFile);
    formData.append("interval_sec", $("#video-interval").value);

    const res = await fetch(`${API_BASE}/analyze/video`, { method: "POST", body: formData });
    const data = await res.json();

    progressFill.style.width = "100%";
    progressText.textContent = "✅ Video analysis complete!";

    setTimeout(() => {
      progressSection.style.display = "none";
      renderVideoResults(data, resultsSection);
      resultsSection.style.display = "block";
    }, 600);
  } catch (err) {
    progressText.textContent = `❌ Error: ${err.message}`;
  } finally {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
});

function renderVideoResults(data, container) {
  container.innerHTML = `
    <div class="results-header">📊 Video Analysis Results</div>

    <div class="score-grid" style="grid-template-columns: repeat(3, 1fr);">
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(data.overall_verdict)}</div>
        <div class="score-card__value">${formatVerdict(data.overall_verdict)}</div>
        <div class="score-card__label">Overall Verdict</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">📊</div>
        <div class="score-card__value ${scoreGradientClass(1 - (data.average_ai_score || 0))}">${pctDisplay(data.average_ai_score)}</div>
        <div class="score-card__label">Avg AI Score</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">🚨</div>
        <div class="score-card__value danger">${data.suspicious_frames?.length || 0}</div>
        <div class="score-card__label">Suspicious Frames</div>
      </div>
    </div>

    <div class="hash-display">🔒 SHA-256: ${data.sha256 || "N/A"}</div>

    <div class="evidence-box info" style="margin-top:1rem;">${data.details || "No details."}</div>

    ${data.timeline_image_base64 ? `
      <div class="detail-section open" style="margin-top:1rem;">
        <div class="detail-section__header">
          <span class="detail-section__title">📈 Risk Timeline</span>
          <span class="detail-section__toggle">▼</span>
        </div>
        <div class="detail-section__body">
          <div class="detail-section__content">
            <img class="result-image" src="data:image/png;base64,${data.timeline_image_base64}" alt="Risk Timeline">
          </div>
        </div>
      </div>
    ` : ""}

    ${data.suspicious_frames?.length ? `
      <div class="detail-section open" style="margin-top:1rem;">
        <div class="detail-section__header">
          <span class="detail-section__title">🚨 Suspicious Keyframes</span>
          <span class="detail-section__toggle">▼</span>
        </div>
        <div class="detail-section__body">
          <div class="detail-section__content">
            <div class="suspicious-grid">
              ${data.suspicious_frames.slice(0, 6).map((sf) => `
                <div class="suspicious-frame">
                  <img src="data:image/jpeg;base64,${sf.image_base64}" alt="Frame at ${sf.timestamp}s">
                  <div class="suspicious-frame__label">t=${sf.timestamp?.toFixed(1)}s · AI: ${pctDisplay(sf.ai_score)}</div>
                </div>
              `).join("")}
            </div>
          </div>
        </div>
      </div>
    ` : ""}
  `;

  container.querySelectorAll(".detail-section__header").forEach((h) => {
    h.addEventListener("click", () => h.parentElement.classList.toggle("open"));
  });
}

// ─── BATCH ANALYSIS ─────────────────────────────────────────

$("#btn-analyze-batch").addEventListener("click", async () => {
  if (!batchFiles.length) return;

  const btn = $("#btn-analyze-batch");
  btn.classList.add("loading");
  btn.disabled = true;

  const progressSection = $("#batch-progress");
  const progressFill = $("#batch-progress-fill");
  const progressText = $("#batch-progress-text");
  const resultsSection = $("#batch-results");

  progressSection.style.display = "block";
  resultsSection.style.display = "none";

  progressFill.style.width = "20%";
  progressText.textContent = `🗂️ Processing ${batchFiles.length} images...`;

  try {
    const formData = new FormData();
    batchFiles.forEach((f) => formData.append("images", f));
    formData.append("claim", $("#batch-claim").value);

    const res = await fetch(`${API_BASE}/analyze/batch`, { method: "POST", body: formData });
    const data = await res.json();

    progressFill.style.width = "100%";
    progressText.textContent = `✅ Batch complete: ${data.total} images analyzed`;

    setTimeout(() => {
      progressSection.style.display = "none";
      renderBatchResults(data, resultsSection);
      resultsSection.style.display = "block";
    }, 600);
  } catch (err) {
    progressText.textContent = `❌ Error: ${err.message}`;
  } finally {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
});

function renderBatchResults(data, container) {
  container.innerHTML = `
    <div class="results-header">📊 Batch Results — ${data.total} Images</div>
    ${data.results.map((r) => {
      const auth = r.authenticity || {};
      const cls = verdictClass(auth.verdict);
      return `
        <div class="batch-item">
          <div class="batch-item__name">
            ${verdictEmoji(auth.verdict)}
            <span>${r.filename}</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.75rem;">
            <span class="verdict-pill ${cls}">${formatVerdict(auth.verdict)}</span>
            <span style="font-size:0.8rem;font-weight:700;color:var(--text-primary);">${pctDisplay(auth.confidence)}</span>
          </div>
        </div>
      `;
    }).join("")}
  `;
}

// ─── AUDIO ANALYSIS ─────────────────────────────────────────

$("#btn-analyze-audio").addEventListener("click", async () => {
  if (!audioFile) return;

  const btn = $("#btn-analyze-audio");
  btn.classList.add("loading");
  btn.disabled = true;

  const progressSection = $("#audio-progress");
  const progressFill = $("#audio-progress-fill");
  const progressText = $("#audio-progress-text");
  const resultsSection = $("#audio-results");

  progressSection.style.display = "block";
  resultsSection.style.display = "none";

  progressFill.style.width = "40%";
  progressText.textContent = "🎙️ Analyzing acoustic fingerprints...";

  try {
    const formData = new FormData();
    formData.append("audio", audioFile);

    const res = await fetch(`${API_BASE}/analyze/voice`, { method: "POST", body: formData });
    const data = await res.json();

    if (data.verdict === "error") throw new Error(data.details);

    progressFill.style.width = "100%";
    progressText.textContent = "✅ Voice analysis complete!";

    setTimeout(() => {
      progressSection.style.display = "none";
      renderAudioResults(data, resultsSection);
      resultsSection.style.display = "block";
    }, 600);
  } catch (err) {
    progressText.textContent = `❌ Error: ${err.message}`;
    resultsSection.innerHTML = `<div class="evidence-box danger">${err.message}</div>`;
    resultsSection.style.display = "block";
  } finally {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
});

function renderAudioResults(data, container) {
  const scorePct = Math.round((data.ai_score || 0) * 100);
  const colorClass = scoreGradientClass(1 - (data.ai_score || 0));
  
  container.innerHTML = `
    <div class="results-header">🔊 Voice Forensic Results</div>

    <div class="score-grid" style="grid-template-columns: repeat(2, 1fr);">
      <div class="score-card">
        <div class="score-card__emoji">${verdictEmoji(data.verdict)}</div>
        <div class="score-card__value">${formatVerdict(data.verdict)}</div>
        <div class="score-card__label">Voice Authenticity</div>
      </div>
      <div class="score-card">
        <div class="score-card__emoji">🦾</div>
        <div class="score-card__value ${colorClass}">${scorePct}%</div>
        <div class="score-card__label">AI Generation Probability</div>
      </div>
    </div>

    <div class="hash-display">🔒 SHA-256: ${data.sha256 || "N/A"}</div>

    <div class="evidence-box info" style="margin-top:1.5rem; border-left: 4px solid var(--info);">
      <strong>🧠 Forensic Interpretation:</strong><br>
      <p style="margin-top:0.5rem; line-height:1.6; font-style:italic;">"${data.interpretation || data.details}"</p>
    </div>

    ${data.flags?.length ? `
      <div class="detail-section open" style="margin-top:1rem;">
        <div class="detail-section__header">
          <span class="detail-section__title">🚨 Suspicious Acoustic Signals</span>
          <span class="detail-section__toggle">▼</span>
        </div>
        <div class="detail-section__body">
          <div class="detail-section__content">
            ${data.flags.map(f => `<div style="padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.05); color:#FF1744; font-size:0.85rem;">⚠️ ${f}</div>`).join("")}
          </div>
        </div>
      </div>
    ` : ""}

    <div class="detail-section" style="margin-top:1rem;">
      <div class="detail-section__header">
        <span class="detail-section__title">📊 Acoustic Metrics</span>
        <span class="detail-section__toggle">▼</span>
      </div>
      <div class="detail-section__body">
        <div class="detail-section__content">
          <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:10px;">
            ${Object.entries(data.features).filter(([k,v]) => v !== null && typeof v !== 'object').map(([k,v]) => `
              <div style="background:rgba(255,255,255,0.03); padding:8px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase;">${k.replace(/_/g, ' ')}</div>
                <div style="font-size:0.9rem; font-weight:700; color:var(--text-primary);">${typeof v === 'number' ? v.toFixed(3) : v}</div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>
    </div>
  `;

  container.querySelectorAll(".detail-section__header").forEach((h) => {
    h.addEventListener("click", () => h.parentElement.classList.toggle("open"));
  });
}
