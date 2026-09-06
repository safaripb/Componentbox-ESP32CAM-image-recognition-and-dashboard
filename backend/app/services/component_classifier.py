from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


SUPPORTED_COMPONENTS = [
    "resistor",
    "capacitor",
    "wire",
    "stepper_motor",
    "seven_segment",
]

DEFAULT_MODEL_PATH = Path(os.getenv("COMPONENT_CLASSIFIER_MODEL", "models/component_classifier.keras"))
DEFAULT_CONFIDENCE_THRESHOLD = float(os.getenv("COMPONENT_CLASSIFIER_CONFIDENCE", "0.75"))


class InvalidComponentImageError(ValueError):
    """Raised when uploaded bytes cannot be decoded as an image."""


@dataclass(frozen=True)
class ComponentPrediction:
    success: bool
    status: str
    message: str
    recommended_component: str | None
    confidence: float
    model_version: str | None = None


class ComponentImageClassifier:
    """Training-ready component classifier for ESP32-CAM images.

    The backend hosts inference. If no trained model is present, the classifier
    returns an unknown result instead of pretending to recognize components.
    """

    def __init__(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        class_names: list[str] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.class_names = class_names or SUPPORTED_COMPONENTS
        self._model = None
        self._tensorflow = None

    def recognize(self, image_bytes: bytes) -> ComponentPrediction:
        image = self._decode_image(image_bytes)
        if image is None:
            raise InvalidComponentImageError("Uploaded file could not be decoded as an image.")

        if not self.model_path.exists():
            return self._unknown()

        try:
            model = self._load_model()
            predictions = model.predict(self._preprocess(image), verbose=0)[0]
        except Exception:
            return self._unknown()

        best_index = int(np.argmax(predictions))
        confidence = round(float(predictions[best_index]), 2)
        if best_index >= len(self.class_names):
            return self._unknown()

        component = self.class_names[best_index]
        if component not in SUPPORTED_COMPONENTS or confidence < self.confidence_threshold:
            return self._unknown(confidence)

        return ComponentPrediction(
            success=True,
            status="component_detected",
            message="Component detected.",
            recommended_component=component,
            confidence=confidence,
            model_version=self.model_path.name,
        )

    def _decode_image(self, image_bytes: bytes) -> np.ndarray | None:
        data = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            import tensorflow as tf
        except ImportError as error:
            raise RuntimeError("TensorFlow is required to run the component classifier.") from error

        self._tensorflow = tf
        self._model = tf.keras.models.load_model(self.model_path)
        return self._model

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        tf = self._tensorflow
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
        batch = np.expand_dims(resized.astype(np.float32), axis=0)
        if tf is None:
            return batch
        return tf.keras.applications.mobilenet_v2.preprocess_input(batch)

    def _unknown(self, confidence: float = 0.0) -> ComponentPrediction:
        return ComponentPrediction(
            success=False,
            status="unknown",
            message="No supported component detected.",
            recommended_component=None,
            confidence=round(confidence, 2),
            model_version=self.model_path.name if self.model_path.exists() else None,
        )
