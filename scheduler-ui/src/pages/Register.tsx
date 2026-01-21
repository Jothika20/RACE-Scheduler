import { Form, Input, Button, message } from 'antd';
import axios from 'axios';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';

interface RegisterFormValues {
    name: string;
    email: string;
    password: string;
}

const Register = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [inviteToken, setInviteToken] = useState('');

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const token = params.get('token');
        if (token) {
            setInviteToken(token);
        }
    }, [location.search]);

    const onFinish = async (values: RegisterFormValues) => {
        try {
            const payload = { ...values, token: inviteToken };
            await axios.post('http://localhost:8000/users/register', payload);
            message.success('Registration successful');
            navigate('/login');
        } catch (err) {
            message.error('Registration failed');
        }
    };

    return (
        <Form onFinish={onFinish} layout="vertical" style={{ maxWidth: 400, margin: '100px auto' }}>
            <h2>Register</h2>

            <Form.Item label="Name" name="name" rules={[{ required: true }]}>
                <Input />
            </Form.Item>

            {!inviteToken && (
                <Form.Item label="Email" name="email" rules={[{ required: true, type: 'email' }]}>
                    <Input />
                </Form.Item>
            )}

            <Form.Item label="Password" name="password" rules={[{ required: true }]} hasFeedback>
                <Input.Password />
            </Form.Item>

            {inviteToken && (
                <div style={{ marginBottom: '10px', color: 'gray', wordBreak: 'break-all' }}>
                    <strong>Invite token:</strong> {inviteToken}
                </div>
            )}

            <Form.Item>
                <Button type="primary" htmlType="submit" block>
                    Register
                </Button>
            </Form.Item>
        </Form>
    );
};

export default Register;
