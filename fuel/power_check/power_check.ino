#include <Wire.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

void scanI2C() {
  Serial.println("\n--- I2C Scan ---");
  byte count = 0;
  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("0x");
      if (addr < 16) Serial.print("0");
      Serial.print(addr, HEX);
      if (addr == 0x36) Serial.println(" <- Fuel Gauge FOUND!");
      else if (addr == 0x3C) Serial.println(" <- OLED");
      else Serial.println();
      count++;
    }
  }
  Serial.print("Total: ");
  Serial.print(count);
  Serial.println(" devices\n");
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();

  u8g2.begin();

  Serial.println("\n=== Fuel Gauge Power Diagnostic ===");
  Serial.println("This will scan I2C every 2 seconds");
  Serial.println("Watch for 0x36 to appear...");
  Serial.println("");
  Serial.println("Troubleshooting steps:");
  Serial.println("1. Make sure battery is connected to fuel gauge");
  Serial.println("2. Battery should be 3.0V - 4.2V (LiPo)");
  Serial.println("3. Check Qwiic cable is firmly seated");
  Serial.println("4. Try unplugging and replugging while watching\n");
}

int scanCount = 0;

void loop() {
  scanCount++;

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tr);

  char line[25];
  sprintf(line, "Scan #%d", scanCount);
  u8g2.drawStr(0, 10, line);
  u8g2.drawLine(0, 12, 127, 12);

  Serial.print("Scan #");
  Serial.println(scanCount);

  byte foundDevices[10];
  int deviceCount = 0;
  bool fuelGaugeFound = false;

  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (deviceCount < 10) {
        foundDevices[deviceCount++] = addr;
      }
      if (addr == 0x36) {
        fuelGaugeFound = true;
      }

      Serial.print("  0x");
      if (addr < 16) Serial.print("0");
      Serial.print(addr, HEX);
      if (addr == 0x36) Serial.println(" <- FUEL GAUGE!");
      else if (addr == 0x3C) Serial.println(" <- OLED");
      else Serial.println();
    }
  }

  if (deviceCount == 0) {
    u8g2.drawStr(0, 25, "No devices found!");
    Serial.println("  No devices found");
  } else {
    sprintf(line, "Found: %d device(s)", deviceCount);
    u8g2.drawStr(0, 25, line);
    Serial.print("  Total: ");
    Serial.println(deviceCount);

    int y = 35;
    for (int i = 0; i < deviceCount && i < 3; i++) {
      sprintf(line, "0x%02X", foundDevices[i]);
      u8g2.drawStr(0, y, line);

      if (foundDevices[i] == 0x36) {
        u8g2.drawStr(35, y, "FUEL GAUGE!");
      } else if (foundDevices[i] == 0x3C) {
        u8g2.drawStr(35, y, "OLED");
      }
      y += 10;
    }
  }

  if (fuelGaugeFound) {
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(0, 60, "SUCCESS!");
    Serial.println("\n*** FUEL GAUGE DETECTED! ***\n");
  } else {
    u8g2.setFont(u8g2_font_6x10_tr);
    u8g2.drawStr(0, 60, "No 0x36 yet...");
  }

  u8g2.sendBuffer();
  Serial.println();

  delay(2000);
}
