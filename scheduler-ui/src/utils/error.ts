export const getErrorMessage = (error: any): string => {
    if (error?.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
            return detail;
        }
        if (Array.isArray(detail)) {
            // Pydantic validation error
            return detail.map((err: any) => err.msg).join(', ');
        }
        if (typeof detail === 'object') {
            return JSON.stringify(detail);
        }
        return String(detail);
    }
    return error?.message || 'An unexpected error occurred';
};
