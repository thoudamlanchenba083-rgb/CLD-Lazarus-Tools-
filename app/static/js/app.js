/**
 * app.js — V2 main visitor page logic.
 *
 * Orchestrates session creation, consent management, camera/location
 * permission requests, snapshot upload, and UI state transitions.
 */
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Camera helpers
// ---------------------------------------------------------------------------
async function startCamera() {
  if (typeof CameraManager !== "undefined") {
    const res = await CameraManager.startPreview($("video"));
    if (res === "granted") {
      $("cameraBox").classList.remove("hidden");
      $("indCamera").classList.remove("hidden");
      $("indicators").classList.remove("hidden");
      return "granted";
    } else {
      $("consentStatus").textContent = "Camera permission denied.";
      return "denied";
    }
  }
  return "denied";
}

function stopCamera() {
  if (typeof CameraManager !== "undefined") {
    CameraManager.stopPreview($("video"));
  }
  $("cameraBox").classList.add("hidden");
  $("indCamera").classList.add("hidden");
}

$("stopCamera").addEventListener("click", () => {
  stopCamera();
  $("consentCamera").checked = false;
  ConsentManager.revokeConsent("CAMERA").catch(() => {});
});

// ---------------------------------------------------------------------------
// Start button: create session (V2 flow)
// ---------------------------------------------------------------------------
$("start").addEventListener("click", async () => {
  if (!$("consent").checked) {
    $("startStatus").textContent = "Tick the consent checkbox first.";
    return;
  }
  $("start").disabled = true;
  $("startStatus").textContent = "Starting session…";

  try {
    await SessionManager.startSession();
    $("startStatus").textContent = "Session started. Use the toggles below to control sharing.";
    $("startPanel").classList.add("hidden");
    $("consentPanel").classList.remove("hidden");
  } catch (e) {
    $("startStatus").textContent = `Could not start session: ${e.message}`;
    $("start").disabled = false;
  }
});

// ---------------------------------------------------------------------------
// Consent toggles (Phase 4, 5, 6, 7)
// ---------------------------------------------------------------------------
$("consentDevice").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      const payload = typeof DeviceCollector !== "undefined"
        ? DeviceCollector.collect()
        : {
            user_agent: navigator.userAgent,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            screen_width: screen.width,
            screen_height: screen.height,
            online: navigator.onLine,
          };

      const summary = typeof DeviceCollector !== "undefined"
        ? DeviceCollector.getSummaryText(payload)
        : `UA: ${payload.user_agent}`;
      const confirmed = confirm(`The following browser metadata will be submitted:\n\n${summary}\n\nDo you want to proceed?`);
      if (!confirmed) {
        this.checked = false;
        return;
      }

      await ConsentManager.grantConsent("DEVICE_METADATA");

      const response = await fetch("/api/device", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": SessionManager.getSessionToken(),
          "X-Session-ID": SessionManager.getSessionUuid(),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Submission failed");
      }

      $("indDevice").classList.remove("hidden");
      $("indicators").classList.remove("hidden");
      status.textContent = "Device metadata shared.";
    } else {
      await ConsentManager.revokeConsent("DEVICE_METADATA");
      $("indDevice").classList.add("hidden");
      status.textContent = "Device metadata consent revoked.";
    }
  } catch (e) {
    status.textContent = `Device: ${e.message}`;
    this.checked = !this.checked;
  }
});

$("consentCamera").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      await ConsentManager.grantConsent("CAMERA");
      const perm = await startCamera();
      if (perm === "denied") {
        await ConsentManager.revokeConsent("CAMERA");
        this.checked = false;
      } else {
        status.textContent = "Camera preview active. Frames are not uploaded.";
      }
    } else {
      stopCamera();
      await ConsentManager.revokeConsent("CAMERA");
      status.textContent = "Camera consent revoked. Preview stopped.";
    }
  } catch (e) {
    status.textContent = `Camera: ${e.message}`;
    this.checked = !this.checked;
  }
});

$("consentSnapshot").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      const confirmed = confirm("Do you explicitly consent to uploading volunteer test snapshots? This is separate and optional.");
      if (!confirmed) {
        this.checked = false;
        return;
      }
      await ConsentManager.grantConsent("SNAPSHOT_UPLOAD");
      status.textContent = "Volunteer snapshot upload consent granted.";
    } else {
      await ConsentManager.revokeConsent("SNAPSHOT_UPLOAD");
      status.textContent = "Snapshot upload consent revoked.";
    }
  } catch (e) {
    status.textContent = `Snapshot consent: ${e.message}`;
    this.checked = !this.checked;
  }
});

$("captureSnapshotBtn").addEventListener("click", async () => {
  const status = $("cameraStatus");
  if (typeof CameraManager === "undefined" || !CameraManager.isStreaming()) {
    status.textContent = "Camera is not streaming.";
    return;
  }
  status.textContent = "Capturing snapshot...";
  try {
    const blob = await CameraManager.captureVolunteerSnapshot($("video"));
    status.textContent = "Uploading volunteer test snapshot...";
    const res = await CameraManager.uploadVolunteerSnapshot(blob);
    status.textContent = `Snapshot uploaded: ${res.filename} (${res.size_bytes} bytes). Auto-deleted in retention window.`;
  } catch (e) {
    status.textContent = `Capture/Upload failed: ${e.message}`;
  }
});

function stopLocationSharing() {
  if (typeof LocationSharer !== "undefined") {
    LocationSharer.stopSharing();
  }
  $("indLocation").classList.add("hidden");
  $("stopLocationBtn").classList.add("hidden");
}

$("stopLocationBtn").addEventListener("click", async () => {
  stopLocationSharing();
  $("consentLocation").checked = false;
  await ConsentManager.revokeConsent("LOCATION").catch(() => {});
  $("consentStatus").textContent = "Location sharing stopped and consent revoked.";
});

$("consentLocation").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      await ConsentManager.grantConsent("LOCATION");
      status.textContent = "Requesting location permission...";

      if (typeof LocationSharer !== "undefined") {
        LocationSharer.startSharing(
          (pos) => {
            $("indLocation").classList.remove("hidden");
            $("indicators").classList.remove("hidden");
            $("stopLocationBtn").classList.remove("hidden");
            status.textContent = `Location sharing: ON (±${Math.round(pos.coords.accuracy || 0)}m)`;
          },
          (err) => {
            stopLocationSharing();
            ConsentManager.revokeConsent("LOCATION").catch(() => {});
            this.checked = false;
            status.textContent = `Location denied or unavailable (${err.message}).`;
          }
        );
      }
    } else {
      stopLocationSharing();
      await ConsentManager.revokeConsent("LOCATION");
      status.textContent = "Location consent revoked. Sharing stopped.";
    }
  } catch (e) {
    status.textContent = `Location: ${e.message}`;
    this.checked = !this.checked;
  }
});

// ---------------------------------------------------------------------------
// End session
// ---------------------------------------------------------------------------
$("stopSession").addEventListener("click", async () => {
  stopCamera();
  stopLocationSharing();
  ConsentManager.clearAll();
  await SessionManager.endSession();
  $("consentPanel").classList.add("hidden");
  $("cameraBox").classList.add("hidden");
  $("startPanel").classList.remove("hidden");
  $("start").disabled = false;
  $("consent").checked = false;
  $("consentDevice").checked = false;
  $("consentCamera").checked = false;
  $("consentLocation").checked = false;
  $("consentSnapshot").checked = false;
  $("indicators").classList.add("hidden");
  $("stopLocationBtn").classList.add("hidden");
  $("startStatus").textContent = "Session ended. You can start a new one.";
});

// ---------------------------------------------------------------------------
// Delete my data (placeholder — full implementation in Phase 11)
// ---------------------------------------------------------------------------
$("deleteData").addEventListener("click", async () => {
  if (!SessionManager.isActive()) return;
  const confirmed = confirm("This will end your session and request deletion of all collected data. Continue?");
  if (!confirmed) return;
  stopCamera();
  stopLocationSharing();
  ConsentManager.clearAll();
  await SessionManager.endSession();
  $("consentPanel").classList.add("hidden");
  $("cameraBox").classList.add("hidden");
  $("startPanel").classList.remove("hidden");
  $("start").disabled = false;
  $("consent").checked = false;
  $("stopLocationBtn").classList.add("hidden");
  $("startStatus").textContent = "Session ended and data deletion requested.";
});
