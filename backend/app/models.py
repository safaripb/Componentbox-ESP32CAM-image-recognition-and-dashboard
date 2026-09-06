from __future__ import annotations

from pydantic import BaseModel, Field


class BandResponse(BaseModel):
    color: str
    hex: str
    confidence: float = Field(ge=0, le=1)


class ComponentScanResponse(BaseModel):
    scan_id: str | None = None
    success: bool
    status: str
    message: str
    recommended_component: str | None = None
    component_class: str | None = None
    resistor_count: int | None = None
    bands: list[str] = Field(default_factory=list)
    detected_bands: list[str] = Field(default_factory=list)
    band_details: list[BandResponse] = Field(default_factory=list)
    resistance_ohms: float | None = None
    formatted_resistance: str | None = None
    recommended_resistance: str | None = None
    tolerance: str | None = None
    confidence: float = Field(ge=0, le=1)
    image_data_url: str | None = None
    filename: str | None = None
    captured_at: str | None = None
    model_version: str | None = None
    saved_image_path: str | None = None
    reviewed: bool = False
    corrected_component: str | None = None
    added_to_inventory: bool = False


class LatestComponentScanResponse(BaseModel):
    scan: ComponentScanResponse | None = None


class ComponentScanHistoryResponse(BaseModel):
    scans: list[ComponentScanResponse]


class ComponentCorrectionRequest(BaseModel):
    component: str = Field(min_length=1, max_length=80)
    save_to_dataset: bool = True


class InventoryItemRequest(BaseModel):
    scan_id: str
    name: str | None = None
    quantity: int = Field(default=1, ge=1)
    box: str | None = None
    notes: str | None = None


class InventoryItemResponse(BaseModel):
    id: str
    scan_id: str
    name: str
    type: str
    quantity: int
    box: str
    notes: str
    created_at: str


ResistorScanResponse = ComponentScanResponse
LatestResistorScanResponse = LatestComponentScanResponse
