# brAInfection — Phishing Awareness Lab

A local, consent-first browser-permission demonstration and admin dashboard.

## What it does
- Clearly labels itself as a training simulation; it does not impersonate a real brand.
- Requests camera access only after the visitor checks consent and selects Camera.
- Displays a local camera preview. Camera frames/audio are never uploaded or stored.
- Requests location only after the visitor checks consent and selects Location.
- Sends coordinates only after browser permission is granted and the visitor submits.
- Collects only selected basic browser metadata.
- Stores consented session records in SQLite.
- Protects the admin API with an `ADMIN_TOKEN`.

## Run on Windows PowerShell

```powershell
cd F:\brAInfection
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ADMIN_TOKEN = "replace-with-a-long-random-local-token"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:
- Visitor demo: http://127.0.0.1:8000
- Admin page: http://127.0.0.1:8000/admin

Paste the same `ADMIN_TOKEN` into the admin page.

## Browser permission notes
Camera and geolocation generally require HTTPS or localhost. For a phone on your LAN, use a properly configured HTTPS development tunnel/server; do not expose the demo publicly with the default token.

## Data and privacy
- The demo does not attempt to read IMEI, contacts, SMS, call logs, or other restricted phone identifiers.
- No camera frames are transmitted.
- Location is stored only when the visitor explicitly grants browser permission and submits the consented form.
- Use synthetic/test data when demonstrating the project.
- Change the default admin token before use. Keep the server bound to localhost unless you have configured HTTPS and proper access controls.
