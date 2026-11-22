"""Freeze check for a Prompt A output (Step 8, item 3). Reads only; never edits the design.

Checks:
  1. the file is a valid JSON array, each item with exactly the seven Prompt A fields;
  2. every source_id starts with an id exactly as the MMS spec writes it, and that id exists
     in this strategy's spec document;
  3. coverage: every obligation id the strategy's rule requires appears in some source_id
     (FR: every CFR/AFR; UC: every use case + each A<n> alternative flow; BR: every active BR;
     WF: every basis/composite workflow).
Exit code 0 = passes both checks; 1 = fails (delete the file, rerun Prompt A in a new session).

Usage: python -I check_design.py fr FR_DESIGN.json
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FIELDS = {"test_id", "source_id", "purpose", "preconditions", "action_or_input",
          "expected_result", "test_type"}
DOC = {"fr": "02_", "uc": "03_", "br": "04_", "wf": "05_"}
ID_RE = {
    "fr": r"(?:CFR|AFR)-MMS-\d{3}",
    "uc": r"MMS-UC-\d{3}",
    "br": r"BR-MMS-\d{3}",
    "wf": r"(?:BW|CW)-MMS-\d{2}",
}


def required(strategy: str, text: str) -> set[str]:
    if strategy == "fr":
        return set(re.findall(r"^\| ((?:CFR|AFR)-MMS-\d{3}) \|", text, re.M)) | \
            set(re.findall(r"^#+ ((?:CFR|AFR)-MMS-\d{3})\b", text, re.M))
    if strategy == "br":
        req = set()
        for block in re.split(r"^## ", text, flags=re.M)[1:]:
            m = re.match(r"(BR-MMS-\d{3})", block)
            if m and "Retired" not in block.split("Status / Notes / TODO", 1)[-1][:80]:
                req.add(m.group(1))
        return req
    if strategy == "wf":
        return set(re.findall(r"^## ((?:BW|CW)-MMS-\d{2})\b", text, re.M))
    req = set()
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        m = re.match(r"(MMS-UC-\d{3})", block)
        if not m:
            continue
        uc = m.group(1)
        req.add(f"{uc} Main")
        alt = re.search(r"^\| Alternative Flows \| (.*) \|$", block, re.M)
        for a in re.findall(r"\b(A\d+)\s*:", alt.group(1) if alt else ""):
            req.add(f"{uc} {a}")
    return req


def main(strategy: str, path: str) -> int:
    spec_dir = BASE if any(BASE.glob(DOC[strategy] + "*.md")) else (BASE / "mms-spec")
    spec = next(spec_dir.glob(DOC[strategy] + "*.md")).read_text(encoding="utf-8")
    raw = Path(path).read_text(encoding="utf-8")
    ok = True
    try:
        cases = json.loads(raw)
        assert isinstance(cases, list) and cases
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: not a non-empty JSON array ({exc})")
        return 1
    for i, c in enumerate(cases):
        if not isinstance(c, dict) or set(c) != FIELDS:
            print(f"FAIL: case {i} fields {sorted(c) if isinstance(c, dict) else type(c)}")
            ok = False
    ids = [c.get("test_id") for c in cases if isinstance(c, dict)]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        print(f"FAIL: duplicate test_id {sorted(dupes)}")
        ok = False

    spec_ids = set(re.findall(ID_RE[strategy], spec))
    covered = set()
    for c in cases:
        sid = str(c.get("source_id", ""))
        m = re.match(ID_RE[strategy], sid)
        if not m:
            print(f"FAIL: {c.get('test_id')}: source_id does not start with a spec id: {sid!r}")
            ok = False
            continue
        if m.group(0) not in spec_ids:
            print(f"FAIL: {c.get('test_id')}: {m.group(0)} is not in the spec document")
            ok = False
        covered.add(m.group(0))
        if strategy == "uc":
            low = sid.lower()
            if "main" in low:
                covered.add(f"{m.group(0)} Main")
            for a in re.findall(r"\b(A\d+)\b", sid):
                covered.add(f"{m.group(0)} {a}")

    req = required(strategy, spec)
    missing = sorted(r for r in req if r not in covered)
    print(f"{len(cases)} cases; {len(req)} required obligations; {len(missing)} not covered")
    for r in missing:
        print(f"  MISSING: {r}")
    if missing:
        ok = False
    print("PASS" if ok else "FAIL -> delete the file and rerun Prompt A in a new session")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in DOC:
        sys.exit("usage: python -I check_design.py fr|uc|br|wf <design.json>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
