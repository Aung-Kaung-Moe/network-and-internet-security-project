from http.server import ThreadingHTTPServer
from threading import Thread

from app import AppHandler, HoneypotHandler, HONEYPOT_ORIGIN, HONEYPOT_PORT, PORT, init_db


def serve(port, handler, label):
    server = ThreadingHTTPServer(("", port), handler)
    print(f"{label} running at http://localhost:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    init_db()
    real_thread = Thread(target=serve, args=(PORT, AppHandler, "Real library"), daemon=True)
    real_thread.start()
    print(f"Fake admin dashboard URL is {HONEYPOT_ORIGIN}/webadmin", flush=True)
    serve(HONEYPOT_PORT, HoneypotHandler, "Fake admin honeypot")
