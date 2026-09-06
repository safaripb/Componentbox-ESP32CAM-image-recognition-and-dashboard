# ComponentBox Architecture

ComponentBox is split into firmware, backend, dashboard, dataset, and documentation areas so each teammate can work without stepping on the others.

## Flow

```text
ESP32-CAM / dashboard upload
        |
        v
FastAPI upload endpoint
        |
        v
Rate limit + image validation
        |
        v
MobileNetV2-style component classifier
        |
        v
Scan history + latest result
        |
        v
Dashboard review + correction
        |
        v
Dataset collection + inventory
```

## Firmware

`firmware/esp32_cam_capture` contains the Arduino sketch for the ESP32-CAM. It:

- connects to Wi-Fi using local values from `secrets.h`;
- initializes the camera;
- serves a local capture page;
- exposes `/capture` for browser preview;
- exposes `/scan` to upload the current JPEG to the FastAPI backend.

`secrets.h` is ignored by Git. Use `secrets.example.h` as the public template.

## Backend

`backend/app/main.py` creates the FastAPI application and registers the component routes.

Important services:

- `component_classifier.py`: MobileNetV2-style Keras classifier wrapper, supported class list, confidence threshold, and `unknown` fallback.
- `component_scan_store.py`: scan image storage, metadata history, label correction, and dataset export.
- `inventory_service.py`: lightweight inventory records created from reviewed scans.
- `rate_limiter.py`: per-client upload limit.
- `resistor_calculator.py`: deterministic 4-band resistor math retained as a tested utility.
- `resistor_recognition.py`: older OpenCV resistor-band recognizer retained for future experiments.

## Dashboard

`dashboard/` is a static AngularJS scan-review dashboard. It posts uploads to the backend, polls the latest scan, shows recent captures, supports filtering, lets users correct labels, and can add reviewed scans to inventory.

The dashboard defaults to `http://localhost:8000` and can be pointed at another backend with `window.COMPONENTBOX_API_URL` or browser local storage.

## Dataset Loop

Corrected labels can be copied into `dataset/<class>/`. Those reviewed images become training examples for the next MobileNetV2 transfer-learning run.

## Compatibility

The preferred upload endpoint is `/api/component-scans`. The backend still supports `/api/resistor-scans` and `/api/resistor-scans/latest` so existing ESP32-CAM and dashboard work is not broken.
