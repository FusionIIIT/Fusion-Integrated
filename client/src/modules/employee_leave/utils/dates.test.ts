import { describe, expect, it } from "vitest";

import { formatLocalDate } from "./dates";

describe("formatLocalDate", () => {
  it("preserves the calendar date selected in the user's local timezone", () => {
    const selected = new Date(2026, 9, 12, 0, 0, 0);
    expect(formatLocalDate(selected)).toBe("2026-10-12");
  });
});