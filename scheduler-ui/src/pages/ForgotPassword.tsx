import { useState } from 'react';
import { Form, Input, Button, Card, App, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Login.css';
import { getErrorMessage } from '../utils/error';
import api from '../api/axios';

const ForgotPassword = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const { message } = App.useApp();

    const onFinish = async (values: any) => {
        try {
            setLoading(true);
            const payload: any = {};

            // Determine if it's email or phone
            if (values.identifier.includes('@')) {
                payload.email = values.identifier;
            } else {
                payload.mobile = values.identifier;
            }

            await api.post('/users/forgot-password', payload);
            message.success('Reset link sent! Check your email.');
            setSubmitted(true);

            // Redirect to login after 3 seconds
            setTimeout(() => {
                navigate('/login');
            }, 3000);
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
                <h2 className="login-title">Reset Password</h2>

                {submitted ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <p style={{ fontSize: '16px', marginBottom: '10px' }}>
                            ✓ Check your email for the reset link
                        </p>
                        <p style={{ color: '#666', fontSize: '14px' }}>
                            Redirecting to login...
                        </p>
                    </div>
                ) : (
                    <Form onFinish={onFinish} layout="vertical">
                        <Form.Item
                            label={<span className="form-label">Email or Phone</span>}
                            name="identifier"
                            rules={[
                                {
                                    required: true,
                                    message: 'Please enter your email or phone number'
                                }
                            ]}
                        >
                            <Input placeholder="Enter email or phone number" />
                        </Form.Item>

                        <Form.Item>
                            <Button type="primary" htmlType="submit" block>
                                Send Reset Link
                            </Button>
                        </Form.Item>

                        <div style={{ textAlign: 'center', marginTop: '20px' }}>
                            <span style={{ color: 'white' }}>Remember your password? </span>
                            <Button
                                type="link"
                                onClick={() => navigate('/login')}
                                style={{ padding: 0 }}
                            >
                                Login
                            </Button>
                        </div>
                    </Form>
                )}
            </Card>
        </div>
    );
};

export default ForgotPassword;
