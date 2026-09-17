#!/usr/bin/env python
"""Regenerate docs/09-leave/ELM_REFERENCE.md."""
from __future__ import annotations

import json
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ELM = ROOT.parent / "ELM"
OUT = ROOT / "docs" / "09-leave" / "ELM_REFERENCE.md"
NOTES = pathlib.Path(__file__).with_name("elm_reference_notes.json")

#: Where a reader should land first.
RULE_ORDER = ("/domain/", "/services/", "/models/", "/selectors/", "/api/",
              "/management/", "client/", "/tests/")
USECASE_ORDER = ("/services/", "/api/", "/domain/", "/models/", "/selectors/",
                 "/management/", "client/", "/tests/")


def _doc(pattern: str) -> str:
    match = next(ELM.glob(pattern), None)
    if match is None:
        sys.exit(f"specification not found: {ELM}/{pattern}")
    with zipfile.ZipFile(match) as archive:
        raw = archive.read("word/document.xml").decode("utf8")
    return re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", raw))


def _field(body: str, name: str) -> str:
    found = re.search(rf"{name}\n(.+?)\n", body)
    return found.group(1).strip() if found else ""


def read_spec() -> dict:
    rules, cases, workflows = _doc("04_*.docx"), _doc("03_*.docx"), _doc("05_*.docx")
    spec: dict = {"br": [], "uc": [], "sf": [], "wf": []}

    for m in re.finditer(
            r"BR-EL-(\d{3}) — ([^\n]+)\n(.*?)(?=BR-EL-\d{3} — |\Z)",
            rules, re.S):
        spec["br"].append({
            "id": f"BR-EL-{m.group(1)}", "name": m.group(2).strip(),
            "statement": _field(m.group(3), "Rule Statement")})

    for m in re.finditer(
            r"EL-UC-(\d{3}) — ([^\n]+)\n"
            r"(.*?)(?=EL-UC-\d{3} — |3\. Scheduled Functions|\Z)",
            cases, re.S):
        spec["uc"].append({
            "id": f"EL-UC-{m.group(1)}", "name": m.group(2).strip(),
            "actor": _field(m.group(3), "Primary Actor")})

    for m in re.finditer(
            r"SF-EL-(\d{3}) — ([^\n]+)\n(.*?)(?=SF-EL-\d{3} — |\Z)",
            cases, re.S):
        spec["sf"].append({
            "id": f"SF-EL-{m.group(1)}", "name": m.group(2).strip(),
            "rules": sorted(set(re.findall(r"BR-EL-\d{3}", m.group(3))))})

    for m in re.finditer(r"(BW-EL-\d\d|CW-EL-\d\d) — ([^\n]+)", workflows):
        spec["wf"].append({"id": m.group(1), "name": m.group(2).strip()})
    return spec


def read_code(ids: list[str]) -> dict:
    """Every place each id is cited, read out of the tree."""
    hits: dict[str, list] = {i: [] for i in ids}
    for base in ("modules/leave", "client/src/modules/leave"):
        for path in (ROOT / base).rglob("*"):
            if (not path.is_file() or path.suffix not in {".py", ".tsx", ".ts"}
                    or "__pycache__" in str(path)):
                continue
            rel = path.relative_to(ROOT).as_posix()
            for number, line in enumerate(path.read_text().splitlines(), 1):
                for identifier in ids:
                    if identifier in line:
                        hits[identifier].append({"file": rel, "line": number})
    return hits


def short(path: str) -> str:
    return (path.replace("modules/leave/", "")
                .replace("client/src/modules/leave/", "client/"))


def link(hits: dict, identifier: str, kind: str = "rule") -> str:
    """The place to look first, then the next two."""
    found = hits.get(identifier) or []
    if not found:
        return "*not in code* —"
    order = RULE_ORDER if kind == "rule" else USECASE_ORDER

    def rank(hit):
        for index, part in enumerate(order):
            if part in hit["file"]:
                return (index, hit["file"], hit["line"])
        return (99, hit["file"], hit["line"])

    places, out, seen = sorted(found, key=rank), [], set()
    for hit in places:
        key = (hit["file"], hit["line"])
        if key in seen:
            continue
        seen.add(key)
        target = f"../../{hit['file']}#L{hit['line']}"
        label = f"`{short(hit['file'])}:{hit['line']}`"
        out.append(f"[{label}]({target})" + (f" [↗]({target})"
                                             if not out else ""))
        if len(out) == 3:
            break
    tail = (f"<br><sub>{len(found)} citations in all</sub>"
            if len(found) >= 4 else "")
    return "<br>".join(out) + tail


def build() -> str:
    spec, notes = read_spec(), json.loads(NOTES.read_text())
    rules = {b["id"]: b for b in spec["br"]}
    cases = {u["id"]: u for u in spec["uc"]}
    identifiers = ([*rules], [*cases], [s["id"] for s in spec["sf"]],
                   sorted({w["id"] for w in spec["wf"]}))
    hits = read_code([i for group in identifiers for i in group])

    implemented_rules = sum(1 for r in rules if hits.get(r))
    implemented_cases = sum(1 for c in cases if hits.get(c))

    out: list[str] = []
    add = out.append
    add(HEAD.format(
        rules=len(rules), rules_done=implemented_rules,
        cases=len(cases), cases_done=implemented_cases,
        sfs=len(spec["sf"]),
        basis=len({w["id"] for w in spec["wf"] if w["id"].startswith("BW")}),
        composite=len({w["id"] for w in spec["wf"] if w["id"].startswith("CW")})))
    add(notes["journey"])
    add(JOURNEY_NOTE)

    add("| Use case | Actor | What it is | Code |")
    add("|---|---|---|---|")
    for identifier in sorted(cases):
        case = cases[identifier]
        actor = case["actor"].replace(" / Responsibility Holder", "")
        add(f"| **{identifier}**<br>{case['name']} | {actor} | "
            f"{notes['use_cases'][identifier]} | "
            f"{link(hits, identifier, 'usecase')} |")

    add(SF_HEAD)
    add("| Function | What it does | Rules | Code |")
    add("|---|---|---|---|")
    for function in spec["sf"]:
        cited = ", ".join(function["rules"][:4])
        cited += " …" if len(function["rules"]) > 4 else ""
        add(f"| **{function['id']}**<br>{function['name']} | "
            f"{notes['scheduled_functions'][function['id']]} | {cited} | "
            f"{link(hits, function['id'], 'usecase')} |")

    add("\n---\n\n## Business rules\n")
    for group in notes["groups"]:
        add(f"### {group['title']}\n")
        add(f"{group['blurb']}\n")
        add("| Rule | Statement | What it means | Code |")
        add("|---|---|---|---|")
        for identifier in group["ids"]:
            rule = rules[identifier]
            statement = rule["statement"].replace("|", "\\|")
            add(f"| **{identifier}**<br>{rule['name']} | {statement} | "
                f"{notes['business_rules'][identifier]} | "
                f"{link(hits, identifier)} |")
        add("")

    add(WORKFLOW_HEAD)
    add("| Workflow | Name | Code |")
    add("|---|---|---|")
    seen: set[str] = set()
    for workflow in spec["wf"]:
        if workflow["id"] in seen:
            continue
        seen.add(workflow["id"])
        add(f"| `{workflow['id']}` | {workflow['name']} | "
            f"{link(hits, workflow['id'])} |")

    add(GAPS_HEAD)
    for gap in notes["gaps"]:
        add(f"**{gap['id']}** — {gap['name']}\n")
        add(f"{gap['note']}\n")

    add(MAP_HEAD)
    for layer in notes["file_map"]:
        add(f"### {layer['layer']}\n")
        add(f"{layer['blurb']}\n")
        for entry in layer["files"]:
            add(f"- `{entry['name']}` — {entry['desc']}")
        add("")

    add(TAIL)
    return "\n".join(out) + "\n"


HEAD = """---
owner: leave-lead
status: generated
last-reviewed: 2026-09-02
---

# Employee Leave Management — the rules, and where each one lives

Every business rule and use case from the ELM specification, what it means in a
sentence, and a link straight to the line of code that decides it.

Built for teaching. Read a rule, click the arrow, land on the function that
enforces it.

> **This page is generated.** Run `python ops/docs/build_elm_reference.py` after
> moving code. The rule statements are read from the `.docx` specifications and
> the line numbers from the source tree, so neither can drift by hand — and
> a line number edited by hand is how a reference stops being trustworthy.

**Source documents** — the six files this is drawn from live in
[`ELM/`](../../../ELM/README.md). This page is the reading order; those are the
contract.

| | |
|---|---|
| Business rules | **{rules}** defined, **{rules_done}** implemented |
| Use cases | **{cases}** defined, **{cases_done}** implemented |
| Scheduled functions | **{sfs}** |
| Workflows | {basis} basis + {composite} composite |
| States / transitions | 23 states, 46 transitions, 4 terminal |
| Tables | 12, with 12 database check constraints |

---

## The journey of one request
"""

JOURNEY_NOTE = """
Two things on that diagram are worth pausing on when teaching:

- **The balance moves once**, at final sanction. Nothing is held while a request
  is pending, which is why a withdrawal needs no reversal — and why two
  separately affordable requests have to be re-checked against each other at
  approval.
- **`[clock]` is not a person.** Leave starting, and reaching its end, are the
  passage of time. If nothing runs that clock, approved leave never becomes
  ongoing, stays cancellable after the employee has gone, and can never be
  extended or closed.

---

## Use cases

Who does what, and why it exists.
"""

SF_HEAD = """
### Scheduled functions

Not use cases: nobody triggers these. They are what the system does because
time passed.
"""

WORKFLOW_HEAD = """
---

## Workflows

The specification derives small **basis** workflows for finite paths, then
composes them. The transition table cites the basis rows, because those are what
a single state change belongs to.
"""

GAPS_HEAD = """
---

## What is deliberately absent, and what is simply missing

The distinction matters when teaching: most of these are decisions, one is a gap.
"""

MAP_HEAD = """---

## Where to look for what

One shape, five layers, and the layer tells you what a file is allowed to do.
"""

TAIL = """---

## The five ideas behind all of it

If somebody remembers only five things from a session on this module:

1. **The balance is a ledger, not a column.** There is no stored total anywhere.
   A balance is the sum of append-only entries, so it can always be re-derived
   and always explained row by row. A wrong entry is corrected by a reversing
   entry, so the mistake survives the correction.
2. **Policy is effective-dated and never edited.** A revised ordinance is a new
   version. Last year's approvals still explain themselves, because they cite
   the version they were decided under.
3. **Transitions are a table.** An illegal state change is *inexpressible*
   rather than rejected by a check somebody can forget to write.
4. **Authority is configuration.** Naming offices in code turns a reorganisation
   into a deployment.
5. **Scope is a queryset.** Somebody else's request is not found, rather than
   refused — because a refusal confirms it exists.

---

## Further reading

- [Domain model](leave-domain-model.md) — tables, categories, bring-up order
- [Counting and entitlement](leave-counting-and-entitlement.md) — the arithmetic
- [State machine](leave-state-machine.md) — all 46 transitions
- [Authority, routing and scope](leave-authority-and-routing.md) — who decides, who sees
"""


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT.relative_to(ROOT)}")
