#!/usr/bin/env python3
"""
Local telemetry server for testing with Neon database.

This server accepts telemetry events and stores them in Neon PostgreSQL.
It's a local replica of the Vercel serverless function.

Run this in one terminal:
    DATABASE_URL="postgresql://..." python3 local_telemetry_server.py

Then in another terminal, run otpilot with:
    OTPILOT_TELEMETRY_ENDPOINT=http://localhost:8080/api/telemetry otpilot version
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("❌ psycopg not installed. Install with: pip install psycopg[binary]")
    sys.exit(1)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    print("   Set it to your Neon connection string:")
    print('   export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"')
    sys.exit(1)

# Allowed events and commands (matching the schema)
ALLOWED_EVENTS = {"app_started", "command_executed", "telemetry_enabled", "telemetry_disabled"}
ALLOWED_COMMANDS = {"fetch", "watch", "hotkey", "login", "logout", "config", "doctor", "version", "telemetry"}


class TelemetryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/telemetry":
            self.send_response(404)
            self.end_headers()
            return

        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self.send_response(415)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Content-Type must be application/json"}')
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1024:
            self.send_response(413)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Payload too large"}')
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        # Validate required fields
        required = ["installation_id", "event", "version", "python_version", "os", "architecture", "timestamp"]
        for field in required:
            if field not in body:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(f'{{"error": "Missing field: {field}"}}'.encode())
                return

        if body["event"] not in ALLOWED_EVENTS:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid event type"}')
            return

        if "command" in body and body["command"] not in ALLOWED_COMMANDS:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid command"}')
            return

        # Store in Neon database
        try:
            with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    # Extract extra fields
                    known_fields = {"installation_id", "event", "version", "python_version", "os", "architecture", "timestamp", "command"}
                    extra = {k: v for k, v in body.items() if k not in known_fields}

                    cur.execute("""
                        INSERT INTO telemetry_events (
                            installation_id, event, version, python_version,
                            os, architecture, timestamp, command, extra
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        body["installation_id"],
                        body["event"],
                        body["version"],
                        body["python_version"],
                        body["os"],
                        body["architecture"],
                        body["timestamp"],
                        body.get("command"),
                        json.dumps(extra) if extra else None,
                    ))
                    conn.commit()
        except Exception as e:
            print(f"❌ Database error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Database error"}')
            return

        # Print received event
        print(f"\n📥 Received telemetry:")
        print(f"   Event: {body['event']}")
        print(f"   Installation ID: {body['installation_id'][:8]}...")
        print(f"   Version: {body['version']}")
        print(f"   OS: {body['os']} ({body['architecture']})")
        print(f"   Python: {body['python_version']}")
        if "command" in body:
            print(f"   Command: {body['command']}")

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"accepted": true}')

    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass


def run_server(port=8080):
    server = HTTPServer(("localhost", port), TelemetryHandler)
    print(f"🚀 Local telemetry server running on http://localhost:{port}/api/telemetry")
    print(f"   Using Neon database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    print(f"   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped")


if __name__ == "__main__":
    run_server()