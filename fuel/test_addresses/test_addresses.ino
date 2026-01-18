#include <Wire.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();
  u8g2.begin();

  Serial.println("\n=== Testing Device at 0x51 ===");

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tr);
  u8g2.drawStr(0, 10, "Testing 0x51...");
  u8g2.sendBuffer();

  // Try to read from 0x51
  Serial.println("\nAttempting to read from 0x51:");

  // Read 16 bytes from 0x51
  Wire.beginTransmission(0x51);
  Wire.endTransmission();

  Wire.requestFrom(0x51, 16);

  Serial.print("Received bytes: ");
  byte bytesRead = 0;
  while (Wire.available()) {
    byte b = Wire.read();
    Serial.print("0x");
    if (b < 16) Serial.print("0");
    Serial.print(b, HEX);
    Serial.print(" ");
    bytesRead++;
  }
  Serial.println();
  Serial.print("Total bytes read: ");
  Serial.println(bytesRead);

  // Try reading register 0x02 (Voltage for MAX17043)
  Serial.println("\nTrying to read register 0x02 from 0x51:");
  Wire.beginTransmission(0x51);
  Wire.write(0x02);
  byte error = Wire.endTransmission();
  Serial.print("Write result: ");
  Serial.println(error);

  if (error == 0) {
    Wire.requestFrom(0x51, 2);
    if (Wire.available() >= 2) {
      byte msb = Wire.read();
      byte lsb = Wire.read();
      Serial.print("Register 0x02: 0x");
      if (msb < 16) Serial.print("0");
      Serial.print(msb, HEX);
      if (lsb < 16) Serial.print("0");
      Serial.println(lsb, HEX);

      // Calculate voltage if this is MAX17043
      uint16_t raw = (msb << 8) | lsb;
      float voltage = (raw >> 4) * 0.00125;
      Serial.print("If this is MAX17043, voltage would be: ");
      Serial.print(voltage, 3);
      Serial.println("V");
    }
  }

  // Try reading register 0x04 (SOC for MAX17043)
  Serial.println("\nTrying to read register 0x04 from 0x51:");
  Wire.beginTransmission(0x51);
  Wire.write(0x04);
  error = Wire.endTransmission();
  Serial.print("Write result: ");
  Serial.println(error);

  if (error == 0) {
    Wire.requestFrom(0x51, 2);
    if (Wire.available() >= 2) {
      byte msb = Wire.read();
      byte lsb = Wire.read();
      Serial.print("Register 0x04: 0x");
      if (msb < 16) Serial.print("0");
      Serial.print(msb, HEX);
      if (lsb < 16) Serial.print("0");
      Serial.println(lsb, HEX);

      // Calculate SOC if this is MAX17043
      uint16_t raw = (msb << 8) | lsb;
      float soc = (raw >> 8) + (float)(lsb) / 256.0;
      Serial.print("If this is MAX17043, SOC would be: ");
      Serial.print(soc, 2);
      Serial.println("%");
    }
  }

  u8g2.clearBuffer();
  u8g2.drawStr(0, 10, "Test complete");
  u8g2.drawStr(0, 25, "Check serial");
  u8g2.drawStr(0, 40, "monitor for");
  u8g2.drawStr(0, 55, "results");
  u8g2.sendBuffer();

  Serial.println("\n=== Test Complete ===");
  Serial.println("Check results above to see if 0x51 responds like a fuel gauge");
}

void loop() {
  delay(5000);
}
