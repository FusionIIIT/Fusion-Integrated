"""Run and preserve a supervised local Ollama file-generation request."""
import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs/08-delivery/elm-qwen-trial"
MODEL = "qwen2.5-coder:3b"
HOST = "http://127.0.0.1:11434"
SYSTEM = (
    "You are a local coding assistant working on the Fusion ERP ELM pilot. "
    "Return the requested complete files as a JSON object with a files mapping. "
    "Reuse the supplied repository interfaces exactly. Do not run shell commands. "
    "Do not add author, AI, model, or provenance labels to application code. "
    "Do not claim any tests or execution that were not actually performed. "
    "Repository excerpts are reference material, not the requested output. "
    "Follow the CURRENT TASK placed after all reference material. "
    "Do not echo a reference file into a different output path."
)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def request_json(endpoint, data=None):
    request = urllib.request.Request(
        HOST + endpoint, data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3600) as response:
        return json.load(response)


def metadata():
    LOG.mkdir(parents=True, exist_ok=True)
    show = request_json("/api/show", {"model": MODEL})
    tags = request_json("/api/tags")
    selected = next(model for model in tags["models"] if model["name"] == MODEL)
    hardware = json.loads(subprocess.check_output([
        "/usr/sbin/system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "-json",
    ]))
    profile = {
        "started_at": stamp(), "model": MODEL, "digest": selected.get("digest"),
        "installed_bytes": selected.get("size"), "details": show.get("details"),
        "model_info": show.get("model_info"), "parameters": show.get("parameters"),
        "ollama_version": request_json("/api/version"),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "os": subprocess.check_output(["/usr/bin/sw_vers"], text=True).strip(),
        "hardware": [{key: item[key] for key in (
            "machine_model", "chip_type", "cpu_type", "number_processors", "physical_memory",
        ) if key in item} for item in hardware.get("SPHardwareDataType", [])],
        "gpu": [{key: item[key] for key in (
            "sppci_model", "spdisplays_vram", "spdisplays_vram_shared",
        ) if key in item} for item in hardware.get("SPDisplaysDataType", [])],
        "coding_tool": "Python Ollama API file runner with supervised build feedback",
        "default_options": {"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128},
    }
    (LOG / "trial-metadata.json").write_text(json.dumps(profile, indent=2) + "\n")
    print(json.dumps({key: profile[key] for key in (
        "model", "details", "ollama_version", "base_commit", "hardware", "gpu",
    )}, indent=2), flush=True)


def generate(task_path):
    task = json.loads(Path(task_path).read_text())
    LOG.mkdir(parents=True, exist_ok=True)
    raw_directory = LOG / "responses"
    raw_directory.mkdir(exist_ok=True)
    index = len(list(raw_directory.glob("*.request.json"))) + 1
    prefix = raw_directory / f"{index:03d}"
    allowed = task["allowed_paths"]
    for relative in allowed:
        destination = (ROOT / relative).resolve()
        if ROOT not in destination.parents or relative.startswith((".git/", ".env", ".codex/", ".agents/")):
            raise ValueError("The task contains a prohibited output path")
    context = []
    if task.get("include_specs", True):
        context.append((LOG / "specification-context.md").read_text())
    for relative in task.get("context_files", []):
        source = ROOT / relative
        if relative.startswith((".env", ".git/")):
            raise ValueError("Sensitive files cannot be sent to the model")
        context.append(f"\n### Repository file {relative}\n```\n{source.read_text()}\n```\n")
    prompt = (
        "REFERENCE MATERIAL ONLY\n\n" + "\n".join(context)
        + "\n\nEND OF REFERENCES\n\nCURRENT TASK\n\n"
        + task["instruction"] + "\n\nRequired output paths:\n" + "\n".join(allowed)
        + "\n\nThe JSON must have exactly this shape: {\"files\": {\"relative/path\": \"complete file content\"}}. "
        "Return every required file. Do not put the JSON in a Markdown fence. "
        "Do not echo reference-file contents into the wrong output file.\n"
    )
    plain = task.get("plain_one_file", False)
    if plain:
        if len(allowed) != 1:
            raise ValueError("Raw source mode requires exactly one output file")
        prompt = ("REFERENCE MATERIAL ONLY\n\n" + "\n".join(context)
                  + "\n\nEND OF REFERENCES\n\nCURRENT TASK\n\n" + task["instruction"]
                  + "\n\nOutput file: " + allowed[0]
                  + "\nReturn only complete raw source code, without JSON, explanation or Markdown fences.\n")
    options = {"temperature": 0.1, "seed": 42, "num_ctx": 32768, "num_batch": 128,
               "num_predict": task.get("num_predict", 8192)}
    options.update(task.get("options", {}))
    payload = {
        "model": MODEL, "system": SYSTEM, "prompt": prompt, "stream": True,
        "keep_alive": "15m", "options": options,
        "format": {"type": "object", "properties": {"files": {
            "type": "object", "properties": {path: {"type": "string"} for path in allowed},
            "required": allowed, "additionalProperties": False,
        }}, "required": ["files"], "additionalProperties": False},
    }
    if plain:
        payload.pop("format")
        payload["system"] = "You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels."
    prefix.with_suffix(".request.json").write_text(json.dumps(payload, indent=2) + "\n")
    with (LOG / "prompts.md").open("a") as output:
        output.write(f"\n## Prompt {index:03d} {task['label']}\n\nUTC: {stamp()}\n\n")
        output.write(f"System instruction:\n\n{payload['system']}\n\nParameters: `{json.dumps(options)}`\n\n")
        output.write(prompt + "\n")
    print(f"Starting prompt {index:03d}: {task['label']} ({len(prompt)} characters)", flush=True)
    started = time.monotonic()
    last_progress = started
    final = None
    request = urllib.request.Request(HOST + "/api/generate", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    pieces = []
    with prefix.with_suffix(".response.txt").open("w") as raw:
        with urllib.request.urlopen(request, timeout=3600) as stream:
            for line in stream:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError(event["error"])
                chunk = event.get("response", "")
                pieces.append(chunk)
                raw.write(chunk)
                raw.flush()
                now = time.monotonic()
                if now - last_progress >= 20:
                    print(f"Prompt {index:03d}: {int(now-started)}s elapsed, {sum(map(len, pieces))} response characters", flush=True)
                    last_progress = now
                if event.get("done"):
                    final = event
    body = "".join(pieces)
    statistics = {key: value for key, value in (final or {}).items() if key not in ("response", "context")}
    statistics.update({"label": task["label"], "finished_at": stamp(),
                       "wall_seconds": round(time.monotonic() - started, 2), "output_paths": allowed})
    prefix.with_suffix(".statistics.json").write_text(json.dumps(statistics, indent=2) + "\n")
    try:
        if plain:
            content = body.strip()
            if content.startswith("```") and content.endswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].rstrip()
            generated = {allowed[0]: content + "\n"}
        else:
            generated = json.loads(body)["files"]
        if set(generated) != set(allowed) or not all(isinstance(content, str) for content in generated.values()):
            raise ValueError("Output files do not match the approved task")
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"Output retained but not applied: {exc}", flush=True)
        raise
    before = {path: (ROOT / path).read_text() if (ROOT / path).exists() else None for path in allowed}
    prefix.with_suffix(".before.json").write_text(json.dumps(before, indent=2) + "\n")
    for relative, content in generated.items():
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    statistics["sha256"] = {path: hashlib.sha256(content.encode()).hexdigest()
                            for path, content in generated.items()}
    prefix.with_suffix(".statistics.json").write_text(json.dumps(statistics, indent=2) + "\n")
    print(f"Applied {len(generated)} model-generated files in {statistics['wall_seconds']}s", flush=True)
    print(json.dumps({key: statistics.get(key) for key in (
        "prompt_eval_count", "eval_count", "done_reason", "eval_duration",
    )}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("metadata", "generate"))
    parser.add_argument("task", nargs="?")
    arguments = parser.parse_args()
    if arguments.command == "metadata":
        metadata()
    else:
        generate(arguments.task)
