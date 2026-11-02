import { useEffect, useState } from "react";
import { fetchClubs, applyMembership, type ClubItem } from "./api";

const ClubsDashboard = () => {
  const [clubs, setClubs] = useState<ClubItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    loadClubs();
  }, []);

  const loadClubs = async () => {
    try {
      setLoading(true);
      const data = await fetchClubs();
      setClubs(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load clubs.");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (clubId: number) => {
    try {
      await applyMembership(clubId);
      setMsg("Membership application submitted successfully!");
    } catch (err: any) {
      setError(err.response?.data?.error || "Application failed.");
    }
  };

  if (loading) return <p>Loading clubs...</p>;

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Gymkhana Clubs</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {msg && <p style={{ color: "green" }}>{msg}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
        {clubs.map((c) => (
          <div key={c.id} style={{ border: "1px solid #e2e8f0", borderRadius: "8px", padding: "1rem" }}>
            <h3>{c.name}</h3>
            <p><strong>Category:</strong> {c.category}</p>
            <p><strong>Status:</strong> {c.status}</p>
            <p>{c.description}</p>
            {c.status === "confirmed" && (
              <button
                onClick={() => handleApply(c.id)}
                style={{ padding: "6px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}
              >
                Apply for Membership
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ClubsDashboard;
