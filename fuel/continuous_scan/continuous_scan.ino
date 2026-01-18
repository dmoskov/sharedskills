#include <Wire.h>
#include <U8g2lib.h>

#define I2C_SDA D4
#define I2C_SCL D5

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, I2C_SCL, I2C_SDA);

void setup() {
  Serial.begin(115200);
  delay(2000);

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  u8g2.begin();

  Serial.println("\n=== Continuous I2C Scanner ===");
  Serial.println("Scanning every 2 seconds...");
  Serial.println("Looking for fuel gauge at 0x36\n");
}

void loop() {
  byte devices[10];
  byte count = 0;
  bool foundFuelGauge = false;

  // Scan I2C bus
  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (count < 10) {
        devices[count++] = addr;
      }
      if (addr == 0x36) {
        foundFuelGauge = true;
      }
    }
  }

  // Display on OLED
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);

  if (foundFuelGauge) {
    u8g2.drawStr(0, 12, "FUEL GAUGE FOUND!");
    u8g2.drawStr(0, 30, "at 0x36");
  } else {
    u8g2.drawStr(0, 12, "Searching...");

    char buf[20];
    sprintf(buf, "Found: %d devices", count);
    u8g2.setFont(u8g2_font_6x10_tr);
    u8g2.drawStr(0, 30, buf);

    int y = 40;
    for (int i = 0; i < count && i < 3; i++) {
      sprintf(buf, "0x%02X", devices[i]);
      u8g2.drawStr(0, y, buf);
      y += 10;
    }
  }
  u8g2.sendBuffer();

  // Serial output
  Serial.print("Scan: ");
  for (int i = 0; i < count; i++) {
    Serial.print("0x");
    if (devices[i] < 16) Serial.print("0");
    Serial.print(devices[i], HEX);
    if (devices[i] == 0x36) Serial.print("(FUEL GAUGE!)");
    Serial.print(" ");
  }

  if (count == 0) {
    Serial.print("No devices found");
  }

  Serial.println();

  delay(2000);
}
