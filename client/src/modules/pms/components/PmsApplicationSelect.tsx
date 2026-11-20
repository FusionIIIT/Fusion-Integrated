import { Select } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { usePmsApplications } from "../api/hooks";

export function PmsApplicationSelect({
  value, onChange, label = "Application", allowEmpty = true,
}: {
  value: string | null;
  onChange: (value: string | null) => void;
  label?: string;
  allowEmpty?: boolean;
}) {
  const query = usePmsApplications();
  if (query.error) return <ErrorState error={query.error} />;
  return (
    <Select
      label={label}
      placeholder={query.isPending ? "Loading applications…" : "Choose an application"}
      data={(query.data ?? []).map((app) => ({
        value: String(app.id),
        label: `${app.application_no} · ${app.title} (${app.status.replace(/_/g, " ")})`,
      }))}
      value={value}
      onChange={onChange}
      searchable
      clearable={allowEmpty}
      disabled={query.isPending}
      nothingFoundMessage="No visible applications"
    />
  );
}
