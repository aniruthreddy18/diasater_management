/**
 * Real-Time Dashboard & WebSocket Stream Controller
 * Multi-Disaster Early Warning System
 */

class DashboardController {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.stations = [];
    this.activeStationId = "STN-NE01";
  }

  init() {
    this.fetchLandslideStations();
    this.fetchInitialStateREST();
    this.connectWebSocket();
    this.setupInspector();
    
    // Polling fallback every 3 seconds to guarantee continuous live sync
    setInterval(() => this.pollStatusREST(), 3000);
  }

  async fetchLandslideStations() {
    try {
      const resp = await fetch("/api/v1/landslides/stations");
      if (resp.ok) {
        const data = await resp.json();
        this.stations = data.stations || [];
        if (data.active_station && data.active_station.id) {
          this.activeStationId = data.active_station.id;
        }
        this.renderSectorPills();
        if (window.disasterMap && typeof window.disasterMap.renderLandslideStations === "function") {
          window.disasterMap.renderLandslideStations(this.stations);
        }
        const activeSt = this.stations.find((s) => s.id === this.activeStationId) || this.stations[0];
        if (activeSt) {
          this.updateLandslideCardSpecs(activeSt);
        }
      }
    } catch (err) {
      console.warn("Could not fetch landslide stations:", err);
    }
  }

  renderSectorPills() {
    const wrap = document.getElementById("landslide-sector-pills");
    const countEl = document.getElementById("total-stations-count");
    if (countEl) countEl.textContent = this.stations.length;
    if (!wrap) return;

    wrap.innerHTML = "";
    this.stations.forEach((st) => {
      const isSelected = (st.id === this.activeStationId);
      const isLive = Boolean(st.is_active_iot_field_unit);
      const pill = document.createElement("div");
      pill.className = `sector-pill ${isSelected ? "active" : ""}`;
      pill.id = `sector-pill-${st.id}`;
      pill.onclick = () => this.selectStation(st.id, true);

      const tagHtml = isLive
        ? `<span class="sector-pill-tag tag-live">LIVE IoT</span>`
        : `<span class="sector-pill-tag">${st.gsi_susceptibility || "GSI"}</span>`;

      pill.innerHTML = `
        <div class="sector-pill-top">
          <span class="sector-pill-code">${st.id}</span>
          ${tagHtml}
        </div>
        <div class="sector-pill-name">${st.name}</div>
        <div class="sector-pill-region">📍 ${st.district}, ${st.state}</div>
      `;
      wrap.appendChild(pill);
    });
  }

  async selectStation(stationId, flyTo = true) {
    this.activeStationId = stationId;
    const st = this.stations.find((s) => s.id === stationId);
    if (!st) return;

    // Update active pill UI
    document.querySelectorAll(".sector-pill").forEach((el) => el.classList.remove("active"));
    const activePill = document.getElementById(`sector-pill-${stationId}`);
    if (activePill) activePill.classList.add("active");

    // Update specs on Landslide Card
    this.updateLandslideCardSpecs(st);

    // Notify backend
    try {
      await fetch("/api/v1/landslides/active-station", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ station_id: stationId }),
      });
    } catch (e) {
      console.warn("Could not notify backend of active station change:", e);
    }

    // Fly map to station
    if (flyTo && window.disasterMap && typeof window.disasterMap.focusLandslideStation === "function") {
      window.disasterMap.focusLandslideStation(stationId);
    }
  }

  updateLandslideCardSpecs(st) {
    if (!st) return;
    const codeEl = document.getElementById("ls-stn-code");
    const nameEl = document.getElementById("ls-stn-name");
    const coordsEl = document.getElementById("ls-spec-coords");
    const slopeEl = document.getElementById("ls-spec-slope");
    const elevEl = document.getElementById("ls-spec-elev");
    const gsiEl = document.getElementById("ls-spec-gsi");
    const assetsEl = document.getElementById("ls-spec-assets");
    const evacEl = document.getElementById("ls-spec-evac");
    const tagEl = document.getElementById("ls-live-iot-tag");

    if (codeEl) codeEl.textContent = st.id;
    if (nameEl) nameEl.textContent = `${st.name} (${st.district}, ${st.state})`;
    if (coordsEl) coordsEl.textContent = `${st.latitude.toFixed(4)}° N, ${st.longitude.toFixed(4)}° E`;
    if (slopeEl) slopeEl.textContent = `${st.slope_deg}° Critical`;
    if (elevEl) elevEl.textContent = `${st.elevation_m}m ASL`;
    if (assetsEl) assetsEl.textContent = st.downhill_assets;
    if (evacEl) evacEl.textContent = st.safe_assembly;

    if (gsiEl) {
      gsiEl.textContent = st.gsi_susceptibility || "HIGH";
      gsiEl.className = "spec-val " + (st.gsi_susceptibility === "EXTREME" ? "gsi-badge-extreme" : "gsi-badge-very-high");
    }

    if (tagEl) {
      if (st.is_active_iot_field_unit || st.id === this.activeStationId) {
        tagEl.style.display = "inline-block";
        tagEl.textContent = "LIVE IoT FIELD UNIT";
      } else {
        tagEl.style.display = "none";
      }
    }
  }

  async fetchInitialStateREST() {
    try {
      const resp = await fetch("/api/v1/status");
      if (resp.ok) {
        const status = await resp.json();
        this.updateMultiDisasterCards(status);
        if (status.receiver_coordinates && status.receiver_coordinates.latitude) {
          const lat = status.receiver_coordinates.latitude;
          const lon = status.receiver_coordinates.longitude;
          const el = document.getElementById("receiver-gps-text");
          if (el) el.textContent = `GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          // Command hub pin omitted - map focuses on disaster hazard pins
        }
      }
      
      const evResp = await fetch("/api/v1/events?limit=20");
      if (evResp.ok) {
        const events = await evResp.json();
        if (window.disasterMap && events) {
          events.forEach((ev) => window.disasterMap.updateHazardMarker(ev));
        }
      }

      const altResp = await fetch("/api/v1/alerts?limit=20");
      if (altResp.ok) {
        const alerts = await altResp.json();
        if (alerts) {
          alerts.forEach((alt) => this.prependAlertItem(alt));
        }
      }
    } catch (e) {
      console.warn("Initial REST sync note:", e);
    }
  }

  async pollStatusREST() {
    // Only poll if websocket is closed
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    try {
      const resp = await fetch("/api/v1/status");
      if (resp.ok) {
        const status = await resp.json();
        this.updateMultiDisasterCards(status);
      }
    } catch (e) {
      // Quiet ignore on polling
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log("[WS] Connecting to:", wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("[WS] Connected to early warning telemetry stream.");
      this.updateConnectionStatus(true);
      if (this.reconnectTimer) clearInterval(this.reconnectTimer);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (err) {
        console.error("[WS] Error parsing message:", err);
      }
    };

    this.ws.onclose = () => {
      console.warn("[WS] Disconnected from early warning stream. Retrying in 3s...");
      this.updateConnectionStatus(false);
      this.scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.error("[WS] WebSocket error:", err);
      this.ws.close();
    };
  }

  scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connectWebSocket();
      }, 3000);
    }
  }

  updateConnectionStatus(online) {
    const pill = document.getElementById("connection-status");
    if (!pill) return;
    if (online) {
      pill.innerHTML = `<span class="status-dot"></span> STREAM LIVE`;
      pill.style.color = "#10b981";
      pill.style.borderColor = "rgba(16, 185, 129, 0.3)";
      pill.style.background = "rgba(16, 185, 129, 0.15)";
    } else {
      pill.innerHTML = `<span class="status-dot" style="background:#ef4444;"></span> OFFLINE`;
      pill.style.color = "#ef4444";
      pill.style.borderColor = "rgba(239, 68, 68, 0.3)";
      pill.style.background = "rgba(239, 68, 68, 0.15)";
    }
  }

  handleMessage(msg) {
    const { type, data } = msg;

    if (type === "INITIAL_STATE") {
      this.updateMultiDisasterCards(data.status);
      if (data.receiver_gps) {
        document.getElementById("receiver-gps-text").textContent =
          `GPS: ${data.receiver_gps.latitude.toFixed(4)}, ${data.receiver_gps.longitude.toFixed(4)}`;
        // Command hub pin omitted
      }
      if (data.firms_hotspots) {
        window.disasterMap.renderFirmsHotspots(data.firms_hotspots);
      }
      if (data.events) {
        data.events.forEach((ev) => window.disasterMap.updateHazardMarker(ev));
      }
      if (data.alerts) {
        data.alerts.forEach((alt) => this.prependAlertItem(alt));
      }
    } else if (type === "HAZARD_UPDATE") {
      this.updateMultiDisasterCards(data.status);
      if (data.event) {
        window.disasterMap.updateHazardMarker(data.event);
        this.displayEventInInspector(data.event);
        this.prependTelemetryLogRow(data.event);
        if (data.event.detected) {
          this.playAlarmTone();
        }
      }
      if (data.alert) {
        this.prependAlertItem(data.alert);
        if (window.alertsDashboardCtrl) {
          window.alertsDashboardCtrl.fetchAlertsHistory();
        }
      }
    } else if (type === "STATUS_RESET") {
      this.updateMultiDisasterCards(data.status);
      if (window.disasterMap) {
        window.disasterMap.clearAllRiskCircles();
      }
      const inspector = document.getElementById("inspector-body");
      if (inspector) inspector.innerHTML = `<p style="color: #64748b; font-size: 12px;">All systems nominal. Select a map node or run a simulation to inspect readings.</p>`;
    }
  }

  updateMultiDisasterCards(status) {
    if (!status) return;

    // Landslide Card
    this.updateSingleCard("landslide", status.landslide);

    // Flood Card
    this.updateSingleCard("flood", status.flash_flood);

    // Wildfire Card
    this.updateSingleCard("wildfire", status.wildfire);

    // Active hazard count badge in header
    const activeBadge = document.getElementById("active-hazard-count");
    if (activeBadge) {
      if (status.active_hazard_count > 0) {
        activeBadge.textContent = `🚨 ${status.active_hazard_count} ACTIVE CRITICAL`;
        activeBadge.className = "hazard-counter-badge counter-alert";
      } else {
        activeBadge.textContent = "🛡️ 0 ACTIVE HAZARDS";
        activeBadge.className = "hazard-counter-badge counter-zero";
      }
    }
  }

  updateSingleCard(prefix, state) {
    if (!state) return;

    const card = document.getElementById(`card-${prefix}`);
    const badge = document.getElementById(`badge-${prefix}`);
    const riskVal = document.getElementById(`risk-${prefix}`);
    const meter = document.getElementById(`meter-${prefix}`);

    if (card) {
      if (state.detected) {
        card.classList.add("detected");
      } else {
        card.classList.remove("detected");
      }
    }

    // Update real sensor chips if available
    const data = state.sensor_data || {};

    if (badge) {
      if (prefix === "landslide") {
        const soil = Number(data.soil_pct !== undefined ? data.soil_pct : (data.soil_moisture || 0));
        const rain = Number(data.rain_pct !== undefined ? data.rain_pct : 0);
        let level = 0;
        if (soil >= 80.0 || rain >= 85.0) level = 2;
        else if (soil >= 56.0 || rain >= 59.5) level = 1;

        if (level === 2) {
          badge.textContent = "ALARM";
          badge.className = "status-pill-badge badge-critical";
        } else if (level === 1) {
          badge.textContent = "WARNING";
          badge.className = "status-pill-badge badge-warning";
        } else {
          badge.textContent = "CLEAR";
          badge.className = "status-pill-badge badge-normal";
        }

        if (data.station_name || data.station_id) {
          const codeEl = document.getElementById("ls-stn-code");
          const nameEl = document.getElementById("ls-stn-name");
          if (codeEl) codeEl.textContent = data.station_id || "STN-NE01";
          if (nameEl) nameEl.textContent = `${data.station_name || "Haflong Slope"} (${data.district || ""}, ${data.state || ""})`;
          
          const coordsEl = document.getElementById("ls-spec-coords");
          if (coordsEl && state.latitude && state.longitude) {
            coordsEl.textContent = `${Number(state.latitude).toFixed(4)}° N, ${Number(state.longitude).toFixed(4)}° E`;
          }
          if (data.slope_deg) {
            const slopeEl = document.getElementById("ls-spec-slope");
            if (slopeEl) slopeEl.textContent = `${data.slope_deg}° Critical`;
          }
          if (data.elevation_m) {
            const elevEl = document.getElementById("ls-spec-elev");
            if (elevEl) elevEl.textContent = `${data.elevation_m}m ASL`;
          }
          if (data.downhill_assets) {
            const assetsEl = document.getElementById("ls-spec-assets");
            if (assetsEl) assetsEl.textContent = data.downhill_assets;
          }
          if (data.safe_assembly) {
            const evacEl = document.getElementById("ls-spec-evac");
            if (evacEl) evacEl.textContent = data.safe_assembly;
          }
        }
      } else if (prefix === "flood") {
        const alarmLevel = (data.alarm_level !== undefined) ? Number(data.alarm_level) : (state.detected ? 2 : 0);
        if (alarmLevel >= 2) {
          badge.textContent = "ALARM";
          badge.className = "status-pill-badge badge-critical";
        } else if (alarmLevel === 1) {
          badge.textContent = "WARN";
          badge.className = "status-pill-badge badge-warning";
        } else {
          badge.textContent = "CLEAR";
          badge.className = "status-pill-badge badge-normal";
        }
      } else if (prefix === "wildfire") {
        const flame = data.flame_detected || (data.flame_raw !== undefined && Number(data.flame_raw) <= 1500);
        const mq2 = Number(data.mq2_v || 0);
        const mq135 = Number(data.mq135_v || 0);
        const mq7 = Number(data.mq7_v || 0);
        const dust = Number(data.dust_ugm3 || 0);
        let level = 0;
        if (flame || mq2 >= 2.5 || mq135 >= 2.5 || mq7 >= 2.5 || dust >= 150.0) level = 2;
        else if (mq2 >= 1.75 || mq135 >= 1.75 || mq7 >= 1.75 || dust >= 105.0) level = 1;
        if (state.detected && level === 0) level = 2;

        if (level === 2) {
          badge.textContent = "ALARM";
          badge.className = "status-pill-badge badge-critical";
        } else if (level === 1) {
          badge.textContent = "WARNING";
          badge.className = "status-pill-badge badge-warning";
        } else {
          badge.textContent = "CLEAR";
          badge.className = "status-pill-badge badge-normal";
        }
      } else {
        badge.textContent = state.risk_level;
        badge.className = `status-pill-badge badge-${state.risk_level.toLowerCase()}`;
      }
    }

    const score = state.risk_score || 0.0;
    if (riskVal) riskVal.textContent = `${score.toFixed(1)}%`;
    if (meter) meter.style.width = `${Math.min(100, Math.max(0, score))}%`;

    if (prefix === "landslide") {
      // EXACT VALUES MATCHING RECEIVER SCREEN:
      // 1. PRES (Pres: 2037564)
      const press = (data.pressure_raw !== undefined && data.pressure_raw !== null)
        ? data.pressure_raw
        : ((data.pore_pressure !== undefined) ? data.pore_pressure : null);
      const elPress = document.getElementById("val-ls-press");
      if (elPress) {
        elPress.textContent = (press !== null && Number(press) !== -1) ? `${Math.round(press)}` : "--";
      }

      // 2. SOIL (Soil: 0%)
      const soil = (data.soil_pct !== undefined) ? data.soil_pct : data.soil_moisture;
      const elSoil = document.getElementById("val-ls-soil");
      if (elSoil) {
        elSoil.textContent = (soil !== undefined && soil !== null) ? `${Number(soil).toFixed(0)}%` : "--%";
      }

      // 3. RAIN (Rain: 0%)
      const rain = (data.rain_pct !== undefined) ? data.rain_pct : 0;
      const elRain = document.getElementById("val-ls-rain");
      if (elRain) {
        elRain.textContent = `${Number(rain).toFixed(0)}%`;
      }

      // 4. SOLAR (Solar: 4.9V)
      const solar = (data.solar_v !== undefined) ? data.solar_v : data.solar;
      const elSolar = document.getElementById("val-ls-solar");
      if (elSolar) {
        elSolar.textContent = (solar !== undefined && solar !== null) ? `${Number(solar).toFixed(1)}V` : "--V";
      }

      // 5. BATTERY (Bat: 1.60V)
      const batt = (data.battery_v !== undefined) ? data.battery_v : data.battery;
      const elBatt = document.getElementById("val-ls-batt");
      if (elBatt) {
        elBatt.textContent = (batt !== undefined && batt !== null) ? `${Number(batt).toFixed(2)}V` : "--V";
      }

      // 6. SEQ (#35)
      const seq = data.sequence !== undefined ? data.sequence : (data.packet_seq || state.sequence);
      const elSeq = document.getElementById("val-ls-seq");
      if (elSeq) {
        elSeq.textContent = (seq !== undefined && seq !== null) ? `#${seq}` : "--";
      }
    } else if (prefix === "flood") {
      // EXACT 4 VALUES FROM RECEIVER LCD:
      // 1. DIST (Dist: xxx.xcm)
      const dist = (data.distance_cm !== undefined) ? data.distance_cm : data.distance;
      const elDist = document.getElementById("val-fl-dist");
      if (elDist && dist !== undefined) {
        elDist.textContent = (Number(dist) < 0) ? "No Echo" : `${Number(dist).toFixed(1)} cm`;
      }

      // 2. FLOW (Flow: x.xxL/m)
      const flow = (data.flow_lpm !== undefined) ? data.flow_lpm : data.water_flow;
      const elFlow = document.getElementById("val-fl-flow");
      if (elFlow && flow !== undefined) elFlow.textContent = `${Number(flow).toFixed(2)} L/m`;

      // 3. RAIN (Rain: xx.x%)
      const rain = (data.rain_pct !== undefined) ? data.rain_pct : data.rainfall_rate;
      const elRain = document.getElementById("val-fl-rain");
      if (elRain && rain !== undefined) elRain.textContent = `${Number(rain).toFixed(1)}%`;

      // 4. BATTERY (Batt: x.xxV)
      const batt = (data.battery_v !== undefined) ? data.battery_v : data.battery;
      const elBatt = document.getElementById("val-fl-batt");
      if (elBatt && batt !== undefined) elBatt.textContent = `${Number(batt).toFixed(2)}V`;
    } else if (prefix === "wildfire") {
      // EXACT VALUES MATCHING RECEIVER SCREEN (Node 3 FIRE-GAS):
      // 1. MQ2 (e.g. 0.56V)
      const elMq2 = document.getElementById("val-wf-mq2");
      if (elMq2) {
        const v = data.mq2_v !== undefined ? data.mq2_v : (data.smoke !== undefined ? (data.smoke / 200.0) : null);
        elMq2.textContent = (v !== null && v !== undefined) ? `${Number(v).toFixed(2)}V` : "--";
      }

      // 2. MQ135 (e.g. 2.32V)
      const elMq135 = document.getElementById("val-wf-mq135");
      if (elMq135) {
        const v = data.mq135_v !== undefined ? data.mq135_v : null;
        elMq135.textContent = (v !== null && v !== undefined) ? `${Number(v).toFixed(2)}V` : "--";
      }

      // 3. MQ7 (e.g. 3.84V)
      const elMq7 = document.getElementById("val-wf-mq7");
      if (elMq7) {
        const v = data.mq7_v !== undefined ? data.mq7_v : null;
        elMq7.textContent = (v !== null && v !== undefined) ? `${Number(v).toFixed(2)}V` : "--";
      }

      // 4. DUST (e.g. 0)
      const elDust = document.getElementById("val-wf-dust");
      if (elDust) {
        const d = data.dust_ugm3 !== undefined ? data.dust_ugm3 : 0;
        elDust.textContent = `${Math.round(d)}`;
      }

      // 5. FLAME (e.g. YES or no)
      const elFlame = document.getElementById("val-wf-flame");
      if (elFlame) {
        const fRaw = data.flame_raw;
        const isFlame = data.flame_detected || (fRaw !== undefined && Number(fRaw) <= 1500);
        elFlame.textContent = isFlame ? "YES" : "no";
        elFlame.style.color = isFlame ? "#ff2a5f" : "#00f59b";
      }

      // 6. BAT (e.g. 0.00V)
      const elBatt = document.getElementById("val-wf-batt");
      if (elBatt) {
        const b = data.battery_v !== undefined ? data.battery_v : data.battery;
        elBatt.textContent = (b !== undefined && b !== null) ? `${Number(b).toFixed(2)}V` : "--";
      }

      // 7. SEQ (e.g. #11)
      const elSeq = document.getElementById("val-wf-seq");
      if (elSeq) {
        const seq = data.sequence !== undefined ? data.sequence : (data.packet_seq || state.sequence);
        elSeq.textContent = (seq !== undefined && seq !== null) ? `#${seq}` : "--";
      }

      // FIRMS status strip
      const firmsStrip = document.getElementById("wildfire-firms-status");
      if (firmsStrip) {
        if (state.firms_confirmed) {
          firmsStrip.className = "firms-status-strip firms-match-active";
          firmsStrip.innerHTML = `<span>🛰️ NASA FIRMS: MATCH CONFIRMED (${state.nearest_firms_distance_km ? state.nearest_firms_distance_km.toFixed(1) : ''} km)</span><span style="font-weight: 800;">+15% BOOST</span>`;
        } else if (state.nearest_firms_distance_km) {
          firmsStrip.className = "firms-status-strip";
          firmsStrip.innerHTML = `<span>🛰️ NASA FIRMS: Hotspot ${state.nearest_firms_distance_km.toFixed(1)} km away</span><span>UNCONFIRMED</span>`;
        } else {
          firmsStrip.className = "firms-status-strip";
          firmsStrip.innerHTML = `<span>🛰️ NASA FIRMS: Satellite Watch Active</span><span>LIVE</span>`;
        }
      }
    }
  }

  setupInspector() {
    window.disasterMap.activeInspectorCallback = (eventData) => {
      this.displayEventInInspector(eventData);
    };
  }

  displayEventInInspector(event) {
    const inspector = document.getElementById("inspector-body");
    if (!inspector) return;

    let sensorHtml = "";
    for (const [k, v] of Object.entries(event.sensor_data || {})) {
      const label = k.replace("_", " ").toUpperCase();
      sensorHtml += `
        <div style="background: rgba(12, 18, 30, 0.6); padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; flex-direction: column;">
          <span style="font-size: 9px; text-transform: uppercase; color: var(--text-dim); font-weight: 600;">${label}</span>
          <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: #f8fafc;">${v}</span>
        </div>
      `;
    }

    let firmsBox = "";
    if (event.hazard_type === "WILDFIRE") {
      if (event.firms_confirmed) {
        firmsBox = `
          <div style="background: rgba(0, 245, 155, 0.1); border: 1px solid rgba(0, 245, 155, 0.4); border-radius: 8px; padding: 10px; margin-top: 10px; font-size: 11px; color: #00f59b;">
            🛰️ <strong>NASA FIRMS MATCH CONFIRMED:</strong> Active satellite thermal anomaly detected 
            <strong style="color: #ffffff;">${event.nearest_firms_distance_km ? event.nearest_firms_distance_km.toFixed(2) : ''} km</strong> away.
            Applied <strong style="color: #ffffff;">+${event.firms_adjustment.toFixed(0)}%</strong> corroboration bonus.
          </div>
        `;
      } else if (event.nearest_firms_distance_km !== null && event.nearest_firms_distance_km !== undefined) {
        firmsBox = `
          <div style="background: rgba(250, 204, 21, 0.1); border: 1px solid rgba(250, 204, 21, 0.3); border-radius: 8px; padding: 10px; margin-top: 10px; font-size: 11px; color: #facc15;">
            🛰️ <strong>NASA FIRMS:</strong> Nearest satellite thermal anomaly is ${event.nearest_firms_distance_km.toFixed(2)} km away (exceeds matching radius).
          </div>
        `;
      }
    }

    inspector.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-weight: 800; font-size: 15px; color: #ffffff; letter-spacing: 0.5px;">${event.hazard_type.replace('_', ' ')}</span>
        <span class="status-pill-badge badge-${event.risk_level.toLowerCase()}">${event.risk_level}</span>
      </div>
      <div style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8; margin-bottom: 12px; display: flex; justify-content: space-between;">
        <span>NODE: <strong style="color: #c7d2fe;">${event.device_id}</strong></span>
        <span>GPS: <strong style="color: #c7d2fe;">${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}</strong></span>
      </div>
      
      <!-- Composite Risk Gauge Bar -->
      <div style="background: rgba(12, 18, 30, 0.7); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
          <span style="font-size: 10px; text-transform: uppercase; color: var(--text-dim); font-weight: 700;">Final Risk Score</span>
          <span style="font-family: var(--font-mono); font-size: 20px; font-weight: 800; color: #ff2a5f;">${event.final_risk_score.toFixed(1)}%</span>
        </div>
        <div class="meter-track">
          <div class="meter-fill" style="width: ${event.final_risk_score}%; background: linear-gradient(90deg, #ffb703, #ff2a5f);"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-dim); margin-top: 4px;">
          <span>Base Sensor Risk: ${event.base_risk_score.toFixed(1)}%</span>
          <span>FIRMS Adjustment: +${event.firms_adjustment.toFixed(0)}%</span>
        </div>
      </div>

      <!-- Telemetry Grid -->
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">
        ${sensorHtml}
      </div>

      ${firmsBox}

      <div style="margin-top: 10px; font-size: 11px; color: #94a3b8; font-style: italic; background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px; border-left: 3px solid #6366f1;">
        "${event.message}"
      </div>
    `;
  }

  prependAlertItem(alert) {
    const feed = document.getElementById("alert-feed");
    if (!feed) return;

    // Remove placeholder
    if (feed.children.length === 1 && feed.children[0].textContent.includes("Awaiting")) {
      feed.innerHTML = "";
    }

    const div = document.createElement("div");
    let typeClass = "wildfire";
    let icon = "🔥";
    if (alert.hazard_type === "FLASH_FLOOD") {
      typeClass = "flood";
      icon = "🌊";
    } else if (alert.hazard_type === "LANDSLIDE") {
      typeClass = "landslide";
      icon = "⛰️";
    }

    div.className = `alert-card-item ${typeClass}`;
    div.innerHTML = `
      <div class="alert-item-top">
        <span>${icon} ${alert.hazard_type.replace('_', ' ')} (${alert.device_id})</span>
        <span style="font-family: var(--font-mono); font-size: 12px; font-weight: 800; color: #ff4d6d;">${alert.risk_score.toFixed(1)}%</span>
      </div>
      <div style="color: #cbd5e1; font-size: 10px;">
        Level: <strong>${alert.risk_level}</strong> • GPS: <span style="font-family: var(--font-mono);">${alert.latitude.toFixed(4)}, ${alert.longitude.toFixed(4)}</span>
      </div>
      <div style="color: #64748b; font-size: 9px; font-family: var(--font-mono); margin-top: 2px;">
        ${new Date(alert.timestamp).toLocaleTimeString()} • Telegram Alert Dispatch
      </div>
    `;

    feed.prepend(div);

    // Keep max 25 in UI feed
    if (feed.children.length > 25) {
      feed.removeChild(feed.lastChild);
    }
  }

  playAlarmTone() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.3);

      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.32);
    } catch (e) {
      // AudioContext policy on unmuted user interaction
    }
  }

  prependTelemetryLogRow(event) {
    const feed = document.getElementById("telemetry-stream-feed");
    if (!feed) return;

    // Remove empty placeholder row if present
    const emptyRow = feed.querySelector(".telemetry-empty-row");
    if (emptyRow) {
      emptyRow.remove();
    }

    // Build concise sensor summary string
    const sensorParts = [];
    for (const [k, v] of Object.entries(event.sensor_data || {})) {
      const shortKey = k.replace("_", " ").slice(0, 8);
      sensorParts.push(`${shortKey}:${v}`);
    }
    const sensorBrief = sensorParts.join(" | ");

    const row = document.createElement("div");
    row.className = `telemetry-log-row ${event.detected ? 'log-danger' : 'log-clear'}`;
    
    const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    const statusTag = event.detected
      ? `<span class="tag-danger">🚨 DANGER (${event.final_risk_score.toFixed(0)}%)</span>`
      : `<span class="tag-clear">✅ CLEAR (SAFE)</span>`;

    row.innerHTML = `
      <span class="log-time">${timeStr}</span>
      <span class="log-dev">${event.device_id}</span>
      <span class="log-gps">${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}</span>
      <span class="log-sensors" title="${sensorBrief}">${sensorBrief}</span>
      ${statusTag}
    `;

    feed.prepend(row);

    // Keep max 30 rows in telemetry feed
    if (feed.children.length > 30) {
      feed.removeChild(feed.lastChild);
    }
  }
}

// Global dashboard controller
window.dashboardCtrl = new DashboardController();
window.dashboardController = window.dashboardCtrl;
