import { Alert, Button, Card, Container, Group, Select, Stack, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalRouting, useLeaveCategories, useSaveApprovalRouting } from "../api/hooks";
import type { ApprovalRouting } from "../api/types";

export default function ApprovalRoutingPage() {
  const categories = useLeaveCategories();
  const routing = useApprovalRouting();
  const save = useSaveApprovalRouting();
  const [code, setCode] = useState<string | null>(null);
  const [unitRole, setUnitRole] = useState("");
  const [estEnabled, setEstEnabled] = useState<string | null>(null);
  const [estRole, setEstRole] = useState("");
  const [finalRole, setFinalRole] = useState("");

  const selected = (routing.data ?? []).find((item) => item.leave_category_code === code);
  useEffect(() => {
    setUnitRole(selected?.unit_head_role ?? "");
    setEstEnabled(selected?.establishment_enabled == null ? null : String(selected.establishment_enabled));
    setEstRole(selected?.establishment_role ?? "");
    setFinalRole(selected?.final_authority_role ?? "");
  }, [code, selected?.unit_head_role, selected?.establishment_enabled, selected?.establishment_role, selected?.final_authority_role]);

  if (categories.error) return <Container size="lg"><ErrorState error={categories.error} /></Container>;
  if (routing.error) return <Container size="lg"><ErrorState error={routing.error} /></Container>;
  const options = (categories.data ?? []).map((item) => ({ value: item.code, label: item.code + " · " + item.label }));
  const higher = code != null && !["CL", "RH"].includes(code);

  const submit = () => {
    if (!code || (higher && estEnabled === null)) return;
    const payload: Omit<ApprovalRouting, "configured"> = {
      leave_category_code: code,
      unit_head_role: unitRole.trim(),
      establishment_enabled: higher ? estEnabled === "true" : null,
      establishment_role: estRole.trim(),
      final_authority_role: finalRole.trim(),
    };
    save.mutate(payload);
  };

  return (
    <Container size="md">
      <PageHeader title="Approval Routing" subtitle="Enter the exact role names configured in IAM. Routing remains blocked until required fields are complete." />
      {save.error && <Alert color="red">{String(save.error)}</Alert>}
      {save.isSuccess && <Alert color="green">Routing saved. Configured: {String(save.data.configured)}</Alert>}
      <Card withBorder>
        <Stack>
          <Select label="Leave category" data={options} value={code} onChange={setCode} />
          {code && (
            <>
              <TextInput label="Unit Head role (exact IAM role name)" value={unitRole} onChange={(event) => setUnitRole(event.currentTarget.value)} />
              {higher && (
                <>
                  <Select label="Route through Establishment?" data={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} value={estEnabled} onChange={setEstEnabled} />
                  {estEnabled === "true" && <TextInput label="Establishment role (exact IAM role name)" value={estRole} onChange={(event) => setEstRole(event.currentTarget.value)} />}
                  <TextInput label="Final sanction authority role (exact IAM role name)" value={finalRole} onChange={(event) => setFinalRole(event.currentTarget.value)} />
                </>
              )}
              <Group>
                <Button onClick={submit} loading={save.isPending} disabled={higher && estEnabled === null}>
                  Save routing
                </Button>
              </Group>
            </>
          )}
        </Stack>
      </Card>
    </Container>
  );
}
