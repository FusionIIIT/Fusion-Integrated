import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  applyLeaveRequest,
  getLeaveBalance,
} from '../../actions/leaveActions';
import './ApplyLeavePage.css';

interface ApplyLeavePageProps {
  match: { params: { id: string } } // Assuming ID is used for some internal logic
}

const ApplyLeavePage: React.FC<ApplyLeavePageProps> = ({ match }) => {
  const dispatch = useDispatch();
  const leaveBalance = useSelector(
    (state) => state.leave.leaveBalance[match.params.id]
  );

  const [formValues, setFormValues] = useState({
    leaveType: 'EL',
    startDate: '',
    endDate: '',
    isHalfDay: false,
    reason: '',
    substitute: '',
    stationLeave: false,
    stationAddress: '',
  });

  const leaveCategories = [
    'Casual Leave (CL)',
    'Restricted Holiday (RH)',
    'Special Casual Leave (SCL)',
    'Earned Leave (EL)',
    'Commuted Leave / Medical (COL)',
    'Vacation Leave (VL)',
  ];

  useEffect(() => {
    if (match.params.id) {
      dispatch(getLeaveBalance(match.params.id));
    }
  }, [match.params.id, dispatch]);

  const handleInputChange = (e) => {
    setFormValues({ ...formValues, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const { leaveType, startDate, endDate, isHalfDay, reason, substitute, stationLeave, stationAddress } = formValues;

    const leaveRequest = {
      employeeId: match.params.id,
      leaveType,
      startDate,
      endDate,
      isHalfDay,
      reason,
      substitute,
      stationLeave,
      stationAddress,
    };

    dispatch(applyLeaveRequest(leaveRequest));
  };

  return (
    <div className="apply-leave-page">
      <h2>Apply Leave</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="leaveType">Leave Type:</label>
          <select
            id="leaveType"
            name="leaveType"
            value={formValues.leaveType}
            onChange={handleInputChange}
            required
          >
            {leaveCategories.map((category) => (
              <option key={category} value={category.split('(')[0].trim()}>{category}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="startDate">Start Date:</label>
          <input
            type="date"
            id="startDate"
            name="startDate"
            value={formValues.startDate}
            onChange={handleInputChange}
            required
          />
        </div>
        <div>
          <label htmlFor="endDate">End Date:</label>
          <input
            type="date"
            id="endDate"
            name="endDate"
            value={formValues.endDate}
            onChange={handleInputChange}
            required
          />
        </div>
        <div>
          <label>
            <input
              type="checkbox"
              id="isHalfDay"
              name="isHalfDay"
              checked={formValues.isHalfDay}
              onChange={handleInputChange}
            />
            Is Half Day
          </label>
        </div>
        <div>
          <label htmlFor="reason">Reason:</label>
          <textarea
            id="reason"
            name="reason"
            value={formValues.reason}
            onChange={handleInputChange}
            required
          />
        </div>
        <div>
          <label htmlFor="substitute">Substitute / Responsibility Holder:</label>
          <input
            type="text"
            id="substitute"
            name="substitute"
            value={formValues.substitute}
            onChange={handleInputChange}
          />
        </div>
        <div>
          <label>
            <input
              type="checkbox"
              id="stationLeave"
              name="stationLeave"
              checked={formValues.stationLeave}
              onChange={handleInputChange}
            />
            Station Leave
          </label>
        </div>
        {formValues.stationLeave && (
          <div>
            <label htmlFor="stationAddress">Station Address:</label>
            <input
              type="text"
              id="stationAddress"
              name="stationAddress"
              value={formValues.stationAddress}
              onChange={handleInputChange}
              required
            />
          </div>
        )}
        <button type="submit">Apply Leave</button>
      </form>
    </div>
  );
};

export default ApplyLeavePage;