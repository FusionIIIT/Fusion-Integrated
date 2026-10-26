/** My leave: balances, my requests with withdraw, and an apply form. */
import { useState } from "react";
import type { FormEvent } from "react";
import {
  Alert, Button, Checkbox, Loader, Select, Stack, Table, Text, TextInput, Title,
} from "@mantine/core";

import {
  useApplyLeaveRequest, useBalance, useLeaveRequests, useWithdrawLeaveRequest,
} from "../api/hooks";
import { LEAVE_CATEGORIES } from "../api/types";
import type { LeaveCategory } from "../api/types";

const WITHDRAWABLE = ["Awaiting Substitute Response", "Awaiting Unit Head Review"];

function errorMessage(error: unknown): string {
  const data = (error as { response?: { data?: { message?: string; detail?: string } } })
    ?.response?.data;
  if (data?.message) return data.message;
  if (data?.detail) return data.detail;
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export function MyLeavePage() {
  const year = new Date().getFullYear();
  const balance = useBalance(year);
  const requests = useLeaveRequests();
  const apply = useApplyLeaveRequest();
  const withdraw = useWithdrawLeaveRequest();

  const [category, setCategory] = useState<LeaveCategory>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [halfDay, setHalfDay] = useState(false);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    apply.mutate(
      { category, start_date: startDate, end_date: endDate, reason, half_day: halfDay },
      {
        onSuccess: () => {
          setStartDate("");
          setEndDate("");
          setReason("");
          setHalfDay(false);
        },
      },
    );
  };

  return (
    <Stack gap="lg">
      <Title order={2}>My leave</Title>

      <Stack gap="xs">
        <Title order={4}>Balance for {year}</Title>
        {balance.isPending && <Loader size="sm" />}
        {balance.isError && <Alert color="red">{errorMessage(balance.error)}</Alert>}
        {balance.data && (
          <Table>
            <Table.Thead>
              <Table.Tr><Table.Th>Category</Table.Th><Table.Th>Days left</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {balance.data.map((row) => (
                <Table.Tr key={row.category}>
                  <Table.Td>{row.category}</Table.Td>
                  <Table.Td>{row.amount}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>

      <Stack gap="xs">
        <Title order={4}>Apply for leave</Title>
        <form onSubmit={onSubmit}>
          <Stack gap="sm">
            <Select
              label="Category"
              data={[...LEAVE_CATEGORIES]}
              value={category}
              onChange={(value) => value && setCategory(value as LeaveCategory)}
              allowDeselect={false}
            />
            <TextInput label="From" type="date" required value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)} />
            <TextInput label="To" type="date" required value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)} />
            <TextInput label="Reason" required value={reason}
              onChange={(e) => setReason(e.currentTarget.value)} />
            <Checkbox label="Half day" checked={halfDay}
              onChange={(e) => setHalfDay(e.currentTarget.checked)} />
            {apply.isError && <Alert color="red">{errorMessage(apply.error)}</Alert>}
            <Button type="submit" loading={apply.isPending}>Apply</Button>
          </Stack>
        </form>
      </Stack>

      <Stack gap="xs">
        <Title order={4}>My requests</Title>
        {requests.isPending && <Loader size="sm" />}
        {requests.isError && <Alert color="red">{errorMessage(requests.error)}</Alert>}
        {withdraw.isError && <Alert color="red">{errorMessage(withdraw.error)}</Alert>}
        {requests.data && requests.data.length === 0 && (
          <Text c="dimmed">You have not applied for any leave yet.</Text>
        )}
        {requests.data && requests.data.length > 0 && (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th><Table.Th>From</Table.Th><Table.Th>To</Table.Th>
                <Table.Th>Status</Table.Th><Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.data.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>{r.category}</Table.Td>
                  <Table.Td>{r.start_date}</Table.Td>
                  <Table.Td>{r.end_date}</Table.Td>
                  <Table.Td>{r.status}</Table.Td>
                  <Table.Td>
                    {WITHDRAWABLE.includes(r.status) && (
                      <Button size="xs" variant="light" loading={withdraw.isPending}
                        onClick={() => withdraw.mutate(r.id)}>Withdraw</Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Stack>
  );
}

export default MyLeavePage;
