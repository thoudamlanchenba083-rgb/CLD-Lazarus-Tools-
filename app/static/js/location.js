/**
 * location.js — Permission-based, bounded, stoppable location sharing.
 *
 * Implements:
 * - getCurrentPosition on start
 * - watchPosition with bounded send interval (e.g., minimum 30 seconds between updates)
 * - Maximum number of client updates per session
 * - clearWatch on Stop, revoke, or session end
 */
const LocationSharer = (function () {
  let watchId = null;
  let lastSentTime = 0;
  let updateCount = 0;
  const MIN_SEND_INTERVAL_MS = 30000; // 30 seconds
  const MAX_CLIENT_UPDATES = 30; // Max updates per session from client side

  function isSharing() {
    return watchId !== null;
  }

  async function sendLocationUpdate(latitude, longitude, accuracy) {
    const sessionUuid = SessionManager.getSessionUuid();
    const sessionToken = SessionManager.getSessionToken();
    if (!sessionUuid || !sessionToken) return;

    try {
      const res = await fetch("/api/location", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionUuid,
          "X-Session-Token": sessionToken,
        },
        body: JSON.stringify({
          latitude,
          longitude,
          accuracy: accuracy || null,
        }),
      });

      if (!res.ok) {
        if (res.status === 403 || res.status === 410) {
          // Consent revoked or session ended
          stopSharing();
        }
      }
    } catch (e) {
      console.warn("Location update failed:", e);
    }
  }

  function startSharing(onSuccess, onError) {
    if (!navigator.geolocation) {
      if (onError) onError(new Error("Geolocation unsupported"));
      return;
    }

    stopSharing();
    updateCount = 0;
    lastSentTime = 0;

    // First one-shot position call
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        lastSentTime = Date.now();
        updateCount++;
        await sendLocationUpdate(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
        if (onSuccess) onSuccess(pos);

        // Then start periodic/movement watchPosition with bounded interval
        watchId = navigator.geolocation.watchPosition(
          async (wPos) => {
            const now = Date.now();
            if (now - lastSentTime < MIN_SEND_INTERVAL_MS) {
              return; // throttle client-side
            }
            if (updateCount >= MAX_CLIENT_UPDATES) {
              stopSharing();
              return;
            }
            lastSentTime = now;
            updateCount++;
            await sendLocationUpdate(wPos.coords.latitude, wPos.coords.longitude, wPos.coords.accuracy);
            if (onSuccess) onSuccess(wPos);
          },
          (err) => {
            if (onError) onError(err);
          },
          { enableHighAccuracy: false, timeout: 15000, maximumAge: 30000 }
        );
      },
      (err) => {
        if (onError) onError(err);
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 30000 }
    );
  }

  function stopSharing() {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
  }

  return {
    startSharing,
    stopSharing,
    isSharing,
  };
})();
