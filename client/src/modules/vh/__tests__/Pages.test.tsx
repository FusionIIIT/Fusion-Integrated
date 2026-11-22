// Frontend component unit tests for VHMS module pages.
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BillingSettlementPage from "../pages/BillingSettlementPage";
import BookingRequisitionsPage from "../pages/BookingRequisitionsPage";
import InventoryPage from "../pages/InventoryPage";
import MyBookingsPage from "../pages/MyBookingsPage";
import NewBookingPage from "../pages/NewBookingPage";
import OperationalRolePage from "../pages/OperationalRolePage";
import StayManagementPage from "../pages/StayManagementPage";
import TariffCardPage from "../pages/TariffCardPage";

const hooks = vi.hoisted(() => ({
  useBookings: vi.fn(),
  useCreateBooking: vi.fn(),
  useCreateOfflineBooking: vi.fn(),
  useCancelBooking: vi.fn(),
  useModifyBooking: vi.fn(),
  useRouteBooking: vi.fn(),
  useAllotRooms: vi.fn(),
  useCheckIn: vi.fn(),
  useCheckOut: vi.fn(),
  useConfirmCancellation: vi.fn(),
  useRoomAvailability: vi.fn(),
  useTariffs: vi.fn(),
  useBookingBill: vi.fn(),
  useSettleBill: vi.fn(),
  useInventory: vi.fn(),
  useSaveInventoryItem: vi.fn(),
  useRequestReplenishment: vi.fn(),
  useReassignRole: vi.fn(),
}));

vi.mock("../api/hooks", () => hooks);

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { user_id: 101, display_name: "Test User" },
    can: () => true,
  }),
}));

const sampleBooking = {
  id: 1,
  booking_reference: "VH-2026-TEST01",
  indenter_id: 101,
  is_offline: false,
  booking_source: "online",
  status: "pending",
  visitor_category: "A",
  visit_purpose: "Academic Lecture",
  arrival_date: "2026-12-01",
  departure_date: "2026-12-05",
  number_of_rooms: 1,
  number_of_occupants: 1,
  billing_responsibility: "visitor",
  cancellation_charge_percentage: "0.00",
  visitors: [{ id: 1, name: "Dr. Test Visitor" }],
  allotments: [],
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T10:00:00Z",
};

describe("VHMS Frontend Pages", () => {
  beforeEach(() => {
    const idleMutation = { mutateAsync: vi.fn(), isPending: false };

    hooks.useBookings.mockReturnValue({
      data: [sampleBooking],
      isPending: false,
      error: null,
    });
    hooks.useCreateBooking.mockReturnValue(idleMutation);
    hooks.useCreateOfflineBooking.mockReturnValue(idleMutation);
    hooks.useCancelBooking.mockReturnValue(idleMutation);
    hooks.useModifyBooking.mockReturnValue(idleMutation);
    hooks.useRouteBooking.mockReturnValue(idleMutation);
    hooks.useAllotRooms.mockReturnValue(idleMutation);
    hooks.useCheckIn.mockReturnValue(idleMutation);
    hooks.useCheckOut.mockReturnValue(idleMutation);
    hooks.useConfirmCancellation.mockReturnValue(idleMutation);
    hooks.useRoomAvailability.mockReturnValue({ data: [], isPending: false });
    hooks.useTariffs.mockReturnValue({
      data: [
        {
          id: 1,
          category: "A",
          room_type: "suite",
          occupancy: "single",
          daily_rate: "800.00",
          effective_from: "2026-01-01",
          is_active: true,
        },
      ],
      isPending: false,
      error: null,
    });
    hooks.useBookingBill.mockReturnValue({
      data: {
        id: 1,
        bill_number: "BILL-2026-001",
        visitor_category: "A",
        total_amount: "1600.00",
        billing_responsibility: "visitor",
        status: "generated",
        items: [],
      },
      isPending: false,
    });
    hooks.useSettleBill.mockReturnValue(idleMutation);
    hooks.useInventory.mockReturnValue({
      data: [
        {
          id: 1,
          item_name: "Bedsheet",
          category: "linen",
          current_quantity: 15,
          minimum_threshold: 10,
          unit: "pieces",
          is_threshold_alert: false,
        },
      ],
      isPending: false,
      error: null,
    });
    hooks.useSaveInventoryItem.mockReturnValue(idleMutation);
    hooks.useRequestReplenishment.mockReturnValue(idleMutation);
    hooks.useReassignRole.mockReturnValue(idleMutation);
  });

  it("renders NewBookingPage with form controls", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <NewBookingPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("New Booking Requisition")).toBeInTheDocument();
    expect(screen.getByLabelText(/Primary Visitor Name/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Submit Requisition/i })).toBeInTheDocument();
  });

  it("renders MyBookingsPage with submitted requisitions", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <MyBookingsPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("My Booking Requisitions")).toBeInTheDocument();
    expect(screen.getByText("VH-2026-TEST01")).toBeInTheDocument();
    expect(screen.getByText("Dr. Test Visitor")).toBeInTheDocument();
  });

  it("renders TariffCardPage with tariff rates", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <TariffCardPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Hostel Tariff Schedule")).toBeInTheDocument();
    expect(screen.getByText("Category A")).toBeInTheDocument();
    expect(screen.getByText("₹800.00")).toBeInTheDocument();
  });

  it("renders BookingRequisitionsPage with triage controls", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <BookingRequisitionsPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Booking Review Desk")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Forward" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("renders StayManagementPage with tabs", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <StayManagementPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Stay & Front Desk Management")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Awaiting Allotment/i })).toBeInTheDocument();
  });

  it("renders InventoryPage with stock and replenishment button", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <InventoryPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Hostel Inventory & Supplies")).toBeInTheDocument();
    expect(screen.getByText("Bedsheet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Replenish/i })).toBeInTheDocument();
  });

  it("renders OperationalRolePage with reassignment form", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <OperationalRolePage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Operational Role Management")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reassign Role/i })).toBeInTheDocument();
  });

  it("renders BillingSettlementPage", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <BillingSettlementPage />
        </MemoryRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Billing & Offline Settlement")).toBeInTheDocument();
  });
});
