import { describe, expect, it } from "vitest";

import { submissionStatus } from "./submissionStatus";

describe("submissionStatus", () => {
  it("uses the status of the student's recorded submission", () => {
    expect(submissionStatus("2030-01-01T00:00:00Z", { status: "submitted" }, 0))
      .toBe("submitted");
    expect(submissionStatus("2020-01-01T00:00:00Z", { status: "late" }, 0))
      .toBe("late");
  });

  it("marks an unreplied assignment missing only after its due date", () => {
    expect(submissionStatus("2030-01-01T00:00:00Z", undefined, 0)).toBeUndefined();
    expect(submissionStatus("2020-01-01T00:00:00Z", undefined, 0)).toBe("missing");
  });
});
