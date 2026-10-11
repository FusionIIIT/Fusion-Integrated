import React, { useState } from 'react';
import './ApplyLeavePage.css';

interface LeaveApplication {
  leaveType: string;
  startDate: Date;
  endDate: Date;
  isHalfDay: boolean;
  reason: string;
  substitute: string | null;
  stationLeaveToggle: boolean;
  stationAddress: string | null;
}

const ApplyLeavePage: React.FC = () => {
  const [leaveApplication, setLeaveApplication] = useState<LeaveApplication>({
    leaveType: '',
    startDate: new Date(),
    endDate: new Date(),
    isHalfDay: false,
    reason: '',
    substitute: null,
    stationLeaveToggle: false,
    stationAddress: null,
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setLeaveApplication({
      ...leaveApplication,
      [name]: value,
    });
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // Implement form submission logic here
    console.log('Submitted leave application:', leaveApplication);
    // Example of sending data to server using fetch API
    try {
      const response = await fetch('/api/leave', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(leaveApplication),
      });
      if (response.ok) {
        alert('Leave application submitted successfully!');
      } else {
        alert('Failed to submit leave application.');
      }
    } catch (error) {
      console.error('Error submitting leave application:', error);
      alert('An error occurred while submitting your leave application.');
    }
  };

  return (
    <div className="apply-leave-page">
      <h1>Apply for Leave</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="leaveType">Leave Type:</label>
          <select
            id="leaveType"
            name="leaveType"
            value={leaveApplication.leaveType}
            onChange={handleInputChange}
          >
            <option value="">Select Leave Type</option>
            <option value="CL">Casual Leave (8 days/yr)</option>
            <option value="RH">Restricted Holiday (2 days/yr)</option>
            <option value="SCL">Special Casual Leave (15 days/yr)</option>
            <option value="EL">Earned Leave (30 days/yr)</option>
            <option value="COL">Commuted Leave / Medical (20 days/yr)</option>
            <option value="VL">Vacation Leave (60 days/yr for faculty)</option>
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="startDate">Start Date:</label>
          <input
            type="date"
            id="startDate"
            name="startDate"
            value={leaveApplication.startDate.toISOString().split('T')[0]}
            onChange={handleInputChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="endDate">End Date:</label>
          <input
            type="date"
            id="endDate"
            name="endDate"
            value={leaveApplication.endDate.toISOString().split('T')[0]}
            onChange={handleInputChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="isHalfDay">Is Half Day?</label>
          <input
            type="checkbox"
            id="isHalfDay"
            name="isHalfDay"
            checked={leaveApplication.isHalfDay}
            onChange={(e) => setLeaveApplication({ ...leaveApplication, isHalfDay: e.target.checked })}
          />
        </div>
        <div className="form-group">
          <label htmlFor="reason">Reason:</label>
          <textarea
            id="reason"
            name="reason"
            value={leaveApplication.reason}
            onChange={handleInputChange}
          ></textarea>
        </div>
        <div className="form-group">
          <label htmlFor="substitute">Substitute / Responsibility Holder:</label>
          <input
            type="text"
            id="substitute"
            name="substitute"
            value={leaveApplication.substitute || ''}
            onChange={handleInputChange}
          />
        </div>
        <div className="form-group">
          <label htmlFor="stationLeaveToggle">Station Leave Toggle:</label>
          <input
            type="checkbox"
            id="stationLeaveToggle"
            name="stationLeaveToggle"
            checked={leaveApplication.stationLeaveToggle}
            onChange={(e) => setLeaveApplication({ ...leaveApplication, stationLeaveToggle: e.target.checked })}
          />
        </div>
        {leaveApplication.stationLeaveToggle && (
          <div className="form-group">
            <label htmlFor="stationAddress">Station Address:</label>
            <input
              type="text"
              id="stationAddress"
              name="stationAddress"
              value={leaveApplication.stationAddress || ''}
              onChange={handleInputChange}
            />
          </div>
        )}
        <button type="submit">Apply for Leave</button>
      </form>
    </div>
  );
};

export default ApplyLeavePage;