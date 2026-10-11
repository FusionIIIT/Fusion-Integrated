import React, { useState } from 'react';
import axios from 'axios';

const LeaveApplicationForm: React.FC = () => {
  const [leaveType, setLeaveType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [purpose, setPurpose] = useState('');
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [destination, setDestination] = useState('');
  const [emergencyContact, setEmergencyContact] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const data = {
      leaveType,
      startDate,
      endDate,
      purpose,
      stationLeave: isStationLeave,
      destination: isStationLeave ? destination : '',
      emergencyContact: isStationLeave ? emergencyContact : '',
    };

    try {
      await axios.post('/api/elm/leaves/', data);
      alert('Leave application submitted successfully');
    } catch (error) {
      alert('Failed to submit leave application');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Leave Type:
        <select value={leaveType} onChange={e => setLeaveType(e.target.value)}>
          <option value="">Select...</option>
          <option value="annual">Annual</option>
          <option value="sick">Sick</option>
          <option value="vacation">Vacation</option>
        </select>
      </label>

      <label>
        Start Date:
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
      </label>

      <label>
        End Date:
        <input type="date" value={endDate} onChanget={e => setEndDate(e.target.value)} required />
      </label>

      <label>
        Purpose:
        <textarea value={purpose} onChange={e => setPurpose(e.target.value)} required />
      </label>

      <label>
        <input type="checkbox" checked={isStationLeave} onChange={e => setIsStationLeave(e.target.checked)} />
        Station Leave
      </label>

      {isStationLeave && (
        <>
          <label>
            Destination:
            <input type="text" value={destination} onChange={e => setDestination(e.target.value)} required />
          </label>

          <label>
            Emergency Contact:
            <input type="text" value={emergencyContact} onChange={e => setEmergencyContact(e.target.value)} required />
          </label>
        </>
      )}

      <button type="submit">Submit</button>
    </form>
  );
};

export default LeaveApplicationForm;