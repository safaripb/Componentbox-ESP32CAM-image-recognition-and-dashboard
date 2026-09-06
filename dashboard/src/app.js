(function () {
  'use strict';

  angular.module('componentBoxApp', [])
    .controller('DashboardController', ['$timeout', '$document', '$http', function ($timeout, $document, $http) {
      var vm = this;
      var apiBaseUrl = getApiBaseUrl();
      var uploadInput = null;

      vm.view = 'grid';
      vm.search = '';
      vm.statusFilter = 'all';
      vm.componentFilter = 'all';
      vm.confidenceFilter = 'all';
      vm.reviewFilter = 'all';
      vm.sortOrder = '-capturedAt';
      vm.selectedScan = null;
      vm.scanResult = null;
      vm.latestScanSeenAt = null;
      vm.pendingUpload = false;
      vm.reviewDeckOpen = false;
      vm.reviewLabel = '';
      vm.reviewSaving = false;
      vm.reviewLeaving = false;
      vm.reviewComplete = false;
      vm.reviewDeckStarted = false;
      vm.toast = '';
      vm.apiOnline = false;
      vm.activeSection = 'overview';
      vm.todayLabel = new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase();
      vm.componentOptions = [
        { value: 'resistor', label: 'Resistor' },
        { value: 'capacitor', label: 'Capacitor' },
        { value: 'wire', label: 'Jumper wire' },
        { value: 'stepper_motor', label: 'Stepper motor' },
        { value: 'seven_segment', label: '7-segment display' }
      ];

      vm.scans = [];
      vm.demoScans = [
        scan(1, 'Resistor', 'resistor', 'Example resistor.jpg', 'Example', 6, 'component_detected', null, 'scan-yellow.svg'),
        scan(2, 'Capacitor', 'capacitor', 'Example capacitor.jpg', 'Example', 10, 'component_detected', null, 'scan-blue.svg'),
        scan(3, '', '', 'Example unknown.jpg', 'Example', 17, 'unknown', null, 'scan-dark.svg'),
        scan(4, 'Jumper wire', 'wire', 'Example jumper wire.jpg', 'Example', 1090, 'component_detected', null, 'scan-green.svg'),
        scan(5, 'Stepper motor', 'stepper_motor', 'Example stepper motor.jpg', 'Example', 1114, 'component_detected', null, 'scan-purple.svg'),
        scan(6, '7-segment display', 'seven_segment', 'Example display.jpg', 'Example', 2598, 'component_detected', null, 'scan-red.svg')
      ];

      function scan(id, value, component, filename, timeLabel, minutesAgo, status, confidence, image) {
        return { id: 'demo-' + id, value: value, component: component, valueNumber: confidence || 0, filename: filename, timeLabel: timeLabel,
          capturedAt: Date.now() - minutesAgo * 60000, status: status, confidence: confidence, bands: [],
          detectedBands: [], bandDetails: [], image: 'assets/scans/' + image, reviewed: false, addedToInventory: false,
          isDemo: true };
      }

      vm.displayedScans = function () {
        return vm.scans.length ? vm.scans : vm.demoScans;
      };

      vm.filteredScans = function () {
        var term = vm.search.toLowerCase().trim();
        return vm.displayedScans().filter(function (item) {
          var matchesStatus = vm.statusFilter === 'all' ||
            item.status === vm.statusFilter ||
            (vm.statusFilter === 'identified' && item.status === 'component_detected') ||
            (vm.statusFilter === 'review' && item.status === 'unknown');
          var searchable = (item.value + ' ' + item.filename + ' ' + (item.component || '')).toLowerCase();
          var matchesTerm = !term || searchable.indexOf(term) !== -1;
          var matchesComponent = vm.componentFilter === 'all' || item.component === vm.componentFilter;
          var matchesConfidence = confidenceMatches(item);
          var matchesReview = vm.reviewFilter === 'all' ||
            (vm.reviewFilter === 'reviewed' && item.reviewed) ||
            (vm.reviewFilter === 'unreviewed' && !item.reviewed);
          return matchesStatus && matchesTerm && matchesComponent && matchesConfidence && matchesReview;
        });
      };

      vm.countByStatus = function (status) {
        return vm.scans.filter(function (item) {
          if (status === 'identified') return item.status === 'identified' || item.status === 'component_detected';
          if (status === 'review') return item.status === 'review' || item.status === 'unknown';
          return item.status === status;
        }).length;
      };

      vm.identificationRate = function () {
        if (!vm.scans.length) return 0;
        return Math.round(vm.countByStatus('identified') / vm.scans.length * 100);
      };

      vm.openScan = function (item) { item.menuOpen = false; vm.selectedScan = item; };
      vm.statusLabel = statusLabel;
      vm.displayComponent = displayComponent;
      vm.closeModal = function (event) { if (event.target === event.currentTarget) vm.selectedScan = null; };
      vm.correctScan = correctScan;
      vm.addToInventory = addToInventory;
      vm.goTo = function (sectionId) {
        var section = document.getElementById(sectionId);
        vm.activeSection = sectionId;
        vm.mobileMenuOpen = false;
        if (section) section.scrollIntoView({behavior: 'smooth', block: 'start'});
      };

      vm.unreviewedScans = function () {
        return vm.displayedScans().filter(function (item) { return !item.reviewed; });
      };

      vm.reviewedScans = function () {
        return vm.displayedScans().filter(function (item) { return item.reviewed; });
      };

      vm.currentReview = function () { return vm.unreviewedScans()[0] || null; };
      vm.openReviewDeck = openReviewDeck;
      vm.closeReviewDeck = function () {
        vm.reviewDeckOpen = false;
        vm.reviewComplete = false;
      };
      vm.chooseReviewLabel = function (component) { vm.reviewLabel = component; };
      vm.confirmReview = confirmReview;
      vm.clearFilters = function () {
        vm.search = '';
        vm.statusFilter = 'all';
        vm.componentFilter = 'all';
        vm.confidenceFilter = 'all';
        vm.reviewFilter = 'all';
      };
      vm.startScan = function () {
        if (uploadInput) uploadInput.click();
      };

      vm.uploadScan = function (file) {
        if (!file || vm.pendingUpload) return;

        var previewUrl = URL.createObjectURL(file);
        var formData = new FormData();
        formData.append('image', file);

        vm.pendingUpload = true;
        vm.scanResult = {
          status: 'processing',
          message: 'Classifying component...',
          image: previewUrl,
          filename: file.name,
          bands: [],
          bandDetails: []
        };

        $http.post(apiBaseUrl + '/api/component-scans', formData, {
          transformRequest: angular.identity,
          headers: { 'Content-Type': undefined }
        }).then(function (response) {
          vm.apiOnline = true;
          var result = normalizeScanResponse(response.data, file.name, previewUrl);
          vm.scanResult = result;
          addScanIfNew(result);
          if (!result.reviewed) openReviewDeck(result);
          showToast(result.success ? 'Component detected' : statusLabel(result.status));
        }).catch(function (error) {
          vm.apiOnline = false;
          vm.scanResult = {
            status: 'error',
            message: apiErrorMessage(error),
            image: previewUrl,
            filename: file.name,
            bands: [],
            bandDetails: []
          };
          showToast('Scan was not accepted');
        }).finally(function () {
          vm.pendingUpload = false;
          if (uploadInput) uploadInput.value = '';
        });
      };

      vm.bandStyle = function (band) {
        return { background: band.hex || band };
      };

      function showToast(message) {
        vm.toast = message;
        $timeout(function () { vm.toast = ''; }, 2800);
      }

      function getApiBaseUrl() {
        var configured = window.COMPONENTBOX_API_URL;
        try {
          configured = configured || window.localStorage.getItem('COMPONENTBOX_API_URL');
        } catch (error) {
          configured = configured || '';
        }
        return (configured || 'http://localhost:8000').replace(/\/$/, '');
      }

      function normalizeScanResponse(data, filename, imageUrl) {
        var bandDetails = data.band_details || [];
        var component = data.recommended_component || data.component_class || '';
        var formatted = component ? displayComponent(component) : '';
        var capturedAt = data.captured_at ? Date.parse(data.captured_at) : Date.now();
        var confidence = typeof data.confidence === 'number' ? Math.round(data.confidence * 100) : null;
        return {
          id: data.scan_id || data.captured_at || Date.now(),
          value: formatted,
          component: component,
          valueNumber: confidence || 0,
          tolerance: data.tolerance || '',
          filename: data.filename || filename || 'esp32-cam.jpg',
          timeLabel: formatTimeLabel(data.captured_at),
          capturedAt: capturedAt,
          capturedAtRaw: data.captured_at,
          status: data.status || (data.success ? 'component_detected' : 'unknown'),
          success: !!data.success,
          message: data.message,
          confidence: confidence,
          bands: bandDetails.length ? bandDetails.map(function (band) { return band.hex; }) : [],
          bandDetails: bandDetails,
          detectedBands: [],
          image: data.image_data_url || imageUrl,
          resistorCount: data.resistor_count,
          modelVersion: data.model_version,
          scanId: data.scan_id,
          reviewed: !!data.reviewed,
          correctedComponent: data.corrected_component,
          addedToInventory: !!data.added_to_inventory
        };
      }

      function addScanIfNew(result) {
        var existing = vm.scans.some(function (scanItem) { return scanItem.id === result.id; });
        if (!existing) vm.scans.unshift(result);
      }

      function pollLatestScan() {
        $http.get(apiBaseUrl + '/api/component-scans/latest').then(function (response) {
          vm.apiOnline = true;
          if (!response.data || !response.data.scan || !response.data.scan.captured_at) return;
          if (response.data.scan.captured_at === vm.latestScanSeenAt) return;

          var latest = normalizeScanResponse(response.data.scan, response.data.scan.filename, response.data.scan.image_data_url);
          vm.latestScanSeenAt = response.data.scan.captured_at;
          vm.scanResult = latest;
          replaceScan(latest);
          if (!latest.reviewed) openReviewDeck(latest);
        }).catch(function () {
          vm.apiOnline = false;
        }).finally(function () {
          $timeout(pollLatestScan, 3500);
        });
      }

      function loadScanHistory() {
        $http.get(apiBaseUrl + '/api/component-scans').then(function (response) {
          vm.apiOnline = true;
          if (!response.data || !response.data.scans) return;
          vm.scans = response.data.scans.map(function (scanData) {
            return normalizeScanResponse(scanData, scanData.filename, scanData.image_data_url);
          }).sort(function (a, b) {
            return b.capturedAt - a.capturedAt;
          });
          if (vm.selectedScan) {
            vm.selectedScan = vm.scans.find(function (scan) { return scan.id === vm.selectedScan.id; }) || vm.selectedScan;
          }
          if (vm.scans.length) {
            vm.scanResult = vm.scans[0];
            vm.latestScanSeenAt = vm.scans[0].capturedAtRaw;
          }
          if (!vm.reviewDeckStarted && vm.unreviewedScans().length) {
            vm.reviewDeckStarted = true;
            openReviewDeck();
          }
        }).catch(function () {
          vm.apiOnline = false;
        }).finally(function () {
          $timeout(loadScanHistory, 4000);
        });
      }

      function statusLabel(status) {
        if (status === 'component_detected' || status === 'identified') return 'Component detected';
        if (status === 'unknown') return 'Unknown component';
        if (status === 'processing') return 'Processing';
        if (status === 'error') return 'Error';
        return 'Needs review';
      }

      function confidenceMatches(item) {
        if (vm.confidenceFilter === 'all') return true;
        if (item.confidence === null || item.confidence === undefined) return false;
        if (vm.confidenceFilter === 'high') return item.confidence >= 85;
        if (vm.confidenceFilter === 'medium') return item.confidence >= 60 && item.confidence < 85;
        if (vm.confidenceFilter === 'low') return item.confidence < 60;
        return true;
      }

      function correctScan(item, component) {
        if (!component) return Promise.reject();
        if (!item.scanId) {
          applyCorrection(item, component);
          showToast('Demo scan label updated');
          return Promise.resolve(item);
        }

        return $http.patch(apiBaseUrl + '/api/component-scans/' + item.scanId + '/correction', {
          component: component,
          save_to_dataset: true
        }).then(function (response) {
          var updated = normalizeScanResponse(response.data, item.filename, item.image);
          replaceScan(updated);
          vm.scanResult = updated;
          vm.selectedScan = updated;
          showToast('Label saved for training');
        }).catch(function (error) {
          showToast(apiErrorMessage(error));
          throw error;
        });
      }

      function openReviewDeck(item) {
        if (!vm.unreviewedScans().length) return;
        vm.reviewDeckOpen = true;
        vm.reviewComplete = false;
        vm.reviewLeaving = false;
        vm.reviewDeckStarted = true;
        vm.reviewLabel = (item || vm.currentReview()).component || '';
      }

      function confirmReview() {
        var item = vm.currentReview();
        var label = (vm.reviewLabel || '').trim();
        if (!item || vm.reviewSaving) return;
        if (!label) {
          showToast('Enter or choose the correct component name');
          return;
        }

        vm.reviewSaving = true;
        correctScan(item, label).then(function () {
          vm.reviewLeaving = true;
          $timeout(function () {
            vm.reviewLeaving = false;
            vm.reviewSaving = false;
            if (vm.unreviewedScans().length) {
              vm.reviewLabel = vm.currentReview().component || '';
            } else {
              vm.reviewComplete = true;
              vm.reviewLabel = '';
            }
          }, 360);
        }).catch(function () {
          vm.reviewSaving = false;
        });
      }

      function addToInventory(item) {
        if (!item.scanId) {
          item.addedToInventory = true;
          showToast('Demo component added to inventory');
          return;
        }

        $http.post(apiBaseUrl + '/api/inventory/components', {
          scan_id: item.scanId,
          quantity: 1,
          box: 'Unsorted'
        }).then(function () {
          item.addedToInventory = true;
          showToast('Component added to inventory');
        }).catch(function (error) {
          showToast(apiErrorMessage(error));
        });
      }

      function applyCorrection(item, component) {
        item.component = component;
        item.value = displayComponent(component);
        item.status = 'component_detected';
        item.success = true;
        item.reviewed = true;
        item.correctedComponent = component;
      }

      function replaceScan(updated) {
        var replaced = false;
        vm.scans = vm.scans.map(function (scanItem) {
          if (scanItem.id === updated.id) {
            replaced = true;
            return updated;
          }
          return scanItem;
        });
        if (!replaced) vm.scans.unshift(updated);
        vm.scans.sort(function (a, b) { return b.capturedAt - a.capturedAt; });
      }

      function displayComponent(component) {
        var labels = {
          resistor: 'Resistor',
          capacitor: 'Capacitor',
          wire: 'Jumper wire',
          stepper_motor: 'Stepper motor',
          seven_segment: '7-segment display'
        };
        return labels[component] || component;
      }

      function formatTimeLabel(capturedAt) {
        if (!capturedAt) return 'Just now';
        var date = new Date(capturedAt);
        if (Number.isNaN(date.getTime())) return 'Just now';
        return date.toLocaleString([], {
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit'
        });
      }

      function apiErrorMessage(error) {
        if (error.status === 429 && error.data && error.data.detail) return error.data.detail;
        if (error.data && error.data.detail) return error.data.detail;
        return 'Could not reach the component recognition API. Check that the backend is running.';
      }

      $timeout(function () {
        uploadInput = document.getElementById('scan-upload');
        if (!uploadInput) return;
        uploadInput.addEventListener('change', function (event) {
          var file = event.target.files && event.target.files[0];
          if (file) {
            $timeout(function () { vm.uploadScan(file); });
          }
        });
      });

      loadScanHistory();
      pollLatestScan();

      $document.on('keydown', function (event) {
        if (event.key === 'Escape') { vm.selectedScan = null; vm.closeReviewDeck(); vm.scans.forEach(function (item) { item.menuOpen = false; }); }
        if (event.key === '/' && event.target.tagName !== 'INPUT') {
          event.preventDefault();
          var input = document.querySelector('.search-box input');
          if (input) input.focus();
        }
      });
    }]);
})();
