#include <Wire.h>
#include <U8g2lib.h>
#include <SparkFun_MAX1704x_Fuel_Gauge_Arduino_Library.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
SFE_MAX1704X fuelGauge(MAX1704X_MAX17043);

bool fuelGaugeConnected = false;
bool device51found = false;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();

  Serial.println("\n\n=== Battery Monitor Diagnostic ===");

  Serial.println("\nScanning I2C bus...");
  for (byte i = 8; i < 120; i++) {
    Wire.beginTransmission(i);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      if (i < 16) Serial.print("0");
      Serial.print(i, HEX);
      Serial.print(" (");
      Serial.print(i);
      Serial.println(")");

      if (i == 0x3C) Serial.println("  -> Expansion board OLED");
      if (i == 0x36) Serial.println("  -> MAX17043 Fuel Gauge");
      if (i == 0x72) Serial.println("  -> SerLCD Display");
      if (i == 0x51) {
        Serial.println("  -> Unknown device - investigating...");
        device51found = true;
      }
    }
  }

  Serial.println("\nInitializing expansion board OLED...");
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(0, 10, "Battery Monitor");
  u8g2.drawStr(0, 25, "Starting...");
  u8g2.sendBuffer();

  Serial.println("\nTrying fuel gauge at 0x36...");
  if (fuelGauge.begin() == false) {
    Serial.println("MAX17043 not detected!");
    Serial.println("Check:");
    Serial.println("  1. Qwiic cable connected?");
    Serial.println("  2. Battery connected?");
    Serial.println("  3. Fuel gauge powered?");
    fuelGaugeConnected = false;
  } else {
    Serial.println("MAX17043 found!");
    fuelGaugeConnected = true;
    fuelGauge.quickStart();
  }

  if (device51found) {
    Serial.println("\nDevice at 0x51 - trying to identify...");
    Wire.beginTransmission(0x51);
    Wire.write(0x00);
    byte error = Wire.endTransmission();
    Serial.print("Write test result: ");
    Serial.println(error);
  }

  delay(2000);
  Serial.println("\nSetup complete - entering main loop");
}

void loop() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);

  if (fuelGaugeConnected) {
    double voltage = fuelGauge.getVoltage();
    double soc = fuelGauge.getSOC();

    char voltStr[20];
    char socStr[20];
    sprintf(voltStr, "V: %.2fV", voltage);
    sprintf(socStr, "Batt: %.1f%%", soc);

    u8g2.drawStr(0, 10, "Battery Info");
    u8g2.drawStr(0, 30, voltStr);
    u8g2.drawStr(0, 45, socStr);

    Serial.print("Voltage: ");
    Serial.print(voltage, 2);
    Serial.print("V  SOC: ");
    Serial.print(soc, 1);
    Serial.println("%");
  } else {
    u8g2.drawStr(0, 10, "No Fuel Gauge");
    u8g2.drawStr(0, 30, "Check wiring:");
    u8g2.drawStr(0, 45, "0x36 not found");
  }

  u8g2.sendBuffer();
  delay(1000);
}
