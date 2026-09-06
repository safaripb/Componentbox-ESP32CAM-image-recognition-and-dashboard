# ESP32-CAM Setup

## Hardware

- ESP32-CAM module
- USB-to-serial programmer or ESP32-CAM-MB programmer
- Stable 5V power source
- Components to scan

## Arduino IDE

Recommended settings:

- Board: AI Thinker ESP32-CAM
- Upload speed: 115200
- Flash frequency: 40 MHz
- Partition scheme: Huge APP
- Core debug level: None

## Secrets

Create a local secrets file before uploading the sketch:

```powershell
copy firmware\esp32_cam_capture\secrets.example.h firmware\esp32_cam_capture\secrets.h
```

Then edit `secrets.h`:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* COMPONENTBOX_BACKEND_SCAN_URL = "http://YOUR_BACKEND_HOST:8000/api/component-scans";
```

Do not commit `secrets.h`.

## Run

1. Start the FastAPI backend.
2. Upload the firmware.
3. Open Serial Monitor at 115200 baud.
4. Use the printed camera URL to open the ESP32-CAM page.
5. Press capture to preview an image.
6. Press upload to send the image to ComponentBox.

The dashboard should show the latest scan after the backend accepts it.
