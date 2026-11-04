/**
 * camera.js — Camera local preview, event logging, and optional test snapshot upload.
 *
 * Principles:
 * - Local preview only. Camera frames are NOT uploaded or saved.
 * - Always stop all tracks (track.stop()) on Stop, revoke, or page close.
 * - Snapshot upload is only available with separate explicit SNAPSHOT_UPLOAD consent.
 */
const CameraManager = (function () {
  let stream = null;

  function isStreaming() {
    return stream !== null;
  }

  async function logCameraEvent(eventType) {
    const sessionUuid = SessionManager.getSessionUuid();
    const sessionToken = SessionManager.getSessionToken();
    if (!sessionUuid || !sessionToken) return;

    try {
      await fetch("/api/camera/events", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionUuid,
          "X-Session-Token": sessionToken,
        },
        body: JSON.stringify({ event_type: eventType }),
      });
    } catch (e) {
      console.warn("Failed to log camera event:", e);
    }
  }

  async function startPreview(videoElement) {
    stopPreview();
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      if (videoElement) {
        videoElement.srcObject = stream;
      }
      await logCameraEvent("PERMISSION_GRANTED");
      await logCameraEvent("PREVIEW_STARTED");
      return "granted";
    } catch (err) {
      await logCameraEvent("PERMISSION_DENIED");
      return "denied";
    }
  }

  async function stopPreview(videoElement) {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
      if (videoElement) {
        videoElement.srcObject = null;
      }
      await logCameraEvent("PREVIEW_STOPPED");
    }
  }

  async function captureVolunteerSnapshot(videoElement) {
    if (!stream || !videoElement) {
      throw new Error("Camera stream is not active.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = videoElement.videoWidth || 640;
    canvas.height = videoElement.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    await logCameraEvent("SNAPSHOT_CAPTURED");

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.85);
    });
  }

  async function uploadVolunteerSnapshot(blob) {
    const sessionUuid = SessionManager.getSessionUuid();
    const sessionToken = SessionManager.getSessionToken();
    if (!sessionUuid || !sessionToken) throw new Error("No active session.");

    const formData = new FormData();
    formData.append("file", blob, "volunteer_test.jpg");

    const res = await fetch("/api/camera/snapshot", {
      method: "POST",
      headers: {
        "X-Session-ID": sessionUuid,
        "X-Session-Token": sessionToken,
      },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }
    return await res.json();
  }

  return {
    startPreview,
    stopPreview,
    isStreaming,
    captureVolunteerSnapshot,
    uploadVolunteerSnapshot,
    logCameraEvent,
  };
})();
