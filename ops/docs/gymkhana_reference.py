from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "18-gymkhana" / "gymkhana-reference.md"

IDS = (
    [f"CFR-GYM-{i:03d}" for i in range(1, 8)]
    + [f"AFR-GYM-{i:03d}" for i in range(1, 35)]
    + [f"UC-GYM-{i:03d}" for i in range(1, 13)]
    + [f"BR-GYM-{i:03d}" for i in range(1, 22)]
)


def main() -> None:
    lines = ["# Gymkhana Specification Reference", "", "| ID | Enforcement evidence |", "|---|---|"]
    enforcement = [
        ("CFR-GYM-", "modules/gymkhana/services/, models/, api/, and tests/"),
        ("AFR-GYM-", "modules/gymkhana/services/, models/, api/, and tests/"),
        ("UC-GYM-", "modules/gymkhana/api/views.py and modules/gymkhana/tests/test_journeys.py"),
        ("BR-GYM-", "modules/gymkhana/domain/, models/, and tests/"),
    ]
    for spec_id in IDS:
        evidence = next(text for prefix, text in enforcement if spec_id.startswith(prefix))
        lines.append(f"| {spec_id} | `{evidence}` |")
    lines.extend(
        f"| {workflow} | `modules/gymkhana/tests/test_journeys.py` |"
        for workflow in ("BW-GYM-01", "BW-GYM-02", "BW-GYM-03")
    )

    required = [
        ROOT / "modules/gymkhana/api/views.py",
        ROOT / "modules/gymkhana/services",
        ROOT / "modules/gymkhana/models",
        ROOT / "modules/gymkhana/tests",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing Gymkhana enforcement paths: " + ", ".join(missing))
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
