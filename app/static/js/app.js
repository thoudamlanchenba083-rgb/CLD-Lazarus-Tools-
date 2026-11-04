/**
 * app.js — V2 main visitor page logic.
 *
 * Orchestrates session creation, consent management, camera/location
 * permission requests, and the UI state transitions.
 */
const $ = (id) => document.getElementById(id);
let stream = null;

// ---------------------------------------------------------------------------
// Camera helpers
// ---------------------------------------------------------------------------
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    $("video").srcObject = stream;
    $("cameraBox").classList.remove("hidden");
    $("indCamera").classList.remove("hidden");
    $("indicators").classList.remove("hidden");
    return "granted";
  } catch (err) {
    $("consentStatus").textContent = `Camera permission: ${err.name || "denied"}.`;
    return "denied";
  }
}

function stopCamera() {
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null;
  $("video").srcObject = null;
  $("cameraBox").classList.add("hidden");
  $("indCamera").classList.add("hidden");
}
$("stopCamera").addEventListener("click", () => {
  stopCamera();
  $("consentCamera").checked = false;
  // Revoke camera consent on stop
  ConsentManager.revokeConsent("CAMERA").catch(() => {});
});

// ---------------------------------------------------------------------------
// Location helpers
// ---------------------------------------------------------------------------
function getLocation() {
  return new Promise(resolve => {
    if (!navigator.geolocation) return resolve({ permission: "unsupported" });
    navigator.geolocation.getCurrentPosition(
      p => resolve({ permission: "granted", latitude: p.coords.latitude,
        longitude: p.coords.longitude, accuracy: p.coords.accuracy }),
      e => resolve({ permission: e.code === 1 ? "denied" : "unavailable" }),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 30000 }
    );
  });
}

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
    // Hide start panel, show consent panel
    $("startPanel").classList.add("hidden");
    $("consentPanel").classList.remove("hidden");
  } catch (e) {
    $("startStatus").textContent = `Could not start session: ${e.message}`;
    $("start").disabled = false;
  }
});

// ---------------------------------------------------------------------------
// Consent toggles (Phase 4)
// ---------------------------------------------------------------------------
$("consentDevice").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      await ConsentManager.grantConsent("DEVICE_METADATA");
      // Send device metadata
      const payload = {
        user_agent: navigator.userAgent,
        language: navigator.language,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        screen_width: screen.width,
        screen_height: screen.height,
        online: navigator.onLine,
      };
      await fetch("/api/device", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": SessionManager.getSessionToken(),
          "X-Session-ID": SessionManager.getSessionUuid(),
        },
        body: JSON.stringify(payload),
      });
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

$("consentLocation").addEventListener("change", async function () {
  if (!SessionManager.isActive()) return;
  const status = $("consentStatus");
  try {
    if (this.checked) {
      await ConsentManager.grantConsent("LOCATION");
      status.textContent = "Requesting location…";
      const loc = await getLocation();
      if (loc.permission === "granted") {
        $("indLocation").classList.remove("hidden");
        $("indicators").classList.remove("hidden");
        status.textContent = "Location shared.";
      } else {
        await ConsentManager.revokeConsent("LOCATION");
        this.checked = false;
        status.textContent = `Location permission: ${loc.permission}.`;
      }
    } else {
      await ConsentManager.revokeConsent("LOCATION");
      $("indLocation").classList.add("hidden");
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
  $("indicators").classList.add("hidden");
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
  ConsentManager.clearAll();
  await SessionManager.endSession();
  $("consentPanel").classList.add("hidden");
  $("cameraBox").classList.add("hidden");
  $("startPanel").classList.remove("hidden");
  $("start").disabled = false;
  $("consent").checked = false;
  $("startStatus").textContent = "Session ended and data deletion requested.";
});
