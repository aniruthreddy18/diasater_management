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
#include <DHT.h>
#include <TinyGPSPlus.h>
#include <Flood_JARVIS_inferencing.h>

// ============================================================
// FLOOD NODE (Node 1) — ESP32
// Sensors: AJ-SR04M ultrasonic, YF-S201 flow, raindrop,
//          DHT22, NEO-6M GPS, battery sense.
// Outputs: 16x2 I2C LCD, buzzer, RED/GREEN/YELLOW status LEDs.
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

struct SensorPacket {
  uint32_t magic;
  uint32_t version;
  uint32_t node;       // 1=Flood, 2=Landslide, 3=Fire/Gas
  uint32_t sequence;
  float value[12];
  uint32_t validMask;
};

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

constexpr uint32_t NODE_ID = 1;
const uint8_t BROADCAST_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint32_t sequenceNumber = 0;

// ------------------------------------------------------------
// 3. HARDWARE PIN DEFINITIONS
// ------------------------------------------------------------
constexpr int TRIG_PIN = 27;
constexpr int ECHO_PIN = 34;     // input-only pin
constexpr int FLOW_PIN = 35;     // input-only YF-S201 pulse
constexpr int RAIN_AO_PIN = 32;
constexpr int RAIN_DO_PIN = 39;
constexpr int DHT_PIN = 33;
constexpr int GPS_RX2_PIN = 16;  // ESP RX2 <- GPS TX
constexpr int GPS_TX2_PIN = 17;  // ESP TX2 -> GPS RX
constexpr int BATTERY_PIN = 36;
constexpr int BUZZER_PIN = 25;
constexpr int LED_RED = 4;
constexpr int LED_GREEN = 2;
constexpr int LED_YELLOW = 13;

// ---- Alarm thresholds ----
constexpr float FLOOD_WARN_CM = 50.0f;   // distance shrinking below this = water rising
constexpr float FLOOD_ALARM_CM = 25.0f;
constexpr float RAIN_WARN_PCT = 60.0f;
constexpr float RAIN_ALARM_PCT = 85.0f;

// ---- Battery sense ----
constexpr float BATTERY_DIVIDER_RATIO = 2.0f;
constexpr float ADC_VREF = 3.3f;
constexpr int ADC_MAX = 4095;

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHT_PIN, DHT22);
TinyGPSPlus gps;
HardwareSerial GPSSerial(2);

volatile uint32_t flowPulseCount = 0;
void IRAM_ATTR onFlowPulse() { flowPulseCount++; }

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return -1.0f;
  return (duration * 0.0343f) / 2.0f;
}

float readFlowLpm(uint32_t intervalMs) {
  noInterrupts();
  uint32_t pulses = flowPulseCount;
  flowPulseCount = 0;
  interrupts();
  return (pulses / 7.5f) * (60000.0f / intervalMs);
}

float readRainPercent() {
  int raw = analogRead(RAIN_AO_PIN);
  constexpr int DRY_RAW = 4095;
  constexpr int WET_RAW = 1500;
  float pct = 100.0f * (DRY_RAW - raw) / (float)(DRY_RAW - WET_RAW);
  return constrain(pct, 0.0f, 100.0f);
}

float readBatteryVoltage() {
  int raw = analogRead(BATTERY_PIN);
  return (raw * (ADC_VREF / ADC_MAX)) * BATTERY_DIVIDER_RATIO;
}

void setAlarmOutputs(int level) {  // 0=clear, 1=warning, 2=alarm
  digitalWrite(LED_GREEN, level == 0 ? HIGH : LOW);
  digitalWrite(LED_YELLOW, level == 1 ? HIGH : LOW);
  digitalWrite(LED_RED, level == 2 ? HIGH : LOW);
  digitalWrite(BUZZER_PIN, level == 2 ? HIGH : LOW);
}

// ------------------------------------------------------------
// 4. POST TELEMETRY JSON TO DASHBOARD SERVER
// ------------------------------------------------------------
void sendTelemetryToDashboard(float distance, float flow, float rainPct,
                              float tempC, float humidity, float battV,
                              double lat, double lon, int alarmLevel) {
  if (WiFi.status() != WL_CONNECTED) {
    return; // Quietly handled by checkWiFiReconnection watchdog
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000);  // 2s timeout prevents blocking loop()

  // Calculate relative water level (bank height 200cm - sensor distance)
  float waterLevel = (distance >= 0.0f) ? max(0.0f, 200.0f - distance) : 0.0f;

  char payload[512];
  snprintf(payload, sizeof(payload),
    "{"
      "\"device_id\":\"FLOOD_001\","
      "\"hazard_type\":\"FLASH_FLOOD\","
      "\"latitude\":%.6f,"
      "\"longitude\":%.6f,"
      "\"sensor_data\":{"
        "\"distance_cm\":%.1f,"
        "\"water_level\":%.1f,"
        "\"flow_lpm\":%.2f,"
        "\"rain_pct\":%.1f,"
        "\"temp_c\":%.1f,"
        "\"humidity_pct\":%.1f,"
        "\"battery_v\":%.2f,"
        "\"alarm_level\":%d"
      "}"
    "}",
    lat, lon, distance, waterLevel, flow, rainPct,
    isnan(tempC) ? 0.0f : tempC,
    isnan(humidity) ? 0.0f : humidity,
    battV, alarmLevel
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
  Serial.printf("FLOOD NODE %lu - LIVE SENSOR DATA & DASHBOARD\n", (unsigned long)NODE_ID);
  Serial.printf("=========================================\n");

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(FLOW_PIN, INPUT_PULLUP);
  pinMode(RAIN_DO_PIN, INPUT);
  pinMode(BATTERY_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), onFlowPulse, FALLING);

  dht.begin();
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX2_PIN, GPS_TX2_PIN);

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Flood Node");
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

  float distance = readDistanceCm();
  float flow = readFlowLpm(READ_INTERVAL_MS);
  float rainPct = readRainPercent();
  float tempC = dht.readTemperature();
  float humidity = dht.readHumidity();
  float battV = readBatteryVoltage();
  bool haveFix = gps.location.isValid();
  
  // Real GPS if acquired, otherwise indoor fallback
  double lat = haveFix ? gps.location.lat() : DEFAULT_LAT;
  double lon = haveFix ? gps.location.lng() : DEFAULT_LON;

  // Evaluate alarm state
  int alarmLevel = 0;
  if (distance >= 0 && distance <= FLOOD_ALARM_CM) alarmLevel = 2;
  else if (distance >= 0 && distance <= FLOOD_WARN_CM) alarmLevel = 1;
  if (rainPct >= RAIN_ALARM_PCT) alarmLevel = 2;
  else if (rainPct >= RAIN_WARN_PCT && alarmLevel < 1) alarmLevel = 1;
  setAlarmOutputs(alarmLevel);

  // 1. ESP-NOW Broadcast to physical Receiver Node
  SensorPacket packet = {};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.node = NODE_ID;
  packet.sequence = ++sequenceNumber;
  packet.value[0] = distance;
  packet.value[1] = flow;
  packet.value[2] = rainPct;
  packet.value[3] = isnan(tempC) ? 0 : tempC;
  packet.value[4] = isnan(humidity) ? 0 : humidity;
  packet.value[8] = (float)lat;
  packet.value[9] = (float)lon;
  packet.value[10] = battV;
  packet.validMask = (distance >= 0 ? (1u << 0) : 0) | (1u << 1) | (1u << 2) |
                      (!isnan(tempC) ? (1u << 3) : 0) | (!isnan(humidity) ? (1u << 4) : 0) |
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

  Serial.printf("Node1 | Dist:%.1fcm Flow:%.2fL/m Rain:%.1f%% Fix:%d Sats:%d Chars:%lu | %s\n",
                distance, flow, rainPct, haveFix ? 1 : 0, sats, chars,
                result == ESP_OK ? "sent" : esp_err_to_name(result));

  // 2. HTTP POST Telemetry directly to Central Receiver Dashboard
  sendTelemetryToDashboard(distance, flow, rainPct, tempC, humidity, battV, lat, lon, alarmLevel);

  // 3. LCD Screen Cycling
  char line2[17];
  switch (displayIndex) {
    case 0: snprintf(line2, sizeof(line2), "Dist:%6.1fcm", distance); break;
    case 1: snprintf(line2, sizeof(line2), "Flow:%5.2fL/m", flow); break;
    case 2: snprintf(line2, sizeof(line2), "Rain:%5.1f%%", rainPct); break;
    case 3: snprintf(line2, sizeof(line2), "T:%4.1fC H:%4.1f%%", tempC, humidity); break;
    default: snprintf(line2, sizeof(line2), "Batt:%4.2fV", battV); break;
  }
  displayIndex = (displayIndex + 1) % 5;
  const char *alarmText = alarmLevel == 2 ? "ALARM" : (alarmLevel == 1 ? "WARN " : "CLEAR");
  lcd.setCursor(0, 0);
  lcd.printf("Flood: %s   ", alarmText);
  lcd.setCursor(0, 1);
  lcd.print(line2);
  lcd.print("                ");
}
