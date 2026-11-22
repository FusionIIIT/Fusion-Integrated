import { describe, expect, it } from "vitest";

import type { RecordFields, ServiceRecord } from "../api/types";
import { changedRecordFields } from "./AdministrationPage";

const record: ServiceRecord = {
  id: 1, user_id: 10, department: "CSE", designation_snapshot: "Professor",
  appointment_details: { date: "2026-01-01", office: { floor: 2, room: "B" } },
  service_history: [
    { kind: "appointment", role: "Professor" },
    { kind: "appraisal", period_key: "FY2026", submitted_form: { count: 2 } },
  ],
  leave_balances: {},
  retirement_status: "", revision: 4,
  created_at: "2026-11-21T10:00:00Z", updated_at: "2026-11-21T10:00:00Z",
};

const fields: RecordFields = {
  appointment_details: record.appointment_details,
  department: record.department,
  designation_snapshot: record.designation_snapshot,
  service_history: record.service_history,
  retirement_status: record.retirement_status,
};

describe("HR record patch selection", () => {
  it("sends only the modified official field without rewriting appraisal archives", () => {
    expect(changedRecordFields(record, { ...fields, department: "ME" })).toEqual({
      department: "ME",
    });
  });

  it("ignores semantic JSON key reordering and skips unchanged revisions", () => {
    expect(changedRecordFields(record, {
      ...fields,
      appointment_details: {
        office: { room: "B", floor: 2 }, date: "2026-01-01",
      },
      service_history: [
        { role: "Professor", kind: "appointment" },
        { submitted_form: { count: 2 }, period_key: "FY2026", kind: "appraisal" },
      ],
    })).toEqual({});
  });

  it("keeps an actual service-history edit for server-side archive validation", () => {
    expect(changedRecordFields(record, {
      ...fields,
      service_history: [
        { kind: "appointment", role: "Professor" },
      ],
    })).toHaveProperty("service_history");
  });
});
