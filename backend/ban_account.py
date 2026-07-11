from pathlib import Path
import datetime as dt
import json
import sqlite3
import sys
import uuid


DB_PATH = Path(__file__).resolve().parent / "library.db"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def find_key(value, keys):
    if isinstance(value, dict):
        for key in keys:
            if key in value and value[key]:
                return str(value[key])
        for child in value.values():
            found = find_key(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_key(child, keys)
            if found:
                return found
    return ""


def read_username():
    if len(sys.argv) > 1:
        return sys.argv[1], "manual"

    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Usage: python backend/ban_account.py <username>")

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return raw, "stdin"

    username = find_key(event, ["account_to_ban", "attacker_username", "username"])
    if not username:
        raise SystemExit("No account_to_ban/attacker_username/username found in alert JSON.")
    return username, json.dumps(event, separators=(",", ":"))[:2000]


def revoke_account_credentials(db, username):
    db.execute(
        """
        UPDATE users
        SET password_hash = ?, decoy_password = NULL
        WHERE username = ?
        """,
        (f"revoked:{uuid.uuid4().hex}", username),
    )


def main():
    username, source = read_username()
    username = username.strip().lower()
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT INTO banned_accounts (username, reason, source_event, banned_at)
            VALUES (?, 'honeypot file download', ?, ?)
            ON CONFLICT(username) DO UPDATE SET
              reason = excluded.reason,
              source_event = excluded.source_event,
              banned_at = excluded.banned_at
            """,
            (username, source, utcnow()),
        )
        revoke_account_credentials(db, username)
    print(f"banned={username}")


if __name__ == "__main__":
    main()
