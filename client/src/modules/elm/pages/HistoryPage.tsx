import { useState, useEffect } from "react";
import {
  Alert, Badge, Card, Container, Group, Loading, Table, TableRow, TableCell,
  TableHead, Text, FaRedo, FaRedoAlt, FaUndo, FaInfoCircle,
} from "@mantine/core";
import { useLeaveHistory } from "../api/hooks";
import { useNavigate } from "react-router-dom";
import type { LeaveHistoryEntry } from "../api/types";

/** EL-UC-012: View Leave Balances and History — detailed history view. */
export default function HistoryPage() {
  const navigate = useNavigate();
  const historyQuery = useLeaveHistory();

  const history = historyQuery.data ?? [];

  if (historyQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={historyQuery.error} />
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader title="Leave History" />

      {history.length > 0 && (
        <Card padding="lg" mb="md">
          <Text fw={600} mb="xs">Leave Account / Request History</Text>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell category>Category</TableCell>
                <TableCell type>Type</TableCell>
                <TableCell status>Status</TableCell>
                <TableCell period>Leave Period</TableCell>
                <TableCell date>Date</TableCell>
                <TableCell decision>Final Decision</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {history.map((entry, idx) => (
                <TableRow key={idx}>
                  <TableCell>{idx + 1}</TableCell>
                  <TableCell>{entry.leave_category_code}</TableCell>
                  <TableCell>{entry.type}</TableCell>
                  <TableCell>
                    <Badge
                      color={
                        entry.status === "approved" ? "green"
                        : entry.status === "rejected" ? "red"
                        : entry.status === "withdrawn" ? "orange"
                        : "blue"
                      }
                    >
                      {entry.status || "—"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {entry.requested_start} - {entry.requested_end}
                  </TableCell>
                  <TableCell>
                    {entry.submitted_at ? new Date(entry.submitted_at).toLocaleDateString() : "—"}
                  </TableCell>
                  <TableCell>
                    {entry.decision || "Pending / None"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {history.length === 0 && (
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No leave history found for your employee profile.
        </Alert>
      )}
    </Container>
  );
}

/** Placeholder ErrorState component */
function ErrorState({ error }: { error: any }) {
  return (
    <Card padding="lg" color="red">
      <Text fw={600} mb="xs">Error</Text>
      <Text c="red">{error?.message || error || "Unknown error"}</Text>
    </Card>
  );
}

/** Placeholder TableBody */
const TableBody = ({ children }: { children: any }) => <>{children</>}</>;