# Antigravity_Ollama: Google Antigravity & Ollama Installation Doctor

Customization of Antigravity for using local-run Ollama installation.

An interactive diagnostic, remediation, and verification app for Google Antigravity running with local Ollama models on-device.

Based on official specifications:
1. [Google Antigravity SDK - local_models.py](https://github.com/google-antigravity/antigravity-sdk-python/blob/main/examples/getting_started/local_models.py)
2. [Google Antigravity Local Models Documentation](https://antigravity.google/docs/sdk/local-models/)

---

## Features

- **Full System & Hardware Audit:**
  - Operating system & architecture detection (macOS Apple Silicon Metal vs CUDA GPU / CPU).
  - Unified Memory (RAM) calculation against model requirements (24GB+ for Gemma 4 26B, 16GB for 9B–14B, 8GB for 3B).
- **Python & Virtual Environment Audit:**
  - Python 3.10+ compliance.
  - Virtual environment (`.venv`) isolation status.
- **Antigravity SDK & CLI Audit:**
  - Antigravity CLI (`agy`) binary and version check.
  - `google-antigravity` Python package installation & import verification (`Agent`, `LocalOpenAIAgentConfig`).
- **Ollama Server & Endpoint Audit:**
  - `ollama` executable & app bundle detection.
  - Daemon service health check on `http://localhost:11434`.
  - OpenAI compatibility endpoint verification on `http://localhost:11434/v1`.
- **Model Compatibility & Inventory:**
  - Checks for recommended Google Antigravity models (`gemma4:26b`, `gemma2:9b`, `llama3.1`, etc.).
- **Explicit User Confirmation Flow:**
  - The app **never** modifies the system without asking the user first.
  - Prompts for confirmation before starting Ollama, installing packages, creating virtual environments, or pulling models.
- **Live End-to-End Agent Verification:**
  - Executes a live test session using `LocalOpenAIAgentConfig(model=..., base_url="http://localhost:11434/v1").lightweight()` and validates token streaming with clean return code 0.

---

## Getting Started

### Option 1: Interactive Terminal Doctor (CLI)

Run the standalone interactive doctor:

```bash
./doctor.py
```

Options:
- `./doctor.py --check-only`: Runs all diagnostic checks and prints summary without interactive remediation.
- `./doctor.py --auto-fix`: Automatically executes recommended fixes without manual prompting.
- `./doctor.py --json`: Outputs full diagnostic audit in JSON.

---

### Option 2: Modern Web Dashboard (GUI)

Start the local dashboard server (zero external pip dependencies required):

```bash
python3 server.py
```

Then open your browser at:
👉 **[http://localhost:8080](http://localhost:8080)**

Features in Web Dashboard:
- Visual status cards and real-time hardware meter.
- Actionable remediation buttons with modal confirmation dialogs.
- Ollama model manager & model puller.
- Interactive Antigravity Agent test runner with live output streaming.
- Real-time diagnostic activity terminal log.

---

### Option 3: Standalone Test Agent Runner

To test running an agent with your local Ollama model directly:

```bash
python3 test_local_agent.py --model gemma4:26b --prompt "Explain Python generators in one concise sentence."
```

---

## Official Antigravity Local Model Configuration Reference

```python
import asyncio
from google.antigravity import Agent, LocalOpenAIAgentConfig

async def main():
    # Configure agent for local Ollama server
    config = LocalOpenAIAgentConfig(
        model="gemma4:26b",
        base_url="http://localhost:11434/v1",
    ).lightweight()

    async with Agent(config=config) as agent:
        response = await agent.chat("Explain Python generators in one concise sentence.")
        async for token in response:
            print(token, end="", flush=True)
        print()

if __name__ == "__main__":
    asyncio.run(main())
```
