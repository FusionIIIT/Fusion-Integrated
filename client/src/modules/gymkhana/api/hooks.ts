import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";

export type Club = {
  id: number;
  name: string;
  category: string;
  description: string;
  status: "open" | "confirmed";
};

export type Poll = {
  id: number;
  title: string;
  description: string;
  expires_at: string;
  choices: Array<{ id: number; text: string; votes_count: number }>;
};

const key = ["gymkhana"] as const;

export function useClubs() {
  return useQuery({
    queryKey: [...key, "clubs"],
    queryFn: async () => (await http.get<Club[]>("/gymkhana/clubs/")).data,
  });
}

export function useCreateClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Club>("/gymkhana/clubs/", body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...key, "clubs"] }),
  });
}

export function useConfirmClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Club>(`/gymkhana/clubs/${id}/confirm/`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...key, "clubs"] }),
  });
}

export function useActivePolls() {
  return useQuery({
    queryKey: [...key, "polls"],
    queryFn: async () => (await http.get<Poll[]>("/gymkhana/polls/")).data,
  });
}

export function useVotePoll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ pollId, choiceId }: { pollId: number; choiceId: number }) =>
      (await http.post(`/gymkhana/polls/${pollId}/vote/`, { choice_id: choiceId })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [...key, "polls"] }),
  });
}
