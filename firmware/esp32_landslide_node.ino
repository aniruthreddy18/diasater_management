#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_err.h>
#include <esp_system.h>
#include <esp_arduino_version.h>
#include <string.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <TinyGPSPlus.h>
#include <Land_slide-JARVIS_inferencing.h>

// ============================================================
// LANDSLIDE NODE (Node 2) — ESP32
// Sensors: HX710B pressure, capacitive soil moisture, raindrop
//          MH-RD, NEO-6M GPS, battery + solar sense.
// Outputs: 16x2 I2C LCD, buzzer, single alarm LED.
// Comms: ESP-NOW (to receiver) + Wi-Fi HTTP POST (to Dashboard)
// ============================================================

// ------------------------------------------------------------
// 1. WI-FI & DASHBOARD CONFIGURATION
// ------------------------------------------------------------
const char* WIFI_SSID     = "Aniruth reddy's 25";
const char* WIFI_PASSWORD = "aniruth26";

// Dashboard server IP on Laptop 1 (Mac)
const char* SERVER_URL    = "http://10.166.170.10:8000/api/v1/telemetry";

// Default coordinates if testing indoors without GPS satellite fix
constexpr double DEFAULT_LAT = 17.3918;
constexpr double DEFAULT_LON = 78.3194;

// ------------------------------------------------------------
// 2. RADIO & PACKET DEFINITIONS
// ------------------------------------------------------------
constexpr uint8_t RADIO_CHANNEL = 1;
constexpr uint32_t PACKET_MAGIC = 0x53494832;
constexpr uint32_t PROTOCOL_VERSION = 2;

// ---- SHARED PACKET FORMAT — must be byte-identical on all 4 boards ----
struct SensorPacket {
  uint32_t magic;
  uint32_t version;
  uint32_t node;
  uint32_t sequence;
  float value[12];
  uint32_t validMask;
};
// Common slots: 8=lat, 9=lon, 10=battery_V, 11=solar_V
// Node 2 Landslide: 0=pressure_raw, 1=soil_pct, 2=rain_pct

void requireOK(esp_err_t result, const char *operation) {
  if (result == ESP_OK) return;
  Serial.printf("STOP: %s: %s (%d)\n", operation, esp_err_to_name(result), (int)result);
  while (true) delay(1000);
}

// ------------------------------------------------------------
// Smart Auto-Detecting Wi-Fi Connection
// ------------------------------------------------------------
String resolvedSSID = WIFI_SSID;

void connectToWiFiWithAutoDetect() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  Serial.println("\n=========================================");
  Serial.println("[WiFi] Scanning 2.4 GHz airwaves for hotspot...");
  int n = WiFi.scanNetworks();
  bool found = false;

  if (n == 0) {
    Serial.println("[WiFi ERROR] No 2.4GHz Wi-Fi networks found at all!");
    Serial.println("[WiFi ERROR] Please check if 2.4GHz is enabled on your phone hotspot.");
  } else {
    Serial.printf("[WiFi] Found %d networks in the area:\n", n);
    for (int i = 0; i < n; ++i) {
      String s = WiFi.SSID(i);
      Serial.printf("   [%2d] \"%s\" | Signal: %d dBm | Ch: %d\n",
                    i + 1, s.c_str(), WiFi.RSSI(i), WiFi.channel(i));

      // Case-insensitive check to catch smart quotes, capitalization, or extra spaces:
      String sLower = s;
      sLower.toLowerCase();
      if (sLower.indexOf("aniruth") >= 0 || sLower.indexOf("reddy") >= 0) {
        resolvedSSID = s; // Grab the EXACT broadcasted string from the air!
        found = true;
        Serial.println("   ---------------------------------------------");
        Serial.printf("   >>> MATCHED YOUR HOTSPOT: \"%s\" (Channel %d)\n", s.c_str(), WiFi.channel(i));
        Serial.println("   ---------------------------------------------");
      }
    }
  }

  if (!found) {
    Serial.println("\n[!] CAUTION: Could not find any network containing 'aniruth' or 'reddy'.");
    Serial.println("[!] Check phone hotspot:");
    Serial.println("    1. Hotspot Band must be set to 2.4 GHz (ESP32 cannot see 5 GHz).");
    Serial.println("    2. Hotspot Security must be WPA2-Personal (not WPA3).");
    Serial.println("    3. Ensure hotspot visibility is ON.");
  }

  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  WiFi.setSleep(false);
  Serial.printf("\n[WiFi] Connecting to \"%s\" with password \"%s\"...\n",
                resolvedSSID.c_str(), WIFI_PASSWORD);
  WiFi.begin(resolvedSSID.c_str(), WIFI_PASSWORD);

  // Allow up to 15 seconds for association & DHCP lease
  unsigned long startWait = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startWait < 15000)) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n*****************************************");
    Serial.println(">>> [WiFi] SUCCESS! CONNECTED TO HOTSPOT! <<<");
    Serial.printf("    Assigned ESP32 IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("    Wi-Fi Channel:     %d\n", WiFi.channel());
    Serial.printf("    Dashboard Target:  %s\n", SERVER_URL);
    Serial.println("*****************************************\n");
  } else {
    Serial.printf("\n[WiFi] Connection timed out (Status: %d). Will auto-retry in background.\n\n", WiFi.status());
  }

  Serial.printf("[ESP-NOW] Transmitter MAC: %s\n", WiFi.macAddress().c_str());
  requireOK(esp_now_init(), "ESP-NOW init");
}

void checkWiFiReconnection() {
  static unsigned long lastRetry = 0;
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastRetry > 15000) {
      lastRetry = millis();
      Serial.printf("[WiFi Watchdog] Reconnecting to \"%s\" (status: %d)...\n", resolvedSSID.c_str(), WiFi.status());
      WiFi.disconnect();
      delay(100);
      WiFi.begin(resolvedSSID.c_str(), WIFI_PASSWORD);
    }
  }
}

constexpr uint32_t NODE_ID = 2;
const uint8_t BROADCAST_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint32_t sequenceNumber = 0;

// ------------------------------------------------------------
// 3. HARDWARE PIN DEFINITIONS (From Landslide Schematic)
// ------------------------------------------------------------
constexpr int HX_DOUT = 32;
constexpr int HX_SCK = 33;
constexpr int SOIL_PIN = 34;
constexpr int RAIN_AO_PIN = 39;
constexpr int RAIN_DO_PIN = 27;
constexpr int RAIN_POWER_PIN = 4;  // sensor VCC switched from a GPIO per schematic
constexpr int ALARM_LED_PIN = 25;
constexpr int BUZZER_PIN = 13;
constexpr int BATTERY_PIN = 35;
constexpr int SOLAR_PIN = 36;
constexpr int GPS_RX2_PIN = 16;
constexpr int GPS_TX2_PIN = 17;

// ---- Alarm thresholds ----
constexpr float SOIL_ALARM_PCT = 80.0f;        // saturated soil = higher slip risk
constexpr float RAIN_ALARM_PCT = 85.0f;
constexpr long PRESSURE_ALARM_DELTA = 500;     // raw-count shift from baseline

constexpr float ADC_VREF = 3.3f;
constexpr int ADC_MAX = 4095;
constexpr float BATTERY_DIVIDER_RATIO = 2.0f;   // 100k/100k
constexpr float SOLAR_DIVIDER_RATIO = 3.128f;   // 100k/47k -> (100+47)/47

LiquidCrystal_I2C lcd(0x27, 16, 2);
TinyGPSPlus gps;
HardwareSerial GPSSerial(2);

// ---- HX710B 24-bit Pressure Sensor Reading ----
long readHX710() {
  unsigned long start = millis();
  while (digitalRead(HX_DOUT) == HIGH) {
    if (millis() - start > 200) return -1;  // not ready / not responding
  }
  long value = 0;
  for (int i = 0; i < 24; i++) {
    digitalWrite(HX_SCK, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | digitalRead(HX_DOUT);
    digitalWrite(HX_SCK, LOW);
    delayMicroseconds(1);
  }
  digitalWrite(HX_SCK, HIGH);  // 25th pulse selects gain/channel for next read
  delayMicroseconds(1);
  digitalWrite(HX_SCK, LOW);
  if (value & 0x800000) value |= 0xFF000000;  // sign-extend 24-bit two's complement
  return value;
}

float readSoilPercent() {
  int raw = analogRead(SOIL_PIN);
  constexpr int DRY_RAW = 3000;
  constexpr int WET_RAW = 1200;
  float pct = 100.0f * (DRY_RAW - raw) / (float)(DRY_RAW - WET_RAW);
  return constrain(pct, 0.0f, 100.0f);
}

float readRainPercent() {
  int raw = analogRead(RAIN_AO_PIN);
  constexpr int DRY_RAW = 4095;
  constexpr int WET_RAW = 1500;
  float pct = 100.0f * (DRY_RAW - raw) / (float)(DRY_RAW - WET_RAW);
  return constrain(pct, 0.0f, 100.0f);
}

float readBatteryVoltage() {
  return analogRead(BATTERY_PIN) * (ADC_VREF / ADC_MAX) * BATTERY_DIVIDER_RATIO;
}

float readSolarVoltage() {
  return analogRead(SOLAR_PIN) * (ADC_VREF / ADC_MAX) * SOLAR_DIVIDER_RATIO;
}

// ------------------------------------------------------------
// 4. POST TELEMETRY JSON TO DASHBOARD SERVER
// ------------------------------------------------------------
void sendTelemetryToDashboard(long pressureRaw, float soilPct, float rainPct,
                              float battV, float solarV,
                              double lat, double lon, int alarmLevel, uint32_t seq) {
  if (WiFi.status() != WL_CONNECTED) {
    return; // Handled by checkWiFiReconnection watchdog
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000);  // 2s timeout prevents blocking loop()

  char payload[512];
  snprintf(payload, sizeof(payload),
    "{"
      "\"device_id\":\"LANDSLIDE_001\","
      "\"hazard_type\":\"LANDSLIDE\","
      "\"latitude\":%.6f,"
      "\"longitude\":%.6f,"
      "\"sensor_data\":{"
        "\"pressure_raw\":%ld,"
        "\"soil_pct\":%.1f,"
        "\"rain_pct\":%.1f,"
        "\"battery_v\":%.2f,"
        "\"solar_v\":%.2f,"
        "\"alarm_level\":%d,"
        "\"sequence\":%lu"
      "}"
    "}",
    lat, lon, pressureRaw, soilPct, rainPct, battV, solarV, alarmLevel, (unsigned long)seq
  );

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    Serial.printf("[HTTP -> Dashboard] Sent OK (HTTP %d)\n", httpCode);
  } else {
    Serial.printf("[HTTP -> Dashboard] POST Failed: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
}

// ------------------------------------------------------------
// 5. SETUP
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.printf("\n=========================================\n");
  Serial.printf("LANDSLIDE NODE %lu - LIVE SENSOR DATA & DASHBOARD\n", (unsigned long)NODE_ID);
  Serial.printf("=========================================\n");

  pinMode(HX_DOUT, INPUT);
  pinMode(HX_SCK, OUTPUT);
  pinMode(RAIN_DO_PIN, INPUT);
  pinMode(RAIN_POWER_PIN, OUTPUT);
  digitalWrite(RAIN_POWER_PIN, HIGH);
  pinMode(ALARM_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX2_PIN, GPS_TX2_PIN);

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Landslide Node");
  lcd.setCursor(0, 1);
  lcd.print("Connecting WiFi");

  // Connect to Wi-Fi with auto-detection of exact SSID
  connectToWiFiWithAutoDetect();

  // Register ESP-NOW broadcast peer on the exact active Wi-Fi channel
  uint8_t activeChannel = WiFi.channel();
  if (activeChannel == 0) activeChannel = RADIO_CHANNEL;

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST_MAC, sizeof(BROADCAST_MAC));
  peer.channel = activeChannel;
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  requireOK(esp_now_add_peer(&peer), "add broadcast peer");

  Serial.println("\n=========================================");
  Serial.printf("[ESP-NOW] Active Broadcast Channel: %d\n", activeChannel);
  Serial.printf(">>> ATTENTION: Your RECEIVER board MUST also be on Channel %d to receive packets! <<<\n", activeChannel);
  Serial.println("=========================================\n");

  lcd.setCursor(0, 1);
  lcd.print("Ready! Live...  ");
  delay(1000);
  Serial.println("[SYSTEM] Ready to stream sensor telemetry.");
}

// ------------------------------------------------------------
// 6. MAIN LOOP
// ------------------------------------------------------------
int displayIndex = 0;
long baselinePressure = 0;
bool baselineSet = false;
uint32_t lastRead = 0;
constexpr uint32_t READ_INTERVAL_MS = 2000;

void loop() {
  // Feed GPS parser continuously
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  // Background watchdog to reconnect Wi-Fi if dropped
  checkWiFiReconnection();

  uint32_t now = millis();
  if (now - lastRead < READ_INTERVAL_MS) return;
  lastRead = now;

  long pressureRaw = readHX710();
  if (!baselineSet && pressureRaw != -1) {
    baselinePressure = pressureRaw;  // first good reading becomes reference point
    baselineSet = true;
  }
  float soilPct = readSoilPercent();
  float rainPct = readRainPercent();
  float battV = readBatteryVoltage();
  float solarV = readSolarVoltage();
  bool haveFix = gps.location.isValid();

  // Real GPS if acquired, otherwise indoor fallback
  double lat = haveFix ? gps.location.lat() : DEFAULT_LAT;
  double lon = haveFix ? gps.location.lng() : DEFAULT_LON;

  // Evaluate alarm state (matches physical receiver logic)
  int alarmLevel = 0;
  if (soilPct >= SOIL_ALARM_PCT || rainPct >= RAIN_ALARM_PCT) {
    alarmLevel = 2;
  } else if (soilPct >= SOIL_ALARM_PCT * 0.7f || rainPct >= RAIN_ALARM_PCT * 0.7f) {
    alarmLevel = 1;
  }
  digitalWrite(ALARM_LED_PIN, alarmLevel > 0 ? HIGH : LOW);
  digitalWrite(BUZZER_PIN, alarmLevel == 2 ? HIGH : LOW);

  // 1. ESP-NOW Broadcast to physical Receiver Node
  SensorPacket packet = {};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.node = NODE_ID;
  packet.sequence = ++sequenceNumber;
  packet.value[0] = (float)pressureRaw;
  packet.value[1] = soilPct;
  packet.value[2] = rainPct;
  packet.value[8] = (float)lat;
  packet.value[9] = (float)lon;
  packet.value[10] = battV;
  packet.value[11] = solarV;
  packet.validMask = (pressureRaw != -1 ? (1u << 0) : 0) | (1u << 1) | (1u << 2) |
                      ((1u << 8) | (1u << 9)) | (1u << 10) | (1u << 11);

  esp_err_t result = esp_now_send(BROADCAST_MAC, reinterpret_cast<const uint8_t *>(&packet), sizeof(packet));

  // Detailed GPS status
  uint32_t chars = gps.charsProcessed();
  int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
  
  if (haveFix) {
    Serial.printf("🎯 [GPS FIX] LAT: %.6f, LON: %.6f | Sats: %d\n", lat, lon, sats);
  } else if (chars == 0 && millis() > 8000) {
    Serial.println("⚠️ [GPS WARNING] 0 characters received! Check wiring: GPS TX -> ESP32 Pin 16, GPS RX -> ESP32 Pin 17, and check VCC/GND!");
  }

  Serial.printf("Node2 | Pressure:%ld Soil:%.1f%% Rain:%.1f%% Batt:%.2fV Solar:%.2fV Fix:%d Sats:%d | %s\n",
                pressureRaw, soilPct, rainPct, battV, solarV, haveFix ? 1 : 0, sats,
                result == ESP_OK ? "sent" : esp_err_to_name(result));

  // 2. HTTP POST Telemetry directly to Central Receiver Dashboard
  sendTelemetryToDashboard(pressureRaw, soilPct, rainPct, battV, solarV, lat, lon, alarmLevel, sequenceNumber);

  // 3. LCD Screen Cycling (Matches Receiver LCD output format)
  char line2[17];
  switch (displayIndex) {
    case 0: snprintf(line2, sizeof(line2), "Press:%7ld", pressureRaw); break;
    case 1: snprintf(line2, sizeof(line2), "Soil: %5.1f%%", soilPct); break;
    case 2: snprintf(line2, sizeof(line2), "Rain: %5.1f%%", rainPct); break;
    default: snprintf(line2, sizeof(line2), "Bat:%4.2f Sol:%4.2f", battV, solarV); break;
  }
  displayIndex = (displayIndex + 1) % 4;
  const char *alarmText = alarmLevel == 2 ? "ALARM" : (alarmLevel == 1 ? "WARN " : "CLEAR");
  lcd.setCursor(0, 0);
  lcd.printf("Slide: %s  ", alarmText);
  lcd.setCursor(0, 1);
  lcd.print(line2);
  lcd.print("                ");
}
