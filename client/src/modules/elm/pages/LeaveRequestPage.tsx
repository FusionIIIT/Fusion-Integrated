import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { LeaveCategory } from "../api/types";
import { submitLeaveApplication } from "../api/api";

export const LeaveRequestPage = () => {
  const navigate = useNavigate();
  const { leaveCategoryCode } = useParams();
  const [form, handleSubmit, { register, setValue }] = useForm();

  useEffect(() => {
    // Fetch leave category details
    // In a full implementation, this would call the API
  }, [leaveCategoryCode]);

  const onSubmit = async (data: any) => {
    const application = await submitLeaveApplication(
      userId=1,  // placeholder - would come from auth
      leaveCategoryCode,
      data.startDate,
      data.endDate,
      data.purpose,
      data.halftype,
      data.stationLeave
    );
    navigate("/leave-history");
  };

  return (
    <div className="leave-request-page">
      <h2>Request Leave</h2>
      <form {...handleSubmit(onSubmit)} >
        <div className="form-group">
          <label>Purpose/Reason</label>
          <input {...register("purpose", { required: true })} />
        </div>
        <div className="form-group">
          <label>Start Date</label>
          <input type="date" {...register("startDate") } />
        </div>
        <div className="form-group">
          <label>End Date</label>
          <input type="date" {...register("endDate") } />
        </div>
        <div className="form-group">
          <label>Half Type (CL only)</label>
          <select {...register("halftype")}>
            <option value="">Select half</option>
            <option value="FIRST_HALF">First Half</option>
            <option value="SECOND_HALF">Second Half</option>
          </select>
        </div>
        <div className="form-group">
          <label>Station Leave (outside Jabalpur)</label>
          <input type="checkbox" {...register("stationLeave") } />
        </div>
        <button type="submit" className="btn-primary">Submit Request</button>
      </form>
    </div>
  );
};