from __future__ import annotations

import base64
from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.models import (
    ComponentCorrectionRequest,
    ComponentScanHistoryResponse,
    ComponentScanResponse,
    InventoryItemRequest,
    InventoryItemResponse,
    LatestComponentScanResponse,
)
from app.services.component_classifier import ComponentImageClassifier, InvalidComponentImageError
from app.services.component_scan_store import ComponentScanStore
from app.services.inventory_service import InventoryService
from app.services.rate_limiter import DEFAULT_IMAGE_UPLOADS_PER_MINUTE, SlidingWindowRateLimiter


router = APIRouter(prefix="/api", tags=["component scans"])
rate_limiter = SlidingWindowRateLimiter()
classifier = ComponentImageClassifier()
scan_store = ComponentScanStore()
inventory_service = InventoryService()
latest_scan: ComponentScanResponse | None = None


@router.post("/resistor-scans", response_model=ComponentScanResponse)
@router.post("/component-scans", response_model=ComponentScanResponse)
async def create_component_scan(request: Request, image: UploadFile = File(...)) -> ComponentScanResponse:
    global latest_scan

    client_key = request.client.host if request.client else "unknown-client"
    accepted, retry_after = rate_limiter.accept(client_key)
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Image capture rate limit exceeded. "
                f"Try again in {retry_after} seconds. "
                f"Limit: {DEFAULT_IMAGE_UPLOADS_PER_MINUTE} images per minute."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be an image file from the ESP32-CAM.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty.")

    image_data_url = _image_data_url(image_bytes, image.content_type or "image/jpeg")
    filename = image.filename or "esp32-cam.jpg"
    captured_at = datetime.now(UTC).isoformat()

    try:
        prediction = classifier.recognize(image_bytes)
    except InvalidComponentImageError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    scan = ComponentScanResponse(
        success=prediction.success,
        status=prediction.status,
        message=prediction.message,
        recommended_component=prediction.recommended_component,
        component_class=prediction.recommended_component,
        confidence=prediction.confidence,
        image_data_url=image_data_url,
        filename=filename,
        captured_at=captured_at,
        model_version=prediction.model_version,
    )
    latest_scan = scan_store.add_scan(scan, image_bytes, image.content_type or "image/jpeg", filename)
    return latest_scan


@router.get("/resistor-scans/latest", response_model=LatestComponentScanResponse)
@router.get("/component-scans/latest", response_model=LatestComponentScanResponse)
def get_latest_component_scan() -> LatestComponentScanResponse:
    return LatestComponentScanResponse(scan=scan_store.latest() or latest_scan)


@router.get("/component-scans", response_model=ComponentScanHistoryResponse)
def list_component_scans(limit: int = 50) -> ComponentScanHistoryResponse:
    return ComponentScanHistoryResponse(scans=scan_store.list_scans(limit=limit))


@router.patch("/component-scans/{scan_id}/correction", response_model=ComponentScanResponse)
def correct_component_scan(scan_id: str, correction: ComponentCorrectionRequest) -> ComponentScanResponse:
    global latest_scan

    try:
        latest_scan = scan_store.correct_scan(scan_id, correction.component, correction.save_to_dataset)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.") from error

    return latest_scan


@router.post("/inventory/components", response_model=InventoryItemResponse)
def add_component_to_inventory(item_request: InventoryItemRequest) -> InventoryItemResponse:
    try:
        scan = scan_store.get_scan(item_request.scan_id)
        item = inventory_service.add_from_scan(scan, item_request)
        scan_store.mark_added_to_inventory(item_request.scan_id)
        return item
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/inventory/components", response_model=list[InventoryItemResponse])
def list_inventory_components() -> list[InventoryItemResponse]:
    return inventory_service.list_items()


def _image_data_url(image_bytes: bytes, content_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{encoded}"
