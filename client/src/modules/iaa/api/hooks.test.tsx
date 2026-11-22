import { describe, expect, it } from "vitest";
import { keys } from "./hooks";

describe("IAA query keys", () => {
  it("builds consistent query keys", () => {
    expect(keys.requests()).toEqual(["iaa", "requests", undefined]);
    expect(keys.requests("submitted")).toEqual(["iaa", "requests", "submitted"]);
    expect(keys.request(42)).toEqual(["iaa", "request", 42]);
    expect(keys.travelClaims()).toEqual(["iaa", "travel", undefined]);
    expect(keys.travelClaim(10)).toEqual(["iaa", "travel", 10]);
    expect(keys.anomalies("open")).toEqual(["iaa", "anomalies", "open"]);
    expect(keys.auditObservations()).toEqual(["iaa", "audit", undefined]);
    expect(keys.dashboard()).toEqual(["iaa", "dashboard"]);
    expect(keys.configuration()).toEqual(["iaa", "configuration"]);
  });
});
