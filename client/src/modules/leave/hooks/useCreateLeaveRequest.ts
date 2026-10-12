import { useState } from 'react';
import { useMutation } from 'react-query';
import { createLeaveRequest } from 'client/src/modules/leave/services';

const useCreateLeaveRequest = () => {
    const [error, setError] = useState<unknown | null>(null);
    const { mutate, isLoading } = useMutation(createLeaveRequest, {
        onError: (err) => setError(err),
    });

    return { mutate, isLoading, error };
};

export default useCreateLeaveRequest;
