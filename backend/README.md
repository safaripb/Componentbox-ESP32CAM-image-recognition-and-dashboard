# ComponentBox Backend

FastAPI backend for the ESP32-CAM component-classification workflow.

## API

- `GET /api/health` returns backend status.
- `POST /api/component-scans` accepts a multipart image field named `image`.
- `POST /api/resistor-scans` is a backwards-compatible alias for the same upload workflow.
- `GET /api/component-scans/latest` returns the newest accepted scan for dashboard polling.
- `GET /api/resistor-scans/latest` is a backwards-compatible alias for the same latest result.
- `GET /api/component-scans` returns saved scan history.
- `PATCH /api/component-scans/{scan_id}/correction` saves a reviewed label and can export the image to `dataset/`.
- `POST /api/inventory/components` adds a detected or corrected scan to the inventory list.

The scan endpoint:

1. Applies a configurable backend rate limit.
2. Validates that the upload can be decoded as an image.
3. Sends the image to `services/component_classifier.py`.
4. Returns `component_detected` with a recommended component class when confidence is high enough.
5. Returns `unknown` with `No supported component detected.` when no trained model is available or confidence is too low.

## Configuration

- `RESISTOR_IMAGE_RATE_LIMIT`: accepted uploads per client per minute. Default: `12`.
- `COMPONENT_CLASSIFIER_MODEL`: trained Keras model path. Default: `models/component_classifier.keras`.
- `COMPONENT_CLASSIFIER_CONFIDENCE`: minimum confidence for accepting a class. Default: `0.75`.

The resistor band recognizer and resistor calculator are still available as reusable services, but they are no longer used by the primary scan endpoint.

Supported classifier labels are `resistor`, `capacitor`, `wire`, `stepper_motor`, and `seven_segment`.

## Train

Add real ESP32-CAM photos under `../dataset/<class-name>/`, then install the training dependencies and run:

```bash
pip install -r requirements-training.txt
python scripts/train_component_classifier.py --dataset ../dataset --output models/component_classifier.keras
```

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
