import { useState } from 'react';
import dayjs from 'dayjs';
import { UnstyledButton, Text, Paper, Group, rem } from '@mantine/core';
import {
    FaUserCheck,
    FaArchive,
    FaCog,
    FaChevronUp,
    FaChevronDown
} from 'react-icons/fa';
import classes from './StatsControls.module.css';

const data = [
    { icon: FaUserCheck, label: 'Users Created' },
    { icon: FaArchive, label: 'Users Archived' },
    { icon: FaCog, label: 'Roles Created' },
];

export function StatsControls() {
    const [date, setDate] = useState(new Date(2024, 9, 11));

    const stats = data.map((stat) => (
        <Paper className={classes.stat} radius="md" shadow="md" p="xs" key={stat.label}>
            <stat.icon
                style={{ width: rem(32), height: rem(32) }}
                className={classes.icon}
            />
            <div>
                <Text fz="sm" className={classes.label}>{stat.label}</Text>
                <Text fz="xl" className={classes.count}>
                    <span className={classes.value}>{Math.floor(Math.random() * 6 + 4)}</span>
                </Text>
            </div>
        </Paper>
    ));

    return (
        <div className={classes.root}>
            <div className={classes.controls}>
                <UnstyledButton
                    className={classes.control}
                    onClick={() => setDate((current) => dayjs(current).add(1, 'day').toDate())}
                >
                    <FaChevronUp
                        style={{ width: rem(16), height: rem(16) }}
                        className={classes.controlIcon}
                    />
                </UnstyledButton>

                <div className={classes.date}>
                    <Text className={classes.day}>{dayjs(date).format('DD')}</Text>
                    <Text className={classes.month}>{dayjs(date).format('MMMM')}</Text>
                </div>

                <UnstyledButton
                    className={classes.control}
                    onClick={() => setDate((current) => dayjs(current).subtract(1, 'day').toDate())}
                >
                    <FaChevronDown
                        style={{ width: rem(16), height: rem(16) }}
                        className={classes.controlIcon}
                    />
                </UnstyledButton>
            </div>
            <Group style={{ flex: 1 }}>{stats}</Group>
        </div>
    );
}
