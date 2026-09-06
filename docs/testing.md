# Testing

Backend tests cover the current component-scan API, rate limiting, inventory actions, correction behavior, and deterministic resistor utility logic.

```powershell
cd backend
pytest
```

## Manual Hardware Checks

- Confirm `secrets.h` exists locally and is not tracked by Git.
- Start the backend and dashboard.
- Open the ESP32-CAM page from the camera IP printed in Serial Monitor.
- Use `/capture` to verify focus and lighting.
- Use the upload button to POST a component to `/api/component-scans`.
- Confirm the dashboard receives the latest scan.
- Correct at least one label and verify the saved image appears in the expected `dataset/<class>/` folder.
- Upload more than `RESISTOR_IMAGE_RATE_LIMIT` images in one minute and verify HTTP 429 behavior.

## Classifier Checks

Test each supported class with realistic ESP32-CAM images:

- resistor
- capacitor
- wire
- stepper_motor
- seven_segment

Images outside the supported set, low-quality captures, and low-confidence predictions should return `unknown` rather than a confident class.
