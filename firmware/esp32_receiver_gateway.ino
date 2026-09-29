#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_err.h>
#include <esp_system.h>
#include <esp_arduino_version.h>
#include <string.h>
#include <stdarg.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <SPI.h>
#include <TFT_eSPI.h>

// ============================================================
// RECEIVER GATEWAY — ESP32 + 2.8" ILI9341 SPI TFT
// Parses real-sensor packets from all 3 transmitters and shows
// a 3-column FLOOD / LANDSLIDE / FIRE-GAS status screen.
//
// TFT_eSPI wiring (verify User_Setup.h):
//   CS=15, RST=4, DC=2, MOSI=23, SCK=18
//   LED tied directly to 3.3V (no GPIO), MISO unconnected.
// ============================================================

// ------------------------------------------------------------
// 1. WI-FI & HOTSPOT CONFIGURATION
// Matches the hotspot shared by the Transmitters and Dashboard.
// ------------------------------------------------------------
const char* WIFI_SSID     = "Aniruth reddy's 25";
const char* WIFI_PASSWORD = "aniruth26";

constexpr uint32_t PACKET_MAGIC = 0x53494832;
constexpr uint32_t PROTOCOL_VERSION = 2;  // must match all 3 transmitters

// ---- SHARED PACKET FORMAT — 68 bytes byte-identical on all 4 boards ----
struct SensorPacket {
  uint32_t magic;
  uint32_t version;
  uint32_t node;
  uint32_t sequence;
  float value[12];
  uint32_t validMask;
};
// Common slots: 8=lat, 9=lon, 10=battery_V, 11=solar_V (landslide only)
// Node 1 Flood:     0=distance_cm, 1=flow_lpm, 2=rain_pct, 3=temp_c, 4=humidity_pct
// Node 2 Landslide: 0=pressure_raw, 1=soil_pct, 2=rain_pct
// Node 3 Fire/Gas:  0=mq2_V, 1=mq135_V, 2=mq7_V, 3=dust_ugm3, 4=flame_raw,
//                   5=bme_temp_c, 6=bme_humidity_pct, 7=bme_pressure_hpa

void requireOK(esp_err_t result, const char *operation) {
  if (result == ESP_OK) return;
  Serial.printf("STOP: %s: %s (%d)\n", operation, esp_err_to_name(result), (int)result);
  while (true) delay(1000);
}

inline bool isSlotValid(const SensorPacket &p, int slot) {
  return (p.validMask >> slot) & 1u;
}

// ------------------------------------------------------------
// Radio & Channel Management
// ------------------------------------------------------------
String resolvedSSID = WIFI_SSID;
uint8_t currentRadioChannel = 1;
bool wifiIsConnected = false;

struct ReceivedPacket {
  SensorPacket packet;
  uint8_t mac[6];
};

QueueHandle_t receiveQueue = nullptr;
const char *nodeNames[4] = {"", "FLOOD", "LANDSLIDE", "FIRE-GAS"};
SensorPacket latest[4] = {};
uint32_t receivedCount[4] = {};
uint32_t lastSeen[4] = {};
bool hasReceived[4] = {};
bool nodeIsOnline[4] = {};
uint8_t sourceMac[4][6] = {};
uint32_t lastSummary = 0;
uint32_t lastStatusBarUpdate = 0;

// Alarm level re-derived on receiver so the TFT banner matches
// transmitter logic (exact same thresholds).
int alarmLevelFor(uint32_t node, const SensorPacket &p) {
  if (node == 1) {  // Flood
    int level = 0;
    if (isSlotValid(p, 0)) {
      if (p.value[0] <= 25.0f) level = 2;
      else if (p.value[0] <= 50.0f) level = 1;
    }
    if (isSlotValid(p, 2) && p.value[2] >= 85.0f) level = 2;
    else if (isSlotValid(p, 2) && p.value[2] >= 60.0f && level < 1) level = 1;
    return level;
  }
  if (node == 2) {  // Landslide
    int level = 0;
    if (isSlotValid(p, 1) && p.value[1] >= 80.0f) level = 2;
    else if (isSlotValid(p, 1) && p.value[1] >= 56.0f && level < 1) level = 1;
    if (isSlotValid(p, 2) && p.value[2] >= 85.0f) level = 2;
    else if (isSlotValid(p, 2) && p.value[2] >= 59.5f && level < 1) level = 1;
    return level;
  }
  if (node == 3) {  // Fire/Gas
    int level = 0;
    if (isSlotValid(p, 4) && p.value[4] <= 1500) level = 2;
    if (isSlotValid(p, 0) && p.value[0] >= 2.5f) level = 2;
    if (isSlotValid(p, 1) && p.value[1] >= 2.5f) level = 2;
    if (isSlotValid(p, 2) && p.value[2] >= 2.5f) level = 2;
    if (isSlotValid(p, 3) && p.value[3] >= 150.0f) level = 2;
    if (level == 0) {
      if ((isSlotValid(p, 0) && p.value[0] >= 1.75f) ||
          (isSlotValid(p, 1) && p.value[1] >= 1.75f) ||
          (isSlotValid(p, 2) && p.value[2] >= 1.75f) ||
          (isSlotValid(p, 3) && p.value[3] >= 105.0f)) {
        level = 1;
      }
    }
    return level;
  }
  return 0;
}

void enqueuePacket(const uint8_t *mac, const uint8_t *data, int length) {
  if (!mac || !data || length != (int)sizeof(SensorPacket)) return;
  ReceivedPacket item = {};
  memcpy(&item.packet, data, sizeof(SensorPacket));
  if (item.packet.magic != PACKET_MAGIC ||
      item.packet.version != PROTOCOL_VERSION ||
      item.packet.node < 1 || item.packet.node > 3) return;
  memcpy(item.mac, mac, sizeof(item.mac));
  if (xQueueSend(receiveQueue, &item, 0) != pdTRUE) {
    // Queue full - dropped
  }
}

#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int length) {
  if (info) enqueuePacket(info->src_addr, data, length);
}
#else
void onReceive(const uint8_t *mac, const uint8_t *data, int length) {
  enqueuePacket(mac, data, length);
}
#endif

// ---- TFT SETUP ----
TFT_eSPI tft = TFT_eSPI();
constexpr int COL_W = 106;  // 320px wide / 3 columns
constexpr uint16_t COLOR_CLEAR = TFT_GREEN;
constexpr uint16_t COLOR_WARN  = TFT_YELLOW;
constexpr uint16_t COLOR_ALARM = TFT_RED;
constexpr uint16_t COLOR_WAIT  = TFT_DARKGREY;

void drawStaticLayout() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(1);
  for (int i = 0; i < 3; i++) {
    tft.drawFastVLine(i * COL_W, 0, 222, TFT_DARKGREY);
    tft.drawString(nodeNames[i + 1], i * COL_W + COL_W / 2, 4, 1);
  }
  // Bottom status divider
  tft.drawFastHLine(0, 223, 320, TFT_DARKGREY);
}

void drawStatusBar() {
  tft.fillRect(0, 224, 320, 16, TFT_NAVY);
  tft.setTextColor(TFT_WHITE, TFT_NAVY);
  tft.setTextDatum(TL_DATUM);
  tft.setTextSize(1);
  char buf[64];
  uint32_t totalPkts = receivedCount[1] + receivedCount[2] + receivedCount[3];
  snprintf(buf, sizeof(buf), "Ch:%d | WiFi:%s | Total:%lu",
           currentRadioChannel,
           wifiIsConnected ? "CONNECTED" : "LOCKED",
           (unsigned long)totalPkts);
  tft.drawString(buf, 6, 228, 1);
}

void printTftLine(int x, int &y, const char *fmt, ...) {
  char buf[32];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  tft.drawString(buf, x, y, 1);
  y += 11;
}

void drawColumn(uint32_t node) {
  if (node < 1 || node > 3) return;
  int x0 = (node - 1) * COL_W + 4;
  int colLeft = (node - 1) * COL_W + 1;
  int colWidth = COL_W - 2;

  // Clear column body below header (16 to 222)
  tft.fillRect(colLeft, 16, colWidth, 206, TFT_BLACK);

  if (!hasReceived[node]) {
    // Show WAITING state immediately so column is never blank
    tft.fillRect(colLeft, 16, colWidth, 12, TFT_DARKGREY);
    tft.setTextColor(TFT_WHITE, TFT_DARKGREY);
    tft.setTextDatum(TC_DATUM);
    tft.drawString("WAITING", (node - 1) * COL_W + COL_W / 2, 17, 1);

    tft.setTextColor(COLOR_WAIT, TFT_BLACK);
    tft.setTextDatum(TL_DATUM);
    tft.drawString("Awaiting", x0, 36, 1);
    tft.drawString("packets...", x0, 48, 1);
    return;
  }

  bool online = (millis() - lastSeen[node]) <= 6000;
  const SensorPacket &p = latest[node];
  int level = alarmLevelFor(node, p);
  uint16_t bannerColor = !online ? COLOR_WAIT : (level == 2 ? COLOR_ALARM : (level == 1 ? COLOR_WARN : COLOR_CLEAR));
  const char *bannerText = !online ? "OFFLINE" : (level == 2 ? "ALARM" : (level == 1 ? "WARNING" : "CLEAR"));

  tft.fillRect(colLeft, 16, colWidth, 12, bannerColor);
  tft.setTextColor(TFT_BLACK, bannerColor);
  tft.setTextDatum(TC_DATUM);
  tft.drawString(bannerText, (node - 1) * COL_W + COL_W / 2, 17, 1);

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(TL_DATUM);
  int y = 32;

  if (node == 1) {
    if (isSlotValid(p, 0)) printTftLine(x0, y, "Dist:%.0fcm", p.value[0]); else printTftLine(x0, y, "Dist:--");
    if (isSlotValid(p, 1)) printTftLine(x0, y, "Flow:%.1fL/m", p.value[1]);
    if (isSlotValid(p, 2)) printTftLine(x0, y, "Rain:%.0f%%", p.value[2]);
    if (isSlotValid(p, 3)) printTftLine(x0, y, "T:%.1fC", p.value[3]);
    if (isSlotValid(p, 4)) printTftLine(x0, y, "H:%.0f%%", p.value[4]);
  } else if (node == 2) {
    if (isSlotValid(p, 0)) printTftLine(x0, y, "Pres:%.0f", p.value[0]); else printTftLine(x0, y, "Pres:--");
    if (isSlotValid(p, 1)) printTftLine(x0, y, "Soil:%.0f%%", p.value[1]);
    if (isSlotValid(p, 2)) printTftLine(x0, y, "Rain:%.0f%%", p.value[2]);
    if (isSlotValid(p, 11)) printTftLine(x0, y, "Solar:%.1fV", p.value[11]);
  } else if (node == 3) {
    if (isSlotValid(p, 0)) printTftLine(x0, y, "MQ2:%.2fV", p.value[0]);
    if (isSlotValid(p, 1)) printTftLine(x0, y, "MQ135:%.2fV", p.value[1]);
    if (isSlotValid(p, 2)) printTftLine(x0, y, "MQ7:%.2fV", p.value[2]);
    if (isSlotValid(p, 3)) printTftLine(x0, y, "Dust:%.0f", p.value[3]);
    if (isSlotValid(p, 4)) printTftLine(x0, y, "Flame:%s", p.value[4] <= 1500 ? "YES" : "no");
  }
  if (isSlotValid(p, 10)) printTftLine(x0, y, "Bat:%.2fV", p.value[10]);
  printTftLine(x0, y, "#%lu", (unsigned long)p.sequence);
}

// ------------------------------------------------------------
// Smart Auto-Detect & Channel Sync
// ------------------------------------------------------------
void syncRadioChannelAndWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  Serial.println("\n=========================================");
  Serial.println("[Receiver] Scanning 2.4 GHz airwaves for hotspot...");
  int n = WiFi.scanNetworks();
  bool hotspotFound = false;
  uint8_t detectedChannel = 1;

  if (n == 0) {
    Serial.println("[WiFi] No networks found. Defaulting to Radio Channel 1.");
  } else {
    Serial.printf("[WiFi] Found %d networks in area:\n", n);
    for (int i = 0; i < n; ++i) {
      String s = WiFi.SSID(i);
      Serial.printf("   [%2d] \"%s\" | RSSI: %d dBm | Ch: %d\n",
                    i + 1, s.c_str(), WiFi.RSSI(i), WiFi.channel(i));

      String sLower = s;
      sLower.toLowerCase();
      if (sLower.indexOf("aniruth") >= 0 || sLower.indexOf("reddy") >= 0) {
        resolvedSSID = s;
        detectedChannel = WiFi.channel(i);
        hotspotFound = true;
        Serial.println("   ---------------------------------------------");
        Serial.printf("   >>> MATCHED HOTSPOT: \"%s\" (Channel %d)\n", s.c_str(), detectedChannel);
        Serial.println("   ---------------------------------------------");
      }
    }
  }

  currentRadioChannel = detectedChannel;

  WiFi.setAutoReconnect(false);
  WiFi.persistent(false);

  if (hotspotFound) {
    Serial.printf("[WiFi] Connecting to \"%s\"...\n", resolvedSSID.c_str());
    WiFi.begin(resolvedSSID.c_str(), WIFI_PASSWORD);

    unsigned long startWait = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startWait < 8000)) {
      delay(300);
      Serial.print(".");
    }
    Serial.println();
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiIsConnected = true;
    currentRadioChannel = WiFi.channel();
    Serial.println("\n*****************************************");
    Serial.println(">>> [WiFi] SUCCESS! RECEIVER CONNECTED TO HOTSPOT! <<<");
    Serial.printf("    Assigned Receiver IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("    Active Radio Channel: %d\n", currentRadioChannel);
    Serial.println("*****************************************\n");
  } else {
    wifiIsConnected = false;
    Serial.printf("\n[WiFi] Operating in standalone ESP-NOW mode on Channel %d\n", currentRadioChannel);
    // Explicitly lock hardware channel to match hotspot channel
    requireOK(esp_wifi_set_channel(currentRadioChannel, WIFI_SECOND_CHAN_NONE), "lock radio channel");
  }

  // CRITICAL: Disable all Wi-Fi modem sleep so RF receiver is awake 100% of the time!
  requireOK(esp_wifi_set_ps(WIFI_PS_NONE), "disable WiFi power save");

  Serial.printf("Receiver MAC: %s\n", WiFi.macAddress().c_str());
  requireOK(esp_now_init(), "ESP-NOW init");
  requireOK(esp_now_register_recv_cb(onReceive), "register receiver");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=========================================");
  Serial.println("RECEIVER GATEWAY - LIVE MULTI-DISASTER TFT");
  Serial.println("=========================================");

  // 1. Initialize Display First
  tft.init();
  tft.setRotation(1);  // landscape (320x240)
  drawStaticLayout();

  // Immediately draw all 3 columns as "WAITING" so screen is never blank
  for (uint32_t node = 1; node <= 3; ++node) {
    drawColumn(node);
  }
  drawStatusBar();

  // 2. Create FreeRTOS packet queue
  receiveQueue = xQueueCreate(32, sizeof(ReceivedPacket));
  if (!receiveQueue) {
    Serial.println("STOP: receive queue allocation failed");
    while (true) delay(1000);
  }

  // 3. Connect/Lock Radio Channel & Initialize ESP-NOW
  syncRadioChannelAndWiFi();

  // Update status bar with actual connected/channel status
  drawStatusBar();

  Serial.println("READY. Listening for Nodes 1 (Flood), 2 (Landslide), and 3 (Fire-Gas)...");
}

void loop() {
  ReceivedPacket item;
  bool packetReceived = false;

  // Process all queued ESP-NOW packets
  while (xQueueReceive(receiveQueue, &item, 0) == pdTRUE) {
    uint32_t node = item.packet.node;
    if (node < 1 || node > 3) continue;

    if (hasReceived[node] && memcmp(sourceMac[node], item.mac, 6) != 0) {
      Serial.printf("WARNING: Node %lu source MAC changed!\n", (unsigned long)node);
    }
    memcpy(sourceMac[node], item.mac, 6);
    hasReceived[node] = true;
    lastSeen[node] = millis();
    nodeIsOnline[node] = true;
    ++receivedCount[node];
    latest[node] = item.packet;
    packetReceived = true;

    const SensorPacket &p = item.packet;
    Serial.printf("[ESP-NOW RX] %s (Node %lu) Seq #%lu:",
                  nodeNames[node], (unsigned long)node, (unsigned long)p.sequence);
    for (int i = 0; i < 12; i++) {
      if ((p.validMask >> i) & 1u) Serial.printf(" v%d=%.2f", i, p.value[i]);
    }
    Serial.println();

    // Redraw the column with the updated packet data
    drawColumn(node);
  }

  uint32_t now = millis();

  // Update status bar if packets arrived or every 5 seconds
  if (packetReceived || (now - lastStatusBarUpdate >= 5000)) {
    lastStatusBarUpdate = now;
    drawStatusBar();
  }

  // Periodic offline watchdog & status summary every 2 seconds
  if ((uint32_t)(now - lastSummary) >= 2000) {
    lastSummary = now;
    for (uint32_t node = 1; node <= 3; ++node) {
      if (hasReceived[node]) {
        bool currentlyOnline = (now - lastSeen[node]) <= 6000;
        if (currentlyOnline != nodeIsOnline[node]) {
          nodeIsOnline[node] = currentlyOnline;
          drawColumn(node);  // Redraw column only when online/offline state changes!
        }
      }
    }
  }

  delay(10);
}
