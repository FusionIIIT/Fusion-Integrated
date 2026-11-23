import { useState } from "react";
import { Badge, Button, FileInput, Stack, Textarea, TextInput } from "@mantine/core";
import { FaRupeeSign } from "react-icons/fa";

import { DataTable } from "../../../../ui/components/DataTable";
import { ErrorState } from "../../../../ui/components/ErrorState";
import { FormModal } from "../../../../ui/components/FormModal";
import { useBudgets, useDownload, useSubmitBudget } from "../../api/hooks";
import type { Budget, LedClub } from "../../api/types";
import { date } from "../format";
import { LoadMore } from "../LoadMore";
import { done, refused } from "../toasts";

export function BudgetsPanel({ club }: { club: LedClub }) {
  const list = useBudgets({ club_id: club.id });
  const download = useDownload();
  const [requesting, setRequesting] = useState(false);
  if (list.error) return <ErrorState error={list.error} />;
  return (
    <>
      <Button mb="md" onClick={() => setRequesting(true)}>Request budget</Button>
      <DataTable<Budget>
        rows={list.rows} loading={list.loading} rowKey={(b) => b.id}
        columns={[
          { key: "purpose", header: "Purpose" },
          { key: "amount", header: "Amount", align: "right", render: (b) => `₹ ${b.amount}` },
          { key: "submitted_at", header: "Submitted", render: (b) => date(b.submitted_at) },
          { key: "status", header: "Status", render: (b) => <Badge variant="light">{b.status}</Badge> },
          {
            key: "file", header: "", align: "right",
            render: (b) => b.supporting_file && (
              <Button size="xs" variant="light"
                aria-label={`Download supporting file for ${b.purpose}`}
                onClick={() => download.mutate(b.supporting_file ?? "", {
                  onError: (e) => refused("Could not download the file", e),
                })}>
                File
              </Button>
            ),
          },
        ]}
        empty={{ icon: FaRupeeSign, title: "No budget requests yet" }}
      />
      <LoadMore list={list} />
      {requesting && <BudgetModal club={club} onClose={() => setRequesting(false)} />}
    </>
  );
}

function BudgetModal({ club, onClose }: { club: LedClub; onClose: () => void }) {
  const submit = useSubmitBudget();
  const [f, setF] = useState({ purpose: "", amount: "", description: "" });
  const [file, setFile] = useState<File | null>(null);
  const negative = Number(f.amount) < 0;
  return (
    <FormModal
      opened onClose={onClose} title="Request budget" subtitle={club.name}
      submitLabel="Submit request" submitting={submit.isPending} error={submit.error}
      disabled={!f.purpose.trim() || !f.amount || negative || !file}
      disabledReason={negative ? "The amount cannot be negative."
        : "Give a purpose, an amount and the supporting file."}
      onSubmit={() => file && submit.mutate({ club_id: club.id, ...f, supporting_file: file }, {
        onSuccess: () => {
          done("Request submitted", "Your budget request is open for tracking.");
          onClose();
        },
      })}
    >
      <Stack gap="md">
        <TextInput label="Purpose" required maxLength={255} value={f.purpose}
          onChange={(e) => setF({ ...f, purpose: e.currentTarget.value })} />
        <TextInput label="Amount (₹)" type="number" min={0} step="0.01" required value={f.amount}
          onChange={(e) => setF({ ...f, amount: e.currentTarget.value })} />
        <FileInput label="Supporting file" required clearable value={file} onChange={setFile}
          placeholder="Up to 5 MB" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.txt"
          clearButtonProps={{ "aria-label": "Remove supporting file" }} />
        <Textarea label="Description" autosize minRows={3} value={f.description}
          onChange={(e) => setF({ ...f, description: e.currentTarget.value })} />
      </Stack>
    </FormModal>
  );
}
