#include <U8g2lib.h>
#include <Wire.h>

// XIAO ESP32-C3: D4=GPIO6(SDA), D5=GPIO7(SCL)
#define I2C_SDA D4
#define I2C_SCL D5

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, I2C_SCL, I2C_SDA);

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== XIAO Expansion Board OLED Test v2 ===\n");
  Serial.print("Using I2C pins: D4 (GPIO");
  Serial.print(I2C_SDA);
  Serial.print("), D5 (GPIO");
  Serial.print(I2C_SCL);
  Serial.println(")");

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  Serial.println("Initializing OLED...");
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB10_tr);
  u8g2.drawStr(0, 15, "XIAO C3");
  u8g2.drawStr(0, 35, "OLED Test");
  u8g2.drawStr(0, 55, "D4/D5");
  u8g2.sendBuffer();

  Serial.println("OLED initialized!");
  Serial.println("Check the OLED display...");
}

void loop() {
  delay(1000);

  static int counter = 0;
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB10_tr);
  u8g2.drawStr(0, 15, "XIAO OLED Test");

  char buf[20];
  sprintf(buf, "Count: %d", counter++);
  u8g2.drawStr(0, 40, buf);
  u8g2.sendBuffer();

  Serial.print("Counter: ");
  Serial.println(counter - 1);
}
