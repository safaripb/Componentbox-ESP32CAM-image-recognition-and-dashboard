from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.models import ComponentScanResponse, InventoryItemRequest, InventoryItemResponse


@dataclass
class InventoryService:
    _items: list[InventoryItemResponse] = field(default_factory=list)

    def add_from_scan(self, scan: ComponentScanResponse, request: InventoryItemRequest) -> InventoryItemResponse:
        component = scan.corrected_component or scan.recommended_component
        if not component:
            raise ValueError("Scan does not have a component label.")

        item = InventoryItemResponse(
            id=uuid4().hex,
            scan_id=request.scan_id,
            name=request.name or self._default_name(component),
            type=component,
            quantity=request.quantity,
            box=request.box or "Unsorted",
            notes=request.notes or "Added from ESP32-CAM scan.",
            created_at=datetime.now(UTC).isoformat(),
        )
        self._items.insert(0, item)
        return item

    def list_items(self) -> list[InventoryItemResponse]:
        return self._items

    def _default_name(self, component: str) -> str:
        labels = {
            "resistor": "Resistor",
            "capacitor": "Capacitor",
            "wire": "Jumper wire",
            "stepper_motor": "Stepper motor",
            "seven_segment": "7-segment display",
        }
        return labels.get(component, component)
