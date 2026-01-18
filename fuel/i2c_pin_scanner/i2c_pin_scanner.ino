#include <Wire.h>

// Test different pin combinations for XIAO ESP32-C3
const int pinPairs[][2] = {
  {4, 5},   // Common for XIAO
  {5, 6},   // Another common config
  {6, 7},   // Current attempt
  {21, 22}, // ESP32 default
};

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== XIAO ESP32-C3 I2C Pin Scanner ===\n");

  for (int i = 0; i < 4; i++) {
    int sda = pinPairs[i][0];
    int scl = pinPairs[i][1];

    Serial.print("Testing SDA=GPIO");
    Serial.print(sda);
    Serial.print(", SCL=GPIO");
    Serial.print(scl);
    Serial.println("...");

    Wire.begin(sda, scl);
    delay(100);

    int found = 0;
    for (byte addr = 8; addr < 120; addr++) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        Serial.print("  Found device at 0x");
        if (addr < 16) Serial.print("0");
        Serial.print(addr, HEX);

        if (addr == 0x36) Serial.print(" <- MAX17043");
        else if (addr == 0x3C) Serial.print(" <- OLED");
        Serial.println();
        found++;
      }
    }

    if (found == 0) {
      Serial.println("  No devices found");
    } else {
      Serial.print("  Total: ");
      Serial.print(found);
      Serial.println(" devices");
    }

    Wire.end();
    Serial.println();
    delay(500);
  }

  Serial.println("Scan complete!");
  Serial.println("Use the pin pair that found devices.");
}

void loop() {
  delay(10000);
}
