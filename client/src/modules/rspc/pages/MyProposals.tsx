import { useState, useEffect } from "react";
import { http, errorMessage } from "../../../lib/http";
import { Container, Card, Stack, Table, Text, Title, Alert } from "@mantine/core";

interface Proposal {
  id: number;
  title: string;
  status: string;
  decisions: { id: number; stage: string; actor_id: number | null; outcome: string; remarks: string; decided_at: string }[];
}

const MyProposals = () => {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProposals = async () => {
      try {
        const response = await http.get("/rspc/proposals/mine/");
        setProposals(response.data);
      } catch (e) {
        setError(errorMessage(e));
      }
    };

    fetchProposals();
  }, []);

  return (
    <Container>
      <Title order={2}>My Proposals</Title>
      {error && <Alert color="red">{error}</Alert>}
      <Card>
        <Stack>
          <Table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Decision History</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((proposal) => (
                <tr key={proposal.id}>
                  <td>{proposal.title}</td>
                  <td>{proposal.status}</td>
                  <td>
                    {proposal.decisions.length > 0 ? (
                      proposal.decisions.map((decision) => (
                        <div key={decision.id}>
                          <Text>{decision.stage}</Text>
                          <Text>{decision.outcome}</Text>
                          <Text>{decision.remarks}</Text>
                          <Text>{new Date(decision.decided_at).toLocaleString()}</Text>
                        </div>
                      ))
                    ) : (
                      <Text>No decisions yet</Text>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Stack>
      </Card>
    </Container>
  );
};

export default MyProposals;
