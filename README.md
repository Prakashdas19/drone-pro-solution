# Drone Pro Solution — Working V4

This is a local production-style base for the company website.

## Run on Windows / VS Code

1. Install Python 3.13.
2. Open this folder in VS Code.
3. In PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DPS_ADMIN_PASSWORD="YOUR-PRIVATE-PASSWORD"
$env:DPS_SESSION_SECRET="PUT-A-LONG-RANDOM-SECRET-HERE"
uvicorn app:app --reload
```

4. Open http://127.0.0.1:8000
5. Private admin: http://127.0.0.1:8000/admin

## Important
- AI Report module is not part of this build.
- Original uploaded images are stored under `storage/originals` and are not exposed by a public static route.
- Public gallery serves only resized/watermarked previews from `storage/previews`.
- A visible preview can still be copied/screenshot; no browser-based website can prevent that completely.
- Before going live, use HTTPS, a strong admin password/secret, secure cookies, proper domain/hosting, backups, and server-level access controls.
