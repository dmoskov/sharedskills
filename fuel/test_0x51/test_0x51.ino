#include <Wire.h>
#include <U8g2lib.h>
#include <SerLCD.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
SerLCD lcd;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();

  Serial.println("\n\n=== Testing 0x51 as SerLCD ===");

  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tr);
  u8g2.drawStr(0, 10, "Testing 0x51...");
  u8g2.sendBuffer();

  Serial.println("Setting LCD address to 0x51...");
  lcd.begin(Wire);
  lcd.setAddress(0x51);

  delay(500);

  Serial.println("Clearing LCD...");
  lcd.clear();
  delay(200);

  Serial.println("Setting backlight to white...");
  lcd.setBacklight(255, 255, 255);
  delay(200);

  Serial.println("Writing test message...");
  lcd.setCursor(0, 0);
  lcd.print("Test at 0x51");
  lcd.setCursor(0, 1);
  lcd.print("Does this work?");

  Serial.println("Done! Check SerLCD display");

  u8g2.clearBuffer();
  u8g2.drawStr(0, 10, "Sent to 0x51:");
  u8g2.drawStr(0, 25, "Test at 0x51");
  u8g2.drawStr(0, 40, "Does this work?");
  u8g2.sendBuffer();

  delay(3000);

  Serial.println("\nNow testing standard 0x72 address...");
  lcd.setAddress(0x72);
  delay(200);
  lcd.clear();
  lcd.print("Test at 0x72");

  Serial.println("Check both addresses tested");
}

void loop() {
  delay(5000);
}
