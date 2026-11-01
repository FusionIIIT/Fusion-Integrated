import { useState, useEffect } from "react";
import { Container, Table, Button, Text, Title, Alert, Textarea, Group } from "@mantine/core";
import { http, errorMessage } from "../../../lib/http";

interface Proposal {
  id: number;
  title: string;
  objectives: string;
  budget: string;
  department: string;
  status: string;
}

interface Remark {
  [id: number]: string;
}

const ACTIONS: Record<string, { action: string; outcomes: string[] }> = {
  submitted: { action: "recommend", outcomes: ["recommended", "not_recommended"] },
  dept_recommended: { action: "verify", outcomes: ["eligible", "not_eligible"] },
  admin_verified: { action: "decide", outcomes: ["approve", "forward", "not_approve"] },
  forwarded_to_director: { action: "authorize", outcomes: ["approve", "not_approve"] },
};

const ReviewQueue = () => {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [remarks, setRemarks] = useState<Remark>({});
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const response = await http.get("/rspc/proposals/queue/");
      setProposals(response.data);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const getActions = (status: string): { action: string; outcomes: string[] } | undefined => {
    return ACTIONS[status];
  };

  const handleRemarkChange = (id: number, value: string) => {
    setRemarks({ ...remarks, [id]: value });
  };

  const handleAction = async (id: number, action: string, outcome: string, remarkText: string) => {
    try {
      await http.post(`/rspc/proposals/${id}/${action}/`, { outcome, remarks: remarkText });
      await load(); // Move load() here to ensure the proposal leaves the queue
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Container>
      <Title order={2}>Review Queue</Title>
      {error && <Alert color="red">{error}</Alert>}
      {proposals.length === 0 ? (
        <Text>No proposals waiting</Text>
      ) : (
        <Table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Objectives</th>
              <th>Budget</th>
              <th>Department</th>
              <th>Status</th>
              <th>Remarks</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {proposals.map(p => {
              const actions = getActions(p.status);
              return (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.title}</td>
                  <td>{p.objectives}</td>
                  <td>{p.budget}</td>
                  <td>{p.department}</td>
                  <td>{p.status}</td>
                  <td>
                    <Textarea
                      value={remarks[p.id] || ""}
                      onChange={e => handleRemarkChange(p.id, e.target.value)}
                    />
                  </td>
                  <td>
                    {actions && (
                      <Group>
                        {actions.outcomes.map(outcome => (
                          <Button key={outcome} onClick={() => handleAction(p.id, actions.action, outcome, remarks[p.id] || "")}>
                            {outcome}
                          </Button>
                        ))}
                      </Group>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </Container>
  );
};

export default ReviewQueue;
