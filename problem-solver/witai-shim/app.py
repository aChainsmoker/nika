"""
Temporary proxy in front of the real wit.ai /message endpoint.

wit.ai's intent classifier is currently broken for newly created apps
(see https://github.com/wit-ai/wit/issues/2851) - it always returns an
empty "intents" array, even for utterances that exactly match trained
data. Entity extraction still works correctly, since it relies on plain
keyword/free-text lookup rather than the broken ML classifier.

This shim forwards every request to the real wit.ai API unchanged, then
overrides the "intents" field with a single hardcoded intent so that
message classification in Nika can proceed. Remove this shim (and point
nika.ini's [wit-ai] url back at https://api.wit.ai/message) once wit.ai
fixes the bug or the project migrates to a self-hosted NLU service.
"""

import http.server
import json
import os
import urllib.error
import urllib.parse
import urllib.request

WIT_TOKEN = os.environ.get("WIT_TOKEN", "")
WIT_URL = os.environ.get("WIT_URL", "https://api.wit.ai/message")
FORCED_INTENT = os.environ.get("FORCED_INTENT", "about_entity")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8091"))


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/message":
            self.send_response(404)
            self.end_headers()
            return

        query = urllib.parse.parse_qs(parsed.query)
        forward_qs = urllib.parse.urlencode(query, doseq=True)
        upstream_url = f"{WIT_URL}?{forward_qs}" if forward_qs else WIT_URL

        request = urllib.request.Request(upstream_url)
        request.add_header("Authorization", f"Bearer {WIT_TOKEN}")

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            data = {"entities": {}, "traits": {}, "text": query.get("q", [""])[0]}

        data["intents"] = [{"id": "0", "name": FORCED_INTENT, "confidence": 1.0}]

        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - matches BaseHTTPRequestHandler signature
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    server.serve_forever()
