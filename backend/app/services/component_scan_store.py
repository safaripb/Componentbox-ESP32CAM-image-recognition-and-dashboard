from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.models import ComponentScanResponse
from app.services.component_classifier import SUPPORTED_COMPONENTS


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass
class ComponentScanStore:
    image_dir: Path = field(default_factory=lambda: _configured_path("COMPONENT_SCAN_IMAGE_DIR", BACKEND_ROOT / "data" / "scans"))
    dataset_dir: Path = field(default_factory=lambda: _configured_path("COMPONENT_DATASET_DIR", REPO_ROOT / "dataset"))
    metadata_path: Path = field(default_factory=lambda: _configured_path("COMPONENT_SCAN_METADATA", BACKEND_ROOT / "data" / "scans.json"))
    max_history: int = 200
    _scans: list[ComponentScanResponse] | None = None
    _metadata_mtime: float | None = None

    def add_scan(
        self,
        scan: ComponentScanResponse,
        image_bytes: bytes,
        content_type: str,
        original_filename: str,
    ) -> ComponentScanResponse:
        self._reload()
        scan_id = uuid4().hex
        extension = self._extension(content_type, original_filename)
        image_path = self.image_dir / f"{scan_id}{extension}"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image_bytes)

        saved = scan.model_copy(update={"scan_id": scan_id, "saved_image_path": self._stored_path(image_path)})
        self._scans.insert(0, saved)
        self._scans = self._scans[: self.max_history]
        self._save()
        return saved

    def latest(self) -> ComponentScanResponse | None:
        self._read_metadata()
        return self._scans[0] if self._scans else None

    def list_scans(self, limit: int = 50) -> list[ComponentScanResponse]:
        self._read_metadata()
        return self._scans[:limit]

    def correct_scan(self, scan_id: str, component: str, save_to_dataset: bool = True) -> ComponentScanResponse:
        self._reload()
        normalized = " ".join(component.strip().split())
        if not normalized:
            raise ValueError("Component label cannot be empty.")
        known_component = normalized.lower() if normalized.lower() in SUPPORTED_COMPONENTS else None

        for index, scan in enumerate(self._scans):
            if scan.scan_id != scan_id:
                continue

            reviewed_path = self._move_to_reviewed(scan)
            updated = scan.model_copy(
                update={
                    "success": True,
                    "status": "component_detected",
                    "message": "Component label confirmed.",
                    "recommended_component": normalized,
                    "component_class": known_component or normalized,
                    "reviewed": True,
                    "corrected_component": normalized,
                    "saved_image_path": reviewed_path or scan.saved_image_path,
                }
            )
            if save_to_dataset and known_component:
                self._copy_to_dataset(updated)
            self._scans[index] = updated
            self._save()
            return updated

        raise KeyError(scan_id)

    def _move_to_reviewed(self, scan: ComponentScanResponse) -> str | None:
        if not scan.saved_image_path:
            return None

        source = self._resolved_saved_image_path(scan.saved_image_path)
        if not source.exists():
            return scan.saved_image_path

        reviewed_dir = self.image_dir / "reviewed"
        reviewed_dir.mkdir(parents=True, exist_ok=True)
        destination = reviewed_dir / source.name
        if source.resolve() != destination.resolve():
            if destination.exists():
                destination.unlink()
            shutil.move(str(source), str(destination))
        return self._stored_path(destination)

    def mark_added_to_inventory(self, scan_id: str) -> ComponentScanResponse:
        self._reload()
        for index, scan in enumerate(self._scans):
            if scan.scan_id == scan_id:
                updated = scan.model_copy(update={"added_to_inventory": True})
                self._scans[index] = updated
                self._save()
                return updated
        raise KeyError(scan_id)

    def get_scan(self, scan_id: str) -> ComponentScanResponse:
        self._reload()
        for scan in self._scans:
            if scan.scan_id == scan_id:
                return scan
        raise KeyError(scan_id)

    def _copy_to_dataset(self, scan: ComponentScanResponse) -> None:
        if not scan.saved_image_path or not scan.corrected_component:
            return

        source = self._resolved_saved_image_path(scan.saved_image_path)
        if not source.exists():
            return

        class_dir = self.dataset_dir / scan.corrected_component
        class_dir.mkdir(parents=True, exist_ok=True)
        destination = class_dir / f"{scan.scan_id}{source.suffix or '.jpg'}"
        shutil.copyfile(source, destination)

    def _extension(self, content_type: str, filename: str) -> str:
        if content_type in IMAGE_EXTENSIONS:
            return IMAGE_EXTENSIONS[content_type]
        suffix = Path(filename).suffix.lower()
        return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"

    def _load(self) -> None:
        if self._scans is not None:
            return
        self._read_metadata()

    def _reload(self) -> None:
        if self._metadata_changed():
            self._read_metadata()

    def _metadata_changed(self) -> bool:
        if self._scans is None:
            return True
        if not self.metadata_path.exists():
            return self._metadata_mtime is not None
        return self.metadata_path.stat().st_mtime != self._metadata_mtime

    def _read_metadata(self) -> None:
        if not self.metadata_path.exists():
            self._scans = []
            self._metadata_mtime = None
            return

        records = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self._scans = [ComponentScanResponse(**record) for record in records]
        self._metadata_mtime = self.metadata_path.stat().st_mtime

    def _save(self) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [scan.model_dump(mode="json") for scan in self._scans]
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._metadata_mtime = self.metadata_path.stat().st_mtime

    def _stored_path(self, image_path: Path) -> str:
        try:
            return image_path.relative_to(self.metadata_path.parent).as_posix()
        except ValueError:
            try:
                return image_path.relative_to(BACKEND_ROOT).as_posix()
            except ValueError:
                return image_path.name

    def _resolved_saved_image_path(self, saved_image_path: str) -> Path:
        path = Path(saved_image_path)
        if path.is_absolute():
            return path

        metadata_relative = self.metadata_path.parent / path
        if metadata_relative.exists():
            return metadata_relative

        return BACKEND_ROOT / path


def _configured_path(env_name: str, default: Path) -> Path:
    configured = os.getenv(env_name)
    if not configured:
        return default

    path = Path(configured)
    return path if path.is_absolute() else BACKEND_ROOT / path
