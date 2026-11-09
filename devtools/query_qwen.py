import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\rohan\Documents\Codex\2026-10-11\documents-plugin-documents-openai-primary-runtime-2\outputs\ELM_Qwen25Coder7B")
LOG_FILE = REPO / "PHASE2_MODEL_INTERACTION_EVIDENCE.md"
MODEL = "qwen2.5-coder:7b"

def query_model(prompt: str, max_tokens: int = 1200) -> str:
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096, "num_predict": max_tokens}
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["response"].strip()

def record_interaction(stage: str, prompt: str, response: str):
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## Stage: {stage}\n\n### Prompt\n\n```text\n{prompt}\n```\n\n### Model Response\n\n```python\n{response}\n```\n")

if __name__ == "__main__":
    prompt = sys.stdin.read()
    stage = sys.argv[1]
    print(f"Querying {MODEL} for stage: {stage}...")
    t0 = time.time()
    response = query_model(prompt)
    print(f"Response received in {round(time.time() - t0, 2)}s")
    record_interaction(stage, prompt, response)
    print(response)
