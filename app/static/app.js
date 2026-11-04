const $ = (id) => document.getElementById(id);
let stream = null;

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    $("video").srcObject = stream;
    $("cameraBox").classList.remove("hidden");
    return "granted";
  } catch (err) {
    $("status").textContent = `Camera permission: ${err.name || "denied"}.`;
    return "denied";
  }
}
function stopCamera() {
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null;
  $("video").srcObject = null;
  $("cameraBox").classList.add("hidden");
}
$("stopCamera").addEventListener("click", stopCamera);

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

$("start").addEventListener("click", async () => {
  if (!$("consent").checked) {
    $("status").textContent = "Tick the consent checkbox first.";
    return;
  }
  $("start").disabled = true;
  $("status").textContent = "Waiting for the permissions you selected…";
  let cameraPermission = "not_requested";
  let loc = { permission: "not_requested" };

  if ($("camera").checked) cameraPermission = await startCamera();
  if ($("location").checked) loc = await getLocation();

  const metadata = $("metadata").checked;
  const payload = {
    consent: true,
    user_agent: metadata ? navigator.userAgent : "",
    platform: metadata ? (navigator.userAgentData?.platform || navigator.platform || "") : "",
    language: metadata ? navigator.language : "",
    screen_width: metadata ? screen.width : null,
    screen_height: metadata ? screen.height : null,
    camera_permission: cameraPermission,
    location_permission: loc.permission,
    latitude: loc.latitude ?? null,
    longitude: loc.longitude ?? null,
    accuracy: loc.accuracy ?? null
  };

  try {
    const response = await fetch("/api/session", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error((await response.json()).detail || "Save failed");
    $("status").textContent = "Your selected information was submitted. You can stop the camera preview at any time.";
  } catch (e) {
    $("status").textContent = `Could not save session: ${e.message}`;
  } finally {
    $("start").disabled = false;
  }
});
