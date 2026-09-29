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
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <TinyGPSPlus.h>
#include <Fire-JARVIS_inferencing.h>

// ============================================================
// FIRE / GAS NODE (Node 3) — ESP32
// Sensors: MQ-2, MQ-135, MQ-7, GP2Y1010 dust, flame IR, BME280,
//          NEO-6M GPS, battery sense.
// Outputs: 16x2 I2C LCD, buzzer, GREEN/AMBER/RED status LEDs.
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
// Common slots: 8=lat, 9=lon, 10=battery_V
// Node 3 Fire/Gas: 0=mq2_V, 1=mq135_V, 2=mq7_V, 3=dust_ugm3, 4=flame_raw,
//                  5=bme_temp_c, 6=bme_humidity_pct, 7=bme_pressure_hpa

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

constexpr uint32_t NODE_ID = 3;
const uint8_t BROADCAST_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint32_t sequenceNumber = 0;

// ---- Pin map (from your Fire/Gas schematic) ----
constexpr int MQ2_PIN = 34;
constexpr int MQ135_PIN = 35;
constexpr int MQ7_PIN = 39;
constexpr int DUST_LED_PIN = 25;
constexpr int DUST_VO_PIN = 32;
constexpr int FLAME_PIN = 33;
constexpr int BUZZER_PIN = 13;
constexpr int LED_GREEN = 4;
constexpr int LED_AMBER = 2;
constexpr int LED_RED = 15;
constexpr int BATTERY_PIN = 36;
constexpr int GPS_RX2_PIN = 16;
constexpr int GPS_TX2_PIN = 17;

constexpr float ADC_VREF = 3.3f;
constexpr int ADC_MAX = 4095;
constexpr float DIVIDER_RATIO = 20000.0f / (10000.0f + 20000.0f);  // 0.667
constexpr float BATTERY_DIVIDER_RATIO = 2.0f;  // 100k/100k

// ---- Alarm thresholds (raw sensor voltage) ----
constexpr float MQ2_ALARM_V = 2.5f;
constexpr float MQ135_ALARM_V = 2.5f;
constexpr float MQ7_ALARM_V = 2.5f;
constexpr float DUST_ALARM_UGM3 = 150.0f;
constexpr int FLAME_ALARM_RAW = 1500;  // flame IR: lower raw = closer flame

LiquidCrystal_I2C lcd(0x27, 16, 2);
Adafruit_BME280 bme;  // I2C, address 0x76
bool bmeOk = false;
TinyGPSPlus gps;
HardwareSerial GPSSerial(2);

float adcToActualVoltage(int raw) {
  float adcVoltage = raw * (ADC_VREF / ADC_MAX);
  return adcVoltage / DIVIDER_RATIO;  // real sensor output before divider
}

float readDustUgm3() {
  digitalWrite(DUST_LED_PIN, LOW);  // GP2Y1010: LED on, active-low drive
  delayMicroseconds(280);
  int raw = analogRead(DUST_VO_PIN);
  delayMicroseconds(40);
  digitalWrite(DUST_LED_PIN, HIGH);  // LED off
  delayMicroseconds(9680);
  float voltage = adcToActualVoltage(raw);
  float density = (0.17f * voltage - 0.1f) * 1000.0f;
  return density < 0 ? 0 : density;
}

float readBatteryVoltage() {
  return analogRead(BATTERY_PIN) * (ADC_VREF / ADC_MAX) * BATTERY_DIVIDER_RATIO;
}

// ------------------------------------------------------------
// 3. POST TELEMETRY JSON TO DASHBOARD SERVER
// ------------------------------------------------------------
void sendTelemetryToDashboard(float mq2V, float mq135V, float mq7V, float dust,
                              int flameRaw, bool flameDetected,
                              float bmeTemp, float bmeHumidity, float bmePressure,
                              float battV, double lat, double lon, int alarmLevel, uint32_t seq) {
  if (WiFi.status() != WL_CONNECTED) {
    return; // Handled by checkWiFiReconnection watchdog
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000);  // 2s timeout prevents blocking loop()

  char payload[600];
  snprintf(payload, sizeof(payload),
    "{"
      "\"device_id\":\"FIRE_001\","
      "\"hazard_type\":\"WILDFIRE\","
      "\"latitude\":%.6f,"
      "\"longitude\":%.6f,"
      "\"sensor_data\":{"
        "\"mq2_v\":%.2f,"
        "\"mq135_v\":%.2f,"
        "\"mq7_v\":%.2f,"
        "\"dust_ugm3\":%.1f,"
        "\"flame_raw\":%d,"
        "\"flame_detected\":%s,"
        "\"temperature\":%.1f,"
        "\"humidity\":%.1f,"
        "\"bme_pressure\":%.1f,"
        "\"battery_v\":%.2f,"
        "\"alarm_level\":%d,"
        "\"sequence\":%lu"
      "}"
    "}",
    lat, lon, mq2V, mq135V, mq7V, dust, flameRaw,
    flameDetected ? "true" : "false",
    bmeTemp, bmeHumidity, bmePressure, battV, alarmLevel, (unsigned long)seq
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
// 4. SETUP
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.printf("\n=========================================\n");
  Serial.printf("FIRE/GAS NODE %lu - LIVE SENSOR DATA & DASHBOARD\n", (unsigned long)NODE_ID);
  Serial.printf("=========================================\n");

  pinMode(DUST_LED_PIN, OUTPUT);
  digitalWrite(DUST_LED_PIN, HIGH);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_AMBER, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX2_PIN, GPS_TX2_PIN);

  Wire.begin(21, 22);
  bmeOk = bme.begin(0x76);
  if (!bmeOk) Serial.println("WARNING: BME280 not found at 0x76 - check wiring");

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Fire/Gas Node");
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
// 5. MAIN LOOP
// ------------------------------------------------------------
int displayIndex = 0;
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

  float mq2V = adcToActualVoltage(analogRead(MQ2_PIN));
  float mq135V = adcToActualVoltage(analogRead(MQ135_PIN));
  float mq7V = adcToActualVoltage(analogRead(MQ7_PIN));
  float dust = readDustUgm3();
  int flameRaw = analogRead(FLAME_PIN);
  float battV = readBatteryVoltage();
  float bmeTemp = bmeOk ? bme.readTemperature() : 0;
  float bmeHumidity = bmeOk ? bme.readHumidity() : 0;
  float bmePressure = bmeOk ? bme.readPressure() / 100.0f : 0;
  bool haveFix = gps.location.isValid();

  // Real GPS if acquired, otherwise indoor fallback
  double lat = haveFix ? gps.location.lat() : DEFAULT_LAT;
  double lon = haveFix ? gps.location.lng() : DEFAULT_LON;

  bool flameDetected = flameRaw <= FLAME_ALARM_RAW;
  int alarmLevel = 0;
  if (flameDetected || mq2V >= MQ2_ALARM_V || mq135V >= MQ135_ALARM_V ||
      mq7V >= MQ7_ALARM_V || dust >= DUST_ALARM_UGM3) {
    alarmLevel = 2;
  } else if (mq2V >= MQ2_ALARM_V * 0.7f || mq135V >= MQ135_ALARM_V * 0.7f ||
             mq7V >= MQ7_ALARM_V * 0.7f || dust >= DUST_ALARM_UGM3 * 0.7f) {
    alarmLevel = 1;
  }
  digitalWrite(LED_GREEN, alarmLevel == 0 ? HIGH : LOW);
  digitalWrite(LED_AMBER, alarmLevel == 1 ? HIGH : LOW);
  digitalWrite(LED_RED, alarmLevel == 2 ? HIGH : LOW);
  digitalWrite(BUZZER_PIN, alarmLevel == 2 ? HIGH : LOW);

  // 1. ESP-NOW Broadcast to physical Receiver Node
  SensorPacket packet = {};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.node = NODE_ID;
  packet.sequence = ++sequenceNumber;
  packet.value[0] = mq2V;
  packet.value[1] = mq135V;
  packet.value[2] = mq7V;
  packet.value[3] = dust;
  packet.value[4] = (float)flameRaw;
  packet.value[5] = bmeTemp;
  packet.value[6] = bmeHumidity;
  packet.value[7] = bmePressure;
  packet.value[8] = (float)lat;
  packet.value[9] = (float)lon;
  packet.value[10] = battV;
  packet.validMask = (1u << 0) | (1u << 1) | (1u << 2) | (1u << 3) | (1u << 4) |
                      (bmeOk ? ((1u << 5) | (1u << 6) | (1u << 7)) : 0) |
                      ((1u << 8) | (1u << 9)) | (1u << 10);

  esp_err_t result = esp_now_send(BROADCAST_MAC, reinterpret_cast<const uint8_t *>(&packet), sizeof(packet));

  // Detailed GPS status
  uint32_t chars = gps.charsProcessed();
  int sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
  
  if (haveFix) {
    Serial.printf("🎯 [GPS FIX] LAT: %.6f, LON: %.6f | Sats: %d\n", lat, lon, sats);
  } else if (chars == 0 && millis() > 8000) {
    Serial.println("⚠️ [GPS WARNING] 0 characters received! Check wiring: GPS TX -> ESP32 Pin 16, GPS RX -> ESP32 Pin 17, and check VCC/GND!");
  }

  Serial.printf("Node3 | MQ2:%.2fV MQ135:%.2fV MQ7:%.2fV Dust:%.1fug/m3 Flame:%d(%s) "
                "T:%.1fC H:%.1f%% P:%.1fhPa Batt:%.2fV Fix:%d Sats:%d | %s\n",
                mq2V, mq135V, mq7V, dust, flameRaw, flameDetected ? "FIRE" : "clear",
                bmeTemp, bmeHumidity, bmePressure, battV, haveFix ? 1 : 0, sats,
                result == ESP_OK ? "sent" : esp_err_to_name(result));

  // 2. HTTP POST Telemetry directly to Central Receiver Dashboard
  sendTelemetryToDashboard(mq2V, mq135V, mq7V, dust, flameRaw, flameDetected,
                           bmeTemp, bmeHumidity, bmePressure, battV, lat, lon, alarmLevel, sequenceNumber);

  // 3. LCD Screen Cycling (Matches Receiver LCD output format)
  char line2[17];
  switch (displayIndex) {
    case 0: snprintf(line2, sizeof(line2), "MQ2:%4.2f MQ135:%4.2f", mq2V, mq135V); line2[16] = '\0'; break;
    case 1: snprintf(line2, sizeof(line2), "MQ7:%4.2fV", mq7V); break;
    case 2: snprintf(line2, sizeof(line2), "Dust:%6.1f", dust); break;
    case 3: snprintf(line2, sizeof(line2), "Flame:%s", flameDetected ? "DETECTED" : "clear"); break;
    case 4: snprintf(line2, sizeof(line2), "T:%4.1fC H:%4.1f%%", bmeTemp, bmeHumidity); break;
    default: snprintf(line2, sizeof(line2), "Batt:%4.2fV", battV); break;
  }
  displayIndex = (displayIndex + 1) % 6;
  const char *alarmText = alarmLevel == 2 ? "ALARM" : (alarmLevel == 1 ? "WARN " : "CLEAR");
  lcd.setCursor(0, 0);
  lcd.printf("FireGas: %s", alarmText);
  lcd.setCursor(0, 1);
  lcd.print(line2);
  lcd.print("                ");
}
