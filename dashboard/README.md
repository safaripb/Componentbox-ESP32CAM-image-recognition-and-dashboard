# ComponentBox Dashboard

A responsive AngularJS 1.8 dashboard for uploading, reviewing, correcting, and inventorying component images captured by the ESP32-CAM.

## Run Locally

```powershell
npm install
npm start
```

Open `http://localhost:5173`.

Start the FastAPI backend on `http://localhost:8000` before uploading component images. To use another API host, define `window.COMPONENTBOX_API_URL` before `src/app.js` loads or store a `COMPONENTBOX_API_URL` value in browser local storage.

## Current Features

- Grid and list views for component captures.
- Search, component, confidence, review-state, and status filters.
- Upload flow for local images and ESP32-CAM captures.
- Latest scan result panel with captured image, recommended component, model, and confidence.
- Scan detail viewer with result metadata.
- Correction buttons that save reviewed labels for future model training.
- Add-to-inventory action for detected or corrected scans.
- Responsive layout for desktop and mobile.
- Demo scans that keep the dashboard useful before the first backend scan.

Supported dashboard labels match the backend classifier classes: resistor, capacitor, jumper wire, stepper motor, and 7-segment display.
