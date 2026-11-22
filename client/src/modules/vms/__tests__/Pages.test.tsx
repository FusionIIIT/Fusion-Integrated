import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PassesPage from "../pages/PassesPage";
import ApprovalsPage from "../pages/ApprovalsPage";
import GatePage from "../pages/GatePage";
import BlacklistPage from "../pages/BlacklistPage";
import EmergencyPage from "../pages/EmergencyPage";
import AnalyticsPage from "../pages/AnalyticsPage";
import type { VisitRequest, BlacklistEntry, GateCheckLog } from "../api/types";

const hooks = vi.hoisted(() => ({
  useVisits: vi.fn(),
  useLiveVisitors: vi.fn(),
  usePreRegisterVisit: vi.fn(),
  useWalkInRegister: vi.fn(),
  useDecideVisit: vi.fn(),
  useContingencyApprove: vi.fn(),
  useExtendVisit: vi.fn(),
  useTerminateVisit: vi.fn(),
  useValidatePass: vi.fn(),
  useGateCheckIn: vi.fn(),
  useGateCheckOut: vi.fn(),
  useGateOverride: vi.fn(),
  useBlacklist: vi.fn(),
  useAddBlacklist: vi.fn(),
  useSafeList: vi.fn(),
  useTriggerMuster: vi.fn(),
  useEmergencyRoster: vi.fn(),
  useRollCall: vi.fn(),
  useAnalytics: vi.fn(),
  useAuditLogs: vi.fn(),
}));

vi.mock("../api/hooks", () => hooks);

const sampleVisitor = {
  id: 1,
  name: "Rajesh Sharma",
  email: "rajesh@example.com",
  phone: "9876543210",
  organization: "TechCorp",
  id_document_type: "AADHAAR",
  id_document_number: "123456789012",
  is_vip: false,
  vip_reason: "",
  created_at: "2026-11-20T10:00:00Z",
};

const sampleVisit: VisitRequest = {
  id: 101,
  visitor: sampleVisitor,
  host_id: 12,
  host_name: "Dr. Vikram",
  purpose: "Research Discussion",
  scheduled_start: "2026-11-20T10:00:00Z",
  scheduled_end: "2026-11-20T14:00:00Z",
  actual_check_in: null,
  actual_check_out: null,
  status: "PENDING_APPROVAL",
  pass_type: "PRE_REGISTERED",
  access_zones: ["Main Gate", "Academic Block"],
  admin_notes: "",
  rejection_reason: "",
  is_urgent_exception: false,
  extension_hours: 0,
  external_event_ref: "",
  digital_pass: {
    id: 201,
    pass_number: "PASS-ABC12345",
    qr_token: "VMS-PASS-ABC12345-tok123",
    pass_type: "PRE_REGISTERED",
    valid_from: "2026-11-20T10:00:00Z",
    valid_to: "2026-11-20T14:00:00Z",
    status: "ACTIVE",
    created_at: "2026-11-20T10:00:00Z",
  },
  created_at: "2026-11-20T10:00:00Z",
};

describe("VMS Pages Unit Tests", () => {
  beforeEach(() => {
    const idleMutation = { mutate: vi.fn(), isPending: false };

    hooks.useVisits.mockReturnValue({ data: [sampleVisit], isPending: false, error: null });
    hooks.useLiveVisitors.mockReturnValue({ data: [sampleVisit], isPending: false, error: null });
    hooks.usePreRegisterVisit.mockReturnValue(idleMutation);
    hooks.useWalkInRegister.mockReturnValue(idleMutation);
    hooks.useDecideVisit.mockReturnValue(idleMutation);
    hooks.useContingencyApprove.mockReturnValue(idleMutation);
    hooks.useExtendVisit.mockReturnValue(idleMutation);
    hooks.useTerminateVisit.mockReturnValue(idleMutation);
    hooks.useValidatePass.mockReturnValue(idleMutation);
    hooks.useGateCheckIn.mockReturnValue(idleMutation);
    hooks.useGateCheckOut.mockReturnValue(idleMutation);
    hooks.useGateOverride.mockReturnValue(idleMutation);

    hooks.useBlacklist.mockReturnValue({
      data: [
        {
          id: 1,
          name: "Blacklisted Person",
          id_document_type: "AADHAAR",
          id_document_number: "999988887777",
          phone: "9999999999",
          reason: "Security violation",
          status: "ACTIVE",
          safe_list_until: null,
          safe_list_reason: "",
          safe_listed_by_id: null,
          created_at: "2026-11-01T00:00:00Z",
        } as BlacklistEntry,
      ],
      isPending: false,
      error: null,
    });
    hooks.useAddBlacklist.mockReturnValue(idleMutation);
    hooks.useSafeList.mockReturnValue(idleMutation);

    hooks.useEmergencyRoster.mockReturnValue({
      data: {
        summary: { total: 1, accounted: 0, unaccounted: 1 },
        roster: [
          {
            id: 1,
            muster_id: "MUSTER-TEST1",
            assembly_point: "Central Ground",
            initiated_by_id: 1,
            initiated_at: "2026-11-20T10:00:00Z",
            visitor: sampleVisitor,
            pass_record: sampleVisit.digital_pass!,
            check_in_time: "2026-11-20T10:00:00Z",
            accountability_status: "UNACCOUNTED",
            accounted_at: null,
            notes: "",
          },
        ],
      },
      isPending: false,
      error: null,
    });
    hooks.useTriggerMuster.mockReturnValue(idleMutation);
    hooks.useRollCall.mockReturnValue(idleMutation);

    hooks.useAnalytics.mockReturnValue({
      data: {
        total_today: 10,
        onsite_now: 3,
        approved: 8,
        pending: 2,
        rejected: 1,
        overstays: 0,
        completed: 5,
      },
      isPending: false,
      error: null,
    });

    hooks.useAuditLogs.mockReturnValue({
      data: [
        {
          id: 1,
          pass_number: "PASS-ABC12345",
          gate_name: "Main Gate",
          checkpoint_type: "ENTRY",
          action: "CHECK_IN",
          operator_id: 5,
          is_override: false,
          override_reason: "",
          is_offline_sync: false,
          timestamp: "2026-11-20T10:05:00Z",
        } as GateCheckLog,
      ],
      isPending: false,
      error: null,
    });
  });

  it("renders PassesPage with register button and pass list", () => {
    render(
      <MantineProvider>
        <PassesPage />
      </MantineProvider>
    );
    expect(screen.getByRole("button", { name: /pre-register visitor/i })).toBeInTheDocument();
    expect(screen.getByText("Rajesh Sharma")).toBeInTheDocument();
  });

  it("renders ApprovalsPage with approve and reject buttons", () => {
    render(
      <MantineProvider>
        <ApprovalsPage />
      </MantineProvider>
    );
    expect(screen.getByRole("button", { name: /^approve$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^reject$/i })).toBeInTheDocument();
  });

  it("renders GatePage with scan controls and walk-in button", () => {
    render(
      <MantineProvider>
        <GatePage />
      </MantineProvider>
    );
    expect(screen.getByRole("button", { name: /validate pass/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /register walk-in guest/i })).toBeInTheDocument();
  });

  it("renders BlacklistPage with blacklist table and add button", () => {
    render(
      <MantineProvider>
        <BlacklistPage />
      </MantineProvider>
    );
    expect(screen.getByRole("button", { name: /add to blacklist/i })).toBeInTheDocument();
    expect(screen.getByText("Blacklisted Person")).toBeInTheDocument();
  });

  it("renders EmergencyPage with evacuation muster button and metrics", () => {
    render(
      <MantineProvider>
        <EmergencyPage />
      </MantineProvider>
    );
    expect(screen.getByRole("button", { name: /trigger evacuation muster/i })).toBeInTheDocument();
    expect(screen.getByText("TOTAL ON-SITE")).toBeInTheDocument();
    expect(screen.getAllByText("UNACCOUNTED").length).toBeGreaterThan(0);
  });

  it("renders AnalyticsPage with metrics summary cards and audit table", () => {
    render(
      <MantineProvider>
        <AnalyticsPage />
      </MantineProvider>
    );
    expect(screen.getByText("TODAY'S VISITS")).toBeInTheDocument();
    expect(screen.getByText("CURRENTLY ON-SITE")).toBeInTheDocument();
    expect(screen.getByText("Main Gate")).toBeInTheDocument();
  });
});
