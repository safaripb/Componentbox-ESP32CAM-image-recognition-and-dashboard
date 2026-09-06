from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


COLOR_HEX = {
    "black": "#1f1f1f",
    "brown": "#724227",
    "red": "#bf3a35",
    "orange": "#e58e31",
    "yellow": "#f0cf43",
    "green": "#3f8f5a",
    "blue": "#3867b7",
    "violet": "#7b4a99",
    "gray": "#8d8d8d",
    "white": "#f2f2e8",
    "gold": "#d6a63b",
    "silver": "#c0c0c0",
}


@dataclass(frozen=True)
class DetectedBand:
    color: str
    confidence: float
    hex: str


@dataclass(frozen=True)
class RecognitionResult:
    success: bool
    bands: list[DetectedBand]
    confidence: float
    message: str


class ResistorImageRecognizer:
    """Explainable OpenCV resistor-band detector for one resistor per image."""

    min_confidence = 0.55

    def count_resistors(self, image_bytes: bytes) -> int:
        image = self._decode_image(image_bytes)
        if image is None:
            return 0
        return len(self._find_resistor_candidates(image))

    def recognize(self, image_bytes: bytes) -> RecognitionResult:
        image = self._decode_image(image_bytes)
        if image is None:
            return self._failure("The uploaded file could not be decoded as an image.")

        crop = self._extract_resistor_region(image)
        if crop is None:
            return self._failure("Could not isolate a resistor-shaped region in the image.")

        bands = self._detect_bands(crop)
        if len(bands) != 4:
            return RecognitionResult(
                success=False,
                bands=bands,
                confidence=self._average_confidence(bands),
                message="Could not confidently detect exactly four resistor bands.",
            )

        confidence = self._average_confidence(bands)
        if confidence < self.min_confidence:
            return RecognitionResult(
                success=False,
                bands=bands,
                confidence=confidence,
                message="Detected four bands, but the color confidence is too low.",
            )

        return RecognitionResult(
            success=True,
            bands=bands,
            confidence=confidence,
            message="Four resistor bands detected.",
        )

    def _decode_image(self, image_bytes: bytes) -> np.ndarray | None:
        data = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    def _extract_resistor_region(self, image: np.ndarray) -> np.ndarray | None:
        candidates = self._find_resistor_candidates(image)
        if not candidates:
            return None

        resized = self._resize_for_processing(image)
        _, best_rect = max(candidates, key=lambda item: item[0])
        return self._warp_rect(resized, best_rect)

    def _find_resistor_candidates(self, image: np.ndarray) -> list[tuple[float, tuple]]:
        resized = self._resize_for_processing(image)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 45, 140)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 900:
                continue
            rect = cv2.minAreaRect(contour)
            width, height = rect[1]
            if width == 0 or height == 0:
                continue
            long_side = max(width, height)
            short_side = min(width, height)
            ratio = long_side / short_side
            if ratio >= 2.2:
                candidates.append((area * ratio, rect))

        return self._dedupe_candidates(candidates)

    def _detect_bands(self, crop: np.ndarray) -> list[DetectedBand]:
        if crop.shape[0] > crop.shape[1]:
            crop = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)

        h, w = crop.shape[:2]
        y1, y2 = int(h * 0.32), int(h * 0.68)
        strip = crop[y1:y2, :]
        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(strip, cv2.COLOR_BGR2LAB)

        column_lab = np.median(lab, axis=0)
        body_lab = np.median(column_lab, axis=0)
        distances = np.linalg.norm(column_lab - body_lab, axis=1)
        saturation = np.median(hsv[:, :, 1], axis=0)
        value = np.median(hsv[:, :, 2], axis=0)

        band_score = distances + saturation * 0.32 + np.maximum(0, 85 - value) * 0.35
        threshold = max(28, float(np.percentile(band_score, 78)))
        mask = band_score > threshold
        mask = self._smooth_mask(mask, max(3, w // 80))
        segments = self._segments_from_mask(mask, w)

        detected = []
        for start, end in segments:
            width = end - start
            if width < max(4, w * 0.012) or width > w * 0.18:
                continue
            pad = max(1, int(width * 0.15))
            sample = crop[y1:y2, start + pad : max(start + pad + 1, end - pad)]
            color, confidence = classify_band_color(sample)
            detected.append((start, DetectedBand(color=color, confidence=confidence, hex=COLOR_HEX[color])))

        detected.sort(key=lambda item: item[0])
        if len(detected) > 4:
            strongest = sorted(detected, key=lambda item: item[1].confidence, reverse=True)[:4]
            detected = sorted(strongest, key=lambda item: item[0])
        return [band for _, band in detected]

    def _resize_for_processing(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        if w <= 900:
            return image
        scale = 900 / w
        return cv2.resize(image, (900, int(h * scale)), interpolation=cv2.INTER_AREA)

    def _warp_rect(self, image: np.ndarray, rect: tuple) -> np.ndarray | None:
        box = cv2.boxPoints(rect)
        width, height = [int(v) for v in rect[1]]
        if width < 1 or height < 1:
            return None
        source = self._order_points(box)
        dest = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
        transform = cv2.getPerspectiveTransform(source, dest)
        warped = cv2.warpPerspective(image, transform, (width, height))
        if warped.shape[0] > warped.shape[1]:
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        return warped

    def _order_points(self, points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")
        sums = points.sum(axis=1)
        diffs = np.diff(points, axis=1)
        rect[0] = points[np.argmin(sums)]
        rect[2] = points[np.argmax(sums)]
        rect[1] = points[np.argmin(diffs)]
        rect[3] = points[np.argmax(diffs)]
        return rect

    def _smooth_mask(self, mask: np.ndarray, kernel_size: int) -> np.ndarray:
        kernel = np.ones(kernel_size, dtype=np.uint8)
        closed = np.convolve(mask.astype(np.uint8), kernel, mode="same") >= max(1, kernel_size // 2)
        return closed

    def _segments_from_mask(self, mask: np.ndarray, width: int) -> list[tuple[int, int]]:
        segments = []
        start = None
        for index, is_band in enumerate(mask):
            if is_band and start is None:
                start = index
            elif not is_band and start is not None:
                segments.append((start, index))
                start = None
        if start is not None:
            segments.append((start, width))
        return segments

    def _dedupe_candidates(self, candidates: list[tuple[float, tuple]]) -> list[tuple[float, tuple]]:
        ordered = sorted(candidates, key=lambda item: item[0], reverse=True)
        kept = []
        for score, rect in ordered:
            center = rect[0]
            long_side = max(rect[1])
            duplicate = False
            for _, kept_rect in kept:
                kept_center = kept_rect[0]
                kept_long_side = max(kept_rect[1])
                center_distance = np.linalg.norm(np.array(center) - np.array(kept_center))
                if center_distance < max(long_side, kept_long_side) * 0.35:
                    duplicate = True
                    break
            if not duplicate:
                kept.append((score, rect))
        return kept

    def _average_confidence(self, bands: list[DetectedBand]) -> float:
        if not bands:
            return 0.0
        return round(sum(band.confidence for band in bands) / len(bands), 2)

    def _failure(self, message: str) -> RecognitionResult:
        return RecognitionResult(success=False, bands=[], confidence=0.0, message=message)


def classify_band_color(sample_bgr: np.ndarray) -> tuple[str, float]:
    hsv = cv2.cvtColor(sample_bgr, cv2.COLOR_BGR2HSV)
    h = float(np.median(hsv[:, :, 0]))
    s = float(np.median(hsv[:, :, 1]))
    v = float(np.median(hsv[:, :, 2]))

    if v < 48:
        return "black", _confidence(v, 20, 40)
    if s < 34 and v > 190:
        return "white", _confidence(v, 235, 60)
    if s < 45:
        return "silver", _confidence(v, 180, 80)
    if 18 <= h <= 36 and 70 <= s <= 190 and v >= 95:
        return "gold", 0.68
    if h < 5 or h >= 170:
        return "red", 0.76
    if 5 <= h < 16:
        return "brown" if v < 125 else "orange", 0.72
    if 16 <= h < 26:
        return "orange", 0.74
    if 26 <= h < 42:
        return "yellow", 0.76
    if 42 <= h < 86:
        return "green", 0.76
    if 86 <= h < 126:
        return "blue", 0.76
    if 126 <= h < 160:
        return "violet", 0.72
    return "gray", 0.45


def _confidence(value: float, target: float, spread: float) -> float:
    return round(max(0.45, min(0.95, 1 - abs(value - target) / spread)), 2)
