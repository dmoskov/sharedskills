#include <Wire.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

byte foundDevices[10];
int deviceCount = 0;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();

  Serial.println("\n\n=== I2C Device Scanner ===");

  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tr);
  u8g2.drawStr(0, 10, "Scanning I2C...");
  u8g2.sendBuffer();

  delay(1000);

  Serial.println("Scanning...");
  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("0x");
      if (addr < 16) Serial.print("0");
      Serial.print(addr, HEX);

      if (addr == 0x36) Serial.println(" <- Fuel Gauge");
      else if (addr == 0x72) Serial.println(" <- SerLCD");
      else if (addr == 0x3C) Serial.println(" <- OLED");
      else Serial.println();

      if (deviceCount < 10) {
        foundDevices[deviceCount++] = addr;
      }
    }
  }

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tr);

  char line[20];
  sprintf(line, "Found: %d devices", deviceCount);
  u8g2.drawStr(0, 10, line);

  int y = 20;
  for (int i = 0; i < deviceCount && i < 5; i++) {
    sprintf(line, "0x%02X", foundDevices[i]);
    u8g2.drawStr(0, y, line);

    if (foundDevices[i] == 0x36) {
      u8g2.drawStr(40, y, "Fuel Gauge");
    } else if (foundDevices[i] == 0x72) {
      u8g2.drawStr(40, y, "SerLCD");
    } else if (foundDevices[i] == 0x3C) {
      u8g2.drawStr(40, y, "OLED");
    } else if (foundDevices[i] == 0x51) {
      u8g2.drawStr(40, y, "Unknown");
    }

    y += 10;
  }

  u8g2.sendBuffer();

  Serial.println("\nScan complete!");
  Serial.print("Total devices found: ");
  Serial.println(deviceCount);
}

void loop() {
  delay(5000);
}
