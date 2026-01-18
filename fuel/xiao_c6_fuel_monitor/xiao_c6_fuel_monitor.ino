#include <Wire.h>
#include <U8g2lib.h>
#include <SparkFun_MAX1704x_Fuel_Gauge_Arduino_Library.h>

// XIAO ESP32-C3: D4=GPIO6(SDA), D5=GPIO7(SCL)
#define I2C_SDA D4
#define I2C_SCL D5

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, I2C_SCL, I2C_SDA);
SFE_MAX1704X fuelGauge(MAX1704X_MAX17043);

bool fuelGaugeConnected = false;
bool oledConnected = false;
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 1000;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  Serial.println("\n=== XIAO ESP32-C3 Battery Monitor v2.0 ===");
  Serial.print("I2C initialized: D4/D5 (GPIO");
  Serial.print(I2C_SDA);
  Serial.print("/GPIO");
  Serial.print(I2C_SCL);
  Serial.println(")");
  Serial.println();

  Serial.println("Initializing OLED...");
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(0, 12, "XIAO C3 Battery");
  u8g2.drawStr(0, 28, "Initializing...");
  u8g2.sendBuffer();
  oledConnected = true;
  Serial.println("OLED initialized!");
  Serial.println();

  delay(1000);

  Serial.println("Checking for fuel gauge...");
  if (fuelGauge.begin() == false) {
    Serial.println("Fuel gauge not found at 0x36");
    fuelGaugeConnected = false;

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(0, 12, "No Fuel Gauge");
    u8g2.drawStr(0, 30, "Check:");
    u8g2.setFont(u8g2_font_6x10_tr);
    u8g2.drawStr(0, 45, "- Grove cable");
    u8g2.drawStr(0, 57, "- Battery");
    u8g2.sendBuffer();
  } else {
    Serial.println("Fuel gauge connected!");
    fuelGaugeConnected = true;
    fuelGauge.quickStart();
    delay(500);
  }

  Serial.println("\nSetup complete!");
  Serial.print("OLED: YES | Fuel Gauge: ");
  Serial.println(fuelGaugeConnected ? "YES" : "NO");
  Serial.println();
}

void scanI2C() {
  byte count = 0;
  Serial.println("Scanning I2C addresses (0x08-0x77):");
  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Device at 0x");
      if (addr < 16) Serial.print("0");
      Serial.print(addr, HEX);

      if (addr == 0x36) Serial.print(" <- MAX17043 Fuel Gauge");
      else if (addr == 0x3C) Serial.print(" <- SSD1306 OLED");
      else if (addr == 0x3D) Serial.print(" <- SSD1306 OLED (Alt)");
      else if (addr == 0x08) Serial.print(" <- Unknown device");
      Serial.println();
      count++;
    }
  }
  Serial.print("Total devices found: ");
  Serial.println(count);
}

void loop() {
  if (millis() - lastUpdate >= UPDATE_INTERVAL) {
    lastUpdate = millis();

    if (oledConnected) {
      u8g2.clearBuffer();
      u8g2.setFont(u8g2_font_ncenB08_tr);
    }

    if (fuelGaugeConnected) {
      double voltage = fuelGauge.getVoltage();
      double soc = fuelGauge.getSOC();

      char voltStr[20];
      char socStr[20];
      sprintf(voltStr, "%.2fV", voltage);
      sprintf(socStr, "%.1f%%", soc);

      u8g2.drawStr(0, 10, "Battery Status");
      u8g2.drawLine(0, 12, 127, 12);

      u8g2.setFont(u8g2_font_ncenB10_tr);
      u8g2.drawStr(0, 30, voltStr);

      u8g2.setFont(u8g2_font_ncenB14_tr);
      int socX = 64 - (strlen(socStr) * 7);
      u8g2.drawStr(socX, 50, socStr);

      int barWidth = (int)((soc / 100.0) * 120);
      u8g2.drawFrame(0, 54, 124, 10);
      if (barWidth > 0) {
        u8g2.drawBox(2, 56, barWidth, 6);
      }

      Serial.print("Voltage: ");
      Serial.print(voltage, 2);
      Serial.print("V  |  SOC: ");
      Serial.print(soc, 1);
      Serial.println("%");

    } else {
      if (oledConnected) {
        u8g2.setFont(u8g2_font_ncenB08_tr);
        u8g2.drawStr(0, 10, "Fuel Gauge Error");
        u8g2.drawLine(0, 12, 127, 12);

        u8g2.setFont(u8g2_font_6x10_tr);
        u8g2.drawStr(0, 26, "Not found at 0x36");
        u8g2.drawStr(0, 38, "Check connections:");
        u8g2.drawStr(0, 48, "- Grove cable");
        u8g2.drawStr(0, 58, "- Battery plugged in");
      }

      Serial.println("ERROR: Fuel gauge not detected");
    }

    if (oledConnected) {
      u8g2.sendBuffer();
    }
  }
}
