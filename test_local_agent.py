#!/usr/bin/env python3
"""Google Antigravity SDK - Local Ollama Agent Example.

Directly implements the official example from:
https://github.com/google-antigravity/antigravity-sdk-python/blob/main/examples/getting_started/local_models.py
and
https://antigravity.google/docs/sdk/local-models/

Usage:
    python3 test_local_agent.py [--model gemma4:26b] [--base_url http://localhost:11434/v1] [--prompt "Your prompt"]
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request


async def run_antigravity_agent(model: str, base_url: str, prompt: str):
    """Runs a local agent using google.antigravity.LocalOpenAIAgentConfig."""
    try:
        from google.antigravity import Agent, LocalOpenAIAgentConfig
    except ImportError:
        print("[ERROR] 'google-antigravity' is not installed in the current Python environment.")
        print(f"Install it with: {sys.executable} -m pip install google-antigravity")
        return False

    print(f"\n[1/3] Initializing LocalOpenAIAgentConfig...")
    print(f"      Model:    {model}")
    print(f"      Base URL: {base_url}")

    # Official pattern from https://antigravity.google/docs/sdk/local-models/
    # LocalOpenAIAgentConfig applies lightweight preset via .lightweight()
    config = LocalOpenAIAgentConfig(
        model=model,
        base_url=base_url,
    ).lightweight()

    print(f"[2/3] Connecting Agent session to local server...")
    async with Agent(config=config) as agent:
        print(f"[3/3] Sending prompt: \"{prompt}\"")
        print("\n" + "=" * 60)
        print("AGENT STREAMING RESPONSE:")
        print("=" * 60)

        response = await agent.chat(prompt)
        async for token in response:
            print(token, end="", flush=True)
        print("\n" + "=" * 60)

    print("\n[SUCCESS] Antigravity Agent executed cleanly with return code 0.")
    return True


def run_fallback_direct_test(model: str, base_url: str, prompt: str):
    """Fallback verification using Ollama's OpenAI-compatible endpoint directly."""
    print(f"\n[INFO] Running direct OpenAI-compatible API test against {base_url}/chat/completions...")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "AntigravityLocalTest"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("\n" + "=" * 60)
            print("OLLAMA STREAMING RESPONSE:")
            print("=" * 60)
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    data = json.loads(line_str[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    print(delta, end="", flush=True)
            print("\n" + "=" * 60)
            print("\n[SUCCESS] Ollama OpenAI-compatible server responded successfully.")
            return True
    except Exception as e:
        print(f"\n[ERROR] Direct call to {url} failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Google Antigravity Local Ollama Agent")
    parser.add_argument("--model", default="gemma4:26b", help="Model registered in Ollama (default: gemma4:26b)")
    parser.add_argument("--base_url", default="http://localhost:11434/v1", help="Ollama OpenAI endpoint (default: http://localhost:11434/v1)")
    parser.add_argument("--prompt", default="Explain Python generators in one concise sentence.", help="Prompt to send")
    parser.add_argument("--direct", action="store_true", help="Force direct OpenAI API test without SDK")
    args = parser.parse_args()

    # Check if SDK is available
    sdk_available = False
    try:
        import google.antigravity
        sdk_available = True
    except ImportError:
        pass

    if args.direct or not sdk_available:
        if not sdk_available and not args.direct:
            print("[NOTICE] 'google-antigravity' SDK not found; using direct Ollama OpenAI endpoint test.")
        success = run_fallback_direct_test(args.model, args.base_url, args.prompt)
    else:
        success = asyncio.run(run_antigravity_agent(args.model, args.base_url, args.prompt))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
