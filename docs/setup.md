# Setup

## Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000` by default.

Optional configuration:

```powershell
set RESISTOR_IMAGE_RATE_LIMIT=12
set COMPONENT_CLASSIFIER_MODEL=models/component_classifier.keras
set COMPONENT_CLASSIFIER_CONFIDENCE=0.75
set COMPONENT_SCAN_IMAGE_DIR=data/scans
set COMPONENT_SCAN_METADATA=data/scans.json
set COMPONENT_DATASET_DIR=../dataset
```

## Dashboard

```powershell
cd dashboard
npm install
npm start
```

Open `http://localhost:5173`.

The dashboard reads the backend URL from `window.COMPONENTBOX_API_URL`, then from browser local storage key `COMPONENTBOX_API_URL`, and falls back to `http://localhost:8000`.

## ESP32-CAM

Create a local firmware secrets file:

```powershell
copy firmware\esp32_cam_capture\secrets.example.h firmware\esp32_cam_capture\secrets.h
```

Edit `firmware/esp32_cam_capture/secrets.h` with your own Wi-Fi and backend URL:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* COMPONENTBOX_BACKEND_SCAN_URL = "http://YOUR_BACKEND_HOST:8000/api/component-scans";
```

Upload `esp32_cam_capture.ino` with the Arduino IDE using the AI Thinker ESP32-CAM board settings.

## Mock Upload

With the backend running:

```powershell
python mock_device/send_fake_component_image.py assets/sample_images/esp32.jpg
```

Use a real component photo for meaningful classifier results. Use `--api-url` if the backend is not on localhost.
