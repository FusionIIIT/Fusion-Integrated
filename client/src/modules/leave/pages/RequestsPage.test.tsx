import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import RequestsPage from './RequestsPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MantineProvider } from '@mantine/core';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { http } from '../../../lib/http';

// Mock http module
vi.mock('../../../lib/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
  errorMessage: vi.fn(),
}));

// Mock useAuth via hoisted
const useAuth = vi.hoisted(() => vi.fn());
vi.mock('../../../auth/AuthProvider', () => ({ useAuth }));

// Correct mock path for NewLeaveRequest component
vi.mock('../components/NewLeaveRequest', () => ({ NewLeaveRequest: () => null }));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MantineProvider>
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  </MantineProvider>
);

describe('RequestsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(http.get).mockResolvedValueOnce({
      data: {
        results: [
          { id: 1, employee_id: 'alice', status: 'pending' },
          { id: 2, employee_id: 'bob', status: 'pending' },
          { id: 3, employee_id: 'alice', status: 'approved' },
        ],
        next: null,
        previous: null,
      },
    });
    useAuth.mockReturnValue({
      session: { user: { username: 'alice' } },
      can: () => true,
    });
  });

  it('shows one Withdraw button for own pending request', async () => {
    render(<RequestsPage />, { wrapper });
    await waitFor(() => {
      expect(http.get).toHaveBeenCalled();
    });
    const buttons = await screen.findAllByRole('button', { name: /withdraw/i });
    expect(buttons).toHaveLength(1);
  });
});