from pathlib import Path
from docx import Document
from openpyxl import load_workbook

src = Path("ELM-Specs")
out = src / "extracted"
out.mkdir(exist_ok=True)

files = [
    p for p in src.iterdir()
    if p.suffix.lower() in (".docx", ".xlsx")
]

if not files:
    print("ERROR: No specification files found!")

for f in files:
    lines = [f"SOURCE: {f.name}"]

    if f.suffix.lower() == ".docx":
        doc = Document(f)

        for p in doc.paragraphs:
            if p.text.strip():
                lines.append(p.text)

        for i, table in enumerate(doc.tables, 1):
            lines.append(f"\nTABLE {i}")
            for row in table.rows:
                lines.append(" | ".join(
                    cell.text.replace("\n", " / ")
                    for cell in row.cells
                ))

    else:
        wb = load_workbook(f, read_only=True, data_only=True)

        for ws in wb.worksheets:
            lines.append(f"\nWORKSHEET: {ws.title}")

            for row in ws.iter_rows(values_only=True):
                values = [
                    str(v) if v is not None else ""
                    for v in row
                ]
                if any(values):
                    lines.append(" | ".join(values))

        wb.close()

    dest = out / (f.stem + ".txt")
    dest.write_text("\n".join(lines), encoding="utf-8")
    print(f"SUCCESS: {f.name} ({dest.stat().st_size:,} bytes)")

print("\nDONE. Check ELM-Specs\\extracted")