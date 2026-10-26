from pathlib import Path
import subprocess
import markdown_it

md_text = Path("docs/ELM_PHASE2_REVIEW.md").read_text(encoding="utf-8")
md = markdown_it.MarkdownIt()
html_content = md.render(md_text)

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Phase 2 ELM Review Report</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    margin: 20px 30px;
    color: #1a1a1a;
    line-height: 1.5;
    font-size: 12px;
  }}
  h1 {{ color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 6px; font-size: 18px; }}
  h2 {{ color: #1e40af; border-bottom: 1px solid #93c5fd; padding-bottom: 4px; margin-top: 20px; font-size: 15px; page-break-after: avoid; }}
  h3 {{ color: #1d4ed8; font-size: 13px; margin-top: 14px; page-break-after: avoid; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10.5px; page-break-inside: auto; }}
  tr {{ page-break-inside: avoid; page-break-after: auto; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 5px 7px; text-align: left; vertical-align: top; }}
  th {{ background-color: #f1f5f9; font-weight: 600; color: #334155; }}
  tr:nth-child(even) {{ background-color: #f8fafc; }}
  code {{ font-family: 'Consolas', 'Courier New', monospace; background: #f1f5f9; padding: 2px 4px; border-radius: 3px; font-size: 10.5px; }}
  pre {{ background: #0f172a; color: #f8fafc; padding: 8px 10px; border-radius: 4px; overflow-x: auto; font-size: 10px; page-break-inside: avoid; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  blockquote {{ border-left: 3px solid #3b82f6; margin: 0; padding-left: 10px; color: #475569; }}
  @page {{ margin: 12mm 15mm; size: A4 portrait; }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""

html_path = Path("docs/ELM_PHASE2_REVIEW.html").resolve()
html_path.write_text(full_html, encoding="utf-8")
print(f"Wrote HTML to {html_path}")

pdf_path = Path("docs/ELM_PHASE2_REVIEW.pdf").resolve()
edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cmd = [
    edge_exe,
    "--headless",
    "--disable-gpu",
    f"--print-to-pdf={pdf_path}",
    "--no-pdf-header-footer",
    str(html_path),
]

subprocess.run(cmd, check=True)
if pdf_path.exists():
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"Successfully generated PDF: {pdf_path} ({size_mb:.2f} MB)")
else:
    print("PDF generation failed.")
