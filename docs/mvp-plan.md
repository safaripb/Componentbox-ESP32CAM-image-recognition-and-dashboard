# Current MVP

The ComponentBox MVP is a working scan-review loop for electronic component classification and lightweight inventory capture.

## MVP Scope

- Capture one component image with the ESP32-CAM or dashboard upload.
- Send the image to the FastAPI backend.
- Classify the image as one of the supported component classes, or return `unknown`.
- Store recent scan metadata and captured images locally.
- Show scans in the dashboard.
- Let a human correct labels and export reviewed images into the dataset.
- Add detected or corrected scans to a simple inventory list.

## Supported Classes

- resistor
- capacitor
- wire
- stepper_motor
- seven_segment

## Out Of Scope For The MVP

- Multi-object detection in a single image.
- Production inventory database.
- Published accuracy claims without a held-out evaluation set.
- On-device inference.
- Resistor value decoding from camera images.

## Next Milestone

The next milestone is dataset quality: collect balanced ESP32-CAM images for every supported class, train the MobileNetV2-style classifier, and document measured validation results.
