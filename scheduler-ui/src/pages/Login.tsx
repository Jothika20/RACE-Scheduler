import { useState } from 'react';
import { Form, Input, Button, Spin, Card, App } from 'antd';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './Login.css'; // 👈 Add custom CSS for styling
import { useAuth } from '../context/AuthContext';

import { getErrorMessage } from '../utils/error';

const Login = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const { message } = App.useApp();


    const onFinish = async (values: any) => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            params.append('username', values.username);
            params.append('password', values.password);

            const res = await axios.post('http://localhost:8000/users/login', params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });
            login(res.data.access_token);
            localStorage.setItem('token', res.data.access_token);
            message.success('Login successful');
            navigate('/dashboard', { replace: true });
        } catch (err: any) {
            message.error(getErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            {loading && (
                <div className="spinner-overlay">
                    <Spin
                        indicator={
                            <img
                                src="/images/reva-spinner.webp"
                                alt="Loading..."
                                className="reva-spinner"
                                style={{ width: '150px', height: '150px' }}
                            />
                        }
                    />
                </div>
            )}

            <Card className="login-card" bordered={false}>
                <h2 className="login-title">REVA Academy for Corporate Excellence</h2>
                <Form onFinish={onFinish} layout="vertical">
                    <Form.Item
                        label={<span className="form-label">Username</span>}
                        name="username"
                        rules={[{ required: true, message: 'Please enter your email or phone' }]}
                    >
                        <Input placeholder="Enter email or phone" />
                    </Form.Item>

                    <Form.Item
                        label={<span className="form-label">Password</span>}
                        name="password"
                        rules={[{ required: true, message: 'Please enter your password' }]}
                    >
                        <Input.Password placeholder="Enter password" />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" block>
                            Login
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
};

export default Login;
