import React, { useState } from 'react';

export const LeaveApplicationForm: React.FC = () => {
  const [leaveType, setLeaveType] = useState('CL');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [purpose, setPurpose] = useState('');
  const [hasStationLeave, setHasStationLeave] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Submitting Leave Application:', { leaveType, startDate, endDate, purpose, hasStationLeave });
  };

  return (
    <div className="p-6 max-w-2xl mx-auto bg-white rounded-xl shadow-md space-y-4">
      <h2 className="text-xl font-bold text-gray-800">Apply for Employee Leave (ELM)</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Leave Type</label>
          <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="VL">Vacation Leave (VL)</option>
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Start Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">End Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" required />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Purpose of Leave</label>
          <textarea value={purpose} onChange={(e) => setPurpose(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" rows={3} required />
        </div>
        <div>
          <label className="inline-flex items-center">
            <input type="checkbox" checked={hasStationLeave} onChange={(e) => setHasStationLeave(e.target.checked)} className="rounded border-gray-300 text-indigo-600 shadow-sm" />
            <span className="ml-2 text-sm text-gray-700">Station Leave Permission (Leaving Jabalpur)</span>
          </label>
        </div>
        <button type="submit" className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
          Submit Leave Application
        </button>
      </form>
    </div>
  );
};
