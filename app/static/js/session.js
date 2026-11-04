/**
 * session.js — V2 session lifecycle management.
 *
 * Creates an anonymous visitor and session, sends heartbeats,
 * ends the session on Stop or page close.
 */
const SessionManager = (function () {
  let visitorUuid = null;
  let sessionUuid = null;
  let sessionToken = null;
  let heartbeatInterval = null;

  async function createVisitor() {
    const res = await fetch("/api/visitors", { method: "POST" });
    if (!res.ok) throw new Error("Failed to create visitor");
    const data = await res.json();
    visitorUuid = data.visitor_uuid;
    return visitorUuid;
  }

  async function startSession() {
    if (!visitorUuid) await createVisitor();
    const res = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_uuid: visitorUuid }),
    });
    if (!res.ok) throw new Error("Failed to start session");
    const data = await res.json();
    sessionUuid = data.session_uuid;
    sessionToken = data.session_token;

    // Start heartbeat every 60 seconds
    heartbeatInterval = setInterval(sendHeartbeat, 60000);

    // End session on page close
    window.addEventListener("pagehide", endSessionBeacon);

    return { sessionUuid, sessionToken };
  }

  async function sendHeartbeat() {
    if (!sessionUuid || !sessionToken) return;
    try {
      await fetch(`/api/sessions/${sessionUuid}/heartbeat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": sessionToken,
        },
      });
    } catch (e) {
      // Heartbeat failure is non-critical
    }
  }

  async function endSession() {
    if (!sessionUuid || !sessionToken) return;
    clearInterval(heartbeatInterval);
    window.removeEventListener("pagehide", endSessionBeacon);
    try {
      await fetch(`/api/sessions/${sessionUuid}/end`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": sessionToken,
        },
      });
    } catch (e) {
      // Best effort
    }
    sessionUuid = null;
    sessionToken = null;
  }

  function endSessionBeacon() {
    if (!sessionUuid || !sessionToken) return;
    // Use sendBeacon for reliable delivery on page unload
    const url = `/api/sessions/${sessionUuid}/end`;
    navigator.sendBeacon(
      url,
      new Blob(
        [JSON.stringify({})],
        { type: "application/json" }
      )
    );
  }

  function getSessionUuid() { return sessionUuid; }
  function getSessionToken() { return sessionToken; }
  function isActive() { return sessionUuid !== null && sessionToken !== null; }

  return {
    startSession,
    endSession,
    getSessionUuid,
    getSessionToken,
    isActive,
  };
})();
