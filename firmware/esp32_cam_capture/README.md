# ESP32-CAM Capture Firmware

This folder contains the ESP32-CAM Arduino sketch for ComponentBox.

## Purpose

The ESP32-CAM captures one electronic component image at a time and sends it to the FastAPI backend for classification. The backend returns a component recommendation or `unknown`; the dashboard then handles review, correction, dataset collection, and inventory actions.

## Current Features

- Connects to Wi-Fi using a local `secrets.h` file.
- Initializes the ESP32-CAM module.
- Serves a small local browser page.
- Provides `/capture` for image preview.
- Provides `/scan` to upload a JPEG to the backend.
- Keeps credentials and local backend URLs out of Git.

## Hardware Used

- ESP32-CAM module
- USB-to-serial programmer or ESP32-CAM-MB programmer
- 5V power source
- Electronic components for sample images

## How It Works

1. The ESP32-CAM connects to Wi-Fi.
2. The Serial Monitor prints the camera page URL.
3. A user opens the camera URL in a browser.
4. The browser can capture a preview image.
5. The upload button captures a JPEG and posts it to `/api/component-scans`.
6. The dashboard polls `/api/component-scans/latest` and shows the newest scan result.

## Arduino IDE Setup

Recommended board settings:

- Board: AI Thinker ESP32-CAM
- Upload speed: 115200
- Flash frequency: 40 MHz
- Partition scheme: Huge APP
- Core debug level: None

## Local Secrets Setup

Copy the public template:

```powershell
copy firmware\esp32_cam_capture\secrets.example.h firmware\esp32_cam_capture\secrets.h
```

Fill in your own local values:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* COMPONENTBOX_BACKEND_SCAN_URL = "http://YOUR_BACKEND_HOST:8000/api/component-scans";
```

`secrets.h` is ignored by Git and should stay local to your machine.
