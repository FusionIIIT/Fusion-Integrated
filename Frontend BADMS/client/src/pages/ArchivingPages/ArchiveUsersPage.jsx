import { useState, useEffect, useCallback } from 'react'
import {
    Box,
    Group,
    TextInput,
    Tabs,
    Container,
    Title,
    Modal,
    Button,
    Flex,
    Checkbox,
    Center,
    Grid
} from '@mantine/core'
import { Simple } from '../../charts/BarChart/Simple/Simple';
import { useDisclosure } from '@mantine/hooks';
import { users } from '../../data/users';
import { notifications } from '@mantine/notifications';
import SimplePieChart from '../../charts/PieChart/Tooltip/Tooltip';

const ArchiveUsersPage = () => {

    const [userRoleData, setUserRoleData] = useState([])
    const [userBatchData, setUserBatchData] = useState([])
    const [colors] = useState([
        { name: "Archived", color: 'blue.6' }
    ])
    const [userList, setUserList] = useState(users)
    useEffect(() => {
        const aggregatedData = userList.reduce((acc, user) => {
            const role = user.role;
            if (!acc[role]) {
                acc[role] = { name: role, value: 0, color: 'indigo.5' }
            }
            if (user.isArchived) {
                acc[role].value += 1
            }
            return acc;
        }, {})
        setUserRoleData(Object.values(aggregatedData));
    }, [userList])

    useEffect(() => {
        const aggregatedData = userList.reduce((acc, user) => {
            const batch = user.batch;
            if (!acc[batch]) {
                acc[batch] = { batch, Archived: 0 }
            }
            if (user.isArchived) {
                acc[batch].Archived += 100
            }
            return acc;
        }, {})
        setUserBatchData(Object.values(aggregatedData));
    }, [userList])

    // tabs section 
    const [searchTerm, setSearchTerm] = useState('');
    const [tabIndex, setTabIndex] = useState(0);
    const [selectedUsers, setSelectedUsers] = useState([]);
    const [isArchiving, setIsArchiving] = useState(false);
    const [opened, { open, close }] = useDisclosure(false);

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

    const handleArchive = useCallback(() => {
        open();
    }, [open]);

    const confirmArchive = () => {
        setUserList(
            userList.map(user => {
                if (selectedUsers.includes(user.id)) {
                    return { ...user, isArchived: !user.isArchived };
                }
                return user;
            })
        );
        setSelectedUsers([]);
        close();
        notifications.show({
            title: isArchiving ? 'Users Archived' : 'Users Unarchived',
            message: '',
            color: 'green',
            autoClose: 3000,
            disallowClose: false,
            position: 'top-center',
        });
    };

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                setIsArchiving(tabIndex === 0);
                handleArchive();
            }
        };

        window.addEventListener('keydown', handleKeyDown);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [tabIndex, handleArchive]);

    const filteredUsers = userList.filter(user => {
        const searchLower = searchTerm.toLowerCase();
        return (
            user.name.toLowerCase().includes(searchLower) ||
            user.branch.toLowerCase().includes(searchLower) ||
            user.role.toLowerCase().includes(searchLower) ||
            (user.rollNo?.toLowerCase().includes(searchLower))
        );
    });

    const displayedUsers = filteredUsers.filter(user => (tabIndex === 0 ? !user.isArchived : user.isArchived));

    return (
        <Container fluid my="md">
            <Flex
                direction={{ base: 'column', sm: 'row' }}
                gap={{ base: 'sm', sm: 'lg' }}
                justify={{ sm: 'center' }}
                mb={'1rem'}
            >
                <Button
                    variant="gradient"
                    size="xl"
                    radius="xs"
                    gradient={{ from: 'blue', to: 'cyan', deg: 90 }}
                    sx={{
                        display: 'block',
                        width: { base: '100%', sm: 'auto' },
                        whiteSpace: 'normal',
                        padding: '1rem',
                        textAlign: 'center',
                    }}
                >
                    <Title
                        order={1}
                        sx={{
                            fontSize: { base: 'lg', sm: 'xl' },
                            lineHeight: 1.2,
                            wordBreak: 'break-word',
                        }}
                    >
                        Archive Users
                    </Title>
                </Button>
            </Flex>
            <Grid style={{ display: 'flex', alignItems: 'stretch' }}>
                <Grid.Col span={6} style={{ display: 'flex' }}>
                    <Container style={{
                        backgroundColor: '#f8f9fa',
                        padding: '1rem',
                        border: '2px solid #ababab',
                        borderRadius: '15px',
                        flex: 1
                    }}>
                        <SimplePieChart data={userRoleData} />
                    </Container>
                </Grid.Col>
                <Grid.Col span={6} style={{ display: 'flex' }}>
                    <Container style={{
                        backgroundColor: '#f8f9fa',
                        padding: '1rem',
                        border: '2px solid #ababab',
                        borderRadius: '15px',
                        flex: 1
                    }}>
                        <Simple title={"User Batch Data"} colors={colors} data={userBatchData} />
                    </Container>
                </Grid.Col>
            </Grid>
            <Box mt={10}>
                <Group position="center" mb={5}>
                    <TextInput
                        placeholder="Search by title, message, etc."
                        value={searchTerm}
                        onChange={handleSearch}

                        styles={{
                            root: {
                                marginLeft: 'auto',
                                marginRight: 'auto',
                                width: '400px'
                            },
                            input: {
                                marginLeft: 'auto',
                                marginRight: 'auto',
                                backgroundColor: 'white',
                                borderRadius: '50px',
                                boxShadow: 'xl',
                                '&:hover': { boxShadow: '2xl' },
                                '&:focus': { borderColor: 'lightcoral' },
                            },
                        }}
                    />
                </Group>
                <Center>
                    <Tabs color="lightcoral" defaultValue='0' value={tabIndex} onChange={setTabIndex}
                        style={{
                            width: '100%',
                            backgroundColor: '#f8f9fa'
                        }}>
                        <Tabs.List justify='center' mb='10px'>
                            <Tabs.Tab value='0'>Active Users</Tabs.Tab>
                            <Tabs.Tab value='1'>Archived Users</Tabs.Tab>
                        </Tabs.List>

                        <Tabs.Panel value='0' style={{
                            minHeight: 300,
                            maxHeight: 400,
                            overflowY: 'auto',
                            scrollBehavior: 'auto',
                            backgroundColor: '#f8f9fa',
                        }}>
                            <Grid>
                                {filteredUsers.map((user) => (
                                    <Grid.Col span={6} key={user.id}>
                                        <Flex
                                            mb={5}
                                            align="center"
                                            style={{
                                                backgroundColor: 'white',
                                                padding: '10px',
                                                borderRadius: '8px',
                                                border: '2px solid #f0f0f0',
                                            }}>
                                            <Checkbox
                                                checked={selectedUsers.includes(user.id)}
                                                onChange={() => toggleSelectUsers(user.id)}
                                                styles={{
                                                    input: {
                                                        cursor: 'pointer',
                                                        width: '20px',
                                                        height: '20px',
                                                    },
                                                }}
                                            />
                                            <Box ml={10} style={{ flex: 1 }}>
                                                <div style={{ fontWeight: 'bold', fontSize: '1.2rem' }}>{user.name}</div>
                                                <div style={{ marginLeft: '10px', fontSize: '0.9rem' }}>{user.rollNo}</div>
                                                <div style={{ marginLeft: '10px', fontSize: '0.8rem' }}>{user.role}</div>
                                            </Box>
                                        </Flex>
                                    </Grid.Col>
                                ))}
                            </Grid>
                        </Tabs.Panel>

                        <Tabs.Panel value='1' style={{
                            minHeight: 300,
                            maxHeight: 400,
                            overflowY: 'auto',
                            scrollBehavior: 'auto',
                            backgroundColor: '#f8f9fa',
                        }}>
                            <Grid>
                                {displayedUsers.map((user) => (
                                    <Grid.Col span={6} key={user.id}>
                                        <Flex
                                            mb={5}
                                            align="center"
                                            style={{
                                                backgroundColor: 'white',
                                                padding: '10px',
                                                borderRadius: '8px',
                                                border: '2px solid #f0f0f0',
                                            }}>
                                            <Checkbox
                                                checked={selectedUsers.includes(user.id)}
                                                onChange={() => toggleSelectUsers(user.id)}
                                                styles={{
                                                    input: {
                                                        cursor: 'pointer',
                                                        width: '20px',
                                                        height: '20px',
                                                    },
                                                }}
                                            />
                                            <Box ml={10} style={{ flex: 1 }}>
                                                <div style={{ fontWeight: 'bold', fontSize: '1.2rem' }}>{user.name}</div>
                                                <div style={{ marginLeft: '10px', fontSize: '0.9rem' }}>{user.rollNo}</div>
                                                <div style={{ marginLeft: '10px', fontSize: '0.8rem' }}>{user.role}</div>
                                            </Box>
                                        </Flex>
                                    </Grid.Col>
                                ))}
                            </Grid>
                        </Tabs.Panel>
                    </Tabs>
                </Center>
                <Center mt={5}>
                    <Group mt={5}>
                        <Button
                            gradient={{ from: 'lightyellow', to: 'lightcoral' }}
                            color="coral"
                            onClick={() => {
                                setIsArchiving(tabIndex === '0');
                                handleArchive();
                            }}
                            disabled={selectedUsers.length === 0} // Disable if no Notifications are selected
                        >
                            {tabIndex === '0' ? 'Archive Selected' : 'Unarchive Selected'}
                        </Button>
                    </Group>
                </Center>
                <Modal opened={opened} onClose={close} title="Confirm Action" >
                    <Modal.Body>
                        Are you sure you want to {isArchiving ? 'archive' : 'unarchive'} the selected Users?
                    </Modal.Body>
                    <center>
                        <Button color="blue" onClick={confirmArchive} mr='10'>
                            Proceed
                        </Button>

                        <Button variant="outline" onClick={close}>
                            Cancel
                        </Button>
                    </center>
                </Modal>
            </Box>

        </Container>
    )
}

export default ArchiveUsersPage


//sample data
// export const data = [
//     { name: 'USA', value: 400, color: 'indigo.6' },
//     { name: 'India', value: 300, color: 'yellow.6' },
//     { name: 'Japan', value: 300, color: 'teal.6' },
//     { name: 'Other', value: 200, color: 'gray.6' },
// ];