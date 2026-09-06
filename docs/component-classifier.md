# Component Classifier

The primary scan workflow classifies one supported electronic component per image:

- resistor
- capacitor
- wire
- stepper_motor
- seven_segment

The classifier runs on the Python FastAPI backend, not on the ESP32-CAM. The ESP32-CAM only captures and uploads JPEG images.

## Dataset

Collect real ESP32-CAM photos in:

```text
dataset/
|-- resistor/
|-- capacitor/
|-- wire/
|-- stepper_motor/
`-- seven_segment/
```

Use one component per photo. Capture the same way the project will be used: same ESP32-CAM module, similar distance, similar background, and realistic lighting. Add variation in angle, placement, rotation, and brightness.

For a student project, start with roughly 100-200 pictures per class. More is better, especially for wire/jumper wire because colors, curves, and connectors vary a lot. Keep a small validation set by letting the training script split 20% of the images.

The dashboard correction workflow also helps build this dataset. When you correct a scan label, the backend copies the saved scan image into the matching dataset class folder.

## Training

The training script uses MobileNetV2 transfer learning and saves a Keras model:

```powershell
cd backend
pip install -r requirements-training.txt
python scripts/train_component_classifier.py --dataset ../dataset --output models/component_classifier.keras
```

The API loads `models/component_classifier.keras` by default. You can override it:

```powershell
set COMPONENT_CLASSIFIER_MODEL=models/my_classifier.keras
```

## Confidence Threshold

The backend accepts a component only when the top model probability is at or above `COMPONENT_CLASSIFIER_CONFIDENCE`, which defaults to `0.75`.

- Higher threshold: fewer wrong labels, more `unknown` results.
- Lower threshold: more detections, but more risk of incorrect labels.

Until a trained model exists, the backend returns:

```json
{
  "success": false,
  "status": "unknown",
  "message": "No supported component detected."
}
```
