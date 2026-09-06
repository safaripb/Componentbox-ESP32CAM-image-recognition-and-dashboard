# Component Classifier Dataset

Add real ESP32-CAM photos to these folders:

```text
dataset/
├── resistor/
├── capacitor/
├── wire/
├── stepper_motor/
└── seven_segment/
```

Keep one component per picture. Use the same camera, lighting, distance, and background you expect during real scans, but include reasonable variation so the classifier does not memorize one exact setup.

Corrected dashboard scans are copied into these folders automatically when `save_to_dataset` is enabled. You can also add photos manually.
