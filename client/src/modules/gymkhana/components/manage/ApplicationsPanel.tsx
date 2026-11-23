import { useState } from "react";
import { Badge, Button, Group, TextInput } from "@mantine/core";
import { FaUserCheck } from "react-icons/fa";

import { DataTable, type RowKey } from "../../../../ui/components/DataTable";
import { ErrorState } from "../../../../ui/components/ErrorState";
import { useApproveMemberships, useMemberships } from "../../api/hooks";
import type { LedClub, Membership } from "../../api/types";
import { date, person } from "../format";
import { LoadMore } from "../LoadMore";
import { done, refused } from "../toasts";

export function ApplicationsPanel({ club }: { club: LedClub }) {
  const list = useMemberships({ club_id: club.id });
  const approve = useApproveMemberships();
  const [selected, setSelected] = useState<Set<RowKey>>(new Set());
  const [remarks, setRemarks] = useState("");
  if (list.error) return <ErrorState error={list.error} />;

  function submit() {
    approve.mutate({ ids: [...selected].map(Number), remarks }, {
      onSuccess: ({ approved, refusal }) => {
        if (approved) done("Applications approved", `${approved} approved.`);
        if (refusal) refused("Some applications were not approved", refusal);
        setSelected(new Set());
        setRemarks("");
      },
    });
  }

  return (
    <>
      <Group align="flex-end" mb="md">
        <TextInput label="Remarks (optional)" value={remarks} w={320}
          onChange={(e) => setRemarks(e.currentTarget.value)} />
        <Button onClick={submit} disabled={!selected.size} loading={approve.isPending}>
          Approve selected
        </Button>
      </Group>
      <DataTable<Membership>
        rows={list.rows} loading={list.loading} rowKey={(m) => m.id}
        selection={{
          selected, onChange: setSelected, isSelectable: (m) => m.status === "open",
        }}
        columns={[
          {
            key: "student", header: "Student",
            render: (m) => person(m.student_name, m.student_id),
          },
          { key: "description", header: "Application" },
          { key: "applied_at", header: "Applied", render: (m) => date(m.applied_at) },
          {
            key: "status", header: "Status",
            render: (m) => (
              <Badge variant="light" color={m.status === "confirmed" ? "green" : "blue"}>
                {m.status}
              </Badge>
            ),
          },
        ]}
        empty={{ icon: FaUserCheck, title: "No applications yet" }}
      />
      <LoadMore list={list} />
    </>
  );
}
