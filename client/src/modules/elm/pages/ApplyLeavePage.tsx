import React from 'react';
import { useForm } from 'react-hook-form';

interface ApplyLeaveFormData {
  leaveType: string;
  startDate: string;
  endDate: string;
  reason: string;
  stationLeave: boolean;
  substitute: string;
}

const ApplyLeavePage: React.FC = () => {
  const { register, handleSubmit, formState: { errors } } = useForm<ApplyLeaveFormData>();

  const onSubmit = (data: ApplyLeaveFormData) => {
    // send data to backend
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <label>
        Leave Type:
        <select {...register("leaveType", { required: true })}>
          <option value="">Select...</option>
          {/* Add options here */}
        </select>
        {errors.leaveType && <span>This field is required</span>}
      </label>
      <label>
        Start Date:
        <input type="date" {...register("startDate", { required: true })} />
        {errors.startDate && <span>This field is required</span>}
      </label>
      <label>
        End Date:
        <input type="date" {...register("endDate", { required: true })} />
        {errors.endDate && <span>This field is required</span>}
      </label>
      <label>
        Reason:
        <textarea {...register("reason", { required: true })} />
        {errors.reason && <span>This field is required</span>}
      </label>
      <label>
        Station Leave:
        <input type="checkbox" {...register("stationLeave")} />
      </label>
      <label>
        Substitute:
        <input type="text" {...register("substitute")} />
      </label>
      <input type="submit" />
    </form>
  );
};

export default ApplyLeavePage;