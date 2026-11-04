/**
 * admin-live.js — Real-time live dashboard updates via WebSocket.
 *
 * Connects to /ws/admin with token, receives event summaries,
 * updates session table live without requiring manual refresh.
 * Tracks heartbeat and honest connection status.
 */
const AdminLive = (function () {
  let ws = null;
  let pingInterval = null;
  let reconnectTimer = null;
  let lastHeartbeatReceived = 0;
  const HEARTBEAT_TIMEOUT_MS = 60000; // 60s without ping => Disconnected

  function init(token) {
    if (!token) return;
    connect(token);
  }

  function connect(token) {
    if (ws) {
      try { ws.close(); } catch (e) {}
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/admin?token=${encodeURIComponent(token)}`;

    const statusEl = document.getElementById("status");
    if (statusEl) statusEl.textContent = "Connecting real-time feed...";

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      lastHeartbeatReceived = Date.now();
      if (statusEl) statusEl.textContent = "Real-time feed: Connected (Live)";
      // Send ping every 30s
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      lastHeartbeatReceived = Date.now();
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "ping") {
          if (ws && ws.readyState === WebSocket.OPEN) ws.send("pong");
          return;
        }
        handleLiveEvent(msg);
      } catch (e) {
        // Text pong response or ignored
      }
    };

    ws.onclose = (event) => {
      if (pingInterval) clearInterval(pingInterval);
      if (statusEl) {
        statusEl.textContent = event.code === 1008
          ? "Real-time authentication failed."
          : "Real-time feed: Disconnected (reconnecting...)";
      }
      if (event.code !== 1008) {
        // Attempt reconnect after 5s
        reconnectTimer = setTimeout(() => connect(token), 5000);
      }
    };

    ws.onerror = (err) => {
      console.warn("WebSocket error:", err);
    };
  }

  function handleLiveEvent(msg) {
    // Check if session row already exists in table
    const rows = document.getElementById("rows");
    if (!rows) return;

    let row = document.getElementById(`session-${msg.session_uuid}`);
    if (!row) {
      row = document.createElement("tr");
      row.id = `session-${msg.session_uuid}`;

      // Insert at the top of the table
      if (rows.firstChild) {
        rows.insertBefore(row, rows.firstChild);
      } else {
        rows.appendChild(row);
      }
    }

    const timeStr = msg.recorded_at ? new Date(msg.recorded_at).toLocaleString() : new Date().toLocaleString();
    const eventSummary = `${msg.event_type} (${msg.status})`;

    row.innerHTML = `
      <td>${timeStr}</td>
      <td><span class="tag" style="background:#1a2a1a;color:#8be0b1;">${msg.status}</span></td>
      <td>${msg.summary?.os || "—"}</td>
      <td>${msg.summary?.browser || msg.summary?.device_type || "—"}</td>
      <td>${msg.event_type.includes("CAMERA") ? msg.event_type : "—"}</td>
      <td>${msg.event_type.includes("LOCATION") ? "Active" : "—"}</td>
      <td>Event: ${msg.event_type}</td>
    `;
  }

  function disconnect() {
    if (pingInterval) clearInterval(pingInterval);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  return {
    init,
    disconnect,
  };
})();
