/**
 * Emergency Alert Command Center & Telegram Bot Manager
 * Multi-Disaster Early Warning System
 */

class AlertsDashboardController {
  constructor() {
    this.alerts = [];
    this.telegramStatus = {
      configured: false,
      chat_id: "",
      has_token: false,
      mode: "SIMULATION",
    };
  }

  init() {
    this.fetchTelegramStatus();
    this.fetchAlertsHistory();
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Sync slider value
    const slider = document.getElementById("broadcast-risk-score");
    const valText = document.getElementById("broadcast-risk-val");
    if (slider && valText) {
      slider.addEventListener("input", (e) => {
        valText.textContent = `${parseFloat(e.target.value).toFixed(0)}%`;
      });
    }
  }

  async fetchTelegramStatus() {
    try {
      const resp = await fetch("/api/v1/telegram/status");
      if (resp.ok) {
        this.telegramStatus = await resp.json();
        this.updateTelegramStatusUI();
      }
    } catch (e) {
      console.warn("Could not fetch Telegram status:", e);
    }
  }

  updateTelegramStatusUI() {
    const badge = document.getElementById("telegram-status-pill");
    const modeBadge = document.getElementById("telegram-mode-metric");
    const chatIdInput = document.getElementById("cfg-telegram-chat-id");
    const chatIdDisplay = document.getElementById("telegram-active-chat-id");

    if (this.telegramStatus.configured) {
      if (badge) {
        badge.innerHTML = `<span class="pulse-dot"></span> LIVE CONNECTED`;
        badge.className = "status-pill-badge badge-normal";
      }
      if (modeBadge) {
        modeBadge.textContent = "LIVE BOT ACTIVE";
        modeBadge.style.color = "#00f59b";
      }
      if (chatIdDisplay) {
        chatIdDisplay.textContent = this.telegramStatus.chat_id || "Active";
      }
      if (chatIdInput && !chatIdInput.value) {
        chatIdInput.value = this.telegramStatus.chat_id || "";
      }
    } else {
      if (badge) {
        badge.innerHTML = `○ SIMULATION MODE`;
        badge.className = "status-pill-badge badge-medium";
      }
      if (modeBadge) {
        modeBadge.textContent = "SIMULATION / LOCAL";
        modeBadge.style.color = "#fb923c";
      }
      if (chatIdDisplay) {
        chatIdDisplay.textContent = "Not Configured";
      }
    }
  }

  async fetchAlertsHistory() {
    try {
      const resp = await fetch("/api/v1/alerts?limit=50");
      if (resp.ok) {
        this.alerts = await resp.json();
        this.renderAlertsTable(this.alerts);
        this.updateMetrics();
      }
    } catch (e) {
      console.warn("Could not fetch alert history:", e);
    }
  }

  updateMetrics() {
    const totalCountEl = document.getElementById("metric-total-alerts");
    const evacCountEl = document.getElementById("metric-evac-orders");
    const tabBadge = document.getElementById("tab-alerts-count");

    const total = this.alerts.length;
    let evacOrders = 0;

    this.alerts.forEach((alt) => {
      if (alt.risk_level === "HIGH" || alt.risk_level === "EXTREME") {
        evacOrders++;
      }
    });

    if (totalCountEl) totalCountEl.textContent = total;
    if (evacCountEl) evacCountEl.textContent = evacOrders;
    if (tabBadge) tabBadge.textContent = `${total} DISPATCHED`;
  }

  renderAlertsTable(alerts) {
    const tbody = document.getElementById("alerts-table-body");
    if (!tbody) return;

    if (!alerts || alerts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-dim); padding: 24px; font-family: var(--font-mono);">
            No emergency alerts dispatched yet. Dispatches from hardware or the manual console will appear here.
          </td>
        </tr>
      `;
      return;
    }

    let rowsHtml = "";
    alerts.forEach((alt) => {
      let icon = "🔥";
      if (alt.hazard_type === "FLASH_FLOOD") icon = "🌊";
      if (alt.hazard_type === "LANDSLIDE") icon = "⛰️";

      const timeStr = alt.timestamp
        ? new Date(alt.timestamp).toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })
        : "N/A";

      const badgeClass = `badge-${alt.risk_level.toLowerCase()}`;
      const statusBadge = alt.delivered
        ? `<span class="delivery-tag tag-delivered">✅ DELIVERED</span>`
        : `<span class="delivery-tag tag-simulated">📋 SIMULATED</span>`;

      // Extract radii or compute approximation
      const pct = Math.max(0.0, Math.min(100.0, alt.risk_score)) / 100.0;
      let rVery = (pct * 1.5).toFixed(2);
      if (alt.hazard_type === "FLASH_FLOOD") rVery = (pct * 0.8).toFixed(2);
      if (alt.hazard_type === "LANDSLIDE") rVery = (pct * 0.4).toFixed(2);

      rowsHtml += `
        <tr class="alert-history-row">
          <td style="font-family: var(--font-mono); color: var(--text-dim);">${timeStr}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 6px; font-weight: 700;">
              <span>${icon}</span>
              <span>${alt.hazard_type.replace('_', ' ')}</span>
            </div>
            <div style="font-size: 10px; color: var(--text-dim); font-family: var(--font-mono);">${alt.device_id}</div>
          </td>
          <td>
            <div style="font-family: var(--font-mono); font-size: 11px; color: #c7d2fe;">
              GPS: ${alt.latitude.toFixed(4)}, ${alt.longitude.toFixed(4)}
            </div>
            <a href="https://www.google.com/maps?q=${alt.latitude},${alt.longitude}" target="_blank" style="font-size: 10px; color: #38bdf8; text-decoration: none;">
              🗺️ Open in Google Maps ↗
            </a>
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="status-pill-badge ${badgeClass}" style="font-size: 9px; padding: 2px 6px;">${alt.risk_level}</span>
              <strong style="font-family: var(--font-mono); font-size: 13px; color: #ff2a5f;">${alt.risk_score.toFixed(1)}%</strong>
            </div>
          </td>
          <td>
            <span class="radii-badge-chip">🔴 Evac &lt; ${rVery} km</span>
          </td>
          <td>
            ${statusBadge}
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;
  }

  async sendManualBroadcast() {
    const hazardType = document.getElementById("broadcast-hazard-type").value;
    const localityName = document.getElementById("broadcast-locality").value.trim() || "Central Locality";
    const lat = parseFloat(document.getElementById("broadcast-lat").value);
    const lon = parseFloat(document.getElementById("broadcast-lon").value);
    const riskScore = parseFloat(document.getElementById("broadcast-risk-score").value);
    const instructions = document.getElementById("broadcast-instructions").value.trim() || "Immediate evacuation advised.";

    const feedback = document.getElementById("broadcast-feedback");
    const btn = document.getElementById("btn-dispatch-manual");

    if (isNaN(lat) || isNaN(lon)) {
      if (feedback) {
        feedback.innerHTML = `<span style="color: #ef4444;">❌ Invalid GPS coordinates! Please provide numerical Latitude and Longitude.</span>`;
      }
      return;
    }

    if (btn) btn.disabled = true;
    if (feedback) feedback.innerHTML = `<span style="color: #38bdf8;">⏳ Dispatching emergency alert to Telegram and digital map...</span>`;

    try {
      const resp = await fetch("/api/v1/alerts/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hazard_type: hazardType,
          locality_name: localityName,
          latitude: lat,
          longitude: lon,
          risk_score: riskScore,
          instructions: instructions,
          device_id: "MANUAL_COMMAND_DISPATCH",
        }),
      });

      const res = await resp.json();
      if (resp.ok) {
        if (feedback) {
          feedback.innerHTML = `
            <div style="background: rgba(0, 245, 155, 0.15); border: 1px solid rgba(0, 245, 155, 0.4); border-radius: 6px; padding: 8px 12px; color: #00f59b;">
              ✅ <strong>EMERGENCY ALERT DISPATCHED SUCCESSFULLY!</strong><br/>
              Locality: <strong>${localityName}</strong> • Risk Score: <strong>${riskScore.toFixed(0)}%</strong><br/>
              Sent to Telegram & Concentric Risk Radii Plotted on Map.
            </div>
          `;
        }
        // Play local alarm tone
        if (window.dashboardCtrl) {
          window.dashboardCtrl.playAlarmTone();
        }
        // Refresh alert history table
        this.fetchAlertsHistory();
      } else {
        if (feedback) {
          feedback.innerHTML = `<span style="color: #ef4444;">❌ Dispatch failed: ${res.detail || "Server error"}</span>`;
        }
      }
    } catch (e) {
      if (feedback) {
        feedback.innerHTML = `<span style="color: #ef4444;">❌ Network exception: ${e.message}</span>`;
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async testTelegramConnection() {
    const token = document.getElementById("cfg-telegram-bot-token").value.replace(/\s+/g, '');
    const chatId = document.getElementById("cfg-telegram-chat-id").value.replace(/\s+/g, '');
    const feedback = document.getElementById("telegram-feedback");
    const btn = document.getElementById("btn-test-telegram");

    if (btn) btn.disabled = true;
    if (feedback) feedback.innerHTML = `<span style="color: #38bdf8;">⏳ Sending test handshake alert to Telegram...</span>`;

    try {
      const resp = await fetch("/api/v1/telegram/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bot_token: token || null,
          chat_id: chatId || null,
        }),
      });

      const res = await resp.json();
      if (res.success) {
        if (feedback) {
          feedback.innerHTML = `
            <div style="background: rgba(0, 245, 155, 0.15); border: 1px solid rgba(0, 245, 155, 0.4); border-radius: 6px; padding: 8px 12px; color: #00f59b;">
              ✅ <strong>TELEGRAM CONNECTED!</strong> Check your Telegram chat—the test alert was delivered.
            </div>
          `;
        }
      } else {
        if (feedback) {
          feedback.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 8px 12px; color: #ff4d6d;">
              ❌ <strong>Connection Failed:</strong> ${res.error}
            </div>
          `;
        }
      }
    } catch (e) {
      if (feedback) {
        feedback.innerHTML = `<span style="color: #ef4444;">❌ Network exception: ${e.message}</span>`;
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async saveTelegramConfig() {
    const token = document.getElementById("cfg-telegram-bot-token").value.replace(/\s+/g, '');
    const chatId = document.getElementById("cfg-telegram-chat-id").value.replace(/\s+/g, '');
    const feedback = document.getElementById("telegram-feedback");
    const btn = document.getElementById("btn-save-telegram");

    if (!token || !chatId) {
      if (feedback) {
        feedback.innerHTML = `<span style="color: #ef4444;">❌ Both Bot Token and Chat ID are required!</span>`;
      }
      return;
    }

    if (btn) btn.disabled = true;
    if (feedback) feedback.innerHTML = `<span style="color: #38bdf8;">⏳ Validating credentials and saving to configuration...</span>`;

    try {
      const resp = await fetch("/api/v1/telegram/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bot_token: token,
          chat_id: chatId,
        }),
      });

      const res = await resp.json();
      if (res.success) {
        if (feedback) {
          feedback.innerHTML = `
            <div style="background: rgba(0, 245, 155, 0.15); border: 1px solid rgba(0, 245, 155, 0.4); border-radius: 6px; padding: 8px 12px; color: #00f59b;">
              ✅ <strong>TELEGRAM BOT ACTIVATED & SAVED!</strong><br/>
              Bot is now in <strong>LIVE DISPATCH MODE</strong>. All future emergency alerts will be pushed to Telegram instantly.
            </div>
          `;
        }
        this.fetchTelegramStatus();
      } else {
        if (feedback) {
          feedback.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 8px 12px; color: #ff4d6d;">
              ❌ <strong>Validation Error:</strong> ${res.error}
            </div>
          `;
        }
      }
    } catch (e) {
      if (feedback) {
        feedback.innerHTML = `<span style="color: #ef4444;">❌ Network exception: ${e.message}</span>`;
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  useCentralGps() {
    const latInput = document.getElementById("broadcast-lat");
    const lonInput = document.getElementById("broadcast-lon");
    if (latInput) latInput.value = "17.3918";
    if (lonInput) lonInput.value = "78.3194";
  }
}

// Global controller instance
window.alertsDashboardCtrl = new AlertsDashboardController();

// Global view switch helper
window.switchView = function (viewName) {
  const tabTactical = document.getElementById("tab-btn-tactical");
  const tabAlerts = document.getElementById("tab-btn-alerts");
  const viewTactical = document.getElementById("view-tactical");
  const viewAlerts = document.getElementById("view-alerts");

  if (viewName === "alerts") {
    if (tabTactical) tabTactical.classList.remove("active");
    if (tabAlerts) tabAlerts.classList.add("active");
    if (viewTactical) viewTactical.style.display = "none";
    if (viewAlerts) viewAlerts.style.display = "block";

    if (window.alertsDashboardCtrl) {
      window.alertsDashboardCtrl.init();
    }
  } else {
    if (tabAlerts) tabAlerts.classList.remove("active");
    if (tabTactical) tabTactical.classList.add("active");
    if (viewAlerts) viewAlerts.style.display = "none";
    if (viewTactical) viewTactical.style.display = "block";

    // Invalidate map size so Leaflet resizes cleanly
    setTimeout(() => {
      if (window.disasterMap && window.disasterMap.map) {
        window.disasterMap.map.invalidateSize();
      }
    }, 100);
  }
};
