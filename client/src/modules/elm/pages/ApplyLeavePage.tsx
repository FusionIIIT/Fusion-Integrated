import { useEffect, useState } from "react";
import {
  Alert, Button, Container, Select, Stack, Textarea, TextInput, Title,
} from "@mantine/core";
import { errorMessage, http } from "../../../lib/http";
import { colleagues, type Colleague } from "../api";
import { ElmNavigation } from "../components/RequestsPage";

type HalfDay = "full" | "first" | "second";

function isHalfDay(value: string | null): value is HalfDay {
  return value === "full" || value === "first" || value === "second";
}

export default function ApplyLeavePage() {
  const [people, setPeople] = useState<Colleague[]>([]);
  const [category, setCategory] = useState("CL");
  const [dates, setDates] = useState({ start_date: "", end_date: "" });
  const [half, setHalf] = useState<HalfDay>("full");
  const [substitute, setSubstitute] = useState<string | null>(null);
  const [station, setStation] = useState("");
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    colleagues().then(setPeople).catch(failure => setError(errorMessage(failure)));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await http.post("/elm/applications/", {
        category, ...dates,
        first_half: category === "CL" && half === "first",
        second_half: category === "CL" && half === "second",
        substitute: substitute ? Number(substitute) : null,
        station_leave_details: station ? { details: station } : {},
        remarks,
      });
      setMessage("Leave application submitted.");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  return <Container size="sm">
    <ElmNavigation />
    <Title order={1} mb="lg">Apply for Leave</Title>
    <form onSubmit={submit}>
      <Stack>
        <Select label="Category" required allowDeselect={false}
          data={["CL", "RH", "SCL", "EL", "COL", "VL"]} value={category}
          onChange={value => { if (value) setCategory(value); }} />
        {category === "CL" && <Select
          label="CL duration" allowDeselect={false} value={half}
          data={[
            { value: "full", label: "Full day" }, { value: "first", label: "First half" },
            { value: "second", label: "Second half" },
          ]}
          onChange={value => { if (isHalfDay(value)) setHalf(value); }}
        />}
        <TextInput label="Start date" required type="date" value={dates.start_date}
          onChange={event => setDates({ ...dates, start_date: event.target.value })} />
        <TextInput label="End date" required type="date" value={dates.end_date}
          onChange={event => setDates({ ...dates, end_date: event.target.value })} />
        <Select label="Substitute" placeholder="No substitute" clearable searchable
          value={substitute} onChange={setSubstitute}
          data={people.map(person => ({ value: String(person.id), label: person.name }))} />
        <Textarea label="Purpose / remarks" value={remarks}
          onChange={event => setRemarks(event.target.value)} />
        <Textarea label="Station Leave details (optional)" value={station}
          onChange={event => setStation(event.target.value)} />
        {error && <Alert color="red" role="alert">{error}</Alert>}
        {message && <Alert color="green" role="status">{message}</Alert>}
        <Button type="submit" loading={busy}>Submit application</Button>
      </Stack>
    </form>
  </Container>;
}
