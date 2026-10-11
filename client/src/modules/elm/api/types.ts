export type LeaveRequest = {
  id: number;
  category: string;
  amount: number;
  status: string;
  applied_at: string;
};

export type Balance = {
  category: string;
  amount: number;
};
