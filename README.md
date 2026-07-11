# Library Honeypot Project

This first version builds the real-looking library system before the admin honeypot dashboard.

The project is split into:

- `frontend/` for the browser UI
- `backend/` for the API and SQLite database
- `wazuh/` for example Wazuh rule and Active Response snippets

## Current Features

- Public book catalog
- Book detail pages
- Register and login
- JWT token returned after login and stored in the `library_jwt` browser cookie
- Borrowing requires login
- User account page without exposing the JWT on screen
- Return button for books that are not overdue
- Overdue fine display at 500 MMK per overdue day
- SQLite tables for users, books, loans, and security events
- Quiet security event logging for suspicious JWT activity
- Honeypot admin trap for forged `role:admin` JWT tokens
- Three fake admin CSV downloads with 30 decoy borrower records
- Fake admin service runs on a separate port from the real website
- Wazuh-ready JSONL alert events when bait files are downloaded
- Ban hook script for owner/Wazuh Active Response workflow

## Honeypot Challenge Path

- `alg:none` is blocked.
- The JWT secret is intentionally weak: `book`.
- A seeded easy account exists: `attacker` / `password123`.
- After login, an attacker can inspect the `library_jwt` cookie or network traffic to find the JWT.
- The intended attack is to crack the weak JWT secret, change `role:user` to `role:admin`, re-sign the token, and replace the `library_jwt` cookie.
- With a valid forged admin cookie, visiting `http://localhost:3000`, `/admin`, or `/dashboard` redirects to the fake admin dashboard.
- The real site runs at `http://localhost:3000`.
- The fake admin honeypot runs at `http://127.0.0.1:4000/dashboard`.
- The real site creates a short-lived handoff ticket and redirects forged admin sessions to the honeypot port.
- The fake dashboard offers three downloadable bait files:
  - `book_borrowers_credentials.csv`
  - `book_borrowers_borrowed_books.csv`
  - `book_borrowers_fine_list.csv`

## Run

```powershell
npm start
```

Open:

```text
http://localhost:3000
```

Use `http://`, not `https://`. This local project does not run a TLS/HTTPS server.

Honeypot dashboard port:

```text
http://127.0.0.1:4000/dashboard
```

Wazuh alert log:

```text
logs/wazuh-honeypot-alerts.jsonl
```

The default JWT secret is intentionally weak for the attack path:

```text
book
```
