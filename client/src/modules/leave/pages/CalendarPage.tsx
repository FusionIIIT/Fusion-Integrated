import React, { useState, useEffect } from 'react';
import { Calendar, DayCellProps } from '@mantine/dates';
import { useQuery } from '@tanstack/react-query';
import { getHolidays } from '../api/client';

const CalendarPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const { data: holidays, isLoading, isError } = useQuery({
    queryKey: ['holidays'],
    queryFn: getHolidays,
  });

  useEffect(() => {
    if (holidays && selectedDate) {
      // Check if the selected date is a holiday
      const isHoliday = holidays.some(holiday => holiday.date === selectedDate.toISOString().split('T')[0]);
      console.log(`Selected Date: ${selectedDate}, Is Holiday: ${isHoliday}`);
    }
  }, [holidays, selectedDate]);

  const handleDayClick = (date: Date) => {
    setSelectedDate(date);
  };

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error fetching holidays</div>;

  return (
    <div>
      <h1>Employee Leave Management - Holiday Calendar</h1>
      <Calendar
        value={selectedDate}
        onChange={handleDayClick}
        dateCellRender={(date, cellProps: DayCellProps) => {
          const isHoliday = holidays.some(holiday => holiday.date === date.toISOString().split('T')[0]);
          return (
            <div
              style={{
                backgroundColor: isHoliday ? '#ffcccc' : 'white',
                border: isHoliday ? '1px solid red' : 'none',
                padding: '5px',
                textAlign: 'center',
              }}
            >
              {cellProps.date.getDate()}
            </div>
          );
        }}
      />
    </div>
  );
};

export default CalendarPage;