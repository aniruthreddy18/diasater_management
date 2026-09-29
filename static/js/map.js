/**
 * Interactive Digital Map Manager (Leaflet.js)
 * Multi-Disaster Early Warning System
 */

class DisasterMapManager {
  constructor(containerId = "map") {
    this.containerId = containerId;
    this.map = null;
    this.markers = {}; // device_id -> L.marker
    this.riskCircles = {}; // device_id -> Array of L.circle (Very Danger, Danger, Moderate)
    this.firmsMarkers = [];
    this.receiverMarker = null;
    this.firmsRadiusCircle = null;
    this.activeInspectorCallback = null;
  }

  init(defaultLat = 17.3918, defaultLon = 78.3194) {
    if (typeof L === "undefined") {
      console.warn("Leaflet library (L) not yet loaded, retrying map init in 500ms...");
      setTimeout(() => this.init(defaultLat, defaultLon), 500);
      return false;
    }

    try {
      // Initialize Leaflet map
      this.map = L.map(this.containerId, {
        zoomControl: true,
        attributionControl: true,
      }).setView([defaultLat, defaultLon], 12);

      // Official OpenStreetMap Tile Server
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
      }).addTo(this.map);

      // Note: Command hub pin removed - map only displays actual detected disaster locations
      // this.setReceiverLocation(defaultLat, defaultLon);

      // Ensure tiles render immediately across flex/grid containers
      setTimeout(() => {
        if (this.map) this.map.invalidateSize();
      }, 200);

      window.addEventListener("resize", () => {
        if (this.map) this.map.invalidateSize();
      });

      console.log("OpenStreetMap initialized successfully at", defaultLat, defaultLon);
      return true;
    } catch (err) {
      console.error("Failed to initialize OpenStreetMap:", err);
      return false;
    }
  }

  setReceiverLocation(lat, lon) {
    if (this.receiverMarker) {
      this.receiverMarker.setLatLng([lat, lon]);
    } else {
      const icon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="beacon-receiver" title="Central Receiver GPS Beacon">📡</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
      this.receiverMarker = L.marker([lat, lon], { icon }).addTo(this.map);
      this.receiverMarker.bindPopup(`
        <div style="font-family: var(--font-main, sans-serif); font-size: 12px; color: #f8fafc; padding: 4px;">
          <div style="font-weight: 800; color: #818cf8; margin-bottom: 2px;">📡 CENTRAL RECEIVER GATEWAY</div>
          <div style="font-family: monospace; color: #94a3b8; font-size: 11px;">GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)}</div>
          <div style="font-size: 10px; color: #00f59b; margin-top: 4px; font-weight: 600;">ACTIVE TELEMETRY HUB</div>
        </div>
      `);
    }
  }

  getHazardIcon(hazardType, detected, riskLevel) {
    let emoji = "⚠️";
    let typeClass = "beacon-wildfire";

    if (hazardType === "WILDFIRE") {
      emoji = "🔥";
      typeClass = "beacon-wildfire";
    } else if (hazardType === "FLASH_FLOOD") {
      emoji = "🌊";
      typeClass = "beacon-flood";
    } else if (hazardType === "LANDSLIDE") {
      emoji = "⛰️";
      typeClass = "beacon-landslide";
    }

    const pulseClass = detected ? "beacon-pulse" : "";

    return L.divIcon({
      className: "custom-div-icon",
      html: `<div class="custom-hazard-beacon ${typeClass} ${pulseClass}">${emoji}</div>`,
      iconSize: [42, 42],
      iconAnchor: [21, 21],
    });
  }

  calculateRiskRadiiMeters(hazardType, riskScore) {
    const pct = Math.max(0.0, Math.min(100.0, riskScore)) / 100.0;
    const ht = String(hazardType).toUpperCase();

    if (ht.includes("WILD") || ht.includes("FIRE")) {
      return {
        veryDanger: Math.max(250, pct * 1500),
        danger: Math.max(600, pct * 3500),
        moderateDanger: Math.max(1200, pct * 6000),
      };
    } else if (ht.includes("FLOOD")) {
      return {
        veryDanger: Math.max(200, pct * 800),
        danger: Math.max(500, pct * 2000),
        moderateDanger: Math.max(1000, pct * 4000),
      };
    } else if (ht.includes("LANDSLIDE")) {
      return {
        veryDanger: Math.max(150, pct * 400),
        danger: Math.max(350, pct * 1000),
        moderateDanger: Math.max(700, pct * 2500),
      };
    }
    return {
      veryDanger: Math.max(200, pct * 1000),
      danger: Math.max(500, pct * 2500),
      moderateDanger: Math.max(1000, pct * 5000),
    };
  }

  clearRiskCircles(deviceId) {
    if (this.riskCircles[deviceId]) {
      this.riskCircles[deviceId].forEach((circle) => {
        if (this.map && this.map.hasLayer(circle)) {
          this.map.removeLayer(circle);
        }
      });
      delete this.riskCircles[deviceId];
    }
  }

  clearAllRiskCircles() {
    Object.keys(this.riskCircles).forEach((devId) => this.clearRiskCircles(devId));
  }

  updateRiskRadiusZones(eventData) {
    const { device_id, hazard_type, latitude, longitude, detected, final_risk_score } = eventData;
    const lat = parseFloat(latitude);
    const lon = parseFloat(longitude);

    if (isNaN(lat) || isNaN(lon)) return;

    // Always clear old circles for this node
    this.clearRiskCircles(device_id);

    // Only render risk radii when dangerous conditions are detected or score is elevated
    if (!detected && final_risk_score < 25) {
      return;
    }

    const radii = this.calculateRiskRadiiMeters(hazard_type, final_risk_score);
    const circles = [];

    // 1. Zone 3: MODERATE DANGER (Outer Circle - Yellow/Amber)
    const cMod = L.circle([lat, lon], {
      radius: radii.moderateDanger,
      color: "#eab308",
      weight: 1.5,
      dashArray: "6, 6",
      fillColor: "#eab308",
      fillOpacity: 0.12,
    }).addTo(this.map);
    cMod.bindTooltip(
      `🟡 <strong>MODERATE DANGER ZONE (Advisory / Watch):</strong> < ${(radii.moderateDanger / 1000).toFixed(2)} km`,
      { sticky: true }
    );
    circles.push(cMod);

    // 2. Zone 2: DANGER (Middle Circle - Orange)
    const cDan = L.circle([lat, lon], {
      radius: radii.danger,
      color: "#f97316",
      weight: 2,
      dashArray: "4, 4",
      fillColor: "#f97316",
      fillOpacity: 0.22,
    }).addTo(this.map);
    cDan.bindTooltip(
      `🟠 <strong>DANGER ZONE (High Warning / Prepare Evacuation):</strong> < ${(radii.danger / 1000).toFixed(2)} km`,
      { sticky: true }
    );
    circles.push(cDan);

    // 3. Zone 1: VERY DANGER (Inner Core Circle - Crimson Red)
    const cVery = L.circle([lat, lon], {
      radius: radii.veryDanger,
      color: "#ef4444",
      weight: 2.5,
      fillColor: "#ef4444",
      fillOpacity: 0.38,
    }).addTo(this.map);
    cVery.bindTooltip(
      `🔴 <strong>VERY DANGER ZONE (Immediate Mandatory Evacuation):</strong> < ${(radii.veryDanger / 1000).toFixed(2)} km`,
      { sticky: true }
    );
    circles.push(cVery);

    this.riskCircles[device_id] = circles;
  }

  updateHazardMarker(eventData) {
    const { device_id, hazard_type, latitude, longitude, detected, risk_level, final_risk_score } = eventData;

    const lat = parseFloat(latitude);
    const lon = parseFloat(longitude);

    if (isNaN(lat) || isNaN(lon)) return;

    const icon = this.getHazardIcon(hazard_type, detected, risk_level);

    if (this.markers[device_id]) {
      // Update existing marker
      this.markers[device_id].setLatLng([lat, lon]);
      this.markers[device_id].setIcon(icon);
    } else {
      // Create new marker
      const marker = L.marker([lat, lon], { icon }).addTo(this.map);
      marker.on("click", () => {
        this.showEventPopup(eventData, marker);
        if (this.activeInspectorCallback) {
          this.activeInspectorCallback(eventData);
        }
      });
      this.markers[device_id] = marker;
    }

    // Refresh popup data
    this.markers[device_id].eventData = eventData;

    // Update concentric risk zones (Very Danger, Danger, Moderate Danger)
    this.updateRiskRadiusZones(eventData);

    // Auto Fly-To: When danger is detected, automatically focus and fly to disaster location!
    if (detected && this.map) {
      this.map.flyTo([lat, lon], 13, {
        animate: true,
        duration: 1.2,
      });
    }
  }

  showEventPopup(event, marker) {
    const isWf = event.hazard_type === "WILDFIRE";
    let firmsInfo = "";
    if (isWf) {
      if (event.firms_confirmed) {
        firmsInfo = `<div style="background: #ecfdf5; border-left: 3px solid #10b981; padding: 4px 6px; margin-top: 6px; font-size: 11px;">
          <strong>🛰️ NASA FIRMS:</strong> CONFIRMED (+15% adjustment)<br>
          Nearest Satellite Hotspot: <strong>${event.nearest_firms_distance_km ? event.nearest_firms_distance_km.toFixed(1) : "?"} km</strong>
        </div>`;
      } else if (event.nearest_firms_distance_km !== null && event.nearest_firms_distance_km !== undefined) {
        firmsInfo = `<div style="background: #fffbeb; border-left: 3px solid #f59e0b; padding: 4px 6px; margin-top: 6px; font-size: 11px;">
          <strong>🛰️ NASA FIRMS:</strong> Unconfirmed (Nearest: ${event.nearest_firms_distance_km.toFixed(1)} km)
        </div>`;
      }
    }

    // Sensor telemetry list
    const labelMap = {
      distance_cm: "DIST",
      flow_lpm: "FLOW",
      rain_pct: "RAIN",
      battery_v: "BATTERY",
      temp_c: "TEMP",
      humidity_pct: "HUMIDITY",
      water_level: "WATER STAGE",
      rate_of_rise: "RATE OF RISE",
      rainfall_rate: "RAINFALL",
      water_flow: "FLOW VELOCITY",
    };
    const unitMap = {
      distance_cm: "cm",
      flow_lpm: "L/m",
      rain_pct: "%",
      temp_c: "°C",
      humidity_pct: "%",
      battery_v: "V",
      water_level: "cm",
      rate_of_rise: "cm/m",
      rainfall_rate: "mm/h",
      water_flow: "m/s",
    };

    let sensorRows = "";
    for (const [k, v] of Object.entries(event.sensor_data || {})) {
      if (["rate_of_rise", "rainfall_rate", "water_flow"].includes(k) && event.sensor_data.distance_cm !== undefined) {
        continue; // Hide redundant legacy duplicates when raw values exist
      }
      const label = labelMap[k] || k.replace(/_/g, " ");
      const unit = unitMap[k] ? ` ${unitMap[k]}` : "";
      const valStr = (typeof v === "number") ? `${v.toFixed(1)}${unit}` : `${v}${unit}`;
      sensorRows += `<tr><td style="padding: 2px 6px; color: #94a3b8;">${label}</td><td style="padding: 2px 6px; font-weight: 700; color: #38bdf8;">${valStr}</td></tr>`;
    }

    const radii = this.calculateRiskRadiiMeters(event.hazard_type, event.final_risk_score);
    const radiiBox = `
      <div style="margin-top: 8px; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px 8px;">
        <div style="font-size: 10px; font-weight: 800; color: #94a3b8; margin-bottom: 4px; letter-spacing: 0.5px;">LOCALLY CLASSIFIED RISK RADII:</div>
        <div style="font-size: 10px; color: #ef4444; display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>🔴 VERY DANGER (Evacuate):</span><strong>&lt; ${(radii.veryDanger / 1000).toFixed(2)} km</strong>
        </div>
        <div style="font-size: 10px; color: #f97316; display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>🟠 DANGER (High Warning):</span><strong>&lt; ${(radii.danger / 1000).toFixed(2)} km</strong>
        </div>
        <div style="font-size: 10px; color: #eab308; display: flex; justify-content: space-between;">
          <span>🟡 MODERATE (Advisory):</span><strong>&lt; ${(radii.moderateDanger / 1000).toFixed(2)} km</strong>
        </div>
      </div>
    `;

    const popupHtml = `
      <div style="font-family: var(--font-main, sans-serif); min-width: 250px; font-size: 12px; color: #f8fafc; line-height: 1.4;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; margin-bottom: 8px;">
          <strong style="font-size: 14px; font-weight: 800; color: #ffffff;">${event.hazard_type.replace('_', ' ')}</strong>
          <span style="background: ${event.detected ? 'rgba(239, 68, 68, 0.25)' : 'rgba(0, 245, 155, 0.2)'}; color: ${event.detected ? '#ff4d6d' : '#00f59b'}; border: 1px solid ${event.detected ? 'rgba(239,68,68,0.5)' : 'rgba(0,245,155,0.4)'}; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 10px; letter-spacing: 0.5px;">
            ${event.detected ? 'ALARM / DANGER' : 'CLEAR'}
          </span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; margin-bottom: 2px;">
          <span>NODE: <strong style="color: #cbd5e1; font-family: monospace;">${event.device_id}</strong></span>
          <span>GPS: <strong style="color: #cbd5e1; font-family: monospace;">${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}</strong></span>
        </div>
        <div style="margin: 8px 0; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);">
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <span style="font-size: 10px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Composite Risk</span>
            <span style="font-family: monospace; font-size: 18px; font-weight: 800; color: #ff2a5f;">${event.final_risk_score.toFixed(1)}%</span>
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 2px;">Severity Classification: <strong style="color: #facc15;">${event.risk_level}</strong></div>
        </div>
        ${radiiBox}
        ${firmsInfo}
        <div style="margin-top: 8px; font-weight: 700; font-size: 10px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px;">Telemetry Snapshot:</div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 11px;">
          ${sensorRows}
        </table>
        <div style="margin-top: 8px; font-size: 10px; color: #64748b; font-family: monospace;">
          TIMESTAMP: ${event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'N/A'}
        </div>
      </div>
    `;

    marker.bindPopup(popupHtml).openPopup();
  }

  renderFirmsHotspots(hotspots) {
    // Clear previous
    this.firmsMarkers.forEach((m) => this.map.removeLayer(m));
    this.firmsMarkers = [];

    hotspots.forEach((hs) => {
      const icon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="firms-marker" title="NASA FIRMS Active Thermal Anomaly">🛰️</div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const m = L.marker([hs.latitude, hs.longitude], { icon }).addTo(this.map);
      m.bindPopup(`
        <div style="font-family: sans-serif; font-size: 11px; color: #1e293b;">
          <strong>🛰️ NASA FIRMS Hotspot</strong><br>
          Satellite: ${hs.satellite || "VIIRS"}<br>
          Brightness: ${hs.brightness} K<br>
          Confidence: ${hs.confidence}<br>
          GPS: ${hs.latitude.toFixed(4)}, ${hs.longitude.toFixed(4)}
        </div>
      `);
      this.firmsMarkers.push(m);
    });
  }

  renderStations(category, stations) {
    if (!this.map || !stations) return;
    if (!this.categoryLayerGroups) this.categoryLayerGroups = {};
    if (!this.stationMarkers) this.stationMarkers = {};

    // Remove existing layer for this category
    if (this.categoryLayerGroups[category]) {
      this.map.removeLayer(this.categoryLayerGroups[category]);
    }
    this.categoryLayerGroups[category] = L.featureGroup().addTo(this.map);

    let emoji = "⛰️";
    let defaultPin = "station-pin-normal";
    let agencyTag = "GSI SECTOR";
    let themeColor = "#ffb703";

    if (category === "flood") {
      emoji = "🌊";
      defaultPin = "station-pin-flood";
      agencyTag = "CWC BASIN";
      themeColor = "#00f0ff";
    } else if (category === "wildfire") {
      emoji = "🔥";
      defaultPin = "station-pin-wildfire";
      agencyTag = "FSI SECTOR";
      themeColor = "#ff2a5f";
    }

    stations.forEach((st) => {
      const isLive = Boolean(st.is_active_iot_field_unit);
      const pinClass = isLive ? "station-pin-active" : defaultPin;
      const icon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="station-pin-marker ${pinClass}" style="width: 32px; height: 32px;" title="${st.id}: ${st.name}">${emoji}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([st.latitude, st.longitude], { icon }).addTo(this.categoryLayerGroups[category]);
      this.stationMarkers[st.id] = marker;

      let specRows = "";
      if (category === "flood") {
        specRows = `
          <div>WATERWAY: <span style="color: #38bdf8;">${st.waterway || "Channel"}</span></div>
          <div>DANGER STAGE: <span style="color: #facc15;">${st.danger_level_m}m MSL</span> | ELEV: ${st.elevation_m}m</div>
          <div>CWC CLASS: <span style="color: #ef4444; font-weight: bold;">${st.cwc_index}</span></div>
        `;
      } else if (category === "wildfire") {
        specRows = `
          <div>BIOME: <span style="color: #f87171;">${st.biome || "Forest"}</span></div>
          <div>FUEL: <span style="color: #facc15;">${st.canopy_fuel || "Canopy"}</span></div>
          <div>FSI CLASS: <span style="color: #ef4444; font-weight: bold;">${st.fsi_hazard_class}</span></div>
        `;
      } else {
        specRows = `
          <div>GPS: <span style="color: #38bdf8;">${st.latitude.toFixed(4)}° N, ${st.longitude.toFixed(4)}° E</span></div>
          <div>SLOPE: <span style="color: #facc15;">${st.slope_deg}° Incline</span> | ELEV: ${st.elevation_m}m ASL</div>
          <div>GSI CLASS: <span style="color: #f97316; font-weight: bold;">${st.gsi_susceptibility}</span></div>
        `;
      }

      const popupHtml = `
        <div style="font-family: var(--font-main, sans-serif); min-width: 260px; font-size: 12px; color: #f8fafc; line-height: 1.4;">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px;">
            <strong style="font-size: 13px; color: ${themeColor};">${st.id} • ${st.name}</strong>
            <span style="background: ${isLive ? 'rgba(239, 68, 68, 0.25)' : 'rgba(255, 255, 255, 0.1)'}; color: ${isLive ? '#ff4d6d' : '#f1f5f9'}; border: 1px solid ${isLive ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.2)'}; padding: 1px 6px; border-radius: 4px; font-weight: 800; font-size: 9px;">
              ${isLive ? '🔴 LIVE IOT UNIT' : `🟡 ${agencyTag}`}
            </span>
          </div>
          <div style="font-size: 11px; color: #cbd5e1; margin-bottom: 4px;">
            📍 ${st.district}, ${st.state} (${st.region || ""})
          </div>
          <div style="background: rgba(0,0,0,0.3); border-radius: 6px; padding: 6px 8px; margin: 6px 0; font-size: 11px; font-family: monospace;">
            ${specRows}
          </div>
          <div style="font-size: 10.5px; color: #f87171; margin-bottom: 4px;">
            ⚠️ <strong>Impact Threat:</strong> ${st.downhill_assets}
          </div>
          <div style="font-size: 10px; color: #34d399; margin-bottom: 8px;">
            🛡️ <strong>Safe Evacuation:</strong> ${st.safe_assembly}
          </div>
          <button onclick="window.dashboardController.selectStation('${category}', '${st.id}')" style="width: 100%; background: linear-gradient(135deg, ${themeColor}, #f59e0b); border: none; color: #000; font-weight: 800; padding: 5px 8px; border-radius: 5px; cursor: pointer; font-size: 10px;">
            🎯 MONITOR & BIND THIS SECTOR
          </button>
        </div>
      `;
      marker.bindPopup(popupHtml);
    });
  }

  renderLandslideStations(stations) {
    this.renderStations("landslide", stations);
  }

  renderFloodStations(stations) {
    this.renderStations("flood", stations);
  }

  renderWildfireStations(stations) {
    this.renderStations("wildfire", stations);
  }

  focusStation(stationId) {
    if (!this.stationMarkers || !this.stationMarkers[stationId]) return;
    const marker = this.stationMarkers[stationId];
    const latLng = marker.getLatLng();
    this.map.flyTo(latLng, 12, { duration: 1.2 });
    setTimeout(() => {
      marker.openPopup();
    }, 1250);
  }

  focusLandslideStation(stationId) {
    this.focusStation(stationId);
  }
}

// Global instance for dashboard
window.disasterMap = new DisasterMapManager();
