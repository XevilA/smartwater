#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

// Pin Definitions
#define LED1  2    // GPIO2 สำหรับ LED1 (Solenoid1 - น้ำ)
#define LED2  4    // GPIO4 สำหรับ LED2 (Solenoid2 - ปุ๋ย)
#define PUMP  5    // GPIO5 สำหรับปั๊มน้ำ

// WiFi Settings
const char* ap_ssid = "ESP32_Irrigation";
const char* ap_password = "12345678";

// Stored WiFi credentials
char stored_ssid[32] = "";
char stored_password[64] = "";
bool wifi_configured = false;

// Web Server
WebServer server(80);
WiFiServer tcpServer(80);

// Preferences for storing settings
Preferences preferences;

// System State
bool isWatering = false;
bool waterMode = false;
bool fertilizerMode = false;
unsigned long wateringStartTime = 0;
unsigned long wateringDuration = 0;

// Serial command buffer
String inputString = "";

void setup() {
  Serial.begin(9600);
  Serial.println("ESP32 Smart Irrigation System Starting...");
  
  // Initialize pins
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(PUMP, OUTPUT);
  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(PUMP, LOW);
  
  // Load saved WiFi settings
  loadWiFiSettings();
  
  // Setup WiFi
  setupWiFi();
  
  // Setup Web Server
  setupWebServer();
  
  // Start TCP Server for socket connections
  tcpServer.begin();
  
  Serial.println("System Ready!");
  Serial.print("IP Address: ");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(WiFi.localIP());
  } else {
    Serial.print("AP Mode - ");
    Serial.println(WiFi.softAPIP());
  }
}

void loop() {
  // Handle Serial Commands
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      handleCommand(inputString);
      inputString = "";
    } else {
      inputString += inChar;
    }
  }
  
  // Handle Web Server
  server.handleClient();
  
  // Handle TCP Socket connections
  handleTCPClients();
  
  // Auto stop if duration exceeded
  if (isWatering && wateringDuration > 0) {
    if (millis() - wateringStartTime > wateringDuration) {
      stopAll();
      Serial.println("Auto stop - duration reached");
    }
  }
  
  delay(10);
}

void setupWiFi() {
  // Try to connect to saved WiFi first
  if (wifi_configured && strlen(stored_ssid) > 0) {
    Serial.print("Connecting to WiFi: ");
    Serial.println(stored_ssid);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(stored_ssid, stored_password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi Connected!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
      return;
    }
  }
  
  // If connection failed or no saved credentials, start AP mode
  Serial.println("\nStarting Access Point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);
  
  Serial.print("AP IP Address: ");
  Serial.println(WiFi.softAPIP());
  Serial.print("SSID: ");
  Serial.println(ap_ssid);
}

void setupWebServer() {
  // Root page
  server.on("/", HTTP_GET, handleRoot);
  
  // WiFi configuration
  server.on("/wifi", HTTP_POST, handleWiFiConfig);
  
  // Control endpoints
  server.on("/control", HTTP_GET, handleControl);
  
  // Status endpoint
  server.on("/status", HTTP_GET, handleStatus);
  
  server.begin();
  Serial.println("Web server started");
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<title>ESP32 Irrigation Control</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial; margin: 20px; background: #f0f0f0; }";
  html += ".container { max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }";
  html += "h1 { color: #333; text-align: center; }";
  html += ".status { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 10px 0; }";
  html += ".button { background: #4CAF50; color: white; padding: 12px 20px; border: none; border-radius: 5px; font-size: 16px; margin: 5px; cursor: pointer; }";
  html += ".button:hover { background: #45a049; }";
  html += ".button.stop { background: #f44336; }";
  html += ".button.stop:hover { background: #da190b; }";
  html += ".form-group { margin: 15px 0; }";
  html += "input[type='text'], input[type='password'] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }";
  html += "label { display: block; margin-bottom: 5px; font-weight: bold; }";
  html += "</style>";
  html += "<script>";
  html += "function sendCommand(cmd) {";
  html += "  fetch('/control?cmd=' + cmd)";
  html += "    .then(response => response.text())";
  html += "    .then(data => { alert(data); location.reload(); });";
  html += "}";
  html += "</script>";
  html += "</head><body>";
  html += "<div class='container'>";
  html += "<h1>🌱 ESP32 Smart Irrigation</h1>";
  
  // System Status
  html += "<div class='status'>";
  html += "<h2>System Status</h2>";
  html += "<p><strong>Water Valve (LED1):</strong> " + String(digitalRead(LED1) ? "ON" : "OFF") + "</p>";
  html += "<p><strong>Fertilizer Valve (LED2):</strong> " + String(digitalRead(LED2) ? "ON" : "OFF") + "</p>";
  html += "<p><strong>Pump:</strong> " + String(digitalRead(PUMP) ? "ON" : "OFF") + "</p>";
  html += "<p><strong>Mode:</strong> ";
  if (isWatering) {
    html += waterMode ? "Water Only" : "Water + Fertilizer";
  } else {
    html += "Idle";
  }
  html += "</p>";
  html += "</div>";
  
  // Control Buttons
  html += "<h2>Manual Control</h2>";
  html += "<div style='text-align: center;'>";
  html += "<button class='button' onclick=\"sendCommand('LED1_ON')\">💧 Water Only</button>";
  html += "<button class='button' onclick=\"sendCommand('LED2_ON')\">🌱 Water + Fertilizer</button>";
  html += "<button class='button stop' onclick=\"sendCommand('STOP')\">⏹️ Stop All</button>";
  html += "</div>";
  
  // WiFi Configuration
  html += "<h2>WiFi Settings</h2>";
  html += "<form action='/wifi' method='POST'>";
  html += "<div class='form-group'>";
  html += "<label>Network Name (SSID):</label>";
  html += "<input type='text' name='ssid' placeholder='Your WiFi network'>";
  html += "</div>";
  html += "<div class='form-group'>";
  html += "<label>Password:</label>";
  html += "<input type='password' name='password' placeholder='WiFi password'>";
  html += "</div>";
  html += "<button type='submit' class='button'>Save & Restart</button>";
  html += "</form>";
  
  // Current WiFi Status
  html += "<div class='status'>";
  if (WiFi.status() == WL_CONNECTED) {
    html += "<p><strong>Connected to:</strong> " + WiFi.SSID() + "</p>";
    html += "<p><strong>IP Address:</strong> " + WiFi.localIP().toString() + "</p>";
  } else {
    html += "<p><strong>Mode:</strong> Access Point</p>";
    html += "<p><strong>AP IP:</strong> " + WiFi.softAPIP().toString() + "</p>";
  }
  html += "</div>";
  
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

void handleWiFiConfig() {
  String new_ssid = server.arg("ssid");
  String new_password = server.arg("password");
  
  if (new_ssid.length() > 0) {
    // Save to preferences
    new_ssid.toCharArray(stored_ssid, 32);
    new_password.toCharArray(stored_password, 64);
    wifi_configured = true;
    
    saveWiFiSettings();
    
    String response = "<html><body><h1>WiFi Settings Saved!</h1>";
    response += "<p>The device will restart and connect to: " + new_ssid + "</p>";
    response += "<p>Please wait 10 seconds and reconnect.</p>";
    response += "</body></html>";
    
    server.send(200, "text/html", response);
    
    delay(2000);
    ESP.restart();
  } else {
    server.send(400, "text/plain", "Invalid SSID");
  }
}

void handleControl() {
  String cmd = server.arg("cmd");
  
  if (cmd.length() > 0) {
    handleCommand(cmd);
    server.send(200, "text/plain", "Command executed: " + cmd);
  } else {
    server.send(400, "text/plain", "No command specified");
  }
}

void handleStatus() {
  String status = "{";
  status += "\"led1\":" + String(digitalRead(LED1) ? "true" : "false") + ",";
  status += "\"led2\":" + String(digitalRead(LED2) ? "true" : "false") + ",";
  status += "\"pump\":" + String(digitalRead(PUMP) ? "true" : "false") + ",";
  status += "\"isWatering\":" + String(isWatering ? "true" : "false") + ",";
  status += "\"mode\":\"" + String(waterMode ? "water" : (fertilizerMode ? "fertilizer" : "idle")) + "\"";
  status += "}";
  
  server.send(200, "application/json", status);
}

void handleTCPClients() {
  WiFiClient client = tcpServer.available();
  
  if (client) {
    Serial.println("New TCP client connected");
    
    while (client.connected()) {
      if (client.available()) {
        String command = client.readStringUntil('\n');
        command.trim();
        
        if (command.length() > 0) {
          Serial.print("TCP Command: ");
          Serial.println(command);
          
          handleCommand(command);
          
          // Send response
          client.println("OK");
        }
      }
      
      // Small delay to prevent CPU hogging
      delay(10);
    }
    
    Serial.println("TCP client disconnected");
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  Serial.print("Executing command: ");
  Serial.println(cmd);
  
  if (cmd == "LED1_ON") {
    // Water mode - turn on water valve and pump
    digitalWrite(LED1, HIGH);
    digitalWrite(PUMP, HIGH);
    isWatering = true;
    waterMode = true;
    fertilizerMode = false;
    wateringStartTime = millis();
    Serial.println("Water mode ON");
    
  } else if (cmd == "LED2_ON") {
    // Fertilizer mode - turn on both valves and pump
    digitalWrite(LED1, HIGH);
    digitalWrite(LED2, HIGH);
    digitalWrite(PUMP, HIGH);
    isWatering = true;
    waterMode = false;
    fertilizerMode = true;
    wateringStartTime = millis();
    Serial.println("Fertilizer mode ON");
    
  } else if (cmd == "LED1_OFF") {
    digitalWrite(LED1, LOW);
    // If LED2 is also off, turn off pump
    if (digitalRead(LED2) == LOW) {
      digitalWrite(PUMP, LOW);
      isWatering = false;
    }
    Serial.println("Water valve OFF");
    
  } else if (cmd == "LED2_OFF") {
    digitalWrite(LED2, LOW);
    // If LED1 is also off, turn off pump
    if (digitalRead(LED1) == LOW) {
      digitalWrite(PUMP, LOW);
      isWatering = false;
    }
    Serial.println("Fertilizer valve OFF");
    
  } else if (cmd == "LED_OFF" || cmd == "STOP") {
    stopAll();
    
  } else if (cmd.startsWith("DURATION:")) {
    // Set watering duration (in seconds)
    wateringDuration = cmd.substring(9).toInt() * 1000;
    Serial.print("Duration set to: ");
    Serial.print(wateringDuration / 1000);
    Serial.println(" seconds");
    
  } else if (cmd == "STATUS") {
    // Send status
    String status = "LED1:" + String(digitalRead(LED1)) + 
                   ",LED2:" + String(digitalRead(LED2)) + 
                   ",PUMP:" + String(digitalRead(PUMP));
    Serial.println(status);
  }
}

void stopAll() {
  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(PUMP, LOW);
  isWatering = false;
  waterMode = false;
  fertilizerMode = false;
  wateringDuration = 0;
  Serial.println("All systems OFF");
}

void saveWiFiSettings() {
  preferences.begin("irrigation", false);
  preferences.putString("ssid", stored_ssid);
  preferences.putString("password", stored_password);
  preferences.putBool("configured", wifi_configured);
  preferences.end();
  
  Serial.println("WiFi settings saved to flash");
}

void loadWiFiSettings() {
  preferences.begin("irrigation", true);
  
  if (preferences.getBool("configured", false)) {
    String ssid = preferences.getString("ssid", "");
    String password = preferences.getString("password", "");
    
    ssid.toCharArray(stored_ssid, 32);
    password.toCharArray(stored_password, 64);
    wifi_configured = true;
    
    Serial.println("WiFi settings loaded from flash");
  }
  
  preferences.end();
}
