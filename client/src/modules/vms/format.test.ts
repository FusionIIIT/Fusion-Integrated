import { describe, expect, it } from "vitest";

import { formatDateTime, formatWindow, humanise } from "./format";

describe("format", () => {
  it("formats a date and time, and shows a dash for nothing or nonsense", () => {
    expect(formatDateTime("2026-01-05T09:30:00")).toBe("5 Jan, 09:30");
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("not a date")).toBe("—");
  });

  it("shows a same-day window with one date and a midnight-spanning one with two", () => {
    expect(formatWindow("2026-01-05T09:30:00", "2026-01-05T11:00:00")).toBe("5 Jan, 09:30 – 11:00");
    expect(formatWindow("2026-01-05T22:00:00", "2026-01-06T01:00:00"))
      .toBe("5 Jan, 22:00 – 6 Jan, 01:00");
    expect(formatWindow("bad", "2026-01-06T01:00:00")).toBe("—");
  });

  it("turns codes into readable words", () => {
    expect(humanise("gate_failure")).toBe("Gate failure");
    expect(humanise("vms.pass.terminate")).toBe("Vms pass terminate");
    expect(humanise("")).toBe("");
  });
});
