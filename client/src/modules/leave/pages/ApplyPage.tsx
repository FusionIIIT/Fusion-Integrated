import { useState } from "react";
import { Button, Card, Checkbox, Container, Select, Stack, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubmitLeave } from "../api/hooks";

export default function ApplyPage() {
  const submit = useSubmitLeave();
  const navigate = useNavigate();
  const [category, setCategory] = useState<string | null>("CL");
  const [startOn, setStartOn] = useState("");
  const [endOn, setEndOn] = useState("");
  const [purpose, setPurpose] = useState("");
  const [half, setHalf] = useState<string | null>("");
  const [station, setStation] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [medical, setMedical] = useState(false);
  const [substitute, setSubstitute] = useState("");

  function onSubmit() {
    submit.mutate({
      category, start_on: startOn, end_on: endOn, purpose,
      half: half || "", station_leave: station, station_details: stationDetails,
      medical_evidence: medical,
      substitute_user_id: substitute ? Number(substitute) : null,
    }, {
      onSuccess: () => {
        notifications.show({ color: "green", message: "Leave request submitted" });
        navigate("/leave/mine");
      },
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="sm">
      <PageHeader title="Apply for leave" subtitle="CL, RH, SCL, EL, COL and VL in the study baseline" />
      <Card padding="lg">
        <Stack>
          <Select label="Category" value={category} onChange={setCategory}
            data={["CL", "RH", "SCL", "EL", "COL", "VL"]} />
          <TextInput type="date" label="Start" value={startOn} onChange={(e) => setStartOn(e.target.value)} />
          <TextInput type="date" label="End" value={endOn} onChange={(e) => setEndOn(e.target.value)} />
          {category === "CL" && (
            <Select label="Half day" value={half} onChange={setHalf}
              data={[{ value: "", label: "Full day" }, { value: "first", label: "First half" },
                     { value: "second", label: "Second half" }]} />
          )}
          <Textarea label="Purpose / reason" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          <Checkbox label="Station Leave (outside Jabalpur)" checked={station}
            onChange={(e) => setStation(e.currentTarget.checked)} />
          {station && (
            <TextInput label="Station details" value={stationDetails}
              onChange={(e) => setStationDetails(e.target.value)} />
          )}
          {category === "COL" && (
            <Checkbox label="Supporting medical evidence provided" checked={medical}
              onChange={(e) => setMedical(e.currentTarget.checked)} />
          )}
          <TextInput label="Substitute user id (required for SCL/EL/COL/VL)"
            value={substitute} onChange={(e) => setSubstitute(e.target.value)} />
          <Button onClick={onSubmit} loading={submit.isPending}>Submit</Button>
        </Stack>
      </Card>
    </Container>
  );
}
