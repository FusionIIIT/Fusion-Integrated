"""Helper to query the local Ollama Qwen2.5:7b model from inside WSL or host."""

import os
import sys

import requests


def get_ollama_host() -> str:
    host = os.environ.get("OLLAMA_HOST")
    if host:
        return host if host.startswith("http") else f"http://{host}"
    try:
        requests.get("http://localhost:11434/api/tags", timeout=1)
    except (requests.RequestException, OSError):
        pass
    else:
        return "http://localhost:11434"
    return "http://172.29.112.1:11434"


def query_ollama(prompt: str, model: str = "qwen2.5:7b") -> str:
    host = get_ollama_host()
    url = f"{host}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(url, json=payload, timeout=120)
    data = resp.json()
    return str(data.get("response", ""))


def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.exists(arg):
            with open(arg, encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = " ".join(sys.argv[1:])
    else:
        prompt_text = sys.stdin.read()
    print(query_ollama(prompt_text))


if __name__ == "__main__":
    main()
