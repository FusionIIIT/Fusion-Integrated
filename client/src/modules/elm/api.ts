import { http } from "../../lib/http";

export type Application = {
  id: string;
  category: string;
  start_date: string;
  end_date: string;
  num_days: string;
  remarks: string;
  station_leave_details: Record<string, unknown>;
  state: string;
  unit_head_recommendation: string | null;
  allowed_actions: string[];
};

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Colleague = { id: number; name: string };

export async function colleagues(): Promise<Colleague[]> {
  const result: Colleague[] = [];
  let url: string | null = "/elm/colleagues/";
  while (url) {
    const { data }: { data: Page<Colleague> } = await http.get(url);
    result.push(...data.results);
    url = data.next;
  }
  return result;
}
