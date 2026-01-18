#include <Wire.h>
#include <SparkFun_MAX1704x_Fuel_Gauge_Arduino_Library.h>
#include <SerLCD.h>

SFE_MAX1704X fuelGauge(MAX1704X_MAX17043);
SerLCD lcd;

const unsigned long UPDATE_INTERVAL = 1000;
unsigned long lastUpdate = 0;
bool fuelGaugeConnected = false;

void scanI2C() {
  Serial.println("\nScanning I2C bus...");
  byte count = 0;
  for (byte i = 8; i < 120; i++) {
    Wire.beginTransmission(i);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      if (i < 16) Serial.print("0");
      Serial.println(i, HEX);
      count++;
    }
  }
  Serial.print("Total devices: ");
  Serial.println(count);
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();

  Serial.println("Battery Monitor Starting...");

  scanI2C();

  Serial.println("\nTrying fuel gauge at 0x36...");
  if (fuelGauge.begin() == false) {
    Serial.println("MAX17043 not detected - will skip battery readings");
    fuelGaugeConnected = false;
  } else {
    Serial.println("MAX17043 connected!");
    fuelGaugeConnected = true;
    fuelGauge.quickStart();
  }

  Serial.println("\nInitializing LCD...");
  lcd.begin(Wire);
  delay(100);

  Serial.println("Setting backlight...");
  lcd.setBacklight(255, 255, 255);
  delay(100);

  Serial.println("Clearing display...");
  lcd.clear();
  delay(100);

  Serial.println("Writing to display...");
  lcd.setCursor(0, 0);
  lcd.print("I2C Test");
  lcd.setCursor(0, 1);
  lcd.print("LCD Works!");

  delay(3000);
  lcd.clear();

  Serial.println("Setup complete");
}

void loop() {
  if (millis() - lastUpdate >= UPDATE_INTERVAL) {
    lastUpdate = millis();

    if (fuelGaugeConnected) {
      double voltage = fuelGauge.getVoltage();
      double soc = fuelGauge.getSOC();

      Serial.print("Voltage: ");
      Serial.print(voltage, 2);
      Serial.print("V  SOC: ");
      Serial.print(soc, 1);
      Serial.println("%");

      lcd.setCursor(0, 0);
      lcd.print("V: ");
      lcd.print(voltage, 2);
      lcd.print("V    ");

      lcd.setCursor(0, 1);
      lcd.print("Batt: ");
      lcd.print(soc, 1);
      lcd.print("%    ");

      if (soc < 20.0) {
        lcd.setBacklight(255, 0, 0);
      } else if (soc < 50.0) {
        lcd.setBacklight(255, 128, 0);
      } else {
        lcd.setBacklight(0, 255, 0);
      }
    } else {
      lcd.setCursor(0, 0);
      lcd.print("No Fuel Gauge");
      lcd.setCursor(0, 1);
      lcd.print("Check wiring");
    }
  }
}
