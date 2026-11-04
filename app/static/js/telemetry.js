/**
 * telemetry.js — Batched visitor event pipeline.
 *
 * Queues non-critical events and sends them together every 10-15 seconds (and on page hide),
 * while sending critical events immediately.
 */
const TelemetryPipeline = (function () {
  let queue = [];
  let flushTimer = null;
  const FLUSH_INTERVAL_MS = 12000; // 12 seconds

  function init() {
    if (!flushTimer) {
      flushTimer = setInterval(flush, FLUSH_INTERVAL_MS);
    }
    window.addEventListener("pagehide", flushBeacon);
  }

  function queueEvent(eventType, metadata = {}) {
    queue.push({
      event_type: eventType,
      metadata: metadata,
      timestamp: new Date().toISOString(),
    });
  }

  async function sendImmediate(eventType, metadata = {}) {
    // Add to batch and flush immediately
    queueEvent(eventType, metadata);
    await flush();
  }

  async function flush() {
    if (queue.length === 0) return;
    const sessionUuid = SessionManager.getSessionUuid();
    const sessionToken = SessionManager.getSessionToken();
    if (!sessionUuid || !sessionToken) {
      queue = [];
      return;
    }

    const batch = queue.splice(0, 50);
    try {
      await fetch("/api/telemetry", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionUuid,
          "X-Session-Token": sessionToken,
        },
        body: JSON.stringify({ events: batch }),
      });
    } catch (e) {
      // Put unsent events back on failure
      queue.unshift(...batch);
    }
  }

  function flushBeacon() {
    if (queue.length === 0) return;
    const sessionUuid = SessionManager.getSessionUuid();
    const sessionToken = SessionManager.getSessionToken();
    if (!sessionUuid || !sessionToken) return;

    const batch = queue.splice(0, 50);
    const payload = JSON.stringify({ events: batch });
    navigator.sendBeacon(
      "/api/telemetry",
      new Blob([payload], { type: "application/json" })
    );
  }

  return {
    init,
    queueEvent,
    sendImmediate,
    flush,
  };
})();
