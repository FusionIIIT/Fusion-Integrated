export interface Registration {
  readonly id: number;
  readonly cycle: string;
  readonly request_type: "register" | "deregister";
  readonly status: "pending" | "registered" | "deregistered" | "rejected";
  readonly submitted_at: string;
  readonly effective_date: string | null;
}

export interface MenuItem {
  readonly id: number;
  readonly week_start: string;
  readonly day: number;
  readonly meal: "breakfast" | "lunch" | "dinner";
  readonly item: string;
}

export interface Rebate {
  readonly id: number;
  readonly reason: string;
  readonly explanation: string;
  readonly start_date: string;
  readonly end_date: string;
  readonly status: "pending" | "approved" | "rejected";
}

export interface ApiError {
  readonly response?: { readonly data?: { readonly error?: { readonly message?: string } } };
}
