import json
from pathlib import Path
from urllib.request import Request, urlopen

root = Path.cwd()
prompt = (root / "audit/prompts/fix01_prompt.txt").read_text(encoding="utf-8")
source = (root / "modules/leave/registry.py").read_text(encoding="utf-8")
request = Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps({
        "model": "qwen14b-hybrid",
        "prompt": f"{prompt}\nFILE:\n{source}",
        "stream": False,
        "options": {"num_gpu": 8, "num_ctx": 4096, "num_predict": 1200,
                    "temperature": 0.1},
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=1800) as response:
    result = json.load(response)
answer = result.get("response", "")
(root / "audit/prompts/fix01_answer_api.md").write_text(answer, encoding="utf-8")
print(f"saved {len(answer)} chars; done={result.get('done')}; eval_count={result.get('eval_count')}")

