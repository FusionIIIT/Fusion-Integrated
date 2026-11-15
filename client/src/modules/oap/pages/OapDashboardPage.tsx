import { useNavigate } from 'react-router-dom';
import { Card, Tabs, Button, Badge, Table, Group, Stack, Title, Text, TextInput, Select } from '@mantine/core';
import { useQuery } from 'react-query';

interface Procedure {
  id: number;
  name: string;
  type: string;
}

const OapDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: procedures } = useQuery<Procedure[]>(
    'procedures',
    async () => {
      try {
        const response = await fetch('/api/procedures');
        return await response.json();
      } catch (error) {
        console.error('Error fetching procedures:', error);
        throw error;
      }
    }
  );

  const handleLeaveClick = () => {
    navigate('/oap/leave');
  };

  const handleBonafideClick = () => {
    navigate('/oap/bonafide');
  };

  const handleNoducesClick = () => {
    navigate('/oap/noduces');
  };

  const handleAssistantshipClick = () => {
    navigate('/oap/assistantship');
  };

  const handleSeminarClick = () => {
    navigate('/oap/seminar');
  };

  return (
    <Stack gap={20}>
      <Title order={2} align="center">
        Other Academic Procedures
      </Title>
      <Tabs defaultValue="student-leave">
        <Tabs.Tab value="student-leave" label="Student Leave">
          <Card>
            <Group align="center">
              <Text>Student Leave Form</Text>
              <Button onClick={handleLeaveClick}>Submit</Button>
            </Group>
            {/* Dummy procedures or forms */}
            <Table
              columns={[
                { header: 'ID', accessor: 'id' },
                { header: 'Name', accessor: 'name' },
                { header: 'Type', accessor: 'type' },
              ]}
              data={procedures}
            />
          </Card>
        </Tabs.Tab>
        <Tabs.Tab value="bonafide" label="Bonafide Certificates">
          <Card>
            <Group align="center">
              <Text>Bonafide Certificate Form</Text>
              <Button onClick={handleBonafideClick}>Submit</Button>
            </Group>
            {/* Dummy procedures or forms */}
            <Table
              columns={[
                { header: 'ID', accessor: 'id' },
                { header: 'Name', accessor: 'name' },
                { header: 'Type', accessor: 'type' },
              ]}
              data={procedures}
            />
          </Card>
        </Tabs.Tab>
        <Tabs.Tab value="nodues" label="No-Dues Clearance">
          <Card>
            <Group align="center">
              <Text>No-Dues Clearance Form</Text>
              <Button onClick={handleNoducesClick}>Submit</Button>
            </Group>
            {/* Dummy procedures or forms */}
            <Table
              columns={[
                { header: 'ID', accessor: 'id' },
                { header: 'Name', accessor: 'name' },
                { header: 'Type', accessor: 'type' },
              ]}
              data={procedures}
            />
          </Card>
        </Tabs.Tab>
        <Tabs.Tab value="assistantship" label="PG Assistantship">
          <Card>
            <Group align="center">
              <Text>PG Assistantship Form</Text>
              <Button onClick={handleAssistantshipClick}>Submit</Button>
            </Group>
            {/* Dummy procedures or forms */}
            <Table
              columns={[
                { header: 'ID', accessor: 'id' },
                { header: 'Name', accessor: 'name' },
                { header: 'Type', accessor: 'type' },
              ]}
              data={procedures}
            />
          </Card>
        </Tabs.Tab>
        <Tabs.Tab value="seminar" label="Graduate Seminars">
          <Card>
            <Group align="center">
              <Text>Graduate Seminar Form</Text>
              <Button onClick={handleSeminarClick}>Submit</Button>
            </Group>
            {/* Dummy procedures or forms */}
            <Table
              columns={[
                { header: 'ID', accessor: 'id' },
                { header: 'Name', accessor: 'name' },
                { header: 'Type', accessor: 'type' },
              ]}
              data={procedures}
            />
          </Card>
        </Tabs.Tab>
      </Tabs>
    </Stack>
  );
};

export default OapDashboardPage;