"""Record explicit build and integration commands for the ELM local-model trial."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs/08-delivery/elm-qwen-trial"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    environment = os.environ.copy()
    configuration = json.loads((LOG / "check-environment.json").read_text())
    temporary = configuration["temporary_settings_directory"]
    if not Path(temporary).is_dir():
        temporary = tempfile.mkdtemp(prefix="elm-qwen-checks-")
        for template in (LOG / "check-settings").glob("*.py"):
            shutil.copyfile(template, Path(temporary) / template.name)
        configuration["temporary_settings_directory"] = temporary
        (LOG / "check-environment.json").write_text(json.dumps(configuration, indent=2) + "\n")
    environment["PYTHONPATH"] = temporary + os.pathsep + str(ROOT)
    environment["DJANGO_SETTINGS_MODULE"] = (
        "qwen_isolated_settings" if arguments.isolated else "qwen_build_settings"
    )
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT / "client" if arguments.client else ROOT,
                            env=environment, capture_output=True, text=True)
    record = {"label": arguments.label, "finished_at": datetime.now(timezone.utc).isoformat(),
              "command": command, "returncode": result.returncode,
              "wall_seconds": round(time.monotonic() - started, 2),
              "stdout": result.stdout, "stderr": result.stderr}
    with (LOG / "checks.jsonl").open("a") as output:
        output.write(json.dumps(record) + "\n")
    with (LOG / "checks.log").open("a") as output:
        output.write(f"\n## {arguments.label}\n{record['finished_at']}\n")
        output.write("Command: " + " ".join(command) + "\n")
        output.write(result.stdout + result.stderr)
        output.write(f"\nExit code: {result.returncode}; {record['wall_seconds']} seconds\n")
    print(result.stdout + result.stderr, end="")
    print(f"Recorded {arguments.label}: exit {result.returncode}", flush=True)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
