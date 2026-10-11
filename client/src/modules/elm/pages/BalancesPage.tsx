import { useState, useEffect } from "react";
import {
  Alert, Badge, Card, Container, Group, Loading, Table, TableRow, TableCell,
  TableHead, Text, Tab, Tabs, FaRedo, FaRedoAlt, FaUndo, FaInfoCircle,
} from "@mantine/core";
import { useLeaveBalances, useLeaveHistory } from "../api/hooks";
import { useNavigate } from "react-router-dom";
import type { LeaveBalance, LeaveHistoryEntry } from "../api/types";

/** EL-UC-012: View Leave Balances and History — Inspect own current leave balances
 *  and leave-account/request history including request status and final decisions. */
export default function BalancesPage() {
  const navigate = useNavigate();
  const balancesQuery = useLeaveBalances();
  const historyQuery = useLeaveHistory();

  const balances = balancesQuery.data?.balances ?? [];
  const history = historyQuery.data ?? [];

  if (balancesQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={balancesQuery.error} />
      </Container>
    );
  }

  // Tab view: Balances vs History
  const [tab, setTab] = useState<"balances" | "history">("balances");

  return (
    <Container size="md">
      <PageHeader title="Leave Balances and History" />

      <Tabs
        variant="filled"
        orientation="horizontal"
        value={tab}
        onChange={setTab}
      >
        <Tab value="balances">Leave Balances</Tab>
        <Tab value="history">Leave History</Tab>
      </Tabs>

      {/* Balances Tab */}
      {tab === "balances" && balances.length > 0 && (
        <Card padding="lg" mb="md">
          <Text fw={600} mb="xs">Current Leave Balances</Text>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell category>Category</TableCell>
                <TableCell entitlement>Entitlement/yr</TableCell>
                <TableCell used>Used (yr)</TableCell>
                <TableCell carry>Carried Forward</TableCell>
                <TableCell available>Available</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {balances.map((bal) => (
                <TableRow key={bal.leave_category_code}>
                  <TableCell>{bal.category_label}</TableCell>
                  <TableCell>{bal.entitlement_per_year}</TableCell>
                  <TableCell>{bal.used_per_year}</TableCell>
                  <TableCell>{bal.carried_forward_from_previous}</TableCell>
                  <TableCell>
                    <Badge color={bal.available_days > 0 ? "green" : "red"}>
                      {bal.available_days}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "balances" && balances.length === 0 && (
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No leave balances found for your employee profile.
        </Alert>
      )}

      {/* History Tab */}
      {tab === "history" && history.length > 0 && (
        <Card padding="lg" mb="md">
          <Text fw={600} mb="xs">Leave History</Text>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell type>Type</TableCell>
                <TableCell category>Category</TableCell>
                <TableCell status>Status</TableCell>
                <TableCell period>Period</TableCell>
                <TableCell date>Date</TableCell>
                <TableCell decision>Decision</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {history.map((entry) => (
                <TableRow key={entry.pk}>
                  <TableCell>{entry.type}</TableCell>
                  <TableCell>{entry.leave_category_code}</TableCell>
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
                  <TableCell>{entry.submitted_at ? new Date(entry.submitted_at).toLocaleDateString() : "—"}</TableCell>
                  <TableCell>
                    {entry.decision || "Pending"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "history" && history.length === 0 && (
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No leave history found.
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

/** Placeholder TableBody - using Mantine Table */
const TableBody = ({ children }: { children: any }) => <>{children}</>;