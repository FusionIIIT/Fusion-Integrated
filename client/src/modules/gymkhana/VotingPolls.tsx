import { useEffect, useState } from "react";
import { fetchPolls, castVote, type PollItem } from "./api";

const VotingPolls = () => {
  const [polls, setPolls] = useState<PollItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [votedPolls, setVotedPolls] = useState<number[]>([]);

  useEffect(() => {
    loadPolls();
  }, []);

  const loadPolls = async () => {
    try {
      setLoading(true);
      const data = await fetchPolls();
      setPolls(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load voting polls.");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (pollId: number, optionId: number) => {
    try {
      await castVote(pollId, optionId);
      setVotedPolls((prev) => [...prev, pollId]);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to cast vote.");
    }
  };

  if (loading) return <p>Loading polls...</p>;

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Active Voting Polls</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
        {polls.map((p) => (
          <div key={p.id} style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "1rem" }}>
            <h3>{p.title}</h3>
            <p>{p.description}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.5rem" }}>
              {p.options.map((opt) => (
                <button
                  key={opt.id}
                  disabled={votedPolls.includes(p.id)}
                  onClick={() => handleVote(p.id, opt.id)}
                  style={{ textAlign: "left", padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "4px", background: votedPolls.includes(p.id) ? "#f1f5f9" : "#fff", cursor: "pointer" }}
                >
                  {opt.option_text}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VotingPolls;
