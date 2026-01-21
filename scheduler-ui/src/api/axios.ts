import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
    baseURL: 'http://localhost:8000',
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const attachLogoutInterceptor = (logout: () => void) => {
    api.interceptors.response.use(
        (response) => response,
        (error) => {
            const status = error?.response?.status;
            const detail = error?.response?.data?.detail;

            if (status === 401 && detail?.toLowerCase().includes('expired')) {
                message.error('Session expired. Please log in again.');
                logout(); // 🔹 Calls context logout → navigates
            }
            return Promise.reject(error);
        }
    );
};

export default api;
