# ComponentBox Component API

## `GET /api/health`

Returns:

```json
{
  "status": "ok",
  "focus": "component-classification"
}
```

## `POST /api/component-scans`

Accepts `multipart/form-data` with one file field:

- `image`: JPEG/PNG/WebP image from the ESP32-CAM or dashboard upload.

`POST /api/resistor-scans` is also available as a backwards-compatible alias for earlier firmware and dashboard work.

Successful component response:

```json
{
  "success": true,
  "status": "component_detected",
  "message": "Component detected.",
  "recommended_component": "resistor",
  "component_class": "resistor",
  "confidence": 0.91,
  "image_data_url": "data:image/jpeg;base64,...",
  "filename": "esp32-cam.jpg",
  "captured_at": "2026-08-30T03:22:10.123456+00:00",
  "model_version": "component_classifier.keras"
}
```

Unknown or low-confidence response:

```json
{
  "success": false,
  "status": "unknown",
  "message": "No supported component detected.",
  "recommended_component": null,
  "confidence": 0.42
}
```

If too many images are uploaded from the same client in one minute, the API returns:

- Status: `429 Too Many Requests`
- Header: `Retry-After`
- Body detail explaining the configured per-minute limit.

Invalid image bytes return `400 Bad Request`.

## `GET /api/component-scans/latest`

Returns the newest accepted scan result for dashboard polling. `GET /api/resistor-scans/latest` is also available as a backwards-compatible alias.

```json
{
  "scan": {
    "success": true,
    "status": "component_detected",
    "recommended_component": "resistor",
    "confidence": 0.91
  }
}
```

If no scan has been accepted since the backend started, it returns `{ "scan": null }`.

## `GET /api/component-scans`

Returns recent saved scan history for the dashboard:

```json
{
  "scans": [
    {
      "scan_id": "abc123",
      "status": "component_detected",
      "recommended_component": "capacitor",
      "confidence": 0.88,
      "reviewed": false,
      "added_to_inventory": false
    }
  ]
}
```

## `PATCH /api/component-scans/{scan_id}/correction`

Confirms or corrects the label. By default, the saved scan image is copied into the matching dataset folder so the correction can be used for training.

```json
{
  "component": "capacitor",
  "save_to_dataset": true
}
```

## `POST /api/inventory/components`

Adds a detected or corrected scan to the lightweight inventory list:

```json
{
  "scan_id": "abc123",
  "quantity": 1,
  "box": "Unsorted"
}
```

## Model

The primary recognition workflow uses `backend/app/services/component_classifier.py`. It is ready to load a trained Keras MobileNetV2-style classifier from `backend/models/component_classifier.keras`, but the repository does not include a trained model yet. Until real ESP32-CAM training photos are collected and a model is saved, scans return `unknown` instead of fake classifications.

Supported classes are `resistor`, `capacitor`, `wire`, `stepper_motor`, and `seven_segment`.
