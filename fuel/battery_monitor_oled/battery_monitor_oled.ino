#include <Wire.h>
#include <U8g2lib.h>
#include <SparkFun_MAX1704x_Fuel_Gauge_Arduino_Library.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
SFE_MAX1704X fuelGauge(MAX1704X_MAX17043);

bool fuelGaugeConnected = false;
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 1000;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Wire.begin();

  Serial.println("\n=== Battery Monitor v2.0 ===");

  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.drawStr(0, 12, "Battery Monitor");
  u8g2.drawStr(0, 28, "Initializing...");
  u8g2.sendBuffer();

  delay(1000);

  Serial.println("Checking for fuel gauge at 0x36...");
  if (fuelGauge.begin() == false) {
    Serial.println("Fuel gauge not found!");
    Serial.println("Battery info unavailable");
    fuelGaugeConnected = false;
  } else {
    Serial.println("Fuel gauge connected!");
    fuelGaugeConnected = true;
    fuelGauge.quickStart();
  }

  delay(500);
  Serial.println("Setup complete\n");
}

void loop() {
  if (millis() - lastUpdate >= UPDATE_INTERVAL) {
    lastUpdate = millis();

    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);

    if (fuelGaugeConnected) {
      double voltage = fuelGauge.getVoltage();
      double soc = fuelGauge.getSOC();

      char voltStr[20];
      char socStr[20];
      sprintf(voltStr, "Voltage: %.2fV", voltage);
      sprintf(socStr, "Battery: %.1f%%", soc);

      u8g2.drawStr(0, 12, "Battery Status");
      u8g2.drawLine(0, 15, 127, 15);
      u8g2.drawStr(0, 32, voltStr);
      u8g2.drawStr(0, 48, socStr);

      int barWidth = (int)((soc / 100.0) * 110);
      u8g2.drawFrame(0, 52, 112, 10);
      u8g2.drawBox(2, 54, barWidth, 6);

      Serial.print("V: ");
      Serial.print(voltage, 2);
      Serial.print("V  SOC: ");
      Serial.print(soc, 1);
      Serial.println("%");

    } else {
      u8g2.drawStr(0, 12, "Fuel Gauge Error");
      u8g2.drawLine(0, 15, 127, 15);
      u8g2.setFont(u8g2_font_6x10_tr);
      u8g2.drawStr(0, 28, "Not detected at 0x36");
      u8g2.drawStr(0, 40, "Check:");
      u8g2.drawStr(0, 50, "- Qwiic connection");
      u8g2.drawStr(0, 60, "- Battery plugged in");

      Serial.println("Fuel gauge not detected");
    }

    u8g2.sendBuffer();
  }
}
