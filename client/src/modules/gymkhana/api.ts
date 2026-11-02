import { api } from "../../lib/api";

export interface ClubItem {
  id: number;
  name: string;
  category: string;
  description: string;
  status: string;
}

export interface ClubMembershipPayload {
  club_id: number;
}

export interface PollItem {
  id: number;
  club: number;
  title: string;
  description: string;
  options: { id: number; option_text: string }[];
  is_active: boolean;
  expires_at: string;
}

export async function fetchClubs(): Promise<ClubItem[]> {
  const { data } = await api.get<ClubItem[]>("/v1/gymkhana/clubs/");
  return data;
}

export async function applyMembership(clubId: number) {
  const { data } = await api.post(`/v1/gymkhana/clubs/${clubId}/apply/`, {});
  return data;
}

export async function fetchPolls(): Promise<PollItem[]> {
  const { data } = await api.get<PollItem[]>("/v1/gymkhana/polls/");
  return data;
}

export async function castVote(pollId: number, optionId: number) {
  const { data } = await api.post(`/v1/gymkhana/polls/${pollId}/vote/`, {
    option_id: optionId,
  });
  return data;
}
