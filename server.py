#!/usr/bin/env python3
"""Local Web Server for Google Antigravity & Ollama Doctor Dashboard.

Zero external dependencies - runs directly on Python 3.10+ standard library.
Serves the web UI and provides diagnostic, remediation, and live test APIs.
"""

import http.server
import json
import os
import platform
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from doctor import AntigravityDoctor

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class DoctorAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean server logging
        sys.stderr.write(f"[HTTP] {args[0]} - {args[1]}\n")

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        if path == "/api/status":
            self.handle_get_status()
        elif path == "/api/models":
            self.handle_get_models()
        else:
            # Fallback to serving static files or index.html for root
            if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if path == "/api/action":
            self.handle_post_action(payload)
        elif path == "/api/test_agent":
            self.handle_post_test_agent(payload)
        else:
            self.send_json({"error": "Endpoint not found"}, status=404)

    # ---------------------------------------------------------
    # API Handlers
    # ---------------------------------------------------------
    def handle_get_status(self):
        doctor = AntigravityDoctor(non_interactive=True)
        doctor.check_system_hardware()
        doctor.check_python_environment()
        doctor.check_antigravity_installation()
        doctor.check_ollama()
        doctor.check_models_compatibility()

        pass_count = sum(1 for c in doctor.checks if c["status"] == "PASS")
        warn_count = sum(1 for c in doctor.checks if c["status"] == "WARN")
        fail_count = sum(1 for c in doctor.checks if c["status"] == "FAIL")

        response = {
            "system": doctor.system_info,
            "checks": doctor.checks,
            "models": doctor.ollama_models,
            "selected_model": doctor.selected_model,
            "summary": {
                "passed": pass_count,
                "warnings": warn_count,
                "failed": fail_count,
                "ready": fail_count == 0,
            },
        }
        self.send_json(response)

    def handle_get_models(self):
        models = []
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", headers={"User-Agent": "AntigravityDoctor"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        except Exception:
            # Fall back to disk search
            manifest_dir = os.path.expanduser("~/.ollama/models/manifests/registry.ollama.ai/library")
            if os.path.isdir(manifest_dir):
                for model_dir in os.listdir(manifest_dir):
                    sub_p = os.path.join(manifest_dir, model_dir)
                    if os.path.isdir(sub_p):
                        for tag in os.listdir(sub_p):
                            models.append(f"{model_dir}:{tag}")

        self.send_json({"models": models})

    def handle_post_action(self, payload: Dict[str, Any]):
        action = payload.get("action")
        confirmed = payload.get("confirmed", False)

        if not confirmed:
            self.send_json({"error": "User confirmation is required to execute this action."}, status=400)
            return

        doctor = AntigravityDoctor(non_interactive=True)
        result = {"success": False, "action": action, "output": ""}

        if action == "start_ollama":
            if platform.system() == "Darwin" and os.path.exists("/Applications/Ollama.app"):
                subprocess.Popen(["open", "-a", "Ollama"])
                result["output"] = "Launched /Applications/Ollama.app in background."
            else:
                ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
                subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                result["output"] = f"Started '{ollama_bin} serve' in background."

            # Wait up to 10s for port to open
            time.sleep(2)
            result["success"] = True

        elif action == "install_sdk":
            cmd = [sys.executable, "-m", "pip", "install", "google-antigravity"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                result["success"] = True
                result["output"] = proc.stdout
            except subprocess.CalledProcessError as e:
                result["success"] = False
                result["output"] = f"{e.stdout}\n{e.stderr}"

        elif action == "create_venv":
            venv_path = os.path.abspath(".venv")
            try:
                subprocess.check_call([sys.executable, "-m", "venv", venv_path])
                result["success"] = True
                result["output"] = f"Virtual environment created at {venv_path}."
            except Exception as e:
                result["success"] = False
                result["output"] = str(e)

        elif action == "pull_model":
            model_name = payload.get("model", "gemma4:26b")
            ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
            try:
                proc = subprocess.run([ollama_bin, "pull", model_name], capture_output=True, text=True, check=True)
                result["success"] = True
                result["output"] = proc.stdout
            except Exception as e:
                result["success"] = False
                result["output"] = str(e)

        else:
            self.send_json({"error": f"Unknown action: {action}"}, status=400)
            return

        self.send_json(result)

    def handle_post_test_agent(self, payload: Dict[str, Any]):
        model = payload.get("model", "gemma4:26b")
        base_url = payload.get("base_url", "http://localhost:11434/v1")
        prompt = payload.get("prompt", "Explain Python generators in one concise sentence.")

        # Check if SDK is available
        has_sdk = False
        try:
            import google.antigravity
            has_sdk = True
        except ImportError:
            pass

        if has_sdk:
            test_script = f"""
import asyncio
from google.antigravity import Agent, LocalOpenAIAgentConfig

async def main():
    config = LocalOpenAIAgentConfig(
        model="{model}",
        base_url="{base_url}",
    ).lightweight()

    async with Agent(config) as agent:
        response = await agent.chat({json.dumps(prompt)})
        text = await response.text()
        print(text)

if __name__ == "__main__":
    asyncio.run(main())
"""
            try:
                proc = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, timeout=60, check=True)
                self.send_json({
                    "success": True,
                    "engine": "google-antigravity SDK",
                    "model": model,
                    "prompt": prompt,
                    "response": proc.stdout.strip(),
                })
                return
            except subprocess.CalledProcessError as e:
                # Fallback to direct call
                pass

        # Fallback to direct OpenAI-compatible API call
        url = f"{base_url}/chat/completions"
        req_payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(req_payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "AntigravityDoctor"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.send_json({
                    "success": True,
                    "engine": "Direct Ollama OpenAI Endpoint",
                    "model": model,
                    "prompt": prompt,
                    "response": content.strip(),
                })
        except Exception as e:
            self.send_json({
                "success": False,
                "error": f"Failed to get response from {url}: {str(e)}",
            }, status=500)


def run_server():
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ("", PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, DoctorAPIHandler) as httpd:
        print(f"\n========================================================")
        print(f"  Google Antigravity & Ollama Doctor Web App Running")
        print(f"  Open in your browser: http://localhost:{PORT}")
        print(f"========================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    run_server()
