#!/bin/bash

SKETCH_DIR="xiao_c6_fuel_monitor"
FQBN="esp32:esp32:XIAO_ESP32C3"

echo "=== XIAO ESP32-C3 Fuel Monitor Upload ==="
echo ""

cd "$(dirname "$0")/.."

echo "Compiling..."
arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR/"

if [ $? -ne 0 ]; then
    echo "Compilation failed!"
    exit 1
fi

echo ""
echo "Finding USB port..."
PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -n 1)

if [ -z "$PORT" ]; then
    echo "ERROR: No USB device found!"
    echo "Make sure XIAO is connected via USB-C"
    exit 1
fi

echo "Found: $PORT"
echo ""
echo "Uploading..."
arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SKETCH_DIR/"

if [ $? -eq 0 ]; then
    echo ""
    echo "Upload successful!"
    echo ""
    echo "Starting serial monitor (Ctrl+C to exit)..."
    sleep 2
    arduino-cli monitor -p "$PORT" -c baudrate=115200
else
    echo "Upload failed!"
    exit 1
fi
