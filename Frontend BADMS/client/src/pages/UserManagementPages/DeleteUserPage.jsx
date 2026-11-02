/* eslint-disable react/prop-types */
import { useState, useEffect, useCallback } from 'react';
import {
    Box,
    Group,
    TextInput,
    Container,
    Title,
    Modal,
    Button,
    Checkbox,
    Grid,
    Card,
    Text,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { users } from '../../data/users';
import { BarChart } from '@mantine/charts';
import PageHeader from '../../components/PageHeader/PageHeader';

function Simple({ title, data, colors, datakey }) {
    return (
        <div>
            {/* Heading */}
            <Title order={2} align="center" mt="md" mb="lg">
                {title}
            </Title>

            {/* BarChart */}
            <BarChart
                h={250}
                data={data}
                dataKey={datakey}
                series={colors}
                tickLine="y"
                styles={{
                    bar: {
                        transition: '0.3s', // Add smooth transition for hover
                        '&:hover': {
                            fillOpacity: 0.8, // Make it slightly transparent on hover
                        },
                    },
                }}
            />
        </div>
    );
}

const DeleteUserPage = () => {
    const [userBatchData, setUserBatchData] = useState([]);
    const [colors] = useState([{ name: 'Deleted', color: 'red' }]);
    const [userList, setUserList] = useState(users);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedUsers, setSelectedUsers] = useState([]);
    const [opened, { open, close }] = useDisclosure(false);

    useEffect(() => {
        // Aggregating user batch data to show in the BarChart
        const aggregatedData = userList.reduce((acc, user) => {
            const batch = user.batch;
            if (!acc[batch]) {
                acc[batch] = { batch, Deleted: 0 };
            }
            acc[batch].Deleted += 100; // Static data for now
            return acc;
        }, {});
        setUserBatchData(Object.values(aggregatedData));
    }, [userList]);

    const handleSearch = (event) => {
        setSearchTerm(event.target.value.toLowerCase());
    };

    const toggleSelectUsers = (id) => {
        setSelectedUsers((prevSelected) =>
            prevSelected.includes(id)
                ? prevSelected.filter((userId) => userId !== id)
                : [...prevSelected, id]
        );
    };

    const handleDelete = useCallback(() => {
        open();
    }, [open]);

    const confirmDelete = () => {
        setUserList(userList.filter(user => !selectedUsers.includes(user.id)));
        setSelectedUsers([]);
        close();
    };

    const filteredUsers = userList.filter(user => {
        const searchLower = searchTerm.toLowerCase();
        return (
            user.name.toLowerCase().includes(searchLower) ||
            user.branch.toLowerCase().includes(searchLower) ||
            user.role.toLowerCase().includes(searchLower) ||
            user.rollNo?.toLowerCase().includes(searchLower)
        );
    });

    return (
        <Container size="lg">
            <PageHeader
                title="Delete Users"
                subtitle="Search, select and permanently remove user accounts from the system."
            />

            <Card padding="lg" withBorder radius="lg" mb="lg">
                <Simple title={'User Batch Data'} colors={colors} data={userBatchData} />
            </Card>

            <Card padding="lg" withBorder radius="lg">
                <Group justify="center" mb="lg">
                    <TextInput
                        placeholder="Search by name, role, roll no, etc."
                        value={searchTerm}
                        onChange={handleSearch}
                        size="md"
                        w={400}
                    />
                </Group>

                <Grid>
                    {filteredUsers.map((user) => (
                        <Grid.Col span={{ base: 12, sm: 6 }} key={user.id}>
                            <Card withBorder radius="md" padding="sm">
                                <Group align="flex-start" wrap="nowrap">
                                    <Checkbox
                                        checked={selectedUsers.includes(user.id)}
                                        onChange={() => toggleSelectUsers(user.id)}
                                        styles={{ input: { cursor: 'pointer' } }}
                                    />
                                    <Box style={{ flex: 1 }}>
                                        <Text fw={600}>{user.name}</Text>
                                        <Text size="sm" c="dimmed">{user.rollNo}</Text>
                                        <Text size="xs" c="dimmed">{user.role}</Text>
                                    </Box>
                                </Group>
                            </Card>
                        </Grid.Col>
                    ))}
                </Grid>

                <Group justify="flex-end" mt="lg">
                    <Button
                        color="red"
                        onClick={handleDelete}
                        disabled={selectedUsers.length === 0} // Disable if no users are selected
                    >
                        Delete Selected
                    </Button>
                </Group>
            </Card>

            <Modal opened={opened} onClose={close} title="Confirm Action">
                <Modal.Body>
                    Are you sure you want to delete the selected users? This action cannot be undone.
                </Modal.Body>
                <Group justify="flex-end" mt="md">
                    <Button variant="default" onClick={close}>
                        Cancel
                    </Button>
                    <Button color="red" onClick={confirmDelete}>
                        Proceed
                    </Button>
                </Group>
            </Modal>
        </Container>
    );
};
export default DeleteUserPage;
