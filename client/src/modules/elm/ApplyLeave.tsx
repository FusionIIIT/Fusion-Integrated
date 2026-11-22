import React, { useState } from 'react';
import axios from 'axios';

type ApplyLeaveProps = {};

const ApplyLeave: React.FC<ApplyLeaveProps> = () => {
    const [formData, setFormData] = useState({
        category: 'CL' as 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL',
        start_date: '',
        end_date: '',
        purpose: '',
        is_station_leave: false,
        station_address: ''
    });

    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        const val = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;

        setFormData(prevState => ({
            ...prevState,
            [name]: val
        }));
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError('');
        setSuccessMessage('');

        const start = new Date(formData.start_date);
        const end = new Date(formData.end_date);

        // Fix: Allow single-day leaves (start <= end)
        if (start <= end) {
            try {
                await axios.post('/api/elm/apply/', formData);
                setSuccessMessage('Leave application submitted successfully!');
                
                // Reset form on success
                setFormData({
                    category: 'CL',
                    start_date: '',
                    end_date: '',
                    purpose: '',
                    is_station_leave: false,
                    station_address: ''
                });
            } catch (err: any) {
                const backendError = err.response?.data?.error || 'Error submitting leave application.';
                setError(backendError);
            }
        } else {
            setError('Start date must be before or equal to end date.');
        }
    };

    return (
        <div className="fusion-card p-6">
            <h2 className="text-xl font-bold mb-4">Apply for Leave (ELM)</h2>
            
            {successMessage && <p className="text-green-600 mb-4 font-medium">{successMessage}</p>}
            {error && <p className="text-red-500 mb-4 font-medium">{error}</p>}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="category" className="block font-medium mb-1">Category:</label>
                    <select
                        id="category"
                        name="category"
                        value={formData.category}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded"
                    >
                        <option value="CL">Casual Leave (CL)</option>
                        <option value="RH">Restricted Holiday (RH)</option>
                        <option value="SCL">Special Casual Leave (SCL)</option>
                        <option value="EL">Earned Leave (EL)</option>
                        <option value="COL">Commuted Leave (COL)</option>
                        <option value="VL">Vacation Leave (VL)</option>
                    </select>
                </div>

                <div>
                    <label htmlFor="start_date" className="block font-medium mb-1">Start Date:</label>
                    <input
                        id="start_date"
                        name="start_date"
                        type="date"
                        value={formData.start_date}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded"
                    />
                </div>

                <div>
                    <label htmlFor="end_date" className="block font-medium mb-1">End Date:</label>
                    <input
                        id="end_date"
                        name="end_date"
                        type="date"
                        value={formData.end_date}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded"
                    />
                </div>

                <div>
                    <label htmlFor="purpose" className="block font-medium mb-1">Purpose:</label>
                    <textarea
                        id="purpose"
                        name="purpose"
                        value={formData.purpose}
                        onChange={handleChange}
                        required
                        className="w-full border p-2 rounded"
                    />
                </div>

                <div className="flex items-center space-x-2">
                    <input
                        id="is_station_leave"
                        name="is_station_leave"
                        type="checkbox"
                        checked={formData.is_station_leave}
                        onChange={handleChange}
                    />
                    <label htmlFor="is_station_leave">Station Leave Required</label>
                </div>

                {formData.is_station_leave && (
                    <div>
                        <label htmlFor="station_address" className="block font-medium mb-1">Station Address:</label>
                        <input
                            id="station_address"
                            name="station_address"
                            type="text"
                            value={formData.station_address}
                            onChange={handleChange}
                            required={formData.is_station_leave}
                            className="w-full border p-2 rounded"
                        />
                    </div>
                )}

                <button type="submit" className="fusion-button-primary mt-4">
                    Submit Application
                </button>
            </form>
        </div>
    );
};

export default ApplyLeave;