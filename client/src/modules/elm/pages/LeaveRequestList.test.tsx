import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MantineProvider } from '@mantine/core';
import LeaveRequestList from './LeaveRequestList';

// Mocks setup
const mocks = vi.hoisted(() => ({
  auth: vi.fn(),
  requests: vi.fn(),
  types: vi.fn(),
  action: vi.fn(),
  mutate: vi.fn(),
}));

vi.mock('../../../auth/AuthProvider', () => ({
  useAuth: mocks.auth,
}));

vi.mock('../api/hooks', () => ({
  useLeaveRequests: mocks.requests,
  useLeaveTypes: mocks.types,
  useLeaveAction: mocks.action,
}));

vi.mock('./LeaveApplicationForm', () => ({
  default: () => <div>Application form</div>,
}));

// Base request fixture
const baseRequest = {
  id: 7,
  employee: 101,
  leave_type: 1,
  start_date: '2026-11-02',
  end_date: '2026-11-02',
  days: 1,
  status: 'PENDING',
  operation: 'LEAVE',
  purpose: 'Family',
  substitute: null as number | null,
  substitute_status: 'NONE',
  route: [201],
  step: 0,
  events: [],
};

// Helper function
const renderAs = (userId: number, permissions: string[], rows = [baseRequest]) => {
  mocks.auth.mockReturnValue({
    session: { user: { id: userId } },
    can: (code: string) => permissions.includes(code),
  });

  mocks.requests.mockReturnValue({
    data: rows,
    isLoading: false,
    error: null,
  });

  mocks.types.mockReturnValue({
    data: [{ id: 1, type: 'CL' }],
  });

  mocks.action.mockReturnValue({
    mutateAsync: mocks.mutate,
    isPending: false,
    error: null,
  });

  return render(
    <MantineProvider>
      <LeaveRequestList />
    </MantineProvider>
  );
};

// Test cases
describe('LeaveRequestList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mutate.mockResolvedValue({});
  });

  // Test 1: Render with apply permission and empty rows
  it('renders with apply permission and empty rows', () => {
    renderAs(101, ['elm.leave_requests.apply'], []);

    expect(screen.getByText(/No leave requests found/i)).toBeInTheDocument();
    expect(screen.getByText('Application form')).toBeInTheDocument();
  });

  // Test 2: Approve permission with base row
  it('approves request with base row', () => {
    renderAs(201, ['elm.leave_requests.approve'], [baseRequest]);

    const approveButton = screen.getByText('APPROVE');
    fireEvent.click(approveButton);

    return waitFor(() => {
      expect(mocks.mutate).toHaveBeenCalledWith({
        request_id: 7,
        action: 'decide',
        payload: { decision: 'APPROVE', notes: '' }
      });
    });
  });

  // Test 3: Approve permission with base row but no button
  it('no approve button for user 301 with base row', () => {
    renderAs(301, ['elm.leave_requests.approve'], [baseRequest]);

    expect(screen.queryByText('APPROVE')).toBeNull();
  });

  // Test 4: Approve permission with substitute PENDING
  it('no approve button when substitute is pending', () => {
    const row = { ...baseRequest, substitute: 301, substitute_status: 'PENDING' };
    renderAs(201, ['elm.leave_requests.approve'], [row]);

    expect(screen.queryByText('APPROVE')).toBeNull();
  });

  // Test 5: Decline substitute request
  it('declines substitute request', () => {
    const row = { ...baseRequest, substitute: 301, substitute_status: 'PENDING' };
    renderAs(301, ['elm.leave_requests.view'], [row]);

    const declineButton = screen.getByText('Decline');
    fireEvent.click(declineButton);

    return waitFor(() => {
      expect(mocks.mutate).toHaveBeenCalledWith({
        request_id: 7,
        action: 'substitute-response',
        payload: { accept: false }
      });
    });
  });

  // Test 6: Withdraw request
  it('withdraws request', () => {
    renderAs(101, ['elm.leave_requests.apply'], [baseRequest]);

    const withdrawButton = screen.getByText('Withdraw');
    fireEvent.click(withdrawButton);

    return waitFor(() => {
      expect(mocks.mutate).toHaveBeenCalledWith({
        request_id: 7,
        action: 'withdraw',
        payload: undefined
      });
    });
  });

  // Test 7: NOT_RECOMMEND action
  it('handles NOT_RECOMMEND action', () => {
    const row = { ...baseRequest, route: [201, 301] };
    renderAs(201, ['elm.leave_requests.approve'], [row]);

    const notRecommendButton = screen.getByText('NOT_RECOMMEND');
    fireEvent.click(notRecommendButton);

    return waitFor(() => {
      expect(mocks.mutate).toHaveBeenCalledWith({
        request_id: 7,
        action: 'decide',
        payload: { decision: 'NOT_RECOMMEND', notes: '' }
      });
      expect(screen.queryByText('APPROVE')).toBeNull();
    });
  });
});
