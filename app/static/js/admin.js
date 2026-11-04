/**
 * admin.js — V2 admin page with REST loading and real-time live WebSocket initiation.
 */
const $ = id => document.getElementById(id);
$("load").addEventListener("click", async () => {
  const token = $("token").value.trim();
  $("status").textContent = "Loading…";
  try {
    const r = await fetch("/api/sessions", { headers: { "X-Admin-Token": token } });
    if (!r.ok) throw new Error(r.status === 401 ? "Invalid token" : "Request failed");
    const data = await r.json();
    $("rows").replaceChildren();
    for (const s of data) {
      const tr = document.createElement("tr");
      tr.id = `session-${s.id}`;
      const values = [
        s.created_at ? new Date(s.created_at).toLocaleString() : "—",
        s.status || "—",
        s.platform || "—",
        s.user_agent || "—",
        s.camera_permission,
        s.location_permission,
        s.latitude == null ? "—" : `${s.latitude.toFixed(5)}, ${s.longitude.toFixed(5)} (±${Math.round(s.accuracy || 0)}m)`
      ];
      for (const v of values) {
        const td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
      }
      $("rows").appendChild(tr);
    }
    $("status").textContent = `${data.length} session(s) loaded. Initializing live WebSocket...`;

    // Start live WebSocket feed
    if (typeof AdminLive !== "undefined") {
      AdminLive.init(token);
    }
  } catch (e) {
    $("status").textContent = e.message;
  }
});
