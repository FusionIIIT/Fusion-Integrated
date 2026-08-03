import { describe, expect, it, vi } from "vitest";

import { filenameFromDisposition, saveBlob } from "./download";

describe("filenameFromDisposition", () => {
  it("prefers the server's name, which carries the export timestamp", () => {
    expect(filenameFromDisposition(
      'attachment; filename="applications-20260803-1015.csv"', "fallback.csv",
    )).toBe("applications-20260803-1015.csv");
  });

  it("reads an unquoted name", () => {
    expect(filenameFromDisposition("attachment; filename=placements.csv", "f.csv"))
      .toBe("placements.csv");
  });

  it("decodes the RFC 5987 form", () => {
    expect(filenameFromDisposition(
      "attachment; filename*=UTF-8''placements%202026.csv", "f.csv",
    )).toBe("placements 2026.csv");
  });

  it.each([undefined, null, "", "attachment", "inline; charset=utf-8"])(
    "falls back when the header says no name (%j)", (header) => {
      expect(filenameFromDisposition(header, "fallback.csv")).toBe("fallback.csv");
    });

  it("strips path separators, so a header cannot choose the directory", () => {
    expect(filenameFromDisposition(
      'attachment; filename="../../etc/passwd"', "f.csv",
    )).toBe(".._.._etc_passwd");
  });
});

describe("saveBlob", () => {
  it("clicks a download link and releases the object URL", () => {
    const createObjectURL = vi.spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:x");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    vi.useFakeTimers();

    saveBlob(new Blob(["a,b\n1,2\n"], { type: "text/csv" }), "report.csv");

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    // Removed synchronously: a stray anchor in the document is a leak.
    expect(document.querySelector("a[download]")).toBeNull();

    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:x");
    vi.useRealTimers();
  });
});
