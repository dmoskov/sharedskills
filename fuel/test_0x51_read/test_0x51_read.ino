#include <Wire.h>

#define I2C_SDA D4
#define I2C_SCL D5

void setup() {
  Serial.begin(115200);
  delay(2000);

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  Serial.println("\n=== Testing Device at 0x51 ===\n");

  // Try reading some registers
  Serial.println("Reading first 16 bytes from 0x51:");
  for (int reg = 0; reg < 16; reg++) {
    Wire.beginTransmission(0x51);
    Wire.write(reg);
    byte error = Wire.endTransmission(false);

    if (error == 0) {
      Wire.requestFrom(0x51, 1);
      if (Wire.available()) {
        byte val = Wire.read();
        Serial.print("Reg 0x");
        if (reg < 16) Serial.print("0");
        Serial.print(reg, HEX);
        Serial.print(": 0x");
        if (val < 16) Serial.print("0");
        Serial.print(val, HEX);
        Serial.print(" (");
        Serial.print(val);
        Serial.println(")");
      }
    }
    delay(50);
  }

  Serial.println("\nAttempting to read voltage/SOC registers:");

  // Try MAX17043 registers at address 0x51
  Wire.beginTransmission(0x51);
  Wire.write(0x02); // VCELL register
  if (Wire.endTransmission(false) == 0) {
    Wire.requestFrom(0x51, 2);
    if (Wire.available() >= 2) {
      byte msb = Wire.read();
      byte lsb = Wire.read();
      uint16_t vcell = (msb << 8) | lsb;
      float voltage = vcell * 1.25 / 1000.0;
      Serial.print("VCELL (0x02): ");
      Serial.print(voltage, 3);
      Serial.println("V");
    }
  }

  Wire.beginTransmission(0x51);
  Wire.write(0x04); // SOC register
  if (Wire.endTransmission(false) == 0) {
    Wire.requestFrom(0x51, 2);
    if (Wire.available() >= 2) {
      byte msb = Wire.read();
      byte lsb = Wire.read();
      float soc = msb + (lsb / 256.0);
      Serial.print("SOC (0x04): ");
      Serial.print(soc, 1);
      Serial.println("%");
    }
  }

  Serial.println("\nTest complete!");
}

void loop() {
  delay(10000);
}
