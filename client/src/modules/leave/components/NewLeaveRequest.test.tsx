import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { NewLeaveRequest } from './NewLeaveRequest';

// Mock AuthProvider
const useAuth = vi.hoisted(() => vi.fn());
vi.mock('../../../auth/AuthProvider', () => ({ useAuth }));

// Mock http and notifications
vi.mock('../../../lib/http', () => ({ http: { post: vi.fn() } }));
vi.mock('@mantine/notifications', () => ({ notifications: { show: vi.fn() } }));

const createQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MantineProvider>
    <QueryClientProvider client={createQueryClient()}>{children}</QueryClientProvider>
  </MantineProvider>
);

describe('NewLeaveRequest', () => {
  beforeEach(() => {
    // Stub scrollIntoView to avoid jsdom errors when opening Mantine Select dropdowns
    Element.prototype.scrollIntoView = vi.fn();
    vi.clearAllMocks();
    useAuth.mockReturnValue({ can: () => true });
  });

  it('submits a leave request with correct payload', async () => {
    const { http } = await import('../../../lib/http');
    vi.mocked(http.post).mockResolvedValueOnce({} as never);

    render(<NewLeaveRequest />, { wrapper });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /new leave request/i }));

    // Wait for modal fields to appear
    const startInput = await screen.findByLabelText(/start date/i) as HTMLInputElement;
    const endInput = await screen.findByLabelText(/end date/i) as HTMLInputElement;
    fireEvent.change(startInput, { target: { value: '2024-10-01' } });
    fireEvent.change(endInput, { target: { value: '2024-10-05' } });

    // Submit
    const submitBtn = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(http.post).toHaveBeenCalledTimes(1);
    });

    const expectedPayload = {
      leave_type: 'CL',
      start_date: '2024-10-01',
      end_date: '2024-10-05',
      reason: '',
      day_period: 'full_day',
    };
    expect(http.post).toHaveBeenCalledWith('/leave/requests/', expectedPayload);
  });

  it('hides the button when user cannot manage leave requests', () => {
    useAuth.mockReturnValue({ can: () => false });
    render(<NewLeaveRequest />, { wrapper });
    const button = screen.queryByRole('button', { name: /new leave request/i });
    expect(button).toBeNull();
  });

  it('shows Day Period textbox with default value Full Day for CL type', async () => {
    render(<NewLeaveRequest />, { wrapper });

    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /new leave request/i }));

    // Wait for modal to appear
    await screen.findByRole('dialog');

    // Find the Day Period textbox
    const dayPeriodTextbox = screen.getByRole('textbox', { name: /day period/i });
    expect(dayPeriodTextbox).toBeInTheDocument();
    expect(dayPeriodTextbox).toHaveValue('Full Day');
  });
});