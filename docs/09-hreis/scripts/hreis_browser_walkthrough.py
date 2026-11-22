"""Bind synthetic browser actor observations to actual runserver request-log evidence."""

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IST = timezone(timedelta(hours=5, minutes=30))
LOG = re.compile(r'^\[(.*?)\] "(\w+) ([^ ]+) HTTP/1\.1" (\d+) \d+$')


def server_requests(path):
    requests = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LOG.fullmatch(line)
        if not match or not match[3].startswith("/api/v1/hreis/"):
            continue
        at = datetime.strptime(match[1], "%d/%b/%Y %H:%M:%S").replace(tzinfo=IST)
        requests.append((at, match[2], match[3], int(match[4]), line))
    return requests


def render(folder):
    latest = {}
    for line in (folder / "walkthrough.jsonl").read_text().splitlines():
        row = json.loads(line)
        latest[row["test"]] = row
    server = server_requests(folder / "backend.log")
    lines = [
        "# Synthetic HR-EIS browser walkthrough",
        "",
        "Actor accounts come from the synthetic Fusion dump. Each quoted line is copied",
        "from the real runserver log and matched by method, path, status and response time",
        "within three seconds. Repeated reads are deduplicated within each actor/test row.",
        "Role reads also use authenticated API responses and their server Date headers.",
        "",
        "| Use case / scenario | Active role | Dump username | Result | Actual runserver lines |",
        "|---|---|---|---|---|",
    ]
    roles = set()
    use_cases = set()
    for row in latest.values():
        if row["status"] != "passed":
            raise ValueError(f"Walkthrough contains an unsuccessful test: {row['test']}")
        cases = re.search(r"HR-UC-([0-9/]+)", row["test"])
        if cases:
            use_cases.update(cases[1].split("/"))
        groups = {}
        for request in row["requests"]:
            if "at" not in request:
                raise ValueError("Repeat the full suite to supply response timestamps.")
            groups.setdefault((request["role"], request["username"]), {})[
                (request["method"], request["path"], request["status"])
            ] = request
        for (role, username), requests in groups.items():
            roles.add(role)
            matched = []
            for request in requests.values():
                observed = datetime.fromisoformat(request["at"])
                candidates = [
                    entry
                    for entry in server
                    if entry[1:4] == (request["method"], request["path"], request["status"])
                ]
                nearest = min(
                    candidates,
                    key=lambda entry: abs((entry[0] - observed).total_seconds()),
                    default=None,
                )
                if nearest is None or abs((nearest[0] - observed).total_seconds()) > 3:
                    raise ValueError(f"No real request-log match: {request}")
                matched.append(f"`{nearest[4]}`")
            lines.append(f"| {row['test']} | {role} | {username} | PASS | {'<br>'.join(matched)} |")
    expected = {f"{value:03d}" for value in (*range(1, 20), 21, 22)}
    if use_cases != expected or len(roles) != 12:
        raise ValueError(f"Expected 21 live use cases and 12 roles; got {use_cases}, {roles}")
    lines.extend(
        [
            "",
            "All 21 live use cases and all 12 registered designations are represented.",
            "The keyboard-only leave test uses Tab, typing and Enter for its entire submission.",
            "Synthetic results do not close institutional approvals or external integrations.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_folder", type=Path)
    options = parser.parse_args()
    output = ROOT / "docs/09-hreis/browser-walkthrough.md"
    output.write_text(render(options.evidence_folder), encoding="utf-8")
    print(
        "Walkthrough generated only from passed browser tests and matching real request-log lines."
    )
