import { Select } from "@mantine/core";
import { useState } from "react";

import { useEmployeeSearch } from "../api/hooks";

/** Faculty and staff only; the server never returns students or the caller. */
export function EmployeePicker({ value, onChange, label, description }: {
  value: number | null;
  onChange: (id: number | null) => void;
  label: string;
  description?: string;
}) {
  const [q, setQ] = useState("");
  const { data = [], isFetching } = useEmployeeSearch(q);
  const options = data.map((e) => ({
    value: String(e.user_id),
    label: `${e.display_name} (${e.username}${e.department ? `, ${e.department}` : ""})`,
  }));
  return (
    <Select
      label={label} description={description} searchable clearable
      placeholder="Type at least two letters of a name"
      data={options} value={value != null ? String(value) : null}
      onChange={(v) => onChange(v ? Number(v) : null)}
      searchValue={q} onSearchChange={setQ}
      nothingFoundMessage={isFetching ? "Searching…" : q.length < 2 ? "" : "No match"}
      filter={({ options: o }) => o}
    />
  );
}
