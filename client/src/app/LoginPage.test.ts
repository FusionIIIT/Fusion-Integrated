import { describe, expect, it } from "vitest";

import { safeInternalPath } from "./LoginPage";

describe("safeInternalPath", () => {
  it.each([
    ["/placement/reports", "/placement/reports"],
    ["/", "/"],
    ["/placement/postings?status=submitted", "/placement/postings?status=submitted"],
  ])("keeps the internal path %s", (input, expected) => {
    expect(safeInternalPath(input)).toBe(expected);
  });

  // Exactly the shapes the react-router open-redirect advisory describes: both
  // leave the site while looking like a path.
  it.each([
    "//evil.test",
    "//evil.test/placement",
    "/\\evil.test",
    "\\\\evil.test",
    "https://evil.test",
    "http://evil.test",
    "javascript:alert(1)",
    "placement/reports",
    "",
  ])("refuses %j", (input) => {
    expect(safeInternalPath(input)).toBeNull();
  });

  it.each([null, undefined, 42, {}, ["/ok"]])("refuses the non-string %j", (input) => {
    expect(safeInternalPath(input)).toBeNull();
  });
});
