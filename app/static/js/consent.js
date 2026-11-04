/**
 * consent.js — V2 granular, revocable consent management.
 *
 * Manages per-type consent toggles and communicates with the backend.
 * Each consent type has a visible indicator and a revoke mechanism.
 */
const ConsentManager = (function () {
  // Track consent IDs by type so we can revoke them
  const consentIds = {};

  function _headers() {
    return {
      "Content-Type": "application/json",
      "X-Session-Token": SessionManager.getSessionToken(),
    };
  }

  async function grantConsent(consentType) {
    const sessionUuid = SessionManager.getSessionUuid();
    if (!sessionUuid) return null;
    const res = await fetch(`/api/consent/${sessionUuid}`, {
      method: "POST",
      headers: _headers(),
      body: JSON.stringify({ consent_type: consentType, granted: true }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to record consent");
    }
    const data = await res.json();
    consentIds[consentType] = data.id;
    return data;
  }

  async function revokeConsent(consentType) {
    const id = consentIds[consentType];
    if (!id) return null;
    const res = await fetch(`/api/consent/${id}`, {
      method: "DELETE",
      headers: _headers(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to revoke consent");
    }
    const data = await res.json();
    delete consentIds[consentType];
    return data;
  }

  function hasConsent(consentType) {
    return consentType in consentIds;
  }

  function getConsentId(consentType) {
    return consentIds[consentType] || null;
  }

  function clearAll() {
    Object.keys(consentIds).forEach(k => delete consentIds[k]);
  }

  return {
    grantConsent,
    revokeConsent,
    hasConsent,
    getConsentId,
    clearAll,
  };
})();
