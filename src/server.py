"""
MemFree REST API Server — serves the Web UI and provides HTTP API.
"""

import json
import sys
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from facts import FACTS_FILE, add_fact, compute_dynamic, feedback_fact, get_stats, load_facts

LOCK = threading.RLock()

CAT_HALF_LIFE = {
    "identity": 365, "preference": 90, "tool": 90,
    "work": 60, "project": 60, "lesson": 60,
    "thread": 30, "behavior": 30, "test": 1,
    "general": 30,
}


class Handler(BaseHTTPRequestHandler):

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _err(self, msg, code=400):
        self._json({"error": msg}, code)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json({"status": "ok", "service": "memfree"})

        elif path == "/facts":
            self._json({"facts": load_facts()})

        elif path == "/stats":
            self._json(get_stats())

        else:
            self._err("Not found", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        try:
            data = json.loads(body) if body else {}
        except Exception:
            self._err("Invalid JSON")
            return

        if path == "/facts/add":
            text = data.get("text", "").strip()
            imp = float(data.get("importance", 0.5))
            cat = data.get("category", "general")
            if not text:
                return self._err("text is required")
            imp = max(0.0, min(1.0, imp))

            # Conflict detection
            facts = load_facts()
            conflicts = []
            for f in facts:
                if f.get("invalidated"):
                    continue

                def ngrams(t, n=4):
                    t2 = t.replace(" ", "")
                    return set(t2[i:i+n] for i in range(max(0, len(t2)-n+1)))

                ng_new = ngrams(text)
                ng_old = ngrams(f["text"])
                overlap = len(ng_new & ng_old)
                if overlap >= 3:
                    if f.get("importance", 0) < 0.9:
                        f["invalidated"] = True
                        f["invalidated_at"] = datetime.now().isoformat()
                        f["invalidated_reason"] = f"Replaced by new fact (4-gram overlap: {overlap})"
                    conflicts.append(f["id"])

            fid = hashlib_md5(text)
            valid_days = CAT_HALF_LIFE.get(cat, 30)
            new_fact = {
                "id": fid,
                "text": text,
                "importance": imp,
                "category": cat,
                "source": "web-ui",
                "created_at": datetime.now().isoformat(),
                "valid_days": valid_days,
                "expires_at": (datetime.now() + timedelta(days=valid_days)).isoformat(),
                "invalidated": False,
                "invalidated_at": None,
                "invalidated_reason": None,
                "access_count": 0,
            }
            facts = [f for f in facts if f["id"] not in conflicts] + [new_fact]

            with LOCK:
                FACTS_FILE.write_text(json.dumps(facts, ensure_ascii=False, indent=2))

            self._json({"fact": new_fact, "conflicts": conflicts})

        elif path == "/facts/feedback":
            fid = data.get("id")
            delta = float(data.get("delta", 0))
            if not fid:
                return self._err("id required")
            result = feedback_fact(fid, delta)
            if result:
                self._json({"fact": result, "dynamic_importance": compute_dynamic(result)})
            else:
                self._err("Fact not found", 404)

        else:
            self._err("Not found", 404)

    def log_message(self, fmt, *args):
        pass  # silent


def hashlib_md5(text):
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()[:8]


def main():
    import argparse
    parser = argparse.ArgumentParser(prog="memfree-server")
    parser.add_argument("--port", "-p", type=int, default=19099)
    parser.add_argument("--host", default="localhost")
    args = parser.parse_args()

    print(f"🧠 MemFree Server")
    print(f"   API:   http://{args.host}:{args.port}")
    print(f"   Facts: {FACTS_FILE}")
    print(f"   Web:   http://{args.host}:{args.port}/web_ui.html")
    print()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"Ready. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
