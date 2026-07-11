from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
import base64
import csv
import datetime as dt
import hashlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import sqlite3
import uuid


ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
DB_PATH = ROOT / "backend" / "library.db"
LOG_DIR = ROOT / "logs"
PORT = int(os.environ.get("PORT", "3000"))
HONEYPOT_PORT = int(os.environ.get("HONEYPOT_PORT", "4000"))
HONEYPOT_ORIGIN = os.environ.get("HONEYPOT_ORIGIN", f"http://localhost:{HONEYPOT_PORT}")
REAL_ORIGIN = os.environ.get("REAL_ORIGIN", f"http://localhost:{PORT}")
REAL_LOGOUT_URL = f"{REAL_ORIGIN}/?logout=1"
JWT_SECRET = os.environ.get("JWT_SECRET", "book")
JWT_COOKIE_NAME = "library_jwt"
HONEYPOT_TICKET_COOKIE = "honeypot_ticket"
ATTACKER_USERNAME = "attacker"
ATTACKER_PASSWORD = "password123"
WEBADMIN_USERNAME = "webadmin"
WEBADMIN_PASSWORD = "webadmin"
WEBADMIN_USER_ID = "decoy-webadmin-account"
LOGIN_BRUTEFORCE_ATTEMPTS = 5
LOGIN_BRUTEFORCE_WINDOW_SECONDS = 60
FINE_PER_OVERDUE_DAY = 500
LOAN_DAYS = 14
HONEYPOT_TICKET_MINUTES = 10


SEED_BOOKS = [
    (
        "bk-001",
        "Applied Network Security",
        "Maya Chen",
        "Security",
        2023,
        4,
        4,
        "A practical introduction to firewalls, secure network design, monitoring, and common attack paths in modern systems.",
        "SEC-12",
        "978-1-4028-1001-2",
    ),
    (
        "bk-002",
        "Web Application Defense",
        "Arun Patel",
        "Security",
        2022,
        3,
        3,
        "Covers authentication, session handling, input validation, API security, logging, and incident response for web systems.",
        "SEC-18",
        "978-1-4028-1002-9",
    ),
    (
        "bk-003",
        "Database Systems in Practice",
        "Elena Brooks",
        "Database",
        2021,
        5,
        5,
        "A clear guide to relational design, queries, indexing, transactions, and responsible data management.",
        "DB-04",
        "978-1-4028-1003-6",
    ),
    (
        "bk-004",
        "Modern JavaScript Patterns",
        "Noah Williams",
        "Programming",
        2024,
        2,
        2,
        "Explains maintainable frontend and backend JavaScript patterns through realistic examples.",
        "PRG-09",
        "978-1-4028-1004-3",
    ),
    (
        "bk-005",
        "Introduction to Cryptography",
        "Sofia Marin",
        "Security",
        2020,
        3,
        3,
        "Introduces encryption, hashing, signatures, key exchange, and common implementation mistakes.",
        "SEC-07",
        "978-1-4028-1005-0",
    ),
    (
        "bk-006",
        "Operating Systems Essentials",
        "Daniel Reed",
        "Systems",
        2019,
        6,
        6,
        "A concise guide to processes, memory, filesystems, permissions, and system-level troubleshooting.",
        "SYS-02",
        "978-1-4028-1006-7",
    ),
]


BASE_DECOY_ACCOUNTS = [
    ("attacker", "password123", "Aye Chan", "aye.chan@northstar.local"),
    ("maythu", "maythu123", "May Thu", "may.thu@northstar.local"),
    ("zinmin", "zinmin123", "Zin Min", "zin.min@northstar.local"),
    ("hlaing", "hlaing123", "Hlaing Myat", "hlaing.myat@northstar.local"),
    ("thazin", "thazin123", "Thazin Oo", "thazin.oo@northstar.local"),
    ("kaung", "kaung123", "Kaung Htet", "kaung.htet@northstar.local"),
    ("su_wai", "suwai123", "Su Wai", "su.wai@northstar.local"),
    ("myatnoe", "myatnoe123", "Myat Noe", "myat.noe@northstar.local"),
    ("nandar", "nandar123", "Nandar Lin", "nandar.lin@northstar.local"),
    ("phyo", "phyo123", "Phyo Hein", "phyo.hein@northstar.local"),
    ("eaint", "eaint123", "Eaint Thet", "eaint.thet@northstar.local"),
    ("naylin", "naylin123", "Nay Lin", "nay.lin@northstar.local"),
    ("khine", "khine123", "Khine Zar", "khine.zar@northstar.local"),
    ("zawmin", "zawmin123", "Zaw Min", "zaw.min@northstar.local"),
    ("hmue", "hmue123", "Hmue Thiri", "hmue.thiri@northstar.local"),
    ("aungko", "aungko123", "Aung Ko", "aung.ko@northstar.local"),
    ("sandar", "sandar123", "Sandar Moe", "sandar.moe@northstar.local"),
    ("thethtar", "thethtar123", "Thet Htar", "thet.htar@northstar.local"),
    ("linhtet", "linhtet123", "Lin Htet", "lin.htet@northstar.local"),
    ("waiyan", "waiyan123", "Wai Yan", "wai.yan@northstar.local"),
    ("monmon", "monmon123", "Mon Mon", "mon.mon@northstar.local"),
    ("heinhtet", "heinhtet123", "Hein Htet", "hein.htet@northstar.local"),
    ("sithu", "sithu123", "Si Thu", "si.thu@northstar.local"),
    ("yehtet", "yehtet123", "Ye Htet", "ye.htet@northstar.local"),
    ("moemoe", "moemoe123", "Moe Moe", "moe.moe@northstar.local"),
    ("yamin", "yamin123", "Yamin Aye", "yamin.aye@northstar.local"),
    ("htetwai", "htetwai123", "Htet Wai", "htet.wai@northstar.local"),
    ("nwezin", "nwezin123", "Nwe Zin", "nwe.zin@northstar.local"),
    ("paing", "paing123", "Paing Soe", "paing.soe@northstar.local"),
    ("ei_san", "eisan123", "Ei San", "ei.san@northstar.local"),
    ("kyawzin", "kyawzin123", "Kyaw Zin", "kyaw.zin@northstar.local"),
    ("shwe", "shwe123", "Shwe Yee", "shwe.yee@northstar.local"),
]


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def iso(value):
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def overdue_days(due_at, now=None):
    now = now or utcnow()
    seconds_over = (now - parse_iso(due_at)).total_seconds()
    if seconds_over <= 0:
        return 0
    return max(1, int((seconds_over + 86399) // 86400))


def fine_for_due_date(due_at):
    return overdue_days(due_at) * FINE_PER_OVERDUE_DAY


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(db, table, column, definition):
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              full_name TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'user',
              password_hash TEXT NOT NULL,
              decoy_password TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS books (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              author TEXT NOT NULL,
              category TEXT NOT NULL,
              year INTEGER NOT NULL,
              copies_total INTEGER NOT NULL,
              copies_available INTEGER NOT NULL,
              summary TEXT NOT NULL,
              shelf TEXT NOT NULL,
              isbn TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loans (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              book_id TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'borrowed',
              borrowed_at TEXT NOT NULL,
              due_at TEXT NOT NULL,
              returned_at TEXT,
              fine_mmk INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY (user_id) REFERENCES users(id),
              FOREIGN KEY (book_id) REFERENCES books(id)
            );

            CREATE TABLE IF NOT EXISTS security_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              type TEXT NOT NULL,
              ip TEXT,
              method TEXT,
              path TEXT,
              user_agent TEXT,
              details TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS honeypot_tickets (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              username TEXT NOT NULL,
              token_role TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS banned_accounts (
              username TEXT PRIMARY KEY,
              reason TEXT NOT NULL,
              source_event TEXT,
              banned_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              ip TEXT NOT NULL,
              username TEXT NOT NULL,
              password TEXT NOT NULL,
              user_agent TEXT NOT NULL
            );
            """
        )
        ensure_column(db, "users", "decoy_password", "TEXT")
        count = db.execute("SELECT COUNT(*) AS count FROM books").fetchone()["count"]
        if count == 0:
            db.executemany(
                """
                INSERT INTO books (
                  id, title, author, category, year, copies_total,
                  copies_available, summary, shelf, isbn
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SEED_BOOKS,
            )
        db.execute(
            """
            INSERT OR IGNORE INTO users (
              id, username, full_name, role, password_hash, decoy_password, created_at
            )
            VALUES (?, ?, ?, 'user', ?, ?, ?)
            """,
            (
                "decoy-attacker-account",
                ATTACKER_USERNAME,
                "Aye Chan",
                password_hash(ATTACKER_USERNAME, ATTACKER_PASSWORD),
                ATTACKER_PASSWORD,
                iso(utcnow()),
            ),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO users (
              id, username, full_name, role, password_hash, decoy_password, created_at
            )
            VALUES (?, ?, ?, 'user', ?, ?, ?)
            """,
            (
                WEBADMIN_USER_ID,
                WEBADMIN_USERNAME,
                "Web Admin",
                password_hash(WEBADMIN_USERNAME, WEBADMIN_PASSWORD),
                WEBADMIN_PASSWORD,
                iso(utcnow()),
            ),
        )
        revoke_banned_account_credentials(db)


def row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "category": row["category"],
        "year": row["year"],
        "copiesTotal": row["copies_total"],
        "copiesAvailable": row["copies_available"],
        "summary": row["summary"],
        "shelf": row["shelf"],
        "isbn": row["isbn"],
    }


def public_user(row, payload=None):
    payload = payload or {}
    payload_role = str(payload.get("role", "")).lower()
    return {
        "id": row["id"],
        "username": payload.get("username") if payload_role == "admin" else row["username"],
        "fullName": row["full_name"],
        "role": "admin" if payload_role == "admin" else row["role"],
    }


def account_is_banned(db, username):
    return db.execute(
        "SELECT username FROM banned_accounts WHERE username = ?",
        (username,),
    ).fetchone() is not None


def revoke_account_credentials(db, username):
    username = str(username or "").strip().lower()
    if not username:
        return
    db.execute(
        """
        UPDATE users
        SET password_hash = ?, decoy_password = NULL
        WHERE username = ?
        """,
        (f"revoked:{uuid.uuid4().hex}", username),
    )


def revoke_banned_account_credentials(db):
    rows = db.execute("SELECT username FROM banned_accounts").fetchall()
    for row in rows:
        revoke_account_credentials(db, row["username"])


def ban_account(db, username, source_event):
    username = str(username or "").strip().lower()
    if not username:
        return
    db.execute(
        """
        INSERT INTO banned_accounts (username, reason, source_event, banned_at)
        VALUES (?, 'honeypot file download', ?, ?)
        ON CONFLICT(username) DO UPDATE SET
          reason = excluded.reason,
          source_event = excluded.source_event,
          banned_at = excluded.banned_at
        """,
        (username, source_event, iso(utcnow())),
    )
    revoke_account_credentials(db, username)


def password_hash(username, password):
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()


def b64url_encode(raw):
    if isinstance(raw, str):
        raw = raw.encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign_jwt(payload):
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = b64url_encode(json.dumps(header, separators=(",", ":")))
    encoded_payload = b64url_encode(json.dumps(payload, separators=(",", ":")))
    data = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(JWT_SECRET.encode(), data.encode(), hashlib.sha256).digest()
    return f"{data}.{b64url_encode(signature)}"


def create_token(user):
    now = int(utcnow().timestamp())
    return sign_jwt(
        {
            "sub": user["id"],
            "username": user["username"],
            "role": user["role"],
            "iat": now,
            "exp": now + 3600,
        }
    )


def create_role_token(user, role, username=None):
    now = int(utcnow().timestamp())
    return sign_jwt(
        {
            "sub": user["id"],
            "username": username or user["username"],
            "role": role,
            "iat": now,
            "exp": now + 3600,
        }
    )


def cookie_header(token, max_age=3600):
    return f"{JWT_COOKIE_NAME}={token}; Path=/; SameSite=Lax; Max-Age={max_age}"


def honeypot_ticket_cookie(ticket, max_age=HONEYPOT_TICKET_MINUTES * 60):
    return f"{HONEYPOT_TICKET_COOKIE}={ticket}; Path=/; SameSite=Lax; Max-Age={max_age}"


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class RedirectHome(Exception):
    pass


class AppHandler(BaseHTTPRequestHandler):
    server_version = "NorthstarLibrary/1.0"

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.handle_api()
        else:
            self.serve_static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.handle_api()
        else:
            self.send_json(404, {"error": "Not found."})

    def log_message(self, format, *args):
        return

    def send_json(self, status, payload, extra_headers=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        if isinstance(extra_headers, dict):
            header_items = extra_headers.items()
        else:
            header_items = extra_headers or []
        for key, value in header_items:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def redirect_home(self):
        self.send_response(302)
        self.send_header("Location", REAL_ORIGIN)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def logout_redirect(self):
        expired = [
            "library_jwt=; Path=/; SameSite=Lax; Max-Age=0",
            "honeypot_ticket=; Path=/; SameSite=Lax; Max-Age=0",
            "library_jwt=; Domain=localhost; Path=/; SameSite=Lax; Max-Age=0",
            "honeypot_ticket=; Domain=localhost; Path=/; SameSite=Lax; Max-Age=0",
        ]
        self.send_response(302)
        self.send_header("Location", REAL_LOGOUT_URL)
        for cookie in expired:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 1_000_000:
            raise ApiError("Request body is too large.", 413)
        if size == 0:
            return {}
        try:
            return json.loads(self.rfile.read(size).decode())
        except json.JSONDecodeError:
            raise ApiError("Invalid JSON body.", 400)

    def log_security(self, event_type, details=None):
        details = details or {}
        with connect_db() as db:
            db.execute(
                """
                INSERT INTO security_events (
                  created_at, type, ip, method, path, user_agent, details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iso(utcnow()),
                    event_type,
                    self.client_address[0],
                    self.command,
                    self.path,
                    self.headers.get("User-Agent", ""),
                    json.dumps(details),
                ),
            )

    def write_wazuh_alert(self, event_type, details):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": iso(utcnow()),
            "honeypot_program": "northstar-library-honeypot",
            "event_type": event_type,
            "severity": "high",
            "action": "alert",
            "owner_action": "ban_candidate",
            **details,
        }
        with (LOG_DIR / "wazuh-honeypot-alerts.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")

    def record_failed_login_attempt(self, username, password):
        now = utcnow()
        cutoff = now - dt.timedelta(seconds=LOGIN_BRUTEFORCE_WINDOW_SECONDS)
        srcip = self.client_address[0]
        with connect_db() as db:
            db.execute(
                """
                INSERT INTO login_attempts (created_at, ip, username, password, user_agent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (iso(now), srcip, username, password, self.headers.get("User-Agent", "")),
            )
            db.execute(
                "DELETE FROM login_attempts WHERE created_at < ?",
                (iso(now - dt.timedelta(days=1)),),
            )
            rows = db.execute(
                """
                SELECT created_at, username, password, user_agent
                FROM login_attempts
                WHERE ip = ? AND created_at >= ?
                ORDER BY created_at ASC
                """,
                (srcip, iso(cutoff)),
            ).fetchall()

        if len(rows) == LOGIN_BRUTEFORCE_ATTEMPTS:
            attempted_credentials = [
                {
                    "username": row["username"],
                    "password": row["password"],
                    "at": row["created_at"],
                }
                for row in rows
            ]
            self.write_wazuh_alert(
                "login_bruteforce_detected",
                {
                    "severity": "medium",
                    "action": "review",
                    "owner_action": "soc_review",
                    "srcip": srcip,
                    "window_seconds": LOGIN_BRUTEFORCE_WINDOW_SECONDS,
                    "attempt_count": len(rows),
                    "attempted_credentials": attempted_credentials,
                    "last_attempt_username": username,
                    "last_attempt_password": password,
                    "url": self.path,
                    "recommendation": "review_credentials_no_auto_ban",
                },
            )

    def cookie_value(self, name):
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            if "=" not in part:
                continue
            key, value = part.strip().split("=", 1)
            if key == name:
                return value
        return ""

    def verify_jwt(self, token):
        parts = str(token or "").split(".")
        if len(parts) != 3:
            self.log_security("jwt_malformed", {"tokenPreview": str(token or "")[:24]})
            raise ApiError("Invalid token format.", 401)

        encoded_header, encoded_payload, signature = parts
        try:
            header = json.loads(b64url_decode(encoded_header))
            payload = json.loads(b64url_decode(encoded_payload))
        except Exception:
            self.log_security("jwt_decode_failed")
            raise ApiError("Invalid token encoding.", 401)

        if str(header.get("alg", "")).lower() == "none":
            self.log_security(
                "jwt_alg_none_attempt",
                {"username": payload.get("username"), "role": payload.get("role")},
            )
            raise ApiError("Unsigned tokens are not accepted.", 401)

        if header.get("alg") != "HS256":
            self.log_security("jwt_unexpected_alg", {"alg": header.get("alg")})
            raise ApiError("Unsupported token algorithm.", 401)

        data = f"{encoded_header}.{encoded_payload}".encode()
        expected = b64url_encode(hmac.new(JWT_SECRET.encode(), data, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            self.log_security(
                "jwt_bad_signature",
                {"username": payload.get("username"), "role": payload.get("role")},
            )
            raise ApiError("Invalid token signature.", 401)

        if payload.get("exp") and payload["exp"] < int(utcnow().timestamp()):
            raise ApiError("Token has expired.", 401)

        return payload

    def require_user(self):
        auth = self.headers.get("Authorization", "")
        token = ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        else:
            token = self.cookie_value(JWT_COOKIE_NAME)

        if not token:
            raise ApiError("Login is required.", 401)

        payload = self.verify_jwt(token)
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE id = ?", (payload.get("sub"),)).fetchone()
            if user and account_is_banned(db, user["username"]):
                raise ApiError("This account has been banned.", 403)
        if not user:
            raise ApiError("Token user no longer exists.", 401)
        return user, payload

    def require_admin_payload(self):
        user, payload = self.require_user()
        if str(payload.get("role", "")).lower() != "admin":
            raise ApiError("Admin access is required.", 403)
        self.log_security(
            "honeypot_admin_token_accepted",
            {
                "sub": payload.get("sub"),
                "username": payload.get("username"),
                "dbRole": user["role"],
                "tokenRole": payload.get("role"),
            },
        )
        return user, payload

    def create_honeypot_redirect_url(self, user, payload):
        ticket = secrets.token_urlsafe(24)
        now = utcnow()
        expires_at = now + dt.timedelta(minutes=HONEYPOT_TICKET_MINUTES)
        with connect_db() as db:
            db.execute(
                """
                INSERT INTO honeypot_tickets (
                  id, user_id, username, token_role, created_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket,
                    user["id"],
                    str(payload.get("username") or user["username"]),
                    str(payload.get("role") or ""),
                    iso(now),
                    iso(expires_at),
                ),
            )
        self.log_security(
            "honeypot_redirect_issued",
            {
                "username": payload.get("username"),
                "userId": user["id"],
                "sourcePath": self.path,
                "target": f"{HONEYPOT_ORIGIN}/webadmin",
            },
        )
        return f"{HONEYPOT_ORIGIN}/webadmin", ticket

    def admin_cookie_redirect_url(self):
        token = self.cookie_value(JWT_COOKIE_NAME)
        if not token:
            return ""

        try:
            payload = self.verify_jwt(token)
        except ApiError:
            return ""

        if str(payload.get("role", "")).lower() != "admin":
            return ""

        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE id = ?", (payload.get("sub"),)).fetchone()
            if user and account_is_banned(db, user["username"]):
                return ""

        if not user:
            return ""

        self.log_security(
            "honeypot_admin_cookie_seen",
            {
                "sub": payload.get("sub"),
                "username": payload.get("username"),
                "dbRole": user["role"],
                "tokenRole": payload.get("role"),
                "sourcePath": self.path,
            },
        )
        return self.create_honeypot_redirect_url(user, payload)

    def require_honeypot_ticket(self):
        query = parse_qs(urlparse(self.path).query)
        ticket = (query.get("t") or [""])[0].strip() or self.cookie_value(HONEYPOT_TICKET_COOKIE)
        if not ticket:
            raise ApiError("Honeypot session is missing.", 401)

        with connect_db() as db:
            record = db.execute(
                """
                SELECT honeypot_tickets.*, users.full_name, users.role, users.decoy_password
                FROM honeypot_tickets
                JOIN users ON users.id = honeypot_tickets.user_id
                WHERE honeypot_tickets.id = ?
                """,
                (ticket,),
            ).fetchone()
            if record and account_is_banned(db, record["username"]):
                raise RedirectHome()

        if not record:
            raise ApiError("Honeypot session is invalid.", 401)
        if parse_iso(record["expires_at"]) < utcnow():
            raise ApiError("Honeypot session has expired.", 401)

        user = {
            "id": record["user_id"],
            "username": record["username"],
            "full_name": record["full_name"],
            "role": record["role"],
            "decoy_password": record["decoy_password"],
        }
        payload = {
            "sub": record["user_id"],
            "username": record["username"],
            "role": record["token_role"],
        }
        return user, payload, ticket

    def send_csv_download(self, filename, rows, headers):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        body = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def decoy_accounts(self, current_user, payload):
        payload_username = str(payload.get("username") or current_user["username"])
        current_password = current_user["decoy_password"] or ATTACKER_PASSWORD
        current = (
            payload_username,
            current_password,
            current_user["full_name"],
            f"{payload_username}@northstar.local",
        )

        accounts = [current]
        seen = {payload_username}
        for username, password, full_name, email in BASE_DECOY_ACCOUNTS:
            if username in seen:
                continue
            accounts.append((username, password, full_name, email))
            seen.add(username)
            if len(accounts) == 30:
                break
        return accounts

    def credential_rows(self, current_user, payload):
        rows = []
        for index, (username, password, full_name, email) in enumerate(
            self.decoy_accounts(current_user, payload),
            start=1,
        ):
            rows.append(
                {
                    "account_id": f"MBR-{index:04d}",
                    "username": username,
                    "password": password,
                    "full_name": full_name,
                    "email": email,
                    "role": "user",
                }
            )
        return rows

    def borrowed_book_rows(self, current_user, payload):
        titles = [
            "Applied Network Security",
            "Web Application Defense",
            "Database Systems in Practice",
            "Modern JavaScript Patterns",
            "Introduction to Cryptography",
            "Operating Systems Essentials",
        ]
        rows = []
        base = utcnow() - dt.timedelta(days=8)
        for index, (username, _password, full_name, _email) in enumerate(
            self.decoy_accounts(current_user, payload),
            start=1,
        ):
            borrowed_at = base - dt.timedelta(days=index % 11)
            due_at = borrowed_at + dt.timedelta(days=LOAN_DAYS)
            rows.append(
                {
                    "loan_id": f"LN-{index:05d}",
                    "username": username,
                    "full_name": full_name,
                    "book_title": titles[index % len(titles)],
                    "borrowed_at": iso(borrowed_at),
                    "due_at": iso(due_at),
                    "status": "borrowed",
                }
            )
        return rows

    def fine_rows(self, current_user, payload):
        rows = []
        for index, (username, _password, full_name, _email) in enumerate(
            self.decoy_accounts(current_user, payload),
            start=1,
        ):
            overdue = 0 if index % 4 == 0 else (index % 9) + 1
            rows.append(
                {
                    "fine_id": f"FN-{index:05d}",
                    "username": username,
                    "full_name": full_name,
                    "overdue_days": overdue,
                    "fine_mmk": overdue * FINE_PER_OVERDUE_DAY,
                    "status": "pending" if overdue else "clear",
                }
            )
        return rows

    def handle_api(self):
        route = urlparse(self.path).path
        try:
            if self.command == "GET" and route == "/api/books":
                self.api_books()
            elif self.command == "GET" and route.startswith("/api/books/"):
                self.api_book(route.rsplit("/", 1)[-1])
            elif self.command == "POST" and route == "/api/register":
                self.api_register()
            elif self.command == "POST" and route == "/api/login":
                self.api_login()
            elif self.command == "GET" and route == "/api/logout":
                self.logout_redirect()
            elif self.command == "GET" and route == "/api/me":
                self.api_me()
            elif self.command == "POST" and route == "/api/honeypot/redirect":
                self.api_honeypot_redirect()
            elif self.command == "POST" and route == "/api/borrow":
                self.api_borrow()
            elif self.command == "POST" and route == "/api/return":
                self.api_return()
            else:
                self.send_json(404, {"error": "API route not found."})
        except RedirectHome:
            self.redirect_home()
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except Exception as error:
            self.send_json(500, {"error": f"Server error: {error}"})

    def api_books(self):
        with connect_db() as db:
            rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
        self.send_json(200, {"books": [row_to_book(row) for row in rows]})

    def api_book(self, book_id):
        with connect_db() as db:
            row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise ApiError("Book not found.", 404)
        self.send_json(200, {"book": row_to_book(row)})

    def api_register(self):
        body = self.read_json()
        username = str(body.get("username", "")).strip().lower()
        full_name = str(body.get("fullName", "")).strip().replace("<", "").replace(">", "")[:80]
        password = str(body.get("password", ""))

        if not username.replace("_", "").isalnum() or not 3 <= len(username) <= 24:
            raise ApiError("Username must be 3-24 characters using letters, numbers, or underscore.", 400)
        if len(password) < 6:
            raise ApiError("Password must be at least 6 characters.", 400)

        user_id = str(uuid.uuid4())
        try:
            with connect_db() as db:
                db.execute(
                    """
                    INSERT INTO users (
                      id, username, full_name, role, password_hash, decoy_password, created_at
                    )
                    VALUES (?, ?, ?, 'user', ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        full_name or username,
                        password_hash(username, password),
                        password,
                        iso(utcnow()),
                    ),
                )
                user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        except sqlite3.IntegrityError:
            raise ApiError("Username already exists.", 409)

        token = create_token(user)
        self.send_json(201, {"user": public_user(user), "token": token}, {"Set-Cookie": cookie_header(token)})

    def api_login(self):
        body = self.read_json()
        username = str(body.get("username", "")).strip().lower()
        password = str(body.get("password", ""))
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user and account_is_banned(db, username):
                raise ApiError("This account has been banned.", 403)

        if username == WEBADMIN_USERNAME and password == WEBADMIN_PASSWORD:
            with connect_db() as db:
                user = db.execute("SELECT * FROM users WHERE username = ?", (WEBADMIN_USERNAME,)).fetchone()
            if not user:
                raise ApiError("Admin account is unavailable.", 503)
            token = create_role_token(user, "admin", WEBADMIN_USERNAME)
            payload = {
                "sub": user["id"],
                "username": WEBADMIN_USERNAME,
                "role": "admin",
            }
            redirect_url, ticket = self.create_honeypot_redirect_url(user, payload)
            self.log_security(
                "webadmin_decoy_login",
                {
                    "username": username,
                    "target": redirect_url,
                    "srcip": self.client_address[0],
                },
            )
            self.write_wazuh_alert(
                "webadmin_decoy_login",
                {
                    "severity": "high",
                    "action": "review",
                    "owner_action": "soc_review",
                    "srcip": self.client_address[0],
                    "attempted_username": username,
                    "attempted_password": password,
                    "token_role": "admin",
                    "target": redirect_url,
                    "url": self.path,
                    "recommendation": "review_webadmin_decoy_login_no_auto_ban",
                },
            )
            self.send_json(
                200,
                {"user": public_user(user, payload), "token": token, "redirect": redirect_url},
                [
                    ("Set-Cookie", cookie_header(token)),
                    ("Set-Cookie", honeypot_ticket_cookie(ticket)),
                ],
            )
            return

        if not user or user["password_hash"] != password_hash(username, password):
            self.record_failed_login_attempt(username, password)
            raise ApiError("Invalid username or password.", 401)
        token = create_token(user)
        self.send_json(200, {"user": public_user(user), "token": token}, {"Set-Cookie": cookie_header(token)})

    def loan_rows(self, db, user_id):
        rows = db.execute(
            """
            SELECT
              loans.*,
              books.id AS book_id_real,
              books.title,
              books.author,
              books.category,
              books.year,
              books.copies_total,
              books.copies_available,
              books.summary,
              books.shelf,
              books.isbn
            FROM loans
            JOIN books ON books.id = loans.book_id
            WHERE loans.user_id = ? AND loans.status = 'borrowed'
            ORDER BY loans.due_at ASC
            """,
            (user_id,),
        ).fetchall()

        loans = []
        for row in rows:
            fine = fine_for_due_date(row["due_at"])
            days = overdue_days(row["due_at"])
            loans.append(
                {
                    "id": row["id"],
                    "bookId": row["book_id"],
                    "status": row["status"],
                    "borrowedAt": row["borrowed_at"],
                    "dueAt": row["due_at"],
                    "returnedAt": row["returned_at"],
                    "overdueDays": days,
                    "fineMmk": fine,
                    "canReturn": fine == 0,
                    "book": row_to_book(
                        {
                            "id": row["book_id_real"],
                            "title": row["title"],
                            "author": row["author"],
                            "category": row["category"],
                            "year": row["year"],
                            "copies_total": row["copies_total"],
                            "copies_available": row["copies_available"],
                            "summary": row["summary"],
                            "shelf": row["shelf"],
                            "isbn": row["isbn"],
                        }
                    ),
                }
            )
        return loans

    def api_me(self):
        user, payload = self.require_user()
        if str(payload.get("role", "")).lower() == "admin":
            self.log_security(
                "honeypot_admin_session_seen",
                {
                    "sub": payload.get("sub"),
                    "username": payload.get("username"),
                    "dbRole": user["role"],
                    "tokenRole": payload.get("role"),
                },
            )
        with connect_db() as db:
            loans = self.loan_rows(db, user["id"])
        self.send_json(
            200,
            {
                "user": public_user(user, payload),
                "loans": loans,
                "totalFineMmk": sum(loan["fineMmk"] for loan in loans),
            },
        )

    def api_honeypot_redirect(self):
        user, payload = self.require_admin_payload()
        url, ticket = self.create_honeypot_redirect_url(user, payload)
        self.send_json(200, {"url": url}, {"Set-Cookie": honeypot_ticket_cookie(ticket)})

    def api_admin_files(self):
        user, payload, ticket = self.require_honeypot_ticket()
        files = [
            {
                "id": "credentials",
                "name": "book_borrowers_credentials.csv",
                "title": "Book borrowers' credentials list",
                "rows": len(self.credential_rows(user, payload)),
            },
            {
                "id": "borrowed-books",
                "name": "book_borrowers_borrowed_books.csv",
                "title": "Book borrowers' borrowed book list",
                "rows": len(self.borrowed_book_rows(user, payload)),
            },
            {
                "id": "fines",
                "name": "book_borrowers_fine_list.csv",
                "title": "Book borrowers' fine list",
                "rows": len(self.fine_rows(user, payload)),
            },
        ]
        self.send_json(200, {"user": public_user(user, payload), "files": files})

    def api_admin_download(self, file_id):
        user, payload, ticket = self.require_honeypot_ticket()
        attacker_username = str(payload.get("username") or "").strip().lower()
        is_webadmin_decoy = attacker_username == WEBADMIN_USERNAME
        self.log_security(
            "honeypot_file_download",
            {
                "file": file_id,
                "sub": payload.get("sub"),
                "username": payload.get("username"),
                "tokenRole": payload.get("role"),
                "ticket": ticket,
            },
        )
        event_type = "webadmin_file_download" if is_webadmin_decoy else "honeypot_file_download"
        recommendation = "review_webadmin_download_no_auto_ban" if is_webadmin_decoy else "ban_account"
        self.write_wazuh_alert(
            event_type,
            {
                "file": file_id,
                "attacker_username": attacker_username,
                **({} if is_webadmin_decoy else {"account_to_ban": attacker_username}),
                "user_id": user["id"],
                "token_role": payload.get("role"),
                "client_ip": self.client_address[0],
                "url": self.path,
                "recommendation": recommendation,
            },
        )
        if not is_webadmin_decoy:
            with connect_db() as db:
                ban_account(
                    db,
                    attacker_username,
                    json.dumps(
                        {
                            "source": "app:honeytoken-download",
                            "file": file_id,
                            "ticket": ticket,
                            "url": self.path,
                        },
                        separators=(",", ":"),
                    ),
                )

        if file_id == "credentials":
            rows = self.credential_rows(user, payload)
            self.send_csv_download(
                "book_borrowers_credentials.csv",
                rows,
                ["account_id", "username", "password", "full_name", "email", "role"],
            )
            return

        if file_id == "borrowed-books":
            rows = self.borrowed_book_rows(user, payload)
            self.send_csv_download(
                "book_borrowers_borrowed_books.csv",
                rows,
                ["loan_id", "username", "full_name", "book_title", "borrowed_at", "due_at", "status"],
            )
            return

        if file_id == "fines":
            rows = self.fine_rows(user, payload)
            self.send_csv_download(
                "book_borrowers_fine_list.csv",
                rows,
                ["fine_id", "username", "full_name", "overdue_days", "fine_mmk", "status"],
            )
            return

        raise ApiError("Admin file not found.", 404)

    def api_borrow(self):
        user, _payload = self.require_user()
        body = self.read_json()
        book_id = str(body.get("bookId", ""))

        with connect_db() as db:
            book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if not book:
                raise ApiError("Book not found.", 404)
            existing = db.execute(
                """
                SELECT id FROM loans
                WHERE user_id = ? AND book_id = ? AND status = 'borrowed'
                """,
                (user["id"], book_id),
            ).fetchone()
            if existing:
                raise ApiError("You already borrowed this book.", 409)
            if book["copies_available"] < 1:
                raise ApiError("No copies are available right now.", 409)

            borrowed_at = utcnow()
            due_at = borrowed_at + dt.timedelta(days=LOAN_DAYS)
            db.execute(
                """
                INSERT INTO loans (
                  id, user_id, book_id, status, borrowed_at, due_at, fine_mmk
                )
                VALUES (?, ?, ?, 'borrowed', ?, ?, 0)
                """,
                (str(uuid.uuid4()), user["id"], book_id, iso(borrowed_at), iso(due_at)),
            )
            db.execute(
                "UPDATE books SET copies_available = copies_available - 1 WHERE id = ?",
                (book_id,),
            )
            updated_book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            loans = self.loan_rows(db, user["id"])

        self.send_json(
            201,
            {
                "message": "Book borrowed successfully.",
                "book": row_to_book(updated_book),
                "loans": loans,
                "totalFineMmk": sum(loan["fineMmk"] for loan in loans),
            },
        )

    def api_return(self):
        user, _payload = self.require_user()
        body = self.read_json()
        loan_id = str(body.get("loanId", ""))

        with connect_db() as db:
            loan = db.execute(
                """
                SELECT * FROM loans
                WHERE id = ? AND user_id = ? AND status = 'borrowed'
                """,
                (loan_id, user["id"]),
            ).fetchone()
            if not loan:
                raise ApiError("Borrowed book not found.", 404)

            fine = fine_for_due_date(loan["due_at"])
            if fine > 0:
                raise ApiError(f"This book is overdue. Fine due: {fine} MMK.", 409)

            returned_at = iso(utcnow())
            db.execute(
                """
                UPDATE loans
                SET status = 'returned', returned_at = ?, fine_mmk = 0
                WHERE id = ?
                """,
                (returned_at, loan_id),
            )
            db.execute(
                "UPDATE books SET copies_available = copies_available + 1 WHERE id = ?",
                (loan["book_id"],),
            )
            book = db.execute("SELECT * FROM books WHERE id = ?", (loan["book_id"],)).fetchone()
            loans = self.loan_rows(db, user["id"])

        self.send_json(
            200,
            {
                "message": "Book returned successfully.",
                "book": row_to_book(book),
                "loans": loans,
                "totalFineMmk": sum(loan["fineMmk"] for loan in loans),
            },
        )

    def serve_static(self):
        path = unquote(urlparse(self.path).path)
        relative = "index.html" if path == "/" else path.lstrip("/")
        if path == "/" or "." not in Path(relative).name:
            redirect_target = self.admin_cookie_redirect_url()
            if redirect_target:
                redirect_url, ticket = redirect_target
                self.send_response(302)
                self.send_header("Location", redirect_url)
                self.send_header("Set-Cookie", honeypot_ticket_cookie(ticket))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return

        file_path = (FRONTEND_DIR / relative).resolve()

        if FRONTEND_DIR.resolve() not in file_path.parents and file_path != FRONTEND_DIR.resolve():
            self.send_error(403)
            return

        if not file_path.exists() or not file_path.is_file():
            if "." not in Path(relative).name:
                file_path = (FRONTEND_DIR / "index.html").resolve()
            else:
                self.send_error(404)
                return

        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HoneypotHandler(AppHandler):
    server_version = "NorthstarLibraryHoneypot/1.0"

    def admin_cookie_redirect_url(self):
        return ""

    def redirect_to_real_site_as_normal_user(self):
        normal_token = ""
        token = self.cookie_value(JWT_COOKIE_NAME)
        if token:
            try:
                payload = self.verify_jwt(token)
                with connect_db() as db:
                    user = db.execute("SELECT * FROM users WHERE id = ?", (payload.get("sub"),)).fetchone()
                    payload_username = str(payload.get("username") or "").lower()
                    if (
                        user
                        and not account_is_banned(db, user["username"])
                        and user["username"] != WEBADMIN_USERNAME
                        and payload_username != WEBADMIN_USERNAME
                    ):
                        normal_token = create_token(user)
            except ApiError:
                normal_token = ""

        self.send_response(302)
        self.send_header("Location", REAL_ORIGIN if normal_token else REAL_LOGOUT_URL)
        self.send_header("Set-Cookie", honeypot_ticket_cookie("", 0))
        if normal_token:
            self.send_header("Set-Cookie", cookie_header(normal_token))
        else:
            self.send_header("Set-Cookie", cookie_header("", 0))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def redirect_with_honeypot_ticket(self):
        try:
            user, payload = self.require_admin_payload()
        except ApiError:
            self.redirect_to_real_site_as_normal_user()
            return True

        redirect_url, ticket = self.create_honeypot_redirect_url(user, payload)
        self.send_response(302)
        self.send_header("Location", redirect_url)
        self.send_header("Set-Cookie", honeypot_ticket_cookie(ticket))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return True

    def serve_static(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self.redirect_to_real_site_as_normal_user()
            return

        query = parse_qs(urlparse(self.path).query)
        query_ticket = (query.get("t") or [""])[0].strip()
        ticket = query_ticket or self.cookie_value(HONEYPOT_TICKET_COOKIE)
        if ticket:
            with connect_db() as db:
                record = db.execute(
                    "SELECT username FROM honeypot_tickets WHERE id = ?",
                    (ticket,),
                ).fetchone()
                if record and account_is_banned(db, record["username"]):
                    self.redirect_home()
                    return
            if query_ticket:
                self.send_response(302)
                self.send_header("Location", f"{HONEYPOT_ORIGIN}/webadmin")
                self.send_header("Set-Cookie", honeypot_ticket_cookie(query_ticket))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
        elif path == "/webadmin":
            if self.redirect_with_honeypot_ticket():
                return
        super().serve_static()

    def do_POST(self):
        self.send_json(404, {"error": "Honeypot route not found."})

    def handle_api(self):
        route = urlparse(self.path).path
        try:
            if self.command == "GET" and route == "/api/logout":
                self.logout_redirect()
            elif self.command == "GET" and route == "/api/admin/files":
                self.api_admin_files()
            elif self.command == "GET" and route.startswith("/api/admin/download/"):
                self.api_admin_download(route.rsplit("/", 1)[-1])
            else:
                self.send_json(404, {"error": "Honeypot API route not found."})
        except RedirectHome:
            self.redirect_home()
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except Exception as error:
            self.send_json(500, {"error": f"Server error: {error}"})


if __name__ == "__main__":
    init_db()
    print(f"Library honeypot foundation running at http://localhost:{PORT}")
    ThreadingHTTPServer(("", PORT), AppHandler).serve_forever()
