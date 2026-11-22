import {
  Alert,
  Button,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from '@mantine/core';
import { useAuth } from '../../../auth/AuthProvider';
import {
  useLeaveRequests,
  useLeaveTypes,
  useLeaveAction,
} from '../api/hooks';
import LeaveApplicationForm from './LeaveApplicationForm';
import type { LeaveRequest } from '../api/hooks'
import { Fragment, useState } from 'react';

export default function LeaveRequestList() {
  const { session, can } = useAuth();
  const { data: leaveRequests = [], isLoading: isRequestsLoading, error: requestsError } = useLeaveRequests();
  const { data: leaveTypes = [] } = useLeaveTypes();
  const { mutateAsync, isPending, error } = useLeaveAction();
  const [sharedNotes, setSharedNotes] = useState('');
  const [showDetails, setShowDetails] = useState<Record<number, boolean>>({});

  const handleAction = async (request: LeaveRequest, action: 'decide' | 'withdraw' | 'substitute-response' | 'renominate' | 'amend', payload?: Record<string, unknown>) => {
    try {
      await mutateAsync({ request_id: request.id, action, payload });
    } catch {}
  };
  const renderTableRow = (request: LeaveRequest) => {
    return (
      <Fragment key={request.id}>
        <tr>
          <td>
            <Stack>
              <Text>{request.id}</Text>
              <Text>{request.operation}</Text>
            </Stack>
          </td>
          <td>{request.employee}</td>
          <td>
            {leaveTypes.find(t => t.id === request.leave_type)?.type || ''}
          </td>
          <td>
            <Stack>
              <Text>{request.start_date}</Text>
              <Text>{request.end_date}</Text>
            </Stack>
          </td>
          <td>{request.days}</td>
          <td>{request.status}</td>
          <td>{request.substitute_status}</td>
          <td>
            <Group>
              <button type="button" onClick={() => setShowDetails(prev => ({ ...prev, [request.id]: !prev[request.id] }))}
              className="Details">
              Details
            </button>
            {request.status === 'PENDING' && (
                <>
                  {request.employee === session?.user.id && (
                    <Button
                      onClick={() => handleAction(request, 'withdraw')}
                      disabled={isPending}
                    >
                      Withdraw
                    </Button>
                  )}
                  {request.substitute_status === 'PENDING' && request.substitute === session?.user.id && (
                    <>
                      <Button
                        onClick={() =>
                          handleAction(
                            request,
                            'substitute-response',
                            { accept: true },
                          )
                        }
                        disabled={isPending}
                      >
                        Accept
                      </Button>
                      <Button
                        onClick={() =>
                          handleAction(
                            request,
                            'substitute-response',
                            { accept: false },
                          )
                        }
                        disabled={isPending}
                      >
                        Decline
                      </Button>
                    </>
                  )}
                </>
              )}
              {request.status === 'PENDING' &&
                can('elm.leave_requests.approve') &&
                request.route[request.step] === session?.user.id &&
                ['NONE', 'ACCEPTED'].includes(request.substitute_status) && (
                  <Group>
                    {request.route.length === request.step + 1 ? (
                      ['APPROVE', 'REJECT'].map(decision => (
                        <Button
                          key={decision}
                          onClick={() =>
                            handleAction(
                              request,
                              'decide',
                              { decision, notes: sharedNotes },
                            )
                          }
                          disabled={isPending}
                        >
                          {decision}
                        </Button>
                      ))
                    ) : (
                      ((request.step === 0) ? ["RECOMMEND", "NOT_RECOMMEND"] : ["FORWARD"]).map(decision => (
                        <Button
                          key={decision}
                          onClick={() =>
                            handleAction(
                              request,
                              'decide',
                              { decision, notes: sharedNotes },
                            )
                          }
                          disabled={isPending}
                        >
                          {decision}
                        </Button>
                      ))
                    )}
                  </Group>
                )}
            </Group>
          </td>
        </tr>
        {showDetails[request.id] && (
          <tr>
            <td colSpan={8}>
              <Stack gap="md">
                <Text fw={700}>Purpose:</Text>
                <Text>{request.purpose}</Text>
                <Text fw={700}>Route:</Text>
                <Text>{request.route.join(', ')}</Text>
                <Text fw={700}>Events:</Text>
                {request.events.map(event => (
                  <Text key={event.id}>
                    {event.action} by {event.actor ? event.actor : 'System'} on{' '}
                    {event.created_at}
                  </Text>
                ))}
              </Stack>
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  return (
    <Paper p="md">
      <Title order={2}>Leave Requests</Title>

      {can('elm.leave_requests.apply') && (
        <LeaveApplicationForm />
      )}

      {requestsError && (
        <Alert title="Error" color="red">
          {requestsError.message}
        </Alert>
      )}

      {isRequestsLoading && (
        <Alert title="Loading" color="blue">Loading leave requests...</Alert>
      )}

      {!isRequestsLoading && leaveRequests.length === 0 && (
        <Alert title="No Requests" color="yellow">
          No leave requests found. Create a new request using the form above.
        </Alert>
      )}

      {leaveRequests.length > 0 && (
        <Table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Employee</th>
              <th>Type</th>
              <th>Dates</th>
              <th>Days</th>
              <th>Status</th>
              <th>Consent</th>
<th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {leaveRequests.map(renderTableRow)}
          </tbody>
        </Table>
      )}

      {error && (
        <Alert title="Mutation Error" color="red">
          {error.message}
        </Alert>
      )}

      <Textarea label="Decision notes" value={sharedNotes} onChange={(event) => setSharedNotes(event.target.value)} />
    </Paper>
  );
}
