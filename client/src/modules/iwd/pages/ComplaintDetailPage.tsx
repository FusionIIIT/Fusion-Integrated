import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useParams, Link } from "react-router-dom";
import { FaArrowLeft } from "react-icons/fa";

import { http, errorMessage } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { Complaint } from "../types";

export default function ComplaintDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);

  // Engineer assessment state
  const [assessmentDetails, setAssessmentDetails] = useState("");
  const [submittingAssessment, setSubmittingAssessment] = useState(false);

  // Estimate state
  const [cost, setCost] = useState("");
  const [days, setDays] = useState("3");
  const [materials, setMaterials] = useState("");
  const [submittingEstimate, setSubmittingEstimate] = useState(false);

  // Verification state
  const [verifyRemarks, setVerifyRemarks] = useState("");
  const [submittingVerify, setSubmittingVerify] = useState(false);

  const fetchComplaint = () => {
    setLoading(true);
    http
      .get(`/iwd/complaints/${id}/`)
      .then((res) => {
        setComplaint(res.data);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchComplaint();
  }, [id]);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  if (loading || !complaint) {
    return <Container size="xl"><Text>Loading complaint...</Text></Container>;
  }

  const handleAssess = async () => {
    setSubmittingAssessment(true);
    try {
      await http.post(`/iwd/complaints/${id}/assess/`, {
        assessment_details: assessmentDetails,
      });
      notifications.show({ color: "teal", title: "Assessment Saved", message: "Complaint marked Assessed." });
      fetchComplaint();
    } catch (err) {
      notifications.show({ color: "red", title: "Error", message: errorMessage(err) });
    } finally {
      setSubmittingAssessment(false);
    }
  };

  const handleEstimate = async () => {
    setSubmittingEstimate(true);
    try {
      await http.post(`/iwd/complaints/${id}/estimates/`, {
        total_cost: cost,
        estimated_time_days: parseInt(days, 10),
        materials_details: materials,
      });
      notifications.show({ color: "teal", title: "Estimate Submitted", message: "Estimate routed for review." });
      fetchComplaint();
    } catch (err) {
      notifications.show({ color: "red", title: "Error", message: errorMessage(err) });
    } finally {
      setSubmittingEstimate(false);
    }
  };

  const handleVerify = async (outcome: "Approved" | "Rework") => {
    setSubmittingVerify(true);
    try {
      await http.post(`/iwd/complaints/${id}/verify/`, {
        outcome,
        remarks: verifyRemarks,
      });
      notifications.show({
        color: outcome === "Approved" ? "teal" : "orange",
        title: `Verification ${outcome}`,
        message: outcome === "Approved" ? "Complaint marked Resolved." : "Complaint sent for rework.",
      });
      fetchComplaint();
    } catch (err) {
      notifications.show({ color: "red", title: "Error", message: errorMessage(err) });
    } finally {
      setSubmittingVerify(false);
    }
  };

  return (
    <Container size="xl">
      <Group mb="md">
        <Button
          component={Link}
          to="/iwd/complaints"
          variant="subtle"
          leftSection={<FaArrowLeft size={12} />}
        >
          Back to Complaints
        </Button>
      </Group>

      <PageHeader
        title={`Complaint #${complaint.id}: ${complaint.category}`}
        subtitle={`Location: ${complaint.location}`}
        action={
          <Badge size="lg" color={complaint.is_resolved ? "teal" : "blue"}>
            {complaint.status}
          </Badge>
        }
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt="md">
        <Card withBorder padding="lg" radius="md">
          <Title order={4} mb="md">Complaint Details</Title>
          <Stack gap="xs">
            <Text size="sm"><strong>Category:</strong> {complaint.category}</Text>
            <Text size="sm"><strong>Location:</strong> {complaint.location}</Text>
            <Text size="sm"><strong>Urgency:</strong> {complaint.urgency}</Text>
            <Text size="sm"><strong>Requester User ID:</strong> {complaint.requester_user_id}</Text>
            <Text size="sm">
              <strong>Assigned Engineer ID:</strong> {complaint.assigned_engineer_id ?? "Unassigned"}
            </Text>
            <Text size="sm"><strong>Rework Count:</strong> {complaint.rework_count} / 1</Text>
            <Divider my="xs" />
            <Text size="sm"><strong>Remarks:</strong> {complaint.remarks || "None"}</Text>
            {complaint.assessment_details && (
              <Text size="sm"><strong>Technical Assessment:</strong> {complaint.assessment_details}</Text>
            )}
          </Stack>
        </Card>

        <Stack gap="lg">
          {/* Assessment Section for Engineer */}
          {complaint.status === "Assigned" && can("iwd.complaint.update") && (
            <Card withBorder padding="lg" radius="md">
              <Title order={4} mb="sm">Record Technical Assessment</Title>
              <Textarea
                placeholder="Enter scope and repair assessment details..."
                value={assessmentDetails}
                onChange={(e) => setAssessmentDetails(e.currentTarget.value)}
                minRows={3}
                mb="sm"
              />
              <Button onClick={handleAssess} loading={submittingAssessment}>
                Complete Assessment
              </Button>
            </Card>
          )}

          {/* Estimate Preparation Section for Engineer */}
          {complaint.status === "Assessed" && can("iwd.estimate.create") && (
            <Card withBorder padding="lg" radius="md">
              <Title order={4} mb="sm">Prepare Cost Estimate</Title>
              <Stack gap="sm">
                <TextInput
                  label="Total Estimated Cost (INR)"
                  placeholder="e.g. 15000 or 80000"
                  value={cost}
                  onChange={(e) => setCost(e.currentTarget.value)}
                />
                <TextInput
                  label="Estimated Duration (Days)"
                  value={days}
                  onChange={(e) => setDays(e.currentTarget.value)}
                />
                <Textarea
                  label="Materials & Work Scope Details"
                  value={materials}
                  onChange={(e) => setMaterials(e.currentTarget.value)}
                />
                <Button onClick={handleEstimate} loading={submittingEstimate}>
                  Submit Estimate
                </Button>
              </Stack>
            </Card>
          )}

          {/* Physical Verification Section for Department Head */}
          {complaint.status === "Verification Pending" && can("iwd.work.verify") && (
            <Card withBorder padding="lg" radius="md">
              <Title order={4} mb="sm">Physical Quality Verification</Title>
              <Text size="sm" c="dimmed" mb="sm">
                As Department Head, inspect repair quality on-site. Approval marks the complaint Resolved.
              </Text>
              <Textarea
                placeholder="Enter inspection remarks..."
                value={verifyRemarks}
                onChange={(e) => setVerifyRemarks(e.currentTarget.value)}
                minRows={2}
                mb="md"
              />
              <Group>
                <Button
                  color="teal"
                  onClick={() => handleVerify("Approved")}
                  loading={submittingVerify}
                >
                  Verify & Approve (Resolve)
                </Button>
                {complaint.rework_count < 1 && (
                  <Button
                    color="orange"
                    variant="outline"
                    onClick={() => handleVerify("Rework")}
                    loading={submittingVerify}
                  >
                    Quality Failed (Require Rework)
                  </Button>
                )}
              </Group>
            </Card>
          )}
        </Stack>
      </SimpleGrid>
    </Container>
  );
}
