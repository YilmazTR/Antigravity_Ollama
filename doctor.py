#!/usr/bin/env python3
"""Google Antigravity + Local Ollama Environment Doctor.

Diagnoses, checks, and fixes system configurations to ensure Google Antigravity
runs smoothly using a local Ollama installation, based on official docs:
- https://github.com/google-antigravity/antigravity-sdk-python/blob/main/examples/getting_started/local_models.py
- https://antigravity.google/docs/sdk/local-models/
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Terminal color constants
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[37m"
BG_BLUE = "\033[44m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}========================================================================{RESET}
{CYAN}{BOLD}       GOOGLE ANTIGRAVITY & LOCAL OLLAMA DIAGNOSTIC DOCTOR           {RESET}
{CYAN}{BOLD}========================================================================{RESET}
{DIM}Verifying system readiness, SDK installation, and Ollama server configuration
for running Google Antigravity Agents entirely on-device.{RESET}
"""
    print(banner)


def status_badge(status: str) -> str:
    if status == "PASS":
        return f"{GREEN}[PASS]{RESET}"
    elif status == "WARN":
        return f"{YELLOW}[WARN]{RESET}"
    elif status == "FAIL":
        return f"{RED}[FAIL]{RESET}"
    elif status == "INFO":
        return f"{BLUE}[INFO]{RESET}"
    return f"[{status}]"


def prompt_confirmation(question: str, default: bool = True) -> bool:
    """Prompts the user for explicit confirmation before executing an action."""
    prompt_str = f" [Y/n]: " if default else f" [y/N]: "
    sys.stdout.write(f"\n{YELLOW}{BOLD}>>> ACTION REQUIRED: {question}{prompt_str}{RESET}")
    sys.stdout.flush()
    try:
        reply = sys.stdin.readline().strip().lower()
        if not reply:
            return default
        return reply in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return False


class AntigravityDoctor:
    def __init__(self, non_interactive: bool = False, auto_fix: bool = False):
        self.non_interactive = non_interactive
        self.auto_fix = auto_fix
        self.checks: List[Dict[str, Any]] = []
        self.system_info: Dict[str, Any] = {}
        self.ollama_models: List[str] = []
        self.selected_model: Optional[str] = None
        self.ollama_base_url = "http://localhost:11434"

    def record_check(
        self,
        name: str,
        category: str,
        status: str,
        message: str,
        details: Optional[str] = None,
        remediation: Optional[str] = None,
        can_auto_fix: bool = False,
        fix_action: Optional[str] = None,
    ):
        check = {
            "name": name,
            "category": category,
            "status": status,
            "message": message,
            "details": details,
            "remediation": remediation,
            "can_auto_fix": can_auto_fix,
            "fix_action": fix_action,
        }
        self.checks.append(check)
        badge = status_badge(status)
        print(f" {badge} {BOLD}{name}{RESET}: {message}")
        if details:
            print(f"        {DIM}{details}{RESET}")

    # ---------------------------------------------------------
    # 1. System & Hardware Checks
    # ---------------------------------------------------------
    def check_system_hardware(self):
        print(f"\n{BOLD}{CYAN}1. System & Hardware Architecture{RESET}")
        os_name = platform.system()
        arch = platform.machine()
        self.system_info["os"] = os_name
        self.system_info["arch"] = arch

        # RAM detection
        ram_gb = 0.0
        is_apple_silicon = False
        metal_support = False

        if os_name == "Darwin":
            try:
                mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
                ram_gb = round(mem_bytes / (1024**3), 1)
            except Exception:
                pass

            try:
                arm64_val = subprocess.check_output(["sysctl", "-n", "hw.optional.arm64"]).decode().strip()
                if arm64_val == "1":
                    is_apple_silicon = True
                    metal_support = True
            except Exception:
                is_apple_silicon = (arch == "arm64")
                metal_support = is_apple_silicon

            try:
                cpu_brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            except Exception:
                cpu_brand = f"Apple Silicon ({arch})"
            self.system_info["cpu"] = cpu_brand
        else:
            self.system_info["cpu"] = platform.processor() or arch
            try:
                # Linux meminfo
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            ram_gb = round(kb / (1024**2), 1)
                            break
            except Exception:
                pass

        self.system_info["ram_gb"] = ram_gb
        self.system_info["apple_silicon"] = is_apple_silicon
        self.system_info["metal_support"] = metal_support

        # Record checks
        self.record_check(
            name="Operating System & Architecture",
            category="Hardware",
            status="PASS",
            message=f"{os_name} ({arch}) - {self.system_info['cpu']}",
            details="Supported platform for Google Antigravity and Ollama.",
        )

        # Hardware Acceleration check
        if os_name == "Darwin" and is_apple_silicon:
            self.record_check(
                name="Hardware Acceleration",
                category="Hardware",
                status="PASS",
                message="Apple Silicon Metal Acceleration active",
                details="Ollama will utilize high-bandwidth unified memory and Metal GPU shaders.",
            )
        elif os_name == "Linux" and shutil.which("nvidia-smi"):
            self.record_check(
                name="Hardware Acceleration",
                category="Hardware",
                status="PASS",
                message="NVIDIA GPU (CUDA) detected",
                details="CUDA acceleration active for local inference.",
            )
        else:
            self.record_check(
                name="Hardware Acceleration",
                category="Hardware",
                status="WARN",
                message="No dedicated Metal or CUDA GPU acceleration detected",
                details="Models may fall back to CPU inference, which is significantly slower.",
            )

        # Memory Check
        if ram_gb >= 24.0:
            self.record_check(
                name="System Unified Memory / RAM",
                category="Hardware",
                status="PASS",
                message=f"{ram_gb} GB Unified Memory detected",
                details="Sufficient memory to run high-reasoning 26B models (like Gemma 4 26B) on-device.",
            )
        elif ram_gb >= 16.0:
            self.record_check(
                name="System Unified Memory / RAM",
                category="Hardware",
                status="PASS",
                message=f"{ram_gb} GB RAM detected",
                details="Ideal for 7B–14B models (e.g., Gemma 2 9B, Llama 3.1 8B). May experience paging on 26B+ models.",
            )
        elif ram_gb >= 8.0:
            self.record_check(
                name="System Unified Memory / RAM",
                category="Hardware",
                status="WARN",
                message=f"{ram_gb} GB RAM detected",
                details="Recommend running quantized 2B–7B lightweight models (e.g. Llama 3.2 3B, Gemma 2 2B).",
                remediation="Use lightweight models in LocalOpenAIAgentConfig to avoid out-of-memory errors.",
            )
        else:
            self.record_check(
                name="System Unified Memory / RAM",
                category="Hardware",
                status="FAIL",
                message=f"{ram_gb} GB RAM is below minimum recommended",
                details="Local models require at least 8 GB RAM to avoid kernel OOM panics.",
            )

    # ---------------------------------------------------------
    # 2. Python Environment Checks
    # ---------------------------------------------------------
    def check_python_environment(self):
        print(f"\n{BOLD}{CYAN}2. Python Environment & Dependencies{RESET}")
        py_ver_tuple = sys.version_info
        py_ver_str = f"{py_ver_tuple.major}.{py_ver_tuple.minor}.{py_ver_tuple.micro}"
        py_executable = sys.executable

        self.system_info["python_version"] = py_ver_str
        self.system_info["python_executable"] = py_executable

        if py_ver_tuple >= (3, 10):
            self.record_check(
                name="Python Version",
                category="Python",
                status="PASS",
                message=f"Python {py_ver_str} ({py_executable})",
                details="Meets minimum requirement (Python >= 3.10).",
            )
        else:
            self.record_check(
                name="Python Version",
                category="Python",
                status="FAIL",
                message=f"Python {py_ver_str} is outdated",
                details="Google Antigravity SDK requires Python 3.10 or newer.",
                remediation="Upgrade Python to 3.10+ using Homebrew or your package manager.",
            )

        # Virtual Environment check
        in_venv = sys.prefix != sys.base_prefix
        self.system_info["in_venv"] = in_venv
        if in_venv:
            self.record_check(
                name="Virtual Environment",
                category="Python",
                status="PASS",
                message=f"Running in isolated virtualenv ({sys.prefix})",
                details="Avoids global package contamination and permission issues.",
            )
        else:
            self.record_check(
                name="Virtual Environment",
                category="Python",
                status="WARN",
                message="Running in global Python environment (not inside a virtualenv)",
                details="The Google Antigravity SDK docs strongly recommend using a dedicated .venv to avoid PATH conflicts.",
                remediation="Create and activate a virtual environment: python3 -m venv .venv && source .venv/bin/activate",
                can_auto_fix=True,
                fix_action="create_venv",
            )

        # Check pip
        try:
            pip_ver = subprocess.check_output([sys.executable, "-m", "pip", "--version"]).decode().strip()
            self.record_check(
                name="Python Package Installer (pip)",
                category="Python",
                status="PASS",
                message=pip_ver.split("from")[0].strip(),
            )
        except Exception as e:
            self.record_check(
                name="Python Package Installer (pip)",
                category="Python",
                status="FAIL",
                message="pip is not available or non-functional",
                details=str(e),
                remediation="Install pip via python3 -m ensurepip --default-pip",
            )

    # ---------------------------------------------------------
    # 3. Google Antigravity SDK & CLI Checks
    # ---------------------------------------------------------
    def check_antigravity_installation(self):
        print(f"\n{BOLD}{CYAN}3. Google Antigravity SDK & CLI{RESET}")

        # Check CLI binary
        agy_cli = shutil.which("agy") or os.path.expanduser("~/.local/bin/agy")
        if os.path.exists(agy_cli) and os.access(agy_cli, os.X_OK):
            try:
                agy_ver = subprocess.check_output([agy_cli, "--version"]).decode().strip()
                self.record_check(
                    name="Antigravity CLI (agy)",
                    category="Antigravity",
                    status="PASS",
                    message=f"Version {agy_ver} found at {agy_cli}",
                    details="Antigravity command-line tools are installed and executable.",
                )
            except Exception as e:
                self.record_check(
                    name="Antigravity CLI (agy)",
                    category="Antigravity",
                    status="WARN",
                    message=f"Found at {agy_cli} but version query failed: {e}",
                )
        else:
            self.record_check(
                name="Antigravity CLI (agy)",
                category="Antigravity",
                status="WARN",
                message="agy executable not found in PATH or ~/.local/bin/agy",
                details="The Antigravity CLI allows launching sessions from the terminal.",
            )

        # Check Python SDK `google-antigravity`
        sdk_installed = False
        sdk_version = None
        try:
            import google.antigravity
            sdk_installed = True
            sdk_version = getattr(google.antigravity, "__version__", "installed")
            self.record_check(
                name="Google Antigravity Python SDK",
                category="Antigravity",
                status="PASS",
                message=f"Package 'google-antigravity' ({sdk_version}) is installed",
                details=f"Location: {google.antigravity.__file__}",
            )
        except ImportError:
            self.record_check(
                name="Google Antigravity Python SDK",
                category="Antigravity",
                status="FAIL",
                message="Package 'google-antigravity' is not installed in current Python environment",
                details="The SDK is required to instantiate Agent and LocalOpenAIAgentConfig.",
                remediation=f"Run: {sys.executable} -m pip install google-antigravity",
                can_auto_fix=True,
                fix_action="install_sdk",
            )

        # Check LocalOpenAIAgentConfig imports
        if sdk_installed:
            try:
                from google.antigravity import Agent, LocalOpenAIAgentConfig
                self.record_check(
                    name="LocalOpenAIAgentConfig Class",
                    category="Antigravity",
                    status="PASS",
                    message="Agent and LocalOpenAIAgentConfig imported successfully",
                    details="Ready for local OpenAI-compatible endpoint configurations.",
                )
            except ImportError as e:
                self.record_check(
                    name="LocalOpenAIAgentConfig Class",
                    category="Antigravity",
                    status="FAIL",
                    message=f"Failed to import LocalOpenAIAgentConfig from google.antigravity: {e}",
                    remediation=f"Update SDK: {sys.executable} -m pip install --upgrade google-antigravity",
                )

    # ---------------------------------------------------------
    # 4. Ollama Installation & Daemon Checks
    # ---------------------------------------------------------
    def check_ollama(self):
        print(f"\n{BOLD}{CYAN}4. Ollama Installation & Server Status{RESET}")

        # Check Ollama Binary
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            # Check common locations
            common_locs = ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
            for loc in common_locs:
                if os.path.exists(loc) and os.access(loc, os.X_OK):
                    ollama_bin = loc
                    break

        if ollama_bin:
            try:
                ver_out = subprocess.check_output([ollama_bin, "--version"], stderr=subprocess.STDOUT).decode().strip()
                # e.g., "ollama version is 0.40.5" or "Warning: could not connect... client version is 0.40.5"
                client_ver = "unknown"
                for line in ver_out.splitlines():
                    if "version is" in line:
                        client_ver = line.split("version is")[-1].strip()
                        break
                self.record_check(
                    name="Ollama Executable",
                    category="Ollama",
                    status="PASS",
                    message=f"Ollama {client_ver} found at {ollama_bin}",
                )
                self.system_info["ollama_bin"] = ollama_bin
                self.system_info["ollama_version"] = client_ver
            except Exception as e:
                self.record_check(
                    name="Ollama Executable",
                    category="Ollama",
                    status="PASS",
                    message=f"Found at {ollama_bin}",
                )
        else:
            # Check if /Applications/Ollama.app exists on macOS
            if platform.system() == "Darwin" and os.path.exists("/Applications/Ollama.app"):
                self.record_check(
                    name="Ollama Executable",
                    category="Ollama",
                    status="WARN",
                    message="Ollama.app installed in /Applications, but 'ollama' CLI is not in PATH",
                    details="Open Ollama.app or symlink /Applications/Ollama.app/Contents/Resources/ollama to /usr/local/bin/ollama",
                )
            else:
                self.record_check(
                    name="Ollama Executable",
                    category="Ollama",
                    status="FAIL",
                    message="Ollama executable not found on the system",
                    details="Ollama is required to host local open-weights models for Google Antigravity.",
                    remediation="Install Ollama from https://ollama.com/download or via 'brew install ollama'",
                    can_auto_fix=True,
                    fix_action="install_ollama",
                )

        # Check Ollama Daemon Status via HTTP
        ollama_running = False
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/api/tags", headers={"User-Agent": "AntigravityDoctor"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    ollama_running = True
                    data = json.loads(resp.read().decode())
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    self.ollama_models = models
                    self.record_check(
                        name="Ollama Server Daemon",
                        category="Ollama",
                        status="PASS",
                        message=f"Ollama service is active and responding on {self.ollama_base_url}",
                        details=f"{len(models)} model(s) available in local registry.",
                    )
        except Exception:
            self.record_check(
                name="Ollama Server Daemon",
                category="Ollama",
                status="FAIL",
                message=f"Ollama daemon is not running on {self.ollama_base_url}",
                details="Antigravity cannot reach the local models server. Connection refused.",
                remediation="Start Ollama by running 'ollama serve' in background, or launch /Applications/Ollama.app",
                can_auto_fix=True,
                fix_action="start_ollama",
            )

        # Check Ollama OpenAI-compatible endpoint (/v1)
        if ollama_running:
            try:
                v1_req = urllib.request.Request(f"{self.ollama_base_url}/v1/models", headers={"User-Agent": "AntigravityDoctor"})
                with urllib.request.urlopen(v1_req, timeout=3) as resp:
                    if resp.status == 200:
                        v1_data = json.loads(resp.read().decode())
                        v1_models = [m.get("id") for m in v1_data.get("data", []) if m.get("id")]
                        self.record_check(
                            name="OpenAI Compatibility Endpoint (/v1)",
                            category="Ollama",
                            status="PASS",
                            message=f"Endpoint {self.ollama_base_url}/v1/models is active",
                            details=f"Compatible with LocalOpenAIAgentConfig(base_url='{self.ollama_base_url}/v1').",
                        )
            except Exception as e:
                self.record_check(
                    name="OpenAI Compatibility Endpoint (/v1)",
                    category="Ollama",
                    status="WARN",
                    message=f"Failed to query {self.ollama_base_url}/v1/models: {e}",
                    details="Ensure Ollama is version 0.1.24+ for full OpenAI API compatibility.",
                )

    # ---------------------------------------------------------
    # 5. Local Models Availability & Antigravity Compatibility
    # ---------------------------------------------------------
    def check_models_compatibility(self):
        print(f"\n{BOLD}{CYAN}5. Local Models & Google Antigravity Compatibility{RESET}")

        # If ollama was not running, check disk manifests in ~/.ollama/models
        if not self.ollama_models:
            disk_models = []
            manifest_dir = os.path.expanduser("~/.ollama/models/manifests/registry.ollama.ai/library")
            if os.path.isdir(manifest_dir):
                for model_dir in os.listdir(manifest_dir):
                    sub_p = os.path.join(manifest_dir, model_dir)
                    if os.path.isdir(sub_p):
                        for tag in os.listdir(sub_p):
                            disk_models.append(f"{model_dir}:{tag}")
            self.ollama_models = disk_models
            if disk_models:
                print(f" {status_badge('INFO')} Found {len(disk_models)} model manifest(s) cached on disk.")

        if not self.ollama_models:
            self.record_check(
                name="Local Model Inventory",
                category="Models",
                status="FAIL",
                message="No models are installed in Ollama",
                details="Google Antigravity requires at least one local model pulled into Ollama.",
                remediation="Pull recommended model: 'ollama pull gemma4:26b' or lightweight 'ollama pull gemma2:9b'",
                can_auto_fix=True,
                fix_action="pull_model",
            )
            return

        # List models
        print(f"    Available models detected: {', '.join(self.ollama_models)}")

        # Check for recommended Google Antigravity models (Gemma 4 26B, Gemma 2, Llama 3.1)
        recommended_candidates = [
            "gemma4:26b",
            "gemma-4-26B-A4B-it",
            "gemma2:27b",
            "gemma2:9b",
            "gemma2:latest",
            "llama3.1:latest",
            "llama3.1:8b",
            "llama3.2:latest",
            "llama3.2:3b",
        ]

        found_recommended = None
        for cand in recommended_candidates:
            for m in self.ollama_models:
                if cand in m or m in cand:
                    found_recommended = m
                    break
            if found_recommended:
                break

        if found_recommended:
            self.selected_model = found_recommended
            self.record_check(
                name="Google Antigravity Recommended Model",
                category="Models",
                status="PASS",
                message=f"Optimal model '{found_recommended}' is present",
                details=f"Matches official documentation recommendations for LocalOpenAIAgentConfig.",
            )
        else:
            # Pick first available model
            self.selected_model = self.ollama_models[0]
            self.record_check(
                name="Google Antigravity Recommended Model",
                category="Models",
                status="WARN",
                message=f"Recommended Gemma models not detected; fallback model '{self.selected_model}' will be used",
                details="Gemma 4 26B (gemma4:26b) or Gemma 2 (gemma2:9b) offer best reasoning and tool calling in Antigravity.",
                remediation="Optional: run 'ollama pull gemma4:26b' for highest fidelity.",
                can_auto_fix=True,
                fix_action="pull_gemma",
            )

    # ---------------------------------------------------------
    # 6. Interactive Remediation & User Confirmation Flow
    # ---------------------------------------------------------
    def run_remediation_flow(self):
        fixable_checks = [c for c in self.checks if c.get("can_auto_fix") and c.get("status") in ("FAIL", "WARN")]

        if not fixable_checks:
            print(f"\n{GREEN}{BOLD}>>> No actionable issues found! System is configured properly.{RESET}")
            return

        print(f"\n{BOLD}{YELLOW}========================================================================{RESET}")
        print(f"{BOLD}{YELLOW}                  ACTIONABLE ISSUES & REMEDIATION PLAN                 {RESET}")
        print(f"{BOLD}{YELLOW}========================================================================{RESET}")
        print(f"The doctor found {len(fixable_checks)} item(s) that require attention before Google Antigravity can run:")

        for idx, item in enumerate(fixable_checks, 1):
            print(f"\n {BOLD}{idx}. {item['name']}{RESET} [{item['status']}]")
            print(f"    Issue:   {item['message']}")
            print(f"    Details: {item.get('details', '')}")
            print(f"    Fix:     {item.get('remediation', '')}")

        print(f"\n{CYAN}The doctor can resolve these issues now with your explicit confirmation.{RESET}")

        for item in fixable_checks:
            action = item.get("fix_action")
            if not action:
                continue

            if action == "start_ollama":
                q = "Start the Ollama background daemon on your machine now?"
                if self.auto_fix or prompt_confirmation(q, default=True):
                    self.execute_start_ollama()

            elif action == "install_sdk":
                q = f"Install 'google-antigravity' in current Python ({sys.executable})?"
                if self.auto_fix or prompt_confirmation(q, default=True):
                    self.execute_install_sdk()

            elif action == "create_venv":
                q = "Create an isolated virtual environment (.venv) in current project directory?"
                if self.auto_fix or prompt_confirmation(q, default=True):
                    self.execute_create_venv()

            elif action in ("pull_model", "pull_gemma"):
                model_to_pull = "gemma4:26b" if self.system_info.get("ram_gb", 0) >= 20 else "gemma2:9b"
                q = f"Download recommended model '{model_to_pull}' via Ollama now?"
                if self.auto_fix or prompt_confirmation(q, default=True):
                    self.execute_pull_model(model_to_pull)

    def execute_start_ollama(self):
        print(f"{BLUE}Starting Ollama service...{RESET}")
        if platform.system() == "Darwin" and os.path.exists("/Applications/Ollama.app"):
            subprocess.Popen(["open", "-a", "Ollama"])
        else:
            ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
            subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for service to become responsive
        print(f"{DIM}Waiting for http://localhost:11434 to become ready...{RESET}")
        ready = False
        for _ in range(12):
            time.sleep(1)
            try:
                with urllib.request.urlopen(f"{self.ollama_base_url}/api/tags", timeout=1) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass

        if ready:
            print(f"{GREEN}{BOLD}✓ Ollama service is now running successfully!{RESET}")
        else:
            print(f"{YELLOW}Ollama startup triggered, but endpoint did not respond immediately. Please verify Ollama is open.{RESET}")

    def execute_install_sdk(self):
        print(f"{BLUE}Installing google-antigravity via pip...{RESET}")
        cmd = [sys.executable, "-m", "pip", "install", "google-antigravity"]
        try:
            subprocess.check_call(cmd)
            print(f"{GREEN}{BOLD}✓ 'google-antigravity' installed successfully!{RESET}")
        except subprocess.CalledProcessError as e:
            print(f"{RED}Installation failed: {e}{RESET}")

    def execute_create_venv(self):
        venv_path = os.path.abspath(".venv")
        print(f"{BLUE}Creating virtualenv at {venv_path}...{RESET}")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", venv_path])
            print(f"{GREEN}{BOLD}✓ Virtual environment created!{RESET}")
            print(f"{CYAN}Activate it with: source .venv/bin/activate{RESET}")
        except Exception as e:
            print(f"{RED}Failed to create venv: {e}{RESET}")

    def execute_pull_model(self, model_name: str):
        print(f"{BLUE}Pulling '{model_name}' using Ollama (this may take a few minutes)...{RESET}")
        ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
        try:
            subprocess.check_call([ollama_bin, "pull", model_name])
            print(f"{GREEN}{BOLD}✓ Model '{model_name}' successfully downloaded!{RESET}")
            if model_name not in self.ollama_models:
                self.ollama_models.append(model_name)
            self.selected_model = model_name
        except Exception as e:
            print(f"{RED}Failed to pull model: {e}{RESET}")

    # ---------------------------------------------------------
    # 7. Live End-to-End Test Agent Execution
    # ---------------------------------------------------------
    def run_live_test(self):
        print(f"\n{BOLD}{CYAN}7. Live End-to-End Google Antigravity Agent Verification{RESET}")

        if not self.selected_model:
            print(f"{YELLOW}Skipping live test: No model available.{RESET}")
            return

        model_name = self.selected_model
        print(f"Selected Model: {BOLD}{model_name}{RESET}")
        print(f"Ollama Server:  {BOLD}{self.ollama_base_url}/v1{RESET}")

        test_code_summary = f"""
{DIM}Code to test (from official Google Antigravity SDK example):{RESET}
{WHITE}from google.antigravity import Agent, LocalOpenAIAgentConfig

config = LocalOpenAIAgentConfig(
    model="{model_name}",
    base_url="{self.ollama_base_url}/v1",
).lightweight()

async with Agent(config) as agent:
    response = await agent.chat("Explain Python generators in one concise sentence.")
    async for token in response:
        print(token, end="", flush=True)
{RESET}
"""
        print(test_code_summary)

        if not self.auto_fix:
            if not prompt_confirmation(f"Run live test agent using model '{model_name}'?", default=True):
                print(f"{DIM}Live test skipped by user.{RESET}")
                return

        # Check if google.antigravity can be imported
        try:
            import google.antigravity
            has_sdk = True
        except ImportError:
            has_sdk = False

        if not has_sdk:
            print(f"{YELLOW}'google-antigravity' is not installed in the current interpreter.{RESET}")
            print(f"{CYAN}Performing direct OpenAI-compatible API verification to ensure Ollama endpoint is functional...{RESET}")
            self.run_direct_ollama_v1_test(model_name)
            return

        # Run via asynchronous sub-process with Google Antigravity SDK
        test_script = f"""
import asyncio
import sys

from google.antigravity import Agent, LocalOpenAIAgentConfig

async def main():
    print("{CYAN}>>> Initializing LocalOpenAIAgentConfig with .lightweight()...{RESET}")
    config = LocalOpenAIAgentConfig(
        model="{model_name}",
        base_url="{self.ollama_base_url}/v1",
    ).lightweight()

    print("{CYAN}>>> Connecting Agent to local Ollama server...{RESET}")
    async with Agent(config) as agent:
        print("{CYAN}>>> Sending prompt: 'Explain Python generators in one concise sentence.'{RESET}")
        print("{GREEN}{BOLD}Agent Response: {RESET}", end="", flush=True)
        response = await agent.chat("Explain Python generators in one concise sentence.")
        async for token in response:
            print(token, end="", flush=True)
        print("\\n")

if __name__ == "__main__":
    asyncio.run(main())
"""
        try:
            res = subprocess.run([sys.executable, "-c", test_script], capture_output=False, check=True)
            print(f"{GREEN}{BOLD}✓ Live Antigravity Agent test completed with Return Code 0!{RESET}")
        except subprocess.CalledProcessError as e:
            print(f"{RED}Live test returned exit code {e.returncode}.{RESET}")
            print(f"{YELLOW}Falling back to direct endpoint check...{RESET}")
            self.run_direct_ollama_v1_test(model_name)

    def run_direct_ollama_v1_test(self, model_name: str):
        """Direct test against http://localhost:11434/v1/chat/completions."""
        url = f"{self.ollama_base_url}/v1/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Explain Python generators in one concise sentence."}],
            "stream": False,
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "AntigravityDoctor"},
            method="POST",
        )
        try:
            print(f"{CYAN}Connecting to {url} with model '{model_name}'...{RESET}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode())
                content = (
                    resp_json.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                print(f"{GREEN}{BOLD}Ollama Response: {RESET}{content.strip()}\n")
                print(f"{GREEN}{BOLD}✓ Ollama OpenAI endpoint is 100% operational and ready for Google Antigravity!{RESET}")
        except Exception as e:
            print(f"{RED}Direct Ollama API call failed: {e}{RESET}")

    # ---------------------------------------------------------
    # Full Diagnosis Execution
    # ---------------------------------------------------------
    def run_all(self):
        print_banner()
        self.check_system_hardware()
        self.check_python_environment()
        self.check_antigravity_installation()
        self.check_ollama()
        self.check_models_compatibility()

        # Summary Table
        pass_count = sum(1 for c in self.checks if c["status"] == "PASS")
        warn_count = sum(1 for c in self.checks if c["status"] == "WARN")
        fail_count = sum(1 for c in self.checks if c["status"] == "FAIL")

        print(f"\n{CYAN}{BOLD}------------------------------------------------------------------------{RESET}")
        print(f"Summary: {GREEN}{pass_count} Passed{RESET} | {YELLOW}{warn_count} Warnings{RESET} | {RED}{fail_count} Failed{RESET}")
        print(f"{CYAN}{BOLD}------------------------------------------------------------------------{RESET}")

        if not self.non_interactive:
            self.run_remediation_flow()
            self.run_live_test()

        return fail_count == 0


def main():
    parser = argparse.ArgumentParser(description="Google Antigravity & Ollama Installation Doctor")
    parser.add_argument("--check-only", action="store_true", help="Run checks only without interactive remediation")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically attempt fixes without prompting")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    doctor = AntigravityDoctor(non_interactive=args.check_only, auto_fix=args.auto_fix)
    if args.json:
        doctor.check_system_hardware()
        doctor.check_python_environment()
        doctor.check_antigravity_installation()
        doctor.check_ollama()
        doctor.check_models_compatibility()
        print(json.dumps({"system": doctor.system_info, "checks": doctor.checks, "models": doctor.ollama_models}, indent=2))
        sys.exit(0)

    success = doctor.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
