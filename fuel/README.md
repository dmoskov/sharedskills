# Battery Monitor with OLED Display

Display battery information from SparkFun LiPo Fuel Gauge (MAX17043) on OLED display.

## Hardware
- Adafruit Feather RP2040
- SparkFun LiPo Fuel Gauge (MAX17043) with Qwiic connector
- 128x64 OLED Display (SSD1306)
- Single-cell LiPo battery

## Wiring
All components connect via I2C/Qwiic:
- Fuel Gauge → Qwiic/STEMMA QT connector on Feather
- OLED → I2C pins (SDA/SCL) or daisy-chain via Qwiic
- 3.3V power to all devices

## Required Libraries
Install via Arduino Library Manager:
1. SparkFun MAX1704x Fuel Gauge Arduino Library
2. U8g2 (for OLED display)

## Features
- Real-time voltage display (V)
- State of charge percentage (%)
- Visual battery level bar graph
- Updates every second
- Serial debug output at 115200 baud

## Upload Procedure
1. Install RP2040 board support in Arduino IDE (File > Preferences > Additional Board Manager URLs)
2. Select "Adafruit Feather RP2040" in Tools > Board
3. Connect Feather RP2040 via USB
4. Select correct COM port
5. Compile and upload:
   ```bash
   arduino-cli compile --fqbn rp2040:rp2040:adafruit_feather battery_monitor_oled.ino
   arduino-cli upload -p /dev/cu.usbmodem* --fqbn rp2040:rp2040:adafruit_feather battery_monitor_oled.ino
   ```
6. Open Serial Monitor (115200 baud) to view debug info

## Display
- Line 1: "Battery Status" header
- Line 2: Voltage reading
- Line 3: State of charge percentage
- Line 4: Visual progress bar

## XIAO ESP32-C6 Version

### Hardware
- Seeed XIAO ESP32-C6
- XIAO Expansion Board (with built-in SSD1306 OLED)
- SparkFun MAX17043 Fuel Gauge connected via Grove I2C connector
- Single-cell LiPo battery

### Upload Procedure
1. Install ESP32 board support in Arduino IDE
2. Install required libraries:
   - SparkFun MAX1704x Fuel Gauge Arduino Library
   - U8g2
3. Select "XIAO_ESP32C6" in Tools > Board > ESP32 Arduino
4. Connect XIAO via USB-C
5. Compile and upload:
   ```bash
   arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C6 xiao_c6_fuel_monitor/
   arduino-cli upload -p /dev/cu.usbmodem* --fqbn esp32:esp32:XIAO_ESP32C6 xiao_c6_fuel_monitor/
   ```
6. Monitor output: `arduino-cli monitor -p /dev/cu.usbmodem* -c baudrate=115200`

### Features
- I2C device scanning at startup
- Real-time voltage and percentage display
- Large, readable fonts on expansion board OLED
- Visual battery bar graph
- Serial debug output at 115200 baud

## Version
v3.0 - XIAO ESP32-C6 with Expansion Board
v2.0 - Updated for Adafruit Feather RP2040 with OLED display
