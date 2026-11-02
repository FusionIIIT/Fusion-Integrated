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
} from '@mantine/core';
import { FaCube } from 'react-icons/fa';
import { Simple } from '../../charts/BarChart/Simple/Simple';
import { useDisclosure } from '@mantine/hooks';
import { announcements } from '../../data/announcements';
import { showNotification } from '@mantine/notifications';

const ArchiveAnnouncementsPage = () => {
    const stats = [
        { title: 'Total Announcements', icon: 'speakerPhone', value: '5,173', diff: 34, time: "In last year" },
        { title: 'Archived', icon: 'arch', value: '573', diff: -30, time: "In last year" },
        { title: 'Non - Archived', icon: 'del', value: '2,543', diff: 18, time: "In last year" },
    ];
    const [archiveAnnouncementStats] = useState(stats)
    const [announcementData, setAnnouncementData] = useState([])
    const [announcementList, setAnnouncementList] = useState(announcements);

    useEffect(() => {
        const aggregatedData = announcementList.reduce((acc, announcement) => {
            const year = new Date(announcement.time).getFullYear();
            if (!acc[year]) {
                acc[year] = { year, Archived: 0 };
            }
            if (announcement.isArchived) {
                acc[year].Archived += 1;
            }
            return acc;
        }, {});

        setAnnouncementData(Object.values(aggregatedData));
    }, [announcementList]);

    const [colors] = useState([
        { name: "Archived", color: 'blue.6' }
    ])


    // tabs sections
    const [searchTerm, setSearchTerm] = useState('');
    const [tabIndex, setTabIndex] = useState(0);
    const [selectedAnnouncements, setSelectedAnnouncements] = useState([]);
    const [isArchiving, setIsArchiving] = useState(false);
    const [opened, { open, close }] = useDisclosure(false);

    const handleSearch = (event) => {
        setSearchTerm(event.target.value.toLowerCase());
    };

    const toggleSelectAnnouncement = (id) => {
        setSelectedAnnouncements((prevSelected) =>
            prevSelected.includes(id)
                ? prevSelected.filter((announcementId) => announcementId !== id)
                : [...prevSelected, id]
        );
    };

    const handleArchive = useCallback(() => {
        open();
    }, [open]);

    const confirmArchive = () => {
        setAnnouncementList(
            announcementList.map(announcement => {
                if (selectedAnnouncements.includes(announcement.id)) {
                    return { ...announcement, isArchived: !announcement.isArchived };
                }
                return announcement;
            })
        );
        setSelectedAnnouncements([]);
        close();
        showNotification({
            title: isArchiving ? 'Announcements Archived' : 'Announcements Unarchived',
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

    const filteredAnnouncements = announcementList.filter(announcement => {
        const searchLower = searchTerm.toLowerCase();
        return (
            announcement.title.toLowerCase().includes(searchLower) ||
            announcement.message.toLowerCase().includes(searchLower) ||
            announcement.time.toLowerCase().includes(searchLower) ||
            String(announcement.year).toLowerCase().includes(searchLower)
        );
    });

    const displayedAnnouncements = filteredAnnouncements.filter(announcement => (tabIndex === 0 ? !announcement.isArchived : announcement.isArchived));

    // console.log(displayedAnnouncements)
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
                        Archive Announcements
                    </Title>
                </Button>
            </Flex>

            <StatsGrid data={archiveAnnouncementStats} />

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

            <Simple title={"Archived Announcements by year"} data={announcementData} colors={colors} />


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
                                Non-Archived Announcements
                            </Tabs.Tab>
                            <Tabs.Tab value='1'>
                                Archived Announcements
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
                                {filteredAnnouncements.map((announcement) => (
                                    <Flex
                                        key={announcement.id}
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
                                            checked={selectedAnnouncements.includes(announcement.id)}
                                            onChange={() => toggleSelectAnnouncement(announcement.id)}
                                            styles={{
                                                input: {
                                                    cursor: 'pointer',
                                                    width: '20px',
                                                    height: '20px',
                                                },
                                            }}
                                        />
                                        <Box ml={10} style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 'bold' }}>{announcement.title}</div>
                                            <div style={{ marginLeft: '10px' }}>{announcement.message}
                                                <div style={{ fontSize: 'small', textAlign: 'end' }}>{announcement.time}</div>
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

                                {displayedAnnouncements.map((announcement) => (
                                    <Flex
                                        key={announcement.id}
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
                                            checked={selectedAnnouncements.includes(announcement.id)}
                                            onChange={() => toggleSelectAnnouncement(announcement.id)}
                                            styles={{
                                                input: {
                                                    cursor: 'pointer',
                                                    width: '20px',
                                                    height: '20px',
                                                },
                                            }}
                                        />
                                        <Box ml={10} style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 'bold' }}>{announcement.title}</div>
                                            <div style={{ marginLeft: '10px' }}>{announcement.message}
                                                <div style={{ fontSize: 'small', textAlign: 'end' }}>{announcement.time}</div>
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
                            disabled={selectedAnnouncements.length === 0} // Disable if no announcements are selected
                        >
                            {tabIndex === '0' ? 'Archive Selected' : 'Unarchive Selected'}
                        </Button>
                    </Group>
                </Center>
                <Modal opened={opened} onClose={close} title="Confirm Action" >
                    <Modal.Body>
                        Are you sure you want to {isArchiving ? 'archive' : 'unarchive'} the selected announcements?
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

export default ArchiveAnnouncementsPage