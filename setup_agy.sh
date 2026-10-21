#!/bin/bash

# Ensure script stops on errors
set -e

echo "=== Google Antigravity & Ollama Environment Setup ==="

# 1. System Check
echo "Checking system architecture..."
ARCH=$(uname -m)
OS=$(uname -s)

if [ "$OS" != "Darwin" ]; then
    echo "Error: This script is configured specifically for macOS."
    exit 1
fi

if [ "$ARCH" != "arm64" ]; then
    echo "Warning: Optimized Apple Silicon (M-series) environment not detected."
else
    echo "✓ Apple Silicon detected ($ARCH)."
fi

# 2. Check Memory (Unified RAM Allocation)
RAM_GB=$(sysctl hw.memsize | awk '{print $2/1073741824}')
echo "System RAM: ${RAM_GB} GB"
if (( $(echo "$RAM_GB < 16" | bc -l) )); then
    echo "Warning: Local model execution requires substantial RAM. 24GB+ is highly recommended."
else
    echo "✓ RAM matches local execution benchmarks."
fi

# 3. Check / Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew or download Ollama from https://ollama.com"
        exit 1
    fi
    brew install ollama
else
    echo "✓ Ollama is already installed."
fi

# Ensure Ollama service is active
echo "Verifying Ollama background service status..."
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama background process..."
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Pull an optimized model for your 24GB setup (Gemma 4 26B or similar base)
echo "Pulling optimized local target model..."
ollama pull gemma4:26b

# 4. Set up Python Environment & Antigravity SDK
echo "Initializing Python environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing Google Antigravity SDK..."
pip install --upgrade pip
pip install google-antigravity

# 5. Generate the Integration Test Script
echo "Creating python agent script: antigravity_ollama_agent.py"
cat << 'EOF' > antigravity_ollama_agent.py
import asyncio
from google.antigravity import Agent
from google.antigravity.config import LocalOpenAIAgentConfig

async def test_local_agent():
    print("Initializing LocalOpenAIAgentConfig pointing to Ollama endpoint...")
    
    # Configure the Antigravity agent to communicate with the local Ollama loopback server
    config = LocalOpenAIAgentConfig(
        base_url="http://localhost:11434/v1",
        model="gemma4:26b",
        context_window=64000
    )
    
    print("Launching agentic validation runtime...")
    async with Agent(config) as agent:
        response = await agent.chat("Confirm local system connection status and list system parameters.")
        async for token in response:
            print(token, end="", flush=True)
        print("\n")

if __name__ == "__main__":
    asyncio.run(test_local_agent())
EOF

echo "====================================================="
echo "Setup Complete!"
echo "To run your agent, execute the following commands:"
echo "  source .venv/bin/activate"
echo "  python antigravity_ollama_agent.py"
echo "====================================================="
