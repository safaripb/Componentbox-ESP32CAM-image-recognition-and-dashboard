$ErrorActionPreference = "Stop"

$repo = "C:\Users\Parnia\downloads\componentbox"
Set-Location $repo

@'
from pathlib import Path

root = Path(r"C:\Users\Parnia\downloads\componentbox")

def replace_once(relative, old, new):
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text was not found in {relative}. The file may have changed.")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"Updated {relative}")

# 1) Make GitHub Actions import the backend package reliably.
replace_once(
    ".github/workflows/tests.yml",
    """      - name: Run backend tests
        working-directory: backend
        run: pytest
""",
    """      - name: Run backend tests
        working-directory: backend
        env:
          PYTHONPATH: .
        run: python -m pytest
"""
)

# 2) Store new scans under scans/unreviewed.
replace_once(
    "backend/app/services/component_scan_store.py",
    """        image_path = self.image_dir / f"{scan_id}{extension}"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image_bytes)

        saved = scan.model_copy(update={"scan_id": scan_id, "saved_image_path": self._stored_path(image_path)})
""",
    """        unreviewed_dir = self.image_dir / "unreviewed"
        image_path = unreviewed_dir / f"{scan_id}{extension}"
        unreviewed_dir.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image_bytes)

        saved = scan.model_copy(
            update={
                "scan_id": scan_id,
                "saved_image_path": self._stored_path(image_path),
                "reviewed": False,
            }
        )
"""
)

# 3) Let a review confirm/correct a known label or save a custom label,
#    and move the actual image into scans/reviewed.
replace_once(
    "backend/app/services/component_scan_store.py",
    """    def correct_scan(self, scan_id: str, component: str, save_to_dataset: bool = True) -> ComponentScanResponse:
        self._reload()
        normalized = component.strip().lower()
        if normalized not in SUPPORTED_COMPONENTS:
            raise ValueError(f"Unsupported component '{component}'.")

        for index, scan in enumerate(self._scans):
            if scan.scan_id != scan_id:
                continue

            updated = scan.model_copy(
                update={
                    "success": True,
                    "status": "component_detected",
                    "message": "Component label confirmed.",
                    "recommended_component": normalized,
                    "component_class": normalized,
                    "reviewed": True,
                    "corrected_component": normalized,
                }
            )
            if save_to_dataset and scan.saved_image_path:
                self._copy_to_dataset(updated)
            self._scans[index] = updated
            self._save()
            return updated

        raise KeyError(scan_id)
""",
    """    def correct_scan(self, scan_id: str, component: str, save_to_dataset: bool = True) -> ComponentScanResponse:
        self._reload()
        normalized = self._normalize_label(component)

        for index, scan in enumerate(self._scans):
            if scan.scan_id != scan_id:
                continue

            current_label = (scan.corrected_component or scan.recommended_component or "").strip().lower()
            reviewed_path = self._move_to_reviewed(scan)
            updated = scan.model_copy(
                update={
                    "success": True,
                    "status": "component_detected",
                    "message": "Component label confirmed." if current_label == normalized else "Component label corrected.",
                    "recommended_component": normalized,
                    "component_class": normalized,
                    "reviewed": True,
                    "corrected_component": normalized,
                    "saved_image_path": reviewed_path or scan.saved_image_path,
                }
            )

            # Known classifier labels can become training data. A custom label is
            # still kept as a reviewed scan, but is not silently added as a new
            # classifier class.
            if save_to_dataset and normalized in SUPPORTED_COMPONENTS:
                self._copy_to_dataset(updated)

            self._scans[index] = updated
            self._save()
            return updated

        raise KeyError(scan_id)
"""
)

replace_once(
    "backend/app/services/component_scan_store.py",
    """    def _copy_to_dataset(self, scan: ComponentScanResponse) -> None:
""",
    """    def _move_to_reviewed(self, scan: ComponentScanResponse) -> str | None:
        if not scan.saved_image_path:
            return None

        source = self._resolved_saved_image_path(scan.saved_image_path)
        if not source.exists():
            return scan.saved_image_path

        reviewed_dir = self.image_dir / "reviewed"
        reviewed_dir.mkdir(parents=True, exist_ok=True)
        destination = reviewed_dir / source.name

        try:
            same_path = source.resolve() == destination.resolve()
        except OSError:
            same_path = source == destination

        if not same_path:
            if destination.exists():
                destination.unlink()
            shutil.move(str(source), str(destination))

        return self._stored_path(destination)

    def _normalize_label(self, component: str) -> str:
        normalized = " ".join(component.strip().lower().split())
        if not normalized:
            raise ValueError("Component label cannot be empty.")
        if len(normalized) > 80:
            raise ValueError("Component label must be 80 characters or fewer.")
        return normalized

    def _copy_to_dataset(self, scan: ComponentScanResponse) -> None:
"""
)

# 4) Dashboard defaults to the unreviewed queue.
replace_once(
    "dashboard/src/app.js",
    """      vm.reviewFilter = 'all';
""",
    """      vm.reviewFilter = 'unreviewed';
"""
)

replace_once(
    "dashboard/src/app.js",
    """      vm.toast = '';
      vm.apiOnline = false;
""",
    """      vm.toast = '';
      vm.customLabel = '';
      vm.apiOnline = false;
"""
)

replace_once(
    "dashboard/src/app.js",
    """      vm.identificationRate = function () {
        if (!vm.scans.length) return 0;
        return Math.round(vm.countByStatus('identified') / vm.scans.length * 100);
      };

      vm.openScan = function (item) { item.menuOpen = false; vm.selectedScan = item; };
""",
    """      vm.identificationRate = function () {
        if (!vm.scans.length) return 0;
        return Math.round(vm.countByStatus('identified') / vm.scans.length * 100);
      };

      vm.countByReview = function (reviewed) {
        return vm.scans.filter(function (item) { return !!item.reviewed === reviewed; }).length;
      };

      vm.openScan = function (item) {
        item.menuOpen = false;
        vm.customLabel = '';
        vm.selectedScan = item;
      };
"""
)

replace_once(
    "dashboard/src/app.js",
    """      vm.correctScan = correctScan;
      vm.addToInventory = addToInventory;
""",
    """      vm.correctScan = correctScan;
      vm.confirmScan = confirmScan;
      vm.saveCustomLabel = saveCustomLabel;
      vm.addToInventory = addToInventory;
"""
)

replace_once(
    "dashboard/src/app.js",
    """      vm.goTo = function (sectionId) {
        var section = document.getElementById(sectionId);
        vm.activeSection = sectionId;
        vm.mobileMenuOpen = false;
        if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
      };
""",
    """      vm.goTo = function (sectionId) {
        var section = document.getElementById(sectionId);
        vm.activeSection = sectionId;
        vm.mobileMenuOpen = false;
        if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
      };
      vm.showReviewState = function (state) {
        vm.reviewFilter = state;
        vm.goTo('scan-gallery');
      };
"""
)

replace_once(
    "dashboard/src/app.js",
    """      function correctScan(item, component) {
""",
    """      function confirmScan(item) {
        if (!item || !item.component) {
          showToast('Choose a label before confirming this scan');
          return;
        }
        correctScan(item, item.component);
      }

      function saveCustomLabel(item) {
        var label = (vm.customLabel || '').trim();
        if (!label) {
          showToast('Enter a label first');
          return;
        }
        correctScan(item, label);
      }

      function correctScan(item, component) {
"""
)

replace_once(
    "dashboard/src/app.js",
    """        if (!item.scanId) {
          applyCorrection(item, component);
          showToast('Demo scan label updated');
          return;
        }
""",
    """        if (!item.scanId) {
          applyCorrection(item, component);
          vm.reviewFilter = 'reviewed';
          vm.customLabel = '';
          showToast('Demo scan reviewed');
          return;
        }
"""
)

replace_once(
    "dashboard/src/app.js",
    """          vm.scanResult = updated;
          vm.selectedScan = updated;
          showToast('Label saved for training');
""",
    """          vm.scanResult = updated;
          vm.selectedScan = updated;
          vm.reviewFilter = 'reviewed';
          vm.customLabel = '';
          showToast('Scan reviewed and moved to Reviewed');
"""
)

# 5) Dashboard navigation and statistics: explicit Review Queue and Reviewed sections.
replace_once(
    "dashboard/index.html",
    """        <button class="nav-item" ng-class="{active: vm.activeSection === 'scan-gallery'}" ng-click="vm.goTo('scan-gallery')"><span class="nav-icon">▧</span>Scan gallery <span class="nav-count">{{vm.scans.length}}</span></button>
        <button class="nav-item" ng-click="vm.startScan()"><span class="nav-icon">◎</span>Upload a scan</button>
""",
    """        <button class="nav-item" ng-class="{active: vm.activeSection === 'scan-gallery' && vm.reviewFilter === 'unreviewed'}" ng-click="vm.showReviewState('unreviewed')"><span class="nav-icon">!</span>Review queue <span class="nav-count">{{vm.countByReview(false)}}</span></button>
        <button class="nav-item" ng-class="{active: vm.activeSection === 'scan-gallery' && vm.reviewFilter === 'reviewed'}" ng-click="vm.showReviewState('reviewed')"><span class="nav-icon">✓</span>Reviewed <span class="nav-count">{{vm.countByReview(true)}}</span></button>
        <button class="nav-item" ng-click="vm.startScan()"><span class="nav-icon">◎</span>Upload a scan</button>
"""
)

replace_once(
    "dashboard/index.html",
    """          <article class="stat-card">
            <div class="stat-icon yellow">✓</div>
            <div><p>Identified</p><strong>{{vm.countByStatus('identified')}}</strong><small>{{vm.identificationRate()}}% success rate</small></div>
          </article>
          <article class="stat-card">
            <div class="stat-icon coral">!</div>
            <div><p>Unknown</p><strong>{{vm.countByStatus('review')}}</strong><small>Collect more training images</small></div>
          </article>
""",
    """          <article class="stat-card">
            <div class="stat-icon yellow">✓</div>
            <div><p>Reviewed</p><strong>{{vm.countByReview(true)}}</strong><small>Confirmed or corrected by a person</small></div>
          </article>
          <article class="stat-card">
            <div class="stat-icon coral">!</div>
            <div><p>Needs review</p><strong>{{vm.countByReview(false)}}</strong><small>Waiting for label confirmation</small></div>
          </article>
"""
)

replace_once(
    "dashboard/index.html",
    """              <h2>Recent captures</h2>
              <p>{{vm.scans.length ? vm.filteredScans().length + ' backend images shown' : 'Example images shown until backend scans arrive'}}</p>
""",
    """              <h2>{{vm.reviewFilter === 'reviewed' ? 'Reviewed scans' : (vm.reviewFilter === 'unreviewed' ? 'Review queue' : 'Recent captures')}}</h2>
              <p ng-if="vm.reviewFilter === 'unreviewed'">Confirm the suggested label, correct it, or enter a custom label.</p>
              <p ng-if="vm.reviewFilter === 'reviewed'">Scans that have already been confirmed or corrected.</p>
              <p ng-if="vm.reviewFilter === 'all'">{{vm.scans.length ? vm.filteredScans().length + ' backend images shown' : 'Example images shown until backend scans arrive'}}</p>
"""
)

replace_once(
    "dashboard/index.html",
    """        <div class="correction-panel">
          <span>Correct label</span>
          <div>
            <button ng-repeat="component in vm.componentOptions" ng-click="vm.correctScan(vm.selectedScan, component.value)">
              {{component.label}}
            </button>
          </div>
        </div>
        <button class="primary-button full" ng-if="vm.selectedScan.success && !vm.selectedScan.addedToInventory" ng-click="vm.addToInventory(vm.selectedScan)">Add to inventory</button>
""",
    """        <div class="correction-panel">
          <span>{{vm.selectedScan.reviewed ? 'Update reviewed label' : 'Review this scan'}}</span>
          <div ng-if="!vm.selectedScan.reviewed && vm.selectedScan.component">
            <button ng-click="vm.confirmScan(vm.selectedScan)">✓ Confirm {{vm.selectedScan.value}}</button>
          </div>
          <div>
            <button ng-repeat="component in vm.componentOptions" ng-click="vm.correctScan(vm.selectedScan, component.value)">
              {{component.label}}
            </button>
          </div>
          <div style="display:flex;gap:8px;margin-top:10px;align-items:center;">
            <input type="text" ng-model="vm.customLabel" maxlength="80" placeholder="Or enter a custom label"
              style="min-width:0;flex:1;padding:9px 10px;border:1px solid #e4dacb;border-radius:8px;background:#fffaf2;">
            <button ng-click="vm.saveCustomLabel(vm.selectedScan)">Save label</button>
          </div>
          <small style="display:block;margin-top:8px;color:#8d918b;line-height:1.4;">
            Known component labels can be saved to the training dataset. Custom labels stay in reviewed storage but are not added as unsupported classifier classes.
          </small>
        </div>
        <button class="primary-button full" ng-if="vm.selectedScan.reviewed && vm.selectedScan.success && !vm.selectedScan.addedToInventory" ng-click="vm.addToInventory(vm.selectedScan)">Add to inventory</button>
"""
)

# 6) Expand backend tests for the new storage/review behavior.
replace_once(
    "backend/tests/test_resistor_scans_api.py",
    """    assert payload["scan_id"]
    assert payload["saved_image_path"]
""",
    """    assert payload["scan_id"]
    assert payload["saved_image_path"]
    assert "unreviewed" in payload["saved_image_path"]
"""
)

replace_once(
    "backend/tests/test_resistor_scans_api.py",
    """    scan_id = scan_response.json()["scan_id"]
    response = client.patch(
""",
    """    scan_id = scan_response.json()["scan_id"]
    unreviewed_path = components.scan_store._resolved_saved_image_path(scan_response.json()["saved_image_path"])
    assert unreviewed_path.exists()
    assert "unreviewed" in scan_response.json()["saved_image_path"]

    response = client.patch(
"""
)

replace_once(
    "backend/tests/test_resistor_scans_api.py",
    """    assert payload["corrected_component"] == "capacitor"
    assert payload["recommended_component"] == "capacitor"
    assert list((components.scan_store.dataset_dir / "capacitor").glob("*.jpg"))


def test_component_scan_can_be_added_to_inventory(monkeypatch):
""",
    """    assert payload["corrected_component"] == "capacitor"
    assert payload["recommended_component"] == "capacitor"
    assert "reviewed" in payload["saved_image_path"]
    assert not unreviewed_path.exists()
    assert components.scan_store._resolved_saved_image_path(payload["saved_image_path"]).exists()
    assert list((components.scan_store.dataset_dir / "capacitor").glob("*.jpg"))


def test_component_scan_accepts_custom_review_label_without_training_folder(monkeypatch):
    monkeypatch.setattr(components, "rate_limiter", AcceptingLimiter())
    monkeypatch.setattr(components, "classifier", UnknownClassifier())
    client = TestClient(app)

    scan_response = client.post(
        "/api/component-scans",
        files={"image": ("mystery.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    scan_id = scan_response.json()["scan_id"]
    response = client.patch(
        f"/api/component-scans/{scan_id}/correction",
        json={"component": "microcontroller board", "save_to_dataset": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewed"] is True
    assert payload["corrected_component"] == "microcontroller board"
    assert "reviewed" in payload["saved_image_path"]
    assert not (components.scan_store.dataset_dir / "microcontroller board").exists()


def test_component_scan_can_be_added_to_inventory(monkeypatch):
"""
)

print("\nAll requested files updated. README files were not touched.")
'@ | python -

Write-Host ""
Write-Host "Running backend tests..." -ForegroundColor Cyan
Push-Location backend
$env:PYTHONPATH = "."
python -m pytest
Pop-Location

Write-Host ""
Write-Host "Running dashboard JavaScript check..." -ForegroundColor Cyan
Push-Location dashboard
npm run check
Pop-Location

Write-Host ""
Write-Host "Changes ready. Review them with: git diff" -ForegroundColor Green
Write-Host "Then commit with:" -ForegroundColor Green
Write-Host 'git add .github/workflows/tests.yml backend/app/services/component_scan_store.py backend/tests/test_resistor_scans_api.py dashboard/src/app.js dashboard/index.html'
Write-Host 'git commit -m "Add reviewed scan workflow"'
Write-Host 'git push'
