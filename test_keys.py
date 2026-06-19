import os
import httpx
from dotenv import load_dotenv

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")

print("Checking OPENAI_API_KEY...")
if openai_key:
    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 5}
    try:
        response = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("OPENAI OK!")
    except Exception as e:
        print(f"OPENAI Failed: {e}")
else:
    print("OPENAI_API_KEY not found.")

print("Checking ANTHROPIC_API_KEY...")
if anthropic_key:
    headers = {"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    payload = {"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 5}
    try:
        response = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("ANTHROPIC OK!")
    except Exception as e:
        print(f"ANTHROPIC Failed: {e}")
else:
    print("ANTHROPIC_API_KEY not found.")
