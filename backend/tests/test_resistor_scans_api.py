from fastapi.testclient import TestClient
import json
import pytest

from app.main import app
from app.routes import components
from app.services.component_classifier import ComponentPrediction, InvalidComponentImageError
from app.services.component_scan_store import ComponentScanStore
from app.services.inventory_service import InventoryService


class AcceptingLimiter:
    def accept(self, key):
        return True, 0


class RejectingLimiter:
    def accept(self, key):
        return False, 17


class SuccessfulClassifier:
    def recognize(self, image_bytes):
        return ComponentPrediction(
            success=True,
            status="component_detected",
            message="Component detected.",
            recommended_component="resistor",
            confidence=0.91,
            model_version="component_classifier.keras",
        )


class UnknownClassifier:
    def recognize(self, image_bytes):
        return ComponentPrediction(
            success=False,
            status="unknown",
            message="No supported component detected.",
            recommended_component=None,
            confidence=0.42,
            model_version="component_classifier.keras",
        )


class InvalidImageClassifier:
    def recognize(self, image_bytes):
        raise InvalidComponentImageError("Uploaded file could not be decoded as an image.")


@pytest.fixture(autouse=True)
def reset_scan_state(tmp_path):
    components.latest_scan = None
    components.scan_store = ComponentScanStore(
        image_dir=tmp_path / "scans",
        dataset_dir=tmp_path / "dataset",
        metadata_path=tmp_path / "scans.json",
    )
    components.inventory_service = InventoryService()
    yield
    components.latest_scan = None


def test_component_scan_endpoint_returns_successful_detection(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    response = client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "component_detected"
    assert payload["recommended_component"] == "resistor"
    assert payload["component_class"] == "resistor"
    assert payload["confidence"] == 0.91
    assert payload["image_data_url"].startswith("data:image/jpeg;base64,")
    assert payload["recommended_resistance"] is None
    assert payload["bands"] == []
    assert payload["scan_id"]
    assert payload["saved_image_path"]


def test_component_scan_endpoint_returns_unknown_for_low_confidence(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    response = client.post(
        "/api/component-scans",
        files={"image": ("unknown.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["status"] == "unknown"
    assert payload["message"] == "No supported component detected."
    assert payload["recommended_component"] is None
    assert payload["confidence"] == 0.42


def test_component_scan_endpoint_returns_clear_rate_limit_error(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", RejectingLimiter())
    client = TestClient(app)

    response = client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert "Image capture rate limit exceeded" in response.json()["detail"]


def test_latest_component_scan_returns_newest_result(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    empty_response = client.get("/api/resistor-scans/latest")
    assert empty_response.status_code == 200
    assert empty_response.json() == {"scan": None}

    client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    latest_response = client.get("/api/component-scans/latest")

    assert latest_response.status_code == 200
    payload = latest_response.json()["scan"]
    assert payload["status"] == "component_detected"
    assert payload["recommended_component"] == "resistor"
    assert payload["filename"] == "component.jpg"


def test_component_scan_history_returns_saved_scans(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    response = client.get("/api/component-scans")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["scans"]) == 1
    assert payload["scans"][0]["recommended_component"] == "resistor"


def test_posted_component_scan_appears_in_history_by_scan_id(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    assert client.get("/api/component-scans").json() == {"scans": []}
    post_response = client.post(
        "/api/component-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert post_response.status_code == 200
    scan_id = post_response.json()["scan_id"]
    history_response = client.get("/api/component-scans")

    assert history_response.status_code == 200
    history_ids = [scan["scan_id"] for scan in history_response.json()["scans"]]
    assert scan_id in history_ids


def test_posted_component_scan_survives_store_recreation(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    post_response = client.post(
        "/api/component-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert post_response.status_code == 200
    scan_id = post_response.json()["scan_id"]
    metadata = json.loads(components.scan_store.metadata_path.read_text(encoding="utf-8"))
    assert any(scan["scan_id"] == scan_id for scan in metadata)

    history_response = client.get("/api/component-scans")
    assert history_response.status_code == 200
    assert any(scan["scan_id"] == scan_id for scan in history_response.json()["scans"])

    components.scan_store = ComponentScanStore(
        image_dir=components.scan_store.image_dir,
        dataset_dir=components.scan_store.dataset_dir,
        metadata_path=components.scan_store.metadata_path,
    )
    recreated_history_response = client.get("/api/component-scans")

    assert recreated_history_response.status_code == 200
    recreated_ids = [scan["scan_id"] for scan in recreated_history_response.json()["scans"]]
    assert scan_id in recreated_ids


def test_unknown_component_scan_is_saved_in_history(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    post_response = client.post(
        "/api/component-scans",
        files={"image": ("unknown.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert post_response.status_code == 200
    scan_id = post_response.json()["scan_id"]
    history_response = client.get("/api/component-scans")

    assert history_response.status_code == 200
    saved_scan = next(scan for scan in history_response.json()["scans"] if scan["scan_id"] == scan_id)
    assert saved_scan["status"] == "unknown"
    assert saved_scan["message"] == "No supported component detected."
    assert saved_scan["recommended_component"] is None


def test_component_scan_history_reloads_json_instead_of_stale_memory(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    assert client.get("/api/component-scans").json() == {"scans": []}
    post_response = client.post(
        "/api/component-scans",
        files={"image": ("unknown.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    scan_id = post_response.json()["scan_id"]

    components.scan_store._scans = []
    history_response = client.get("/api/component-scans")

    assert history_response.status_code == 200
    assert any(scan["scan_id"] == scan_id for scan in history_response.json()["scans"])


def test_component_correction_reviews_scan_and_exports_dataset(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    scan_response = client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    scan_id = scan_response.json()["scan_id"]
    response = client.patch(
        f"/api/component-scans/{scan_id}/correction",
        json={"component": "capacitor", "save_to_dataset": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewed"] is True
    assert payload["corrected_component"] == "capacitor"
    assert payload["recommended_component"] == "capacitor"
    assert list((components.scan_store.dataset_dir / "capacitor").glob("*.jpg"))


def test_component_correction_accepts_a_custom_manual_label(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    scan_response = client.post(
        "/api/component-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    scan_id = scan_response.json()["scan_id"]
    response = client.patch(
        f"/api/component-scans/{scan_id}/correction",
        json={"component": "Light sensor module", "save_to_dataset": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewed"] is True
    assert payload["corrected_component"] == "Light sensor module"
    assert payload["recommended_component"] == "Light sensor module"
    assert not (components.scan_store.dataset_dir / "Light sensor module").exists()


def test_component_scan_can_be_added_to_inventory(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", SuccessfulClassifier())
    client = TestClient(app)

    scan_response = client.post(
        "/api/resistor-scans",
        files={"image": ("component.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    scan_id = scan_response.json()["scan_id"]
    response = client.post(
        "/api/inventory/components",
        json={"scan_id": scan_id, "quantity": 3, "box": "Drawer A"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_id"] == scan_id
    assert payload["type"] == "resistor"
    assert payload["quantity"] == 3
    assert payload["box"] == "Drawer A"


def test_component_scan_endpoint_rejects_invalid_images(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", InvalidImageClassifier())
    client = TestClient(app)

    response = client.post(
        "/api/resistor-scans",
        files={"image": ("not-an-image.jpg", b"not-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file could not be decoded as an image."
