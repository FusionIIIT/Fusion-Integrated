import React, { useState, useEffect } from 'react';
import axios from 'axios';

type ApplyLeaveProps = {};

type LeaveCategory = 'CL' | 'RH' | 'SCL' | 'EL' | 'COL' | 'VL';

const ApplyLeave: React.FC<ApplyLeaveProps> = () => {
    const [formData, setFormData] = useState({
        category: 'CL' as LeaveCategory,
        start_date: '',
        end_date: '',
        purpose: '',
        is_station_leave: false,
        station_address: ''
    });

    const [balances, setBalances] = useState<Record<string, number>>({});
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);

    // 1. Fetch available leave balances on component mount
    useEffect(() => {
        const fetchBalances = async () => {
            try {
                const response = await axios.get('/api/elm/balance-history/');
                if (response.data && response.data.balances) {
                    setBalances(response.data.balances);
                }
            } catch (err) {
                console.error('Failed to fetch leave balances:', err);
            }
        };
        fetchBalances();
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        const checked = (e.target as HTMLInputElement).checked;

        setFormData(prevState => ({
            ...prevState,
            [name]: type === 'checkbox' ? checked : value
        }));
        setError('');
        setSuccess('');
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const start = new Date(formData.start_date);
        const end = new Date(formData.end_date);

        // 2. Client-side date validation (allows single-day leaves where start == end)
        if (start > end) {
            setError('Start date must be before or equal to end date.');
            return;
        }

        // 3. Balance check prior to submission
        const requestedDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 3600 * 24)) + 1;
        const availableBalance = balances[formData.category] ?? 0;

        if (requestedDays > availableBalance) {
            setError(`Insufficient balance. Requested: ${requestedDays} day(s), Available: ${availableBalance} day(s).`);
            return;
        }

        setLoading(true);
        try {
            await axios.post('/api/elm/apply/', formData);
            setSuccess('Leave application submitted successfully!');
            setFormData({
                category: 'CL',
                start_date: '',
                end_date: '',
                purpose: '',
                is_station_leave: false,
                station_address: ''
            });
        } catch (err: any) {
            setError(err.response?.data?.error || 'Error submitting leave application.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fusion-card p-6 max-w-2xl mx-auto bg-white rounded-lg shadow-md">
            <h2 className="text-xl font-bold mb-4 text-gray-800">Apply for Leave (ELM)</h2>

            {/* Dynamic Leave Balance Display Badge */}
            <div className="p-3 mb-4 bg-blue-50 border border-blue-200 text-blue-800 rounded-md text-sm flex justify-between items-center">
                <span>Available <strong>{formData.category}</strong> Balance:</span>
                <span className="font-bold text-base">{balances[formData.category] ?? '--'} Days</span>
            </div>

            {/* Inline Error/Success Messages */}
            {error && (
                <div className="p-3 mb-4 bg-red-100 border border-red-300 text-red-700 rounded-md text-sm">
                    {error}
                </div>
            )}
            {success && (
                <div className="p-3 mb-4 bg-green-100 border border-green-300 text-green-700 rounded-md text-sm">
                    {success}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
                        Leave Category
                    </label>
                    <select
                        id="category"
                        name="category"
                        value={formData.category}
                        onChange={handleChange}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        required
                    >
                        <option value="CL">Casual Leave (CL)</option>
                        <option value="RH">Restricted Holiday (RH)</option>
                        <option value="SCL">Special Casual Leave (SCL)</option>
                        <option value="EL">Earned Leave (EL)</option>
                        <option value="COL">Commuted Leave (COL)</option>
                        <option value="VL">Vacation Leave (VL)</option>
                    </select>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="start_date" className="block text-sm font-medium text-gray-700 mb-1">
                            Start Date
                        </label>
                        <input
                            id="start_date"
                            name="start_date"
                            type="date"
                            value={formData.start_date}
                            onChange={handleChange}
                            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="end_date" className="block text-sm font-medium text-gray-700 mb-1">
                            End Date
                        </label>
                        <input
                            id="end_date"
                            name="end_date"
                            type="date"
                            value={formData.end_date}
                            onChange={handleChange}
                            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            required
                        />
                    </div>
                </div>

                <div>
                    <label htmlFor="purpose" className="block text-sm font-medium text-gray-700 mb-1">
                        Purpose
                    </label>
                    <textarea
                        id="purpose"
                        name="purpose"
                        rows={3}
                        value={formData.purpose}
                        onChange={handleChange}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        placeholder="Reason for leave..."
                        required
                    />
                </div>

                <div className="flex items-center space-x-2">
                    <input
                        id="is_station_leave"
                        name="is_station_leave"
                        type="checkbox"
                        checked={formData.is_station_leave}
                        onChange={handleChange}
                        className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                    />
                    <label htmlFor="is_station_leave" className="text-sm font-medium text-gray-700">
                        Station Leave Required
                    </label>
                </div>

                {formData.is_station_leave && (
                    <div>
                        <label htmlFor="station_address" className="block text-sm font-medium text-gray-700 mb-1">
                            Station Address
                        </label>
                        <input
                            id="station_address"
                            name="station_address"
                            type="text"
                            value={formData.station_address}
                            onChange={handleChange}
                            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            placeholder="Address while out of station"
                            required={formData.is_station_leave}
                        />
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md shadow transition duration-200 disabled:opacity-50"
                >
                    {loading ? 'Submitting...' : 'Submit Application'}
                </button>
            </form>
        </div>
    );
};

export default ApplyLeave;