#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();

  delay(2000);
  Serial.println("\nI2C Scanner");
  Serial.println("Scanning...");

  byte count = 0;

  for (byte i = 8; i < 120; i++) {
    Wire.beginTransmission(i);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found address: 0x");
      if (i < 16) Serial.print("0");
      Serial.print(i, HEX);
      Serial.print(" (");
      Serial.print(i);
      Serial.println(")");

      if (i == 0x36) Serial.println("  -> MAX17043 Fuel Gauge");
      if (i == 0x72) Serial.println("  -> SerLCD Display");

      count++;
      delay(1);
    }
  }

  Serial.print("\nFound ");
  Serial.print(count);
  Serial.println(" device(s)");
}

void loop() {
  delay(5000);
}
