import React, { useState } from 'react';
import { http } from '../../lib/http';

const LeaveApplicationForm: React.FC = () => {
  const [leaveType, setLeaveType] = useState<string>('CL');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [purpose, setPurpose] = useState<string>('');
  const [isHalfDay, setIsHalfDay] = useState<boolean>(false);
  const [halfDaySlot, setHalfDaySlot] = useState<string>('FIRST');
  const [hasStationLeave, setHasStationLeave] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    if (!leaveType || !startDate || !endDate || !purpose.trim()) {
      const errMsg = 'Validation Error: Please fill in all required fields (Leave Type, Dates, Purpose).';
      setError(errMsg);
      alert(errMsg);
      setLoading(false);
      return;
    }

    if (startDate > endDate) {
      const errMsg = 'Validation Error: Start Date cannot be after End Date!';
      setError(errMsg);
      alert(errMsg);
      setLoading(false);
      return;
    }

    try {
      const payload = {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        purpose: purpose.trim(),
        is_half_day: isHalfDay,
        half_day_slot: isHalfDay ? halfDaySlot : null,
        has_station_leave: hasStationLeave,
      };

      const res = await http.post('/elm/leaves/', payload);
      const successMsg = `Leave application submitted successfully! Application ID: #${res.data.id}`;
      setMessage(successMsg);
      alert(successMsg);
      resetForm();
    } catch (err: any) {
      let msg = 'Failed to submit leave application.';
      if (err.response?.data) {
        const d = err.response.data;
        if (typeof d === 'string') {
          msg = d;
        } else if (d.end_date) {
          msg = Array.isArray(d.end_date) ? d.end_date[0] : String(d.end_date);
        } else if (d.start_date) {
          msg = Array.isArray(d.start_date) ? d.start_date[0] : String(d.start_date);
        } else if (d.error) {
          msg = typeof d.error === 'string' ? d.error : d.error.message || JSON.stringify(d.error);
        } else if (d.detail) {
          msg = String(d.detail);
        } else {
          msg = JSON.stringify(d);
        }
      } else if (err.message) {
        msg = err.message;
      }
      setError(`Submission failed: ${msg}`);
      alert(`Submission failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setLeaveType('CL');
    setStartDate('');
    setEndDate('');
    setPurpose('');
    setIsHalfDay(false);
    setHalfDaySlot('FIRST');
    setHasStationLeave(false);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow-md rounded-xl space-y-4">
      <h2 className="text-2xl font-bold text-gray-800">Apply for Employee Leave (ELM)</h2>
      {message && (
        <div className="bg-green-50 border-l-4 border-green-500 text-green-700 p-3 rounded">
          {message}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-3 rounded font-medium">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="leaveType" className="block text-sm font-medium text-gray-700">
            Leave Type
          </label>
          <select
            id="leaveType"
            value={leaveType}
            onChange={(e) => setLeaveType(e.target.value)}
            className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          >
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="VL">Vacation Leave (VL)</option>
            <option value="COL">Commuted Leave (COL)</option>
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="startDate" className="block text-sm font-medium text-gray-700">
              Start Date
            </label>
            <input
              type="date"
              id="startDate"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="endDate" className="block text-sm font-medium text-gray-700">
              End Date
            </label>
            <input
              type="date"
              id="endDate"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
        </div>

        <div>
          <label htmlFor="purpose" className="block text-sm font-medium text-gray-700">
            Purpose of Leave
          </label>
          <textarea
            id="purpose"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            rows={3}
            required
            className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          />
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="isHalfDay"
            checked={isHalfDay}
            onChange={(e) => setIsHalfDay(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 shadow-sm"
          />
          <label htmlFor="isHalfDay" className="text-sm text-gray-700">
            Half Day Leave
          </label>
        </div>

        {isHalfDay && (
          <div>
            <label htmlFor="halfDaySlot" className="block text-sm font-medium text-gray-700">
              Half Day Slot
            </label>
            <select
              id="halfDaySlot"
              value={halfDaySlot}
              onChange={(e) => setHalfDaySlot(e.target.value)}
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="FIRST">First Half</option>
              <option value="SECOND">Second Half</option>
            </select>
          </div>
        )}

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="hasStationLeave"
            checked={hasStationLeave}
            onChange={(e) => setHasStationLeave(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 shadow-sm"
          />
          <label htmlFor="hasStationLeave" className="text-sm text-gray-700">
            Station Leave Permission (Leaving Station)
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {loading ? 'Submitting Leave Application...' : 'Submit Leave Application'}
        </button>
      </form>
    </div>
  );
};

export { LeaveApplicationForm };
export default LeaveApplicationForm;
