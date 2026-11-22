"""The dependency-free PDF table writer (AFR-152)."""
import re

from modules.vms.services.common import pdf


def _parse(data: bytes):
    """Check the cross-reference table is exact and return the page count."""
    assert data.startswith(b"%PDF-1.4\n") and data.rstrip().endswith(b"%%EOF")
    startxref = int(re.search(rb"startxref\n(\d+)\n%%EOF", data).group(1))
    assert data[startxref:startxref + 4] == b"xref"
    size = int(re.search(rb"/Size (\d+)", data).group(1))
    table = re.findall(rb"(\d{10}) 00000 n \n", data[startxref:])
    assert len(table) == size - 1
    for num, off in enumerate(table, start=1):
        assert data[int(off):].startswith(b"%d 0 obj\n" % num), f"object {num} offset wrong"
    return int(re.search(rb"/Count (\d+)", data).group(1))


def test_a_small_table_is_one_valid_page():
    data = pdf.render_table(title="Daily summary", header=["Date", "Check-ins"],
                            rows=[["2026-11-23", 4], ["2026-11-24", 7]], subtitle="range")
    assert _parse(data) == 1
    assert b"(Daily summary)" in data and b"(2026-11-23)" in data
    assert b"Page 1 of 1" in data


def test_an_empty_report_is_still_a_valid_one_page_document():
    data = pdf.render_table(title="Empty", header=["A", "B"], rows=[])
    assert _parse(data) == 1 and b"(A)" in data


def test_long_reports_paginate_and_repeat_the_header():
    rows = [[f"row{i}", i] for i in range(200)]
    data = pdf.render_table(title="Big", header=["Name", "N"], rows=rows)
    pages = _parse(data)
    assert pages > 1
    assert data.count(b"(Name)") == pages
    assert f"Page {pages} of {pages}".encode() in data and b"(row199)" in data


def test_pdf_string_delimiters_are_escaped():
    data = pdf.render_table(title="T", header=["H"],
                            rows=[["a (b) \\ c"], ["line1\nline2\ttab"]])
    assert b"(a \\(b\\) \\\\ c)" in data
    assert b"(line1 line2 tab)" in data


def test_text_outside_latin1_is_replaced_not_crashing():
    data = pdf.render_table(title="T", header=["H"], rows=[["Ravi कुमार"]])
    _parse(data)
    assert b"Ravi ???" in data


def test_overlong_cells_are_cut_to_their_column():
    data = pdf.render_table(title="T", header=["A", "B", "C", "D", "E", "F", "G", "H"],
                            rows=[["x" * 500] + ["y"] * 7])
    _parse(data)
    assert b"x" * 500 not in data and b".." in data


def test_none_cells_render_empty_and_output_is_deterministic():
    one = pdf.render_table(title="T", header=["H", "I"], rows=[[None, 1]])
    assert one == pdf.render_table(title="T", header=["H", "I"], rows=[[None, 1]])
    assert b"() Tj" in one
