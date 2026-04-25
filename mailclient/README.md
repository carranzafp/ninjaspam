# NinjaSpam Mail Client

Simple Flask mail client split into `backend/` and `frontend/`, using JSON command/response messages over WebSocket.

## Run

```bash
cd /home/maximus/ninjaspam/mailclient
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Notes

- Shared app settings stay in `config.json` and can be committed to GitHub.
- The local password is stored separately in `secret.json`, which is ignored by git.
- On a new machine, type the IMAP password once in the login form and it will be saved locally for later autofill.
- The frontend uses Bootstrap via CDN.
- Configuration changes are persisted to `config.json`, while the password is persisted to `secret.json`.
- The current inbox view returns subject, sender, and date for the latest emails.
- Clicking an email opens a bottom detail panel with **Body** and **Details** tabs.
- The detail panel includes **Mark as SPAM**, **Mark as HAM**, and **Test email** actions.
- Labeled emails are stored in `mailclient/maildatabase.json` with normalized content and SHA-256 deduplication.
- The Debug section can clear the JSON database only after two UI confirmations plus typed confirmation.
- Allowed languages use short language identifiers like `EN`, `ES`, `FR`.
- Allowed countries use ISO-style country codes like `MX`, `US`, `ES`.