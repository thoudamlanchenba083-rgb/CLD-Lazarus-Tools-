/**
 * device.js — Client-side device metadata collection and summary.
 *
 * Reads only browser-exposed metadata:
 * - navigator.language
 * - Intl.DateTimeFormat().resolvedOptions().timeZone
 * - screen.width / height
 * - navigator.onLine
 * - navigator.userAgent
 *
 * Explicitly does NOT read IMEI, contacts, SMS, serial numbers, or files.
 */
const DeviceCollector = (function () {
  function collect() {
    return {
      user_agent: navigator.userAgent || "",
      language: navigator.language || "",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      screen_width: window.screen ? window.screen.width : null,
      screen_height: window.screen ? window.screen.height : null,
      online: typeof navigator.onLine === "boolean" ? navigator.onLine : null,
    };
  }

  function getSummaryText(data) {
    const lines = [
      `Browser/UA: ${data.user_agent.slice(0, 80)}...`,
      `Language: ${data.language || "Unknown"}`,
      `Timezone: ${data.timezone || "Unknown"}`,
      `Screen: ${data.screen_width || "?"}x${data.screen_height || "?"}`,
      `Online: ${data.online ? "Yes" : "No"}`
    ];
    return lines.join("\n");
  }

  return {
    collect,
    getSummaryText,
  };
})();
