import { useState, useEffect, useCallback } from 'react'
import { StatsGrid } from '../../components/StatsGrid/StatsGrid';
import {
    Box,
    Group,
    TextInput,
    Tabs,
    Container,
    Title,
    Divider,
    Modal,
    Button,
    Flex,
    Checkbox,
    Center
} from '@mantine/core'
import { FaCube } from 'react-icons/fa';
import { Simple } from '../../charts/BarChart/Simple/Simple';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '../../data/notifications';
import { showNotification } from '@mantine/notifications';

const ArchiveNotificationsPage = () => {
    const stats = [
        { title: 'Total Notifications', icon: 'speakerPhone', value: '5,173', diff: 34, time: "In last year" },
        { title: 'Archived', icon: 'arch', value: '573', diff: -30, time: "In last year" },
        { title: 'Non - Archived', icon: 'del', value: '2,543', diff: 18, time: "In last year" },
    ];
    const [archiveNotificationstats] = useState(stats)
    const [notificationData, setNotificationData] = useState([])
    const [notificationList, setNotificationList] = useState(notifications);

    useEffect(() => {
        const aggregatedData = notificationList.reduce((acc, notification) => {
            const year = new Date(notification.time).getFullYear();
            if (!acc[year]) {
                acc[year] = { year, Archived: 0 };
            }
            if (notification.isArchived) {
                acc[year].Archived += 1;
            }
            return acc;
        }, {});

        setNotificationData(Object.values(aggregatedData));
    }, [notificationList]);

    const [colors] = useState([
        { name: "Archived", color: 'blue.6' }
    ])


    // tabs sections
    const [searchTerm, setSearchTerm] = useState('');
    const [tabIndex, setTabIndex] = useState(0);
    const [selectedNotifications, setSelectedNotifications] = useState([]);
    const [isArchiving, setIsArchiving] = useState(false);
    const [opened, { open, close }] = useDisclosure(false);

    const handleSearch = (event) => {
        setSearchTerm(event.target.value.toLowerCase());
    };

    const toggleSelectNotification = (id) => {
        setSelectedNotifications((prevSelected) =>
            prevSelected.includes(id)
                ? prevSelected.filter((notificationId) => notificationId !== id)
                : [...prevSelected, id]
        );
    };

    const handleArchive = useCallback(() => {
        open();
    }, [open]);

    const confirmArchive = () => {
        setNotificationList(
            notificationList.map(notification => {
                if (selectedNotifications.includes(notification.id)) {
                    return { ...notification, isArchived: !notification.isArchived };
                }
                return notification;
            })
        );
        setSelectedNotifications([]);
        close();
        showNotification({
            title: isArchiving ? 'Notifications Archived' : 'Notifications Unarchived',
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

    const filteredNotifications = notificationList.filter(notification => {
        const searchLower = searchTerm.toLowerCase();
        return (
            notification.title.toLowerCase().includes(searchLower) ||
            notification.message.toLowerCase().includes(searchLower) ||
            notification.time.toLowerCase().includes(searchLower) ||
            String(notification.year).toLowerCase().includes(searchLower)
        );
    });

    const displayedNotifications = filteredNotifications.filter(notification => (tabIndex === 0 ? !notification.isArchived : notification.isArchived));

    // console.log(displayedNotifications)
    return (
        <Container fluid my="md">
            <Flex
                direction={{ base: 'column', sm: 'row' }}
                gap={{ base: 'sm', sm: 'lg' }}
                justify={{ sm: 'center' }}
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
                        Archive Notifications
                    </Title>
                </Button>
            </Flex>

            <StatsGrid data={archiveNotificationstats} />

            <Divider
                my="xs"
                // variant="dashed"
                labelPosition="center"
                label={
                    <>
                        <FaCube size={12} />
                    </>
                }
            />

            <Simple
                title={"Archived Notifications by year"}
                data={notificationData}
                colors={colors}
                datakey={'year'}
            />


            <Box>
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
                            <Tabs.Tab
                                value='0'
                            >
                                Non-Archived Notifications
                            </Tabs.Tab>
                            <Tabs.Tab value='1'>
                                Archived Notifications
                            </Tabs.Tab>
                        </Tabs.List>


                        <Tabs.Panel value='0' style={{
                            minHeight: 300,
                            maxHeight: 400,
                            overflowY: 'auto',
                            scrollBehavior: 'auto',
                            backgroundColor: '#f8f9fa',
                        }}>
                            <center>
                                {filteredNotifications.map((notification) => (
                                    <Flex
                                        key={notification.id}
                                        position="center"
                                        mb={5}
                                        align="center"
                                        style={{
                                            backgroundColor: 'white',
                                            padding: '10px',
                                            borderRadius: '8px',
                                            border: '2px solid #f0f0f0',
                                            width: '70%',
                                        }}>
                                        <Checkbox
                                            checked={selectedNotifications.includes(notification.id)}
                                            onChange={() => toggleSelectNotification(notification.id)}
                                            styles={{
                                                input: {
                                                    cursor: 'pointer',
                                                    width: '20px',
                                                    height: '20px',
                                                },
                                            }}
                                        />
                                        <Box ml={10} style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 'bold' }}>{notification.title}</div>
                                            <div style={{ marginLeft: '10px' }}>{notification.message}
                                                <div style={{ fontSize: 'small', textAlign: 'end' }}>{notification.time}</div>
                                            </div>
                                        </Box>
                                    </Flex>
                                ))}
                            </center>
                        </Tabs.Panel>
                        <Tabs.Panel value='1' style={{
                            minHeight: 300,
                            maxHeight: 400,
                            overflowY: 'auto',
                            scrollBehavior: 'auto',
                            backgroundColor: '#f8f9fa',
                        }}>
                            <center>

                                {displayedNotifications.map((notification) => (
                                    <Flex
                                        key={notification.id}
                                        position="center"
                                        mb={5}
                                        align="center"
                                        style={{
                                            backgroundColor: 'white',
                                            padding: '10px',
                                            borderRadius: '8px',
                                            border: '2px solid #f0f0f0',
                                            width: '70%',
                                        }}>
                                        <Checkbox
                                            checked={selectedNotifications.includes(notification.id)}
                                            onChange={() => toggleSelectNotification(notification.id)}
                                            styles={{
                                                input: {
                                                    cursor: 'pointer',
                                                    width: '20px',
                                                    height: '20px',
                                                },
                                            }}
                                        />
                                        <Box ml={10} style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 'bold' }}>{notification.title}</div>
                                            <div style={{ marginLeft: '10px' }}>{notification.message}
                                                <div style={{ fontSize: 'small', textAlign: 'end' }}>{notification.time}</div>
                                            </div>
                                        </Box>
                                    </Flex>
                                ))}
                            </center>
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
                            disabled={selectedNotifications.length === 0} // Disable if no Notifications are selected
                        >
                            {tabIndex === '0' ? 'Archive Selected' : 'Unarchive Selected'}
                        </Button>
                    </Group>
                </Center>
                <Modal opened={opened} onClose={close} title="Confirm Action" >
                    <Modal.Body>
                        Are you sure you want to {isArchiving ? 'archive' : 'unarchive'} the selected Notifications?
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


        </Container >
    )
}

export default ArchiveNotificationsPage